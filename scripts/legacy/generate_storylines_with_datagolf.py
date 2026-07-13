#!/usr/bin/env python3
"""
Generate AI-powered storylines enhanced with Data Golf insights.

This script combines:
1. Data Golf skill ratings (strokes-gained components)
2. Course-specific fit adjustments
3. Model predictions (win %, top 10 %, etc.)
4. Course characteristics database

...and feeds all this data to Claude to write intelligent, data-driven storylines.

Usage:
    python scripts/generate_storylines_with_datagolf.py --tournament "WM Phoenix Open" --year 2026
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Script lives in scripts/legacy/; project root is 2 levels up
ROOT = Path(__file__).resolve().parent.parent.parent
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


def load_course_database() -> dict:
    """Load course characteristics database."""
    course_file = ROOT / "data" / "course_characteristics.json"
    if course_file.exists():
        with open(course_file) as f:
            return json.load(f)
    return {"courses": {}, "grass_types": {}, "skill_correlations": {}}


def get_course_info(course_db: dict, event_name: str) -> Optional[dict]:
    """Find course info by tournament name."""
    event_lower = event_name.lower()
    for course_id, info in course_db.get("courses", {}).items():
        if event_lower in info.get("tournament", "").lower():
            return info
        if event_lower in info.get("name", "").lower():
            return info
    return None


def build_datagolf_context(dg_client: DataGolfClient, tour: str = "pga") -> dict:
    """Fetch all Data Golf data for the current event."""
    print("  Fetching field updates...")
    field = dg_client.get_field_updates(tour=tour)

    print("  Fetching predictions...")
    predictions = dg_client.get_pre_tournament_predictions(tour=tour)

    print("  Fetching skill ratings...")
    skill_ratings = dg_client.get_player_skill_ratings()

    print("  Fetching course decompositions...")
    decompositions = dg_client.get_player_skill_decompositions(tour=tour)

    # Build lookup maps
    field_ids = {p.dg_id for p in field}
    field_map = {p.dg_id: p for p in field}
    skill_map = {s.dg_id: s for s in skill_ratings}
    decomp_map = {p["dg_id"]: p for p in decompositions.get("players", [])}
    pred_map = {p.dg_id: p for p in predictions.get("predictions", [])}

    # Rank players by various metrics
    field_skills = [s for s in skill_ratings if s.dg_id in field_ids]

    sg_total_ranked = sorted(field_skills, key=lambda x: x.sg_total or -999, reverse=True)
    sg_ott_ranked = sorted(field_skills, key=lambda x: x.sg_ott or -999, reverse=True)
    sg_app_ranked = sorted(field_skills, key=lambda x: x.sg_app or -999, reverse=True)
    sg_putt_ranked = sorted(field_skills, key=lambda x: x.sg_putt or -999, reverse=True)

    def get_rank(ranked_list, dg_id):
        for i, s in enumerate(ranked_list):
            if s.dg_id == dg_id:
                return i + 1
        return None

    return {
        "event_name": predictions.get("event_name"),
        "course_name": decompositions.get("course_name"),
        "field": field,
        "field_map": field_map,
        "skill_map": skill_map,
        "decomp_map": decomp_map,
        "pred_map": pred_map,
        "rankings": {
            "sg_total": sg_total_ranked,
            "sg_ott": sg_ott_ranked,
            "sg_app": sg_app_ranked,
            "sg_putt": sg_putt_ranked,
        },
        "get_rank": get_rank,
    }


def build_player_prompt_context(
    player_name: str,
    dg_context: dict,
    course_info: Optional[dict],
    existing_data: dict,
    recent_form_data: dict,
) -> str:
    """Build comprehensive context for a single player."""

    # Find player by name in field
    player = None
    for p in dg_context["field"]:
        if player_name.lower() in p.player_name.lower() or p.player_name.lower() in player_name.lower():
            player = p
            break

    if not player:
        # Fall back to existing data
        ctx = existing_data.get("odds", {}).get(player_name, {})
        recent = recent_form_data.get(player_name, "—")
        return f"""Player: {player_name}
