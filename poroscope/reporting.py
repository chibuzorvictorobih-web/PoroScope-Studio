"""Export a reproducible engineering inspection bundle and PDF report."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO, StringIO
import csv
import json
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

from .engine import InspectionResult


def png_bytes(data: Image.Image | np.ndarray) -> bytes:
    im = data if isinstance(data, Image.Image) else Image.fromarray(np.asarray(data))
    b = BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


def measurements_csv(pores: list[dict]) -> str:
    columns = ["id", "centroid_x_px", "centroid_y_px", "area_px2", "equiv_diameter_px", "eccentricity", "solidity"]
    if any("area_um2" in p for p in pores):
        columns += ["area_um2", "equiv_diameter_um"]
    s = StringIO()
    writer = csv.DictWriter(s, fieldnames=columns)
    writer.writeheader()
    writer.writerows(pores)
    return s.getvalue()


def _page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(40, 28, "PoroScope Studio | Research and preliminary inspection only")
    canvas.drawRightString(A4[0] - 40, 28, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(result: InspectionResult, sample_name: str, sensitivity: dict | None = None) -> bytes:
    output = BytesIO()
    report = SimpleDocTemplate(output, pagesize=A4, topMargin=32, bottomMargin=44, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("PoroScope Studio | Inspection record", styles["Title"]),
        Spacer(1, 9),
        Paragraph(f"Sample: {escape(sample_name)}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 13),
        Paragraph("2-D image screening summary", styles["Heading2"]),
    ]
    m = result.metrics
    rows = [
        ["Metric", "Observed value"],
        ["Candidate regions", str(m["candidate_count"])],
        ["Candidate area fraction", f'{m["area_fraction_pct"]:.3f}% of analysed field'],
        ["Median equivalent diameter", f'{m["median_equiv_diameter_px"]:.2f} px'],
        ["Field size", f'{m["image_width_px"]} x {m["image_height_px"]} px'],
        ["Analysis method", result.config.method],
        ["Polarity", result.config.polarity],
        ["Minimum region size", f'{result.config.min_area_px} px2'],
        ["Relative ROI", f'{result.config.roi_fraction * 100:.0f}% central field'],
    ]
    if "median_equiv_diameter_um" in m:
        rows.append(["Median calibrated diameter", f'{m["median_equiv_diameter_um"]:.3f} micrometres'])
    if sensitivity:
        rows.append(["Shift sensitivity range", f'{sensitivity["range_percentage_points"]:.3f} percentage points'])
    t = Table(rows, colWidths=[215, 283], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2740")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d0dee8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([t, Spacer(1, 8), Paragraph("Annotated field", styles["Heading2"])])
    img = Image.fromarray(result.overlay)
    buff = BytesIO()
    img.save(buff, "PNG")
    buff.seek(0)
    im = RLImage(buff, width=235, height=min(260, 235 * img.height / img.width))
    im.hAlign = "CENTER"
    story.append(im)
    story.extend([
        Spacer(1, 5),
        Paragraph("Interpretation and limits", styles["Heading2"]),
        Paragraph(
            "Pink regions are threshold-derived feature candidates. The blue box marks the analysed field. "
            "The area fraction is a 2-D image-area measurement, not a 3-D volumetric pore fraction. "
            "Camera settings, illumination, specimen preparation, calibration and segmentation choice "
            "can strongly influence results. No material acceptance, structural safety or standards "
            "compliance is determined by this software.", styles["BodyText"],
        ),
        Spacer(1, 8),
        Paragraph(
            "Method context: ASTM E1245-03(2023) discusses automated measurements of discrete "
            "constituents and explicitly does not establish acceptability limits. "
            "This educational workflow is not an implementation certified to that standard.",
            styles["BodyText"],
        ),
    ])
    report.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output.getvalue()


def build_bundle(
    result: InspectionResult,
    sample_name: str,
    original: Image.Image,
    sensitivity: dict | None = None,
) -> bytes:
    image_data = png_bytes(original)
    manifest = result.metadata()
    manifest["sample_name"] = sample_name
    manifest["input_png_sha256"] = sha256(image_data).hexdigest()
    manifest["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    if sensitivity is not None:
        manifest["threshold_sensitivity"] = sensitivity
    items = {
        "input.png": image_data,
        "annotated.png": png_bytes(result.overlay),
        "candidate_mask.png": png_bytes(np.uint8(result.mask) * 255),
        "regions.csv": measurements_csv(result.pores).encode("utf-8"),
        "metadata.json": json.dumps(manifest, indent=2, allow_nan=False).encode("utf-8"),
        "inspection_report.pdf": build_pdf(result, sample_name, sensitivity),
        "READ_ME_FIRST.txt": (
            "PoroScope Studio independent material image inspection record.\n"
            "This contains image-derived candidates, not confirmed porosity or a certified test.\n"
            "Review metadata.json for threshold, calibration, ROI and file provenance.\n"
        ).encode("utf-8"),
    }
    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as archive:
        for name, data in items.items():
            archive.writestr(name, data)
    return output.getvalue()
