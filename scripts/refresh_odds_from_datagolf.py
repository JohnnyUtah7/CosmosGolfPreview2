#!/usr/bin/env python3
"""
Refresh tournament odds from Data Golf API (outright winner, top 5, top 10).

Uses Data Golf fair odds (model baseline_history_fit) as the single source
for a repeatable process—no DraftKings or other book dependency. Same
golfdata API used for matchups and outrights.

Creates players_data JSON if it does not exist. Otherwise updates the odds
section and data_sources.

Usage:
    python scripts/refresh_odds_from_datagolf.py --tournament "WM Phoenix Open" --year 2026
    python scripts/refresh_odds_from_datagolf.py --players-data data/wm_phoenix_open_2026_players_data.json --year 2026
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_american(s: str) -> int | None:
    """Parse American odds string to integer. '+225' -> 225, '-186' -> -186."""
    if not s:
        return None
    t = str(s).replace("−", "-").replace(",", "").strip()
    if t.startswith("+"):
        t = t[1:]
    if re.fullmatch(r"-?\d{2,7}", t):
        return int(t)
    return None


def _slugify(name: str) -> str:
    """Convert tournament name to slug for file paths."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


_EVENT_STOPWORDS = {"the", "presented", "by", "of", "at", "in", "and", "a", "an", "for"}


def _event_tokens(name: str) -> set[str]:
    return {
        w for w in re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).split()
        if w not in _EVENT_STOPWORDS
    }


def _events_match(expected: str, actual: str) -> bool:
    """True if the Data Golf event name plausibly matches the expected tournament.

    Guards against Data Golf still serving the PREVIOUS event's odds early in the
    week (outrights roll over ~Mon night/Tue). Requires a strong majority of the
    expected event's distinctive tokens to appear in the actual event name — so
    'Genesis Scottish Open' does NOT match 'John Deere Classic' or 'Genesis
    Invitational', but tolerates sponsor-string variations (e.g. schedule's
    'The Memorial Tournament presented by Workday' vs DG's 'the Memorial Tournament').
    """
    exp = _event_tokens(expected)
    act = _event_tokens(actual)
    if not exp or not act:
        return True  # can't validate — don't block
    overlap = len(exp & act)
    import math
    return overlap >= max(1, math.ceil(0.6 * len(exp)))


