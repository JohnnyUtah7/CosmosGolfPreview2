#!/usr/bin/env python3
"""
Apply manual corrections to historical data.

Usage:
  python scripts/apply_manual_corrections.py --players-data data/wm_phoenix_open_2026_players_data.json --corrections data/wm_historical_corrections.json
  python scripts/apply_manual_corrections.py --tournament "WM Phoenix Open" --year 2026
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def main():
    parser = argparse.ArgumentParser(description="Apply manual corrections to players_data")
    parser.add_argument("--players-data", type=Path, help="Path to players_data.json")
    parser.add_argument("--corrections", type=Path, help="Path to corrections JSON")
    parser.add_argument("--tournament", type=str, help="Tournament name (to derive paths)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    if args.players_data is not None:
        path = Path(args.players_data)
        if not path.is_absolute():
            path = ROOT / path
    else:
        if not args.tournament:
            print("❌ Provide --players-data or --tournament")
            return 1
        slug = _slugify(args.tournament)
        path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"

    if args.corrections is not None:
        corrections_path = Path(args.corrections)
        if not corrections_path.is_absolute():
            corrections_path = ROOT / corrections_path
    else:
        slug = _slugify(args.tournament) if args.tournament else "amex"
        corrections_path = ROOT / "data" / f"{slug}_historical_corrections.json"

    if not path.exists():
        print(f"❌ Missing {path}")
        return 1
    if not corrections_path.exists():
        print(f"❌ Missing {corrections_path}")
        return 1

    players_data = json.loads(path.read_text(encoding="utf-8"))
    corrections = json.loads(corrections_path.read_text(encoding="utf-8"))

    players = players_data["players"]

    print("📝 Applying manual corrections to historical data...\n")

    corrections_applied = 0
    for player_name, corrections_dict in corrections.items():
        if player_name not in players:
            print(f"⚠️  Player not found: {player_name}")
            continue

        print(f"Correcting {player_name}:")
        for field, correct_value in corrections_dict.items():
            old_value = players[player_name].get(field, "NA")
            if old_value != correct_value:
                players[player_name][field] = correct_value
                corrections_applied += 1
                print(f"  {field}: {old_value} → {correct_value} ✓")
            else:
                print(f"  {field}: {correct_value} (already correct)")
        print()

    players_data["players"] = players
    path.write_text(
        json.dumps(players_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"✅ Applied {corrections_applied} corrections")
    print(f"💾 Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
