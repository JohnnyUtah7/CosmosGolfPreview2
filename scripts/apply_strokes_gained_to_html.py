#!/usr/bin/env python3
"""
Apply strokes gained data to tournament preview HTML.

This script reads player_strokes_gained.json and updates the HTML file
to add the SG toggle buttons and expandable panels for each player.

Usage:
    python scripts/apply_strokes_gained_to_html.py wm_phoenix_open_2026.html
    python scripts/apply_strokes_gained_to_html.py --dry-run wm_phoenix_open_2026.html
"""

import argparse
import json
import re
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"
SG_DATA_FILE = DATA_DIR / "player_strokes_gained.json"


def load_sg_data() -> dict:
    """Load strokes gained data from JSON file."""
    if not SG_DATA_FILE.exists():
        print(f"Warning: {SG_DATA_FILE} not found. Run fetch_pga_strokes_gained.py first.")
        return {}

    with open(SG_DATA_FILE) as f:
        return json.load(f)


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    # Remove extra whitespace, convert to lowercase
    return re.sub(r'\s+', ' ', name.strip().lower())


def generate_player_id(name: str) -> str:
    """Generate a URL-safe player ID from name."""
    # Convert to lowercase, replace spaces with hyphens, remove special chars
    player_id = name.lower()
    player_id = re.sub(r'[^\w\s-]', '', player_id)
    player_id = re.sub(r'\s+', '-', player_id)
    return player_id


def generate_sg_button_html(player_id: str) -> str:
    """Generate the SG toggle button HTML."""
    return f'''<td class="sg-cell">
                <button class="sg-toggle-btn" data-player-id="{player_id}" onclick="toggleSGPanel(this, '{player_id}')" title="View Strokes Gained Stats">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                </button>
              </td>'''


def generate_sg_panel_html(player_id: str, stats: dict) -> str:
    """Generate the SG panel row HTML."""

    def format_stat(val):
        if val is None:
            return 'N/A', 'neutral', 0
        sign = '+' if val >= 0 else ''
        cls = 'positive' if val > 0 else ('negative' if val < 0 else 'neutral')
        pct = min(100, abs(val) / 2.0 * 100)
        return f"{sign}{val:.2f}", cls, int(pct)

    ott_val, ott_cls, ott_pct = format_stat(stats.get('sg_off_tee'))
    app_val, app_cls, app_pct = format_stat(stats.get('sg_approach'))
    arg_val, arg_cls, arg_pct = format_stat(stats.get('sg_around_green'))
    put_val, put_cls, put_pct = format_stat(stats.get('sg_putting'))

    return f'''            <tr id="sg-panel-{player_id}" class="sg-panel-row">
              <td colspan="11">
                <div class="sg-panel">
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
                </div>
              </td>
            </tr>'''


def generate_no_data_panel_html(player_id: str) -> str:
    """Generate an SG panel with no data available message."""
    return f'''            <tr id="sg-panel-{player_id}" class="sg-panel-row">
              <td colspan="11">
                <div class="sg-panel">
                  <div class="sg-no-data">Strokes gained data not available for this player</div>
                </div>
              </td>
            </tr>'''


def process_html(html_path: Path, sg_data: dict, dry_run: bool = False) -> tuple[str, int, int]:
    """
    Process HTML file and add SG components to player rows.

    Returns:
        Tuple of (modified_html, rows_updated, rows_skipped)
    """
    with open(html_path) as f:
        html = f.read()

    # Create a lookup dict with normalized names
    sg_lookup = {}
    for name, stats in sg_data.items():
        norm_name = normalize_name(name)
        sg_lookup[norm_name] = stats

    # Find all player rows that don't already have SG cells
    # Pattern: <tr> ... <td class="player-cell"> ... player name ... </td> ... </tr>
    # But NOT rows that already have sg-cell

    # First, let's identify rows that already have SG components
    rows_with_sg = set()
    for match in re.finditer(r'data-player-id="([^"]+)"', html):
        rows_with_sg.add(match.group(1))

    # Find player rows by looking for player-name anchors
    player_row_pattern = re.compile(
        r'(<tr(?![^>]*data-player-id)[^>]*>)\s*'  # Opening tr without data-player-id
        r'(<td>\d+</td>\s*'  # Rank cell
        r'<td class="player-cell">.*?'
        r'<div class="player-name"><a[^>]*>([^<]+)</a></div>'  # Player name
        r'.*?</td>)'  # Rest of player cell
        r'(.*?)'  # Middle cells
        r'(<td class="recent-cell">.*?</td>)\s*'  # Recent form cell
        r'(</tr>)',  # Closing tr
        re.DOTALL
    )

    rows_updated = 0
    rows_skipped = 0

    def replace_row(match):
        nonlocal rows_updated, rows_skipped

        tr_open = match.group(1)
        rank_and_player = match.group(2)
        player_name = match.group(3).strip()
        middle_cells = match.group(4)
        recent_cell = match.group(5)
        tr_close = match.group(6)

        player_id = generate_player_id(player_name)

        # Check if this row already has SG component
        if player_id in rows_with_sg:
            rows_skipped += 1
            return match.group(0)

        # Look up stats
        norm_name = normalize_name(player_name)
        stats = sg_lookup.get(norm_name)

        # Add data-player-id to tr
        new_tr_open = tr_open.replace('<tr', f'<tr data-player-id="{player_id}"')

        # Generate SG button
        sg_button = generate_sg_button_html(player_id)

        # Generate SG panel
        if stats:
            sg_panel = generate_sg_panel_html(player_id, stats)
        else:
            sg_panel = generate_no_data_panel_html(player_id)

        rows_updated += 1

        # Reconstruct row with SG components
        return f'''{new_tr_open}
{rank_and_player}{middle_cells}{recent_cell}
{sg_button}
            {tr_close}
{sg_panel}
'''

    modified_html = player_row_pattern.sub(replace_row, html)

    return modified_html, rows_updated, rows_skipped


def main():
    parser = argparse.ArgumentParser(description="Apply SG data to HTML")
    parser.add_argument("html_file", type=Path, help="HTML file to update")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify file, just report")
    parser.add_argument("--sg-data", type=Path, default=SG_DATA_FILE, help="SG data JSON file")

    args = parser.parse_args()

    if not args.html_file.exists():
        print(f"Error: {args.html_file} not found")
        return 1

    # Load SG data
    sg_data = load_sg_data() if args.sg_data == SG_DATA_FILE else json.load(open(args.sg_data))

    print(f"Loaded SG data for {len(sg_data)} players")

    # Process HTML
    modified_html, updated, skipped = process_html(args.html_file, sg_data, args.dry_run)

    print(f"Rows updated: {updated}")
    print(f"Rows skipped (already have SG): {skipped}")

    if args.dry_run:
        print("\nDry run - no changes made")
    else:
        with open(args.html_file, 'w') as f:
            f.write(modified_html)
        print(f"\nSaved changes to {args.html_file}")

    return 0


if __name__ == "__main__":
    exit(main())
