"""PoroScope Studio | Streamlit entry point."""
from __future__ import annotations


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from poroscope import __version__
from poroscope.circularity import ENERGY_CONTEXT, PATHWAYS, SOURCES
from poroscope.alloy_case import (
    SOURCE_PAGE, SOURCE_IMAGE_URL, SOURCE_AUTHOR, SOURCE_LICENSE,
    SOURCE_SHA1, SourceVerificationError, retrieve_source_image,
    verify_source_bytes, analyse_field, case_export,
)
from poroscope.engine import InspectionConfig, inspect, threshold_sensitivity
from poroscope.io import decode_image
from poroscope.reporting import build_bundle, build_pdf, png_bytes
from poroscope.synthetic import SCENARIOS, make_sample, reference_mask_image
from poroscope.validation import benchmark, compare_masks

st.set_page_config(
    page_title="PoroScope Studio | Materials Image Inspection",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """<style>
    .block-container{max-width:1300px;padding-top:1.5rem;padding-bottom:4rem}
    .hero{background:linear-gradient(125deg,#0c243b,#163c53 64%,#126778);
        padding:32px 36px;border-radius:19px;color:#f8fafc;margin-bottom:18px}
    .hero small{color:#82dfdb;letter-spacing:2.8px;font-weight:750}
    .hero h1{font-size:2.4rem;line-height:1.15;margin:10px 0;color:#fff}
    .hero p{font-size:1.05rem;color:#d5e6f0;max-width:730px;margin-bottom:0}
    .notice{padding:12px 16px;background:#ebf5fa;border-left:4px solid #0c8193;
        color:#17374b;border-radius:6px;margin:12px 0}
    .tag{font-size:12px;color:#167083;font-weight:700;letter-spacing:.1em}
    @media (max-width:740px){
       .block-container{padding:1rem .75rem 3rem}
       .hero{padding:22px 19px;border-radius:12px}
       .hero h1{font-size:1.85rem}
       .hero p{font-size:.96rem}
       div[data-testid="stMetricValue"]{font-size:1.55rem}
       .stButton button,.stDownloadButton button{width:100%;min-height:46px}
    }
    </style>""",
    unsafe_allow_html=True,
)


