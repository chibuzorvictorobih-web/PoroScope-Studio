"""Export contracts, provenance and safe decoding."""
import csv
import hashlib
from io import BytesIO, StringIO
import json
from zipfile import ZipFile

import numpy as np
import pytest
from PIL import Image

from poroscope.circularity import ENERGY_CONTEXT, PATHWAYS, SOURCES
from poroscope.engine import InspectionConfig, inspect, threshold_sensitivity
from poroscope.io import decode_image
from poroscope.reporting import build_bundle, build_pdf, measurements_csv, png_bytes
from poroscope.synthetic import make_sample


def test_png_round_trip():
    demo = make_sample()
    raw = png_bytes(demo.image)
    assert np.array_equal(np.asarray(demo.image), np.asarray(decode_image(raw).convert("L")))


def test_zip_contains_replayable_provenance_and_report():
    demo = make_sample(seed=11)
    r = inspect(demo.image, InspectionConfig(microns_per_pixel=1.5))
    sensitivity = threshold_sensitivity(demo.image, r.config)
    data = build_bundle(r, "sample<alert>&1", demo.image, sensitivity)
    with ZipFile(BytesIO(data)) as z:
        assert set(z.namelist()) == {
            "input.png", "annotated.png", "candidate_mask.png", "regions.csv",
            "metadata.json", "inspection_report.pdf", "READ_ME_FIRST.txt",
        }
        meta = json.loads(z.read("metadata.json"))
        assert meta["input_png_sha256"] == hashlib.sha256(z.read("input.png")).hexdigest()
        assert meta["metrics"] == r.metrics
        assert meta["threshold_sensitivity"] == sensitivity
        assert z.read("inspection_report.pdf").startswith(b"%PDF")
        assert len(z.read("inspection_report.pdf")) > 3000
        rows = list(csv.DictReader(StringIO(z.read("regions.csv").decode())))
        assert len(rows) == r.metrics["candidate_count"]
        assert "equiv_diameter_um" in rows[0]


def test_pdf_report_without_calibration_or_sensitivity():
    sample = make_sample(seed=17)
    r = inspect(sample.image, InspectionConfig())
    doc = build_pdf(r, "Lab & inspection <test>")
    assert doc.startswith(b"%PDF")


def test_csv_with_no_regions_has_headers():
    raw = measurements_csv([])
    assert "equiv_diameter_px" in raw
    assert len(raw.splitlines()) == 1


def test_non_image_and_empty_rejected():
    with pytest.raises(ValueError):
        decode_image(b"")
    with pytest.raises(ValueError):
        decode_image(b"not-an-image")
    with pytest.raises(ValueError):
        decode_image(b"x" * (12 * 1024 * 1024 + 1))


def test_oversize_image_rejected():
    x = Image.new("L", (4500, 4000), color=180)
    with pytest.raises(ValueError, match="16 megapixels"):
        decode_image(png_bytes(x))


def test_circularity_sources_and_scope_are_grounded():
    assert ENERGY_CONTEXT["primary_aluminium_gj_per_tonne"] == 186
    assert ENERGY_CONTEXT["recycled_aluminium_gj_per_tonne"] == 8.3
    assert all(s["url"].startswith("https://") for s in SOURCES)
    assert len(PATHWAYS) >= 4