- Win Odds: {ctx.get('odds', 'N/A')}
- Recent Form: {recent}
- [No Data Golf data available]"""

    dg_id = player.dg_id
    skills = dg_context["skill_map"].get(dg_id)
    decomp = dg_context["decomp_map"].get(dg_id, {})
    pred = dg_context["pred_map"].get(dg_id)
    get_rank = dg_context["get_rank"]

    # Build stats block
    lines = [f"Player: {player_name}"]
    lines.append(f"- Country: {player.country or 'N/A'}")

    # Odds from existing data
    odds_data = existing_data.get("odds", {}).get(player_name, {})
    lines.append(f"- Win Odds: {odds_data.get('odds', 'N/A')}")
    lines.append(f"- Top 5 Odds: {odds_data.get('top5', 'N/A')}")

    # Recent form
    recent = recent_form_data.get(player_name, "—")
    lines.append(f"- Recent Form: {recent}")

    # Strokes Gained
    if skills:
        sg_total_rank = get_rank(dg_context["rankings"]["sg_total"], dg_id)
        sg_app_rank = get_rank(dg_context["rankings"]["sg_app"], dg_id)
        sg_putt_rank = get_rank(dg_context["rankings"]["sg_putt"], dg_id)
        sg_ott_rank = get_rank(dg_context["rankings"]["sg_ott"], dg_id)

        lines.append(f"- SG Total: {skills.sg_total:+.2f} (#{sg_total_rank} in field)" if skills.sg_total else "")
        lines.append(f"- SG Off-the-Tee: {skills.sg_ott:+.2f} (#{sg_ott_rank} in field)" if skills.sg_ott else "")
        lines.append(f"- SG Approach: {skills.sg_app:+.2f} (#{sg_app_rank} in field)" if skills.sg_app else "")
        lines.append(f"- SG Putting: {skills.sg_putt:+.2f} (#{sg_putt_rank} in field)" if skills.sg_putt else "")
        if skills.driving_dist:
            lines.append(f"- Driving Distance: {skills.driving_dist:+.1f} yards vs avg")

    # Course Fit
    if decomp:
        course_hist = decomp.get("course_history_adjustment", 0)
        total_fit = decomp.get("total_fit_adjustment", 0)
        if course_hist and abs(course_hist) > 0.05:
            lines.append(f"- Course History Adj: {course_hist:+.2f} strokes (positive = good here historically)")
        if total_fit and abs(total_fit) > 0.03:
            lines.append(f"- Course Fit Adj: {total_fit:+.2f} strokes (positive = game suits this course)")

    # Predictions
    if pred and pred.win_prob:
        lines.append(f"- Model Win Prob: {pred.win_prob * 100:.1f}%")
        if pred.top_10_prob:
            lines.append(f"- Model Top 10 Prob: {pred.top_10_prob * 100:.1f}%")

    # Historical (from existing data)
    hist = existing_data.get("historical", {}).get(player_name, {})
    if hist:
        hist_str = ", ".join([f"{y}: {f}" for y, f in hist.items() if f and f != "NA"])
        if hist_str:
            lines.append(f"- Course History: {hist_str}")

    # Course demands (if we have course info)
    if course_info:
        key_skills = course_info.get("key_skills", {}).get("primary", [])
        bombers = course_info.get("scoring_profile", {}).get("bombers_advantage", "")
        if key_skills:
            lines.append(f"- Course Demands: {', '.join(key_skills)}")
        if bombers in ["high", "very_high"]:
            lines.append("- This is a BOMBERS course - driving distance is a major advantage")

    return "\n".join(filter(None, lines))


def generate_content_batch(
    players_batch: list,
    dg_context: dict,
    course_info: Optional[dict],
    existing_data: dict,
    recent_form_data: dict,
    tournament_name: str,
) -> dict:
    """Generate storylines for a batch of players using Claude with Data Golf context."""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        print("❌ anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Could not initialize Anthropic client: {e}")
        sys.exit(1)

    # Build player contexts with Data Golf data
    player_contexts = []
    for player in players_batch:
        ctx = build_player_prompt_context(
            player, dg_context, course_info, existing_data, recent_form_data
        )
        player_contexts.append(ctx)

    # Build course context
    course_context = ""
    if course_info:
        c = course_info
        course_context = f"""
Course: {c.get('name', 'Unknown')}
- Par: {c.get('characteristics', {}).get('par')}
- Yardage: {c.get('characteristics', {}).get('yardage')}
- Grass: {c.get('characteristics', {}).get('grass_type')}
- Bombers Advantage: {c.get('scoring_profile', {}).get('bombers_advantage')}
- Typical Winning Score: {c.get('scoring_profile', {}).get('typical_winning_score')}
- Key Skills Required: {', '.join(c.get('key_skills', {}).get('primary', []))}
- Notes: {c.get('key_skills', {}).get('notes', '')}
"""

    prompt = f"""You are a professional golf analytics writer creating betting preview content for {tournament_name}.