def header(title: str, subtitle: str, label: str = "ENGINEERING IMAGE INTELLIGENCE") -> None:
    st.markdown(
        '<div class="hero">'
        f'<small>{label}</small><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def notes() -> None:
    st.info(
        "**Important:** Image-derived candidates are not proven 3-D voids. This is a "
        "reproducible research and screening application, not a certified qualification "
        "or structural safety decision tool."
    )


def settings() -> InspectionConfig:
    st.sidebar.subheader("Detection settings")
    method = st.sidebar.selectbox("Segmentation", ("Flat-field Otsu", "Otsu", "Adaptive", "Manual"), help="Lighting-corrected global, original global, local or custom threshold")
    polarity = st.sidebar.selectbox("Feature contrast", ("Dark", "Bright"))
    shift = st.sidebar.slider("Threshold adjustment", -40, 40, 0, 1)
    manual = 115
    if method == "Manual":
        manual = st.sidebar.slider("Base threshold (0-255)", 0, 255, 115)
    window = 61
    if method == "Adaptive":
        window = st.sidebar.slider("Local window (pixels)", 15, 151, 61, 2)
    kernel = st.sidebar.select_slider("Median noise filter", options=(1, 3, 5, 7), value=3)
    min_area = st.sidebar.number_input("Minimum candidate size (px²)", min_value=1, max_value=20000, value=16)
    ignore_border = st.sidebar.checkbox("Ignore objects touching ROI edge", value=True)
    roi = st.sidebar.select_slider("Central field retained", options=(40, 60, 80, 90, 100), value=100)
    calibrated = st.sidebar.checkbox("I have a verified pixel calibration", value=False)
    scale = st.sidebar.number_input("Micrometres / pixel", min_value=0.001, max_value=10000.0, value=1.0, step=0.1, format="%.3f") if calibrated else None
    return InspectionConfig(
        method=method, polarity=polarity, threshold_shift=int(shift),
        manual_threshold=manual, local_window=window,
        median_kernel=kernel, min_area_px=int(min_area),
        ignore_border=ignore_border, roi_fraction=roi / 100,
        microns_per_pixel=scale,
    )


def show_summary(result, sensitivity: dict) -> None:
    m = result.metrics
    a, b, c, d = st.columns(4)
    a.metric("Candidate regions", f'{m["candidate_count"]:,}')
    b.metric("2-D candidate area", f'{m["area_fraction_pct"]:.2f}%')
    c.metric("Median diameter", f'{m["median_equiv_diameter_px"]:.1f} px')
    d.metric("Threshold sensitivity", f'{sensitivity["range_percentage_points"]:.2f} pp', help="Range across ±8 threshold units; not a confidence interval")
    if result.config.microns_per_pixel is not None:
        st.caption(
            f'Calibrated diameter: {m["median_equiv_diameter_um"]:.2f} µm · '
            f'Candidate density: {m["candidates_per_mm2"]:.1f} per mm²'
        )
    else:
        st.caption("Uncalibrated image: physical length and area density are intentionally omitted.")


def show_distribution(result) -> None:
    if not result.pores:
        st.warning("No candidate regions survived the selected thresholds and size filter.")
        return
    fig, ax = plt.subplots(figsize=(7.5, 2.6))
    diameters = [p["equiv_diameter_px"] for p in result.pores]
    ax.hist(diameters, bins=min(14, max(4, int(np.sqrt(len(diameters)) * 2))), color="#137a8d", edgecolor="white")
    ax.set(xlabel="Equivalent circular diameter (pixels)", ylabel="Count", title="Candidate size distribution")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def view_overview() -> None:
    header(
        "PoroScope Studio", "From optical images to traceable microstructure evidence — inspect, challenge, compare and report."
    )
    notes()
    st.subheader("A genuine analysis workflow, not a formula calculator")
    st.write(
        "Inspect uploaded material images or try deterministic synthetic micrographs. "
        "The pipeline segments candidate features, measures their 2-D geometry, evaluates "
        "threshold sensitivity, benchmarks against known masks, and exports evidence records."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**01 · Investigate**")
        st.write("Detect connected candidates, estimate area fraction, examine sizes, and inspect an annotated overlay.")
    with c2:
        st.markdown("**02 · Validate**")
        st.write("Run 12 repeatable tests on synthetic reference masks, with Dice, IoU, precision and recall.")
    with c3:
        st.markdown("**03 · Document**")
        st.write("Export an inspection PDF and a ZIP containing the input, mask, CSV, metadata and SHA-256 trace.")
    sample = make_sample("Moderate | clear contrast", seed=11)
    result = inspect(sample.image, InspectionConfig())
    left, right = st.columns(2)
    with left:
        st.image(sample.image, caption="Generated, labelled example · synthetic; not a real specimen", use_container_width=True)
    with right:
        st.image(result.overlay, caption="Pink = segmented candidates · blue = analysed field", use_container_width=True)
    st.caption("The example is synthetic and explicitly labelled; do not present benchmark accuracy as accuracy on real materials.")


def view_inspection(config: InspectionConfig) -> None:
    header("Image inspection lab", "Upload a microscope image or use a labelled demonstration sample; settings are in the sidebar.", "02 / INSPECTION")
    notes()
    origin = st.radio("Choose image source", ("Synthetic demonstration", "Upload a micrograph"), horizontal=True)
    source = None
    ground_truth = None
    if origin == "Synthetic demonstration":
        x, y = st.columns([3, 1])
        with x:
            scenario = st.selectbox("Microstructure scenario", tuple(SCENARIOS))
        with y:
            seed = st.number_input("Random seed", min_value=0, max_value=999999, value=11)
        example = make_sample(scenario, int(seed))
        source, ground_truth = example.image, example.truth
        name = f'synthetic_{scenario.split(" |")[0].lower()}_{seed}'
        st.caption("Generated data, not experimental validation. Reference mask is available for inspection.")
        st.download_button("Reference mask PNG", png_bytes(reference_mask_image(example)), file_name="synthetic_reference_mask.png", mime="image/png")
    else:
        upload = st.file_uploader("Upload PNG, JPG, TIFF, BMP or WEBP (max 12 MB, 16 MP)", type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"])
        if upload is None:
            st.info("Choose an image above to start inspecting. No files are saved by this application.")
            return
        try:
            source = decode_image(upload.getvalue())
        except ValueError as error:
            st.error(str(error))
            return
        name = upload.name
    try:
        result = inspect(source, config)
        sensitivity = threshold_sensitivity(source, config)
    except ValueError as error:
        st.error(str(error))
        return
    show_summary(result, sensitivity)
    first, second = st.columns(2)
    with first:
        st.image(source, caption="Input field", use_container_width=True)
    with second:
        st.image(result.overlay, caption="Pink candidate regions · Cyan region of interest", use_container_width=True)
    if ground_truth is not None:
        score = compare_masks(result.mask, ground_truth)
        st.caption(f'Pixel-level synthetic reference comparison: Dice {score.dice:.3f} · IoU {score.iou:.3f} · precision {score.precision:.3f} · recall {score.recall:.3f}.')
    with st.expander("Size distribution and candidate measurements", expanded=True):
        show_distribution(result)
        if result.pores:
            st.dataframe(pd.DataFrame(result.pores), use_container_width=True, hide_index=True)
    with st.expander("Threshold sensitivity (not statistical confidence)"):
        st.write("The same image is re-analysed after shifting the threshold by ±8 intensity units.")
        d = pd.DataFrame({"Shift": sensitivity["shifts_from_nominal"], "Candidate area (%)": sensitivity["area_fraction_pct"]})
        st.dataframe(d, hide_index=True, use_container_width=True)
        st.caption(sensitivity["interpretation"])
    st.subheader("Evidence exports")
    a, b = st.columns(2)
    with a:
        bundle = build_bundle(result, name, source, sensitivity)
        st.download_button("Download complete analysis ZIP", bundle, file_name="poroscope_inspection_record.zip", mime="application/zip", type="primary", use_container_width=True)
    with b:
        st.download_button("Download PDF report", build_pdf(result, name, sensitivity), file_name="poroscope_inspection_report.pdf", mime="application/pdf", use_container_width=True)
    st.caption("Exports contain algorithm settings, source image, SHA-256 provenance hash, candidate geometry and explicit limitations.")


def view_batch(config: InspectionConfig) -> None:
    header("Batch comparison", "Review multiple fields using the same measurement rules, then identify images needing manual attention.", "03 / BATCH WORKFLOW")
    notes()
    st.caption("No automatic material pass/fail decisions are made. The review marker is a user-defined image screening threshold, not a standard.")
    items = st.file_uploader("Optional batch input (maximum 8 images)", type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"], accept_multiple_files=True)
    limit = st.slider("Review marker: image candidate area (%)", 0.1, 25.0, 3.0, 0.1)
    cases = []
    if not items:
        st.caption("Showing a 4-scenario synthetic inspection campaign. Upload your own images to replace it.")
        for scenario in SCENARIOS:
            cases.append((scenario, make_sample(scenario, seed=11).image))
    elif len(items) > 8:
        st.error("At most 8 images per batch. Remove extra files.")
        return
    else:
        for item in items:
            try:
                cases.append((item.name, decode_image(item.getvalue())))
            except ValueError as error:
                st.warning(f"Skipped {item.name}: {error}")
    rows = []
    for name, image in cases:
        result = inspect(image, config)
        s = threshold_sensitivity(image, config)
        frac = result.metrics["area_fraction_pct"]
        rows.append({
            "Image": name,
            "Candidate count": result.metrics["candidate_count"],
            "Area fraction (%)": frac,
            "Median diameter (px)": result.metrics["median_equiv_diameter_px"],
            "Sensitivity span (pp)": s["range_percentage_points"],
            "Marker": "Flag for review" if frac >= limit else "Below marker",
        })
    if not rows:
        st.info("No compatible images were supplied.")
        return
    frame = pd.DataFrame(rows)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    st.bar_chart(frame.set_index("Image")[["Area fraction (%)"]], horizontal=True)
    st.download_button("Export batch comparison CSV", frame.to_csv(index=False).encode(), "batch_inspections.csv", "text/csv", use_container_width=True)
    st.caption("The review threshold is exploratory. Its relationship to performance must be established separately by validated engineering requirements.")


@st.cache_data(show_spinner=False)
def get_benchmark() -> pd.DataFrame:
    return pd.DataFrame(benchmark())


def view_validation() -> None:
    header("Validation & repeatability", "Measure performance against exactly known synthetic masks rather than relying on polished screenshots.", "04 / OPEN EVIDENCE")
    notes()
    st.write("**12 deterministic tests:** four scenarios × three fixed random seeds (11, 21 and 31). All compare predicted candidate pixels with exact generated reference masks.")
    with st.spinner("Executing segmentation benchmark..."):
        df = get_benchmark()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Mean Dice", f'{df["dice"].mean():.3f}')
    k2.metric("Mean IoU", f'{df["iou"].mean():.3f}')
    k3.metric("Mean precision", f'{df["precision"].mean():.3f}')
    k4.metric("Minimum Dice", f'{df["dice"].min():.3f}')
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Download benchmark CSV", df.to_csv(index=False), "synthetic_benchmark.csv", "text/csv")
    st.subheader("What this benchmark actually proves")
    st.write(
        "It measures reproducibility and segmentation performance **on generated data with known masks**. "
        "It does not establish accuracy for etched alloys, real castings, microscopy artifacts, "
        "different cameras, or a certified acceptance test. A real-world validation study "
        "requires labelled experimental images, independent operators, calibration and external checks."
    )
    st.caption("Benchmark uses default flat-field-corrected Otsu segmentation; the difficult case includes a non-pore scratch to test false positives. Changing inspection settings does not change the reference benchmark.")


def view_sustainability() -> None:
    header("Materials & circularity", "Link inspection traceability to lower-waste process thinking without inventing carbon savings.", "05 / RESPONSIBLE ENGINEERING")
    st.subheader("Material-sensitive inspection pathways")
    st.write("A bright spot or dark region is not the same physical defect across every material or imaging method.")
    st.dataframe(pd.DataFrame(PATHWAYS), use_container_width=True, hide_index=True)
    st.subheader("Aluminium recycling energy: published production context")
    en = ENERGY_CONTEXT
    chart = pd.DataFrame({"Primary energy (GJ / tonne)": [en["primary_aluminium_gj_per_tonne"], en["recycled_aluminium_gj_per_tonne"]]}, index=["Primary aluminium", "Recycled aluminium"])
    st.bar_chart(chart, horizontal=True)
    st.caption(
        "IAI-reported values: 186 GJ/t primary and 8.3 GJ/t recycled, based on reported inventories. "
        "They concern production processes, not energy or emissions for the uploaded sample. "
        "Different process boundaries and geography limit direct comparisons."
    )
    st.markdown("**Good decision sequence:** reliable measurement → distinguish actual defect from artifact → evaluate repair or process improvement → document reuse/recycling feasibility → perform a proper product-specific LCA before environmental claims.")
    st.subheader("Sources and interpretation")
    for source in SOURCES:
        st.markdown(f'- [{source["name"]}]({source["url"]})')
    st.warning("This software is not ASTM-certified, not a validated product LCA, and does not estimate real CO₂ savings from pixel measurements.")


def view_alloy_case() -> None:
    header(
        "6061-T6 alloy · real microscopy case",
        "Reproduce an exploratory segmentation challenge on a cited experimental micrograph, then audit algorithm sensitivity.",
        "06 / REAL IMAGE CASE STUDY",
    )
    st.info(
        "**Scientific boundary:** The original author describes etched grain boundaries and second-phase/inclusion "
        "contrast. The image has no expert pore labels. Dark-feature segmentation is **not** validated "
        "porosity detection or an aerospace component acceptance assessment."
    )
    st.markdown(
        f"**Source:** [{SOURCE_AUTHOR} · 6061 aluminium grain boundaries]({SOURCE_PAGE}) · "
        f"{SOURCE_LICENSE}. Derivative analysis visuals carry this image licence. "
        "The app does not claim authorship or sponsorship of the source."
    )
    st.caption(
        "Source: 6061-T6 polished and etched plate; uncalibrated image analysis. "
        "The bottom 13% is cropped out to exclude the photographed scale bar and caption. "
        "No micrometre values are reported until a calibration is independently verified."
    )
    st.image(SOURCE_IMAGE_URL, caption="Original licensed photograph hosted by Wikimedia Commons · Bob Clemintime · CC BY-SA 4.0")
    st.markdown(f"[Open original image and license information]({SOURCE_PAGE})")
    st.write(
        "**Reproducibility:** Only the byte-identical original file is accepted (published SHA-1: "
        f"`{SOURCE_SHA1}`). Use the Fetch button, or download the original file from Commons "
        "and upload it here. Resized previews intentionally fail the checksum check."
    )
    if "verified_alloy_bytes" not in st.session_state:
        st.session_state.verified_alloy_bytes = None
    upload = st.file_uploader("Or supply original Wikimedia PNG", type=["png"], key="alloy_verified_upload")
    if upload is not None:
        try:
            verify_source_bytes(upload.getvalue())
            st.session_state.verified_alloy_bytes = upload.getvalue()
            st.success("Uploaded file matches the published source checksum.")
        except (ValueError, SourceVerificationError) as error:
            st.error(str(error))
            st.session_state.verified_alloy_bytes = None
    if st.button("Fetch and verify original real image", type="primary", use_container_width=True):
        with st.spinner("Fetching and checking image provenance..."):
            try:
                st.session_state.verified_alloy_bytes = retrieve_source_image()
            except SourceVerificationError as error:
                st.warning(f"{error}. The original can be uploaded above instead.")
    image_data = st.session_state.verified_alloy_bytes
    if image_data is None:
        st.info("Fetch or upload the verified original PNG to run the three-method comparison.")
        return
    min_area = st.slider("Minimum dark-region area (pixels²)", min_value=8, max_value=150, value=24, step=4)
    with st.spinner("Analysing real 6061-T6 optical micrograph..."):
        image = verify_source_bytes(image_data)
        rows, details = analyse_field(image, min_area)
    st.subheader("Real image · method-dependent segmentation")
    original, segmented = st.columns(2)
    with original:
        st.image(details["field"], caption="Top 87% of source; cropped scale-bar annotation", use_container_width=True)
    with segmented:
        st.image(details["baseline"].overlay, caption="Flat-field Otsu · highlighted dark-feature candidates", use_container_width=True)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.subheader("Agreement is not accuracy")
    agreements = details["method_agreement_iou"]
    c1, c2 = st.columns(2)
    c1.metric("Otsu vs corrected Otsu · mask IoU", f'{agreements["Otsu"]:.3f}')
    c2.metric("Adaptive vs corrected Otsu · mask IoU", f'{agreements["Adaptive"]:.3f}')
    st.caption(
        "These scores compare algorithms with each other—not with independent defect labels. "
        "High agreement does not prove that a pixel is a pore."
    )
    st.write("**Threshold perturbation** (three analyses of the same image, ±8 intensity units)")
    sensitivity = details["sensitivity"]
    st.dataframe(pd.DataFrame({
        "Shift from nominal": sensitivity["shifts_from_nominal"],
        "2-D dark-feature area (%)": sensitivity["area_fraction_pct"],
    }), hide_index=True, use_container_width=True)
    st.caption(
        f'Area range: {sensitivity["range_percentage_points"]:.3f} percentage points. '
        "This is parameter sensitivity, not a confidence interval or measurement uncertainty."
    )
    with st.expander("What a proper real-material validation must add"):
        st.write(
            "Obtain permissioned representative specimens; image multiple fields per specimen; "
            "collect independently reviewed feature labels; establish calibration and preparation protocol; "
            "split evaluation by specimen; measure false positives, inter-operator variability, "
            "and agreement with independent physical testing. These steps are not yet completed."
        )
    st.download_button(
        "Download attributed real-image evidence ZIP",
        data=case_export(image_data, rows, details),
        file_name="poroscope_6061T6_real_image_case.zip",
        mime="application/zip", use_container_width=True,
    )
    st.caption(
        "Export includes source credit, CC BY-SA licensing, original-image SHA-256, crop fraction, "
        "per-method measurements, mask agreement, inspection PDF, overlay and settings."
    )


with st.sidebar:
    st.markdown("### 🔬 PoroScope Studio")
    st.caption(f"Independent engineering software · v{__version__}")
    page = st.radio(
        "Workspace", ("Overview", "Inspect", "Batch lab", "Validation", "6061-T6 case study", "Materials & circularity"),
        label_visibility="collapsed",
    )
config = settings() if page in ("Inspect", "Batch lab") else InspectionConfig()
if page == "Overview":
    view_overview()
elif page == "Inspect":
    view_inspection(config)
elif page == "Batch lab":
    view_batch(config)
elif page == "Validation":
    view_validation()
elif page == "6061-T6 case study":
    view_alloy_case()
else:
    view_sustainability()

st.divider()
st.caption("PoroScope Studio v1.1.0 · Made for transparent analysis and reproducible learning · No image is intentionally retained by this application after processing.")
