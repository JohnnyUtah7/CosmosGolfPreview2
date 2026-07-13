#!/usr/bin/env python3
"""
Generate AI-powered storylines for any tournament using Claude API (WM Phoenix style prompt).

Usage:
    python scripts/generate_wm_phoenix_storylines.py --tournament "WM Phoenix Open" --year 2026
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Script lives in historical/wm_phoenix_open/scripts/; project root is 3 levels up
ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _slugify(name: str) -> str:
    slug = name.lower()
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

    # Get country
    ctx["country"] = data.get("countries", {}).get(player_name)

    # Get historical WM Phoenix finishes
    hist = data.get("historical", {}).get(player_name, {})
    ctx["wm_2025"] = hist.get("2025")
    ctx["wm_2024"] = hist.get("2024")
    ctx["wm_2023"] = hist.get("2023")

    return ctx


def generate_content_batch(players_batch: list, data: dict) -> dict:
    """Generate storylines for a batch of players using Claude."""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        print("❌ anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Could not initialize Anthropic client: {e}")
        sys.exit(1)

    # Build a comprehensive prompt for the batch
    player_contexts = []
    for player in players_batch:
        context = get_player_context(player, data)

        player_contexts.append(f"""
Player: {player}
- Win Odds: {context.get('win_odds', 'N/A')}
- Top 5 Odds: {context.get('top5_odds', 'N/A')}
- Top 10 Odds: {context.get('top10_odds', 'N/A')}
- Country: {context.get('country', 'N/A')}
- WM Phoenix 2025: {context.get('wm_2025', 'NA')}
- WM Phoenix 2024: {context.get('wm_2024', 'NA')}
- WM Phoenix 2023: {context.get('wm_2023', 'NA')}
""")

    prompt = f"""You are a professional golf writer creating betting preview content for the WM Phoenix Open 2026.

Tournament Context:
- WM Phoenix Open is played at TPC Scottsdale (Stadium Course) in Scottsdale, Arizona
- February 5-8, 2026
- Par 71, 7,261 yards
- Known for the rowdy par-3 16th hole "The Coliseum" with stadium seating
- Desert target golf course requiring accuracy off the tee
- Bermuda grass greens that get slick and fast
- Thomas Detry is the defending champion (won 2025)
- Course favors precise iron play, good scramblers, and those who handle pressure
- Scottie Scheffler won in 2023 and had T3 in 2024
- Nick Taylor won in 2024 in a dramatic playoff

For each player below, write:
1. A compelling 2-3 sentence "Why They Could Win" storyline

Writing Guidelines:
- Focus on SPECIFIC course history at WM Phoenix (wins, top 5s, top 10s) if they have it
- Connect their game/strengths to what TPC Scottsdale demands
- Use concrete data points (finishes, specific tournaments, recent form)
- Mention their 2025, 2024, 2023 finishes if relevant (1 = win, T3 = tied 3rd, MC = missed cut)
- Avoid generic phrases like "could surprise" or "don't overlook"
- If they have no WM Phoenix history, focus on current form + game fit for the desert layout
- Make it concise but substantive - no fluff
- Be specific about why their game suits TPC Scottsdale

Tone: Professional betting preview, data-driven, specific, engaging

{''.join(player_contexts)}

Return your response as a JSON object with this structure:
{{
  "Player Name": {{
    "storyline": "2-3 sentence why they could win"
  }}
}}

Only include JSON in your response, nothing else."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response
        content = response.content[0].text
        # Try to find JSON in the response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        return result

    except Exception as e:
        print(f"❌ Error generating content for batch: {e}")
        # Return empty results for this batch
        return {player: {"storyline": f"{player} looks to make an impact at TPC Scottsdale."} for player in players_batch}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI storylines (Claude, WM Phoenix style) for any tournament")
    parser.add_argument("--tournament", type=str, default="WM Phoenix Open", help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    players_data_path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    storylines_out_path = ROOT / "data" / f"{slug}_{args.year}_storylines.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    data = json.loads(players_data_path.read_text(encoding="utf-8"))
    tournament_name = data.get("tournament", {}).get("name", args.tournament)

    players = list(data.get("odds", {}).keys())
    print(f"📊 Generating AI storylines for {len(players)} players using Claude ({tournament_name})...")

    storylines = {}

    batch_size = 10
    for i in range(0, len(players), batch_size):
        batch = players[i:i+batch_size]
        print(f"  Processing batch {i//batch_size + 1}/{(len(players)-1)//batch_size + 1} ({len(batch)} players)...", end=" ", flush=True)

        try:
            results = generate_content_batch(batch, data)

            for player in batch:
                if player in results:
                    storylines[player] = results[player].get("storyline", f"{player} looks to make an impact.")
                else:
                    context = get_player_context(player, data)
                    storylines[player] = f"{player} looks to contend with odds of {context.get('win_odds', 'TBD')}."

            print("✓")

        except Exception as e:
            print(f"❌ {e}")
            for player in batch:
                context = get_player_context(player, data)
                storylines[player] = f"{player} looks to contend with odds of {context.get('win_odds', 'TBD')}."

    from datetime import datetime, timezone
    output = {
        "storylines": storylines,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": "claude-sonnet-4",
        "tournament": f"{tournament_name} {args.year}"
    }

    storylines_out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Wrote {storylines_out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
