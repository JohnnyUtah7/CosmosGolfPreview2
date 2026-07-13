#!/usr/bin/env python3
"""
Generate AI-powered executive summary and betting insights.

This script analyzes all player Data Golf analytics and generates:
1. An executive summary paragraph with key insights
2. Top 5-10 specific betting insights based on the data

Usage:
    python scripts/generate_ai_insights.py --tournament "WM Phoenix Open" --year 2026
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()


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


def get_schedule_course(tournament_name: str, year: int) -> str | None:
    """Authoritative venue name from the PGA schedule (e.g. 'TPC Toronto at Osprey Valley')."""
    sched_path = ROOT / "data" / f"pga_schedule_{year}.json"
    if not sched_path.exists():
        return None
    try:
        sched = json.loads(sched_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    slug = _slugify(tournament_name)
    for t in sched.get("tournaments", []) + sched.get("fall_schedule", []):
        if t.get("slug") == slug or tournament_name.lower() in (t.get("name", "") or "").lower():
            return t.get("course")
    return None


def get_event_champions(slug: str, year: int) -> tuple[dict[int, str], str | None]:
    """Past winners from result caches + the defending champion (last year's winner).

    Prevents the model from mislabeling a past winner as 'defending champion' or
    inventing a title. Returns ({year: winner}, defending_champ_or_None).
    """
    cache_dir = ROOT / "data" / "tournament_results_cache"
    winners: dict[int, str] = {}
    for f in sorted(cache_dir.glob(f"{slug}_*.json")):
        m = re.search(rf"{re.escape(slug)}_(\d{{4}})\.json$", f.name)
        if not m:
            continue
        y = int(m.group(1))
        try:
            res = json.loads(f.read_text(encoding="utf-8")).get("results", {})
        except Exception:
            continue
        w = next((nm for nm, fin in res.items() if str(fin).replace("T", "").strip() == "1"), None)
        if w:
            if "," in w:
                a, b = [x.strip() for x in w.split(",", 1)]
                w = f"{b} {a}"
            winners[y] = w
    prior = sorted([y for y in winners if y < year])
    return winners, (winners[prior[-1]] if prior else None)


def get_course_info(course_db: dict, event_name: str) -> dict | None:
    """Find course info by tournament name."""
    event_lower = event_name.lower()
    for course_id, info in course_db.get("courses", {}).items():
        if event_lower in info.get("tournament", "").lower():
            return info
        if event_lower in info.get("name", "").lower():
            return info
    return None


def build_analysis_context(data: dict, tournament_name: str, course_info: dict | None) -> str:
    """Build comprehensive context for AI analysis."""
    odds = data.get("odds", {})
    datagolf = data.get("datagolf", {})
    historical = data.get("historical", {})

    # Sort by odds
    players_by_odds = sorted(
        [(name, info.get("odds") or 9999) for name, info in odds.items()],
        key=lambda x: x[1]
    )

    context_lines = [f"Tournament: {tournament_name}"]

    # Course info
    if course_info:
        context_lines.append(f"\nCourse: {course_info.get('name')}")
        context_lines.append(f"Par: {course_info.get('characteristics', {}).get('par')}")
        context_lines.append(f"Yardage: {course_info.get('characteristics', {}).get('yardage')}")
        context_lines.append(f"Key Skills: {', '.join(course_info.get('key_skills', {}).get('primary', []))}")
        context_lines.append(f"Bombers Advantage: {course_info.get('scoring_profile', {}).get('bombers_advantage')}")
        context_lines.append(f"Typical Winning Score: {course_info.get('scoring_profile', {}).get('typical_winning_score')}")

    context_lines.append(f"\n=== FIELD ANALYSIS ({len(odds)} players) ===\n")

    # Top favorites analysis
    context_lines.append("TOP 10 FAVORITES:")
    for name, win_odds in players_by_odds[:10]:
        dg = datagolf.get(name, {})
        hist = historical.get(name, {})

        sg_total = dg.get("sg_total")
        sg_total_rank = dg.get("sg_total_rank")
        sg_app = dg.get("sg_app")
        sg_putt = dg.get("sg_putt")
        win_prob = dg.get("win_prob")
        top10_prob = dg.get("top_10_prob")
        course_fit = dg.get("course_fit")
        course_hist = dg.get("course_history")

        hist_str = ", ".join([f"{y}: {v}" for y, v in hist.items() if v and v != "NA"])

        line = f"  {name} ({'+' if win_odds >= 0 else ''}{win_odds})"
        if sg_total:
            line += f" | SG Total: {sg_total:+.2f} (#{sg_total_rank})"
        if win_prob:
            line += f" | Model Win: {win_prob:.1f}%"
        if course_fit:
            line += f" | Course Fit: {course_fit:+.3f}"
        if hist_str:
            line += f" | History: {hist_str}"
        context_lines.append(line)

    # Value plays (high win prob relative to odds)
    context_lines.append("\n\nPOTENTIAL VALUE PLAYS (model sees more value than odds suggest):")
    value_plays = []
    for name, win_odds in players_by_odds:
        dg = datagolf.get(name, {})
        win_prob = dg.get("win_prob")
        if win_prob:
            # Rough conversion: +500 odds ≈ 16.7% implied prob
            implied_prob = 100 / (win_odds + 100) if win_odds > 0 else 100 / (100 - win_odds)
            edge = win_prob - implied_prob
            if edge > 2:  # 2% edge or more
                value_plays.append((name, win_odds, win_prob, implied_prob, edge, dg))

    value_plays.sort(key=lambda x: x[4], reverse=True)
    for name, odds_val, win_prob, implied, edge, dg in value_plays[:8]:
        sg_total = dg.get("sg_total")
        context_lines.append(f"  {name}: Odds {'+' if odds_val >= 0 else ''}{odds_val} (implied {implied:.1f}%) vs Model {win_prob:.1f}% | Edge: +{edge:.1f}%{f' | SG Total: {sg_total:+.2f}' if sg_total else ''}")

    # Best ball-strikers in field
    context_lines.append("\n\nTOP BALL-STRIKERS (SG Approach):")
    approach_leaders = []
    for name in odds.keys():
        dg = datagolf.get(name, {})
        if dg.get("sg_app"):
            approach_leaders.append((name, dg.get("sg_app"), dg.get("sg_app_rank"), odds.get(name, {}).get("odds") or 9999))
    approach_leaders.sort(key=lambda x: x[1], reverse=True)
    for name, sg_app, rank, odds_val in approach_leaders[:5]:
        context_lines.append(f"  {name}: {sg_app:+.2f} (#{rank} in field) | Odds: {'+' if odds_val >= 0 else ''}{odds_val}")

    # Best putters
    context_lines.append("\n\nTOP PUTTERS (SG Putting):")
    putt_leaders = []
    for name in odds.keys():
        dg = datagolf.get(name, {})
        if dg.get("sg_putt"):
            putt_leaders.append((name, dg.get("sg_putt"), dg.get("sg_putt_rank"), odds.get(name, {}).get("odds") or 9999))
    putt_leaders.sort(key=lambda x: x[1], reverse=True)
    for name, sg_putt, rank, odds_val in putt_leaders[:5]:
        context_lines.append(f"  {name}: {sg_putt:+.2f} (#{rank} in field) | Odds: {'+' if odds_val >= 0 else ''}{odds_val}")

    # Best course history
    context_lines.append("\n\nBEST COURSE HISTORY ADJUSTMENT:")
    hist_leaders = []
    for name in odds.keys():
        dg = datagolf.get(name, {})
        if dg.get("course_history") and dg.get("course_history") > 0.05:
            hist_leaders.append((name, dg.get("course_history"), odds.get(name, {}).get("odds") or 9999))
    hist_leaders.sort(key=lambda x: x[1], reverse=True)
    for name, hist_adj, odds_val in hist_leaders[:5]:
        context_lines.append(f"  {name}: {hist_adj:+.3f} strokes | Odds: {'+' if odds_val >= 0 else ''}{odds_val}")

    # Longshots with good profiles
    context_lines.append("\n\nLONGSHOT ANALYSIS (+5000 or longer with good profiles):")
    longshots = []
    for name, win_odds in players_by_odds:
        if win_odds >= 5000:
            dg = datagolf.get(name, {})
            if dg.get("sg_total") and dg.get("sg_total") > 0.5:
                longshots.append((name, win_odds, dg))

    for name, odds_val, dg in longshots[:5]:
        sg_total = dg.get("sg_total") or 0
        top10_prob = dg.get("top_10_prob") or 0
        context_lines.append(f"  {name}: +{odds_val} | SG Total: {sg_total:+.2f} | Top 10 Prob: {top10_prob:.1f}%")

    return "\n".join(context_lines)


def generate_insights(tournament_name: str, context: str, course_info: dict | None, course_name: str | None = None, champions: dict | None = None, defending_champ: str | None = None) -> dict:
    """Generate AI insights using Claude."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        print("❌ anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)

    # Authoritative venue so the model never names a former host course (e.g. a
    # past Canadian Open at Hamilton G&CC when 2026 is at TPC Toronto).
    venue_line = ""
    if course_name:
        venue_line = (
            f"\nIMPORTANT: This week's {tournament_name} is played at {course_name}. "
            f"If you reference a course by name, use ONLY \"{course_name}\" — never name any "
            f"other golf course or a former host venue.\n"
        )

    champ_line = ""
    if champions:
        wl = "; ".join(f"{y}: {champions[y]}" for y in sorted(champions, reverse=True))
        champ_line = (
            f"\nFACTS — past champions of this event: {wl}. "
            f"The DEFENDING champion is {defending_champ or 'unknown'}. "
            f"Only call {defending_champ or 'that player'} the 'defending champion', and only call a "
            f"player a 'champion'/'winner' of this event if they appear in this list. "
            f"Never invent or infer a title from a player's name.\n"
        )

    course_context = ""
    if course_info:
        course_context = f"""
Course Profile:
- {course_info.get('name')} - Par {course_info.get('characteristics', {}).get('par')}, {course_info.get('characteristics', {}).get('yardage')} yards
- Key skills: {', '.join(course_info.get('key_skills', {}).get('primary', []))}
- Grass: {course_info.get('characteristics', {}).get('grass_type')} fairways, {course_info.get('characteristics', {}).get('green_type')} greens
- Bombers advantage: {course_info.get('scoring_profile', {}).get('bombers_advantage')}
- Notes: {course_info.get('key_skills', {}).get('notes', '')}
"""

    prompt = f"""You are an expert golf betting analyst writing for COSMOS Golf. Analyze the following field data for {tournament_name} and generate betting insights.
{venue_line}{champ_line}
{course_context}

{context}

Generate a JSON response with:
1. "executive_summary" - A compelling 3-4 sentence paragraph that gives the key takeaways for bettors this week. Mention 2-3 specific players and why they stand out. Be specific with numbers. Make it sound authoritative and data-driven.

2. "insights" - An array of 7-10 specific betting insights. Each insight should be an object with:
   - "title" - Short punchy title (4-8 words)
   - "insight" - 1-2 sentence specific insight with data points
   - "players" - Array of 1-3 player names mentioned
   - "category" - One of: "value", "favorite", "longshot", "course_fit", "form", "avoid"

Focus on:
- Players where the model sees more value than the odds suggest
- Course fit advantages (match skills to what the course demands)
- Recent form and strokes gained leaders
- Historical performance at this venue
- Longshots with legitimate profiles
- Any red flags (negative course fit, poor form, etc.)

Be specific with numbers. Don't be generic. Every insight should reference actual data from the analysis.

Return ONLY valid JSON, nothing else."""

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except Exception as e:
        print(f"❌ Error generating insights: {e}")
        return {
            "executive_summary": f"Analysis for {tournament_name} is being prepared.",
            "insights": []
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI betting insights.")
    parser.add_argument("--tournament", type=str, required=True, help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--slug", type=str, default=None, help="Explicit data-file slug (overrides slugified --tournament; matches the schedule slug)")
    args = parser.parse_args()

    slug = args.slug or _slugify(args.tournament)
    year = args.year
    players_data_path = ROOT / "data" / f"{slug}_{year}_players_data.json"
    insights_out_path = ROOT / "data" / f"{slug}_{year}_insights.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    print(f"📊 Generating AI insights for {args.tournament}...")

    # Load data
    data = json.loads(players_data_path.read_text(encoding="utf-8"))
    tournament_name = data.get("tournament", {}).get("name", args.tournament)

    # Load course info
    course_db = load_course_database()
    course_info = get_course_info(course_db, tournament_name)
    if course_info:
        print(f"✓ Found course profile: {course_info.get('name')}")

    # Authoritative venue from the schedule (prevents naming a former host course)
    course_name = get_schedule_course(args.tournament, year) or (course_info.get("name") if course_info else None)
    if course_name:
        print(f"✓ Venue: {course_name}")

    # Authoritative champions (prevents mislabeling the defending champ / inventing titles)
    champions, defending_champ = get_event_champions(slug, year)
    if defending_champ:
        print(f"✓ Defending champion: {defending_champ}")

    # Build analysis context
    print("  Building analysis context...")
    context = build_analysis_context(data, tournament_name, course_info)

    # Generate insights
    print("  Generating AI insights...")
    insights = generate_insights(tournament_name, context, course_info, course_name, champions, defending_champ)

    # Add metadata
    output = {
        "tournament": tournament_name,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": "claude-opus-4-6",
        "executive_summary": insights.get("executive_summary", ""),
        "insights": insights.get("insights", []),
    }

    insights_out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Wrote {insights_out_path}")

    # Print summary
    print(f"\n📝 Executive Summary:\n{output['executive_summary']}")
    print(f"\n💡 Generated {len(output['insights'])} insights")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
