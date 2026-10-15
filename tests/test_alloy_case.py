"""Offline verification of source checks, real-image workflow contract and exports.

A generated array here tests software behavior; it is NOT an experimental micrograph.
"""
from io import BytesIO
import hashlib
import json
from zipfile import ZipFile

import numpy as np
import pytest
from PIL import Image

from poroscope import alloy_case


def patterned_image(size=(128, 112)) -> Image.Image:
    yy, xx = np.indices((size[1], size[0]))
    base = np.full((size[1], size[0], 3), 190, dtype=np.uint8)
    base[((xx - 32) ** 2 + (yy - 35) ** 2) < 100] = 32
    base[((xx - 76) ** 2 + (yy - 56) ** 2) < 64] = 65
    base[:, :, 0] = np.minimum(255, base[:, :, 0].astype(int) + (xx // 8)).astype(np.uint8)
    return Image.fromarray(base)


def matched_original(monkeypatch):
    image = patterned_image()
    stream = BytesIO()
    image.save(stream, "PNG")
    data = stream.getvalue()
    monkeypatch.setattr(alloy_case, "SOURCE_SHA1", hashlib.sha1(data).hexdigest())
    monkeypatch.setattr(alloy_case, "SOURCE_WIDTH_HEIGHT", image.size)
    return data


def test_verification_fails_closed():
    with pytest.raises(alloy_case.SourceVerificationError, match="checksum"):
        alloy_case.verify_source_bytes(b"not the cited image")
    with pytest.raises(alloy_case.SourceVerificationError, match="limit"):
        alloy_case.verify_source_bytes(b"0" * (12 * 1024 * 1024 + 1))


def test_verification_matching_file_and_dimensions(monkeypatch):
    data = matched_original(monkeypatch)
    img = alloy_case.verify_source_bytes(data)
    assert img.size == (128, 112)
    monkeypatch.setattr(alloy_case, "SOURCE_WIDTH_HEIGHT", (124, 112))
    with pytest.raises(alloy_case.SourceVerificationError, match="dimensions"):
        alloy_case.verify_source_bytes(data)


def test_cropping_excludes_bottom_annotations():
    original = patterned_image()
    cropped = alloy_case.image_field(original)
    assert cropped.size == (128, int(112 * 0.87))
    with pytest.raises(ValueError):
        alloy_case.image_field(original, 0.31)


def test_agreement_formula_and_shape_guard():
    a = np.array([[1, 1], [0, 0]], dtype=bool)
    b = np.array([[1, 0], [1, 0]], dtype=bool)
    assert alloy_case.mask_iou(a, b) == pytest.approx(1 / 3)
    assert alloy_case.mask_iou(a * False, b * False) == 1.0
    with pytest.raises(ValueError):
        alloy_case.mask_iou(a, b[:1])


def test_algorithm_comparison_reports_no_ground_truth():
    rows, details = alloy_case.analyse_field(patterned_image())
    assert [r["method"] for r in rows] == ["Otsu", "Flat-field Otsu", "Adaptive"]
    assert all(0 <= r["2d_dark_feature_area_pct"] <= 100 for r in rows)
    assert all(0 <= x <= 1 for x in details["method_agreement_iou"].values())
    assert len(details["sensitivity"]["area_fraction_pct"]) == 3
    with pytest.raises(ValueError):
        alloy_case.analyse_field(patterned_image(), 0)


def test_case_export_contains_license_and_trace(monkeypatch):
    original = matched_original(monkeypatch)
    rows, details = alloy_case.analyse_field(alloy_case.verify_source_bytes(original))
    provenance = alloy_case.case_provenance(original, details["field"], rows, details)
    assert provenance["independent_ground_truth_available"] is False
    assert provenance["confirmed_pores"] is None
    assert provenance["real_world_detection_accuracy"] is None
    assert provenance["verified_original_sha256"] == hashlib.sha256(original).hexdigest()
    record = alloy_case.case_export(original, rows, details)
    with ZipFile(BytesIO(record)) as archive:
        assert "alloy_case_provenance.json" in archive.namelist()
        assert "IMAGE_CREDIT_AND_LICENSE.txt" in archive.namelist()
        assert "inspection_report.pdf" in archive.namelist()
        manifest = json.loads(archive.read("alloy_case_provenance.json"))
        assert manifest["original_author"] == "Bob Clemintime"
        assert manifest["original_dimensions_px"] == [128, 112]
        assert b"CC BY-SA 4.0" in archive.read("IMAGE_CREDIT_AND_LICENSE.txt")
        assert archive.read("inspection_report.pdf").startswith(b"%PDF")


def test_export_works_with_legacy_four_argument_reporting_api(monkeypatch):
    """Regression: Streamlit can temporarily retain an earlier module after redeploy."""
    from poroscope.reporting import build_bundle as current_build_bundle

    original = matched_original(monkeypatch)
    rows, details = alloy_case.analyse_field(alloy_case.verify_source_bytes(original))
    captured = {}

    def reporting_api_v1(result, sample_name, field, sensitivity):
        captured["sample_name"] = sample_name
        return current_build_bundle(result, sample_name, field, sensitivity)

    monkeypatch.setattr(alloy_case, "build_bundle", reporting_api_v1)
    bundle = alloy_case.case_export(original, rows, details)
    assert "Bob Clemintime" in captured["sample_name"]
    assert "CC BY-SA 4.0" in captured["sample_name"]
    with ZipFile(BytesIO(bundle)) as archive:
        assert archive.read("inspection_report.pdf").startswith(b"%PDF")
        metadata = json.loads(archive.read("metadata.json"))
        assert "Bob Clemintime" in metadata["sample_name"]
        assert archive.read("IMAGE_CREDIT_AND_LICENSE.txt").count(b"Bob Clemintime") == 1
