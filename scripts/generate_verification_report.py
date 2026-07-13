#!/usr/bin/env python3
"""Generate a verification report for top players."""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

players_data = json.load(open(ROOT / 'data/amex_2026_players_data.json'))
odds = json.load(open(ROOT / 'data/american_express_2026_odds.json'))

# Get all players with odds
player_list = []
for name, info in players_data['players'].items():
    odds_val = odds.get(name, 999999)
    if isinstance(odds_val, dict):
        odds_val = odds_val.get('odds', 999999)
    try:
        odds_num = int(str(odds_val).replace('+', '').replace(',', ''))
    except:
        odds_num = 999999

    player_list.append({
        'name': name,
        'odds': odds_num,
        'h2025': info.get('history_2025', 'NA'),
        'h2024': info.get('history_2024', 'NA'),
        'h2023': info.get('history_2023', 'NA')
    })

player_list.sort(key=lambda x: x['odds'])

print('TOP 50 PLAYERS - AMERICAN EXPRESS HISTORICAL DATA VERIFICATION')
print('=' * 90)
print(f"{'#':<4} {'Player':<30} {'2025':<8} {'2024':<8} {'2023':<8} {'Odds':<10}")
print('=' * 90)

for i, p in enumerate(player_list[:50], 1):
    odds_str = f"+{p['odds']}" if p['odds'] < 999999 else "—"
    print(f"{i:<4} {p['name']:<30} {p['h2025']:<8} {p['h2024']:<8} {p['h2023']:<8} {odds_str:<10}")

print('=' * 90)
print(f"\nIf you find errors, add them to: data/amex_historical_corrections.json")
print(f"Then run: python3 scripts/apply_manual_corrections.py")