{course_context}

For each player below, write a compelling 2-3 sentence "Why They Could Win" storyline.

IMPORTANT - Use the Data Golf analytics provided:
- Reference their STROKES GAINED rankings and what it means for this course
- Use COURSE FIT adjustments to explain why they suit (or don't suit) this venue
- Connect their specific strengths to what THIS COURSE demands
- If they have positive course history adjustment, mention their track record here
- Use actual numbers and rankings - be specific and data-driven

Writing Guidelines:
- Lead with their most compelling statistical edge at THIS course
- Connect strokes-gained strengths to course demands (e.g., "ranks #3 in SG: Approach, crucial at this precision course")
- If course history adjustment is positive, weave in their track record
- Mention model win probability if it shows they're undervalued
- Be concise but substantive - no generic fluff
- Make it sound like an insider betting tip, not a Wikipedia bio

{'---'.join(player_contexts)}

Return your response as a JSON object with this structure:
{{
  "Player Name": {{
    "storyline": "2-3 sentence data-driven storyline"
  }}
}}

Only include JSON in your response, nothing else."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        return result

    except Exception as e:
        print(f"❌ Error generating content for batch: {e}")
        return {player: {"storyline": f"Competing at {tournament_name}."} for player in players_batch}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI storylines with Data Golf analytics.")
    parser.add_argument("--tournament", type=str, required=True, help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--tour", type=str, default="pga", help="Tour code (pga, euro, kft)")
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    year = args.year
    players_data_path = ROOT / "data" / f"{slug}_{year}_players_data.json"
    storylines_out_path = ROOT / "data" / f"{slug}_{year}_storylines.json"
    recent_form_path = ROOT / "data" / f"{slug}_{year}_recent_form.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    existing_data = json.loads(players_data_path.read_text(encoding="utf-8"))
    tournament_name = existing_data.get("tournament", {}).get("name", args.tournament)

    # Load recent form data
    recent_form_data = {}
    if recent_form_path.exists():
        try:
            recent_form_data = json.loads(recent_form_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  Could not load recent form data: {e}")

    # Load course database
    course_db = load_course_database()
    course_info = get_course_info(course_db, tournament_name)
    if course_info:
        print(f"✓ Found course profile for: {course_info.get('name')}")
    else:
        print(f"⚠️  No course profile found for {tournament_name}")

    # Initialize Data Golf client and fetch data
    print(f"\n📊 Fetching Data Golf analytics...")
    try:
        dg_client = DataGolfClient()
        dg_context = build_datagolf_context(dg_client, tour=args.tour)
        print(f"✓ Data Golf event: {dg_context['event_name']}")
        print(f"✓ Field size: {len(dg_context['field'])} players")
    except Exception as e:
        print(f"❌ Could not fetch Data Golf data: {e}")
        return 1

    # Get all players from odds
    players = list(existing_data.get("odds", {}).keys())
    print(f"\n📝 Generating AI storylines for {len(players)} players...")

    storylines = {}
    batch_size = 8  # Slightly smaller batches for more context per player

    for i in range(0, len(players), batch_size):
        batch = players[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(players) - 1) // batch_size + 1
        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} players)...", end=" ", flush=True)

        try:
            results = generate_content_batch(
                batch, dg_context, course_info, existing_data, recent_form_data, tournament_name
            )

            for player in batch:
                if player in results:
                    storylines[player] = results[player].get("storyline", f"Competing at {tournament_name}.")
                else:
                    storylines[player] = f"Competing at {tournament_name}."

            print("✓")

        except Exception as e:
            print(f"❌ {e}")
            for player in batch:
                storylines[player] = f"Competing at {tournament_name}."

    # Load existing storylines if they exist to preserve recent_form_analyses
    existing_storylines = {}
    if storylines_out_path.exists():
        try:
            existing_storylines = json.loads(storylines_out_path.read_text(encoding="utf-8"))
        except:
            pass

    output = {
        "storylines": storylines,
        "recent_form_analyses": existing_storylines.get("recent_form_analyses", {}),
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": "claude-sonnet-4 + Data Golf",
        "data_golf_event": dg_context["event_name"],
        "course_info_used": course_info.get("name") if course_info else None,
    }

    storylines_out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Wrote {storylines_out_path}")

    # Clean up
    dg_client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
