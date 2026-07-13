#!/usr/bin/env python3
"""
Inject OWGR and country from players_data.json into an existing WM Phoenix HTML file.
Updates each <div class="player-country"> to show correct country and OWGR #N.

Usage:
    python scripts/inject_owgr_into_html.py
    python scripts/inject_owgr_into_html.py --html wm_phoenix_open_2026.html --players-data data/wm_phoenix_open_2026_players_data.json
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ISO 2-letter code -> display name (for player-country line)
CODE_TO_DISPLAY = {
    "US": "USA", "JP": "JPN", "KR": "KOR", "GB": "ENG", "NO": "NOR", "DK": "DEN",
    "CA": "CAN", "AU": "AUS", "ZA": "RSA", "DE": "GER", "FR": "FRA", "IT": "ITA",
    "ES": "ESP", "IE": "IRL", "SE": "SWE", "BE": "BEL", "AT": "AUT", "FI": "FIN",
    "CN": "CHN", "IN": "IND", "AR": "ARG", "CO": "COL", "MX": "MEX", "PR": "PUR",
    "PH": "PHI", "NZ": "NZL", "NL": "NED", "TH": "THA", "TW": "TPE", "VE": "VEN",
    "CL": "CHI", "SCO": "SCO", "NIR": "NIR", "WAL": "WAL", "ENG": "ENG",
}


def main():
    parser = argparse.ArgumentParser(description="Inject OWGR and country into WM Phoenix HTML")
    parser.add_argument("--html", type=Path, default=ROOT / "wm_phoenix_open_2026.html", help="HTML file to update")
    parser.add_argument("--players-data", type=Path, default=ROOT / "data" / "wm_phoenix_open_2026_players_data.json", help="players_data JSON")
    args = parser.parse_args()

    with open(args.players_data, encoding="utf-8") as f:
        data = json.load(f)
    countries = data.get("countries", {})
    owgr = data.get("owgr", {})

    with open(args.html, encoding="utf-8") as f:
        html = f.read()

    # Match: player-name div (name text + optional expand span) then player-country div
    pattern = re.compile(
        r'<div class="player-name">([^<]+)(?:<span class="expand-indicator"></span>)?</div>\s*<div class="player-country">([^<]*)</div>',
        re.DOTALL,
    )

    def repl(match):
        name = match.group(1).strip()
        code = countries.get(name, "US")
        country_display = CODE_TO_DISPLAY.get(code, code)
        rank = owgr.get(name)
        owgr_str = str(rank) if rank is not None else "-"
        new_line = f"{country_display} - OWGR #{owgr_str}"
        # Replace content inside the player-country div (indices relative to match)
        start_rel = match.start(2) - match.start(0)
        end_rel = match.end(2) - match.start(0)
        return match.group(0)[:start_rel] + new_line + match.group(0)[end_rel:]

    new_html = pattern.sub(repl, html)
    if new_html == html:
        print("No player-country blocks matched (pattern may have changed).")
        return 1

    with open(args.html, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"Updated OWGR and country in {args.html.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
