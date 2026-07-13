#!/usr/bin/env python3
"""
Generate AI analysis and recommendations for Round 1 3-ball matchups (and optional post-cut summary).

Reads matchups JSON + players_data (for SG, course history). Outputs matchup_insights.json
with a summary and per-group pick + analysis. Run inject_matchup_insights_into_html.py
after to embed into wm_phoenix_open_2026.html.

Usage:
    python scripts/generate_matchup_ai_insights.py --tournament "WM Phoenix Open" --year 2026
    python scripts/generate_matchup_ai_insights.py --matchups data/wm_phoenix_open_2026_matchups.json --players-data data/wm_phoenix_open_2026_players_data.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load ANTHROPIC_API_KEY (and other secrets) from .env, matching sibling AI scripts
from dotenv import load_dotenv
load_dotenv()


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def build_matchup_context(
    three_balls: list,
    players_data: dict,
    max_groups: int = 20,
) -> str:
    """Build context string for AI: each group with player odds and datagolf stats."""
    datagolf = players_data.get("datagolf", {})
    historical = players_data.get("historical", {})

    lines = [
        "Round 1 — 3-Ball matchups. For each group, recommend ONE pick (who wins the 3-ball) with confidence and short analysis.",
        "",
        "=== GROUPS (Group #, Tee Time, Hole, then Player / Odds / SG Total / Course History) ===",
    ]

    for g in three_balls[:max_groups]:
        grp = g.get("group", 0)
        teetime = (g.get("teetime") or "").split(" ")[-1][:5] if g.get("teetime") else ""
        hole = g.get("start_hole", "")
        p1 = g.get("player_1_name", "")
        p2 = g.get("player_2_name", "")
        p3 = g.get("player_3_name", "")
        o1 = g.get("player_1_odds", "")
        o2 = g.get("player_2_odds", "")
        o3 = g.get("player_3_odds", "")

        def line_for(name: str, odds: str) -> str:
            dg = datagolf.get(name, {})
            sg = dg.get("sg_total")
            hist = historical.get(name, {})
            h = " | ".join([f"{y}:{v}" for y, v in sorted(hist.items()) if v and v != "NA"]) if hist else "—"
            sg_str = f"SG {sg:+.2f}" if sg is not None else "SG —"
            return f"    {name}  Odds: {odds}  {sg_str}  History: {h}"

        lines.append(f"\nGroup {grp}  Tee: {teetime}  Hole: {hole}")
        lines.append(line_for(p1, o1))
        lines.append(line_for(p2, o2))
        lines.append(line_for(p3, o3))

    return "\n".join(lines)


def generate_matchup_insights(
    tournament_name: str,
    context: str,
    course_name: str = "TPC Scottsdale",
) -> dict:
    """Call Claude to get summary + per-group pick and analysis."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        print("❌ anthropic not installed. Run: pip install anthropic")
        sys.exit(1)

    prompt = f"""You are an expert golf betting analyst for COSMOS Golf. Analyze the following Round 1 three-ball matchups for {tournament_name} at {course_name}.

{context}

Return a JSON object with:

1. "summary" — 2–4 sentences for Round 1 3-balls: overall theme (e.g. favor SG/putting, course history, or value vs odds). Include a brief note on post-cut/weekend matchups if relevant (e.g. "For weekend head-to-heads, lean same course-fit and form angles.").

2. "round_1_3ball" — An array of objects, one per group you're asked to analyze. Each object must have:
   - "group" (number)
   - "pick" (exact player name as in the list)
   - "confidence" (one of: "Strong", "Lean", "Value")
   - "analysis" (1–2 sentences: why this pick, cite SG/course history/odds value)

Only include groups you have a clear opinion on. Skip groups where it's a coin flip. Be specific with numbers.

Return ONLY valid JSON, no markdown or extra text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"summary": "Matchup analysis will be updated before Round 1.", "round_1_3ball": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI matchup insights for 3-balls.")
    parser.add_argument("--tournament", type=str, default="WM Phoenix Open")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--matchups", type=Path, help="Path to matchups JSON")
    parser.add_argument("--players-data", type=Path, help="Path to players_data JSON")
    parser.add_argument("--max-groups", type=int, default=20, help="Max 3-ball groups to analyze")
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    matchups_path = args.matchups or ROOT / "data" / f"{slug}_{args.year}_matchups.json"
    players_path = args.players_data or ROOT / "data" / f"{slug}_{args.year}_players_data.json"

    if not matchups_path.exists():
        print(f"❌ Missing {matchups_path}")
        return 1
    if not players_path.exists():
        print(f"❌ Missing {players_path}")
        return 1

    matchups = json.loads(matchups_path.read_text(encoding="utf-8"))
    players_data = json.loads(players_path.read_text(encoding="utf-8"))
    three_balls = matchups.get("daily_three_balls") or matchups.get("three_balls") or []

    if not three_balls:
        print("❌ No daily_three_balls in matchups JSON")
        return 1

    print(f"📊 Generating matchup AI insights for {args.tournament} ({len(three_balls)} 3-ball groups)...")
    context = build_matchup_context(three_balls, players_data, max_groups=args.max_groups)
    raw = generate_matchup_insights(
        args.tournament,
        context,
        course_name=players_data.get("tournament", {}).get("course", "TPC Scottsdale"),
    )

    out = {
        "tournament": args.tournament,
        "generated_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": raw.get("summary", ""),
        "round_1_3ball": raw.get("round_1_3ball", []),
    }

    out_path = ROOT / "data" / f"{slug}_{args.year}_matchup_insights.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Wrote {out_path}")
    print(f"   Summary: {out['summary'][:120]}...")
    print(f"   Picks: {len(out['round_1_3ball'])} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
