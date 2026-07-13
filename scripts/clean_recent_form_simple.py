#!/usr/bin/env python3
"""
Clean recent form data: remove junk, keep last events with finishes.

Usage:
  python scripts/clean_recent_form_simple.py --tournament "WM Phoenix Open" --year 2026
  python scripts/clean_recent_form_simple.py --players-data data/.../players_data.json --recent-form data/.../recent_form.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ============================================================================
# RECENT FORM CONFIGURATION - Update this as the 2026 season progresses!
# ============================================================================
# Priority events for recent form (most recent first, ordered by importance)
# Update this list after each tournament week completes
PRIORITY_EVENTS_2026 = [
    # 2026 PGA Tour events (add new ones at the top as they complete)
    "WM Phoenix Open (Feb 2026)",       # Week 5
    "Farmers Insurance Open (Jan 2026)", # Week 4
    "American Express (Jan 2026)",       # Week 3
    "Sony Open in Hawaii (Jan 2026)",    # Week 2
    "The Sentry (Jan 2026)",             # Week 1 (winners/invite only)
]

FALLBACK_EVENTS_2025 = [
    # Late 2025 events for context
    "RSM Classic (Nov 2025)",
    "Houston Open (Nov 2025)",
    "Mayakoba (Nov 2025)",
    "Hero World Challenge (Dec 2025)",     # Unofficial but important
    "DP World Tour Championship (Nov 2025)",
    "Nedbank Golf Challenge (Dec 2025)",
]

CURRENT_MONTH = "February 2026"  # Update this each month
# ============================================================================


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")

def is_junk_data(text: str) -> bool:
    """Check if entry is junk (AI error message or news headline)."""
    if not text or text.strip() == "—":
        return False  # "—" is acceptable

    # AI error messages (multiple patterns to catch all variations)
    ai_error_indicators = [
        "I don't have access",
        "I cannot provide",
        "my knowledge",
        "knowledge cutoff",
        "real-time",
        "I'd recommend checking",
        "cannot browse",
        "up to my knowledge cutoff"
    ]

    for indicator in ai_error_indicators:
        if indicator in text:
            return True

    # News headlines without tournament results
    junk_patterns = [
        r"american express.*odds.*predictions",
        r"best bets",
        r"tickets.*parking",
        r"prize money",
        r"expert picks",
        r"betting tips",
        r"DFS.*picks",
        r"commits to.*field",
        r"launches.*GC",
        r"after playing.*hole",
        r"ties course record",
        r"things to do include",
        r"almost died",
        r"no days off",
        r"world no\. \d+",
        r"slowest in the world",
    ]

    text_lower = text.lower()
    for pattern in junk_patterns:
        if re.search(pattern, text_lower):
            return True

    # Check if it looks like a valid result
    valid_patterns = [
        r"\((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\)",  # (Jan 2026)
        r"T\d+",  # T4, T29, etc.
        r"MC",    # Missed cut
        r"WD",    # Withdrew
        r"\d{1,3}(?:st|nd|rd|th)",  # 1st, 2nd, etc.
        r"Korn Ferry Tour",  # Valid tour reference
    ]

    for pattern in valid_patterns:
        if re.search(pattern, text):
            return False  # Has valid tournament result format

    return True  # Everything else is junk


def clean_entry(text: str) -> str:
    """Clean a single entry, converting to — if it's junk."""
    if is_junk_data(text):
        return "—"
    return text.strip()


