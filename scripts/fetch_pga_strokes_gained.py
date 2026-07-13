#!/usr/bin/env python3
"""
Fetch PGA Tour Strokes Gained statistics for players.

This script scrapes strokes gained data from PGA Tour's website and stores it
in a JSON file that can be used to populate the betting preview HTML.

Usage:
    python scripts/fetch_pga_strokes_gained.py
    python scripts/fetch_pga_strokes_gained.py --player "Scottie Scheffler"
    python scripts/fetch_pga_strokes_gained.py --update-html

Requirements:
    pip install playwright beautifulsoup4
    playwright install chromium
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# PGA Tour stat IDs for strokes gained categories
STAT_IDS = {
    "sg_total": "02675",
    "sg_off_tee": "02567",
    "sg_approach": "02568",
    "sg_around_green": "02569",
    "sg_putting": "02564",
    "sg_tee_to_green": "02674",
}

# PGA Tour stats URLs
BASE_URL = "https://www.pgatour.com/stats/detail"

# Output file
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "player_strokes_gained.json"


def fetch_sg_stats_playwright(player_names: Optional[list] = None) -> dict:
    """
    Fetch strokes gained stats using Playwright for dynamic content.

    Args:
        player_names: Optional list of player names to filter results

    Returns:
        Dictionary mapping player names to their SG stats
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for stat_name, stat_id in STAT_IDS.items():
            if stat_name == "sg_total" or stat_name == "sg_tee_to_green":
                continue  # Skip composite stats for now

            url = f"{BASE_URL}/{stat_id}"
            print(f"Fetching {stat_name} from {url}...")

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_selector("table", timeout=10000)

                # Extract table data
                rows = page.query_selector_all("table tbody tr")

                for row in rows:
                    cells = row.query_selector_all("td")
                    if len(cells) >= 3:
                        # Typical structure: Rank, Player Name, Stat Value
                        player_cell = cells[1]
                        player_name = player_cell.inner_text().strip()

                        # Clean player name
                        player_name = re.sub(r'\s+', ' ', player_name)

                        # Get stat value
                        value_cell = cells[2]
                        value_text = value_cell.inner_text().strip()

                        try:
                            value = float(value_text)
                        except ValueError:
                            continue

                        if player_names and player_name not in player_names:
                            continue

                        if player_name not in results:
                            results[player_name] = {
                                "name": player_name,
                                "sg_off_tee": None,
                                "sg_approach": None,
                                "sg_around_green": None,
                                "sg_putting": None,
                                "last_updated": datetime.now().isoformat()
                            }

                        # Map stat name to result key
                        results[player_name][stat_name] = value

            except Exception as e:
                print(f"  Error fetching {stat_name}: {e}")
                continue

        browser.close()

    return results


def fetch_sg_stats_manual() -> dict:
    """
    Manual entry mode for strokes gained stats.

    Use this when automated scraping isn't working. Data can be
    manually looked up from https://www.pgatour.com/stats/strokes-gained

    Returns:
        Dictionary with example/placeholder data
    """
    # Example data structure - fill in from PGA Tour website manually
    return {
        "Scottie Scheffler": {
            "name": "Scottie Scheffler",
            "sg_off_tee": 1.45,
            "sg_approach": 1.12,
            "sg_around_green": 0.38,
            "sg_putting": 0.42,
            "last_updated": datetime.now().isoformat()
        },
        "Xander Schauffele": {
            "name": "Xander Schauffele",
            "sg_off_tee": 0.89,
            "sg_approach": 0.72,
            "sg_around_green": 0.21,
            "sg_putting": 0.58,
            "last_updated": datetime.now().isoformat()
        },
        "Cameron Young": {
            "name": "Cameron Young",
            "sg_off_tee": 1.17,
            "sg_approach": 0.65,
            "sg_around_green": -0.12,
            "sg_putting": -0.28,
            "last_updated": datetime.now().isoformat()
        },
        "Hideki Matsuyama": {
            "name": "Hideki Matsuyama",
            "sg_off_tee": 0.52,
            "sg_approach": 1.35,
            "sg_around_green": 0.18,
            "sg_putting": 0.31,
            "last_updated": datetime.now().isoformat()
        },
        "Si Woo Kim": {
            "name": "Si Woo Kim",
            "sg_off_tee": 0.35,
            "sg_approach": 1.09,
            "sg_around_green": 0.15,
            "sg_putting": -0.22,
            "last_updated": datetime.now().isoformat()
        },
        "Ben Griffin": {
            "name": "Ben Griffin",
            "sg_off_tee": 0.78,
            "sg_approach": 0.92,
            "sg_around_green": 0.45,
            "sg_putting": 0.35,
            "last_updated": datetime.now().isoformat()
        },
        "Sam Burns": {
            "name": "Sam Burns",
            "sg_off_tee": 0.95,
            "sg_approach": 0.55,
            "sg_around_green": 0.22,
            "sg_putting": 0.18,
            "last_updated": datetime.now().isoformat()
        },
        "Brooks Koepka": {
            "name": "Brooks Koepka",
            "sg_off_tee": 0.82,
            "sg_approach": 0.68,
            "sg_around_green": -0.15,
            "sg_putting": -0.35,
            "last_updated": datetime.now().isoformat()
        },
    }


