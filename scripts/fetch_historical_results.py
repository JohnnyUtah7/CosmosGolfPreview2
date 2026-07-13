#!/usr/bin/env python3
"""
Fetch historical tournament results for players.

This script retrieves the last 3 finishes for each player at a specific
tournament/course using web search to find official leaderboard data.

RECOMMENDED WORKFLOW:
    # Step 1: Fetch full tournament leaderboards (one-time per tournament/year)
    python scripts/fetch_tournament_results_web.py --tournament "American Express" --years 2023 2024 2025

    # Step 2: Apply cached results to player data file
    python scripts/apply_historical_results.py --tournament "American Express" --data data/amex_2026_players_data.json

LEGACY USAGE (per-player lookup):
    python scripts/fetch_historical_results.py --tournament "Sony Open" --players "Scottie Scheffler"
"""
import sys
import json
import argparse
import os
import re
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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


def get_player_result_from_cache(
    player_name: str,
    tournament_name: str,
    year: int
) -> str:
    """Get a player's result from cached leaderboard data."""
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


def get_player_historical_finishes(
    player_name: str,
    tournament_name: str,
    years: int = 3
) -> dict[int, str]:
    """
    Get a player's finishes at a tournament for the last N years.

    First checks cache, then falls back to web search if needed.

    Args:
        player_name: Player's full name
        tournament_name: Tournament name to search for
        years: Number of years back to search (default 3)

    Returns:
        Dictionary mapping year -> finish position (e.g., {2025: "T5", 2024: "MC", 2023: "1"})
    """
    current_year = datetime.now().year
    results = {}

    # Check cache for each year
    cache_hits = 0
    for year in range(current_year - years, current_year):
        result = get_player_result_from_cache(player_name, tournament_name, year)
        if result != "-":
            cache_hits += 1
        results[year] = result

    if cache_hits == 0:
        print(f"⚠️  No cached data found for {tournament_name}")
        print(f"   Run this first to fetch leaderboards:")
        print(f"   python scripts/fetch_tournament_results_web.py --tournament \"{tournament_name}\" --years {' '.join(str(y) for y in range(current_year - years, current_year))}")

    return results


def format_finish_for_display(finish: str) -> dict:
    """
    Format a tournament finish for HTML display with appropriate styling.

    Args:
        finish: Finish position (e.g., "1", "T5", "MC", "CUT", "WD", "-")

    Returns:
        Dictionary with 'text' and 'class' for styling
    """
    finish_upper = finish.upper()

    # Win
    if finish in ["1", "W", "WIN"]:
        return {"text": "1", "class": "win"}

    # Top 5
    if finish.startswith("T") and finish[1:].isdigit():
        pos = int(finish[1:])
        if pos <= 5:
            return {"text": finish, "class": "top5"}
        elif pos <= 10:
            return {"text": finish, "class": "top10"}
        else:
            return {"text": finish, "class": ""}

    if finish.isdigit():
        pos = int(finish)
        if pos <= 5:
            return {"text": finish, "class": "top5"}
        elif pos <= 10:
            return {"text": finish, "class": "top10"}
        else:
            return {"text": finish, "class": ""}

    # Missed cut
    if finish_upper in ["MC", "CUT", "MDF"]:
        return {"text": "MC", "class": "missed-cut"}

    # Withdrew/DQ
    if finish_upper in ["WD", "DQ", "DNS"]:
        return {"text": finish_upper, "class": "missed-cut"}

    # No data
    if finish in ["-", "", "N/A"]:
        return {"text": "-", "class": ""}

    # Default
    return {"text": finish, "class": ""}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch historical tournament results for players",
        epilog="""
RECOMMENDED WORKFLOW:
  1. Fetch full leaderboards first (cached for reuse):
     python scripts/fetch_tournament_results_web.py --tournament "American Express" --years 2023 2024 2025

  2. Apply to player data:
     python scripts/apply_historical_results.py --tournament "American Express" --data data/amex_2026_players_data.json

This legacy script looks up individual players from cached leaderboard data.
        """
    )
    parser.add_argument(
        "--tournament",
        type=str,
        required=True,
        help="Tournament name (e.g., 'Sony Open', 'American Express')"
    )
    parser.add_argument(
        "--players",
        type=str,
        nargs="+",
        help="Specific players to fetch"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=3,
        help="Number of years back to search (default: 3)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path"
    )

    args = parser.parse_args()

    print("📊 Historical Results Fetcher")
    print("=" * 60)
    print(f"Tournament: {args.tournament}")
    print(f"Years back: {args.years}")
    print()

    if not args.players:
        print("⚠️  No players specified. Use --players option.")
        print("Example: --players 'Scottie Scheffler' 'Rory McIlroy'")
        print()
        print("💡 TIP: For bulk updates, use the recommended workflow:")
        print("   python scripts/fetch_tournament_results_web.py --tournament \"" + args.tournament + "\" --years 2023 2024 2025")
        print("   python scripts/apply_historical_results.py --tournament \"" + args.tournament + "\" --data data/your_players.json")
        return 1

    historical_data = {}

    for player_name in args.players:
        print(f"\n🏌️  Looking up {player_name}...")
        finishes = get_player_historical_finishes(
            player_name,
            args.tournament,
            args.years
        )
        historical_data[player_name] = finishes

        # Display results
        for year, finish in sorted(finishes.items(), reverse=True):
            status = "✅" if finish not in ["-", "NA", "MC"] else ("⚠️" if finish == "MC" else "❌")
            print(f"  {year}: {finish} {status}")

    # Save to file if specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(historical_data, f, indent=2)
        print(f"\n💾 Data saved to: {args.output}")

    print("\n✅ Historical results lookup complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
