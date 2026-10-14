"""Ensure benchmark is honest about ground truth and failure cases."""
import numpy as np
import pytest

from poroscope.engine import InspectionConfig, inspect
from poroscope.synthetic import SCENARIOS, make_sample, reference_mask_image
from poroscope.validation import benchmark, compare_masks


def test_known_masks_perfect_scores():
    a = np.array([[1, 0], [0, 1]], dtype=bool)
    s = compare_masks(a, a)
    assert s.dice == s.iou == s.precision == s.recall == 1.0


def test_known_mismatch_scores():
    a = np.array([[1, 0], [0, 0]], dtype=bool)
    b = np.array([[1, 1], [0, 0]], dtype=bool)
    s = compare_masks(a, b)
    assert s.precision == 1.0
    assert s.recall == 0.5
    assert s.iou == 0.5
    assert s.dice == pytest.approx(2 / 3)


def test_empty_predictions_and_truth_are_perfect():
    s = compare_masks(np.zeros((4, 4), bool), np.zeros((4, 4), bool))
    assert s.dice == 1.0


def test_empty_predictions_nonempty_truth_have_zero_recall():
    s = compare_masks(np.zeros((4, 4), bool), np.ones((4, 4), bool))
    assert s.precision == 0.0 and s.recall == 0.0


def test_masks_require_matching_shapes_and_boolean():
    with pytest.raises(ValueError):
        compare_masks(np.zeros((5, 5), bool), np.zeros((5, 6), bool))
    with pytest.raises(ValueError):
        compare_masks(np.zeros((5, 5), dtype=int), np.zeros((5, 5), bool))


def test_generators_are_deterministic_across_runs():
    s1 = make_sample(seed=123)
    s2 = make_sample(seed=123)
    assert np.array_equal(np.asarray(s1.image), np.asarray(s2.image))
    assert np.array_equal(s1.truth, s2.truth)
    assert np.array_equal(np.asarray(reference_mask_image(s1)) > 0, s1.truth)


def test_each_scenario_has_real_known_defects():
    for case in SCENARIOS:
        sample = make_sample(case, 3)
        assert 0 < sample.truth.mean() < 0.5


def test_clean_benchmark_dice_above_93_percent():
    sample = make_sample("Moderate | clear contrast", seed=11)
    r = inspect(sample.image, InspectionConfig())
    assert compare_masks(r.mask, sample.truth).dice >= 0.93


def test_benchmark_cardinality_and_scores():
    rows = benchmark(seeds=(11,))
    assert len(rows) == len(SCENARIOS)
    for r in rows:
        assert 0 <= r["dice"] <= 1
        assert 0 <= r["iou"] <= 1


def test_benchmark_rejects_empty_seeds():
    with pytest.raises(ValueError):
        benchmark(seeds=())


def test_generator_rejects_bad_cases():
    for kwargs in ({"scenario": "unavailable"}, {"size": 16}, {"seed": -1}):
        with pytest.raises(ValueError):
            make_sample(**kwargs)
