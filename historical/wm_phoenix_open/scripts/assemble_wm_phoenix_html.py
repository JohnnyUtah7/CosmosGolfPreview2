#!/usr/bin/env python3
"""Assemble tournament HTML (WM Phoenix Open style layout). Supports any tournament via --tournament/--year."""

import argparse
import json
import re
from pathlib import Path

# Script lives in historical/wm_phoenix_open/scripts/; project root is 4 levels up
ROOT = Path(__file__).resolve().parent.parent.parent.parent
HISTORICAL_WM = ROOT / "historical" / "wm_phoenix_open"

# Set by main() from --tournament / --year (WM data and output live in historical folder)
PLAYERS_DATA = HISTORICAL_WM / "data" / "wm_phoenix_open_2026_players_data.json"
STORYLINES = HISTORICAL_WM / "data" / "wm_phoenix_open_2026_storylines.json"
RECENT_FORM = HISTORICAL_WM / "data" / "wm_phoenix_open_2026_recent_form.json"
OUTPUT = HISTORICAL_WM / "wm_phoenix_open_2026.html"


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
    "SCO": ("gb-sct", "SCO"),
    "ENG": ("gb-eng", "ENG"),
    "NIR": ("gb-nir", "NIR"),
    "WAL": ("gb-wls", "WAL"),
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
    "Thomas Detry": 45,
    "Michael Kim": 110,
    "Charley Hoffman": 115,
    "Nick Dunlap": 58,
    "Justin Thomas": 14,
    "Keegan Bradley": 35,
    "Patrick Cantlay": 10,
    "Ludvig Aberg": 4,
    "Jason Day": 42,
    "Adam Scott": 55,
    "Shane Lowry": 25,
    "Tommy Fleetwood": 22,
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


def generate_table_rows(data, storylines, recent_form):
    """Generate HTML table rows."""
    odds_data = data.get("odds", {})
    historical = data.get("historical", {})
    countries = data.get("countries", {})
    owgr_data = data.get("owgr", {})

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
        storyline = storylines.get(name, f"{name} looks to make an impact at TPC Scottsdale.")

        # Get country and flag
        flag_code, country_name = get_country_flag(name, countries)

        # Get OWGR ranking: prefer JSON (owgr), then hardcoded fallback
        owgr = owgr_data.get(name) or OWGR_RANKINGS.get(name, "-")
        owgr_display = f"#{owgr}" if isinstance(owgr, int) else "#-"

        # Recent form from data
        form = recent_form.get(name, "—")
        if not form or form == "—":
            form = "Form data pending"

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

    return "\n".join(rows)


