# Verification, benchmark design and limitations

## Scope

Validation in this release consists of unit-level property tests, exact known-shape tests, image-file error tests, JSON/CSV/PDF/ZIP contract tests, deterministic synthetic-image ground-truth tests and a CI workflow. This is strong verification of the current *software*, not a validation of material identification or manufacturing acceptability.

## Exact known shapes

A 20×20 dark square has a pixel area of 400 in unfiltered manual segmentation, an equivalent circular diameter of `2 * sqrt(400 / pi)` pixels, and a 2-D area of 2.7778% in a 120×120 field. Tests set median kernel to 1 when exact area preservation is required. Calibrated measurements use known micrometres-per-pixel values and reject invalid values. The test suite also covers ROI denominator changes, boundary exclusion, bright features, filtering and uniform fields.

## Synthetic validation

The reproducible dataset is defined in `poroscope/synthetic.py`. Each case is 480×480 pixels, with pixel-exact true masks and fixed seeds. The scenes represent:

1. Sparse high-contrast features.
2. Moderate high-contrast features.
3. Dense or overlapping ellipse regions (so candidate count differs from intended generated ellipses).
4. Non-uniform illumination, noise, relatively low feature contrast **and a dark scratch deliberately excluded from the ground-truth pore mask**.

For each scenario the scripts run seeds 11, 21 and 31 (12 total cases). The default algorithm is background-corrected Otsu, with median kernel 3, minimum area 16 pixels, and border exclusion.

**Observed default baseline in the packaged test run** (these may change with later code/dependency versions):

| Measure | 12 synthetic cases |
|---|---:|
| Mean Dice | ~0.9890 |
| Mean Intersection-over-Union (IoU) | ~0.9788 |
| Mean precision | ~0.9795 |
| Mean recall | ~0.9992 |
| Minimum Dice | ~0.9560 |

High values occur in part because the clean synthetic images are purposefully distinguishable. The challenging image produces false positives from a scratch. These numbers **cannot be quoted as field accuracy**; the population does not represent actual laboratory microscopy photographs.

`TP` is the intersection of candidate and true reference pixels. `FP` is candidate-only. `FN` is truth-only.

- `precision = TP/(TP+FP)`
- `recall = TP/(TP+FN)`
- `Dice = 2TP/(2TP+FP+FN)`
- `IoU = TP/(TP+FP+FN)`

For a pair of empty masks, the code defines perfect agreement. For a nonempty reference and empty prediction, recall/Dice/IoU are zero. This convention is tested.

Reproduce and export the baseline:

```bash
python scripts/reproduce_validation.py
```

## Test quality and CI

The included suite covers processing, positive/negative samples, synthetic determinism and evidence outputs. The `Engineering QA` GitHub Actions workflow performs `ruff check .`, `pytest` with a minimum core-package coverage threshold of 80%, `compileall` and an independence scan for both Python 3.11 and 3.12. The workflow file exists in `.github/workflows/ci.yml`; users must verify the results after publishing.

## Real optical micrograph extension (exploratory, not labelled validation)

Version 1.1 adds a documented 6061-T6 optical image acquired from Wikimedia Commons, with SHA-1 source verification, a fixed bottom image crop, and comparison across global Otsu, flat-field Otsu and adaptive thresholds. No independent expert reference mask exists for this source; cross-algorithm IoU reports **consistency, not correctness**. See [ALLOY_CASE_STUDY.md](ALLOY_CASE_STUDY.md).

## Proposed real-world evaluation (not yet completed)

Collect material-specific image data under a defined protocol. Use multiple preparation batches, illumination settings, microscopy operators and specimen locations. Obtain expert annotations with an adjudication process, split evaluation by **specimen**, not merely image crop, and report per-material precision/recall, false-positive rates and agreement across operators. Use an independent physical characterisation method when appropriate. Never interpret a single image as proof of material safety.

Recommended go/no-go criteria are *process dependent*, not universal. This software intentionally provides no default acceptance criterion or industrial qualification label.

## Known technical constraints

- Pixel-threshold methods confuse similar-intensity material phases and preparation artifacts.
- Converted 8-bit images lose scientific TIFF high-bit-depth information.
- Overlapping components merge into one labelled candidate.
- Micrometres-per-pixel must be externally verified; no auto-calibration is implied.
- Threshold-parameter variation omits statistical operator, pixel-resolution, image-selection and metrology uncertainties.
- Batch review marker is a screening heuristic set by the user, not a material acceptance standard.
- CI checks source and core logic; Streamlit rendering and phone layout require manual deployment checks.
