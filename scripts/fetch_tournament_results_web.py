#!/usr/bin/env python3
"""
Fetch historical tournament results using web search - SIMPLE VERSION.

Searches Google for tournament leaderboards and extracts results.
Designed to work with Claude Code's WebSearch/WebFetch capabilities.

Usage:
    # From Claude Code, just ask to fetch results for a tournament:
    # "Fetch American Express 2025 results and save to cache"

    # Or run manually to look up cached results:
    python3 scripts/fetch_tournament_results_web.py --tournament "American Express" --year 2025
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "data" / "tournament_results_cache"


def load_cached_leaderboard(tournament_name: str, year: int) -> dict[str, str]:
    """Load tournament results from cache if available."""
    safe_name = re.sub(r'[^\w\s-]', '', tournament_name.lower())
    safe_name = re.sub(r'[\s]+', '_', safe_name)

    cache_file = CACHE_DIR / f"{safe_name}_{year}.json"

    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return data.get("results", {})
        except (json.JSONDecodeError, KeyError):
            return {}
    return {}


def save_to_cache(tournament_name: str, year: int, results: dict[str, str], source: str = "web_search") -> Path:
    """Save leaderboard to cache file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r'[^\w\s-]', '', tournament_name.lower())
    safe_name = re.sub(r'[\s]+', '_', safe_name)

    cache_file = CACHE_DIR / f"{safe_name}_{year}.json"

    data = {
        "tournament": tournament_name,
        "year": year,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "results": results
    }

    cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return cache_file


def get_player_result(
    player_name: str,
    tournament_name: str,
    year: int
) -> str:
    """Look up a player's result from cached leaderboard."""
    leaderboard = load_cached_leaderboard(tournament_name, year)

    if not leaderboard:
        return "-"

    # Exact match
    if player_name in leaderboard:
        return leaderboard[player_name]

    # Case-insensitive match
    player_lower = player_name.lower()
    for name, result in leaderboard.items():
        if name.lower() == player_lower:
            return result

    # Last name + first initial match
    parts = player_name.split()
    if len(parts) >= 2:
        last_name = parts[-1].lower()
        first_initial = parts[0][0].lower() if parts[0] else ""

        for name, result in leaderboard.items():
            name_parts = name.split()
            if len(name_parts) >= 2:
                if name_parts[-1].lower() == last_name:
                    if name_parts[0][0].lower() == first_initial:
                        return result

    return "NA"  # Player wasn't in the field


def main():
    parser = argparse.ArgumentParser(
        description="Look up tournament results from cache",
        epilog="""
HOW TO POPULATE CACHE:
  Ask Claude Code to search Google and fetch results, e.g.:
  "Search for American Express 2025 golf leaderboard and save all player results to cache"

  Claude will use WebSearch/WebFetch to get the data and save it.

THEN USE THIS SCRIPT:
  python3 scripts/fetch_tournament_results_web.py --tournament "American Express" --year 2025 --players "Sepp Straka"
        """
    )
    parser.add_argument(
        "--tournament",
        type=str,
        required=True,
        help="Tournament name (e.g., 'American Express')"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Year to look up"
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        help="Multiple years to look up"
    )
    parser.add_argument(
        "--players",
        type=str,
        nargs="+",
        help="Specific players to look up"
    )
    parser.add_argument(
        "--show-cache",
        action="store_true",
        help="Show what's in the cache"
    )

    args = parser.parse_args()

    # Determine years
    years = []
    if args.year:
        years = [args.year]
    elif args.years:
        years = args.years
    else:
        years = [2023, 2024, 2025]

    print(f"🏌️ Tournament Results Lookup")
    print(f"=" * 50)
    print(f"Tournament: {args.tournament}")
    print(f"Years: {', '.join(map(str, years))}")
    print()

    # Check cache status
    for year in years:
        cached = load_cached_leaderboard(args.tournament, year)
        if cached:
            print(f"✅ {year}: {len(cached)} players in cache")
            if args.show_cache:
                print(f"   Sample: {list(cached.items())[:5]}")
        else:
            print(f"❌ {year}: No cache - ask Claude to fetch it!")

    # Look up specific players if requested
    if args.players:
        print(f"\n📋 Player Results")
        print("-" * 40)

        for player in args.players:
            print(f"\n{player}:")
            for year in sorted(years, reverse=True):
                result = get_player_result(player, args.tournament, year)
                status = "✅" if result not in ["-", "NA", "MC"] else ("⚠️" if result == "MC" else "❌")
                print(f"  {year}: {result} {status}")

    print(f"\n✅ Done!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
