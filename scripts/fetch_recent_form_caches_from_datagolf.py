#!/usr/bin/env python3
"""
Fetch tournament result caches from Data Golf for recent-form events.

Uses the PGA schedule to find events that precede the current tournament,
then fetches each event's results from the Data Golf API and writes them
to data/tournament_results_cache/ so build_recent_form_from_cache.py
(and the weekly run) have up-to-date Pebble, Genesis, Cognizant, etc.

No more manual pulling—run this (or the weekly orchestrator) to automate.

Usage:
    python scripts/fetch_recent_form_caches_from_datagolf.py --tournament "Arnold Palmer Invitational" --year 2026
    python scripts/fetch_recent_form_caches_from_datagolf.py  # auto-detect current tournament from schedule
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCHEDULE_PATH = PROJECT_ROOT / "data" / "pga_schedule_2026.json"
DEFAULT_MAX_EVENTS = 13


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def load_schedule() -> dict:
    if not SCHEDULE_PATH.exists():
        return {"tournaments": [], "fall_schedule": []}
    return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))


def get_events_before_tournament(
    schedule: dict, current_tournament_name: str, year: int, max_events: int = DEFAULT_MAX_EVENTS
) -> list[tuple[str, str]]:
    """
    Return list of (event_display_name, event_full_name) for events before the current one.
    Most recent first. Uses full name for Data Golf fetch.
    """
    all_t = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])
    dated = []
    for t in all_t:
        start = (t.get("dates") or {}).get("start")
        if not start:
            continue
        try:
            d = datetime.strptime(start, "%Y-%m-%d").date()
            dated.append((t, d))
        except ValueError:
            continue
    dated.sort(key=lambda x: x[1])

    current_slug = _slugify(current_tournament_name)
    idx = None
    for i, (t, _) in enumerate(dated):
        if t.get("slug") == current_slug or _slugify(t.get("name", "")) == current_slug:
            idx = i
            break
        if current_tournament_name.lower() in (t.get("name") or "").lower():
            idx = i
            break
    if idx is None or idx == 0:
        return []

    before = dated[:idx]
    take = before[-max_events:] if len(before) >= max_events else before
    take.reverse()
    return [(t.get("name", ""), t.get("name", "")) for t, _ in take]


def get_this_weeks_tournament(schedule: dict):
    """Current week's tournament from schedule (same logic as orchestrator)."""
    from datetime import timedelta
    today = datetime.now().date()
    week_ahead = today + timedelta(days=7)
    all_t = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])
    candidates = []
    for t in all_t:
        dates = t.get("dates", {})
        start_str = dates.get("start", "")
        if not start_str:
            continue
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            if today <= start_date <= week_ahead:
                candidates.append((t, start_date))
            end_str = dates.get("end", start_str)
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            if start_date <= today <= end_date:
                candidates.append((t, start_date))
        except ValueError:
            continue
    if candidates:
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
    future = []
    for t in all_t:
        start_str = (t.get("dates") or {}).get("start", "")
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                if start_date > today:
                    future.append((t, start_date))
            except ValueError:
                pass
    if future:
        future.sort(key=lambda x: x[1])
        return future[0][0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch tournament result caches from Data Golf for recent-form events"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        default=None,
        help="Current tournament name (default: auto-detect from schedule)",
    )
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS)
    parser.add_argument("--dry-run", action="store_true", help="Print what would be fetched")
    args = parser.parse_args()

    if args.year is None:
        args.year = datetime.now().year

    schedule = load_schedule()
    if not schedule.get("tournaments") and not schedule.get("fall_schedule"):
        print("❌ No schedule found at", SCHEDULE_PATH)
        return 1

    if args.tournament:
        current_name = args.tournament
    else:
        t = get_this_weeks_tournament(schedule)
        if not t:
            print("❌ Could not determine current tournament from schedule")
            return 1
        current_name = t.get("name", "")

    events = get_events_before_tournament(
        schedule, current_name, args.year, max_events=args.max_events
    )
    if not events:
        print(f"No events before '{current_name}' in schedule (or tournament not found).")
        return 0

    print(f"Fetching tournament results from Data Golf for events before: {current_name}")
    print(f"Year: {args.year} | Events: {len(events)}")
    for name, _ in events:
        print(f"  • {name}")
    print()

    script = PROJECT_ROOT / "scripts" / "fetch_historical_from_datagolf.py"
    if not script.exists():
        print("❌ fetch_historical_from_datagolf.py not found")
        return 1

    failed = 0
    for event_name, _ in events:
        if args.dry_run:
            print(f"[DRY RUN] Would fetch: {event_name} ({args.year})")
            continue
        cmd = [
            sys.executable,
            str(script),
            "--tournament",
            event_name,
            "--years",
            str(args.year),
        ]
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            failed += 1
            print(f"  ⚠ Fetch failed for: {event_name}")
        else:
            print(f"  ✓ {event_name}")

    if failed and not args.dry_run:
        print(f"\n⚠ {failed} fetch(es) failed (event may not be completed or DG may not have data yet)")
    elif not args.dry_run:
        print("\n✅ Done. Run build_recent_form_from_cache.py to refresh recent form.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