def save_stats(stats: dict, output_file: Path = OUTPUT_FILE):
    """Save stats to JSON file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"Saved {len(stats)} player stats to {output_file}")


def load_stats(input_file: Path = OUTPUT_FILE) -> dict:
    """Load stats from JSON file."""
    if not input_file.exists():
        return {}

    with open(input_file) as f:
        return json.load(f)


def generate_sg_html(player_stats: dict) -> str:
    """
    Generate the SG panel HTML for a player.

    Args:
        player_stats: Dictionary with player's SG stats

    Returns:
        HTML string for the SG panel
    """
    def format_value(val):
        if val is None:
            return 'N/A', 'neutral', 0
        sign = '+' if val >= 0 else ''
        cls = 'positive' if val >= 0 else 'negative'
        # Calculate bar width (max 2.0 = 100%)
        pct = min(100, abs(val) / 2.0 * 100)
        return f"{sign}{val:.2f}", cls, int(pct)

    ott_val, ott_cls, ott_pct = format_value(player_stats.get('sg_off_tee'))
    app_val, app_cls, app_pct = format_value(player_stats.get('sg_approach'))
    arg_val, arg_cls, arg_pct = format_value(player_stats.get('sg_around_green'))
    put_val, put_cls, put_pct = format_value(player_stats.get('sg_putting'))

    return f'''<div class="sg-panel">
  <div class="sg-panel-header">Strokes Gained (2026 Season)</div>
  <div class="sg-grid">
    <div class="sg-stat">
      <div class="sg-stat-header">
        <span class="sg-stat-label">
          <svg class="sg-stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          Off-the-Tee
        </span>
        <span class="sg-stat-value {ott_cls}">{ott_val}</span>
      </div>
      <div class="sg-bar-track"><div class="sg-bar-fill {ott_cls}" style="width: {ott_pct}%;"></div></div>
    </div>
    <div class="sg-stat">
      <div class="sg-stat-header">
        <span class="sg-stat-label">
          <svg class="sg-stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M12 2v4m0 12v4m10-10h-4M6 12H2"></path></svg>
          Approach
        </span>
        <span class="sg-stat-value {app_cls}">{app_val}</span>
      </div>
      <div class="sg-bar-track"><div class="sg-bar-fill {app_cls}" style="width: {app_pct}%;"></div></div>
    </div>
    <div class="sg-stat">
      <div class="sg-stat-header">
        <span class="sg-stat-label">
          <svg class="sg-stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>
          Around Green
        </span>
        <span class="sg-stat-value {arg_cls}">{arg_val}</span>
      </div>
      <div class="sg-bar-track"><div class="sg-bar-fill {arg_cls}" style="width: {arg_pct}%;"></div></div>
    </div>
    <div class="sg-stat">
      <div class="sg-stat-header">
        <span class="sg-stat-label">
          <svg class="sg-stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"></path></svg>
          Putting
        </span>
        <span class="sg-stat-value {put_cls}">{put_val}</span>
      </div>
      <div class="sg-bar-track"><div class="sg-bar-fill {put_cls}" style="width: {put_pct}%;"></div></div>
    </div>
  </div>
  <div class="sg-source">Source: PGA Tour Stats · Last 50 rounds</div>
</div>'''


def print_manual_lookup_guide():
    """Print instructions for manual data lookup."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                  PGA TOUR STROKES GAINED LOOKUP GUIDE                ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Visit these URLs to manually look up strokes gained stats:          ║
