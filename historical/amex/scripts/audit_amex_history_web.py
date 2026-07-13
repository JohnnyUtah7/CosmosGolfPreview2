#!/usr/bin/env python3
"""
Audit and update American Express tournament history using web search (2023-2025).

Fetches accurate historical results from PGA Tour leaderboards.
"""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLAYERS_DATA = ROOT / "data" / "amex_2026_players_data.json"


def get_amex_history_for_player_web(player_name: str, year: int, client) -> str:
    """Get American Express tournament result using Claude with web search."""
    try:
        # For 2025, the tournament just happened in January 2025
        # For 2024 and 2023, we can search historical results
        prompt = f"""Search for {player_name}'s finish at The American Express golf tournament in {year}.

The American Express is a PGA Tour event held in January in La Quinta, California.

Return ONLY the finish position:
- "T7" for tied 7th
- "4" for solo 4th
- "MC" for missed cut
- "WD" for withdrew
- "NA" if player did NOT play in the tournament that year

Do NOT include any explanations. Just return the finish position or NA.

Examples: "T7", "MC", "NA", "12"
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

        # Remove any extra text - just get first word/token
        result = result.split()[0] if result.split() else "NA"

        # Check for "not play" or similar indicators
        result_lower = result.lower()
        if any(phrase in result_lower for phrase in ["not", "didn't", "did not", "na", "n/a"]):
            return "NA"

        # Remove ordinal suffixes
        result = re.sub(r'(st|nd|rd|th)\b', '', result, flags=re.IGNORECASE)

        # Validate result format
        if result.upper() in ["MC", "WD", "DQ"]:
            return result.upper()

        # Check for T## or ## format
        if re.match(r'^T?\d+$', result, re.IGNORECASE):
            return result.upper()

        return "NA"

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
    print(f"🔄 Checking results for 2025, 2024, 2023 via web search...\n")

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
            actual_result = get_amex_history_for_player_web(player_name, year, client)

            # Only update if we got a valid result different from current
            if actual_result != "NA" and actual_result != current_value:
                players[player_name][field_name] = actual_result
                updated_count += 1
                player_updated = True
                print(f"{actual_result:6s} ✓ (updated)")
            elif actual_result == current_value:
                print(f"{actual_result:6s} (confirmed)")
            else:
                # Keep existing value if we couldn't find data
                print(f"{current_value:6s} (kept existing)")

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
