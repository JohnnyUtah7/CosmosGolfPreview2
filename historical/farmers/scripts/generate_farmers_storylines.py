#!/usr/bin/env python3
"""
Generate AI-powered storylines for Farmers Insurance Open 2026.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
PLAYERS_DATA = ROOT / "data" / "farmers_insurance_open_2026_players_data.json"
STORYLINES_OUT = ROOT / "data" / "farmers_insurance_open_2026_storylines.json"


def get_player_context(player_name: str, data: dict) -> dict:
    """Extract all relevant context for a player."""
    ctx = {"name": player_name}

    odds_data = data.get("odds", {}).get(player_name, {})
    ctx["win_odds"] = odds_data.get("odds")
    ctx["top5_odds"] = odds_data.get("top5")
    ctx["top10_odds"] = odds_data.get("top10")

    hist = data.get("historical", {}).get(player_name, {})
    ctx["farmers_2025"] = hist.get("2025", "NA")
    ctx["farmers_2024"] = hist.get("2024", "NA")
    ctx["farmers_2023"] = hist.get("2023", "NA")

    return ctx


def generate_content_batch(players_batch: list, data: dict) -> dict:
    """Generate storylines for a batch of players using Claude."""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        print("Error: anthropic package not installed")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing Anthropic client: {e}")
        sys.exit(1)

    player_contexts = []
    for player in players_batch:
        context = get_player_context(player, data)

        player_contexts.append(f"""
Player: {player}
- Win Odds: +{context.get('win_odds', 'N/A')}
- Top 5 Odds: +{context.get('top5_odds', 'N/A')}
- Top 10 Odds: +{context.get('top10_odds', 'N/A')}
- Farmers 2025: {context.get('farmers_2025', 'NA')}
- Farmers 2024: {context.get('farmers_2024', 'NA')}
- Farmers 2023: {context.get('farmers_2023', 'NA')}
""")

    # Add news context
    news_context = """
CURRENT NEWS & STORYLINES TO INCORPORATE:
- Brooks Koepka is making his PGA Tour return after leaving LIV Golf. He's returning under the new Returning Member Program after 2+ years away. This is a huge storyline.
- Xander Schauffele is making his 2026 PGA Tour debut after winning the Baycurrent Classic in his last start. He's the favorite and a local San Diego native.
- Harris English is the defending champion looking to become the first player since Tiger Woods to repeat at Torrey Pines.
- Jason Day is a two-time Farmers champion (2015, 2018) returning to a course where he's had great success.
- J.J. Spaun is the reigning U.S. Open champion.
- This is the final year of Farmers Insurance as the tournament sponsor.
- Featured grouping: Harris English + Xander Schauffele + J.J. Spaun
- Featured grouping: Jason Day + Justin Rose + Hideki Matsuyama
"""

    prompt = f"""You are a professional golf writer creating betting preview content for the 2026 Farmers Insurance Open at Torrey Pines.

Tournament Context:
- Torrey Pines Golf Course in La Jolla, California (South and North courses)
- $9.6 million purse, 500 FedEx Cup points
- Historically favors long hitters who can handle Poa annua greens
- The South Course is one of the toughest on Tour (hosts U.S. Opens)
- January 29 - February 1, 2026

{news_context}

For each player below, write:
1. A compelling 2-3 sentence "Why They Could Win" storyline (MUST be creative and engaging)
2. A brief recent form analysis (1 sentence, 15-25 words)

Writing Guidelines:
- Be CREATIVE and engaging - these should read like sports journalism, not AI-generated content
- Reference the NEWS above when relevant (Koepka's return, English defending, Schauffele's home course, etc.)
- Focus on SPECIFIC course history at Torrey Pines if they have it
- Connect their strengths to what Torrey Pines demands (length off the tee, iron play, putting on Poa)
- Use concrete data points (past finishes, wins, world ranking)
- For players without Torrey Pines history, focus on current form + game fit
- Make each storyline unique and interesting - avoid generic templates
- Include personality and storytelling

{''.join(player_contexts)}

Return your response as a JSON object with this structure:
{{
  "Player Name": {{
    "storyline": "2-3 sentence creative why they could win",
    "form_analysis": "1 sentence recent form analysis"
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
        print(f"Error generating content: {e}")
        return {player: {"storyline": f"Competing at the Farmers Insurance Open.", "form_analysis": "-"} for player in players_batch}


def main() -> int:
    if not PLAYERS_DATA.exists():
        print(f"Missing {PLAYERS_DATA}")
        return 1

    data = json.loads(PLAYERS_DATA.read_text(encoding="utf-8"))

    players = list(data.get("odds", {}).keys())
    print(f"Generating AI storylines for {len(players)} players...")

    storylines = {}
    form_analyses = {}

    # Process in batches of 10
    batch_size = 10
    for i in range(0, len(players), batch_size):
        batch = players[i:i+batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(players)-1)//batch_size + 1
        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} players)...", end=" ", flush=True)

        try:
            results = generate_content_batch(batch, data)

            for player in batch:
                if player in results:
                    storylines[player] = results[player].get("storyline", f"Competing at the Farmers Insurance Open.")
                    form_analyses[player] = results[player].get("form_analysis", "-")
                else:
                    context = get_player_context(player, data)
                    storylines[player] = f"Competing at the Farmers Insurance Open with odds of +{context.get('win_odds', 'TBD')}."
                    form_analyses[player] = "-"

            print("Done")

        except Exception as e:
            print(f"Error: {e}")
            for player in batch:
                storylines[player] = f"Competing at the Farmers Insurance Open."
                form_analyses[player] = "-"

    output = {
        "tournament": "Farmers Insurance Open",
        "year": 2026,
        "storylines": storylines,
        "recent_form_analyses": form_analyses,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model": "claude-sonnet-4"
    }

    STORYLINES_OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote storylines to {STORYLINES_OUT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
