#!/usr/bin/env python3
"""
Fetch tournament odds from DraftKings with fallback to The Odds API.

This script searches for any PGA Tour tournament by name and fetches:
- Win odds
- Top 5 odds
- Top 10 odds

Priority order:
1. DraftKings direct API (has top5/top10 markets)
2. The Odds API (aggregates multiple books, may lack top5/top10)

Usage:
    python scripts/fetch_draftkings_odds.py --tournament "Farmers Insurance Open"
    python scripts/fetch_draftkings_odds.py --tournament "farmers" --year 2026
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from difflib import SequenceMatcher

import httpx

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.tools.odds import OddsAPIClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_minus(s: str) -> str:
    """Normalize unicode minus signs to ASCII."""
    return (s or "").replace("\u2212", "-").strip()


def _parse_american_odds(s: str) -> Optional[int]:
    """Parse American odds string to integer."""
    t = _normalize_minus(s).replace(",", "").strip()
    if not t:
        return None
    if t.startswith("+"):
        t = t[1:]
    if re.fullmatch(r"-?\d{2,7}", t):
        return int(t)
    return None


def _slugify(name: str) -> str:
    """Convert tournament name to slug for file naming."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


def _similarity(a: str, b: str) -> float:
    """Calculate string similarity ratio."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class DraftKingsClient:
    """Client for fetching odds directly from DraftKings API."""

    BASE_URL = "https://sportsbook-nash.draftkings.com/sites/{site}/api/sportscontent"

    def __init__(self, site: str = "US-SB", timeout: float = 30.0):
        self.site = site
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "CosmosGolfBetting/1.0"}
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def search_golf_tournaments(self) -> list[dict]:
        """Search for available golf tournaments on DraftKings."""
        # DraftKings categories API - golf is typically category 9
        url = f"https://sportsbook-nash.draftkings.com/sites/{self.site}/api/sportscontent/navigation/v1/leagues"
        params = {"sport": "golf"}

        try:
            resp = self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            leagues = []
            for league in data.get("leagues", []):
                leagues.append({
                    "id": league.get("id"),
                    "name": league.get("name"),
                    "slug": league.get("slug"),
                })
            return leagues
        except Exception as e:
            print(f"[DraftKings] Error searching tournaments: {e}")
            return []

    def find_tournament_by_name(self, name: str) -> Optional[dict]:
        """Find a tournament by name using fuzzy matching."""
        leagues = self.search_golf_tournaments()

        if not leagues:
            return None

        # Try exact match first
        name_lower = name.lower()
        for league in leagues:
            league_name = league.get("name", "").lower()
            if name_lower in league_name or league_name in name_lower:
                return league

        # Fuzzy match
        best_match = None
        best_score = 0.5  # Minimum threshold

        for league in leagues:
            league_name = league.get("name", "")
            score = _similarity(name, league_name)
            if score > best_score:
                best_score = score
                best_match = league

        return best_match

    def fetch_tournament_odds(
        self,
        league_id: str,
        subcategory_id: str = "4508"  # Default for outrights/top-finish
    ) -> dict[str, dict[str, Any]]:
        """
        Fetch win/top5/top10 odds for a tournament.

        Returns:
            dict mapping player names to {"win": int, "top5": int, "top10": int}
        """
        url = f"{self.BASE_URL.format(site=self.site)}/controldata/league/leagueSubcategory/v1/markets"
        params = {
            "isBatchable": "false",
            "templateVars": league_id,
            "eventsQuery": f"$filter=leagueId eq '{league_id}' AND clientMetadata/Subcategories/any(s: s/Id eq '{subcategory_id}')",
            "marketsQuery": f"$filter=clientMetadata/subCategoryId eq '{subcategory_id}' AND tags/all(t: t ne 'SportcastBetBuilder')",
            "include": "Events",
            "entity": "events",
        }

        try:
            resp = self.client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"[DraftKings] Error fetching odds: {e}")
            return {}

        return self._extract_odds_from_payload(payload)

    def _extract_odds_from_payload(self, payload: dict) -> dict[str, dict[str, Any]]:
        """Extract win/top5/top10 odds from DraftKings payload."""
        markets = payload.get("markets") if isinstance(payload.get("markets"), list) else []
        selections = payload.get("selections") if isinstance(payload.get("selections"), list) else []

        # Map marketId -> marketName
        market_name_by_id: dict[str, str] = {}
        for m in markets:
            mid = str(m.get("id") or "").strip()
            name = str(m.get("name") or "").strip()
            if mid and name:
                market_name_by_id[mid] = name

        # Identify markets
        winner_ids = {mid for mid, nm in market_name_by_id.items() if nm.lower() == "winner"}
        top5_ids = {mid for mid, nm in market_name_by_id.items() if "top 5" in nm.lower()}
        top10_ids = {mid for mid, nm in market_name_by_id.items() if "top 10" in nm.lower()}

        # Collect odds per player
        odds_by_player: dict[str, dict[str, int]] = {}

        for s in selections:
            mid = str(s.get("marketId") or "").strip()
            name = str(s.get("label") or "").strip()
            if not mid or not name:
                continue

            disp = s.get("displayOdds") if isinstance(s.get("displayOdds"), dict) else {}
            american = _normalize_minus(str(disp.get("american") or "")).strip()
            val = _parse_american_odds(american)
            if val is None:
                continue

            if mid in winner_ids:
                odds_by_player.setdefault(name, {})["win"] = val
            elif mid in top5_ids:
                odds_by_player.setdefault(name, {})["top5"] = val
            elif mid in top10_ids:
                odds_by_player.setdefault(name, {})["top10"] = val

        # Filter to players with win odds
        return {n: v for n, v in odds_by_player.items() if "win" in v}


def fetch_odds_from_draftkings(tournament_name: str) -> Optional[dict[str, dict[str, Any]]]:
    """
    Attempt to fetch odds from DraftKings directly.

    Returns:
        dict mapping player names to odds, or None if failed
    """
    print(f"[DraftKings] Searching for tournament: {tournament_name}")

    with DraftKingsClient() as client:
        tournament = client.find_tournament_by_name(tournament_name)

        if not tournament:
            print(f"[DraftKings] Tournament not found: {tournament_name}")
            return None

        print(f"[DraftKings] Found tournament: {tournament.get('name')} (ID: {tournament.get('id')})")

        league_id = str(tournament.get("id"))
        odds = client.fetch_tournament_odds(league_id)

        if odds:
            print(f"[DraftKings] Fetched odds for {len(odds)} players")
            return odds
        else:
            print("[DraftKings] No odds data available")
            return None


def fetch_odds_from_odds_api(tournament_name: str) -> Optional[dict[str, dict[str, Any]]]:
    """
    Fetch odds from The Odds API as fallback.

    Returns:
        dict mapping player names to odds (win only), or None if failed
    """
    print(f"[The Odds API] Searching for tournament: {tournament_name}")

    try:
        with OddsAPIClient() as client:
            sports = client.get_golf_sports()

            # Find matching tournament
            needle = tournament_name.lower()
            match = None
            best_score = 0.5

            for sport in sports:
                title = sport.get("title", "").lower()
                key = sport.get("key", "").lower()

                # Exact substring match
                if needle in title or needle in key:
                    match = sport
                    break

                # Fuzzy match
                score = max(_similarity(needle, title), _similarity(needle, key))
                if score > best_score:
                    best_score = score
                    match = sport

            if not match:
                print(f"[The Odds API] Tournament not found: {tournament_name}")
                return None

            sport_key = match.get("key")
            sport_title = match.get("title")
            print(f"[The Odds API] Found tournament: {sport_title} (key: {sport_key})")

            # Fetch odds
            tournament_odds = client.get_tournament_odds(sport_key, markets="outrights")

            if not tournament_odds:
                print("[The Odds API] No odds data available")
                return None

            # Aggregate best odds per player
            odds_by_player: dict[str, dict[str, Any]] = {}

            for player_name in tournament_odds.get_all_players():
                result = tournament_odds.get_player_best_odds(player_name)
                if result:
                    bookmaker, odds_val = result
                    odds_by_player[player_name] = {
                        "win": odds_val,
                        "bookmaker": bookmaker
                    }

            print(f"[The Odds API] Fetched odds for {len(odds_by_player)} players")
            return odds_by_player

    except Exception as e:
        print(f"[The Odds API] Error: {e}")
        return None


def fetch_tournament_odds(tournament_name: str) -> tuple[dict[str, dict[str, Any]], str]:
    """
    Fetch odds using DraftKings first, falling back to The Odds API.

    Returns:
        (odds_dict, source) where source is "DraftKings" or "The Odds API"
    """
    # Try DraftKings first
    odds = fetch_odds_from_draftkings(tournament_name)
    if odds:
        return odds, "DraftKings"

    # Fallback to The Odds API
    print("\n[Fallback] Trying The Odds API...")
    odds = fetch_odds_from_odds_api(tournament_name)
    if odds:
        return odds, "The Odds API"

    # No odds available
    return {}, "None"


def save_odds_data(
    tournament_name: str,
    odds: dict[str, dict[str, Any]],
    source: str,
    year: int,
    output_dir: Path
) -> tuple[Path, Path]:
    """
    Save odds data to JSON files.

    Creates:
    - {slug}_{year}_odds.json - Simple win odds mapping
    - {slug}_{year}_players_data.json - Full player data bundle
    """
    slug = _slugify(tournament_name)
    now = _now_iso()

    # Simple win odds file
    win_odds = {name: info.get("win", 0) for name, info in odds.items()}
    win_odds_sorted = dict(sorted(win_odds.items(), key=lambda kv: kv[1]))

    odds_file = output_dir / f"{slug}_{year}_odds.json"
    odds_file.write_text(json.dumps(win_odds_sorted, indent=2), encoding="utf-8")

    # Full players data bundle
    players_data = {
        "tournament": {"name": tournament_name},
        "odds": {},
        "players": {},
        "historical": {},
        "metadata": {
            "updated_at": now,
            "source": source,
            "player_count": len(odds),
        }
    }

    for name, info in odds.items():
        entry = {
            "bookmaker": info.get("bookmaker", source),
            "odds": info.get("win", 0),
            "imported_at": now,
        }
        if "top5" in info:
            entry["top5"] = info["top5"]
        if "top10" in info:
            entry["top10"] = info["top10"]

        players_data["odds"][name] = entry
        players_data["players"][name] = {}
        players_data["historical"][name] = {}

    players_file = output_dir / f"{slug}_{year}_players_data.json"
    players_file.write_text(json.dumps(players_data, indent=2), encoding="utf-8")

    return odds_file, players_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch tournament odds from DraftKings with The Odds API fallback"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        required=True,
        help="Tournament name to search for (e.g., 'Farmers Insurance Open')"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Tournament year for file naming (default: current year)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data",
        help="Output directory for JSON files"
    )
    parser.add_argument(
        "--draftkings-only",
        action="store_true",
        help="Only try DraftKings, skip The Odds API fallback"
    )
    parser.add_argument(
        "--odds-api-only",
        action="store_true",
        help="Only try The Odds API, skip DraftKings"
    )

    args = parser.parse_args()

    print(f"""
{'=' * 70}
 COSMOS Golf - Tournament Odds Fetcher
 Tournament: {args.tournament}
 Year: {args.year}
{'=' * 70}
""")

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch odds
    if args.draftkings_only:
        odds = fetch_odds_from_draftkings(args.tournament)
        source = "DraftKings" if odds else "None"
        odds = odds or {}
    elif args.odds_api_only:
        odds = fetch_odds_from_odds_api(args.tournament)
        source = "The Odds API" if odds else "None"
        odds = odds or {}
    else:
        odds, source = fetch_tournament_odds(args.tournament)

    if not odds:
        print(f"\n[ERROR] Could not fetch odds for '{args.tournament}'")
        print("Possible reasons:")
        print("  - Tournament not currently listed on sportsbooks")
        print("  - Tournament name mismatch (try variations)")
        print("  - API rate limits exceeded")
        return 1

    # Save data
    odds_file, players_file = save_odds_data(
        args.tournament,
        odds,
        source,
        args.year,
        args.output_dir
    )

    # Summary
    has_top5 = sum(1 for v in odds.values() if "top5" in v)
    has_top10 = sum(1 for v in odds.values() if "top10" in v)

    print(f"""
{'=' * 70}
 SUCCESS - Odds Data Retrieved
{'=' * 70}
 Source: {source}
 Players: {len(odds)}
 With Top 5 odds: {has_top5}
 With Top 10 odds: {has_top10}

 Files created:
 - {odds_file}
 - {players_file}
{'=' * 70}

Sample odds (top 5 favorites):
""")

    # Show top 5 favorites
    sorted_odds = sorted(odds.items(), key=lambda x: x[1].get("win", 99999))[:5]
    for name, info in sorted_odds:
        win = info.get("win", "N/A")
        top5 = info.get("top5", "N/A")
        top10 = info.get("top10", "N/A")
        print(f"  {name}: Win {win:+d} | Top5 {top5} | Top10 {top10}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
