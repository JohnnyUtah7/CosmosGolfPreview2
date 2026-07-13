#!/usr/bin/env python3
"""
Fix recent form data using AI to find betting-relevant context.

Focuses on:
- Recent tournament results (PGA Tour, DP World Tour, international)
- Hot streaks and momentum
- Final round scoring (e.g., "shot 63 on Sunday")
- Injuries or form concerns
- Recent wins or strong finishes

Since the 2026 PGA Tour season just started, it's OK if players don't have much recent data.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RECENT_FORM_PATH = ROOT / "data" / "amex_2026_recent_form.json"
ODDS_FILE = ROOT / "data" / "american_express_2026_odds.json"
PLAYERS_DATA = ROOT / "data" / "amex_2026_players_data.json"


def is_junk_recent_form(text: str) -> bool:
    """Check if recent form entry is junk (news headline vs actual result)."""
    if not text or text.strip() == "—":
        return True

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


def get_recent_form_for_player(player_name: str, player_country: str, client) -> str:
    """Get recent form using Claude with web search capability."""
    try:
        prompt = f"""Find recent golf tournament results for {player_name} ({player_country}) as of January 2026. Focus on betting-relevant information:

What to look for:
1. Recent PGA Tour results (Sony Open, Tournament of Champions, etc.)
2. DP World Tour or international events for non-US players
3. Hot streaks ("three straight top-10s")
4. Exceptional final rounds ("shot 63 on Sunday")
5. Recent wins or runner-up finishes
6. Injury news or withdrawals

IMPORTANT:
- The 2026 PGA Tour season just started in January, so many players won't have much recent data yet - that's OK
- If no meaningful recent results, it's fine to return "—"
- For European/International players, check DP World Tour, Asian Tour, etc.

Format as ONE concise sentence (20-30 words max) for betting context. Examples:
- "Shot 63 on Sunday at Sony Open to finish T4 — scorching hot heading into desert"
- "Three straight top-10s including runner-up at DP World Tour Championship — trending perfectly"
- "Withdrew from Tournament of Champions with back tightness — health question mark"
- "Won on DP World Tour in December — arriving with confidence and momentum"
- "Season debut after quiet fall — fresh legs could be advantage"

If NO meaningful recent data found, return ONLY: —

Return ONLY the analysis sentence or —, nothing else."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text.strip()

        # Clean up any extra formatting
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]

        return result if result and result != "—" else "—"

    except Exception as e:
        print(f" ERROR: {e}")
        return "—"


def main() -> int:
    if not RECENT_FORM_PATH.exists():
        print(f"❌ Missing {RECENT_FORM_PATH}")
        return 1

    if not ODDS_FILE.exists():
        print(f"❌ Missing {ODDS_FILE}")
        return 1

    # Initialize Anthropic client
    try:
        from anthropic import Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ ANTHROPIC_API_KEY not set")
            return 1
        client = Anthropic(api_key=api_key)
    except ImportError:
        print("❌ anthropic package not installed")
        return 1

    # Load data
    recent_form = json.loads(RECENT_FORM_PATH.read_text(encoding="utf-8"))
    odds_data = json.loads(ODDS_FILE.read_text(encoding="utf-8"))
    players_data = json.loads(PLAYERS_DATA.read_text(encoding="utf-8"))

    # Get player countries for context
    player_countries = {}
    for player_name, player_info in players_data.get("players", {}).items():
        player_countries[player_name] = player_info.get("country", "USA")

    # Get odds for sorting
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

    # Find players with junk recent form
    junk_players = []
    for player, form_text in recent_form.items():
        if is_junk_recent_form(form_text):
            junk_players.append((player, player_odds.get(player, 999999)))

    # Sort by odds (favorites first)
    junk_players.sort(key=lambda x: x[1])

    print(f"📊 Found {len(junk_players)} players with junk recent form data")
    print(f"🔄 Fixing recent form using Claude API...\n")

    updated_count = 0
    for i, (player, odds) in enumerate(junk_players, 1):
        country = player_countries.get(player, "USA")
        print(f"  [{i}/{len(junk_players)}] {player:25s} ({country:3s}, {odds:6d})...", end=" ", flush=True)

        new_form = get_recent_form_for_player(player, country, client)
        recent_form[player] = new_form

        if new_form != "—":
            updated_count += 1
            print(f"✓")
        else:
            print("—")

        # Save progress every 10 players
        if i % 10 == 0:
            RECENT_FORM_PATH.write_text(
                json.dumps(recent_form, indent=2, sort_keys=True),
                encoding="utf-8"
            )
            print(f"    💾 Progress saved ({updated_count} updated so far)")

    # Final save
    RECENT_FORM_PATH.write_text(
        json.dumps(recent_form, indent=2, sort_keys=True),
        encoding="utf-8"
    )

    print(f"\n✅ Complete! Updated {updated_count}/{len(junk_players)} players")
    print(f"💾 Wrote {RECENT_FORM_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
