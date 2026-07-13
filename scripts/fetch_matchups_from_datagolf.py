#!/usr/bin/env python3
"""
Fetch tournament and round matchup odds from Data Golf and save for the preview.

Writes JSON with:
- tournament_matchups: head-to-head (2-ball) for the full tournament
- round_matchups: round-by-round head-to-head (if available)
- three_balls: 3-ball matchups (if available)

All odds from Data Golf API (repeatable; no book dependency). daily_three_balls
uses DG fair odds; tournament/round matchups include DG probabilities and lean.

Usage:
    python scripts/fetch_matchups_from_datagolf.py
    python scripts/fetch_matchups_from_datagolf.py --output data/wm_phoenix_open_2026_matchups.json
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


def _event_key_tokens(name: str) -> set[str]:
    """Distinctive tokens of an event name (drops sponsor/format stopwords).

    Used to detect when the all-pairings endpoint is still returning the PREVIOUS
    event's groupings (common early in the week before tee times are posted).
    'RBC Canadian Open' -> {rbc, canadian}; 'the Memorial ... Workday' -> {memorial, workday}.
    """
    stop = {
        "the", "presented", "by", "tournament", "open", "championship", "classic",
        "invitational", "pga", "tour", "golf", "of", "at", "in", "and", "challenge",
        "an", "a", "cup", "championships", "event",
    }
    toks = re.findall(r"[a-z0-9]+", (name or "").lower())
    return {t for t in toks if t not in stop and len(t) > 2}


def _event_matches(expected: str | None, actual: str | None) -> bool:
    """True if the API's event name plausibly matches the expected tournament."""
    if not expected:
        return True  # no guard requested
    exp, act = _event_key_tokens(expected), _event_key_tokens(actual)
    return bool(exp & act)


def _dg_name_to_display(name: str) -> str:
    """Convert 'Last, First' to 'First Last'."""
    if not name or "," not in name:
        return name.strip()
    parts = [p.strip() for p in name.split(",", 1)]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name.strip()


def _american_to_implied_prob(odds: int | str | None) -> float | None:
    """Convert American odds to implied probability (0-1)."""
    if odds is None:
        return None
    try:
        n = int(odds)
    except (TypeError, ValueError):
        return None
    if n > 0:
        return 100 / (n + 100)
    return abs(n) / (abs(n) + 100)


def _edge_analysis(
    dg_prob: float | None,
    book_odds: int | str | None,
) -> tuple[str, float | None]:
    """Return (lean_label, edge_pct). edge_pct = (dg_prob - book_implied) * 100."""
    if dg_prob is None:
        return ("—", None)
    book_implied = _american_to_implied_prob(book_odds)
    if book_implied is None or book_implied <= 0:
        return (f"{dg_prob:.0%} DG", None)
    edge_pct = (dg_prob - book_implied) * 100
    if edge_pct >= 3:
        return (f"Lean (DG +{edge_pct:.1f}%)", edge_pct)
    if edge_pct <= -3:
        return (f"Fade (DG {edge_pct:.1f}%)", edge_pct)
    return ("Fair", edge_pct)


