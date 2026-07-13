#!/usr/bin/env python3
"""
Move Tournament to Historical

Moves a completed tournament's files from the main editor area (project root + data/)
into historical/{slug}/ so the main list view only shows the current tournament.

Moves:
  - Root HTML: {slug}_{year}.html, {slug}_{year}_v2.html -> historical/{slug}/
  - data/{slug}_*.json -> historical/{slug}/data/
  - data/tournament_results_cache/{slug}_*.json -> historical/{slug}/data/tournament_results_cache/

Usage:
    python scripts/move_tournament_to_historical.py --tournament "Cognizant Classic in The Palm Beaches" --year 2026
    python scripts/move_tournament_to_historical.py --tournament "Cognizant Classic" --year 2026
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HISTORICAL_ROOT = PROJECT_ROOT / "historical"
DATA_ROOT = PROJECT_ROOT / "data"
CACHE_DIR = DATA_ROOT / "tournament_results_cache"


def _slugify(name: str) -> str:
    """Convert tournament name to slug (matches generate_tournament_html / data filenames)."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def move_tournament_to_historical(tournament_name: str, year: int, dry_run: bool = False) -> int:
    """
    Move all files for the given tournament from main (root + data/) to historical/{slug}/.
    Returns the number of files moved.
    """
    prefix = _slugify(tournament_name)
    # Historical folder name: use same prefix as data files (e.g. cognizant_classic_in_the_palm_beaches)
    hist_dir = HISTORICAL_ROOT / prefix
    hist_data = hist_dir / "data"
    hist_cache = hist_data / "tournament_results_cache"

    moved = 0

    # 1) Root HTML files
    for html in PROJECT_ROOT.glob("*.html"):
        stem = html.stem.lower()
        # Match {prefix}_2026 or {prefix}_2026_v2
        if stem == f"{prefix}_{year}" or stem.startswith(f"{prefix}_{year}_"):
            dest = hist_dir / html.name
            if not dry_run:
                hist_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(html), str(dest))
            print(f"[MOVE] {html.name} -> historical/{prefix}/")
            moved += 1

    # 2) data/{prefix}_*.json
    if DATA_ROOT.exists():
        for j in DATA_ROOT.glob(f"{prefix}_*.json"):
            dest = hist_data / j.name
            if not dry_run:
                hist_data.mkdir(parents=True, exist_ok=True)
                shutil.move(str(j), str(dest))
            print(f"[MOVE] data/{j.name} -> historical/{prefix}/data/")
            moved += 1

    # 3) data/tournament_results_cache/{prefix}_*.json
    if CACHE_DIR.exists():
        for c in CACHE_DIR.glob(f"{prefix}_*.json"):
            dest = hist_cache / c.name
            if not dry_run:
                hist_cache.mkdir(parents=True, exist_ok=True)
                shutil.move(str(c), str(dest))
            print(f"[MOVE] data/tournament_results_cache/{c.name} -> historical/{prefix}/data/tournament_results_cache/")
            moved += 1

    return moved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move a tournament's files from main to historical/"
    )
    parser.add_argument("--tournament", type=str, required=True, help="Tournament name (e.g. Cognizant Classic in The Palm Beaches)")
    parser.add_argument("--year", type=int, default=None, help="Year (default: current)")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be moved")
    args = parser.parse_args()

    if args.year is None:
        from datetime import datetime
        args.year = datetime.now().year

    prefix = _slugify(args.tournament)
    print(f"""
{'=' * 60}
 COSMOS Golf - Move Tournament to Historical
 Tournament: {args.tournament}
 Slug: {prefix}
 Year: {args.year}
{'=' * 60}
""")
    if args.dry_run:
        print("[DRY RUN] No files will be moved.\n")

    moved = move_tournament_to_historical(args.tournament, args.year, dry_run=args.dry_run)

    if moved == 0:
        print("[INFO] No files found to move. Files may already be in historical/ or not yet generated.")
        return 0

    print(f"\n[OK] Moved {moved} file(s) to historical/{prefix}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
