"""Reproducible real-image *exploratory* alloy case, not defect ground truth.

Original image is hosted by Wikimedia Commons under CC BY-SA 4.0. We verify
its published SHA-1 before using it; a verified photo is not an expert label.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha1, sha256
from io import BytesIO
import json
from urllib.request import Request, urlopen
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image

from .engine import InspectionConfig, inspect, threshold_sensitivity
from .io import decode_image, MAX_UPLOAD_BYTES
from .reporting import build_bundle

SOURCE_PAGE = "https://commons.wikimedia.org/wiki/File:6061_Aluminum_Grain_Boundaries.png"
SOURCE_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/9/92/6061_Aluminum_Grain_Boundaries.png"
SOURCE_SHA1 = "b4854fc6a0913cd63e94482f607bdc02a945faa9"
SOURCE_AUTHOR = "Bob Clemintime"
SOURCE_LICENSE = "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
SOURCE_MATERIAL = "6061-T6 aluminium alloy; polished/etched plate surface"
SOURCE_FEATURE = "Grain-boundary etch contrast and second-phase/inclusion indications; not pore labels"
SOURCE_WIDTH_HEIGHT = (1392, 1040)
BAR_REGION_REMOVED = 0.13  # exclude original bottom annotation and scale bar from measurements


class SourceVerificationError(ValueError):
    """The external image is unavailable or is not the cited original."""


def verify_source_bytes(data: bytes) -> Image.Image:
    """Accept only byte-identical official source image, not a different upload."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise SourceVerificationError("The file exceeds the 12 MB safety limit")
    if sha1(data).hexdigest() != SOURCE_SHA1:
        raise SourceVerificationError(
            "Image checksum does not match the published Commons original. "
            "Download the original file from the linked source page (not a resized preview)."
        )
    image = decode_image(data)
    if image.size != SOURCE_WIDTH_HEIGHT:
        raise SourceVerificationError("Unexpected dimensions for the verified source image")
    return image


def retrieve_source_image() -> bytes:
    """Retrieve only the fixed HTTPS source; fail closed if verification fails."""
    request = Request(SOURCE_IMAGE_URL, headers={"User-Agent": "PoroScopeStudio/1.1 (educational research case)"})
    try:
        with urlopen(request, timeout=12) as response:  # noqa: S310 - constant trusted HTTPS URL
            data = response.read(MAX_UPLOAD_BYTES + 1)
    except (OSError, TimeoutError) as exc:
        raise SourceVerificationError("Cannot reach Wikimedia Commons; upload the original PNG instead") from exc
    verify_source_bytes(data)
    return data


def image_field(image: Image.Image, cut_fraction: float = BAR_REGION_REMOVED) -> Image.Image:
    """Remove caption/scale-bar pixels so image annotations are not segmented."""
    if not 0.05 <= cut_fraction <= 0.30:
        raise ValueError("Cut fraction must be between 5% and 30%")
    w, h = image.size
    if min(w, h) < 64:
        raise ValueError("Invalid field dimensions")
    return image.convert("RGB").crop((0, 0, w, int(h * (1 - cut_fraction))))


def mask_iou(first: np.ndarray, second: np.ndarray) -> float:
    """Agreement between algorithms; **not** precision against a true mask."""
    a, b = np.asarray(first, dtype=bool), np.asarray(second, dtype=bool)
    if a.shape != b.shape:
        raise ValueError("Mask dimensions must agree")
    union = np.count_nonzero(a | b)
    return float(np.count_nonzero(a & b) / union) if union else 1.0