def get_recent_form_for_player(player_name: str, player_country: str, client, current_tournament: str = None) -> str:
    """Get last 3-4 tournament results using Claude with extended search."""
    try:
        # Build priority list from config
        priority_2026 = "\n".join(f"{i+1}. {evt}" for i, evt in enumerate(PRIORITY_EVENTS_2026))
        fallback_2025 = "\n".join(f"{i+len(PRIORITY_EVENTS_2026)+1}. {evt}" for i, evt in enumerate(FALLBACK_EVENTS_2025))

        prompt = f"""Find the last 3-4 golf tournament results for {player_name} ({player_country}) as of {CURRENT_MONTH}.

PRIORITY - 2026 PGA Tour events (show these FIRST if player competed):
{priority_2026}

Then fall back to late 2025 events:
{fallback_2025}

CRITICAL RULES:
- ALWAYS show missed cuts as "MC" - this is important betting info!
- Show most recent tournaments first, then work backwards
- Include 3-4 events if available (more context is better for betting)
- If player shot a hot final round (63-66), mention it! e.g., "(shot 63 Sunday)"
- WD = withdrew, DQ = disqualified - include these too
- If you cannot find ANY tournament data, return ONLY "—"

FORMAT - separate with " • " bullet:
- "WM Phoenix Open (Feb 2026): T11 • Farmers Insurance Open (Jan 2026): MC • American Express (Jan 2026): T6"
- "American Express (Jan 2026): T4 (shot 64 Sunday) • Sony Open (Jan 2026): MC • RSM Classic (Nov 2025): T15"
- "Sony Open (Jan 2026): Won • Hero World Challenge (Dec 2025): T3 • DP World Tour Championship (Nov 2025): T8"

If player has 3-4 events: show all separated by " • "
If player has 1-2 events: show what's available
If player has 0 events or no data found: return ONLY "—"

Return ONLY the formatted results or —, nothing else. Never return error messages."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text.strip()

        # Clean up formatting
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]

        # Remove any extra explanations
        if "\n\n" in result:
            result = result.split("\n\n")[0]

        return result if result and result != "—" else "—"

    except Exception as e:
        print(f" ERROR: {e}")
        return "—"


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean recent form data (remove junk, optional AI refresh)")
    parser.add_argument("--players-data", type=Path, help="Path to players_data.json")
    parser.add_argument("--recent-form", type=Path, help="Path to recent_form.json")
    parser.add_argument("--tournament", type=str, help="Tournament name (to derive paths)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    if args.players_data is not None and args.recent_form is not None:
        players_data_path = Path(args.players_data)
        recent_form_path = Path(args.recent_form)
        if not players_data_path.is_absolute():
            players_data_path = ROOT / players_data_path
        if not recent_form_path.is_absolute():
            recent_form_path = ROOT / recent_form_path
    elif args.tournament:
        slug = _slugify(args.tournament)
        players_data_path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
        recent_form_path = ROOT / "data" / f"{slug}_{args.year}_recent_form.json"
    else:
        print("❌ Provide --players-data and --recent-form, or --tournament (and optional --year)")
        return 1

    if not recent_form_path.exists():
        print(f"❌ Missing {recent_form_path}")
        return 1
    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    recent_form = json.loads(recent_form_path.read_text(encoding="utf-8"))
    players_data = json.loads(players_data_path.read_text(encoding="utf-8"))
    odds_data = players_data.get("odds", {})

    # Get player countries
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

    print("🧹 Phase 1: Cleaning junk data...")
    cleaned_count = 0
    for player in list(recent_form.keys()):
        original = recent_form[player]
        cleaned = clean_entry(original)
        if cleaned != original:
            recent_form[player] = cleaned
            cleaned_count += 1

    print(f"   Cleaned {cleaned_count} junk entries to —")

    # Find players needing new data (now showing —)
    players_needing_data = []
    for player, form_text in recent_form.items():
        if form_text.strip() == "—":
            players_needing_data.append((player, player_odds.get(player, 999999)))

    # Sort by odds (favorites first)
    players_needing_data.sort(key=lambda x: x[1])

    print(f"\n📊 Phase 2: Fetching recent form for {len(players_needing_data)} players...")
    print(f"   (Prioritizing favorites by odds)\n")

    # Initialize Anthropic client
    try:
        from anthropic import Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ ANTHROPIC_API_KEY not set")
            print("   Skipping AI-powered data fetch")
            return 0
        client = Anthropic(api_key=api_key)
    except ImportError:
        print("❌ anthropic package not installed")
        print("   Skipping AI-powered data fetch")
        return 0

    updated_count = 0
    for i, (player, odds) in enumerate(players_needing_data, 1):
        country = player_countries.get(player, "USA")
        print(f"  [{i}/{len(players_needing_data)}] {player:30s} ({country:3s}, {odds:6d})...", end=" ", flush=True)

        new_form = get_recent_form_for_player(player, country, client)
        recent_form[player] = new_form

        if new_form != "—":
            updated_count += 1
            print(f"✓")
        else:
            print("—")

        if i % 20 == 0:
            recent_form_path.write_text(
                json.dumps(recent_form, indent=2, sort_keys=True),
                encoding="utf-8"
            )
            print(f"    💾 Progress saved ({updated_count} updated so far)")

    recent_form_path.write_text(
        json.dumps(recent_form, indent=2, sort_keys=True),
        encoding="utf-8"
    )

    print(f"\n✅ Complete!")
    print(f"   Phase 1: Cleaned {cleaned_count} junk entries")
    print(f"   Phase 2: Updated {updated_count}/{len(players_needing_data)} players with new data")
    print(f"   💾 Wrote {recent_form_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
