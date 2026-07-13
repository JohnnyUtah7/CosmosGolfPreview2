#!/usr/bin/env python3
"""
Fetch complete American Express leaderboards for 2023-2025 and update player history.

This is more efficient than querying each player individually.
"""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLAYERS_DATA = ROOT / "data" / "amex_2026_players_data.json"


def fetch_amex_leaderboard(year: int, client) -> dict[str, str]:
    """Fetch complete leaderboard for The American Express in a given year."""
    try:
        prompt = f"""Find the complete final leaderboard for The American Express PGA Tour tournament from {year}.

The American Express is held in January in La Quinta, California.

Return the results as a simple list of player names and their finish positions, one per line:
PlayerName: Position

Examples:
Jon Rahm: 1
Max Greyserman: T7
Adam Schenk: T7
Patrick Cantlay: MC
Sam Burns: WD

Include:
- All players who made the cut (top ~70 players)
- Players who missed the cut (MC)
- Players who withdrew (WD)

Format each line as: PlayerName: Position
Use "T7" format for tied positions, "MC" for missed cut, "WD" for withdrew.
"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text.strip()

        # Parse the leaderboard into a dictionary
        leaderboard = {}
        for line in result.split('\n'):
            line = line.strip()
            if ':' not in line:
                continue

            # Split on first colon only
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue

            player_name = parts[0].strip()
            position = parts[1].strip()

            # Normalize position
            position = position.replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
            position = position.strip()

            # Validate position format
            if position.upper() in ["MC", "WD", "DQ"] or re.match(r'^T?\d+$', position, re.IGNORECASE):
                leaderboard[player_name] = position.upper() if position.upper() in ["MC", "WD", "DQ"] else position

        return leaderboard

    except Exception as e:
        print(f" ERROR fetching {year} leaderboard: {e}")
        return {}


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    # Remove common suffixes
    name = re.sub(r'\s+(Jr\.|Sr\.|III|II|IV)$', '', name, flags=re.IGNORECASE)
    # Convert to lowercase for comparison
    return name.strip().lower()


def match_player(leaderboard_name: str, field_players: list[str]):
    """Try to match a leaderboard name to a player in the field."""
    lb_norm = normalize_name(leaderboard_name)

    # Try exact match first
    for player in field_players:
        if normalize_name(player) == lb_norm:
            return player

    # Try last name match
    lb_last = lb_norm.split()[-1] if lb_norm.split() else ""
    if lb_last:
        for player in field_players:
            player_last = normalize_name(player).split()[-1] if normalize_name(player).split() else ""
            if player_last == lb_last:
                return player

    return None


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
    field_players = list(players.keys())

    print(f"📊 Fetching American Express leaderboards for 2023-2025")
    print(f"🔄 This will make 3 API calls (one per year)...\n")

    years = [2025, 2024, 2023]
    all_leaderboards = {}

    # Fetch leaderboards for each year
    for year in years:
        print(f"Fetching {year} leaderboard...", end=" ", flush=True)
        leaderboard = fetch_amex_leaderboard(year, client)
        all_leaderboards[year] = leaderboard
        print(f"✓ ({len(leaderboard)} players found)")

    print(f"\n📝 Matching leaderboard results to field of {len(field_players)} players...\n")

    updated_count = 0
    matched_count = 0

    for player_name in sorted(field_players):
        player_info = players[player_name]
        player_updated = False

        for year in years:
            field_name = f"history_{year}"
            current_value = player_info.get(field_name, "NA")
            leaderboard = all_leaderboards[year]

            # Try to find player in leaderboard
            matched_player = match_player(player_name, list(leaderboard.keys()))

            if matched_player:
                new_value = leaderboard[matched_player]
                matched_count += 1

                if new_value != current_value:
                    players[player_name][field_name] = new_value
                    updated_count += 1
                    player_updated = True
                    print(f"  {player_name:35s} | {year}: {current_value:6s} → {new_value:6s} ✓")

    # Save updated data
    players_data["players"] = players
    PLAYERS_DATA.write_text(
        json.dumps(players_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n✅ Complete!")
    print(f"   Matched {matched_count} player-year combinations")
    print(f"   Updated {updated_count} historical results")
    print(f"   💾 Wrote {PLAYERS_DATA}")

    # Show summary by year
    print(f"\n📈 Summary by year:")
    for year in years:
        lb_count = len(all_leaderboards[year])
        print(f"   {year}: {lb_count} players in leaderboard")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
