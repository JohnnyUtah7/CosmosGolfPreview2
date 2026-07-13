#!/usr/bin/env python3
"""
Apply OWGR (Official World Golf Ranking) to any tournament's players_data.json.

Fetches live OWGR from Data Golf API (preds/get-dg-rankings endpoint).
Falls back to hardcoded ESPN top-100 if the API call fails.

Writes into both:
- data["owgr"] (name -> rank int) for tournament-specific assemblers
- data["players"][name]["owgr"] (str) for generic generate_tournament_html.py

Usage:
    python scripts/apply_owgr.py --tournament "WM Phoenix Open" --year 2026
    python scripts/apply_owgr.py --players-data data/wm_phoenix_open_2026_players_data.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Name aliases: field name -> canonical name used by Data Golf
NAME_ALIASES = {
    "John Keefer": "Johnny Keefer",
    "Daniel Brown": "Dan Brown",
    "Nico Echavarria": "Nicolas Echavarria",
    "Nicolas Echavarria": "Nico Echavarria",
    "Matti Schmid": "Matthias Schmid",
    "Matthias Schmid": "Matti Schmid",
}


def _dg_name_to_display(name: str) -> str:
    """Convert 'Last, First' (DG format) to 'First Last'."""
    if not name or "," not in name:
        return name.strip()
    parts = [p.strip() for p in name.split(",", 1)]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name.strip()


def _fetch_rankings_from_datagolf() -> tuple[dict[str, int], dict[str, int]]:
    """Fetch live OWGR and DG rankings from Data Golf API.

    Returns (owgr_map, dg_rank_map) - both are display_name -> rank.
    Uses OWGR as the primary ranking, with DG rank as supplemental.
    """
    try:
        from mcp_server.tools.datagolf import DataGolfClient
        client = DataGolfClient()
        rankings = client.get_dg_rankings()
        owgr_map = {}
        dg_map = {}
        for r in rankings:
            display_name = _dg_name_to_display(r.player_name)
            if r.owgr and r.owgr > 0:
                owgr_map[display_name] = r.owgr
            if r.datagolf_rank and r.datagolf_rank > 0:
                dg_map[display_name] = r.datagolf_rank
        return owgr_map, dg_map
    except Exception as e:
        print(f"⚠️  Data Golf API fetch failed: {e}")
        return {}, {}


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply OWGR to tournament players_data.json")
    parser.add_argument("--tournament", type=str, help="Tournament name (e.g. WM Phoenix Open)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--players-data", type=Path, help="Path to players_data.json (overrides --tournament/--year)")
    parser.add_argument("--slug", type=str, default=None, help="Explicit data-file slug (overrides slugified --tournament; matches the schedule slug)")
    args = parser.parse_args()

    if args.players_data is not None:
        path = Path(args.players_data)
        if not path.is_absolute():
            path = ROOT / path
    else:
        if not args.tournament:
            print("❌ Provide --tournament or --players-data")
            return 1
        slug = args.slug or _slugify(args.tournament)
        path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"

    if not path.exists():
        print(f"❌ Missing {path}")
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    odds_names = list(data.get("odds", {}).keys())
    if not odds_names:
        print("⚠️  No odds entries; nothing to update")
        return 0

    # Ensure "players" exists
    if "players" not in data:
        data["players"] = {}
    players = data["players"]

    # Fetch live rankings from Data Golf API
    print("🔄 Fetching live OWGR + DG rankings from Data Golf API...")
    owgr_ranks, dg_ranks = _fetch_rankings_from_datagolf()
    source = "Data Golf API (preds/get-dg-rankings)"

    if not owgr_ranks and not dg_ranks:
        print("⚠️  Data Golf API returned no data; no rankings applied")
        return 1

    print(f"   Fetched OWGR for {len(owgr_ranks)} players, DG rank for {len(dg_ranks)} players")

    # Build owgr: exact match on field name, then try aliases
    owgr_top = {}
    for name in odds_names:
        rank = owgr_ranks.get(name)
        if rank is None:
            alias = NAME_ALIASES.get(name)
            if alias:
                rank = owgr_ranks.get(alias)
        # Fall back to DG rank if no OWGR
        if rank is None:
            rank = dg_ranks.get(name)
            if rank is None:
                alias = NAME_ALIASES.get(name)
                if alias:
                    rank = dg_ranks.get(alias)
        if rank is not None:
            owgr_top[name] = rank
            if name not in players:
                players[name] = {}
            players[name]["owgr"] = str(rank)

    data["owgr"] = owgr_top
    data["players"] = players
    if "data_sources" not in data:
        data["data_sources"] = {}
    data["data_sources"]["owgr"] = source
    data["data_sources"]["owgr_applied_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    missing = len(odds_names) - len(owgr_top)
    print(f"✅ Applied OWGR to {len(owgr_top)} players")
    if missing:
        print(f"   Missing OWGR: {missing} players (not in top 100 / alias list)")
    print(f"💾 Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