def analyse_field(image: Image.Image, min_area_px: int = 24) -> tuple[list[dict], dict]:
    """Repeat three *algorithm choices* on the same real photo, with no labels.

    Choice-sensitive disagreement is a robustness warning; it does not
    establish the identity of any image feature or accuracy of a classifier.
    """
    if not 1 <= min_area_px <= 10000:
        raise ValueError("Unsupported minimum feature area")
    field = image_field(image)
    base = InspectionConfig(min_area_px=min_area_px, median_kernel=3, ignore_border=True)
    outputs = {}
    rows = []
    for method in ("Otsu", "Flat-field Otsu", "Adaptive"):
        cfg = replace(base, method=method)
        result = inspect(field, cfg)
        outputs[method] = result
        rows.append({
            "method": method,
            "candidate_count": result.metrics["candidate_count"],
            "2d_dark_feature_area_pct": result.metrics["area_fraction_pct"],
            "median_equiv_diameter_px": result.metrics["median_equiv_diameter_px"],
        })
    baseline = outputs["Flat-field Otsu"]
    sensitivity = threshold_sensitivity(field, baseline.config)
    return rows, {
        "field": field,
        "baseline": baseline,
        "sensitivity": sensitivity,
        "method_agreement_iou": {
            method: round(mask_iou(baseline.mask, res.mask), 5)
            for method, res in outputs.items() if method != "Flat-field Otsu"
        },
    }


def case_provenance(original_file: bytes, field: Image.Image, rows: list[dict], details: dict) -> dict:
    return {
        "study": "Real 6061-T6 optical micrograph, qualitative algorithm comparison",
        "material_record": SOURCE_MATERIAL,
        "source_page": SOURCE_PAGE,
        "source_original_file": SOURCE_IMAGE_URL,
        "original_author": SOURCE_AUTHOR,
        "source_license": SOURCE_LICENSE,
        "license_url": LICENSE_URL,
        "published_source_sha1": SOURCE_SHA1,
        "verified_original_sha256": sha256(original_file).hexdigest(),
        "original_dimensions_px": list(SOURCE_WIDTH_HEIGHT),
        "removed_bottom_fraction": BAR_REGION_REMOVED,
        "analysed_field_dimensions_px": list(field.size),
        "feature_meaning": SOURCE_FEATURE,
        "algorithms": rows,
        "algorithm_mask_agreement_iou": details["method_agreement_iou"],
        "threshold_sensitivity": details["sensitivity"],
        "independent_ground_truth_available": False,
        "confirmed_pores": None,
        "real_world_detection_accuracy": None,
        "pixel_calibration": None,
        "interpretation": (
            "Unlabelled real micrograph: detected dark regions may be etched grain boundaries, "
            "secondary phases, inclusions, preparation artifacts or other features. "
            "An algorithm agreement score is NOT performance against ground truth. "
            "No physical dimensions, structural fitness or volumetric porosity are inferred."
        ),
        "derivative_image_license": SOURCE_LICENSE,
    }


def case_export(original_bytes: bytes, rows: list[dict], details: dict) -> bytes:
    """Add original credit and methods comparison to the existing evidence ZIP."""
    verify_source_bytes(original_bytes)
    field = details["field"]
    metadata = case_provenance(original_bytes, field, rows, details)
    # Use the stable, four-argument reporting API so an app hot-reload cannot
    # combine a new case-study module with an older reporting module.
    # Attribution is also included in the PDF's sample title; the export ZIP
    # carries full original-file provenance and the CC BY-SA licence notice.
    report_sample = (
        f"6061-T6 real alloy image (unlabelled) | Source: {SOURCE_AUTHOR}; "
        f"CC BY-SA 4.0; {SOURCE_PAGE}"
    )
    standard_bundle = build_bundle(
        details["baseline"], report_sample, field, details["sensitivity"],
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as destination:
        with ZipFile(BytesIO(standard_bundle)) as base:
            for name in base.namelist():
                destination.writestr(name, base.read(name))
        destination.writestr("alloy_case_provenance.json", json.dumps(metadata, indent=2))
        destination.writestr(
            "IMAGE_CREDIT_AND_LICENSE.txt",
            (
                f"Original image: {SOURCE_AUTHOR}, 6061 Aluminum Grain Boundaries.png\n"
                f"Source: {SOURCE_PAGE}\nLicense: {SOURCE_LICENSE}\nLicense link: {LICENSE_URL}\n"
                "Derivative images: analysed/cropped input, overlay and mask.\n"
                "Image-derived content is shared with CC BY-SA 4.0 credit and terms.\n"
                "Software code remains under the repository's BSD-3-Clause licence.\n"
                "Do not interpret dark regions as confirmed porosity or grain phase identity.\n"
            ),
        )
    return output.getvalue()
