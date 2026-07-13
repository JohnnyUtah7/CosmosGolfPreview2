#!/usr/bin/env python3
"""
Apply OWGR (Official World Golf Ranking) to WM Phoenix Open 2026 players_data.json.

Merges ESPN OWGR (top 100), assembler fallback rankings, and name variations
so the HTML can display OWGR for as many players as possible.

Usage:
    python scripts/apply_owgr_to_wm_phoenix.py
"""

import json
from pathlib import Path

# Script lives in historical/wm_phoenix_open/scripts/; project root is 3 levels up
ROOT = Path(__file__).resolve().parent.parent.parent.parent
PLAYERS_DATA = ROOT / "data" / "wm_phoenix_open_2026_players_data.json"

# ESPN OWGR top 100 (Jan 2026) – primary source
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
    "Ludvig Aberg": 18,
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
    "Sami Valimaki": 39,
    "Rasmus Hojgaard": 40,
    "Ryan Fox": 41,
    "Si Woo Kim": 42,
    "Taylor Pendrith": 43,
    "Patrick Reed": 44,
    "Min Woo Lee": 45,
    "Rasmus Neergaard-Petersen": 47,
    "Sungjae Im": 48,
    "Wyndham Clark": 49,
    "Sam Stevens": 50,
    "Nick Taylor": 51,
    "Akshay Bhatia": 52,
    "Daniel Berger": 53,
    "Harry Hall": 54,
    "Nicolas Echavarria": 55,
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
    "Nicolai Hojgaard": 81,
    "Christiaan Bezuidenhout": 82,
    "Rickie Fowler": 83,
    "Aldrich Potgieter": 84,
    "Haotong Li": 86,
    "Patrick Rodgers": 87,
    "Davis Riley": 88,
    "Jon Rahm": 89,
    "Pierceson Coody": 90,
    "Jordan Smith": 91,
    "Matthias Schmid": 92,
    "Kevin Yu": 93,
    "Jake Knapp": 94,
    "Thorbjorn Olesen": 95,
    "Mackenzie Hughes": 96,
    "Shaun Norris": 97,
    "Davis Thompson": 98,
    "David Puig": 99,
    "Neal Shipley": 100,
}

# Name variations: WM Phoenix field name -> rank (ESPN uses different spelling)
OWGR_ALIASES = {
    "John Keefer": 46,   # ESPN: Johnny Keefer
    "Daniel Brown": 67, # ESPN: Dan Brown
}

# Fallback: assembler OWGR (players in WM field not in ESPN top 100)
ASSEMBLER_OWGR = {
    "Brooks Koepka": 15,
    "Tony Finau": 28,
    "Wyndham Clark": 30,
    "Tom Kim": 32,
    "Sahith Theegala": 38,
    "Sungjae Im": 42,
    "Nick Taylor": 52,
    "Akshay Bhatia": 52,
    "Harry Hall": 54,
    "Nicolas Echavarria": 55,
    "J.T. Poston": 56,
    "Billy Horschel": 57,
    "Matt McCarty": 58,
    "Nick Dunlap": 58,
    "Charley Hoffman": 115,
    "Emiliano Grillo": 90,
    "Gary Woodland": 85,
    "Keith Mitchell": 75,
    "Joel Dahmen": 120,
    "S.H. Kim": 125,
    "Stephan Jaeger": 102,
    "Mac Meissner": 195,
    "Ryo Hisatsune": 105,
    "Eric Cole": 108,
    "Alex Smalley": 112,
    "Adam Schenk": 118,
    "Erik Van Rooyen": 122,
    "Patton Kizzire": 128,
    "Webb Simpson": 130,
    "Vince Whaley": 135,
    "Matthias Schmid": 92,
    "William Mouw": 140,
    "Michael Brennan": 34,
    "Austin Eckroat": 145,
    "Chad Ramey": 150,
    "Austin Smotherman": 155,
    "Tom Hoge": 160,
    "Chandler Phillips": 165,
    "Aldrich Potgieter": 84,
    "Mark Hubbard": 170,
    "Adrien Dumont De Chassart": 175,
    "Takumi Kanaya": 180,
    "Kevin Roy": 185,
    "Karl Vilips": 190,
    "Matthieu Pavon": 195,
    "Keita Nakajima": 200,
    "Zecheng Dou": 205,
    "Chandler Blanchet": 210,
    "Sudarshan Yellamaraju": 215,
    "Emilio Gonzalez": 220,
    "Zach Bauchou": 225,
    "Cameron Davis": 230,
    "Brice Garnett": 235,
    "John Vanderlaan": 240,
    "Seung Taek Lee": 245,
    "Hank Lebioda": 250,
    "Kensei Hirata": 255,
    "Christo Lamprecht": 260,
    "Danny Walker": 265,
    "Davis Chatfield": 270,
    "Joe Highsmith": 275,
    "Jeffrey Kang": 280,
    "Peter Malnati": 285,
    "Rafael Campos": 290,
    "Thomas Avant": 300,
}


def main() -> int:
    if not PLAYERS_DATA.exists():
        print(f"❌ Missing {PLAYERS_DATA}")
        return 1

    data = json.loads(PLAYERS_DATA.read_text(encoding="utf-8"))
    odds_names = set(data.get("odds", {}).keys())

    # Build owgr: prefer ESPN, then alias (name variation), then assembler
    owgr = {}
    for name in odds_names:
        rank = (
            ESPN_OWGR.get(name)
            or OWGR_ALIASES.get(name)
            or ASSEMBLER_OWGR.get(name)
        )
        if rank is not None:
            owgr[name] = rank

    data["owgr"] = owgr
    data["data_sources"]["owgr"] = "ESPN/OWGR + assembler fallback"
    data["data_sources"]["owgr_applied_at"] = "2026-02-02"

    PLAYERS_DATA.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    missing = len(odds_names) - len(owgr)
    print(f"✅ Applied OWGR to {len(owgr)} players in WM Phoenix field")
    print(f"   Missing OWGR: {missing} players")
    print(f"💾 Wrote {PLAYERS_DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
