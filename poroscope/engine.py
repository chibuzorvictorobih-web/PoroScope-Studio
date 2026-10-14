"""Auditable segmentation and 2-D pore measurements.

The measured dark regions are *candidates*, not confirmed 3-D porosity.
No acceptance standard is implemented.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi, sqrt
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.filters import threshold_local, threshold_otsu
from skimage.measure import regionprops
from skimage.transform import resize

Method = Literal["Flat-field Otsu", "Otsu", "Adaptive", "Manual"]
Polarity = Literal["Dark", "Bright"]


@dataclass(frozen=True)
class InspectionConfig:
    method: Method = "Flat-field Otsu"
    polarity: Polarity = "Dark"
    threshold_shift: int = 0
    manual_threshold: int = 115
    local_window: int = 61
    median_kernel: int = 3
    min_area_px: int = 16
    ignore_border: bool = True
    roi_fraction: float = 1.0
    microns_per_pixel: float | None = None

    def validate(self) -> None:
        if self.method not in ("Flat-field Otsu", "Otsu", "Adaptive", "Manual"):
            raise ValueError("Unknown segmentation method")
        if self.polarity not in ("Dark", "Bright"):
            raise ValueError("Unknown defect polarity")
        if not -100 <= self.threshold_shift <= 100:
            raise ValueError("Threshold shift must be within [-100, 100]")
        if not 0 <= self.manual_threshold <= 255:
            raise ValueError("Manual threshold must be 0-255")
        if self.local_window < 3 or self.local_window % 2 != 1:
            raise ValueError("Local window must be odd and >= 3")
        if self.median_kernel < 1 or self.median_kernel % 2 != 1:
            raise ValueError("Median kernel must be odd and >= 1")
        if self.min_area_px < 1:
            raise ValueError("Minimum area must be >= 1")
        if not 0.4 <= self.roi_fraction <= 1.0:
            raise ValueError("ROI fraction must be within [0.4, 1]")
        if self.microns_per_pixel is not None and not 0 < self.microns_per_pixel <= 10_000:
            raise ValueError("Microns per pixel must be positive and <= 10000")


@dataclass
class InspectionResult:
    gray: np.ndarray
    mask: np.ndarray
    labels: np.ndarray
    overlay: np.ndarray
    pores: list[dict]
    metrics: dict
    roi: tuple[int, int, int, int]
    threshold_value: float | None
    config: InspectionConfig

    def metadata(self) -> dict:
        return {
            "algorithm": "PoroScope deterministic 2D threshold/connected components v1",
            "config": asdict(self.config),
            "metrics": self.metrics,
            "roi_y0_x0_y1_x1": list(self.roi),
            "threshold_value": self.threshold_value,
            "disclaimer": (
                "Candidate dark/bright features in a single 2D image; no "
                "3D pore fraction, material fitness or standards compliance is inferred."
            ),
        }


def _gray(image: Image.Image | np.ndarray) -> np.ndarray:
    """Convert PIL or uint8 numpy arrays to a grayscale 2-D uint8 image."""
    if isinstance(image, Image.Image):
        x = np.asarray(image.convert("L"))
    else:
        x = np.asarray(image)
        if x.ndim == 3 and x.shape[2] in (3, 4):
            rgb = x[..., :3].astype(float)
            x = np.clip(np.rint(0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]), 0, 255)
        if x.ndim != 2:
            raise ValueError("Expected a 2D grayscale or RGB/RGBA image")
        if x.dtype != np.uint8:
            if not np.issubdtype(x.dtype, np.number) or not np.isfinite(x).all():
                raise ValueError("Image must contain finite numeric pixel values")
            x = np.uint8(np.clip(x, 0, 255))
    if min(x.shape) < 32:
        raise ValueError("Image must be at least 32 by 32 pixels")
    if x.size > 16_000_000:
        raise ValueError("Maximum image size is 16 megapixels")
    return np.ascontiguousarray(x)


def _get_roi(shape: tuple[int, int], fraction: float) -> tuple[int, int, int, int]:
    h, w = shape
    dh = int(round(h * (1 - fraction) / 2))
    dw = int(round(w * (1 - fraction) / 2))
    return dh, dw, h - dh, w - dw


def _segment(pixels: np.ndarray, config: InspectionConfig) -> tuple[np.ndarray, float | None]:
    if int(pixels.max()) == int(pixels.min()):
        return np.zeros(pixels.shape, dtype=bool), None
    smoothed = ndi.median_filter(pixels, size=config.median_kernel)
    if config.method == "Manual":
        t = float(config.manual_threshold + config.threshold_shift)
    elif config.method == "Flat-field Otsu":
        # Gaussian background estimation reduces broad lighting gradients.
        # This can still fail when the image is dominated by feature regions.
        # Work on a bounded-size proxy to keep large microscopy uploads practical.
        # Blur scale remains relative to field dimensions after downsampling.
        reduced_shape = tuple(max(32, min(256, d)) for d in smoothed.shape)
        proxy = resize(smoothed, reduced_shape, order=1, preserve_range=True, anti_aliasing=True)
        proxy_background = ndi.gaussian_filter(proxy, sigma=max(4.0, min(reduced_shape) / 14.0))
        background = resize(proxy_background, smoothed.shape, order=1, preserve_range=True, anti_aliasing=False)
        flattened = smoothed.astype(float) - background + np.median(background)
        t = float(threshold_otsu(flattened) + config.threshold_shift)
        mask = flattened < t if config.polarity == "Dark" else flattened > t
    elif config.method == "Adaptive":
        win = min(config.local_window, min(pixels.shape))
        if win % 2 == 0:
            win -= 1
        t = threshold_local(smoothed, block_size=win, method="gaussian") + config.threshold_shift
    else:
        t = float(threshold_otsu(smoothed) + config.threshold_shift)
    if config.method != "Flat-field Otsu":
        mask = smoothed < t if config.polarity == "Dark" else smoothed > t
    label_map, count = ndi.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(label_map.ravel(), minlength=count + 1)
    keep = sizes >= config.min_area_px
    keep[0] = False
    if config.ignore_border and count:
        border = np.unique(
            np.concatenate((label_map[0], label_map[-1], label_map[:, 0], label_map[:, -1]))
        )
        keep[border] = False
    return keep[label_map], float(t) if np.isscalar(t) else None


def inspect(image: Image.Image | np.ndarray, config: InspectionConfig) -> InspectionResult:
    config.validate()
    gray = _gray(image)
    roi = _get_roi(gray.shape, config.roi_fraction)
    y0, x0, y1, x1 = roi
    local_mask, threshold = _segment(gray[y0:y1, x0:x1], config)
    mask = np.zeros(gray.shape, dtype=bool)
    mask[y0:y1, x0:x1] = local_mask
    labels, _ = ndi.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    scale = config.microns_per_pixel
    pores: list[dict] = []
    for prop in regionprops(labels):
        cy, cx = prop.centroid
        item = {
            "id": int(prop.label),
            "centroid_x_px": round(float(cx), 2),
            "centroid_y_px": round(float(cy), 2),
            "area_px2": int(prop.area),
            "equiv_diameter_px": round(float(prop.equivalent_diameter_area), 3),
            "eccentricity": round(float(prop.eccentricity), 3),
            "solidity": round(float(prop.solidity), 3),
        }
        if scale is not None:
            item["area_um2"] = round(item["area_px2"] * scale**2, 3)
            item["equiv_diameter_um"] = round(item["equiv_diameter_px"] * scale, 3)
        pores.append(item)
    pore_pixels = int(mask.sum())
    roi_area = (y1 - y0) * (x1 - x0)
    eq = np.array([2 * sqrt(p["area_px2"] / pi) for p in pores])
    metrics = {
        "candidate_count": len(pores),
        "candidate_pixels": pore_pixels,
        "roi_pixels": roi_area,
        "area_fraction_pct": round(100 * pore_pixels / roi_area, 5),
        "median_equiv_diameter_px": round(float(np.median(eq)), 3) if len(eq) else 0.0,
        "max_equiv_diameter_px": round(float(np.max(eq)), 3) if len(eq) else 0.0,
        "image_height_px": gray.shape[0],
        "image_width_px": gray.shape[1],
    }
    if scale is not None:
        metrics["median_equiv_diameter_um"] = round(metrics["median_equiv_diameter_px"] * scale, 3)
        metrics["field_area_mm2"] = round(roi_area * scale**2 / 1e6, 6)
        metrics["candidates_per_mm2"] = round(len(pores) * 1e6 / (roi_area * scale**2), 3)
    overlay = np.stack([gray, gray, gray], axis=-1).copy()
    overlay[mask] = np.uint8(np.round(0.52 * overlay[mask] + 0.48 * np.array([255, 43, 119])))
    canvas = Image.fromarray(overlay)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(72, 202, 238), width=2)
    return InspectionResult(gray, mask, labels, np.asarray(canvas), pores, metrics, roi, threshold, config)


def threshold_sensitivity(image: Image.Image | np.ndarray, config: InspectionConfig, step: int = 8) -> dict:
    """Simple parameter sensitivity, NOT a confidence interval."""
    if not 1 <= step <= 30:
        raise ValueError("Sensitivity step must be 1..30")
    from dataclasses import replace

    values = []
    for shift in (-step, 0, step):
        c = replace(config, threshold_shift=max(-100, min(100, config.threshold_shift + shift)))
        values.append(inspect(image, c).metrics["area_fraction_pct"])
    return {
        "shifts_from_nominal": [-step, 0, step],
        "area_fraction_pct": values,
        "range_percentage_points": round(max(values) - min(values), 5),
        "interpretation": "Threshold-parameter sensitivity only; not measurement uncertainty or a confidence interval.",
    }
