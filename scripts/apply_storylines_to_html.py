#!/usr/bin/env python3
"""
Apply regenerated storylines into an existing HTML preview.

This updates `<div class="storyline-text">...</div>` within the player rows by
matching on the player name anchor text.

Usage:
  python scripts/apply_storylines_to_html.py \
    --html american_express_2026.html \
    --storylines data/amex_2026_storylines.json \
    --in-place
"""

import argparse
import html as html_lib
import json
import re
from pathlib import Path


def _load_storylines(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "storylines" in data and isinstance(data["storylines"], dict):
        return {k: str(v) for k, v in data["storylines"].items()}
    # flat mapping
    return {k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _escape(s: str) -> str:
    # HTML file expects raw text inside a div, so escape special chars.
    return html_lib.escape(s, quote=False)


def apply_storylines(html_text: str, storylines: dict[str, str]) -> tuple[str, list[str]]:
    updated_players: list[str] = []
    out = html_text

    for player, storyline in storylines.items():
        escaped_name = re.escape(player)

        # Match the specific row segment by finding player-name anchor then the next storyline-text div.
        pattern = re.compile(
            rf'(<div class="player-name"><a[^>]*>{escaped_name}</a></div>[\s\S]*?<div class="storyline-text">)([\s\S]*?)(</div>)',
            flags=re.IGNORECASE,
        )

        def repl(m: re.Match) -> str:
            return m.group(1) + _escape(storyline) + m.group(3)

        new_out, n = pattern.subn(repl, out, count=1)
        if n:
            out = new_out
            updated_players.append(player)

    return out, updated_players


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply storylines to HTML")
    parser.add_argument("--html", type=Path, required=True, help="HTML file to update")
    parser.add_argument("--storylines", type=Path, required=True, help="Storylines JSON")
    parser.add_argument("--output", type=Path, help="Output HTML path (default: stdout)")
    parser.add_argument("--in-place", action="store_true", help="Overwrite the input HTML file")
    args = parser.parse_args()

    html_text = args.html.read_text(encoding="utf-8")
    storylines = _load_storylines(args.storylines)
    if not storylines:
        print(f"❌ No storylines found in {args.storylines}")
        return 1

    updated_html, updated_players = apply_storylines(html_text, storylines)
    print(f"✅ Updated {len(updated_players)} players in HTML")

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

