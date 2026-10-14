# Methodology and mathematical definitions

## 1. Imaging scope

PoroScope performs 2-D connected-feature screening of optical material images. It does **not** establish physical class: candidate dark areas could be pores, inclusions or preparation artifacts. Bright features are supported when the user selects the opposite polarity. Images from multiple facilities or microscope modes may need different settings.

## 2. Image preprocessing

A Pillow image is converted to 8-bit luminance (`L`); RGB arrays use a conventional weighted luminance approximation. Alpha is ignored for arrays. A central rectangular region of interest (ROI) retains 40–100% of the field span in both dimensions. Optional median filtering with an odd kernel suppresses impulse-like noise and may alter small shapes or pixel counts.

## 3. Detection algorithms

- **Flat-field Otsu (default):** apply median denoising; estimate slowly varying background as a Gaussian-filtered image with sigma `max(10, min(height, width)/14)` pixels. Subtract it and add the median estimated background. Apply a global Otsu threshold to the flattened image. This aims to reduce broad lighting gradients, not to guarantee illumination invariance.
- **Otsu:** apply a global data-driven threshold to the median-filtered grayscale ROI.
- **Adaptive:** calculate a spatially varying Gaussian local threshold with an odd window, 15–151 pixels.
- **Manual:** compare the median-filtered image against a user-provided grayscale threshold.

All methods support an additive threshold shift of -40…+40 in the UI. For **dark** candidates, pixel intensity below threshold is foreground; for **bright**, pixel intensity above threshold is foreground. Pixels equal to the threshold are background. Uniform fields return no candidates.

Next label eight-connected components. Exclude components smaller than `min_area_px`; optionally exclude components touching the **ROI** border. Connectivity and the removal of small features can merge or discard real pores; the filtering settings are exported with every result.

## 4. Measurements

For `N` candidate pixels in an analysed field of `A` pixels:

`2D area fraction (%) = 100 × N / A`

For each component of pixel area `a`:

`equivalent circular diameter (px) = 2 × sqrt(a / π)`

The system also outputs centroid, eccentricity and solidity as computed by scikit-image's region property methods. Two touching or overlapping candidates can be counted as one; candidate count is not a physically proven void count.

When a microscope-specific scale `s` in **µm/pixel** is independently provided:

`area (µm²) = a × s²`

`diameter (µm) = diameter_px × s`

`analysed field (mm²) = A × s² / 1,000,000`

`candidate density (mm⁻²) = component_count / field_area_mm²`

Absent verified calibration, unit conversion is disabled. Precision shown in the interface is display precision, not an uncertainty declaration.

## 5. Sensitivity

Three full analyses are performed at `threshold_shift −8`, nominal, and `threshold_shift +8` grayscale levels. The displayed sensitivity span is:

`max(2D area fractions) − min(2D area fractions)` in **percentage points**.

This is a **single-parameter perturbation experiment**, *not* measurement confidence, a statistical confidence interval, or a complete uncertainty budget. Pixel size uncertainty, preparation, batch variation, operator variation and microscope repeatability are not included.

## 6. Standards perspective

ASTM E1245-03(2023) describes automatic stereological image measurements of constituents and states that the procedure does not establish acceptance limits. PoroScope is not claimed as an implementation of, or certification to, that standard. It does not follow a complete specimen sampling or material acceptance procedure.

Useful references:

- ASTM overview: https://store.astm.org/e1245-03r23.html
- scikit-image labelled-region example: https://scikit-image.org/docs/stable/auto_examples/segmentation/plot_label.html

## 7. Export integrity

The ZIP archive contains a normalized PNG copy of the inspected image, a binary candidate mask, an overlay, a CSV with all measurements, a JSON settings-and-provenance record, and a PDF summary. `input_png_sha256` checks the normalized PNG content in the ZIP, *not* original JPEG or TIFF file bytes. The report date is in UTC. No implicit structural, material class or sustainability finding is exported.
