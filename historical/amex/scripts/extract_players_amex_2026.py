#!/usr/bin/env python3
"""
Extract structured player data from `scripts/generate_american_express.py`.

This creates a JSON file compatible with `scripts/generate_storylines.py` so we
can regenerate storylines safely (and without hard-coded claims).

Usage:
  python scripts/extract_players_amex_2026.py --output data/amex_2026_players_data.json
"""

import argparse
import json
from pathlib import Path
import importlib.util


def _parse_american_odds(value: str) -> int:
    v = (value or "").strip()
    v = v.replace(",", "")
    if v.startswith("+"):
        v = v[1:]
    try:
        return int(v)
    except Exception:
        return 10000


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract AMEX 2026 player data to JSON")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path")
    args = parser.parse_args()

    # Load `scripts/generate_american_express.py` without requiring `scripts/` to be a package.
    generator_path = Path(__file__).parent / "generate_american_express.py"
    spec = importlib.util.spec_from_file_location("generate_american_express", generator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {generator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]

    PLAYERS = getattr(module, "PLAYERS")
    TOURNAMENT_NAME = getattr(module, "TOURNAMENT_NAME")

    out = {
        "tournament": {"name": TOURNAMENT_NAME},
        "odds": {},
        "players": {},
        "historical": {},
    }

    for p in PLAYERS:
        name = p["name"]
        out["odds"][name] = {
            "bookmaker": "DraftKings",
            "odds": _parse_american_odds(p.get("win_odds", "")),
        }
        out["players"][name] = {
            "country": p.get("country", ""),
            "owgr": p.get("owgr", ""),
        }
        hist = {}
        if p.get("history_2025") and p.get("history_2025") != "NA":
            hist["2025"] = p["history_2025"]
        if p.get("history_2024") and p.get("history_2024") != "NA":
            hist["2024"] = p["history_2024"]
        if p.get("history_2023") and p.get("history_2023") != "NA":
            hist["2023"] = p["history_2023"]
        out["historical"][name] = hist

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"✅ Wrote {len(out['odds'])} players to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

