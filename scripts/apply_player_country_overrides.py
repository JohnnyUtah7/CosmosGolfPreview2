#!/usr/bin/env python3
"""
Apply `data/player_country_overrides.json` to a players-data bundle in-place.

This is useful when you want the audit JSON itself to carry the fixes (not just
the HTML generator).

Usage:
  python3 scripts/apply_player_country_overrides.py \
    --players-data data/amex_2026_players_data.json \
    --overrides data/player_country_overrides.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from country_utils import normalize_country_code


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply player country overrides to players-data JSON")
    parser.add_argument("--players-data", type=Path, required=True)
    parser.add_argument("--overrides", type=Path, default=Path("data/player_country_overrides.json"))
    args = parser.parse_args()

    raw = json.loads(args.players_data.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit("players-data JSON must be an object")

    overrides_raw = json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides.exists() else {}
    if not isinstance(overrides_raw, dict):
        raise SystemExit("overrides JSON must be an object mapping player -> country code")

    players = _as_dict(raw.get("players"))
    raw["players"] = players

    applied = 0
    for name, code in overrides_raw.items():
        n = str(name)
        c = normalize_country_code(str(code))
        if not c:
            continue
        info = _as_dict(players.get(n))
        if info.get("country") != c:
            info["country"] = c
            players[n] = info
            applied += 1

    args.players_data.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Applied {applied} overrides to {args.players_data}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

