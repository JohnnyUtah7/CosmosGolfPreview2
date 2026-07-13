#!/usr/bin/env python3
"""
Build recent form strings from Data Golf historical event finishes.

Fetches get_event_finishes(tour='pga', year=2025) and year=2026, groups by
player, and formats the last N events as "Event (Season): Pos • ...".
Updates the master recent-form cache and writes tournament-specific
recent_form JSON so the weekly tournament (e.g. WM Phoenix) is populated.

Usage:
    python scripts/refresh_recent_form_from_datagolf.py --tournament "WM Phoenix Open" --year 2026
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.tools.datagolf import DataGolfClient

MASTER_CACHE = PROJECT_ROOT / "data" / "player_recent_form_cache.json"
DEFAULT_MAX_EVENTS = 4


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _dg_name_to_display(name: str) -> str:
    """Convert 'Last, First' (DG format) to 'First Last'."""
    if not name or "," not in name:
        return name.strip()
    parts = [p.strip() for p in name.split(",", 1)]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name.strip()


def _format_finish(pos: str | int | None) -> str:
    if pos is None:
        return "—"
    s = str(pos).strip().upper()
    if s in ("MC", "CUT", "MDF", "WD", "DQ", "DNS"):
        return s
    return str(pos)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build recent form from Data Golf event finishes")
    parser.add_argument("--tournament", type=str, default="WM Phoenix Open", help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS, help="Max events per player")
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    players_data_path = PROJECT_ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    output_path = PROJECT_ROOT / "data" / f"{slug}_{args.year}_recent_form.json"

    # Get player list from tournament so we only output form for field
    tournament_players = set()
    if players_data_path.exists():
        data = json.loads(players_data_path.read_text(encoding="utf-8"))
        tournament_players = set(data.get("odds", {}).keys())

    try:
        with DataGolfClient() as dg:
            try:
                finishes_2026 = dg.get_event_finishes(tour="pga", year=2026)
            except Exception:
                finishes_2026 = []
            try:
                finishes_2025 = dg.get_event_finishes(tour="pga", year=2025)
            except Exception:
                finishes_2025 = []
    except Exception as e:
        print(f"⚠️ Data Golf historical finishes not available: {e}")
        finishes_2026, finishes_2025 = [], []

    # Group by player (display name). DG returns "Last, First"
    by_player: dict[str, list[tuple[str, str, int]]] = {}  # display_name -> [(event_name, finish_str, year), ...]

    for res in finishes_2026:
        name = _dg_name_to_display(res.player_name or "")
        if not name:
            continue
        pos = _format_finish(res.finish_position)
        event = (res.event_name or "Event").strip()
        if name not in by_player:
            by_player[name] = []
        by_player[name].append((event, pos, 2026))

    for res in finishes_2025:
        name = _dg_name_to_display(res.player_name or "")
        if not name:
            continue
        pos = _format_finish(res.finish_position)
        event = (res.event_name or "Event").strip()
        if name not in by_player:
            by_player[name] = []
        by_player[name].append((event, pos, 2025))

    # Build form string: last N events (2026 first, then 2025; order within season is API order)
    def sort_key(item: tuple[str, str, int]) -> tuple[int, str]:
        year, event_name = item[2], item[0]
        return (-year, event_name)

    recent_form_all: dict[str, str] = {}
    for player, events in by_player.items():
        events_sorted = sorted(events, key=sort_key)
        parts = []
        for event_name, finish, year in events_sorted[: args.max_events]:
            parts.append(f"{event_name} ({year}): {finish}")
        recent_form_all[player] = " • ".join(parts) if parts else "—"

    # If DG returned no historical data, use existing master cache so we don't wipe form
    if not recent_form_all and MASTER_CACHE.exists():
        recent_form_all = json.loads(MASTER_CACHE.read_text(encoding="utf-8"))
        print("   (Using existing cache; Data Golf historical finishes unavailable)")

    # Update master cache
    master = {}
    if MASTER_CACHE.exists():
        master = json.loads(MASTER_CACHE.read_text(encoding="utf-8"))
    for player, form in recent_form_all.items():
        if form and form != "—":
            master[player] = form
    MASTER_CACHE.parent.mkdir(parents=True, exist_ok=True)
    MASTER_CACHE.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")

    # Tournament-specific: only players in field, fallback to "—"
    tournament_form = {}
    if tournament_players:
        for p in tournament_players:
            tournament_form[p] = recent_form_all.get(p, "—")
    else:
        tournament_form = recent_form_all

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tournament_form, indent=2, ensure_ascii=False), encoding="utf-8")

    with_data = sum(1 for v in tournament_form.values() if v and v != "—")
    print(f"✅ Recent form from Data Golf: {len(tournament_form)} players ({with_data} with data)")
    print(f"   Master cache: {MASTER_CACHE}")
    print(f"   Tournament:   {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
