#!/usr/bin/env python3
"""
Apply cached historical tournament results to player data files.

This script reads from the tournament results cache and updates player
data JSON files with historical finish positions.

Usage:
    # First, fetch the results (creates cache)
    python scripts/fetch_tournament_results_web.py --tournament "American Express" --years 2023 2024 2025

    # Then apply to player data
    python scripts/apply_historical_results.py --tournament "American Express" --data data/amex_2026_players_data.json
"""

import argparse
import json
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "data" / "tournament_results_cache"


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    # Remove accents/diacritics (basic)
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
        'ñ': 'n', 'ø': 'o', 'å': 'a', 'æ': 'ae',
    }
    name_lower = name.lower()
    for char, replacement in replacements.items():
        name_lower = name_lower.replace(char, replacement)
    return name_lower


def fuzzy_match_player(
    player_name: str,
    leaderboard: dict[str, str]
) -> Optional[str]:
    """
    Try to find a player in the leaderboard using fuzzy matching.

    Returns the result if found, None otherwise.
    """
    # Exact match
    if player_name in leaderboard:
        return leaderboard[player_name]

    # Normalized exact match
    player_norm = normalize_name(player_name)
    for name, result in leaderboard.items():
        if normalize_name(name) == player_norm:
            return result

    # Try matching on last name + first initial
    parts = player_name.split()
    if len(parts) >= 2:
        last_name = normalize_name(parts[-1])
        first_initial = normalize_name(parts[0])[0] if parts[0] else ""

        for name, result in leaderboard.items():
            name_parts = name.split()
            if len(name_parts) >= 2:
                lb_last = normalize_name(name_parts[-1])
                lb_first_initial = normalize_name(name_parts[0])[0] if name_parts[0] else ""

                if lb_last == last_name and lb_first_initial == first_initial:
                    return result

    # Try matching on last name only (be careful with common names)
    if len(parts) >= 1:
        last_name = normalize_name(parts[-1])
        matches = []
        for name, result in leaderboard.items():
            name_parts = name.split()
            if len(name_parts) >= 1:
                if normalize_name(name_parts[-1]) == last_name:
                    matches.append((name, result))

        # Only use if exactly one match
        if len(matches) == 1:
            return matches[0][1]

    return None


def load_cached_results(tournament_name: str, year: int) -> dict[str, str]:
    """Load tournament results from cache."""
    safe_name = re.sub(r'[^\w\s-]', '', tournament_name.lower())
    safe_name = re.sub(r'[\s]+', '_', safe_name)

    cache_file = CACHE_DIR / f"{safe_name}_{year}.json"

    if not cache_file.exists():
        return {}

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return data.get("results", {})
    except (json.JSONDecodeError, KeyError):
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Apply cached historical results to player data"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        required=True,
        help="Tournament name (must match cache files)"
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Player data JSON file to update"
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=[2023, 2024, 2025],
        help="Years to apply (default: 2023 2024 2025)"
    )
    parser.add_argument(
        "--field-prefix",
        type=str,
        default="history_",
        help="Prefix for history fields (default: history_)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without saving"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if not args.data.exists():
        print(f"❌ Player data file not found: {args.data}")
        return 1

    print(f"📊 Apply Historical Results")
    print(f"=" * 60)
    print(f"Tournament: {args.tournament}")
    print(f"Data file: {args.data}")
    print(f"Years: {', '.join(map(str, args.years))}")
    if args.dry_run:
        print(f"Mode: DRY RUN (no changes will be saved)")
    print()

    # Load all cached leaderboards
    leaderboards = {}
    for year in args.years:
        lb = load_cached_results(args.tournament, year)
        if lb:
            leaderboards[year] = lb
            print(f"✅ Loaded {year}: {len(lb)} players in cache")
        else:
            print(f"⚠️  No cache for {year} - run fetch_tournament_results_web.py first")

    if not leaderboards:
        print(f"\n❌ No cached results found. Run fetch first:")
        print(f"   python scripts/fetch_tournament_results_web.py --tournament \"{args.tournament}\" --years {' '.join(map(str, args.years))}")
        return 1

    # Load player data
    players_data = json.loads(args.data.read_text(encoding="utf-8"))

    # Determine where players are stored
    if "players" in players_data:
        players = players_data["players"]
    elif "odds" in players_data:
        # If using odds-based structure, we need to create/update players section
        if "players" not in players_data:
            players_data["players"] = {}
        players = players_data["players"]

        # Initialize player entries from odds if they don't exist
        for player_name in players_data["odds"]:
            if player_name not in players:
                players[player_name] = {}
    else:
        print(f"❌ Unrecognized data structure (no 'players' or 'odds' key)")
        return 1

    print(f"\n📋 Updating {len(players)} players...")
    print("-" * 60)

    stats = {
        "updated": 0,
        "confirmed": 0,
        "not_found": 0,
        "no_cache": 0
    }

    for player_name, player_info in sorted(players.items()):
        if args.verbose:
            print(f"\n{player_name}:")

        for year in args.years:
            field = f"{args.field_prefix}{year}"
            current = player_info.get(field, "NA")

            if year not in leaderboards:
                stats["no_cache"] += 1
                continue

            result = fuzzy_match_player(player_name, leaderboards[year])

            if result is None:
                # Player wasn't in the field
                new_value = "NA"
            else:
                new_value = result

            if current != new_value:
                if args.verbose:
                    print(f"  {year}: {current} → {new_value} ✏️")
                players[player_name][field] = new_value
                stats["updated"] += 1
            else:
                if args.verbose:
                    print(f"  {year}: {current} (confirmed)")
                stats["confirmed"] += 1

    # Update players back
    players_data["players"] = players

    print(f"\n📈 Summary")
    print("-" * 40)
    print(f"  Updated:   {stats['updated']}")
    print(f"  Confirmed: {stats['confirmed']}")
    print(f"  Not in field: {stats['not_found']}")

    if not args.dry_run:
        args.data.write_text(
            json.dumps(players_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n💾 Saved to {args.data}")
    else:
        print(f"\n⚠️  DRY RUN - no changes saved")

    print(f"\n✅ Complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
