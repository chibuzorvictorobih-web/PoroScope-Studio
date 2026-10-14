"""Ground-truth benchmark metrics and reproducibility tools."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .engine import InspectionConfig, inspect
from .synthetic import SCENARIOS, make_sample


@dataclass(frozen=True)
class PixelScores:
    precision: float
    recall: float
    dice: float
    iou: float
    tp: int
    fp: int
    fn: int


def compare_masks(predicted: np.ndarray, truth: np.ndarray) -> PixelScores:
    a, b = np.asarray(predicted), np.asarray(truth)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("Predicted and truth masks must be same-size 2D arrays")
    if a.dtype != bool or b.dtype != bool:
        raise ValueError("Masks must be boolean arrays")
    tp = int(np.logical_and(a, b).sum())
    fp = int(np.logical_and(a, ~b).sum())
    fn = int(np.logical_and(~a, b).sum())
    precision = tp / (tp + fp) if tp + fp else float(tp == 0 and fn == 0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    dice = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0
    iou = tp / (tp + fp + fn) if tp + fp + fn else 1.0
    return PixelScores(precision, recall, dice, iou, tp, fp, fn)


def benchmark(config: InspectionConfig | None = None, seeds: tuple[int, ...] = (11, 21, 31)) -> list[dict]:
    cfg = config or InspectionConfig()
    if not seeds:
        raise ValueError("Benchmark needs at least one seed")
    results = []
    for scenario in SCENARIOS:
        for seed in seeds:
            sample = make_sample(scenario=scenario, seed=seed)
            detected = inspect(sample.image, cfg)
            score = compare_masks(detected.mask, sample.truth)
            results.append({
                "scenario": scenario,
                "seed": seed,
                "precision": round(score.precision, 4),
                "recall": round(score.recall, 4),
                "dice": round(score.dice, 4),
                "iou": round(score.iou, 4),
                "reference_area_pct": round(100 * sample.truth.mean(), 4),
                "detected_area_pct": detected.metrics["area_fraction_pct"],
                "candidate_count": detected.metrics["candidate_count"],
                "intended_ellipses": sample.intended_features,
            })
    return results