def matchup_to_dict(m) -> dict:
    """Convert DataGolfMatchup to JSON-serializable dict with display names and analysis."""
    p1_name = _dg_name_to_display(m.player_1_name or "")
    p2_name = _dg_name_to_display(m.player_2_name or "")
    p1_prob = m.player_1_dg_prob
    p2_prob = m.player_2_dg_prob
    p1_odds = m.player_1_book_odds
    p2_odds = m.player_2_book_odds

    lean1, edge1 = _edge_analysis(p1_prob, p1_odds)
    lean2, edge2 = _edge_analysis(p2_prob, p2_odds)

    out = {
        "matchup_type": m.matchup_type or "2-ball",
        "player_1_name": p1_name,
        "player_2_name": p2_name,
        "player_1_odds": p1_odds,
        "player_2_odds": p2_odds,
        "player_1_dg_prob": round(p1_prob, 3) if p1_prob is not None else None,
        "player_2_dg_prob": round(p2_prob, 3) if p2_prob is not None else None,
        "player_1_lean": lean1,
        "player_2_lean": lean2,
        "player_1_edge_pct": round(edge1, 1) if edge1 is not None else None,
        "player_2_edge_pct": round(edge2, 1) if edge2 is not None else None,
    }
    if m.player_3_name or m.player_3_dg_id:
        out["player_3_name"] = _dg_name_to_display(m.player_3_name or "")
        out["player_3_odds"] = m.player_3_book_odds
        out["player_3_dg_prob"] = round(m.player_3_dg_prob, 3) if m.player_3_dg_prob is not None else None
        out["player_3_lean"], _ = _edge_analysis(m.player_3_dg_prob, m.player_3_book_odds)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch matchup odds from Data Golf")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "wm_phoenix_open_2026_matchups.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--tour",
        type=str,
        default="pga",
        help="Tour code (default: pga)",
    )
    parser.add_argument(
        "--expected-event",
        type=str,
        default=None,
        help="Target tournament name. If the all-pairings endpoint returns a "
        "different event (stale pairings from last week), daily three-balls are dropped.",
    )
    args = parser.parse_args()

    out_path = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with DataGolfClient() as dg:
            tournament = dg.get_matchup_odds(tour=args.tour, market="tournament_matchups")
            try:
                round_matchups = dg.get_matchup_odds(tour=args.tour, market="round_matchups")
            except Exception:
                round_matchups = []
            try:
                three_balls = dg.get_matchup_odds(tour=args.tour, market="3_balls")
            except Exception:
                three_balls = []
            # Round 1 (and 2) group pairings with DG fair odds - always available for current event
            try:
                all_pairings = dg.get_matchup_odds_all_pairings(tour=args.tour)
            except Exception:
                all_pairings = {}
    except Exception as e:
        print(f"❌ Data Golf API error: {e}")
        return 1

    # Build round 1 (daily) three-ball pairings from all_pairings response
    daily_three_balls = []
    pairings_list = all_pairings.get("pairings") or []
    event_name_from_api = all_pairings.get("event_name") or "Current event"
    last_update_pairings = all_pairings.get("last_update") or _now_iso()

    # Guard: early in the week the all-pairings endpoint still returns LAST week's
    # final-round groupings. Drop them rather than mislabel them as this event's.
    if pairings_list and not _event_matches(args.expected_event, event_name_from_api):
        print(
            f"⚠️  Pairings event '{event_name_from_api}' != expected '{args.expected_event}' "
            f"— dropping {len(pairings_list)} stale daily groups (tee times not posted yet)."
        )
        pairings_list = []

    for g in pairings_list:
        p1 = g.get("p1") or {}
        p2 = g.get("p2") or {}
        p3 = g.get("p3") or {}
        daily_three_balls.append({
            "group": g.get("group"),
            "teetime": g.get("teetime"),
            "start_hole": g.get("start_hole"),
            "course": g.get("course"),
            "player_1_name": _dg_name_to_display(p1.get("name") or ""),
            "player_2_name": _dg_name_to_display(p2.get("name") or ""),
            "player_3_name": _dg_name_to_display(p3.get("name") or ""),
            "player_1_odds": p1.get("odds"),
            "player_2_odds": p2.get("odds"),
            "player_3_odds": p3.get("odds"),
        })

    payload = {
        "event_name": event_name_from_api,
        "last_updated": _now_iso(),
        "last_update_pairings": last_update_pairings,
        "source": "Data Golf",
        "odds_source": "Data Golf",
        "tournament_matchups": [matchup_to_dict(m) for m in tournament],
        "round_matchups": [matchup_to_dict(m) for m in round_matchups],
        "three_balls": [matchup_to_dict(m) for m in three_balls],
        "daily_three_balls": daily_three_balls,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    n_t, n_r, n_3, n_d = (
        len(payload["tournament_matchups"]),
        len(payload["round_matchups"]),
        len(payload["three_balls"]),
        len(payload["daily_three_balls"]),
    )
    print(f"✅ Matchups saved: {n_t} tournament, {n_r} round, {n_3} 3-ball, {n_d} daily groups → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
