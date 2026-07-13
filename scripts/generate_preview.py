#!/usr/bin/env python3
"""
Generate weekly PGA tournament betting preview.

This script fetches the next upcoming PGA tournament, retrieves betting odds
from multiple sportsbooks via The Odds API, gets tournament/player data from
BallDontLie PGA API, and generates an HTML preview page.

Usage:
    python scripts/generate_preview.py [--output-dir OUTPUT_DIR]
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.odds import OddsAPIClient
from mcp_server.tools.pga import PGAAPIClient


def main():
    """Main entry point for generating tournament preview."""
    parser = argparse.ArgumentParser(
        description="Generate PGA tournament betting preview"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to save generated HTML (default: current directory)"
    )
    parser.add_argument(
        "--save-data",
        action="store_true",
        help="Save raw JSON data to file"
    )
    args = parser.parse_args()

    print("🏌️  COSMOS Golf Betting Preview Generator")
    print("=" * 60)

    # Initialize API clients
    print("\n📡 Connecting to APIs...")
    try:
        odds_client = OddsAPIClient()
        pga_client = PGAAPIClient()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have a .env file with:")
        print("  ODDS_API_KEY=your_key_here")
        print("  BALLDONTLIE_API_KEY=your_key_here")
        return 1

    try:
        # Step 1: Find next PGA tournament from BallDontLie
        print("\n🔍 Finding next PGA tournament...")
        current_year = datetime.now().year
        next_tournament = pga_client.get_next_tournament(season=current_year)

        if not next_tournament:
            print(f"❌ No upcoming tournaments found for {current_year} season")
            return 1

        tournament_name = next_tournament.get("name", "Unknown Tournament")
        print(f"✅ Found: {tournament_name}")
        print(f"   Tournament ID: {next_tournament.get('id')}")

        # Step 2: Get available golf sports from The Odds API
        print("\n🎲 Fetching betting odds...")
        golf_sports = odds_client.get_golf_sports()

        if not golf_sports:
            print("❌ No golf tournaments available in The Odds API")
            return 1

        print(f"✅ Found {len(golf_sports)} golf events with odds:")
        for sport in golf_sports:
            print(f"   - {sport.get('title')} ({sport.get('key')})")

        # Step 3: Try to match tournament and get odds
        # For now, just use the first available golf event
        # TODO: Implement smart matching between BallDontLie and The Odds API
        sport_key = golf_sports[0].get("key")
        sport_title = golf_sports[0].get("title")

        print(f"\n📊 Fetching odds for: {sport_title}")
        tournament_odds = odds_client.get_tournament_odds(sport_key)

        if not tournament_odds:
            print(f"❌ No odds available for {sport_title}")
            return 1

        # Step 4: Aggregate best odds across all sportsbooks
        print("\n💰 Aggregating best odds across sportsbooks...")
        best_odds = {}
        all_players = tournament_odds.get_all_players()

        print(f"✅ Found odds for {len(all_players)} players")
        print(f"   Sportsbooks: {len(tournament_odds.bookmakers)}")

        for bookmaker in tournament_odds.bookmakers:
            print(f"   - {bookmaker.bookmaker_name}: {len(bookmaker.players)} players")

        for player_name in all_players:
            result = tournament_odds.get_player_best_odds(player_name)
            if result:
                best_odds[player_name] = {
                    "bookmaker": result[0],
                    "odds": result[1]
                }

        # Step 5: Get player data from BallDontLie
        print("\n👥 Fetching player information...")
        players_data = {}

        # Get a sample of players (limit API calls for free tier)
        sample_players = list(all_players)[:10]  # Limit to 10 for free tier

        for player_name in sample_players:
            player_info = pga_client.get_player_by_name(player_name)
            if player_info:
                players_data[player_name] = player_info
                country = player_info.get("country", "N/A")
                print(f"   ✓ {player_name} ({country})")

        # Step 6: Prepare data summary
        print("\n" + "=" * 60)
        print("📋 PREVIEW DATA SUMMARY")
        print("=" * 60)
        print(f"Tournament: {sport_title}")
        print(f"Start Date: {tournament_odds.commence_time}")
        print(f"Total Players with Odds: {len(all_players)}")
        print(f"Sportsbooks: {len(tournament_odds.bookmakers)}")
        print(f"Player Details Fetched: {len(players_data)}")

        # Step 7: Display top 10 favorites
        print("\n🏆 TOP 10 FAVORITES:")
        sorted_players = sorted(
            best_odds.items(),
            key=lambda x: x[1]["odds"]
        )[:10]

        for idx, (player, odds_info) in enumerate(sorted_players, 1):
            odds_str = f"+{odds_info['odds']}" if odds_info['odds'] > 0 else str(odds_info['odds'])
            country = players_data.get(player, {}).get("country", "")
            country_str = f" ({country})" if country else ""
            print(f"{idx:2d}. {player:25s} {odds_str:>6s}  [{odds_info['bookmaker']}]{country_str}")

        # Step 8: Save data if requested
        if args.save_data:
            output_data = {
                "generated_at": datetime.now().isoformat(),
                "tournament": {
                    "name": sport_title,
                    "sport_key": sport_key,
                    "commence_time": tournament_odds.commence_time.isoformat() if tournament_odds.commence_time else None,
                },
                "odds": {
                    player: {
                        "bookmaker": info["bookmaker"],
                        "odds": info["odds"]
                    }
                    for player, info in best_odds.items()
                },
                "players": players_data,
                "sportsbooks": [
                    {
                        "key": bm.bookmaker_key,
                        "name": bm.bookmaker_name,
                        "player_count": len(bm.players)
                    }
                    for bm in tournament_odds.bookmakers
                ]
            }

            output_file = args.output_dir / f"preview_data_{datetime.now().strftime('%Y%m%d')}.json"
            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)

            print(f"\n💾 Data saved to: {output_file}")

        # Step 9: Generate HTML (TODO in next phase)
        print("\n⚠️  HTML generation coming next!")
        print("   For now, use the JSON data to manually create your preview.")

        print("\n✅ Preview generation complete!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Clean up clients
        odds_client.close()
        pga_client.close()


if __name__ == "__main__":
    sys.exit(main())
