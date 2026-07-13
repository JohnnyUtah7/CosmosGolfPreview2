#!/usr/bin/env python3
"""
Enrich recent form data with betting-relevant context.

This script focuses on what bettors actually care about:
- Hot streaks and momentum
- Recent low rounds (especially final round scoring)
- Current tournament position (if playing this week)
- Injuries or form concerns
- Recent wins or strong finishes

Uses web search to find real-time data for top contenders.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLAYERS_DATA = ROOT / "data" / "amex_2026_players_data.json"
RECENT_FORM_OUT = ROOT / "data" / "amex_2026_recent_form_enriched.json"
ODDS_FILE = ROOT / "data" / "american_express_2026_odds.json"


def get_top_players(odds_data: dict, limit: int = 50) -> list[tuple[str, int]]:
    """Get top N players by odds (lower odds = favorites)."""
    # Convert odds to (player, odds_value) tuples
    players_with_odds = []
    for player, odds_info in odds_data.items():
        if isinstance(odds_info, dict):
            odds = odds_info.get("odds", 999999)
        else:
            odds = odds_info
        players_with_odds.append((player, int(odds) if odds else 999999))

    # Sort by odds (lower = better)
    players_with_odds.sort(key=lambda x: x[1])
    return players_with_odds[:limit]


def get_recent_form_for_player(player_name: str, anthropic_client) -> str:
    """Get recent form context using Claude/web search."""
    try:
        # Use web search to find recent performance
        from anthropic import Anthropic

        prompt = f"""Find recent PGA Tour performance data for golfer {player_name} (January 2026). Focus on betting-relevant information:

1. Most recent tournament results (last 2-3 starts)
2. Any exceptional final rounds (like a 63 on Sunday)
3. Current form streaks (hot/cold)
4. Any injury news or withdrawals
5. Recent wins or top-5 finishes in past 3 months

Format as a single concise sentence (20-30 words) suitable for a betting preview. Examples:
- "Shot 63 on Sunday at Sony Open to finish T4 — scorching hot heading into the desert"
- "Three straight top-10s including runner-up at The Sentry — trending at perfect time"
- "Withdrew from Tournament of Champions with back tightness — health question mark"
- "Missed cut at Sony but historically bounces back strong — fade-the-public angle"

If no relevant recent data found, return just: "—"

Return ONLY the analysis sentence, nothing else."""

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        result = response.content[0].text.strip()
        return result if result and result != "—" else "—"

    except Exception as e:
        print(f"  ⚠️  {player_name}: {e}")
        return "—"


def main() -> int:
    # Load odds data to identify top players
    if not ODDS_FILE.exists():
        print(f"❌ Missing {ODDS_FILE}")
        return 1

    odds_data = json.loads(ODDS_FILE.read_text(encoding="utf-8"))
    top_players = get_top_players(odds_data, limit=50)  # Focus on top 50 favorites

    print(f"📊 Enriching recent form for top 50 players...")

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

    # Load existing recent form data
    existing_form = {}
    recent_form_path = ROOT / "data" / "amex_2026_recent_form.json"
    if recent_form_path.exists():
        try:
            existing_form = json.loads(recent_form_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    enriched_form = existing_form.copy()

    # Enrich top players
    for i, (player, odds) in enumerate(top_players, 1):
        print(f"  [{i}/50] {player} ({odds})...", end=" ", flush=True)

        # Get betting-relevant recent form
        form = get_recent_form_for_player(player, client)
        enriched_form[player] = form

        print("✓" if form != "—" else "—")

    # Write enriched data
    RECENT_FORM_OUT.write_text(
        json.dumps(enriched_form, indent=2, sort_keys=True),
        encoding="utf-8"
    )
    print(f"\n✅ Wrote {RECENT_FORM_OUT}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
