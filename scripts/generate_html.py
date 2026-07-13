#!/usr/bin/env python3
"""
Generate HTML preview from JSON data.

This script takes the JSON output from generate_preview.py and creates
an HTML file matching the Sony Open template style.

Usage:
    python scripts/generate_html.py --data previews/preview_data_20260116.json
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


def load_json_data(filepath: Path) -> dict:
    """Load JSON data from file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def generate_html(data: dict, template_path: Path = None) -> str:
    """
    Generate HTML from preview data.

    Args:
        data: Preview data dictionary
        template_path: Path to HTML template (optional)

    Returns:
        Generated HTML string
    """
    tournament_name = data.get('tournament', {}).get('name', 'PGA Tournament')
    commence_time = data.get('tournament', {}).get('commence_time')
    odds = data.get('odds', {})
    sportsbooks = data.get('sportsbooks', [])

    # Convert commence_time to readable format
    if commence_time:
        try:
            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            date_str = dt.strftime("%B %d-%d, %Y")  # e.g., "January 16-19, 2026"
        except:
            date_str = commence_time
    else:
        date_str = "TBD"

    # Sort players by odds (favorites first)
    sorted_players = sorted(
        odds.items(),
        key=lambda x: x[1]['odds']
    )

    # Generate player rows HTML
    player_rows = ""
    for idx, (player_name, odds_info) in enumerate(sorted_players, 1):
        odds_val = odds_info['odds']
        bookmaker = odds_info['bookmaker']

        # Format odds
        odds_str = f"+{odds_val}" if odds_val > 0 else str(odds_val)

        # Determine tier badge
        if odds_val <= 800:
            tier_class = "favorite"
            tier_label = "Favorite"
        elif odds_val <= 2000:
            tier_class = "contender"
            tier_label = "Contender"
        elif odds_val <= 5000:
            tier_class = "value"
            tier_label = "Value Play"
        else:
            tier_class = "longshot"
            tier_label = "Longshot"

        # Get player data if available
        player_info = data.get('players', {}).get(player_name, {})
        country = player_info.get('country', '')
        country_flag = f" 🌍" if country else ""

        # Placeholder historical data
        hist_2025 = '-'
        hist_2024 = '-'
        hist_2023 = '-'

        player_rows += f"""
        <tr>
            <td>{idx}</td>
            <td>{player_name}{country_flag}</td>
            <td class="owgr">-</td>
            <td class="hist-result">{hist_2025}</td>
            <td class="hist-result">{hist_2024}</td>
            <td class="hist-result">{hist_2023}</td>
            <td class="odds-win">{odds_str}</td>
            <td class="odds-top5">-</td>
            <td class="odds-top10">-</td>
            <td class="tier-badge {tier_class}">{tier_label}</td>
            <td class="storyline">Odds from {bookmaker}. Tournament analysis coming soon.</td>
        </tr>
        """

    # Sportsbook summary
    sportsbook_summary = "<br>".join([
        f"• {sb['name']}: {sb['player_count']} players"
        for sb in sportsbooks[:5]  # Show top 5
    ])

    # Generate complete HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COSMOS Golf - {tournament_name} Betting Preview</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">

    <style>
        /* NASA-Inspired Space Theme */
        :root {{
            --nasa-blue: #0B3D91;
            --nasa-red: #FC3D21;
            --space-black: #0a0a0f;
            --cyber-cyan: #00d4ff;
            --grid-green: #00ff88;
            --warning-gold: #ffd700;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Rajdhani', sans-serif;
            background: var(--space-black);
            color: #ffffff;
            line-height: 1.6;
            position: relative;
            overflow-x: hidden;
        }}

        /* Animated grid background */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px),
                linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            z-index: 0;
            pointer-events: none;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }}

        header {{
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 40px;
            background: linear-gradient(135deg, rgba(11,61,145,0.3) 0%, rgba(0,0,0,0.5) 100%);
            border: 2px solid var(--cyber-cyan);
            border-radius: 10px;
            box-shadow: 0 0 30px rgba(0,212,255,0.3);
        }}

        h1 {{
            font-family: 'Orbitron', sans-serif;
            font-size: 3em;
            font-weight: 900;
            color: var(--cyber-cyan);
            text-transform: uppercase;
            letter-spacing: 4px;
            text-shadow: 0 0 20px rgba(0,212,255,0.8);
            margin-bottom: 10px;
        }}

        .subtitle {{
            font-family: 'Share Tech Mono', monospace;
            color: var(--grid-green);
            font-size: 1.2em;
            letter-spacing: 2px;
        }}

        .tournament-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .info-card {{
            background: rgba(0,212,255,0.05);
            border: 1px solid var(--cyber-cyan);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}

        .info-label {{
            font-family: 'Share Tech Mono', monospace;
            color: var(--grid-green);
            font-size: 0.9em;
            margin-bottom: 5px;
        }}

        .info-value {{
            font-family: 'Orbitron', sans-serif;
            color: #ffffff;
            font-size: 1.4em;
            font-weight: 700;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
            background: rgba(10,10,15,0.9);
            border: 2px solid var(--cyber-cyan);
            border-radius: 10px;
            overflow: hidden;
        }}

        thead {{
            background: linear-gradient(135deg, var(--nasa-blue) 0%, rgba(0,0,0,0.8) 100%);
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            color: var(--cyber-cyan);
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
            border-bottom: 2px solid var(--cyber-cyan);
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid rgba(0,212,255,0.1);
        }}

        tbody tr {{
            transition: all 0.3s ease;
        }}

        tbody tr:hover {{
            background: rgba(0,212,255,0.1);
            transform: translateX(5px);
        }}

        .tier-badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: inline-block;
        }}

        .tier-badge.favorite {{
            background: linear-gradient(135deg, var(--warning-gold), #ffed4e);
            color: #000;
        }}

        .tier-badge.contender {{
            background: linear-gradient(135deg, #00ff88, #00d4ff);
            color: #000;
        }}

        .tier-badge.value {{
            background: linear-gradient(135deg, #9333ea, #c026d3);
            color: #fff;
        }}

        .tier-badge.longshot {{
            background: linear-gradient(135deg, #666, #999);
            color: #fff;
        }}

        footer {{
            text-align: center;
            margin-top: 60px;
            padding: 30px;
            border-top: 2px solid var(--cyber-cyan);
            font-family: 'Share Tech Mono', monospace;
            color: var(--grid-green);
        }}

        .disclaimer {{
            font-size: 0.85em;
            color: #888;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>COSMOS Golf</h1>
            <div class="subtitle">{tournament_name}</div>
            <div class="subtitle" style="color: var(--cyber-cyan); margin-top: 10px;">{date_str}</div>
        </header>

        <div class="tournament-info">
            <div class="info-card">
                <div class="info-label">Players with Odds</div>
                <div class="info-value">{len(sorted_players)}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Sportsbooks</div>
                <div class="info-value">{len(sportsbooks)}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Best Odds</div>
                <div class="info-value">Aggregated</div>
            </div>
            <div class="info-card">
                <div class="info-label">Generated</div>
                <div class="info-value">{datetime.now().strftime("%b %d")}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Player</th>
                    <th>OWGR</th>
                    <th>2025</th>
                    <th>2024</th>
                    <th>2023</th>
                    <th>Win</th>
                    <th>Top 5</th>
                    <th>Top 10</th>
                    <th>Tier</th>
                    <th>Analysis</th>
                </tr>
            </thead>
            <tbody>
                {player_rows}
            </tbody>
        </table>

        <footer>
            <p><strong>COSMOS Golf · Golf in the Cosmos</strong></p>
            <p class="disclaimer">
                Odds are aggregated from multiple sportsbooks. This preview is for entertainment purposes only.
                Please gamble responsibly. Generated automatically via API integration.
            </p>
        </footer>
    </div>
</body>
</html>
"""

    return html


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate HTML preview from JSON data"
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to JSON data file from generate_preview.py"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output HTML file path (default: auto-generated)"
    )
    parser.add_argument(
        "--template",
        type=Path,
        help="Custom HTML template (optional)"
    )

    args = parser.parse_args()

    print("🎨 HTML Preview Generator")
    print("=" * 60)

    # Load data
    if not args.data.exists():
        print(f"❌ Error: Data file not found: {args.data}")
        return 1

    print(f"📄 Loading data from: {args.data}")
    data = load_json_data(args.data)

    # Generate HTML
    print("🎨 Generating HTML...")
    html = generate_html(data, args.template)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Auto-generate filename
        tournament_name = data.get('tournament', {}).get('name', 'tournament')
        safe_name = tournament_name.lower().replace(' ', '_').replace('-', '_')
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = Path(f"previews/{safe_name}_{date_str}.html")

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write HTML
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ HTML generated: {output_path}")
    print(f"   File size: {len(html)} bytes")
    print("")
    print("🌐 Preview locally:")
    print(f"   python scripts/preview_server.py")
    print(f"   Then open: http://localhost:8000/{output_path.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
