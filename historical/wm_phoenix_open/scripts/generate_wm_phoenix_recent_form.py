#!/usr/bin/env python3
"""
Generate recent form data for any tournament by merging master cache + optional fallback.

Usage:
    python scripts/generate_wm_phoenix_recent_form.py --tournament "WM Phoenix Open" --year 2026
    python scripts/generate_wm_phoenix_recent_form.py --tournament "WM Phoenix Open" --year 2026 --fallback historical/amex/data/amex_2026_recent_form.json
"""

import argparse
import json
import re
from pathlib import Path

# Script lives in historical/wm_phoenix_open/scripts/; project root is 3 levels up
ROOT = Path(__file__).resolve().parent.parent.parent.parent
MASTER_CACHE = ROOT / "data" / "player_recent_form_cache.json"


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def main():
    parser = argparse.ArgumentParser(description="Generate recent form from cache + optional fallback")
    parser.add_argument("--tournament", type=str, required=True, help="Tournament name (e.g. WM Phoenix Open)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--fallback", type=Path, help="Optional path to previous event recent_form.json")
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    players_data_path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    output_path = ROOT / "data" / f"{slug}_{args.year}_recent_form.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    data = json.loads(players_data_path.read_text())
    players = list(data.get("odds", {}).keys())

    master_cache = {}
    if MASTER_CACHE.exists():
        master_cache = json.loads(MASTER_CACHE.read_text())

    fallback_form = {}
    if args.fallback is not None:
        p = Path(args.fallback)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            fallback_form = json.loads(p.read_text())

    recent_form = {}
    for player in players:
        if player in master_cache and master_cache[player] and master_cache[player] != "—":
            recent_form[player] = master_cache[player]
        elif player in fallback_form and fallback_form[player] and fallback_form[player] != "—":
            recent_form[player] = fallback_form[player]
        else:
            recent_form[player] = "—"

    output_path.write_text(json.dumps(recent_form, indent=2, ensure_ascii=False))

    updated_master = False
    for player, form in recent_form.items():
        if form and form != "—" and player not in master_cache:
            master_cache[player] = form
            updated_master = True
    if updated_master:
        MASTER_CACHE.write_text(json.dumps(master_cache, indent=2, ensure_ascii=False))
        print("   ↳ Updated master cache with new entries")

    found_count = sum(1 for v in recent_form.values() if v and v != "—")
    print(f"✅ Generated recent form for {len(players)} players")
    print(f"   - {found_count} with actual data")
    print(f"   → {output_path}")


if __name__ == "__main__":
    main()
