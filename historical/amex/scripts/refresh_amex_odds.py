#!/usr/bin/env python3
"""
Refresh The American Express odds snapshot from The Odds API.

Writes:
- `data/american_express_2026_odds.json` (flat mapping: player -> win odds int)
- Optionally updates `data/amex_2026_players_data.json` (odds block only)

This is the missing piece when you’re stuck on a 32-player curated list:
once ODDS_API_KEY is set, you can pull *all* available outrights and the
HTML generator will render every player it sees odds for.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent


def _find_sport_key(sports: list[dict[str, Any]], tournament_substring: str) -> dict[str, str] | None:
    needle = (tournament_substring or "").strip().lower()
    if not needle:
        return None
    for s in sports:
        title = str(s.get("title") or "").lower()
        key = str(s.get("key") or "").lower()
        if needle in title or needle in key:
            return {"key": str(s.get("key") or ""), "title": str(s.get("title") or "")}
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh AMEX odds snapshot from The Odds API")
    parser.add_argument("--tournament", type=str, default="The American Express", help="Tournament substring to match")
    parser.add_argument("--sport-key", type=str, default=None, help="Explicit sport key (skips auto-detect)")
    parser.add_argument(
        "--output-odds",
        type=Path,
        default=PROJECT_ROOT / "data" / "american_express_2026_odds.json",
        help="Output odds JSON path (player -> odds int)",
    )
    parser.add_argument(
        "--update-players-data",
        type=Path,
        default=PROJECT_ROOT / "data" / "amex_2026_players_data.json",
        help="Players-data JSON to update (odds section only). Use /dev/null to skip.",
    )
    args = parser.parse_args()

    # Local import so this script can run standalone.
    from mcp_server.tools.odds import OddsAPIClient  # noqa: WPS433

    with OddsAPIClient() as client:
        sports = client.get_golf_sports()
        if not sports:
            raise SystemExit("No golf sports returned by The Odds API.")

        chosen = None
        if args.sport_key:
            chosen = {"key": args.sport_key, "title": args.sport_key}
        else:
            chosen = _find_sport_key(sports, args.tournament)

        if not chosen or not chosen.get("key"):
            raise SystemExit(f"Could not find a sport key matching: {args.tournament!r}")

        sport_key = chosen["key"]
        sport_title = chosen.get("title") or sport_key
        print(f"Fetching odds for: {sport_title} ({sport_key})")

        tournament_odds = client.get_tournament_odds(sport_key, markets="outrights", odds_format="american")
        if not tournament_odds:
            raise SystemExit("No odds returned for this sport key.")

        odds_map: dict[str, int] = {}
        best_book_map: dict[str, str] = {}

        for player_name in tournament_odds.get_all_players():
            best = tournament_odds.get_player_best_odds(player_name)
            if not best:
                continue
            book, odds_val = best
            if isinstance(odds_val, bool):
                continue
            try:
                odds_map[str(player_name)] = int(odds_val)
                best_book_map[str(player_name)] = str(book)
            except Exception:
                continue

    # Write flat mapping (sorted favorites first)
    odds_map_sorted = dict(sorted(odds_map.items(), key=lambda kv: kv[1]))
    args.output_odds.parent.mkdir(parents=True, exist_ok=True)
    args.output_odds.write_text(json.dumps(odds_map_sorted, indent=2), encoding="utf-8")
    print(f"Wrote odds snapshot: {args.output_odds} ({len(odds_map_sorted)} players)")

    # Optionally update players-data (odds block only)
    if str(args.update_players_data) != "/dev/null":
        try:
            pd_path = Path(args.update_players_data)
            data: dict[str, Any] = {}
            if pd_path.exists():
                data = json.loads(pd_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}

            data.setdefault("tournament", {"name": "The American Express"})
            data.setdefault("players", {})
            data.setdefault("historical", {})
            odds_block: dict[str, Any] = {}
            for name, odds_val in odds_map_sorted.items():
                odds_block[name] = {
                    "bookmaker": best_book_map.get(name, "Best available"),
                    "odds": int(odds_val),
                }
                data["players"].setdefault(name, {})
                data["historical"].setdefault(name, {})
            data["odds"] = odds_block

            pd_path.parent.mkdir(parents=True, exist_ok=True)
            pd_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Updated players-data odds: {pd_path} ({len(odds_block)} players)")
        except Exception as e:
            print(f"⚠️  Could not update players-data file: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

