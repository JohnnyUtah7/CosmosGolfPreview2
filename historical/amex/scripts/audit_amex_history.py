#!/usr/bin/env python3
"""
Audit and update American Express tournament history for all players (2023-2025).

Fetches accurate historical results and updates players_data.json.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLAYERS_DATA = ROOT / "data" / "amex_2026_players_data.json"


def get_amex_history_for_player(player_name: str, player_country: str, year: int, client) -> str:
    """Get American Express tournament result for a specific year using Claude."""
    try:
        prompt = f"""What was {player_name}'s ({player_country}) finish at The American Express golf tournament in {year}?

IMPORTANT:
- The American Express is a PGA Tour event held in January in La Quinta, California
- It was previously called the CareerBuilder Challenge (2017), Humana Challenge (2012-2016), Bob Hope Classic (before 2012)
- Return ONLY the finish position in this exact format:
  - "T7" for tied 7th
  - "4" or "4th" for solo 4th
  - "MC" for missed cut
  - "WD" for withdrew
  - "NA" if player did NOT play in the tournament that year

Do NOT return:
- "I don't have access"
- Any explanations or additional text
- Just the finish position or NA

Examples of correct responses:
- "T7"
- "MC"
- "NA"
- "12"
"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text.strip()

        # Clean up formatting
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]

        # Remove any extra text
        result = result.split('\n')[0].strip()

        # Normalize the result
        result_upper = result.upper()
        if result_upper == "NA" or "NOT" in result_upper or "DID NOT" in result_upper or "DIDN'T" in result_upper:
            return "NA"

        # Remove ordinal suffixes (1st -> 1, 2nd -> 2, etc.)
        result = result.replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")

        return result.strip() if result.strip() else "NA"

    except Exception as e:
        print(f" ERROR: {e}")
        return "NA"


def main() -> int:
    if not PLAYERS_DATA.exists():
        print(f"❌ Missing {PLAYERS_DATA}")
        return 1

    # Initialize Anthropic client
    try:
        from anthropic import Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ ANTHROPIC_API_KEY not set")
            return 1
        client = Anthropic(api_key=api_key)
    except ImportError:
        print("❌ anthropic package not installed")
        return 1

    # Load player data
    players_data = json.loads(PLAYERS_DATA.read_text(encoding="utf-8"))
    players = players_data.get("players", {})

    print(f"📊 Auditing American Express history for {len(players)} players")
    print(f"🔄 Checking results for 2023, 2024, 2025...\n")

    years = [2025, 2024, 2023]
    updated_count = 0
    total_checks = 0

    for i, (player_name, player_info) in enumerate(sorted(players.items()), 1):
        country = player_info.get("country", "USA")
        print(f"[{i}/{len(players)}] {player_name:35s} ({country:3s})")

        player_updated = False
        for year in years:
            field_name = f"history_{year}"
            current_value = player_info.get(field_name, "NA")

            # Fetch the actual result
            print(f"  {year}: {current_value:6s} → ", end="", flush=True)
            actual_result = get_amex_history_for_player(player_name, country, year, client)

            if actual_result != current_value:
                players[player_name][field_name] = actual_result
                updated_count += 1
                player_updated = True
                print(f"{actual_result:6s} ✓ (updated)")
            else:
                print(f"{actual_result:6s} (no change)")

            total_checks += 1

        # Save progress every 10 players
        if i % 10 == 0:
            players_data["players"] = players
            PLAYERS_DATA.write_text(
                json.dumps(players_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"  💾 Progress saved ({updated_count} updates so far)\n")

    # Final save
    players_data["players"] = players
    PLAYERS_DATA.write_text(
        json.dumps(players_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n✅ Complete!")
    print(f"   Checked {total_checks} player-year combinations")
    print(f"   Updated {updated_count} historical results")
    print(f"   💾 Wrote {PLAYERS_DATA}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
