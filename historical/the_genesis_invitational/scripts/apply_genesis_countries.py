#!/usr/bin/env python3
"""
Populate country for every player in Genesis players_data using cache + overrides + aliases.
Fixes HTML showing all players as USA (e.g. Tommy Fleetwood).
"""

from __future__ import annotations

import json
from pathlib import Path

# Run from project root. Genesis data lives in historical/the_genesis_invitational/data/
_HERE = Path(__file__).resolve().parent  # .../historical/the_genesis_invitational/scripts
GENESIS_ROOT = _HERE.parent  # historical/the_genesis_invitational
PROJECT_ROOT = _HERE.parent.parent.parent  # project root (data/player_country_*.json)

# Aliases: Genesis field name -> cache/override name, or direct code for names not in cache
NAME_TO_COUNTRY_ALIAS: dict[str, str] = {
    "Nico Echavarria": "COL",  # cache has "Nicolas Echavarria"
    "Matti Schmid": "GER",     # cache has "Matthias Schmid"
    "Tommy Fleetwood": "ENG",
    "Rory McIlroy": "NIR",
    "Matt Fitzpatrick": "ENG",
    "Robert MacIntyre": "SCO",
    "Sepp Straka": "AUT",
    "Viktor Hovland": "NOR",
    "Nick Taylor": "CAN",
    "Shane Lowry": "IRL",
    "Harry Hall": "WAL",
    "Corey Conners": "CAN",
    "Ryan Fox": "NZL",
}


def main() -> int:
    players_path = GENESIS_ROOT / "data" / "the_genesis_invitational_2026_players_data.json"
    cache_path = PROJECT_ROOT / "data" / "player_country_cache.json"
    overrides_path = PROJECT_ROOT / "data" / "player_country_overrides.json"

    raw = json.loads(players_path.read_text(encoding="utf-8"))
    players = raw.get("players") or {}
    odds_names = list(raw.get("odds") or {})

    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else {}
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    def code(name: str) -> str:
        c = (overrides.get(name) or NAME_TO_COUNTRY_ALIAS.get(name) or cache.get(name) or "USA")
        return (c or "USA").strip().upper()

    updated = 0
    for name in odds_names:
        info = players.get(name)
        if not isinstance(info, dict):
            info = {}
            players[name] = info
        current = (info.get("country") or "").strip().upper()
        new_code = code(name)
        if current != new_code:
            info["country"] = new_code
            players[name] = info
            updated += 1

    raw["players"] = players
    players_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Set country for {updated} players in {players_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