def _dg_name_to_display(name: str) -> str:
    """Convert 'Last, First' (DG format) to 'First Last'."""
    if not name or "," not in name:
        return name.strip()
    parts = [p.strip() for p in name.split(",", 1)]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh tournament odds from Data Golf")
    parser.add_argument(
        "--players-data",
        type=Path,
        default=None,
        help="Path to tournament players_data JSON (created if missing). If not set, --tournament and --year are required.",
    )
    parser.add_argument(
        "--tournament",
        type=str,
        default=None,
        help="Tournament name (e.g. 'WM Phoenix Open'). Used with --year to derive path when --players-data is not set.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Tournament year (used when creating a new players_data file or with --tournament)",
    )
    parser.add_argument(
        "--expected-event",
        type=str,
        default=None,
        help="Expected tournament name. If Data Golf's outrights event does not match "
             "(e.g. it is still serving last week's event early in the week), abort instead "
             "of silently building the wrong field.",
    )
    parser.add_argument(
        "--skip-event-check",
        action="store_true",
        help="Bypass the --expected-event guard (build with whatever event DG returns).",
    )
    args = parser.parse_args()

    if args.players_data is not None:
        path = args.players_data if args.players_data.is_absolute() else PROJECT_ROOT / args.players_data
    elif args.tournament and args.year:
        slug = _slugify(args.tournament)
        path = PROJECT_ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    else:
        print("Error: Provide either --players-data OR both --tournament and --year.", file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}

    if "odds" not in data:
        data["odds"] = {}

    with DataGolfClient() as dg:
        win_result = dg.get_outright_odds(tour="pga", market="win")
        top5_result = dg.get_outright_odds(tour="pga", market="top_5")
        top10_result = dg.get_outright_odds(tour="pga", market="top_10")

    event = win_result.get("event_name", "Current PGA event")
    print(f"Event: {event}")

    # Guard: Data Golf rolls outrights over to the new event only ~Mon night/Tue.
    # Early in the week it keeps serving the PREVIOUS event, which would silently
    # build the wrong field. Abort loudly instead.
    expected = args.expected_event
    if expected and not args.skip_event_check and not _events_match(expected, event):
        print("=" * 70, file=sys.stderr)
        print(f"❌ ODDS EVENT MISMATCH — Data Golf outrights are not for the expected event.", file=sys.stderr)
        print(f"     expected : {expected}", file=sys.stderr)
        print(f"     Data Golf: {event}", file=sys.stderr)
        print(f"   Data Golf has not rolled its odds market over to '{expected}' yet", file=sys.stderr)
        print(f"   (usually posts Mon night/Tue for a Thu start). Re-run once it flips,", file=sys.stderr)
        print(f"   or pass --skip-event-check to build with the '{event}' field anyway.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return 2

    def _dg_fair_or_book(o: dict, book_key: str = "draftkings") -> int | None:
        """Prefer Data Golf fair odds; fall back to book line if DG missing."""
        dg = o.get("datagolf") or {}
        fair = dg.get("baseline_history_fit") or dg.get("baseline")
        if fair is not None:
            return _parse_american(str(fair))
        return _parse_american(o.get(book_key))

    win_odds_list = win_result.get("odds", [])
    top5_by_name = {o.get("player_name"): o for o in top5_result.get("odds", [])}
    top10_by_name = {o.get("player_name"): o for o in top10_result.get("odds", [])}

    new_odds = {}
    for o in win_odds_list:
        dg_name = o.get("player_name")
        if not dg_name:
            continue
        display_name = _dg_name_to_display(dg_name)
        win_int = _dg_fair_or_book(o)
        if win_int is None:
            continue
        top5_o = top5_by_name.get(dg_name)
        top10_o = top10_by_name.get(dg_name)
        top5_int = _dg_fair_or_book(top5_o) if top5_o else None
        top10_int = _dg_fair_or_book(top10_o) if top10_o else None
        new_odds[display_name] = {
            "bookmaker": "Data Golf",
            "odds": win_int,
            "top5": top5_int,
            "top10": top10_int,
        }

    data["odds"] = new_odds

    # Also pull in field players who don't have odds yet (field-updates endpoint)
    with DataGolfClient() as dg2:
        try:
            field_players = dg2.get_field_updates(tour="pga")
            # field_players is a list of FieldUpdate objects
            added = 0
            for fp in field_players:
                dg_name = getattr(fp, "player_name", "") or ""
                if not dg_name:
                    continue
                display_name = _dg_name_to_display(dg_name)
                if display_name not in new_odds:
                    new_odds[display_name] = {
                        "bookmaker": "Data Golf",
                        "odds": None,
                        "top5": None,
                        "top10": None,
                    }
                    added += 1
            if added:
                data["odds"] = new_odds
                print(f"   + {added} field players added without odds (from field-updates)")
        except Exception as e:
            print(f"   ⚠ Could not fetch field updates: {e}")

    if "data_sources" not in data:
        data["data_sources"] = {}
    data["data_sources"]["odds"] = "Data Golf"
    data["data_sources"]["odds_fetched_at"] = _now_iso()

    # If we created from scratch, ensure required structure for downstream scripts
    if "tournament" not in data:
        data["tournament"] = {
            "name": event,
            "year": args.year,
            "location": "",
            "course": "",
            "dates": "",
            "purse": "",
            "defending_champion": "",
        }
    if "historical_years" not in data:
        data["historical_years"] = [str(args.year - 1), str(args.year - 2), str(args.year - 3)]
    if "historical" not in data:
        data["historical"] = {}
    if "countries" not in data:
        data["countries"] = {}
    if "owgr" not in data:
        data["owgr"] = {}

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Odds from Data Golf: {len(new_odds)} players (win, top 5, top 10) → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
