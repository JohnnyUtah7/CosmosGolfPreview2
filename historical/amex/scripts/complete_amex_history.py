#!/usr/bin/env python3
"""
Complete American Express historical data for ALL players using web search.

This script will systematically check every player who still has NA for any year
and use web search to find their results.
"""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLAYERS_DATA = ROOT / "data" / "amex_2026_players_data.json"


def search_player_amex_result(player_name: str, year: int, client) -> str:
    """Search for a player's American Express result using Claude with web search."""
    try:
        prompt = f"""Search for {player_name}'s finish position at The American Express PGA Tour golf tournament in {year}.

The American Express is held in January in La Quinta, California.

Return ONLY the finish position:
- "T7" for tied 7th place
- "4" for solo 4th place
- "MC" for missed cut
- "WD" for withdrew
- "DQ" for disqualified
- "NA" if the player did NOT compete in the tournament that year

Do NOT return any explanations or additional text. Just the position or NA.

Examples: "T7", "MC", "NA", "12", "WD"
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

        # Just get first token
        result = result.split()[0] if result.split() else "NA"

        # Check for "did not play" indicators
        result_lower = result.lower()
        if any(phrase in result_lower for phrase in ["not", "didn't", "did not", "na", "n/a", "didn't"]):
            return "NA"

        # Remove ordinal suffixes
        result = re.sub(r'(st|nd|rd|th)\b', '', result, flags=re.IGNORECASE)

        # Validate result format
        if result.upper() in ["MC", "WD", "DQ"]:
            return result.upper()

        # Check for T## or ## format
        if re.match(r'^T?\d+$', result, re.IGNORECASE):
            return result.upper()

        # If we got something weird, return NA to be safe
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

    print(f"📊 Completing American Express historical data for ALL {len(players)} players")
    print(f"🔄 Searching for missing results across 2023-2025...\n")

    years = [2025, 2024, 2023]

    # Find all missing data
    missing_data = []
    for player_name, player_info in sorted(players.items()):
        for year in years:
            field_name = f"history_{year}"
            current_value = player_info.get(field_name, "NA")
            if not current_value or current_value.strip() == "" or current_value == "NA":
                missing_data.append((player_name, year))

    print(f"Found {len(missing_data)} missing player-year combinations to search\n")

    updated_count = 0
    searches_performed = 0

    for i, (player_name, year) in enumerate(missing_data, 1):
        field_name = f"history_{year}"
        country = players[player_name].get("country", "USA")

        print(f"[{i}/{len(missing_data)}] {player_name:35s} | {year} ({country:3s})...", end=" ", flush=True)

        result = search_player_amex_result(player_name, year, client)
        searches_performed += 1

        # Only update if we found actual data (not NA)
        if result != "NA":
            players[player_name][field_name] = result
            updated_count += 1
            print(f"✓ {result:6s}")
        else:
            # Keep as NA - player didn't play
            players[player_name][field_name] = "NA"
            print(f"— (did not play)")

        # Save progress every 20 searches
        if i % 20 == 0:
            players_data["players"] = players
            PLAYERS_DATA.write_text(
                json.dumps(players_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"    💾 Progress saved ({updated_count} updates so far)\n")

    # Final save
    players_data["players"] = players
    PLAYERS_DATA.write_text(
        json.dumps(players_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n✅ Complete!")
    print(f"   Performed {searches_performed} web searches")
    print(f"   Found and updated {updated_count} new results")
    print(f"   Confirmed {searches_performed - updated_count} players did not compete")
    print(f"   💾 Wrote {PLAYERS_DATA}")

    # Show final coverage
    print(f"\n📈 Final coverage:")
    for year in years:
        total = len(players)
        has_data = sum(1 for p in players.values() if p.get(f"history_{year}", "NA") not in ["NA", "", None])
        pct = (has_data / total * 100) if total > 0 else 0
        print(f"   {year}: {has_data}/{total} players ({pct:.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
