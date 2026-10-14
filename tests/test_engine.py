"""Pure-function inspections and regression tests."""
from dataclasses import replace

import numpy as np
import pytest
from PIL import Image

from poroscope.engine import InspectionConfig, inspect, threshold_sensitivity
from poroscope.synthetic import make_sample


def dark_square_image() -> Image.Image:
    a = np.full((120, 120), 220, np.uint8)
    a[40:60, 40:60] = 20
    return Image.fromarray(a)


def test_manual_known_geometry():
    result = inspect(dark_square_image(), InspectionConfig(method="Manual", manual_threshold=100, median_kernel=1))
    assert result.metrics["candidate_count"] == 1
    assert result.metrics["candidate_pixels"] == 400
    assert result.metrics["area_fraction_pct"] == pytest.approx(400 / 14400 * 100, abs=0.0001)
    assert result.pores[0]["area_px2"] == 400


def test_scaled_physical_units_are_correct():
    r = inspect(dark_square_image(), InspectionConfig(method="Manual", microns_per_pixel=2.0, median_kernel=1))
    assert r.metrics["field_area_mm2"] == pytest.approx(0.0576)
    assert r.metrics["median_equiv_diameter_um"] == pytest.approx(2 * 2 * np.sqrt(400 / np.pi), abs=0.002)
    assert r.metrics["candidates_per_mm2"] == pytest.approx(1 / 0.0576, abs=0.001)
    assert r.pores[0]["area_um2"] == 1600


def test_calibration_absent_means_no_spurious_physical_measurement():
    result = inspect(dark_square_image(), InspectionConfig(method="Manual"))
    assert "field_area_mm2" not in result.metrics
    assert "equiv_diameter_um" not in result.pores[0]


def test_border_object_is_excluded_only_if_requested():
    a = np.full((120, 120), 220, dtype=np.uint8)
    a[:10, :10] = 10
    off = inspect(a, InspectionConfig(method="Manual", manual_threshold=100, ignore_border=False, median_kernel=1))
    on = inspect(a, InspectionConfig(method="Manual", manual_threshold=100, ignore_border=True, median_kernel=1))
    assert off.metrics["candidate_pixels"] == 100
    assert on.metrics["candidate_count"] == 0


def test_roi_area_denominator_not_entire_image():
    result = inspect(dark_square_image(), InspectionConfig(method="Manual", roi_fraction=0.5, median_kernel=1))
    assert result.metrics["roi_pixels"] == 3600
    assert result.metrics["area_fraction_pct"] == pytest.approx(400 / 3600 * 100, abs=0.0001)


def test_manual_threshold_adjustment_changes_result():
    a = np.full((100, 100), 220, dtype=np.uint8)
    a[30:60, 30:60] = 120
    cfg = InspectionConfig(method="Manual", manual_threshold=100, median_kernel=1)
    assert inspect(a, cfg).metrics["candidate_count"] == 0
    assert inspect(a, replace(cfg, threshold_shift=30)).metrics["candidate_count"] == 1


def test_bright_polarity():
    a = np.full((100, 100), 30, dtype=np.uint8)
    a[35:45, 50:60] = 240
    cfg = InspectionConfig(method="Manual", manual_threshold=120, polarity="Bright", median_kernel=1)
    assert inspect(a, cfg).metrics["candidate_pixels"] == 100


def test_minimum_region_area_filters_noise():
    a = np.full((100, 100), 220, dtype=np.uint8)
    a[20:30, 20:30] = 20
    a[50:52, 50:52] = 20
    r = inspect(a, InspectionConfig(method="Manual", min_area_px=8, median_kernel=1))
    assert r.metrics["candidate_count"] == 1
    assert r.metrics["candidate_pixels"] == 100


@pytest.mark.parametrize("method", ["Flat-field Otsu", "Otsu", "Adaptive", "Manual"])
def test_three_segmentation_methods(method):
    cfg = InspectionConfig(method=method, manual_threshold=120)
    r = inspect(make_sample(seed=12).image, cfg)
    assert r.metrics["candidate_pixels"] > 0
    assert r.overlay.shape == (480, 480, 3)
    assert len(r.pores) == r.metrics["candidate_count"]


def test_sensitivity_uses_nearby_thresholds():
    s = threshold_sensitivity(make_sample().image, InspectionConfig())
    assert s["shifts_from_nominal"] == [-8, 0, 8]
    assert s["area_fraction_pct"] == sorted(s["area_fraction_pct"])
    assert "not" in s["interpretation"]


def test_completely_uniform_image_has_no_candidates():
    r = inspect(np.full((80, 80), 120, dtype=np.uint8), InspectionConfig())
    assert r.metrics["candidate_count"] == 0
    assert r.threshold_value is None


@pytest.mark.parametrize("changed", [
    {"method": "nonsense"}, {"polarity": "nonsense"}, {"threshold_shift": 101},
    {"manual_threshold": -1}, {"min_area_px": 0}, {"local_window": 10},
    {"median_kernel": 0}, {"roi_fraction": 0.2}, {"microns_per_pixel": 0},
])
def test_invalid_settings_raise(changed):
    with pytest.raises(ValueError):
        inspect(dark_square_image(), replace(InspectionConfig(), **changed))


@pytest.mark.parametrize("shape", [(20, 20), (5000, 5000), (40, 40, 2)])
def test_unsupported_size_or_channels_raise(shape):
    with pytest.raises(ValueError):
        inspect(np.zeros(shape, dtype=np.uint8), InspectionConfig())


def test_nan_pixels_raise():
    x = np.full((60, 60), np.nan)
    with pytest.raises(ValueError):
        inspect(x, InspectionConfig())


def test_rgba_input_accepted():
    img = np.zeros((100, 100, 4), dtype=np.uint8)
    img[..., :3] = 200
    img[..., 3] = 255
    r = inspect(img, InspectionConfig())
    assert r.gray.shape == (100, 100)
