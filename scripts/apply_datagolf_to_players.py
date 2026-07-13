#!/usr/bin/env python3
"""
Apply Data Golf analytics to player data files.

This script fetches Data Golf data (skill ratings, predictions, course fit)
and merges it into the tournament's players_data.json file for use in
HTML generation and storyline creation.

Usage:
    python scripts/apply_datagolf_to_players.py --tournament "WM Phoenix Open" --year 2026
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from mcp_server.tools.datagolf import DataGolfClient


def _slugify(name: str) -> str:
    """Convert tournament name to slug."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


_EVENT_STOPWORDS = {"the", "presented", "by", "of", "at", "in", "and", "a", "an", "for"}


def _events_match(expected: str, actual: str) -> bool:
    """True if the Data Golf event name plausibly matches the expected tournament.

    Guards against Data Golf still serving the PREVIOUS event's pre-tournament
    predictions early in the week (they roll over ~Mon night/Tue). Requires a
    strong majority of the expected event's distinctive tokens to appear in the
    actual name, so 'Genesis Scottish Open' matches neither 'John Deere Classic'
    nor 'Genesis Invitational', but tolerates sponsor-string variants.
    """
    import math

    def toks(name: str) -> set:
        return {
            w for w in re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).split()
            if w not in _EVENT_STOPWORDS
        }

    exp, act = toks(expected), toks(actual)
    if not exp or not act:
        return True
    return len(exp & act) >= max(1, math.ceil(0.6 * len(exp)))


def normalize_name(name: str) -> str:
    """Normalize name to 'first last' format for comparison."""
    name = name.lower().strip()
    # Handle "Last, First" format from Data Golf
    if ", " in name:
        parts = name.split(", ", 1)
        return f"{parts[1]} {parts[0]}"
    return name


