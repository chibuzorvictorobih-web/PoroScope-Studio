"""Deterministic synthetic micrographs with pixel-exact reference masks."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


@dataclass
class SyntheticSample:
    image: Image.Image
    truth: np.ndarray
    scenario: str
    seed: int
    intended_features: int


SCENARIOS = {
    "Sparse | clear contrast": (9, 5, 10, 3.0, 1.5),
    "Moderate | clear contrast": (26, 6, 13, 4.5, 3.0),
    "Dense | overlapping pores": (72, 7, 16, 5.0, 5.0),
    "Challenging | uneven light": (29, 6, 14, 16.0, 72.0),
}


def make_sample(scenario: str = "Moderate | clear contrast", seed: int = 11, size: int = 480) -> SyntheticSample:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    if size < 64 or size > 1500:
        raise ValueError("size must be 64..1500")
    if not 0 <= seed < 2**32:
        raise ValueError("seed must fit uint32")
    n, low, high, noise, gradient = SCENARIOS[scenario]
    rng = np.random.default_rng(seed)
    mask_img = Image.new("L", (size, size), color=0)
    drawer = ImageDraw.Draw(mask_img)
    for _ in range(n):
        rx = int(rng.integers(low, high + 1) * size / 480)
        ry = int(rng.integers(low, high + 1) * size / 480)
        rx = max(2, rx)
        ry = max(2, ry)
        x = int(rng.integers(rx + 3, size - rx - 3))
        y = int(rng.integers(ry + 3, size - ry - 3))
        drawer.ellipse((x - rx, y - ry, x + rx, y + ry), fill=255)
    truth = np.asarray(mask_img) > 0
    xx = np.linspace(-1, 1, size)[None, :]
    yy = np.linspace(-1, 1, size)[:, None]
    background = 204 + gradient * (0.6 * xx + 0.4 * yy)
    values = background + rng.normal(0, noise, (size, size))
    values[truth] -= 87 if scenario == "Challenging | uneven light" else 128
    if scenario == "Challenging | uneven light":
        # Artificial dark machining-like scratch is NOT included in the
        # reference pore mask: deliberately tests a false-positive failure.
        start, end = int(size * 0.17), int(size * 0.83)
        for row in range(int(size * 0.28), int(size * 0.28) + max(3, size // 160)):
            values[row, start:end] -= 95
    img = Image.fromarray(np.uint8(np.clip(values, 0, 255))).filter(ImageFilter.GaussianBlur(radius=0.42))
    return SyntheticSample(img, truth, scenario, seed, n)


def reference_mask_image(sample: SyntheticSample) -> Image.Image:
    return Image.fromarray(np.uint8(sample.truth) * 255)
