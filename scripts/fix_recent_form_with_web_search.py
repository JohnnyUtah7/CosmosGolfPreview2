#!/usr/bin/env python3
"""
Fix recent form data by replacing junk entries with web search results.

Identifies entries that contain news headlines instead of actual results,
then uses web search to find real recent performance data.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RECENT_FORM_PATH = ROOT / "data" / "amex_2026_recent_form.json"
ODDS_FILE = ROOT / "data" / "american_express_2026_odds.json"


def is_junk_recent_form(text: str) -> bool:
    """Check if recent form entry is junk (news headline vs actual result)."""
    if not text or text.strip() == "—":
        return True

    # Check for news headline indicators
    junk_patterns = [
        r"american express.*odds",
        r"predictions.*field",
        r"best bets",
        r"tickets.*parking",
        r"prize money",
        r"how much",
        r"added to.*field",
        r"makes a compelling case",
    ]

    text_lower = text.lower()
    for pattern in junk_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def search_recent_form(player_name: str) -> str:
    """Use web search to find player's recent form."""
    # This would use WebSearch tool in the actual implementation
    # For now, return a placeholder that we'll fill with actual searches
    return f"SEARCH_NEEDED:{player_name}"


def main() -> int:
    if not RECENT_FORM_PATH.exists():
        print(f"❌ Missing {RECENT_FORM_PATH}")
        return 1

    if not ODDS_FILE.exists():
        print(f"❌ Missing {ODDS_FILE}")
        return 1

    # Load data
    recent_form = json.loads(RECENT_FORM_PATH.read_text(encoding="utf-8"))
    odds_data = json.loads(ODDS_FILE.read_text(encoding="utf-8"))

    # Get odds as simple dict for sorting
    player_odds = {}
    for player in recent_form.keys():
        if player in odds_data:
            odds_info = odds_data[player]
            if isinstance(odds_info, dict):
                player_odds[player] = int(odds_info.get("odds", 999999))
            else:
                player_odds[player] = int(odds_info) if odds_info else 999999
        else:
            player_odds[player] = 999999

    # Find players with junk recent form, prioritize by odds
    junk_players = []
    for player, form_text in recent_form.items():
        if is_junk_recent_form(form_text):
            junk_players.append((player, player_odds.get(player, 999999)))

    # Sort by odds (favorites first)
    junk_players.sort(key=lambda x: x[1])

    print(f"📊 Found {len(junk_players)} players with junk recent form data")
    print(f"   Top 30 by odds (lower = favorite):")

    # Show top 30 that need fixing
    for i, (player, odds) in enumerate(junk_players[:30], 1):
        current_text = recent_form[player][:80] + "..." if len(recent_form[player]) > 80 else recent_form[player]
        print(f"  {i:2d}. {player:25s} ({odds:6d}) - {current_text}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
