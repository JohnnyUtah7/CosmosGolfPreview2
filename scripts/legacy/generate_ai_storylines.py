#!/usr/bin/env python3
"""
Generate AI-powered storylines using Gemini API for any tournament.

Usage:
    python scripts/generate_ai_storylines.py --tournament "WM Phoenix Open" --year 2026
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai

# Script lives in scripts/legacy/; project root is 2 levels up
ROOT = Path(__file__).resolve().parent.parent.parent

# Configure Gemini (key from env; remove hardcoded key in production)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")

def get_player_context(player_name: str, data: dict) -> dict:
    """Extract all relevant context for a player."""
    ctx = {"name": player_name}

    # Get odds
    odds_data = data.get("odds", {}).get(player_name, {})
    ctx["win_odds"] = odds_data.get("odds")
    ctx["top5_odds"] = odds_data.get("top5")
    ctx["top10_odds"] = odds_data.get("top10")

    # Get player info
    player_info = data.get("players", {}).get(player_name, {})
    ctx["country"] = player_info.get("country")
    ctx["owgr"] = player_info.get("owgr")

    # Get historical finishes at this event
    hist = data.get("historical", {}).get(player_name, {})
    ctx["hist_2025"] = hist.get("2025")
    ctx["hist_2024"] = hist.get("2024")
    ctx["hist_2023"] = hist.get("2023")

    return ctx


def generate_storyline(player_name: str, context: dict, recent_form: str, tournament_name: str) -> str:
    """Generate a compelling storyline using Gemini."""

    prompt = f"""You are a professional golf writer creating betting preview content. Write a compelling 2-3 sentence "Why They Could Win" storyline for {player_name} at {tournament_name}.

Player Context:
- Win Odds: {context.get('win_odds', 'N/A')}
- Top 5 Odds: {context.get('top5_odds', 'N/A')}
- Top 10 Odds: {context.get('top10_odds', 'N/A')}
- OWGR: {context.get('owgr', 'N/A')}
- Country: {context.get('country', 'N/A')}
- Event 2025: {context.get('hist_2025', 'NA')}
- Event 2024: {context.get('hist_2024', 'NA')}
- Event 2023: {context.get('hist_2023', 'NA')}
- Recent Form: {recent_form}

Writing Guidelines:
1. Focus on SPECIFIC course history at this event (wins, top 5s, top 10s)
2. Mention recent form ONLY if it's from the past 3 months and relevant
3. Connect their game/strengths to what this course demands
4. Use concrete data points (finishes, world ranking, specific tournaments)
5. Avoid generic phrases like "could surprise" or "don't overlook"
6. If they have no history at this event, focus on current form + game fit
7. Make it concise but substantive - no fluff

Tone: Professional betting preview, data-driven, specific, engaging

Write ONLY the 2-3 sentence storyline, nothing else:"""

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)

    return response.text.strip()


def analyze_recent_form(player_name: str, recent_form: str, context: dict) -> str:
    """Generate insightful recent form analysis using Gemini."""

    if not recent_form or recent_form == "—" or "odds" in recent_form.lower() or "predictions" in recent_form.lower():
        return "—"

    prompt = f"""You are a professional golf analyst. Analyze this recent tournament result for {player_name}:

Recent Result: {recent_form}
Player OWGR: {context.get('owgr', 'N/A')}

Write a single concise sentence (15-25 words) that provides context/insight about this result. Options:
- If it's a top finish: "Coming off a T4 at the Sony Open last week — iron play was elite all weekend."
- If it's a MC: "Missed cut at Waialae but historically bounces back strong after early stumbles."
- If it's been quiet: "Quiet since [date] but known to play in spurts when conditions suit his game."
- If it's trending: "Third straight top-20 finish — form trending in exactly the right direction."

Be specific, insightful, and connect it to momentum or context that matters for betting. No generic phrases.

Write ONLY the analysis sentence:"""

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)

    return response.text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI storylines with Gemini for any tournament")
    parser.add_argument("--tournament", type=str, required=True, help="Tournament name (e.g. WM Phoenix Open)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    players_data_path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    storylines_out_path = ROOT / "data" / f"{slug}_{args.year}_storylines.json"
    recent_form_path = ROOT / "data" / f"{slug}_{args.year}_recent_form.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    data = json.loads(players_data_path.read_text(encoding="utf-8"))
    tournament_name = data.get("tournament", {}).get("name", args.tournament)

    recent_form_data = {}
    if recent_form_path.exists():
        try:
            recent_form_data = json.loads(recent_form_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  Could not load recent form data: {e}")

    players = list(data.get("odds", {}).keys())
    print(f"📊 Generating AI storylines for {len(players)} players ({tournament_name})...")

    storylines = {}
    form_analyses = {}

    for i, player in enumerate(players, 1):
        print(f"  [{i}/{len(players)}] {player}...", end=" ", flush=True)

        try:
            context = get_player_context(player, data)
            recent_form = recent_form_data.get(player, "—")

            storyline = generate_storyline(player, context, recent_form, tournament_name)
            storylines[player] = storyline

            time.sleep(12)

            form_analysis = analyze_recent_form(player, recent_form, context)
            form_analyses[player] = form_analysis

            time.sleep(12)

            print("✓")

        except Exception as e:
            print(f"❌ {e}")
            context = get_player_context(player, data)
            storylines[player] = f"Competing at {tournament_name} with odds of {context.get('win_odds', 'TBD')}."
            form_analyses[player] = "—"

    from datetime import datetime, timezone
    output = {
        "storylines": storylines,
        "recent_form_analyses": form_analyses,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": "gemini-1.5-flash"
    }

    storylines_out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Wrote {storylines_out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
