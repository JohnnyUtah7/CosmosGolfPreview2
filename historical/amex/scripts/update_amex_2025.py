#!/usr/bin/env python3
"""
Update American Express 2025 results from web-scraped leaderboard.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLAYERS_DATA = ROOT / "data" / "amex_2026_players_data.json"

# 2025 American Express leaderboard (from PGA Tour website)
AMEX_2025_RESULTS = {
    "Sepp Straka": "1",
    "Justin Thomas": "2",
    "Justin Lower": "T3",
    "Jason Day": "T3",
    "Patrick Cantlay": "T5",
    "Charley Hoffman": "T5",
    "Camilo Villegas": "T7",
    "Taylor Moore": "T7",
    "Ben Griffin": "T7",
    "Max Greyserman": "T7",
    "Alex Smalley": "11",
    "Nick Taylor": "T12",
    "J.T. Poston": "T12",
    "Will Zalatoris": "T12",
    "Frankie Capan III": "T12",
    "Beau Hossler": "T12",
    "Mark Hubbard": "T12",
    "Trey Mullinax": "T18",
    "Kevin Roy": "T18",
    "Cameron Davis": "T18",
    "Harry Hall": "T21",
    "Jacob Bridgeman": "T21",
    "Doug Ghim": "T21",
    "Rickie Fowler": "T21",
    "Billy Horschel": "T21",
    "Keith Mitchell": "T21",
    "Daniel Berger": "T21",
    "Ben Kohles": "T21",
    "Vincent Norrman": "T29",
    "Carson Young": "T29",
    "Tom Hoge": "T29",
    "J.J. Spaun": "T29",
    "Sam Burns": "T29",
    "Lanto Griffin": "T34",
    "Quade Cummins": "T34",
    "Lee Hodges": "T34",
    "Victor Perez": "T34",
    "Ryan Palmer": "T34",
    "Harry Higgs": "T34",
    "Nick Dunlap": "T34",
    "Chris Kirk": "T34",
    "Brice Garnett": "T34",
    "Ricky Castillo": "T43",
    "Matt Kuchar": "T43",
    "Sam Ryder": "T43",
    "Michael Kim": "T43",
    "Ryo Hisatsune": "T43",
    "Matteo Manassero": "T43",
    "Rikuya Hoshino": "T43",
    "Harris English": "T43",
    "Matti Riedel": "T51",
    "Sam Stevens": "T51",
    "Brandt Snedeker": "T51",
    "Si Woo Kim": "T51",
    "Brian Campbell": "T51",
    "Ryan Gerard": "T51",
    "Davis Thompson": "T51",
    "Mackenzie Hughes": "T58",
    "Kurt Kitayama": "T58",
    "Rico Hoey": "T58",
    "Taylor Montgomery": "T58",
    "Kris Ventura": "T58",
    "Alejandro Tosti": "T58",
    "Jake Paul": "T64",
    "Vince Whaley": "T64",
    "Joe Highsmith": "T66",
    "Will Gordon": "T66",
    "Eric Cole": "T68",
    "Mac Meissner": "T68",
    "Patrick Rodgers": "70",
    "Chez Reavie": "71",

    # Missed cut
    "Norman Xiong": "MC",
    "Joel Dahmen": "MC",
    "Luke List": "MC",
    "Kevin Yu": "MC",
    "Chandler Phillips": "MC",
    "Michael Thorbjornsen": "MC",
    "Zach Johnson": "MC",
    "Kevin Lee": "MC",
    "Jake Knapp": "MC",
    "Francesco Molinari": "MC",
    "Isaiah Salinda": "MC",
    "Tony Finau": "MC",
    "Chris Gotterup": "MC",
    "Tobias Widing": "MC",
    "Andrew Putnam": "MC",
    "Patrick Kizzire": "MC",
    "Takumi Kanaya": "MC",
    "Henrik Norlander": "MC",
    "Tom Kim": "MC",
    "Chan Kim": "MC",
    "Sungjae Im": "MC",
    "Jesper Svensson": "MC",
    "Nicolas Echavarria": "MC",
    "Peter Malnati": "MC",
    "Matt McCarty": "MC",
    "Jhonattan Vegas": "MC",
    "Ben Brown": "MC",
    "John Pak": "MC",
    "Adam Hadwin": "MC",
    "Ben Martin": "MC",
    "Aaron Baddeley": "MC",
    "Greyson Sigg": "MC",
    "Wyndham Clark": "MC",
    "Zac Blair": "MC",
    "Nick Hardy": "MC",
    "Matthias Schmid": "MC",
    "Emiliano Grillo": "MC",
    "Adam Svensson": "MC",
    "Brian Harman": "MC",
    "Aldrich Potgieter": "MC",
    "Max McGreevy": "MC",
    "Patrick Peterson": "MC",
    "Davis Walker": "MC",
    "Christiaan Bezuidenhout": "MC",
    "Lucas Glover": "MC",
    "Erik van Rooyen": "MC",
    "Jackson Suber": "MC",

    # Withdrawals
    "Martin Andersen": "WD",
    "David Lipsky": "WD",
}


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    # Remove common suffixes
    name = re.sub(r'\s+(Jr\.|Sr\.|III|II|IV)$', '', name, flags=re.IGNORECASE)
    # Convert to lowercase for comparison
    return name.strip().lower()


def match_player(leaderboard_name: str, field_players: list) -> str:
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

    # Load player data
    players_data = json.loads(PLAYERS_DATA.read_text(encoding="utf-8"))
    players = players_data.get("players", {})
    field_players = list(players.keys())

    print(f"📊 Updating American Express 2025 results")
    print(f"🔄 Matching {len(AMEX_2025_RESULTS)} leaderboard entries to {len(field_players)} players...\n")

    updated_count = 0
    matched_count = 0

    for leaderboard_name, result in AMEX_2025_RESULTS.items():
        matched_player = match_player(leaderboard_name, field_players)

        if matched_player:
            matched_count += 1
            current_value = players[matched_player].get("history_2025", "NA")

            if current_value != result:
                players[matched_player]["history_2025"] = result
                updated_count += 1
                print(f"  {matched_player:35s} | 2025: {current_value:6s} → {result:6s} ✓")

    # Save updated data
    players_data["players"] = players
    PLAYERS_DATA.write_text(
        json.dumps(players_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n✅ Complete!")
    print(f"   Matched {matched_count}/{len(AMEX_2025_RESULTS)} players from leaderboard")
    print(f"   Updated {updated_count} historical results")
    print(f"   💾 Wrote {PLAYERS_DATA}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
