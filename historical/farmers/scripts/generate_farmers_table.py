#!/usr/bin/env python3
"""Generate Farmers Insurance Open player table rows from data files - Best in class version."""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent  # historical/farmers
PROJECT_ROOT = Path(__file__).parent.parent.parent  # repo root
PLAYERS_DATA = ROOT / "data" / "farmers_insurance_open_2026_players_data.json"
STORYLINES = ROOT / "data" / "farmers_insurance_open_2026_storylines.json"
COUNTRY_CACHE = PROJECT_ROOT / "data" / "player_country_cache.json"
RECENT_FORM = ROOT / ".." / "amex" / "data" / "amex_2026_recent_form.json"

# Country code to flag mapping (ISO 3166-1 alpha-2 for flagcdn.com)
COUNTRY_FLAGS = {
    "USA": ("us", "USA"),
    "SWE": ("se", "SWE"),
    "KOR": ("kr", "KOR"),
    "AUS": ("au", "AUS"),
    "RSA": ("za", "RSA"),
    "JPN": ("jp", "JPN"),
    "GER": ("de", "GER"),
    "FRA": ("fr", "FRA"),
    "IRL": ("ie", "IRL"),
    "ENG": ("gb-eng", "ENG"),
    "SCO": ("gb-sct", "SCO"),
    "ESP": ("es", "ESP"),
    "ITA": ("it", "ITA"),
    "NOR": ("no", "NOR"),
    "DEN": ("dk", "DEN"),
    "BEL": ("be", "BEL"),
    "ARG": ("ar", "ARG"),
    "CHI": ("cl", "CHI"),
    "COL": ("co", "COL"),
    "MEX": ("mx", "MEX"),
    "CAN": ("ca", "CAN"),
    "WAL": ("gb-wls", "WAL"),
    "CHN": ("cn", "CHN"),
    "TWN": ("tw", "TPE"),
    "TPE": ("tw", "TPE"),
    "THA": ("th", "THA"),
    "IND": ("in", "IND"),
    "FIN": ("fi", "FIN"),
    "AUT": ("at", "AUT"),
    "VEN": ("ve", "VEN"),
    "NZL": ("nz", "NZL"),
    "PHI": ("ph", "PHI"),
    "NED": ("nl", "NED"),
}

# Known OWGR rankings (approximate current rankings)
OWGR_RANKINGS = {
    "Xander Schauffele": 2,
    "Ludvig Aberg": 4,
    "Hideki Matsuyama": 5,
    "Collin Morikawa": 6,
    "Patrick Cantlay": 8,
    "Sungjae Im": 10,
    "Cameron Young": 12,
    "Keegan Bradley": 14,
    "Will Zalatoris": 15,
    "Si Woo Kim": 18,
    "Max Homa": 20,
    "Tony Finau": 22,
    "Jason Day": 25,
    "Wyndham Clark": 28,
    "Tom Hoge": 30,
    "Justin Rose": 32,
    "Harris English": 35,
    "Adam Scott": 38,
    "Sahith Theegala": 40,
    "Maverick McNealy": 42,
    "J.J. Spaun": 45,
    "Taylor Pendrith": 48,
    "Akshay Bhatia": 50,
    "Aaron Rai": 52,
    "Rasmus Hojgaard": 55,
    "Nicolai Hojgaard": 58,
    "Alex Noren": 60,
    "Christiaan Bezuidenhout": 62,
    "Brooks Koepka": 65,
    "Billy Horschel": 68,
    "Seamus Power": 70,
    "Davis Thompson": 75,
    "Keith Mitchell": 80,
    "Denny McCarthy": 85,
    "Matt Kuchar": 90,
    "Gary Woodland": 95,
    "Emiliano Grillo": 100,
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


def get_country_flag(name: str, country_cache: dict) -> tuple[str, str]:
    """Get flag code and country name for a player."""
    country_code = country_cache.get(name, "USA")

    # Handle special mappings
    flag_code, display_name = COUNTRY_FLAGS.get(country_code, ("us", "USA"))
    return flag_code, display_name


def main():
    # Load all data
    data = json.loads(PLAYERS_DATA.read_text())
    storylines_data = json.loads(STORYLINES.read_text())

    # Load country cache
    country_cache = {}
    if COUNTRY_CACHE.exists():
        country_cache = json.loads(COUNTRY_CACHE.read_text())

    # Load recent form data
    recent_form = {}
    if RECENT_FORM.exists():
        recent_form = json.loads(RECENT_FORM.read_text())

    odds_data = data.get("odds", {})
    historical = data.get("historical", {})
    storylines = storylines_data.get("storylines", {})

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

        # Get storyline
        storyline = storylines.get(name, f"{name} looks to make an impact at Torrey Pines.")

        # Get country and flag
        flag_code, country_name = get_country_flag(name, country_cache)

        # Get OWGR ranking
        owgr = OWGR_RANKINGS.get(name, "-")
        owgr_display = f"#{owgr}" if isinstance(owgr, int) else "#-"

        # Get recent form
        form = recent_form.get(name, "")
        if not form or form == "—" or form.startswith("I don't have"):
            form = "Form data pending"

        # Clean up form text - replace bullet with proper bullet
        form = form.replace("•", "•").replace(" · ", " • ")

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