def match_player_name(name: str, dg_players: list) -> Optional[object]:
    """Find matching Data Golf player by name."""
    name_normalized = normalize_name(name)
    name_parts = name_normalized.split()

    for p in dg_players:
        dg_normalized = normalize_name(p.player_name)
        dg_parts = dg_normalized.split()

        # Exact match
        if name_normalized == dg_normalized:
            return p

        # Fuzzy match (one contains the other)
        if name_normalized in dg_normalized or dg_normalized in name_normalized:
            return p

        # Try last name match with first initial
        if len(name_parts) >= 2 and len(dg_parts) >= 2:
            # Compare last names
            if name_parts[-1] == dg_parts[-1]:
                # Check first initial
                if name_parts[0][0] == dg_parts[0][0]:
                    return p

        # Try first and last name only (ignore middle names)
        if len(name_parts) >= 2 and len(dg_parts) >= 2:
            if name_parts[0] == dg_parts[0] and name_parts[-1] == dg_parts[-1]:
                return p

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Data Golf data to players file.")
    parser.add_argument("--tournament", type=str, required=True, help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--tour", type=str, default="pga", help="Tour code (pga, euro, kft)")
    parser.add_argument("--slug", type=str, default=None, help="Explicit data-file slug (overrides slugified --tournament; matches the schedule slug)")
    parser.add_argument("--expected-event", type=str, default=None, help="Expected event name for the DG rollover guard (defaults to --tournament)")
    parser.add_argument("--skip-event-check", action="store_true", help="Bypass the pre-tournament-predictions event guard")
    args = parser.parse_args()

    slug = args.slug or _slugify(args.tournament)
    year = args.year
    players_data_path = ROOT / "data" / f"{slug}_{year}_players_data.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    print(f"📊 Fetching Data Golf analytics for {args.tournament}...")

    try:
        dg = DataGolfClient()

        # Fetch all relevant data
        print("  Fetching field updates...")
        field = dg.get_field_updates(tour=args.tour)

        print("  Fetching predictions...")
        predictions = dg.get_pre_tournament_predictions(tour=args.tour)

        print("  Fetching skill ratings...")
        skill_ratings = dg.get_player_skill_ratings()

        print("  Fetching course decompositions...")
        decompositions = dg.get_player_skill_decompositions(tour=args.tour)

        # Build lookup maps
        field_map = {p.dg_id: p for p in field}
        skill_map = {s.dg_id: s for s in skill_ratings}
        decomp_map = {p["dg_id"]: p for p in decompositions.get("players", [])}
        pred_map = {p.dg_id: p for p in predictions.get("predictions", [])}

        # Rank players by various metrics for field-relative rankings
        field_ids = {p.dg_id for p in field}
        field_skills = [s for s in skill_ratings if s.dg_id in field_ids]

        sg_total_ranked = sorted(field_skills, key=lambda x: x.sg_total or -999, reverse=True)
        sg_ott_ranked = sorted(field_skills, key=lambda x: x.sg_ott or -999, reverse=True)
        sg_app_ranked = sorted(field_skills, key=lambda x: x.sg_app or -999, reverse=True)
        sg_arg_ranked = sorted(field_skills, key=lambda x: x.sg_arg or -999, reverse=True)
        sg_putt_ranked = sorted(field_skills, key=lambda x: x.sg_putt or -999, reverse=True)

        def get_rank(ranked_list, dg_id):
            for i, s in enumerate(ranked_list):
                if s.dg_id == dg_id:
                    return i + 1
            return None

        dg_event = predictions.get("event_name")
        print(f"✓ Data Golf event: {dg_event}")

        # Guard: DG pre-tournament predictions roll over ~Mon night/Tue. Early in
        # the week they still describe last week's event; applying them would map
        # the wrong SG/model/course-fit onto this week's field. Abort loudly.
        expected = args.expected_event or args.tournament
        if expected and not args.skip_event_check and not _events_match(expected, dg_event):
            print("=" * 70, file=sys.stderr)
            print("❌ ANALYTICS EVENT MISMATCH — Data Golf predictions are not for the expected event.", file=sys.stderr)
            print(f"     expected : {expected}", file=sys.stderr)
            print(f"     Data Golf: {dg_event}", file=sys.stderr)
            print("   Data Golf has not rolled its pre-tournament model over to this event yet", file=sys.stderr)
            print("   (usually posts Mon night/Tue). Re-run once it flips, or pass", file=sys.stderr)
            print("   --skip-event-check to apply the current model anyway.", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            return 2

        print(f"✓ Field size: {len(field)} players")
        print(f"✓ Skill ratings: {len(skill_ratings)} players")

        # Load existing player data
        data = json.loads(players_data_path.read_text(encoding="utf-8"))
        player_names = list(data.get("odds", {}).keys())

        # Initialize datagolf section
        if "datagolf" not in data:
            data["datagolf"] = {}

        # Populate player countries from Data Golf field-updates (authoritative,
        # covers the whole field with 3-letter codes e.g. SCO/NIR/SWE). Without this
        # the HTML falls back to "USA" for everyone — wrong for global/co-sanctioned
        # fields like the Genesis Scottish Open.
        if "countries" not in data:
            data["countries"] = {}

        # Match and merge data for each player
        matched = 0
        unmatched = []

        for player_name in player_names:
            dg_player = match_player_name(player_name, field)

            if not dg_player:
                unmatched.append(player_name)
                continue

            matched += 1
            dg_id = dg_player.dg_id

            # Country (from field-updates) — 3-letter code, authoritative for the field.
            ccode = (getattr(dg_player, "country", "") or "").strip().upper()
            if ccode:
                data["countries"][player_name] = ccode

            skills = skill_map.get(dg_id)
            decomp = decomp_map.get(dg_id, {})
            pred = pred_map.get(dg_id)

            # Build player's Data Golf data
            dg_data = {
                "dg_id": dg_id,
                "dg_name": dg_player.player_name,
            }

            # Strokes Gained data
            if skills:
                dg_data["sg_total"] = round(skills.sg_total, 2) if skills.sg_total else None
                dg_data["sg_ott"] = round(skills.sg_ott, 2) if skills.sg_ott else None
                dg_data["sg_app"] = round(skills.sg_app, 2) if skills.sg_app else None
                dg_data["sg_arg"] = round(skills.sg_arg, 2) if skills.sg_arg else None
                dg_data["sg_putt"] = round(skills.sg_putt, 2) if skills.sg_putt else None
                dg_data["driving_dist"] = round(skills.driving_dist, 1) if skills.driving_dist else None
                dg_data["driving_acc"] = round(skills.driving_acc, 3) if skills.driving_acc else None

                # Field rankings
                dg_data["sg_total_rank"] = get_rank(sg_total_ranked, dg_id)
                dg_data["sg_ott_rank"] = get_rank(sg_ott_ranked, dg_id)
                dg_data["sg_app_rank"] = get_rank(sg_app_ranked, dg_id)
                dg_data["sg_arg_rank"] = get_rank(sg_arg_ranked, dg_id)
                dg_data["sg_putt_rank"] = get_rank(sg_putt_ranked, dg_id)

            # Course fit data
            if decomp:
                dg_data["course_fit"] = round(decomp.get("total_fit_adjustment", 0), 3) if decomp.get("total_fit_adjustment") else None
                dg_data["course_history"] = round(decomp.get("course_history_adjustment", 0), 3) if decomp.get("course_history_adjustment") else None

            # Predictions
            if pred:
                dg_data["win_prob"] = round(pred.win_prob * 100, 2) if pred.win_prob else None
                dg_data["top_5_prob"] = round(pred.top_5_prob * 100, 1) if pred.top_5_prob else None
                dg_data["top_10_prob"] = round(pred.top_10_prob * 100, 1) if pred.top_10_prob else None
                dg_data["top_20_prob"] = round(pred.top_20_prob * 100, 1) if pred.top_20_prob else None
                dg_data["make_cut_prob"] = round(pred.make_cut_prob * 100, 1) if pred.make_cut_prob else None

            # DFS salaries if available
            if dg_player.dk_salary:
                dg_data["dk_salary"] = dg_player.dk_salary
            if dg_player.fd_salary:
                dg_data["fd_salary"] = dg_player.fd_salary

            data["datagolf"][player_name] = dg_data

        # Add metadata
        data["datagolf_metadata"] = {
            "event_name": predictions.get("event_name"),
            "course_name": decompositions.get("course_name"),
            "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "matched_players": matched,
            "unmatched_players": len(unmatched),
            "field_size": len(field),
        }

        # Save updated data
        players_data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"\n✅ Applied Data Golf data to {players_data_path}")
        print(f"   Matched: {matched}/{len(player_names)} players")

        if unmatched:
            print(f"\n⚠️  Unmatched players ({len(unmatched)}):")
            for name in unmatched[:10]:
                print(f"   - {name}")
            if len(unmatched) > 10:
                print(f"   ... and {len(unmatched) - 10} more")

        dg.close()
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
