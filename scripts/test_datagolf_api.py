#!/usr/bin/env python3
"""Test script for the Data Golf API integration.

This script validates the Data Golf API connection and demonstrates
how to fetch various data types including:
- Player rankings and skill ratings
- Tournament field updates
- Pre-tournament predictions
- Betting odds with edge calculations
- Historical strokes-gained data

Usage:
    python scripts/test_datagolf_api.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Allow passing API key as argument for testing
if len(sys.argv) > 1:
    os.environ["DATAGOLF_API_KEY"] = sys.argv[1]

from mcp_server.tools.datagolf import DataGolfClient


def test_player_list():
    """Test fetching the master player list."""
    print("\n" + "=" * 60)
    print("TEST: Player List")
    print("=" * 60)

    with DataGolfClient() as dg:
        players = dg.get_player_list()
        print(f"Total players in database: {len(players)}")

        # Show some sample players
        print("\nSample players:")
        for p in players[:5]:
            print(f"  - {p.player_name} (ID: {p.dg_id}, Country: {p.country})")

        # Test player lookup
        scottie = dg.get_player_by_name("Scottie Scheffler")
        if scottie:
            print(f"\nLookup 'Scottie Scheffler': ID={scottie.dg_id}")


def test_rankings():
    """Test fetching Data Golf rankings."""
    print("\n" + "=" * 60)
    print("TEST: Data Golf Rankings")
    print("=" * 60)

    with DataGolfClient() as dg:
        rankings = dg.get_dg_rankings()
        print(f"Total ranked players: {len(rankings)}")

        print("\nTop 10 by Data Golf ranking:")
        for i, p in enumerate(rankings[:10], 1):
            print(
                f"  {i}. {p.player_name} "
                f"(DG Rank: {p.datagolf_rank}, OWGR: {p.owgr}, "
                f"Skill: {p.dg_skill_estimate:.2f})"
            )


def test_field_updates():
    """Test fetching current tournament field."""
    print("\n" + "=" * 60)
    print("TEST: Current Field Updates")
    print("=" * 60)

    with DataGolfClient() as dg:
        field = dg.get_field_updates(tour="pga")
        print(f"Current field size: {len(field)}")

        print("\nSample players with DFS salaries:")
        for p in field[:10]:
            dk = f"${p.dk_salary:,}" if p.dk_salary else "N/A"
            fd = f"${p.fd_salary:,}" if p.fd_salary else "N/A"
            print(f"  - {p.player_name}: DK {dk}, FD {fd}")


def test_predictions():
    """Test fetching pre-tournament predictions."""
    print("\n" + "=" * 60)
    print("TEST: Pre-Tournament Predictions")
    print("=" * 60)

    with DataGolfClient() as dg:
        result = dg.get_pre_tournament_predictions(tour="pga")
        print(f"Event: {result.get('event_name')}")
        print(f"Last Updated: {result.get('last_updated')}")

        predictions = result.get("predictions", [])
        print(f"Total predictions: {len(predictions)}")

        print("\nTop 10 by win probability:")
        sorted_preds = sorted(
            predictions, key=lambda x: x.win_prob or 0, reverse=True
        )
        for p in sorted_preds[:10]:
            win_pct = (p.win_prob or 0) * 100
            top5_pct = (p.top_5_prob or 0) * 100
            top10_pct = (p.top_10_prob or 0) * 100
            print(
                f"  {p.player_name}: "
                f"Win {win_pct:.1f}%, Top5 {top5_pct:.1f}%, Top10 {top10_pct:.1f}%"
            )


def test_skill_ratings():
    """Test fetching player strokes-gained ratings."""
    print("\n" + "=" * 60)
    print("TEST: Player Skill Ratings (Strokes Gained)")
    print("=" * 60)

    with DataGolfClient() as dg:
        skills = dg.get_player_skill_ratings(display="value")
        print(f"Total players with skill data: {len(skills)}")

        # Sort by total strokes gained
        sorted_skills = sorted(
            skills, key=lambda x: x.sg_total or 0, reverse=True
        )

        print("\nTop 10 by SG Total:")
        for p in sorted_skills[:10]:
            print(
                f"  {p.player_name}: "
                f"Total={p.sg_total:.2f}, OTT={p.sg_ott:.2f}, "
                f"APP={p.sg_app:.2f}, ARG={p.sg_arg:.2f}, PUTT={p.sg_putt:.2f}"
            )


def test_skill_decompositions():
    """Test fetching course-specific skill decompositions."""
    print("\n" + "=" * 60)
    print("TEST: Course-Specific Skill Decompositions")
    print("=" * 60)

    with DataGolfClient() as dg:
        decomp = dg.get_player_skill_decompositions(tour="pga")
        print(f"Event: {decomp.get('event_name')}")
        print(f"Course: {decomp.get('course_name')}")

        players = decomp.get("players", [])
        print(f"Total players: {len(players)}")

        print("\nTop 5 by course fit (final_pred - baseline_pred):")
        sorted_players = sorted(
            players,
            key=lambda x: (x.get("final_pred", 0) - x.get("baseline_pred", 0)),
        )[:5]
        for p in sorted_players:
            name = p.get("player_name", "Unknown")
            fit_adj = p.get("total_fit_adjustment", 0)
            history_adj = p.get("course_history_adjustment", 0)
            print(f"  {name}: Fit Adj={fit_adj:.3f}, History Adj={history_adj:.3f}")


def test_outright_odds():
    """Test fetching betting odds with Data Golf fair values."""
    print("\n" + "=" * 60)
    print("TEST: Outright Odds with Data Golf Fair Values")
    print("=" * 60)

    with DataGolfClient() as dg:
        result = dg.get_outright_odds(tour="pga", market="win")
        print(f"Event: {result.get('event_name')}")
        print(f"Market: {result.get('market')}")
        print(f"Books offering: {', '.join(result.get('books_offering', []))}")

        odds = result.get("odds", [])
        print(f"Total players with odds: {len(odds)}")

        print("\nTop 10 favorites (by DraftKings odds) with DG Fair Value:")
        sorted_odds = sorted(
            [o for o in odds if o.get("draftkings")],
            key=lambda x: int(str(x.get("draftkings", "9999")).replace("+", "")),
        )
        for o in sorted_odds[:10]:
            dk = o.get("draftkings", "N/A")
            dg_odds = o.get("datagolf", {})
            dg_fair = dg_odds.get("baseline_history_fit", "N/A")
            print(f"  {o.get('player_name')}: DK {dk}, DG Fair {dg_fair}")


def test_best_bets():
    """Test finding value bets."""
    print("\n" + "=" * 60)
    print("TEST: Best Bets (Positive Edge)")
    print("=" * 60)

    with DataGolfClient() as dg:
        bets = dg.get_best_bets(tour="pga", market="win", min_edge_pct=3.0)
        print(f"Bets with 3%+ edge: {len(bets)}")

        if bets:
            print("\nTop value plays:")
            for b in bets[:10]:
                print(
                    f"  {b['player_name']}: "
                    f"Edge {b['edge_pct']:.1f}%, "
                    f"DK {b['draftkings']}, DG Fair {b['dg_fair_odds']}"
                )
        else:
            print("No bets found with 3%+ edge (market may be efficient).")


def test_tour_schedule():
    """Test fetching tour schedule."""
    print("\n" + "=" * 60)
    print("TEST: Tour Schedule")
    print("=" * 60)

    with DataGolfClient() as dg:
        schedule = dg.get_tour_schedules(tour="pga", season=2026)
        print(f"Events in 2026 PGA Tour schedule: {len(schedule)}")

        print("\nUpcoming events:")
        for t in schedule[:10]:
            purse = f"${t.purse / 1e6:.1f}M" if t.purse else "TBD"
            print(f"  {t.start_date}: {t.event_name} ({purse})")


def main():
    """Run all Data Golf API tests."""
    print("=" * 60)
    print("DATA GOLF API INTEGRATION TEST")
    print("=" * 60)

    api_key = os.getenv("DATAGOLF_API_KEY")
    if not api_key:
        print("\nERROR: DATAGOLF_API_KEY not set!")
        print("Add to .env file: DATAGOLF_API_KEY=your_key_here")
        print("Or pass as argument: python test_datagolf_api.py YOUR_KEY")
        sys.exit(1)

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")

    try:
        test_player_list()
        test_rankings()
        test_field_updates()
        test_predictions()
        test_skill_ratings()
        test_skill_decompositions()
        test_outright_odds()
        test_best_bets()
        test_tour_schedule()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
