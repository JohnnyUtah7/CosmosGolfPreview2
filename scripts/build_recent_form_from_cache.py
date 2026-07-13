#!/usr/bin/env python3
"""
Build recent form from tournament results caches.

Uses the PGA schedule to determine which events precede the current tournament,
then merges finishes from those events (Pebble, Genesis/Riviera, Cognizant, etc.)
in chronological order (most recent first). Looks for caches in both data/ and
historical/*/data/tournament_results_cache/.

If the most recent event (e.g. Cognizant 2026) is missing from recent form, add
its cache first: e.g. fetch_tournament_results_web.py --tournament "Cognizant Classic in The Palm Beaches" --year 2026,
or ensure Data Golf historical data is loaded, then re-run this script.

Usage:
    python scripts/build_recent_form_from_cache.py --tournament "Arnold Palmer Invitational" --year 2026
    python scripts/build_recent_form_from_cache.py --tournament "The Genesis Invitational" --year 2026
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "data" / "tournament_results_cache"
HISTORICAL_ROOT = ROOT / "historical"
SCHEDULE_PATH = ROOT / "data" / "pga_schedule_2026.json"

# Max events to include in recent form (most recent first)
DEFAULT_MAX_EVENTS = 13


def normalize_name(name: str) -> str:
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
                    "ñ": "n", "ø": "o", "å": "a", "æ": "ae"}
    s = name.lower()
    for c, r in replacements.items():
        s = s.replace(c, r)
    return s


def fuzzy_match(player: str, leaderboard: dict[str, str]) -> str | None:
    if player in leaderboard:
        return leaderboard[player]
    pnorm = normalize_name(player)
    for name, pos in leaderboard.items():
        if normalize_name(name) == pnorm:
            return pos
    parts = player.split()
    if len(parts) >= 2:
        last = normalize_name(parts[-1])
        fi = normalize_name(parts[0])[0] if parts[0] else ""
        for name, pos in leaderboard.items():
            np = name.split()
            if len(np) >= 2 and normalize_name(np[-1]) == last and normalize_name(np[0])[0] == fi:
                return pos
    return None


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _parse_results_from_cache(data: dict) -> dict[str, str]:
    """Extract player -> finish from cache JSON (handles both wrapped and flat format)."""
    if not isinstance(data, dict):
        return {}
    if "results" in data and isinstance(data["results"], dict):
        return data["results"]
    skip = {"tournament", "year", "fetched_at", "source", "updated_at"}
    return {k: str(v) for k, v in data.items() if k not in skip and isinstance(v, (str, int))}


def load_cache(slug: str, slug_alt: str, year: int) -> dict[str, str]:
    """Load cache from data/tournament_results_cache or historical/*/data/tournament_results_cache."""
    # Try stems: slug, slug_alt, and hyphen/underscore variants (e.g. att_pebble_beach_pro-am)
    stems = [f"{slug}_{year}", f"{slug_alt}_{year}"]
    for s in (slug, slug_alt):
        stems.append(f"{s.replace('-', '_')}_{year}")
        stems.append(f"{s.replace('_', '-')}_{year}")
        stems.append(f"{s.replace('pro_am', 'pro-am')}_{year}")  # Pebble: att_pebble_beach_pro-am
    stems = list(dict.fromkeys(stems))  # dedup

    for stem in stems:
        path = CACHE_DIR / f"{stem}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return _parse_results_from_cache(data)
            except (json.JSONDecodeError, KeyError):
                pass

    # Search historical/*/data/tournament_results_cache
    if HISTORICAL_ROOT.exists():
        for hist_dir in HISTORICAL_ROOT.iterdir():
            if not hist_dir.is_dir():
                continue
            cache_sub = hist_dir / "data" / "tournament_results_cache"
            if not cache_sub.exists():
                continue
            for stem in stems:
                path = cache_sub / f"{stem}.json"
                if path.exists():
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        return _parse_results_from_cache(data)
                    except (json.JSONDecodeError, KeyError):
                        pass
    return {}


def load_schedule() -> dict:
    if not SCHEDULE_PATH.exists():
        return {"tournaments": [], "fall_schedule": []}
    return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))


def get_events_before_tournament(
    schedule: dict, current_tournament_name: str, year: int, max_events: int = DEFAULT_MAX_EVENTS
) -> list[tuple[str, str, str, str]]:
    """
    Return list of (display_name, cache_slug, slug_alt, when_str) for events before the current one.
    Most recent first. Uses schedule slugs and slugify(name) for cache lookup.
    """
    all_t = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])
    dated = []
    for t in all_t:
        start = (t.get("dates") or {}).get("start")
        if not start:
            continue
        try:
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

    # Events before current (take last max_events)
    before = dated[:idx]
    take = before[-max_events:] if len(before) >= max_events else before
    take.reverse()  # most recent first

    out = []
    for t, d in take:
        name = t.get("name", "")
        slug = t.get("slug", _slugify(name))
        slug_alt = _slugify(name)  # e.g. cognizant_classic_in_the_palm_beaches
        when = d.strftime("%b %Y")
        # Short labels for display
        if "American Express" in name or "The American Express" in name:
            label = "American Express"
        elif "Sony Open" in name:
            label = "Sony Open"
        elif "Genesis" in name and "Invitational" in name:
            label = "The Genesis Invitational (Riviera)"
        elif "Pebble Beach" in name:
            label = "AT&T Pebble Beach Pro-Am"
        elif "Cognizant" in name:
            label = "Cognizant Classic"
        else:
            label = name
        out.append((label, slug, slug_alt, when))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build recent form from tournament result caches")
    parser.add_argument("--tournament", default="Arnold Palmer Invitational presented by Mastercard")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS)
    parser.add_argument("--slug", type=str, default=None, help="Explicit data-file slug (overrides slugified --tournament; matches the schedule slug)")
    args = parser.parse_args()

    slug = args.slug or _slugify(args.tournament)
    players_path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    output_path = ROOT / "data" / f"{slug}_{args.year}_recent_form.json"

    if not players_path.exists():
        print(f"❌ Missing {players_path}")
        return 1

    schedule = load_schedule()
    events = get_events_before_tournament(
        schedule, args.tournament, args.year, max_events=args.max_events
    )
    if not events:
        print(f"❌ Could not find tournament in schedule or no events before it: {args.tournament}")
        return 1

    print(f"Events before {args.tournament} (most recent first):")
    for label, _, _, when in events:
        print(f"  • {label} ({when})")
    print()

    players_data = json.loads(players_path.read_text(encoding="utf-8"))
    player_names = list(players_data.get("odds", {}).keys())

    caches = {}
    for display_name, cache_slug, slug_alt, when in events:
        results = load_cache(cache_slug, slug_alt, args.year)
        caches[display_name] = (when, results)
        if results:
            print(f"  ✓ {display_name}: {len(results)} results")

    recent_form = {}
    for player in player_names:
        parts = []
        for display_name, (when, results) in caches.items():
            if not results:
                continue
            pos = fuzzy_match(player, results)
            if pos:
                parts.append(f"{display_name} ({when}): {pos}")

        if parts:
            recent_form[player] = " • ".join(parts)
        else:
            recent_form[player] = "—"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(recent_form, indent=2, ensure_ascii=False), encoding="utf-8")
    with_data = sum(1 for v in recent_form.values() if v and v != "—")
    print(f"\n✅ Built recent form: {len(recent_form)} players ({with_data} with data)")
    print(f"   Output: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
