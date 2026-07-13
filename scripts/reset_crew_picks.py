#!/usr/bin/env python3
"""
Reset crew picks to the placeholder state for a new tournament week.

Sets placeholder=true (renderer shows "picks coming soon") and blanks every
pick to TBD while preserving crew names, photos, and display order. Run at
the start of the automated Monday publish; picks are filled in Wednesday and
the page redeployed.

Usage:
    python3 scripts/reset_crew_picks.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CREW_PICKS_PATH = PROJECT_ROOT / "data" / "crew_picks.json"

PLACEHOLDER_TEXT = "Crew picks drop Wednesday night"


def main() -> int:
    if not CREW_PICKS_PATH.exists():
        print(f"[ERROR] {CREW_PICKS_PATH} not found")
        return 1

    data = json.loads(CREW_PICKS_PATH.read_text())

    data["placeholder"] = True
    data["placeholder_text"] = PLACEHOLDER_TEXT

    reset_count = 0
    for member in data.get("crew", []):
        for pick in member.get("picks", []):
            if pick.get("player") != "TBD" or pick.get("odds") != "-":
                reset_count += 1
            pick["player"] = "TBD"
            pick["odds"] = "-"

    CREW_PICKS_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"[OK] Crew picks reset to placeholder state "
          f"({len(data.get('crew', []))} members, {reset_count} picks cleared)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
