#!/usr/bin/env python3
"""
Quick test that the generated HTML has matchups in the page and in the PDF.
Run after: python3 scripts/generate_tournament_html.py --tournament "WM Phoenix Open" --year 2026
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML_PATH = ROOT / "wm_phoenix_open_2026.html"


def main() -> int:
    if not HTML_PATH.exists():
        print(f"Missing {HTML_PATH}. Generate it first with generate_tournament_html.py")
        return 1

    html = HTML_PATH.read_text(encoding="utf-8")

    checks = [
        ("Download PDF button", "downloadPdf()" in html and "pdf-button" in html),
        ("Matchups tab content", "Round 1 — 3-Balls" in html or "matchups-table" in html),
        ("PDF includes matchups section", "DAILY MATCHUPS" in html and "matchupsEl" in html),
        ("Matchups table in DOM for PDF", 'getElementById(\'daily-matchups\')' in html),
    ]

    ok = True
    for name, passed in checks:
        status = "OK" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            ok = False

    if ok:
        print("\nAll checks passed. Open wm_phoenix_open_2026.html in a browser,")
        print("click 'Download PDF', and confirm the print preview includes a Matchups page.")
        return 0
    print("\nSome checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