HTML_TEMPLATE = '''<!--
SHOPIFY EMBED INSTRUCTIONS:
1. Upload these images to Shopify Files (Settings > Files):
   - COSMOS_Golf-Dec-Logo_001.png
   - wm_phoenix_course.jpg (TPC Scottsdale Stadium Course image)

2. Copy the image URLs from Shopify Files

3. Replace the image URLs below with your Shopify file URLs

4. In Shopify Admin:
   - Go to Online Store > Pages > Add page
   - Or add this to an existing page using a Custom HTML section
   - Paste this entire code block
-->

<div class="cosmos-betting-preview">
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <style>
    .cosmos-betting-preview {
      --bg: #ffffff;
      --text: #000000;
      --border: #d9d9d9;
      --odds-green: #0a7a3f;
      --finish-win: #0a7a3f;
      --finish-top5: #b07d00;
      --finish-top10: #005bbb;
      --finish-top25: #0077b6;
      --finish-made: #000000;
      --finish-bad: #b00020;
    }

    .cosmos-betting-preview, .cosmos-betting-preview * {
      box-sizing: border-box;
    }

    .cosmos-betting-preview {
      font-family: 'Rajdhani', sans-serif;
      background: var(--bg);
      color: var(--text);
      width: 100%;
      padding: 0;
      margin: 0;
      overflow-x: hidden;
    }

    .cosmos-betting-preview header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 16px;
      padding: 18px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--bg);
    }

    .cosmos-betting-preview .mission-tag {
      font-family: 'Share Tech Mono', monospace;
      font-size: 12px;
      letter-spacing: 2px;
      opacity: 0.75;
      margin-bottom: 8px;
    }

    .cosmos-betting-preview h1 {
      font-family: 'Orbitron', sans-serif;
      font-size: 30px;
      font-weight: 900;
      letter-spacing: 1px;
      margin: 0 0 6px 0;
    }

    .cosmos-betting-preview .subtitle {
      font-size: 16px;
      opacity: 0.8;
    }

    .cosmos-betting-preview .logo-container {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 10px;
      margin-left: auto;
      text-align: right;
    }

    .cosmos-betting-preview .logo-container img {
      height: 88px;
      width: auto;
      filter: none;
    }

    .cosmos-betting-preview .pdf-button {
      font-family: 'Orbitron', sans-serif;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid var(--text);
      background: var(--text);
      color: var(--bg);
      cursor: pointer;
      line-height: 1;
      user-select: none;
    }

    .cosmos-betting-preview .pdf-button:hover {
      background: var(--bg);
      color: var(--text);
    }

    .cosmos-betting-preview .pdf-button:focus-visible {
      outline: 2px solid var(--text);
      outline-offset: 2px;
    }

    .cosmos-betting-preview .container {
      max-width: 1680px;
      margin: 0 auto;
      padding: 16px;
    }

    .cosmos-betting-preview .event-info {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      padding: 14px;
      margin: 16px 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--bg);
    }

    .cosmos-betting-preview .info-block {
      text-align: center;
      padding: 10px 8px;
    }

    .cosmos-betting-preview .info-label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      opacity: 0.6;
      margin-bottom: 4px;
    }

    .cosmos-betting-preview .info-value {
      font-family: 'Orbitron', sans-serif;
      font-size: 20px;
      font-weight: 700;
    }

    .cosmos-betting-preview .course-image {
      margin: 18px 0;
      border-radius: 8px;
      overflow: hidden;
    }

    .cosmos-betting-preview .course-image img {
      width: 100%;
      height: auto;
      display: block;
    }

    .cosmos-betting-preview .section-header {
      margin: 24px 0 12px;
    }

    .cosmos-betting-preview .section-header h2 {
      font-family: 'Orbitron', sans-serif;
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 1px;
      margin: 0 0 8px 0;
    }

    .cosmos-betting-preview .section-line {
      height: 2px;
      background: var(--text);
      width: 60px;
    }

    .cosmos-betting-preview .crew-picks {
      margin: 16px 0 24px;
    }

    .cosmos-betting-preview .crew-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }

    .cosmos-betting-preview .crew-card {
      display: flex;
      align-items: flex-start;
      gap: 14px;
      padding: 16px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--bg);
    }

    .cosmos-betting-preview .crew-photo {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      object-fit: cover;
      flex-shrink: 0;
    }

    .cosmos-betting-preview .crew-name {
      font-family: 'Orbitron', sans-serif;
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 8px;
    }

    .cosmos-betting-preview .crew-picks-list {
      list-style: none;
      padding: 0;
      margin: 0;
      font-size: 13px;
    }

    .cosmos-betting-preview .crew-picks-list li {
      margin-bottom: 4px;
    }

    .cosmos-betting-preview .pick-label {
      font-weight: 600;
      margin-right: 6px;
    }

    .cosmos-betting-preview .pick-odds {
      opacity: 0.7;
      font-size: 12px;
      margin-left: 4px;
    }

    .cosmos-betting-preview .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      padding: 12px;
      margin-bottom: 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 12px;
    }

    .cosmos-betting-preview .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .cosmos-betting-preview .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }

    .cosmos-betting-preview .tab-navigation {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }

    .cosmos-betting-preview .tab-button {
      font-family: 'Orbitron', sans-serif;
      font-size: 13px;
      font-weight: 600;
      padding: 10px 18px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg);
      color: var(--text);
      cursor: pointer;
      transition: all 0.2s;
    }

    .cosmos-betting-preview .tab-button:hover {
      border-color: var(--text);
    }

    .cosmos-betting-preview .tab-button.active {
      background: var(--text);
      color: var(--bg);
      border-color: var(--text);
    }

    .cosmos-betting-preview .tab-content {
      display: none;
    }

    .cosmos-betting-preview .tab-content.active {
      display: block;
    }

    .cosmos-betting-preview .table-container {
      overflow-x: auto;
      margin: 12px 0;
    }

    .cosmos-betting-preview table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }

    .cosmos-betting-preview th,
    .cosmos-betting-preview td {
      padding: 12px 10px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }

    .cosmos-betting-preview th {
      font-family: 'Orbitron', sans-serif;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      background: var(--bg);
      position: sticky;
      top: 0;
      z-index: 10;
    }

    .cosmos-betting-preview th.center {
      text-align: center;
    }

    .cosmos-betting-preview tr:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    .cosmos-betting-preview .player-cell {
      min-width: 180px;
    }

    .cosmos-betting-preview .player-name {
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 4px;
    }

    .cosmos-betting-preview .player-name a {
      color: inherit;
      text-decoration: none;
    }

    .cosmos-betting-preview .player-name a:hover {
      text-decoration: underline;
    }

    .cosmos-betting-preview .player-country {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      opacity: 0.75;
      margin-bottom: 6px;
    }

    .cosmos-betting-preview .flag-img {
      border-radius: 2px;
      vertical-align: middle;
    }

    .cosmos-betting-preview .country-code {
      font-weight: 600;
    }

    .cosmos-betting-preview .owgr {
      font-family: 'Share Tech Mono', monospace;
      font-size: 11px;
    }

    .cosmos-betting-preview .tier-badge {
      display: inline-block;
      font-family: 'Orbitron', sans-serif;
      font-size: 9px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }

    .cosmos-betting-preview .tier-favorite {
      background: #ffd700;
      color: #000;
    }

    .cosmos-betting-preview .tier-contender {
      background: #c0c0c0;
      color: #000;
    }

    .cosmos-betting-preview .tier-value {
      background: #cd7f32;
      color: #fff;
    }

    .cosmos-betting-preview .tier-longshot {
      background: #333;
      color: #fff;
    }

    .cosmos-betting-preview .storyline-cell {
      min-width: 280px;
      max-width: 400px;
    }

    .cosmos-betting-preview .storyline-text {
      font-size: 13px;
      line-height: 1.5;
      color: #333;
    }

    .cosmos-betting-preview .result-cell {
      text-align: center;
      min-width: 60px;
    }

    .cosmos-betting-preview .result-value {
      display: inline-block;
      font-family: 'Orbitron', sans-serif;
      font-size: 13px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 4px;
      min-width: 44px;
    }

    .cosmos-betting-preview .result-win {
      background: var(--finish-win);
      color: #fff;
    }

    .cosmos-betting-preview .result-top5 {
      background: var(--finish-top5);
      color: #fff;
    }

    .cosmos-betting-preview .result-top10 {
      background: var(--finish-top10);
      color: #fff;
    }

    .cosmos-betting-preview .result-top25 {
      background: var(--finish-top25);
      color: #fff;
    }

    .cosmos-betting-preview .result-made {
      background: #e8e8e8;
      color: var(--finish-made);
    }

    .cosmos-betting-preview .result-mc {
      background: #ffebee;
      color: var(--finish-bad);
    }

    .cosmos-betting-preview .result-na {
      background: #f5f5f5;
      color: #999;
    }

    .cosmos-betting-preview .odds-cell {
      text-align: center;
      min-width: 70px;
    }

    .cosmos-betting-preview .odds-value {
      font-family: 'Orbitron', sans-serif;
      font-size: 14px;
      font-weight: 600;
      color: var(--odds-green);
    }

    .cosmos-betting-preview .recent-cell {
      min-width: 200px;
      max-width: 320px;
    }

    .cosmos-betting-preview .recent-text {
      font-size: 12px;
      line-height: 1.5;
      color: #555;
    }

    .cosmos-betting-preview footer {
      text-align: center;
      padding: 24px 16px;
      margin-top: 24px;
      border-top: 1px solid var(--border);
    }

    .cosmos-betting-preview .footer-text {
      font-family: 'Orbitron', sans-serif;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 2px;
      margin-bottom: 8px;
    }

    .cosmos-betting-preview .data-source {
      font-size: 12px;
      opacity: 0.6;
    }

    @media (max-width: 768px) {
      .cosmos-betting-preview h1 {
        font-size: 22px;
      }

      .cosmos-betting-preview .logo-container img {
        max-width: 200px;
      }

      .cosmos-betting-preview table {
        font-size: 12px;
      }

      .cosmos-betting-preview th,
      .cosmos-betting-preview td {
        padding: 8px 6px;
      }

      .cosmos-betting-preview .storyline-cell {
        min-width: 200px;
      }

      .cosmos-betting-preview .recent-cell {
        min-width: 160px;
      }
    }

    @media print {
      .cosmos-betting-preview .pdf-button {
        display: none;
      }

      .cosmos-betting-preview .container {
        padding-left: 28px;
        padding-right: 28px;
      }
    }
  </style>

  <header>
    <div class="header-left">
      <div class="mission-tag">// MISSION BRIEFING - FEBRUARY 5-8, 2026</div>
      <h1>WM Phoenix Open</h1>
      <div class="subtitle">TPC Scottsdale (Stadium Course) · Scottsdale, Arizona · February 5-8, 2026</div>
    </div>
    <div class="logo-container">
      <img src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/COSMOS_Golf-Dec-Logo_001.png?v=1768281723" alt="COSMOS Golf" style="max-width: 420px;">
      <button class="pdf-button" type="button" onclick="downloadPdf()" title="Opens print dialog — choose "Save as PDF"">Download PDF</button>
    </div>
  </header>

  <div class="container">
    <div class="section-header">
      <h2>Cosmos Crew Picks</h2>
      <div class="section-line"></div>
    </div>

    <div class="crew-picks">
      <div class="crew-grid">

        <div class="crew-card">
          <img class="crew-photo" src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/miller.jpg?v=1768439524" alt="Miller">
          <div>
            <div class="crew-name">Miller</div>
            <ul class="crew-picks-list">
              <li><span class="pick-label">Win</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 5</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 10</span> TBD <span class="pick-odds">TBD</span></li>
            </ul>
          </div>
        </div>

        <div class="crew-card">
          <img class="crew-photo" src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kham.jpg?v=1768439565" alt="Kevin">
          <div>
            <div class="crew-name">Kevin</div>
            <ul class="crew-picks-list">
              <li><span class="pick-label">Win</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 5</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 10</span> TBD <span class="pick-odds">TBD</span></li>
            </ul>
          </div>
        </div>

        <div class="crew-card">
          <img class="crew-photo" src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/andrew_hammond.jpg?v=1768439595" alt="Andrew">
          <div>
            <div class="crew-name">Andrew</div>
            <ul class="crew-picks-list">
              <li><span class="pick-label">Win</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 5</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 10</span> TBD <span class="pick-odds">TBD</span></li>
            </ul>
          </div>
        </div>

        <div class="crew-card">
          <img class="crew-photo" src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kcon.jpg?v=1768439465" alt="Kcon">
          <div>
            <div class="crew-name">Kcon</div>
            <ul class="crew-picks-list">
              <li><span class="pick-label">Win</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 5</span> TBD <span class="pick-odds">TBD</span></li>
              <li><span class="pick-label">Top 10</span> TBD <span class="pick-odds">TBD</span></li>
            </ul>
          </div>
        </div>

      </div>
    </div>

    <div class="event-info">
      <div class="info-block"><div class="info-label">Total Purse</div><div class="info-value">$9.2M</div></div>
      <div class="info-block"><div class="info-label">Winner's Share</div><div class="info-value">$1.656M</div></div>
      <div class="info-block"><div class="info-label">Course</div><div class="info-value">7,261 YDS</div></div>
      <div class="info-block"><div class="info-label">Par</div><div class="info-value">71</div></div>
      <div class="info-block"><div class="info-label">Field Size</div><div class="info-value">132</div></div>
      <div class="info-block"><div class="info-label">FedExCup Pts</div><div class="info-value">500</div></div>
    </div>

    <div class="course-image">
      <img src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/WM_teeshot.avif?v=1770087703" alt="TPC Scottsdale Stadium Course - WM Phoenix Open">
    </div>

    <div class="weather-forecast" style="background: #f8f9fa; border-left: 4px solid #000; padding: 16px 20px; margin: 24px 0; font-size: 15px; line-height: 1.6;">
      <strong style="font-size: 16px; display: block; margin-bottom: 8px;">⛅ Tournament Weather Forecast</strong>
      Expect pleasant desert conditions with highs around 70-75°F and calm winds 5-10 mph. Clear skies throughout the week with cooler mornings around 50°F. Perfect conditions for scoring at TPC Scottsdale.
    </div>

    <div class="section-header">
      <h2>Complete Betting Board</h2>
      <div class="section-line"></div>
    </div>

    <div class="tab-navigation">
      <button class="tab-button active" onclick="switchTab(event, 'tournament-odds')">Tournament Odds</button>
      <button class="tab-button" onclick="switchTab(event, 'daily-matchups')">Daily Matchups</button>
    </div>

    <div id="tournament-odds" class="tab-content active">
      <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-win);"></div><span>WIN / 1st</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-top5);"></div><span>TOP 5 (2nd-5th)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-top10);"></div><span>TOP 10 (6th-10th)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-top25);"></div><span>TOP 25 (11th-25th)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-made);"></div><span>MADE CUT (26th+)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-bad);"></div><span>MC / WD</span></div>
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Why They Could Win</th>
              <th class="center">2025</th>
              <th class="center">2024</th>
              <th class="center">2023</th>
              <th class="center">Win Odds</th>
              <th class="center">Top 5</th>
              <th class="center">Top 10</th>
              <th>Recent Form</th>
            </tr>
          </thead>
          <tbody>
{TABLE_ROWS}
          </tbody>
        </table>
      </div>
    </div>

    <div id="daily-matchups" class="tab-content">
      <div style="padding: 28px 12px; border: 1px solid var(--border); border-radius: 8px; margin-top: 12px;">
        <div style="font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 18px;">Daily Matchups Coming Soon</div>
        <div style="margin-top: 8px; font-size: 14px;">Head-to-head player matchups will be available closer to tournament time.</div>
      </div>
    </div>

    <footer>
      <div class="footer-text">COSMOS GOLF BETTING PREVIEW</div>
      <div class="data-source">Odds current as of February 2026 · Research your book for latest lines</div>
    </footer>
  </div>

  <script>
    function switchTab(event, tabName) {
      document.querySelectorAll('.cosmos-betting-preview .tab-content').forEach(tab => tab.classList.remove('active'));
      document.querySelectorAll('.cosmos-betting-preview .tab-button').forEach(btn => btn.classList.remove('active'));
      document.getElementById(tabName).classList.add('active');
      event.target.classList.add('active');
    }

    function downloadPdf() {
      const rows = document.querySelectorAll('.cosmos-betting-preview table tbody tr');
      const players = [];
      rows.forEach((row, idx) => {
        const cells = row.querySelectorAll('td');
        if (cells.length < 10) return;
        const pc = cells[1];
        const nameEl = pc.querySelector('.player-name a');
        const name = nameEl ? nameEl.textContent.trim().replace(' 🌍', '') : '';
        const tb = pc.querySelector('.tier-badge');
        const tier = tb ? tb.textContent.trim() : 'LONGSHOT';
        const cEl = pc.querySelector('.country-code');
        const country = cEl ? cEl.textContent.trim() : '';
        const oEl = pc.querySelector('.owgr');
        const owgr = oEl ? oEl.textContent.trim().replace('OWGR #', '#') : '';
        // Extract storyline from column 2 (full text for PDF Why column)
        const storylineEl = cells[2].querySelector('.storyline-text');
        let storyline = storylineEl ? storylineEl.textContent.trim() : '';
        // Extract recent form from column 9
        const recentEl = cells[9].querySelector('.recent-text');
        let recent = recentEl ? recentEl.textContent.trim() : '';
        if (recent.length > 60) recent = recent.substring(0, 57) + '...';
        const r25 = cells[3].textContent.trim();
        const r24 = cells[4].textContent.trim();
        const r23 = cells[5].textContent.trim();
        const win = cells[6].textContent.trim();
        const t5 = cells[7].textContent.trim();
        const t10 = cells[8].textContent.trim();
        players.push({ rk: idx+1, nm: name.length > 16 ? name.substring(0,14)+'..' : name, tier,
          ts: tier==='FAVORITE'?'FAV':tier==='CONTENDER'?'CON':tier==='VALUE'?'VAL':'LSH',
          cty: country, owgr, r25, r24, r23, win, t5, t10, storyline, recent });
      });
      // Color scale for results: green (good) to red (bad)
      const rb = r => {
        if(!r||r==='—'||r==='NA') return 'background:#f5f5f5;color:#999;';
        if(r==='WIN'||r==='1st') return 'background:#1e8449;color:#fff;font-weight:700;';
        if(r==='MC'||r==='WD') return 'background:#e74c3c;color:#fff;';
        const n=parseInt(r.replace('T',''));
        if(n<=3) return 'background:#27ae60;color:#fff;font-weight:600;';
        if(n<=5) return 'background:#58d68d;color:#000;';
        if(n<=10) return 'background:#abebc6;color:#000;';
        if(n<=20) return 'background:#f9e79f;color:#000;';
        if(n<=30) return 'background:#f5cba7;color:#000;';
        return 'background:#fadbd8;color:#000;';
      };
      // Color scale for odds: green (short/good) to white (long)
      const ob = o => {
        if(!o||o==='—') return 'background:#fff;';
        const v = parseInt(o.replace('+','').replace('-',''));
        const neg = o.startsWith('-');
        if(neg) return 'background:#1e8449;color:#fff;font-weight:700;';
        if(v<=500) return 'background:#27ae60;color:#fff;font-weight:600;';
        if(v<=1500) return 'background:#58d68d;color:#000;';
        if(v<=3000) return 'background:#abebc6;color:#000;';
        if(v<=6000) return 'background:#d5f5e3;color:#000;';
        if(v<=10000) return 'background:#fcf3cf;color:#000;';
        if(v<=20000) return 'background:#fef9e7;color:#000;';
        return 'background:#fff;color:#666;';
      };
      const tc = t => { if(t==='FAV') return 'background:#f4c430;color:#000;'; if(t==='CON') return 'background:#27ae60;color:#fff;'; if(t==='VAL') return 'background:#3498db;color:#fff;'; return 'background:#95a5a6;color:#fff;'; };
      const pp = 28, pgs = [];
      for(let i=0; i<players.length; i+=pp) pgs.push(players.slice(i,i+pp));
      // Build row with Why column (storyline + optional recent)
      const bR = list => list.map(p => '<tr class="main"><td class="c">'+p.rk+'</td><td class="c"><span class="tier" style="'+tc(p.ts)+'">'+p.ts+'</span></td><td class="nm">'+p.nm+'</td><td class="c">'+p.cty+'</td><td class="c rk">'+p.owgr+'</td><td class="c" style="'+rb(p.r25)+'">'+(p.r25||'—')+'</td><td class="c" style="'+rb(p.r24)+'">'+(p.r24||'—')+'</td><td class="c" style="'+rb(p.r23)+'">'+(p.r23||'—')+'</td><td class="c" style="'+ob(p.win)+'">'+p.win+'</td><td class="c" style="'+ob(p.t5)+'">'+p.t5+'</td><td class="c" style="'+ob(p.t10)+'">'+p.t10+'</td><td class="storyline-col">'+(p.storyline||'')+(p.recent && p.recent !== '—' ? ' | '+p.recent : '')+'</td></tr>').join('');
      const bP = (list,pn,tot) => '<div class="pg"><div class="hdr"><div class="hdr-l"><strong>WM PHOENIX OPEN 2026</strong> <span class="sub">TPC Scottsdale · Scottsdale, AZ · Feb 5-8 · $9.2M Purse</span></div><div class="hdr-r"><span class="leg"><b style="background:#1e8449">&nbsp;</b>WIN <b style="background:#58d68d">&nbsp;</b>T5 <b style="background:#abebc6">&nbsp;</b>T10 <b style="background:#f9e79f">&nbsp;</b>T20 <b style="background:#e74c3c">&nbsp;</b>MC</span><span class="pn">'+pn+'/'+tot+'</span></div></div><table><thead><tr><th>#</th><th>T</th><th class="l">PLAYER</th><th>CTY</th><th>RK</th><th>\'25</th><th>\'24</th><th>\'23</th><th>WIN</th><th>T5</th><th>T10</th><th>Why</th></tr></thead><tbody>'+bR(list)+'</tbody></table><div class="ftr">COSMOS GOLF · @COSMOSGOLF · Odds &amp; Data as of Feb 2026</div></div>';
      const css = '@page{size:landscape;margin:0.15in}*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial,Helvetica,sans-serif;font-size:7px;background:#fff;color:#222;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}.pg{margin:0 auto 8px;padding:4px;page-break-after:always}.pg:last-child{page-break-after:avoid}.hdr{display:flex;justify-content:space-between;align-items:center;padding:4px 6px;background:#2c3e50;color:#fff;margin-bottom:3px}.hdr-l{font-size:11px}.hdr-l .sub{font-size:7px;font-weight:400;margin-left:8px;opacity:0.8}.hdr-r{display:flex;align-items:center;gap:10px}.leg{font-size:6px;display:flex;align-items:center;gap:4px}.leg b{display:inline-block;width:10px;height:8px;margin-right:1px}.pn{font-size:8px;font-weight:700;background:#f4c430;color:#000;padding:2px 6px;border-radius:2px}table{width:100%;border-collapse:collapse;font-size:6.5px;border:1px solid #bdc3c7}th{background:#ecf0f1;font-size:6px;font-weight:700;padding:2px 3px;text-align:center;border:1px solid #bdc3c7}th.l{text-align:left}td{padding:1px 2px;border:1px solid #ecf0f1;vertical-align:middle}td.c{text-align:center}td.nm{font-weight:600;white-space:nowrap;font-size:6.5px}td.rk{color:#7f8c8d;font-size:5.5px}.tier{display:inline-block;padding:1px 3px;border-radius:2px;font-size:5px;font-weight:700}tr.main td{border-bottom:none}td.storyline-col{white-space:normal;word-wrap:break-word;overflow-wrap:break-word;width:2in;max-width:2.5in;vertical-align:top;font-size:5px;color:#555;font-style:italic;padding:2px;line-height:1.2}.ftr{text-align:center;padding:3px;font-size:6px;color:#7f8c8d;margin-top:2px}@media print{.pg{margin:0}}';
      const html = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>WM Phoenix Open 2026 Cheat Sheet</title><style>'+css+'</style></head><body>'+pgs.map((p,i)=>bP(p,i+1,pgs.length)).join('')+'<script>window.onload=function(){setTimeout(function(){window.print()},300)};<\/script></body></html>';
      const w = window.open('', '_blank', 'width=1100,height=800');
      w.document.write(html);
      w.document.close();
    }
  </script>
</div>'''


