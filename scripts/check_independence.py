"""Avoid sample user-specific paths or institutional endorsements in source."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
search = ["users/dell", "c:\\users\\dell", "scholarship application", "institutional affiliation:"]
excluded = {".png", ".jpg", ".jpeg", ".pdf", ".zip", ".ico", ".pyc"}
problems = []
for p in root.rglob("*"):
    if not p.is_file() or any(part.startswith(".") and part != ".github" and part != ".streamlit" for part in p.relative_to(root).parts):
        continue
    if p.suffix.lower() in excluded:
        continue
    content = p.read_text(encoding="utf-8", errors="replace").lower()
    if p.name == "check_independence.py":
        content = re.sub(r'search = \[.*\]', "", content)
    for forbidden in search:
        if forbidden in content or forbidden in str(p.relative_to(root)).lower():
            problems.append((str(p.relative_to(root)), forbidden))
if problems:
    raise SystemExit(f"Independence check failed: {problems}")
print("Independent-source and local-path check passed.")
