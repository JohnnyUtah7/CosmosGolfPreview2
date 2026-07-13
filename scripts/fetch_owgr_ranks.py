#!/usr/bin/env python3
"""
Fetch OWGR (Official World Golf Ranking) for all players missing it.

Uses Claude API to look up current OWGR rankings for players.

Usage:
    python scripts/fetch_owgr_ranks.py --players-data data/wm_phoenix_open_2026_players_data.json
    python scripts/fetch_owgr_ranks.py --tournament "WM Phoenix Open" --year 2026
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


def get_owgr_for_player(player_name: str, player_country: str, client) -> str:
    """Get OWGR rank using Claude."""
    try:
        prompt = f"""What is the current Official World Golf Ranking (OWGR) for {player_name} ({player_country}) as of January 2026?

Return ONLY the numeric rank (e.g., "42" or "156"), nothing else.
If the player is unranked or you cannot find the ranking, return "—"."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text.strip()

        # Clean up formatting
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]

        # Remove any # symbols
        result = result.replace("#", "").strip()

        # Check if it's a valid number
        if result.isdigit():
            return result

        return ""

    except Exception as e:
        print(f" ERROR: {e}")
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch OWGR for players missing it (Claude API)")
    parser.add_argument("--players-data", type=Path, help="Path to players_data.json")
    parser.add_argument("--tournament", type=str, help="Tournament name (e.g. WM Phoenix Open)")
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

    # Load player data
    players_data = json.loads(path.read_text(encoding="utf-8"))
    players = players_data.get("players", {})

    # Find players missing OWGR
    missing_owgr = []
    for player_name, player_info in players.items():
        owgr = player_info.get("owgr", "")
        if not owgr or not str(owgr).strip():
            country = player_info.get("country", "USA")
            missing_owgr.append((player_name, country))

    print(f"📊 Found {len(missing_owgr)} players missing OWGR rank")
    print(f"🔄 Fetching OWGR ranks using Claude API...\\n")

    updated_count = 0
    for i, (player_name, country) in enumerate(missing_owgr, 1):
        print(f"  [{i}/{len(missing_owgr)}] {player_name:30s} ({country:3s})...", end=" ", flush=True)

        owgr = get_owgr_for_player(player_name, country, client)

        if owgr:
            players[player_name]["owgr"] = owgr
            updated_count += 1
            print(f"✓ (#{owgr})")
        else:
            print("—")

        # Save progress every 20 players
        if i % 20 == 0:
            players_data["players"] = players
            path.write_text(
                json.dumps(players_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"    💾 Progress saved ({updated_count} updated so far)")

    # Final save
    players_data["players"] = players
    path.write_text(
        json.dumps(players_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n✅ Complete! Updated {updated_count}/{len(missing_owgr)} players with OWGR ranks")
    print(f"💾 Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
