#!/usr/bin/env python3
"""
Import a DraftKings odds paste into our data files (legacy / fallback).

PREFERRED: Use Data Golf for odds going forward (no manual paste):
  python scripts/refresh_odds_from_datagolf.py --players-data data/<tournament>_<year>_players_data.json --year <year>
The weekly orchestrator uses Data Golf by default.

This script remains for manual paste when Data Golf is unavailable.

Input: a plain text file containing repeated blocks:
  Player Name
  +WIN
  +TOP5 (or -TOP5)
  +TOP10 (or -TOP10)

Output/side-effects:
- Updates win odds JSON and players_data (odds section: win/top5/top10)
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_minus(s: str) -> str:
    # DK paste often uses unicode minus (U+2212)
    return (s or "").replace("−", "-").strip()


def _parse_american_odds(s: str) -> int | None:
    t = _normalize_minus(s)
    t = t.replace(",", "")
    if not t:
        return None
    if t.startswith("+"):
        t = t[1:]
    if re.fullmatch(r"-?\d{2,7}", t):
        return int(t)
    return None


def _is_header_line(line: str) -> bool:
    l = (line or "").strip().lower()
    if not l:
        return True
    return l in {
        "the american express 2026",
        "thu jan 22nd 12:00 am",
        "winner",
        "top 5 (including ties)",
        "top 10 (including ties)",
    }


def parse_dk_text(text: str) -> tuple[dict[str, dict[str, int]], list[str]]:
    """
    Returns:
      odds_by_player: {name: {"win": int, "top5": int, "top10": int}}
      warnings: list of strings
    """
    warnings: list[str] = []
    lines = [_normalize_minus(ln) for ln in (text or "").splitlines()]
    # keep non-empty non-header lines
    cleaned = [ln for ln in lines if ln and not _is_header_line(ln)]

    odds_by_player: dict[str, dict[str, int]] = {}

    i = 0
    while i < len(cleaned):
        name = cleaned[i].strip()
        # names should not look like odds
        if _parse_american_odds(name) is not None:
            i += 1
            continue

        win = _parse_american_odds(cleaned[i + 1]) if i + 1 < len(cleaned) else None
        top5 = _parse_american_odds(cleaned[i + 2]) if i + 2 < len(cleaned) else None
        top10 = _parse_american_odds(cleaned[i + 3]) if i + 3 < len(cleaned) else None

        if win is None or top5 is None or top10 is None:
            # Not a full block; advance
            i += 1
            continue

        if name in odds_by_player:
            prev = odds_by_player[name]
            # If duplicates, keep the *shorter* win odds as the "more current/likely" line.
            # (DK list sometimes repeats a name with a later refresh.)
            if win != prev["win"] or top5 != prev["top5"] or top10 != prev["top10"]:
                warnings.append(
                    f"Duplicate '{name}' encountered: "
                    f"existing(win={prev['win']},top5={prev['top5']},top10={prev['top10']}) "
                    f"new(win={win},top5={top5},top10={top10}). Keeping shorter win odds."
                )
                # choose the more favored (lower positive, more negative)
                def _fav(a: int, b: int) -> int:
                    # lower is more favored for positive odds; more negative is more favored for negatives
                    if (a >= 0) and (b >= 0):
                        return min(a, b)
                    if (a < 0) and (b < 0):
                        return min(a, b)  # e.g. -310 < -160, keep -310
                    # mixed: treat negative as more favored than positive
                    return a if a < 0 else b

                keep_win = _fav(prev["win"], win)
                keep = prev if keep_win == prev["win"] else {"win": win, "top5": top5, "top10": top10}
                odds_by_player[name] = keep
        else:
            odds_by_player[name] = {"win": win, "top5": top5, "top10": top10}

        i += 4

    if not odds_by_player:
        warnings.append("No player odds blocks parsed. Check input formatting.")

    return odds_by_player, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Import DraftKings odds paste")
    parser.add_argument("--input", type=Path, help="Path to DK paste text file")
    parser.add_argument("--players-data", type=Path, help="Players-data JSON to update/merge")
    parser.add_argument("--win-odds-json", type=Path, help="Flat win odds JSON (player -> win odds int)")
    parser.add_argument("--tournament", type=str, help="Tournament name (to derive paths if not given)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    args = parser.parse_args()

    slug = _slugify(args.tournament) if args.tournament else None
    if args.players_data is None and slug:
        args.players_data = PROJECT_ROOT / "data" / f"{slug}_{args.year}_players_data.json"
    if args.input is None and slug:
        args.input = PROJECT_ROOT / "data" / f"{slug}_{args.year}_draftkings_odds.txt"
    if args.win_odds_json is None and slug:
        args.win_odds_json = PROJECT_ROOT / "data" / f"{slug}_{args.year}_odds.json"
    if args.players_data is None or args.input is None:
        print("❌ Provide --players-data and --input, or --tournament (and optional --year)")
        return 1

    text = args.input.read_text(encoding="utf-8")
    dk_odds, warnings = parse_dk_text(text)

    # Write/update flat win odds mapping
    win_map = {name: info["win"] for name, info in dk_odds.items()}
    win_sorted = dict(sorted(win_map.items(), key=lambda kv: kv[1]))
    args.win_odds_json.parent.mkdir(parents=True, exist_ok=True)
    args.win_odds_json.write_text(json.dumps(win_sorted, indent=2), encoding="utf-8")

    # Merge into players-data bundle
    bundle: dict[str, Any] = {}
    if args.players_data.exists():
        try:
            bundle = json.loads(args.players_data.read_text(encoding="utf-8"))
        except Exception:
            bundle = {}
    if not isinstance(bundle, dict):
        bundle = {}

    bundle.setdefault("tournament", {"name": "The American Express"})
    bundle.setdefault("players", {})
    bundle.setdefault("historical", {})
    bundle.setdefault("odds", {})

    for name, info in dk_odds.items():
        bundle["odds"][name] = {
            "bookmaker": "DraftKings",
            "odds": int(info["win"]),
            "top5": int(info["top5"]),
            "top10": int(info["top10"]),
            "imported_at": _now_iso(),
        }
        bundle["players"].setdefault(name, {})
        bundle["historical"].setdefault(name, {})

    # Add metadata
    bundle["metadata"] = {
        "updated_at": _now_iso(),
        "source": "DraftKings paste",
        "player_count": len(bundle.get("odds", {})),
    }

    args.players_data.parent.mkdir(parents=True, exist_ok=True)
    args.players_data.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    print(f"✅ Parsed DK odds for {len(dk_odds)} players")
    print(f"✅ Updated {args.win_odds_json} (win odds only)")
    print(f"✅ Updated {args.players_data} (win/top5/top10)")
    if warnings:
        print("\nWarnings:")
        for w in warnings[:25]:
            print(f"- {w}")
        if len(warnings) > 25:
            print(f"- ... {len(warnings) - 25} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

