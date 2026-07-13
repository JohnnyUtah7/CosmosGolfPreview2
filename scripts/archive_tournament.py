#!/usr/bin/env python3
"""
Archive Tournament Preview

Moves completed tournament previews to an organized archive structure.

Archive structure:
    archive/
    └── 2026/
        ├── the_sentry/
        │   ├── index.html          (latest version)
        │   └── preview_2026-01-06.html (dated backup)
        ├── sony_open/
        │   └── ...
        └── archive_index.json      (catalog of all archives)

Usage:
    python scripts/archive_tournament.py --tournament "The American Express" --year 2026
    python scripts/archive_tournament.py --file american_express_2026.html
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
ARCHIVE_ROOT = PROJECT_ROOT / "archive"


def _slugify(name: str) -> str:
    """Convert tournament name to slug."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _now_iso() -> str:
    """Current timestamp in ISO format."""
    return datetime.now().isoformat()


def _today_str() -> str:
    """Today's date as string."""
    return datetime.now().strftime("%Y-%m-%d")


def load_archive_index(year: int) -> dict:
    """Load or create archive index for a year."""
    index_path = ARCHIVE_ROOT / str(year) / "archive_index.json"
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))
    return {
        "year": year,
        "tournaments": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso()
    }


def save_archive_index(year: int, index: dict) -> None:
    """Save archive index."""
    index["updated_at"] = _now_iso()
    index_path = ARCHIVE_ROOT / str(year) / "archive_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def find_html_file(tournament_name: str, year: int) -> Optional[Path]:
    """Find the HTML file for a tournament."""
    slug = _slugify(tournament_name)

    # Try various naming patterns
    patterns = [
        f"{slug}_{year}.html",
        f"{slug.replace('_', '-')}_{year}.html",
        f"{tournament_name.lower().replace(' ', '_')}_{year}.html",
        f"{tournament_name.lower().replace(' ', '-')}-{year}.html",
    ]

    for pattern in patterns:
        path = PROJECT_ROOT / pattern
        if path.exists():
            return path

    # Check for any HTML file with the slug in the name
    for html_file in PROJECT_ROOT.glob("*.html"):
        if slug in html_file.stem.lower():
            return html_file

    # Check historical/<slug>/ for past tournament HTML
    historical_dir = PROJECT_ROOT / "historical" / slug
    if historical_dir.exists():
        for html_file in historical_dir.glob("*.html"):
            return html_file

    return None


def archive_tournament(
    source_file: Path,
    tournament_name: str,
    year: int,
    keep_original: bool = False
) -> tuple[Path, Path]:
    """
    Archive a tournament preview file.

    Args:
        source_file: Path to the HTML file to archive
        tournament_name: Tournament name for organization
        year: Tournament year
        keep_original: If True, copy instead of move

    Returns:
        (index_path, dated_path) - paths to the archived files
    """
    slug = _slugify(tournament_name)
    archive_dir = ARCHIVE_ROOT / str(year) / slug
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Create paths
    index_path = archive_dir / "index.html"
    dated_path = archive_dir / f"preview_{_today_str()}.html"

    # Copy/move the file
    if keep_original:
        shutil.copy2(source_file, index_path)
        shutil.copy2(source_file, dated_path)
        print(f"[COPY] {source_file} -> {index_path}")
    else:
        shutil.copy2(source_file, dated_path)  # Always keep dated backup
        shutil.move(source_file, index_path)
        print(f"[MOVE] {source_file} -> {index_path}")

    print(f"[BACKUP] {dated_path}")

    # Update archive index
    index = load_archive_index(year)

    # Check if tournament already in index
    existing = next(
        (t for t in index["tournaments"] if t.get("slug") == slug),
        None
    )

    if existing:
        existing["updated_at"] = _now_iso()
        existing["versions"] = existing.get("versions", 0) + 1
    else:
        index["tournaments"].append({
            "name": tournament_name,
            "slug": slug,
            "path": str(archive_dir.relative_to(ARCHIVE_ROOT)),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "versions": 1
        })

    save_archive_index(year, index)
    print(f"[INDEX] Updated archive_index.json")

    return index_path, dated_path


def list_archives(year: Optional[int] = None) -> None:
    """List all archived tournaments."""
    if not ARCHIVE_ROOT.exists():
        print("No archives found.")
        return

    years = [year] if year else [int(d.name) for d in ARCHIVE_ROOT.iterdir() if d.is_dir() and d.name.isdigit()]
    years.sort(reverse=True)

    for y in years:
        index = load_archive_index(y)
        tournaments = index.get("tournaments", [])

        if tournaments:
            print(f"\n{'=' * 50}")
            print(f" {y} Season Archives ({len(tournaments)} tournaments)")
            print(f"{'=' * 50}")

            for t in sorted(tournaments, key=lambda x: x.get("created_at", "")):
                versions = t.get("versions", 1)
                updated = t.get("updated_at", "")[:10]
                print(f"  - {t['name']:<35} [{versions} version(s)] {updated}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive tournament preview files"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        help="Tournament name to archive"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Tournament year (default: current year)"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Specific HTML file to archive"
    )
    parser.add_argument(
        "--keep-original",
        action="store_true",
        help="Keep original file (copy instead of move)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all archived tournaments"
    )

    args = parser.parse_args()

    # List mode
    if args.list:
        list_archives(args.year if args.year != datetime.now().year else None)
        return 0

    # Archive mode
    if args.file:
        if not args.file.exists():
            print(f"[ERROR] File not found: {args.file}")
            return 1

        # Extract tournament name from filename if not provided
        tournament_name = args.tournament
        if not tournament_name:
            # Try to parse from filename: some_tournament_2026.html
            stem = args.file.stem
            match = re.match(r"(.+?)_\d{4}$", stem)
            if match:
                tournament_name = match.group(1).replace("_", " ").title()
            else:
                tournament_name = stem.replace("_", " ").title()

        source_file = args.file

    elif args.tournament:
        tournament_name = args.tournament
        source_file = find_html_file(tournament_name, args.year)

        if not source_file:
            print(f"[ERROR] Could not find HTML file for '{tournament_name}'")
            print("Try specifying the file with --file")
            return 1

    else:
        parser.print_help()
        return 1

    print(f"""
{'=' * 60}
 COSMOS Golf - Tournament Archiver
 Tournament: {tournament_name}
 Year: {args.year}
 Source: {source_file}
{'=' * 60}
""")

    index_path, dated_path = archive_tournament(
        source_file,
        tournament_name,
        args.year,
        args.keep_original
    )

    print(f"""
{'=' * 60}
 SUCCESS - Tournament Archived
{'=' * 60}
 Archive location: {index_path.parent}
 Index file: {index_path}
 Dated backup: {dated_path}
{'=' * 60}
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
