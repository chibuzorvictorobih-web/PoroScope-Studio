# Release verification | PoroScope Studio v1.0.0

**Release packaged:** 2026-10-14 (UTC)

## Completed locally

- Python source compile check: **PASS**.
- Core package test suite: **46 passing tests** (pytest, Python 3.13 in the packaging environment).
- Core package coverage: **99.10%** (319+ evaluated statements; coverage configuration uses the `poroscope/` Python package only, not the Streamlit UI).
- Fixed synthetic benchmark: **12/12 processed** (four scenarios x three seeds).
- Mean synthetic Dice: **0.9890**; smallest synthetic Dice: **0.9560**. These are explicitly synthetic results and not material test-accuracy claims.
- Image, annotation, reference mask, CSV, JSON, PDF and ZIP exports: **PASS** on supplied synthetic examples.
- Inspection PDF: **rendered and visually inspected**, one page for reference test case.
- Source independence and private-local-path scanner: **PASS**.
- ZIP integrity and mandatory hidden workflow checks: validated during final package assembly.

## Awaiting checks in your real deployment

- GitHub-hosted CI (Python 3.11 and 3.12, including Ruff): the workflow is included and will execute *after* publishing. The local packaging environment could not download Ruff.
- Actual Streamlit runtime/browser smoke test: Streamlit was not installed in the packaging environment and network access for package installation was unavailable.
- Phone layout screenshot check: the CSS and responsive view structure are included, but the site must be opened on a real mobile device or responsive browser after deployment.
- Actual microscopy validation: **not undertaken** because no independently labelled physical microscopy image dataset was supplied. Follow the controlled study protocol in `VALIDATION.md` before using for material decisions.

**Assessment note:** well-tested source code, reproducible analysis and transparent scientific limits support a strong student engineering portfolio. Neither this verification record nor an arbitrary 10/10 score substitutes for external experimental validation, actual cloud deployment, or scholarly review.