def main():
    parser = argparse.ArgumentParser(description="Assemble tournament HTML (WM Phoenix style)")
    parser.add_argument("--tournament", type=str, default="WM Phoenix Open", help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    global PLAYERS_DATA, STORYLINES, RECENT_FORM, OUTPUT
    slug = _slugify(args.tournament)
    PLAYERS_DATA = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    STORYLINES = ROOT / "data" / f"{slug}_{args.year}_storylines.json"
    RECENT_FORM = ROOT / "data" / f"{slug}_{args.year}_recent_form.json"
    OUTPUT = ROOT / f"{slug}_{args.year}.html"

    if not PLAYERS_DATA.exists():
        print(f"❌ Missing {PLAYERS_DATA}")
        return 1

    # Load all data
    data = json.loads(PLAYERS_DATA.read_text())

    # Try to load storylines
    storylines = {}
    if STORYLINES.exists():
        storylines_data = json.loads(STORYLINES.read_text())
        storylines = storylines_data.get("storylines", {})

    # Load recent form data
    recent_form = {}
    if RECENT_FORM.exists():
        recent_form = json.loads(RECENT_FORM.read_text())

    # Generate table rows
    table_rows = generate_table_rows(data, storylines, recent_form)

    # Create final HTML
    html = HTML_TEMPLATE.replace("{TABLE_ROWS}", table_rows)

    # Write output
    OUTPUT.write_text(html)
    print(f"Generated {OUTPUT}")
    print(f"Total players: {len(data.get('odds', {}))}")


if __name__ == "__main__":
    main()
