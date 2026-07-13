#!/usr/bin/env python3
"""Generate tournament player table rows from data files. Usage: --tournament "WM Phoenix Open" --year 2026"""

import argparse
import json
import re
from pathlib import Path

# Script lives in historical/wm_phoenix_open/scripts/; project root is 3 levels up
ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")

# ISO 2-letter code mappings
ISO2_TO_FLAG = {
    "US": ("us", "USA"),
    "SE": ("se", "SWE"),
    "KR": ("kr", "KOR"),
    "AU": ("au", "AUS"),
    "ZA": ("za", "RSA"),
    "JP": ("jp", "JPN"),
    "DE": ("de", "GER"),
    "FR": ("fr", "FRA"),
    "IE": ("ie", "IRL"),
    "GB": ("gb", "ENG"),
    "ES": ("es", "ESP"),
    "IT": ("it", "ITA"),
    "NO": ("no", "NOR"),
    "DK": ("dk", "DEN"),
    "BE": ("be", "BEL"),
    "AR": ("ar", "ARG"),
    "CL": ("cl", "CHI"),
    "CO": ("co", "COL"),
    "MX": ("mx", "MEX"),
    "CA": ("ca", "CAN"),
    "CN": ("cn", "CHN"),
    "TW": ("tw", "TPE"),
    "TH": ("th", "THA"),
    "IN": ("in", "IND"),
    "FI": ("fi", "FIN"),
    "AT": ("at", "AUT"),
    "VE": ("ve", "VEN"),
    "NZ": ("nz", "NZL"),
    "PH": ("ph", "PHI"),
    "NL": ("nl", "NED"),
    "PR": ("pr", "PUR"),
}

# OWGR rankings (current as of Feb 2026)
OWGR_RANKINGS = {
    "Scottie Scheffler": 1,
    "Xander Schauffele": 2,
    "Hideki Matsuyama": 5,
    "Collin Morikawa": 6,
    "Viktor Hovland": 8,
    "Cameron Young": 12,
    "Brooks Koepka": 15,
    "Jordan Spieth": 18,
    "Si Woo Kim": 20,
    "Max Homa": 22,
    "Sam Burns": 25,
    "Tony Finau": 28,
    "Wyndham Clark": 30,
    "Tom Kim": 32,
    "Matt Fitzpatrick": 35,
    "Sahith Theegala": 38,
    "Maverick McNealy": 40,
    "Sungjae Im": 42,
    "Rickie Fowler": 45,
    "Corey Conners": 48,
    "J.J. Spaun": 50,
    "Nick Taylor": 52,
    "Akshay Bhatia": 55,
    "Harris English": 58,
    "Min Woo Lee": 60,
    "Kurt Kitayama": 62,
    "Sepp Straka": 65,
    "Daniel Berger": 68,
    "Brian Harman": 70,
    "Keith Mitchell": 75,
    "Billy Horschel": 80,
    "Gary Woodland": 85,
    "Emiliano Grillo": 90,
    "Ben Griffin": 95,
    "Davis Thompson": 98,
    "Christiaan Bezuidenhout": 100,
}


def get_tier(odds: int) -> tuple[str, str]:
    """Get tier label and class from odds."""
    if odds <= 1500:
        return "FAVORITE", "tier-favorite"
    elif odds <= 3500:
        return "CONTENDER", "tier-contender"
    elif odds <= 8000:
        return "VALUE", "tier-value"
    else:
        return "LONGSHOT", "tier-longshot"


def get_result_class(val: str) -> str:
    """Get CSS class for result value."""
    v = str(val).strip().upper()
    if v in ("1", "WIN"):
        return "result-win"
    if v.startswith("T") and v[1:].isdigit():
        pos = int(v[1:])
    elif v.isdigit():
        pos = int(v)
    else:
        if v in ("MC", "CUT", "WD", "DQ"):
            return "result-mc"
        if v in ("NA", "-", "N/A", ""):
            return "result-na"
        return "result-made"

    if pos == 1:
        return "result-win"
    if pos <= 5:
        return "result-top5"
    if pos <= 10:
        return "result-top10"
    if pos <= 25:
        return "result-top25"
    return "result-made"


