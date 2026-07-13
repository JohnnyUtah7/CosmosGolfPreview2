#!/usr/bin/env python3
"""
Verify historical data using Google Gemini API for better accuracy.

Usage:
  python scripts/verify_with_gemini.py --players-data data/wm_phoenix_open_2026_players_data.json
  python scripts/verify_with_gemini.py --tournament "WM Phoenix Open" --year 2026
"""

import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def verify_player_with_gemini(player_name: str, years: list[int]):
    """Use Gemini to verify American Express results for a player."""
    try:
        import google.generativeai as genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not set")
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        prompt = f"""What were {player_name}'s exact finishing positions at The American Express PGA Tour golf tournament for these years:
- 2025 (January 2025)
- 2024 (January 2024)
- 2023 (January 2023)

Return ONLY in this exact format:
2025: [position or NA]
2024: [position or NA]
2023: [position or NA]

Use format like: T12, MC, WD, 5, or NA if didn't play.
No explanations, just the three lines."""

        response = model.generate_content(prompt)
        result = response.text.strip()

        # Parse results
        results = {}
        for line in result.split('\n'):
            if ':' in line:
                year_str, pos = line.split(':', 1)
                year = year_str.strip()
                position = pos.strip()
                if year in ['2025', '2024', '2023']:
                    results[f"history_{year}"] = position if position != "NA" else "NA"

        return results

    except Exception as e:
        print(f"Error with Gemini API: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Verify historical data with Gemini")
    parser.add_argument("--players-data", type=Path, help="Path to players_data.json")
    parser.add_argument("--tournament", type=str, help="Tournament name (to derive path)")
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

    players_data = json.loads(path.read_text(encoding="utf-8"))
    players = players_data["players"]

    odds = {}
    for name, info in players_data.get("odds", {}).items():
        o = info.get("odds", 999999) if isinstance(info, dict) else info
        try:
            odds[name] = int(str(o).replace("+", "").replace(",", ""))
        except (TypeError, ValueError):
            odds[name] = 999999

    # Get all players sorted by odds
    player_list = []
    for name, info in players.items():
        odds_val = odds.get(name, 999999)
        if isinstance(odds_val, dict):
            odds_val = odds_val.get('odds', 999999)
        try:
            odds_num = int(str(odds_val).replace('+', '').replace(',', ''))
        except:
            odds_num = 999999
        player_list.append((name, odds_num))

    player_list.sort(key=lambda x: x[1])
    top_50_players = [name for name, _ in player_list[:50]]

    print("🔍 Verifying TOP 50 players with Google Gemini API...\n")
    print(f"This will take ~5-10 minutes for 50 players\n")

    verified_count = 0
    errors_found = 0
    discrepancies = {}

    for i, player_name in enumerate(top_50_players, 1):
        if player_name not in players:
            continue

        print(f"[{i}/50] Verifying {player_name}...", end=" ")
        gemini_results = verify_player_with_gemini(player_name, [2025, 2024, 2023])

        if not gemini_results:
            print(f"⚠️  Could not verify")
            continue

        # Compare with our data
        current_data = players[player_name]
        has_errors = False
        player_discrepancies = {}

        for year_field in ['history_2025', 'history_2024', 'history_2023']:
            our_value = current_data.get(year_field, "NA")
            gemini_value = gemini_results.get(year_field, "NA")

            if our_value != gemini_value:
                errors_found += 1
                has_errors = True
                player_discrepancies[year_field] = {
                    "ours": our_value,
                    "gemini": gemini_value
                }

        if has_errors:
            print(f"❌ {len(player_discrepancies)} errors found")
            discrepancies[player_name] = player_discrepancies
        else:
            print(f"✓")
            verified_count += 1

    print(f"\n{'='*80}")
    print(f"📊 Verification Summary:")
    print(f"   Verified correct: {verified_count}/50")
    print(f"   Players with errors: {len(discrepancies)}")
    print(f"   Total field errors: {errors_found}")
    print(f"{'='*80}\n")

    if discrepancies:
        print("🔍 DISCREPANCIES FOUND:\n")
        for player_name, errors in discrepancies.items():
            print(f"{player_name}:")
            for field, values in errors.items():
                year = field.replace("history_", "")
                print(f"  {year}: Our={values['ours']} → Gemini={values['gemini']}")
            print()

        # Auto-generate corrections file
        corrections_file = ROOT / "data" / "amex_historical_corrections.json"
        corrections = {}

        if corrections_file.exists():
            corrections = json.loads(corrections_file.read_text(encoding="utf-8"))

        for player_name, errors in discrepancies.items():
            corrections[player_name] = {}
            for field, values in errors.items():
                corrections[player_name][field] = values['gemini']

        corrections_file.write_text(
            json.dumps(corrections, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"✅ Auto-generated corrections file: {corrections_file}")
        print(f"💡 Run: python3 scripts/apply_manual_corrections.py")
    else:
        print("✅ All top 50 players verified - no errors found!")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