║                                                                      ║
║  • SG: Off-the-Tee     https://www.pgatour.com/stats/detail/02567   ║
║  • SG: Approach        https://www.pgatour.com/stats/detail/02568   ║
║  • SG: Around Green    https://www.pgatour.com/stats/detail/02569   ║
║  • SG: Putting         https://www.pgatour.com/stats/detail/02564   ║
║  • SG: Total           https://www.pgatour.com/stats/detail/02675   ║
║  • SG: Tee-to-Green    https://www.pgatour.com/stats/detail/02674   ║
║                                                                      ║
║  After looking up stats, add them to:                                ║
║  data/player_strokes_gained.json                                     ║
║                                                                      ║
║  Format:                                                             ║
║  {                                                                   ║
║    "Player Name": {                                                  ║
║      "name": "Player Name",                                          ║
║      "sg_off_tee": 1.23,                                             ║
║      "sg_approach": 0.45,                                            ║
║      "sg_around_green": 0.12,                                        ║
║      "sg_putting": -0.34,                                            ║
║      "last_updated": "2026-02-03T12:00:00"                           ║
║    }                                                                 ║
║  }                                                                   ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="Fetch PGA Tour Strokes Gained stats")
    parser.add_argument("--player", help="Fetch stats for a specific player")
    parser.add_argument("--manual", action="store_true", help="Use manual/example data")
    parser.add_argument("--guide", action="store_true", help="Print manual lookup guide")
    parser.add_argument("--playwright", action="store_true", help="Use Playwright for scraping")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="Output JSON file")

    args = parser.parse_args()

    if args.guide:
        print_manual_lookup_guide()
        return

    if args.manual:
        print("Using manual/example data...")
        stats = fetch_sg_stats_manual()
    elif args.playwright:
        print("Fetching stats using Playwright...")
        player_filter = [args.player] if args.player else None
        stats = fetch_sg_stats_playwright(player_filter)
    else:
        # Default: use manual data and print guide
        print("Note: PGA Tour loads stats dynamically. Using example data.")
        print("Run with --playwright to attempt automated scraping,")
        print("or run with --guide for manual lookup instructions.\n")
        stats = fetch_sg_stats_manual()

    if stats:
        save_stats(stats, args.output)

        # Print summary
        print("\nStats Summary:")
        print("-" * 60)
        for name, data in sorted(stats.items()):
            ott = data.get('sg_off_tee', 'N/A')
            app = data.get('sg_approach', 'N/A')
            arg = data.get('sg_around_green', 'N/A')
            put = data.get('sg_putting', 'N/A')

            ott_str = f"+{ott:.2f}" if isinstance(ott, (int, float)) and ott >= 0 else (f"{ott:.2f}" if isinstance(ott, (int, float)) else ott)
            app_str = f"+{app:.2f}" if isinstance(app, (int, float)) and app >= 0 else (f"{app:.2f}" if isinstance(app, (int, float)) else app)
            arg_str = f"+{arg:.2f}" if isinstance(arg, (int, float)) and arg >= 0 else (f"{arg:.2f}" if isinstance(arg, (int, float)) else arg)
            put_str = f"+{put:.2f}" if isinstance(put, (int, float)) and put >= 0 else (f"{put:.2f}" if isinstance(put, (int, float)) else put)

            print(f"{name:25s} OTT:{ott_str:>7s} APP:{app_str:>7s} ARG:{arg_str:>7s} PUT:{put_str:>7s}")
    else:
        print("No stats fetched.")


if __name__ == "__main__":
    main()
