#!/usr/bin/env python3
"""
Extract recent form from generated HTML and write to recent_form.json.

Use when the HTML has good recent form data (e.g. from a prior successful
BallDontLie or DataGolf refresh) and you need to restore the JSON.

Usage:
    python scripts/extract_recent_form_from_html.py --html historical/the_genesis_invitational/the_genesis_invitational_2026_v2.html --output historical/the_genesis_invitational/data/the_genesis_invitational_2026_recent_form.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True, help="Path to HTML file")
    parser.add_argument("--output", help="Output JSON path (default: derived from HTML)")
    args = parser.parse_args()

    html_path = Path(args.html)
    if not html_path.is_absolute():
        html_path = ROOT / html_path
    if not html_path.exists():
        print(f"❌ Not found: {html_path}")
        return 1

    html = html_path.read_text(encoding="utf-8")

    # Pattern: player-name div contains "FirstName LastName" then we find the next recent-form-text
    # Structure: <div class="player-name">Scottie Scheffler<span class="expand-indicator">
    # ... <div class="recent-form-text">AT&T Pebble Beach...
    player_pattern = re.compile(
        r'<div class="player-name">([^<]+?)<span class="expand-indicator">',
        re.DOTALL
    )
    form_pattern = re.compile(
        r'class="recent-form-text">(.*?)</div>',
        re.DOTALL
    )

    player_matches = list(player_pattern.finditer(html))
    form_matches = list(form_pattern.finditer(html))

    recent_form = {}
    for i, pm in enumerate(player_matches):
        name = pm.group(1).strip()
        # Find the next recent-form-text after this player block (in the following player-detail row)
        start = pm.end()
        form_in_section = html[start:start + 3000]
        fm = form_pattern.search(form_in_section)
        if fm:
            form_text = fm.group(1).strip()
            form_text = form_text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            recent_form[name] = form_text if form_text else "—"
        else:
            recent_form[name] = "—"

    if args.output:
        out_path = Path(args.output)
    else:
        # Derive from HTML name, e.g. the_genesis_invitational_2026_v2.html -> the_genesis_invitational_2026_recent_form.json
        stem = html_path.stem.replace("_v2", "").replace("_shopify", "")
        if "_2026" in stem:
            out_path = ROOT / "data" / f"{stem}_recent_form.json"
        else:
            out_path = ROOT / "data" / f"{stem}_recent_form.json"

    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(recent_form, indent=2, ensure_ascii=False), encoding="utf-8")

    with_data = sum(1 for v in recent_form.values() if v and v != "—")
    print(f"✅ Extracted {len(recent_form)} players ({with_data} with form) to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
