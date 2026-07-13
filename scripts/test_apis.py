#!/usr/bin/env python3
"""
Quick test script to verify API connections and credentials.

Usage:
    python scripts/test_apis.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.odds import OddsAPIClient
from mcp_server.tools.pga import PGAAPIClient


def test_odds_api():
    """Test The Odds API connection."""
    print("🎲 Testing The Odds API...")
    try:
        with OddsAPIClient() as client:
            sports = client.get_golf_sports()
            print(f"✅ Connection successful!")
            print(f"   Found {len(sports)} golf events")
            if sports:
                for sport in sports[:3]:
                    print(f"   - {sport.get('title')}")
            return True
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ API error: {e}")
        return False


def test_pga_api():
    """Test BallDontLie PGA API connection."""
    print("\n🏌️  Testing BallDontLie PGA API...")
    try:
        with PGAAPIClient() as client:
            # Test getting tournaments
            from datetime import datetime
            current_year = datetime.now().year
            result = client.get_tournaments(season=current_year, per_page=3)
            tournaments = result.get("data", [])

            print(f"✅ Connection successful!")
            print(f"   Found {len(tournaments)} tournaments for {current_year}")
            if tournaments:
                for tournament in tournaments:
                    print(f"   - {tournament.get('name')}")
            return True
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ API error: {e}")
        return False


def main():
    """Run all API tests."""
    print("=" * 60)
    print("COSMOS Golf - API Connection Test")
    print("=" * 60)

    odds_ok = test_odds_api()
    pga_ok = test_pga_api()

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"The Odds API:       {'✅ PASS' if odds_ok else '❌ FAIL'}")
    print(f"BallDontLie PGA API: {'✅ PASS' if pga_ok else '❌ FAIL'}")

    if odds_ok and pga_ok:
        print("\n🎉 All tests passed! You're ready to generate previews.")
        print("\nNext step:")
        print("  python scripts/generate_preview.py --save-data")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check your .env file and API keys.")
        print("\nMake sure you have:")
        print("  1. Created a .env file in the project root")
        print("  2. Added valid API keys for both services")
        print("\nSee SETUP.md for detailed instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
