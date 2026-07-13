#!/usr/bin/env python3
"""
Fetch historical tournament results from Data Golf API and write to tournament_results_cache.

Uses the historical-raw-data/rounds endpoint which returns per-player finish positions.
This automates what was previously done by manual PDF transcription.

Usage:
    python scripts/fetch_historical_from_datagolf.py --tournament "AT&T Pebble Beach Pro-Am" --years 2023 2024 2025
    python scripts/fetch_historical_from_datagolf.py --event-id 5 --years 2023 2024 2025
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.tools.datagolf import DataGolfClient

CACHE_DIR = PROJECT_ROOT / "data" / "tournament_results_cache"


def _safe_name(tournament_name: str) -> str:
    """Match the safe_name logic in apply_historical_results.py."""
    safe = re.sub(r'[^\w\s-]', '', tournament_name.lower())
    safe = re.sub(r'[\s]+', '_', safe)
    return safe


def _dg_name_to_display(name: str) -> str:
    """Convert 'Last, First' (DG format) to 'First Last'."""
    if not name or "," not in name:
        return name.strip()
    parts = [p.strip() for p in name.split(",", 1)]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name.strip()


def find_event_id(dg: DataGolfClient, tournament_name: str) -> str | None:
    """Find Data Golf event_id for a tournament name."""
    events = dg.get_historical_raw_event_ids(tour="pga")
    name_lower = tournament_name.lower()
    # Exact substring match (either direction)
    for e in events:
        ename = (e.get("event_name") or "").lower()
        if name_lower in ename or ename in name_lower:
            return str(e.get("event_id"))
    # Partial match: require ALL significant keywords to match
    keywords = [kw for kw in name_lower.split() if len(kw) >= 4]
    if keywords:
        for e in events:
            ename = (e.get("event_name") or "").lower()
            if all(kw in ename for kw in keywords):
                return str(e.get("event_id"))
    return None


def _normalize_finish(fin_str: str) -> str:
    """Normalize finish text: Cut -> MC, W/D -> WD, etc."""
    fin_str = str(fin_str).strip()
    lower = fin_str.lower()
    if lower in ("cut", "mc", "mdf"):
        return "MC"
    if lower in ("w/d", "wd"):
        return "WD"
    if lower == "dq":
        return "DQ"
    return fin_str


def fetch_results_for_year(dg: DataGolfClient, event_id: str, year: int, tournament_name: str = "") -> dict[str, str]:
    """Fetch finish positions for a single year from Data Golf.

    Tries the historical-raw-data/rounds endpoint first. If that fails for
    current-season events (400/404), falls back to the preds/in-play endpoint
    which has final results for the most recently completed event.
    """
    import httpx
    from mcp_server.config import DATAGOLF_API_KEY

    # Try historical endpoint first (works for past seasons)
    url = "https://feeds.datagolf.com/historical-raw-data/rounds"
    params = {
        "tour": "pga",
        "event_id": event_id,
        "year": year,
        "file_format": "json",
        "key": DATAGOLF_API_KEY,
    }
    resp = httpx.get(url, params=params, timeout=30)

    if resp.status_code == 200:
        data = resp.json()
        scores = data.get("scores", [])
        if scores:
            # Deduplicate: only take the first occurrence per player
            # (scores has one entry per round; fin_text is the same across rounds)
            results = {}
            for s in scores:
                raw_name = s.get("player_name", "")
                name = _dg_name_to_display(raw_name)
                fin = s.get("fin_text")
                if fin is None:
                    continue
                if name not in results:
                    results[name] = _normalize_finish(fin)
            return results

    # Fallback: try preds/in-play for current-season events
    if resp.status_code in (400, 404) and year >= datetime.now(timezone.utc).year:
        print(f"  Historical endpoint unavailable for {year}, trying in-play fallback...")
        inplay_url = "https://feeds.datagolf.com/preds/in-play"
        inplay_params = {
            "tour": "pga",
            "odds_format": "american",
            "file_format": "json",
            "key": DATAGOLF_API_KEY,
        }
        try:
            inplay_resp = httpx.get(inplay_url, params=inplay_params, timeout=30)
            if inplay_resp.status_code == 200:
                inplay_data = inplay_resp.json()
                # Verify the in-play event matches the requested tournament
                inplay_event = (inplay_data.get("info", {}).get("event_name") or "").lower()
                if tournament_name and tournament_name.lower() not in inplay_event and inplay_event not in tournament_name.lower():
                    print(f"  In-play event '{inplay_event}' does not match '{tournament_name}', skipping fallback")
                else:
                    players = inplay_data.get("data", [])
                    if players:
                        results = {}
                        for p in players:
                            raw_name = p.get("player_name", "")
                            name = _dg_name_to_display(raw_name)
                            pos = str(p.get("current_pos", "")).strip()
                            if pos:
                                results[name] = _normalize_finish(pos)
                        if results:
                            print(f"  Got {len(results)} results from in-play endpoint ({inplay_event})")
                            return results
        except Exception as e:
            print(f"  In-play fallback failed: {e}")

    if resp.status_code == 404:
        return {}
    if resp.status_code != 200:
        resp.raise_for_status()
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch historical results from Data Golf API")
    parser.add_argument("--tournament", type=str, help="Tournament name (e.g. 'AT&T Pebble Beach Pro-Am')")
    parser.add_argument("--event-id", type=str, default=None, help="Data Golf event ID (overrides tournament name lookup)")
    parser.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025], help="Years to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Print results without saving")
    args = parser.parse_args()

    if not args.tournament and not args.event_id:
        print("Error: --tournament or --event-id required")
        return 1

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    dg = DataGolfClient()
    try:
        # Resolve event ID
        event_id = args.event_id
        tournament_name = args.tournament or ""
        if not event_id:
            print(f"Looking up event ID for '{tournament_name}'...")
            event_id = find_event_id(dg, tournament_name)
            if not event_id:
                print(f"Could not find Data Golf event ID for '{tournament_name}'")
                return 1
            print(f"Found event_id: {event_id}")
        else:
            if not tournament_name:
                tournament_name = f"event_{event_id}"

        safe = _safe_name(tournament_name)

        for year in args.years:
            print(f"\nFetching {year}...")
            try:
                results = fetch_results_for_year(dg, event_id, year, tournament_name=tournament_name)
            except Exception as e:
                print(f"  Error: {e}")
                continue

            if not results:
                print(f"  No data for {year}")
                continue

            print(f"  Got {len(results)} players")

            cache_data = {
                "tournament": tournament_name,
                "year": year,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "source": "Data Golf API (historical-raw-data/rounds)",
                "results": results,
            }

            if args.dry_run:
                # Show top 10
                for name, fin in list(results.items())[:10]:
                    print(f"    {name}: {fin}")
                print(f"  (dry run - not saved)")
            else:
                cache_file = CACHE_DIR / f"{safe}_{year}.json"
                cache_file.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"  Saved to {cache_file}")

        print("\nDone!")
        return 0
    finally:
        dg.close()


if __name__ == "__main__":
    raise SystemExit(main())
