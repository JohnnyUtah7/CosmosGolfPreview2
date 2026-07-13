#!/usr/bin/env python3
"""
Audit recent form data for a tournament.

Uses the PGA schedule to determine which events should appear in recent form
(Pebble, Genesis/Riviera, Cognizant, etc.) and checks:
1. That recent form mentions those key events where expected
2. Players with empty or very short form
3. Narrative text that might be incorrect (e.g. "nearly won" from wrong event)

Usage:
    python scripts/audit_recent_form.py --tournament "Arnold Palmer Invitational" --year 2026
    python scripts/audit_recent_form.py --tournament "The Genesis Invitational" --year 2026
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCHEDULE_PATH = PROJECT_ROOT / "data" / "pga_schedule_2026.json"


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def load_schedule() -> dict:
    if not SCHEDULE_PATH.exists():
        return {"tournaments": [], "fall_schedule": []}
    return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))


def get_events_before_tournament(
    schedule: dict, current_tournament_name: str, year: int, max_events: int = 6
) -> list[str]:
    """Return display names of events that should appear in recent form (most recent first)."""
    all_t = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])
    dated = []
    for t in all_t:
        start = (t.get("dates") or {}).get("start")
        if not start:
            continue
        try:
            from datetime import datetime
            d = datetime.strptime(start, "%Y-%m-%d").date()
            dated.append((t, d))
        except ValueError:
            continue
    dated.sort(key=lambda x: x[1])

    current_slug = _slugify(current_tournament_name)
    idx = None
    for i, (t, _) in enumerate(dated):
        if t.get("slug") == current_slug or _slugify(t.get("name", "")) == current_slug:
            idx = i
            break
        if current_tournament_name.lower() in (t.get("name") or "").lower():
            idx = i
            break
    if idx is None or idx == 0:
        return []

    before = dated[:idx]
    take = before[-max_events:] if len(before) >= max_events else before
    take.reverse()
    labels = []
    for t, _ in take:
        name = t.get("name", "")
        if "American Express" in name or "The American Express" in name:
            labels.append("American Express")
        elif "Sony Open" in name:
            labels.append("Sony Open")
        elif "Genesis" in name and "Invitational" in name:
            labels.append("Genesis")  # also match "Riviera"
        elif "Pebble Beach" in name:
            labels.append("Pebble")
        elif "Cognizant" in name:
            labels.append("Cognizant")
        else:
            labels.append(name)
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit recent form for a tournament")
    parser.add_argument(
        "--tournament",
        type=str,
        default="Arnold Palmer Invitational presented by Mastercard",
        help="Current tournament name",
    )
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args()

    slug = _slugify(args.tournament)
    recent_form_path = PROJECT_ROOT / "data" / f"{slug}_{args.year}_recent_form.json"

    if not recent_form_path.exists():
        print(f"❌ No recent form at {recent_form_path}")
        print("   Run: python scripts/build_recent_form_from_cache.py --tournament \"...\" --year 2026")
        print("   Or:  python scripts/refresh_recent_form_from_datagolf.py --tournament \"...\" --year 2026")
        return 1

    recent_form = json.loads(recent_form_path.read_text(encoding="utf-8"))
    schedule = load_schedule()
    key_events = get_events_before_tournament(schedule, args.tournament, args.year)

    # Regexes for key events (Pebble, Riviera/Genesis, Cognizant)
    pebble_re = re.compile(r"Pebble Beach|AT&T Pebble|Pebble", re.I)
    genesis_re = re.compile(r"Genesis|Riviera", re.I)
    cognizant_re = re.compile(r"Cognizant|Palm Beaches", re.I)

    print("=" * 70)
    print(f"RECENT FORM AUDIT: {args.tournament} {args.year}")
    print("=" * 70)
    print(f"\nEvents that should appear in recent form (before this tournament):")
    for e in key_events:
        print(f"  • {e}")
    print()

    missing_pebble = []
    missing_genesis = []
    missing_cognizant = []
    has_narrative = []
    empty_or_short = []
    total = len(recent_form)
    with_data = sum(1 for v in recent_form.values() if v and v.strip() not in ("—", ""))

    for player, form in recent_form.items():
        if not form or form.strip() in ("—", ""):
            empty_or_short.append(player)
            continue
        if len(form) < 30:
            empty_or_short.append(player)
        # Only flag missing key events for players who have some form (so we expect recent events)
        if len(form) > 20:
            if any("Pebble" in e for e in key_events) and not pebble_re.search(form):
                missing_pebble.append((player, form[:100] + "..." if len(form) > 100 else form))
            if any("Genesis" in e for e in key_events) and not genesis_re.search(form):
                missing_genesis.append((player, form[:100] + "..." if len(form) > 100 else form))
            if any("Cognizant" in e for e in key_events) and not cognizant_re.search(form):
                missing_cognizant.append((player, form[:100] + "..." if len(form) > 100 else form))
        if re.search(r"nearly|struggled|returning|maiden|shot \d+|playoff", form, re.I):
            has_narrative.append((player, form[:100] + "..." if len(form) > 100 else form))

    print(f"Summary: {total} players, {with_data} with non-empty form")
    print()

    if missing_pebble:
        print(f"⚠️  Players with form but NO Pebble Beach mention ({len(missing_pebble)}):")
        for p, f in missing_pebble[:12]:
            print(f"   • {p}: {f}")
        if len(missing_pebble) > 12:
            print(f"   ... and {len(missing_pebble) - 12} more")
        print()

    if missing_genesis:
        print(f"⚠️  Players with form but NO Genesis/Riviera mention ({len(missing_genesis)}):")
        for p, f in missing_genesis[:12]:
            print(f"   • {p}: {f}")
        if len(missing_genesis) > 12:
            print(f"   ... and {len(missing_genesis) - 12} more")
        print()

    if missing_cognizant:
        print(f"⚠️  Players with form but NO Cognizant Classic mention ({len(missing_cognizant)}):")
        for p, f in missing_cognizant[:12]:
            print(f"   • {p}: {f}")
        if len(missing_cognizant) > 12:
            print(f"   ... and {len(missing_cognizant) - 12} more")
        print()

    if has_narrative:
        print(f"ℹ️  Players with narrative/qualitative text ({len(has_narrative)}):")
        for p, f in has_narrative[:8]:
            print(f"   • {p}: {f}")
        if len(has_narrative) > 8:
            print(f"   ... and {len(has_narrative) - 8} more")
        print()

    if empty_or_short:
        print(f"⚠️  Players with empty or very short form ({len(empty_or_short)}):")
        for p in empty_or_short[:15]:
            print(f"   • {p}")
        if len(empty_or_short) > 15:
            print(f"   ... and {len(empty_or_short) - 15} more")
        print()

    # Sample a couple of players
    samples = ["Scottie Scheffler", "Jordan Spieth", "Hideki Matsuyama"]
    for s in samples:
        if s in recent_form:
            print(f"Sample - {s}:")
            print(f"   {recent_form[s]}")
            print()

    print("=" * 70)
    print("Recommendations:")
    print("  1. Rebuild from cache (includes Pebble/Genesis when caches exist):")
    print(f'     python scripts/build_recent_form_from_cache.py --tournament "{args.tournament}" --year {args.year}')
    print("  2. Or refresh from Data Golf (API event finishes):")
    print(f'     python scripts/refresh_recent_form_from_datagolf.py --tournament "{args.tournament}" --year {args.year} --max-events 5')
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
