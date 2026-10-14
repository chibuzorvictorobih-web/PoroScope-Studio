# Publication and deployment guide

## A. Run and inspect locally

1. Extract `PoroScope-Studio.zip` to a normal folder.
2. Install Python 3.11 or 3.12 if it is not installed.
3. On Windows, double-click `START_HERE_Windows.bat`; otherwise use `python -m pip install -r requirements.txt` and `python -m streamlit run app.py`.
4. Open the `Inspect`, `Batch lab`, `Validation` and `Materials & circularity` pages. Download one PDF and one ZIP inspection report.
5. If an installer fails, open a terminal in the folder to read the full error and rerun the installation command; do not delete files from the package.

## B. Publish a new GitHub repository

1. Create a **new empty** GitHub repository called `PoroScope-Studio` (or another independent project name).
2. Upload the **contents of the extracted folder**, not the outer ZIP. Keep `app.py` and `requirements.txt` at the repository root.
3. Make sure hidden directories `.github/workflows/` and `.streamlit/` are uploaded. GitHub's web interface can upload hidden paths when placed inside the folder structure; confirm the final tree explicitly.
4. Commit everything. Never upload `.venv`, `__pycache__`, `.pytest_cache` or local private files.
5. Open GitHub > **Actions** and verify the **Engineering QA** workflow runs. Do not assume CI passed without viewing the completed run.

## C. Deploy with Streamlit Community Cloud

1. Go to https://share.streamlit.io/ and sign in with GitHub.
2. Select your newly created repo, branch `main` and entry point `app.py`.
3. Deploy and open the published address. The app uses only requirements defined in `requirements.txt` and in-memory demo generation.
4. If the first deploy fails, check the deployment logs, package resolver and Python version in your hosting environment.
5. Keep the actual live address in the GitHub repository description; do not use a placeholder as a live link.

## D. Mobile acceptance checklist (manual validation required)

A mobile stylesheet is included; **its actual appearance must be checked in a browser on a phone or in responsive developer tools after deployment**. The build environment used to package the project did not have Streamlit and could not install it for visual browser verification.

- [ ] Sidebar navigation opens, closes and all five pages remain reachable.
- [ ] The header fits without sideways scrolling at 360 px and 390 px viewport widths.
- [ ] Image cards stack naturally and keep captions readable.
- [ ] Batch results and measurements remain readable (horizontal scrolling **inside** tables is acceptable).
- [ ] The file uploader works from the phone photo/document picker.
- [ ] All download buttons are reachable and PDF/ZIP exports open correctly.
- [ ] No text, input, chart or legend is clipped in light or dark OS display settings.
- [ ] Repeat the checks on a desktop browser after deployment.

## E. Release-quality gate

```bash
python -m compileall -q app.py poroscope tests
python -m pytest -q --cov=poroscope --cov-fail-under=80
python scripts/reproduce_validation.py
python scripts/check_independence.py
```

CI also runs Ruff, Python compilation and full tests in the GitHub-hosted environment. Test status and visual deployment status are separate checks.
