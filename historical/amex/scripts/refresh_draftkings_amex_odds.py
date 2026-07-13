#!/usr/bin/env python3
"""
Refresh AMEX 2026 odds directly from DraftKings (public markets endpoint).

This uses the same backend endpoint the page at:
  `https://sportsbook.draftkings.com/leagues/golf/the-american-express`
calls to render Winner / Top 5 / Top 10 markets.

Outputs:
- `data/american_express_2026_odds.json` (player -> win odds int)
- Updates `data/amex_2026_players_data.json` (odds section: win/top5/top10)
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).parent.parent


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_minus(s: str) -> str:
    return (s or "").replace("−", "-").strip()


def _parse_american_odds(s: str) -> int | None:
    t = _normalize_minus(s).replace(",", "").strip()
    if not t:
        return None
    if t.startswith("+"):
        t = t[1:]
    if re.fullmatch(r"-?\d{2,7}", t):
        return int(t)
    return None


def fetch_amex_markets(*, league_id: str, subcategory_id: str, site: str, timeout_seconds: float = 30.0) -> dict[str, Any]:
    """
    Fetch markets payload from DraftKings.

    This endpoint is not officially documented; it mirrors what the webpage calls.
    """
    url = f"https://sportsbook-nash.draftkings.com/sites/{site}/api/sportscontent/controldata/league/leagueSubcategory/v1/markets"
    params = {
        "isBatchable": "false",
        "templateVars": league_id,
        "eventsQuery": f"$filter=leagueId eq '{league_id}' AND clientMetadata/Subcategories/any(s: s/Id eq '{subcategory_id}')",
        "marketsQuery": f"$filter=clientMetadata/subCategoryId eq '{subcategory_id}' AND tags/all(t: t ne 'SportcastBetBuilder')",
        "include": "Events",
        "entity": "events",
    }
    with httpx.Client(timeout=timeout_seconds, headers={"User-Agent": "CosmosGolfBetting/1.0"}) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def extract_win_top5_top10(payload: dict[str, Any]) -> tuple[dict[str, dict[str, int]], list[str]]:
    """
    Returns:
      odds_by_player: {name: {"win": int, "top5": int, "top10": int}}
      warnings: list[str]
    """
    warnings: list[str] = []

    markets = payload.get("markets") if isinstance(payload.get("markets"), list) else []
    selections = payload.get("selections") if isinstance(payload.get("selections"), list) else []

    # Map marketId -> marketName
    market_name_by_id: dict[str, str] = {}
    for m in markets:
        mid = str(m.get("id") or "").strip()
        name = str(m.get("name") or "").strip()
        if mid and name:
            market_name_by_id[mid] = name

    # Identify the 3 markets we care about by their names (stable on the page)
    winner_ids = {mid for mid, nm in market_name_by_id.items() if nm.lower() == "winner"}
    top5_ids = {mid for mid, nm in market_name_by_id.items() if "top 5" in nm.lower()}
    top10_ids = {mid for mid, nm in market_name_by_id.items() if "top 10" in nm.lower()}

    if not winner_ids:
        warnings.append("Could not find Winner market in payload.")
    if not top5_ids:
        warnings.append("Could not find Top 5 market in payload.")
    if not top10_ids:
        warnings.append("Could not find Top 10 market in payload.")

    # Collect odds per player per market
    odds_by_player: dict[str, dict[str, int]] = {}

    def _set(name: str, key: str, val: int) -> None:
        odds_by_player.setdefault(name, {})[key] = val

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
            _set(name, "win", val)
        elif mid in top5_ids:
            _set(name, "top5", val)
        elif mid in top10_ids:
            _set(name, "top10", val)

    # Keep only players with win odds (roster source-of-truth)
    odds_by_player = {n: v for n, v in odds_by_player.items() if "win" in v}

    # Warn if missing placement markets for some players
    missing5 = [n for n, v in odds_by_player.items() if "top5" not in v]
    missing10 = [n for n, v in odds_by_player.items() if "top10" not in v]
    if missing5:
        warnings.append(f"Missing Top 5 odds for {len(missing5)} players (showing first 10): {missing5[:10]}")
    if missing10:
        warnings.append(f"Missing Top 10 odds for {len(missing10)} players (showing first 10): {missing10[:10]}")

    return odds_by_player, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh AMEX odds from DraftKings markets endpoint")
    parser.add_argument("--site", type=str, default="US-SB", help="DraftKings site code")
    parser.add_argument("--league-id", type=str, default="87527", help="DraftKings leagueId for AMEX page")
    parser.add_argument("--subcategory-id", type=str, default="4508", help="DraftKings subCategoryId for outrights/top-finish")
    parser.add_argument(
        "--win-odds-json",
        type=Path,
        default=PROJECT_ROOT / "data" / "american_express_2026_odds.json",
        help="Output win odds mapping (player -> int)",
    )
    parser.add_argument(
        "--players-data",
        type=Path,
        default=PROJECT_ROOT / "data" / "amex_2026_players_data.json",
        help="Players-data JSON to update (odds section)",
    )
    args = parser.parse_args()

    payload = fetch_amex_markets(league_id=args.league_id, subcategory_id=args.subcategory_id, site=args.site)
    odds_by_player, warnings = extract_win_top5_top10(payload)

    # Write win odds mapping
    win_map = {name: info["win"] for name, info in odds_by_player.items()}
    win_sorted = dict(sorted(win_map.items(), key=lambda kv: kv[1]))
    args.win_odds_json.parent.mkdir(parents=True, exist_ok=True)
    args.win_odds_json.write_text(json.dumps(win_sorted, indent=2), encoding="utf-8")

    # Merge into players-data
    bundle: dict[str, Any] = {}
    if args.players_data.exists():
        try:
            bundle = json.loads(args.players_data.read_text(encoding="utf-8"))
        except Exception:
            bundle = {}
    if not isinstance(bundle, dict):
        bundle = {}
    bundle.setdefault("tournament", {"name": "The American Express"})
    bundle.setdefault("players", {})
    bundle.setdefault("historical", {})
    bundle.setdefault("odds", {})

    now = _now_iso()
    for name, info in odds_by_player.items():
        entry: dict[str, Any] = {
            "bookmaker": "DraftKings",
            "odds": int(info["win"]),
            "imported_at": now,
            "source_url": "https://sportsbook.draftkings.com/leagues/golf/the-american-express",
        }
        if "top5" in info:
            entry["top5"] = int(info["top5"])
        if "top10" in info:
            entry["top10"] = int(info["top10"])
        bundle["odds"][name] = entry
        bundle["players"].setdefault(name, {})
        bundle["historical"].setdefault(name, {})

    bundle["metadata"] = {
        "updated_at": now,
        "source": "DraftKings markets endpoint",
        "player_count": len(bundle.get("odds", {})),
    }
    args.players_data.parent.mkdir(parents=True, exist_ok=True)
    args.players_data.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    print(f"✅ DraftKings refresh complete: {len(odds_by_player)} players")
    print(f"✅ Updated {args.win_odds_json}")
    print(f"✅ Updated {args.players_data}")
    if warnings:
        print("\nWarnings:")
        for w in warnings[:20]:
            print(f"- {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

