#!/usr/bin/env python3
"""
Update OWGR ranks in players_data.json with data from ESPN rankings.

Usage:
    python scripts/update_owgr_from_espn.py --players-data data/wm_phoenix_open_2026_players_data.json
    python scripts/update_owgr_from_espn.py --tournament "WM Phoenix Open" --year 2026
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")

# OWGR rankings from ESPN (as of Jan 2026)
ESPN_OWGR = {
    "Scottie Scheffler": 1,
    "Rory McIlroy": 2,
    "Tommy Fleetwood": 3,
    "Xander Schauffele": 4,
    "Russell Henley": 5,
    "Robert MacIntyre": 6,
    "J.J. Spaun": 7,
    "Ben Griffin": 8,
    "Justin Thomas": 9,
    "Justin Rose": 10,
    "Harris English": 11,
    "Sepp Straka": 12,
    "Alex Noren": 13,
    "Viktor Hovland": 14,
    "Hideki Matsuyama": 15,
    "Keegan Bradley": 16,
    "Chris Gotterup": 17,
    "Ludvig Aberg": 18,  # "Ludvig Åberg" in original
    "Collin Morikawa": 19,
    "Cameron Young": 20,
    "Tyrrell Hatton": 21,
    "Matt Fitzpatrick": 22,
    "Maverick McNealy": 23,
    "Aaron Rai": 24,
    "Sam Burns": 25,
    "Shane Lowry": 26,
    "Patrick Cantlay": 27,
    "Bryson DeChambeau": 28,
    "Marco Penge": 29,
    "Ryan Gerard": 30,
    "Corey Conners": 31,
    "Andrew Novak": 32,
    "Max Greyserman": 33,
    "Michael Brennan": 34,
    "Kristoffer Reitan": 35,
    "Brian Harman": 36,
    "Kurt Kitayama": 37,
    "Michael Kim": 38,
    "Sami Valimaki": 39,  # "Sami Välimäki" in original
    "Rasmus Hojgaard": 40,  # "Rasmus Højgaard" in original
    "Ryan Fox": 41,
    "Si Woo Kim": 42,
    "Taylor Pendrith": 43,
    "Patrick Reed": 44,
    "Min Woo Lee": 45,
    "Johnny Keefer": 46,
    "Rasmus Neergaard-Petersen": 47,
    "Sungjae Im": 48,
    "Wyndham Clark": 49,
    "Sam Stevens": 50,
    "Nick Taylor": 51,
    "Akshay Bhatia": 52,
    "Daniel Berger": 53,
    "Harry Hall": 54,
    "Nicolas Echavarria": 55,  # "Nico Echavarria" in original
    "J.T. Poston": 56,
    "Billy Horschel": 57,
    "Matt McCarty": 58,
    "Jayden Schaper": 59,
    "Laurie Canter": 60,
    "Thomas Detry": 61,
    "Jason Day": 62,
    "Jacob Bridgeman": 63,
    "Garrick Higgo": 64,
    "Lucas Glover": 65,
    "Thriston Lawrence": 66,
    "Dan Brown": 67,  # Could be "Daniel Brown"
    "Adam Scott": 68,
    "Bud Cauley": 69,
    "Max McGreevy": 70,
    "Rico Hoey": 71,
    "Michael Thorbjornsen": 72,
    "Denny McCarthy": 73,
    "Brian Campbell": 74,
    "Tom McKibbin": 75,
    "Matt Wallace": 76,
    "Chris Kirk": 77,
    "Adrien Saddier": 78,
    "Jordan Spieth": 79,
    "John Parry": 80,
    "Nicolai Hojgaard": 81,  # "Nicolai Højgaard" in original
    "Christiaan Bezuidenhout": 82,
    "Rickie Fowler": 83,
    "Aldrich Potgieter": 84,
    "Jhonattan Vegas": 85,
    "Haotong Li": 86,
    "Patrick Rodgers": 87,
    "Davis Riley": 88,
    "Jon Rahm": 89,
    "Pierceson Coody": 90,
    "Jordan Smith": 91,
    "Matthias Schmid": 92,  # Could be "Matti Schmid"
    "Kevin Yu": 93,
    "Jake Knapp": 94,
    "Thorbjorn Olesen": 95,  # "Thorbjørn Olesen" in original
    "Mackenzie Hughes": 96,
    "Shaun Norris": 97,
    "Davis Thompson": 98,
    "David Puig": 99,
    "Neal Shipley": 100,
}

# Name variations to try matching
NAME_VARIATIONS = {
    "Daniel Brown": ["Dan Brown"],
    "Johnny Keefer": ["John Keefer"],
}


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    return name.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Update OWGR in players_data from ESPN rankings")
    parser.add_argument("--players-data", type=Path, help="Path to players_data.json")
    parser.add_argument("--tournament", type=str, help="Tournament name (e.g. WM Phoenix Open)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    if args.players_data is not None:
        path = Path(args.players_data)
        if not path.is_absolute():
            path = ROOT / path
    else:
        if not args.tournament:
            print("❌ Provide --players-data or --tournament")
            return 1
        slug = _slugify(args.tournament)
        path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"

    if not path.exists():
        print(f"❌ Missing {path}")
        return 1

    # Load player data
    players_data = json.loads(path.read_text(encoding="utf-8"))
    players = players_data.get("players", {})

    print(f"📊 Updating OWGR ranks from ESPN rankings (Top 100)")
    print(f"🔄 Matching {len(ESPN_OWGR)} ranked players to {len(players)} players in field...\\n")

    updated_count = 0
    matched_players = set()

    # First pass: exact name matches
    for player_name in players.keys():
        norm_name = normalize_name(player_name)
        if norm_name in ESPN_OWGR:
            rank = ESPN_OWGR[norm_name]
            players[player_name]["owgr"] = str(rank)
            updated_count += 1
            matched_players.add(norm_name)
            print(f"  ✓ {player_name:35s} → OWGR #{rank}")

    # Second pass: name variations
    for player_name in players.keys():
        if normalize_name(player_name) in matched_players:
            continue

        for canonical, variations in NAME_VARIATIONS.items():
            if player_name in variations and canonical in ESPN_OWGR:
                rank = ESPN_OWGR[canonical]
                players[player_name]["owgr"] = str(rank)
                updated_count += 1
                matched_players.add(canonical)
                print(f"  ✓ {player_name:35s} → OWGR #{rank} (matched as {canonical})")

    # Save updated data
    players_data["players"] = players
    path.write_text(
        json.dumps(players_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n✅ Complete! Updated {updated_count} players with OWGR ranks")
    print(f"💾 Wrote {path}")

    # Report unmatched ESPN rankings
    unmatched_espn = set(ESPN_OWGR.keys()) - matched_players
    if unmatched_espn:
        print(f"\\n⚠️  {len(unmatched_espn)} ESPN rankings not matched to field:")
        for name in sorted(unmatched_espn, key=lambda x: ESPN_OWGR[x])[:10]:
            print(f"     - {name} (#{ESPN_OWGR[name]})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
