#!/usr/bin/env python3
"""
Apply recent form data to HTML preview's Recent Form column.

Updates `<div class="recent-text">...</div>` within player rows by
matching on the player name anchor text.

Usage:
  python scripts/apply_recent_form_to_html.py \
    --html american_express_2026.html \
    --recent-form data/amex_2026_recent_form.json \
    --in-place
"""

import argparse
import html as html_lib
import json
import re
from pathlib import Path


def _load_recent_form(path: Path) -> dict[str, str]:
    """Load recent form data from JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _escape(s: str) -> str:
    """HTML escape special characters."""
    return html_lib.escape(s, quote=False)


def apply_recent_form(html_text: str, recent_form: dict[str, str]) -> tuple[str, list[str]]:
    """Apply recent form data to HTML, return (updated_html, list_of_updated_players)."""
    updated_players: list[str] = []
    out = html_text

    for player, form_text in recent_form.items():
        escaped_name = re.escape(player)

        # Match the specific row segment by finding player-name anchor (with possible extra content like flags/emoji)
        # then the next recent-text div anywhere in that row.
        # Pattern: player name in anchor, followed by anything until we hit recent-text div
        pattern = re.compile(
            rf'(<div class="player-name"><a[^>]*>{escaped_name}[^<]*</a></div>[\s\S]*?<div class="recent-text">)([\s\S]*?)(</div>)',
            flags=re.IGNORECASE,
        )

        def repl(m: re.Match) -> str:
            return m.group(1) + _escape(form_text) + m.group(3)

        new_out, n = pattern.subn(repl, out, count=1)
        if n:
            out = new_out
            updated_players.append(player)

    return out, updated_players


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply recent form to HTML")
    parser.add_argument("--html", type=Path, required=True, help="HTML file to update")
    parser.add_argument("--recent-form", type=Path, required=True, help="Recent form JSON")
    parser.add_argument("--output", type=Path, help="Output HTML path (default: stdout)")
    parser.add_argument("--in-place", action="store_true", help="Overwrite the input HTML file")
    args = parser.parse_args()

    html_text = args.html.read_text(encoding="utf-8")
    recent_form = _load_recent_form(args.recent_form)
    if not recent_form:
        print(f"❌ No recent form data found in {args.recent_form}")
        return 1

    updated_html, updated_players = apply_recent_form(html_text, recent_form)
    print(f"✅ Updated {len(updated_players)} players' recent form in HTML")

    if args.in_place:
        args.html.write_text(updated_html, encoding="utf-8")
        print(f"💾 Wrote in-place: {args.html}")
        return 0

    if args.output:
        args.output.write_text(updated_html, encoding="utf-8")
        print(f"💾 Wrote: {args.output}")
        return 0

    # If neither output nor in-place, print to stdout (discouraged for huge HTML).
    print(updated_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
