# 6061-T6 aluminium: real-image case study (v1.1)

## Objective and falsifiable claim

The question is **how three threshold-based computer-vision methods disagree when measuring dark regions on a real optical micrograph of an etched aluminium alloy**. The case does **not** ask the software to decide that these regions are pores, microcracks, or a verified particular precipitate.

This supplements — but does not replace — the 12 synthetic images with pixel-exact masks. It shows behavior on an experimental image without treating unlabeled data as ground truth.

## External image and permission

- **File:** `6061 Aluminum Grain Boundaries.png` (1392 × 1040 pixels).
- **Photographer:** Bob Clemintime (2020).
- **Material:** source describes the top surface of a polished and etched 6061-T6 aluminium plate. The author discusses grain boundaries and secondary-phase/inclusion contrast.
- **Original description and licence:** <https://commons.wikimedia.org/wiki/File:6061_Aluminum_Grain_Boundaries.png>
- **Licence:** Creative Commons Attribution-ShareAlike 4.0; <https://creativecommons.org/licenses/by-sa/4.0/>
- **Image SHA-1 from Commons:** `b4854fc6a0913cd63e94482f607bdc02a945faa9` (full original file, not thumbnail).
- **Distribution:** the app retrieves the source original on demand, verifies its checksum and provides an attribution-preserving ZIP of derived analysis images. It does not imply the photographer endorses the software. Derivative *image content* is released under CC BY-SA 4.0, separately from the BSD-3-Clause software code.
- **Availability:** if Commons cannot be reached from the deployed app, download the **original-resolution file** from Commons and upload it in the case workspace. Resized files are deliberately rejected.

## Reproduction

1. Open the **6061-T6 case study** workspace in the app.
2. Select **Fetch and verify original real image** or provide the original PNG through the upload control.
3. Keep minimum detected area at **24 px²** (or document a different choice).
4. Three dark-feature segmentation methods are run on the same cropped field: uncorrected global Otsu, flat-field-corrected Otsu and adaptive local threshold. Other settings: median filter 3, exclude border-touching components, uncalibrated pixel units.
5. Record for each method candidate count, 2-D area fraction and median equivalent diameter in **pixels**. Compare masks using IoU (agreement *between algorithms*). Repeat flat-field Otsu using intensity thresholds shifted by -8/0/+8 to measure parameter sensitivity.
6. Download the provenance-rich ZIP, keeping the credit notice with any copies of image derivatives.

### Image-area validity

The bottom **13% of the original** is removed *before* segmentation to avoid treating a photographed scale bar and numeric caption as image features. This crop is stated in the exported provenance. The visible `50 µm` annotation is not used to claim a physical calibration: its pixel endpoints have not been independently measured and confirmed. The remaining image reflects polishing, etching, optics and possible artifacts; dark pixels are **not confirmed pores**.

### Outputs to distinguish

| Output | Supports | Does **not** support |
|---|---|---|
| Three-method feature area | The numerical dependence on threshold method | A porosity-volume estimate |
| Pairwise segmentation IoU | Agreement between two algorithms | Segmentation accuracy against an independent label |
| Threshold ±8 test | Sensitivity to this one tuning parameter | Confidence intervals or repeatability across operators |
| Source-file hash | That the specified original image was used | Image measurement or object label validity |
| One documented 6061-T6 field | A real-world challenge to the software | Material certification or population-level generalization |

## Independent validation that remains necessary

A truly validated aerospace-materials case requires **expert consensus masks of defined physical constituents**, imaging metadata, multiple alloy batches, independently validated calibration, replicate specimen fields, blinded labelling and a specimen-level test split. Report metrics separately for each material/imaging condition; validate suspected flaws using appropriate independent microscopy or inspection where justified. Until these are collected the app reports **no real-image Dice / precision / recall / detection accuracy**.

## Scope statement

6061-T6 has uses in engineering, including some aerospace-adjacent structures. This **single photograph is not tied to a documented flight component** and cannot establish mechanical integrity, aerospace certification, or alloy quality. The example illustrates a transferable research *method* rather than proving eligibility for any specific manufacturing application.
