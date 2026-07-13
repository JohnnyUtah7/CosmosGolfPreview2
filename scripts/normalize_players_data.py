#!/usr/bin/env python3
"""
Normalize/merge duplicate player keys in a players-data bundle.

Sometimes upstream odds feeds include the same player under slightly different casing
(e.g. "Erik van Rooyen" vs "Erik Van Rooyen"). This script merges those entries
across odds/players/historical.

Usage:
  python3 scripts/normalize_players_data.py --players-data data/amex_2026_players_data.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _key_norm(name: str) -> str:
    # Case/space/punctuation-insensitive key used only for grouping.
    n = name.strip().casefold()
    n = re.sub(r"[^\w\s]+", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _pick_canonical(names: list[str]) -> str:
    # Prefer the variant with more lowercase letters (keeps "van", "de", etc).
    def score(n: str) -> tuple[int, int, str]:
        lower_letters = sum(1 for ch in n if ch.isalpha() and ch.islower())
        return (lower_letters, -len(n), n)

    return sorted(names, key=score, reverse=True)[0]


def _merge_dict_prefer_nonempty(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k not in out or out[k] in ("", None, {}, []):
            out[k] = v
    return out


def _merge_odds_entries(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    # Merge two odds dicts; prefer the better (lower) win odds when both present.
    out = _merge_dict_prefer_nonempty(a, b)
    try:
        ao = int(a.get("odds")) if isinstance(a.get("odds"), (int, str)) else None
    except Exception:
        ao = None
    try:
        bo = int(b.get("odds")) if isinstance(b.get("odds"), (int, str)) else None
    except Exception:
        bo = None
    if ao is not None and bo is not None:
        out["odds"] = min(ao, bo)
    elif ao is not None:
        out["odds"] = ao
    elif bo is not None:
        out["odds"] = bo
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize/merge duplicate player keys in players-data bundle")
    parser.add_argument("--players-data", type=Path, required=True, help="Players-data JSON bundle to normalize")
    args = parser.parse_args()

    raw = _load_json(args.players_data)
    odds = _as_dict(raw.get("odds"))
    players = _as_dict(raw.get("players"))
    historical = _as_dict(raw.get("historical"))

    # Build groups based on normalized keys (from odds list; that's the roster).
    groups: dict[str, list[str]] = defaultdict(list)
    for name in odds.keys():
        groups[_key_norm(str(name))].append(str(name))

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    if not dup_groups:
        print("✅ No duplicate player keys found.")
        return 0

    # Canonicalize all three sections.
    new_odds: dict[str, Any] = {}
    new_players: dict[str, Any] = {}
    new_historical: dict[str, Any] = {}

    for norm_key, name_list in groups.items():
        canon = _pick_canonical(name_list)

        # Odds
        merged_odds: dict[str, Any] = {}
        for n in name_list:
            entry = _as_dict(odds.get(n))
            merged_odds = _merge_odds_entries(merged_odds, entry)
        if merged_odds:
            new_odds[canon] = merged_odds

        # Players info
        merged_player: dict[str, Any] = {}
        for n in name_list:
            merged_player = _merge_dict_prefer_nonempty(merged_player, _as_dict(players.get(n)))
        if merged_player:
            new_players[canon] = merged_player
        else:
            new_players.setdefault(canon, {})

        # Historical
        merged_hist: dict[str, Any] = {}
        for n in name_list:
            merged_hist = _merge_dict_prefer_nonempty(merged_hist, _as_dict(historical.get(n)))
        if merged_hist:
            new_historical[canon] = merged_hist
        else:
            new_historical.setdefault(canon, {})

    raw["odds"] = new_odds
    raw["players"] = new_players
    raw["historical"] = new_historical

    _dump_json(args.players_data, raw)
    print(f"✅ Normalized duplicate player keys in {args.players_data}")
    print("Merged groups:")
    for _, name_list in sorted(dup_groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0].lower())):
        canon = _pick_canonical(name_list)
        print(f"- {canon} <= {', '.join(name_list)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