def format_odds(odds: int) -> str:
    """Format odds integer to display string."""
    if odds >= 0:
        return f"+{odds}"
    return str(odds)


def get_country_flag(name: str, countries: dict) -> tuple[str, str]:
    """Get flag code and country name for a player."""
    country_code = countries.get(name, "US")
    flag_code, display_name = ISO2_TO_FLAG.get(country_code, ("us", "USA"))
    return flag_code, display_name


def main():
    parser = argparse.ArgumentParser(description="Generate tournament table rows")
    parser.add_argument("--tournament", type=str, default="WM Phoenix Open", help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    players_data_path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    storylines_path = ROOT / "data" / f"{slug}_{args.year}_storylines.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    data = json.loads(players_data_path.read_text())

    storylines = {}
    if storylines_path.exists():
        storylines_data = json.loads(storylines_path.read_text())
        storylines = storylines_data.get("storylines", {})

    odds_data = data.get("odds", {})
    historical = data.get("historical", {})
    countries = data.get("countries", {})

    # Build player list sorted by odds
    players = []
    for name, odds_info in odds_data.items():
        win_odds = odds_info.get("odds", 99999)
        players.append({
            "name": name,
            "win_odds": win_odds,
            "top5_odds": odds_info.get("top5"),
            "top10_odds": odds_info.get("top10"),
        })

    players.sort(key=lambda x: x["win_odds"])

    # Generate HTML rows
    rows = []
    for rank, p in enumerate(players, 1):
        name = p["name"]
        win_odds = p["win_odds"]
        top5 = p["top5_odds"]
        top10 = p["top10_odds"]

        # Get historical
        hist = historical.get(name, {})
        h_2025 = hist.get("2025", "NA")
        h_2024 = hist.get("2024", "NA")
        h_2023 = hist.get("2023", "NA")

        # Get tier
        tier_label, tier_class = get_tier(win_odds)

        tournament_name = data.get("tournament", {}).get("name", "this tournament")
        storyline = storylines.get(name, f"{name} looks to make an impact at {tournament_name}.")

        # Get country and flag
        flag_code, country_name = get_country_flag(name, countries)

        # Get OWGR: prefer players_data, then hardcoded fallback
        owgr = data.get("owgr", {}).get(name) or data.get("players", {}).get(name, {}).get("owgr") or OWGR_RANKINGS.get(name, "-")
        if isinstance(owgr, str) and owgr.isdigit():
            owgr = int(owgr)
        owgr_display = f"#{owgr}" if isinstance(owgr, int) else "#-"

        # Recent form placeholder
        form = "Form data pending"

        # Build row
        row = f'''
            <tr>
              <td>{rank}</td>
              <td class="player-cell">
                <div class="player-name"><a href="https://www.google.com/search?q={name.replace(' ', '+')}+PGA+Tour" target="_blank">{name}</a></div>
                <div class="player-country"><img class="flag-img" src="https://flagcdn.com/{flag_code}.svg" width="20" height="15" loading="lazy" alt="{country_name} flag" /> <span class="country-code">{country_name}</span> · <span class="owgr">OWGR {owgr_display}</span></div>
                <span class="tier-badge {tier_class}">{tier_label}</span>
              </td>
              <td class="storyline-cell"><div class="storyline-text">{storyline}</div></td>
              <td class="result-cell"><span class="result-value {get_result_class(h_2025)}">{h_2025}</span></td>
              <td class="result-cell"><span class="result-value {get_result_class(h_2024)}">{h_2024}</span></td>
              <td class="result-cell"><span class="result-value {get_result_class(h_2023)}">{h_2023}</span></td>
              <td class="odds-cell"><span class="odds-value">{format_odds(win_odds)}</span></td>
              <td class="odds-cell"><span class="odds-value">{format_odds(top5) if top5 else "N/A"}</span></td>
              <td class="odds-cell"><span class="odds-value">{format_odds(top10) if top10 else "N/A"}</span></td>
              <td class="recent-cell"><div class="recent-text">{form}</div></td>
            </tr>'''
        rows.append(row)

    # Output the rows
    print("          <tbody>")
    for row in rows:
        print(row)
    print("          </tbody>")


if __name__ == "__main__":
    main()
