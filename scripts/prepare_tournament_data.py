#!/usr/bin/env python3
"""
DEPRECATED: Use the weekly orchestrator instead.

    python scripts/weekly_tournament_orchestrator.py
    # or: ./run_weekly.sh

This script referenced removed scripts (complete_amex_history.py, generate_american_express.py)
and is kept only for reference. For weekly generation, run weekly_tournament_orchestrator.py;
it runs: refresh_odds_from_datagolf → apply_owgr → storylines → generate_tournament_html.

Legacy description:
  Automated Tournament Data Preparation - ran historical, OWGR, recent form, weather, HTML.
  Default was american_express_2026.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_script(script_name: str, description: str) -> int:
    """Run a Python script and return its exit code."""
    script_path = ROOT / "scripts" / script_name

    print(f"\n{'=' * 80}")
    print(f"🔄 {description}")
    print(f"{'=' * 80}\n")

    result = subprocess.run(
        ["python3", str(script_path)],
        cwd=str(ROOT)
    )

    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return result.returncode

    print(f"\n✅ {description} completed successfully")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="(Deprecated) Prepare tournament data. Prefer: python scripts/weekly_tournament_orchestrator.py"
    )
    parser.add_argument(
        "--tournament",
        default="american_express_2026",
        help="Tournament identifier (default: american_express_2026)"
    )
    parser.add_argument(
        "--skip-historical",
        action="store_true",
        help="Skip historical tournament results (use if already collected)"
    )
    parser.add_argument(
        "--skip-owgr",
        action="store_true",
        help="Skip OWGR rank updates (use if already collected)"
    )
    parser.add_argument(
        "--skip-recent-form",
        action="store_true",
        help="Skip recent form updates (use if already collected)"
    )
    parser.add_argument(
        "--skip-weather",
        action="store_true",
        help="Skip weather forecast (use if not needed)"
    )

    args = parser.parse_args()

    print("""
⚠️  DEPRECATED: Use the weekly orchestrator instead:
    python scripts/weekly_tournament_orchestrator.py
    or: ./run_weekly.sh

This script may fail (references removed scripts). Continuing anyway...
""")

    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  COSMOS GOLF - TOURNAMENT DATA PREPARATION                   ║
║                          {args.tournament:^50s}║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    steps = []

    # Step 1: Historical Tournament Results
    if not args.skip_historical:
        steps.append((
            "complete_amex_history.py",
            "Fetching historical tournament results (2023-2025)"
        ))

    # Step 2: OWGR Rankings
    if not args.skip_owgr:
        steps.append((
            "update_owgr_from_espn.py",
            "Updating OWGR rankings from ESPN"
        ))

    # Step 3: Recent Form
    if not args.skip_recent_form:
        steps.append((
            "clean_recent_form_simple.py",
            "Fetching recent form data (last 3 tournaments)"
        ))

    # Step 4: Weather Forecast
    if not args.skip_weather:
        steps.append((
            "fetch_tournament_weather.py",
            "Fetching weather forecast for tournament week"
        ))

    # Step 5: Generate HTML
    steps.append((
        "generate_american_express.py",
        "Generating HTML betting preview"
    ))

    # Run all steps
    for i, (script, description) in enumerate(steps, 1):
        print(f"\n📍 Step {i}/{len(steps)}")

        exit_code = run_script(script, description)

        if exit_code != 0:
            print(f"\n\n❌ FAILED at step {i}/{len(steps)}: {description}")
            print("Fix the error and re-run with appropriate --skip-* flags to resume.")
            return exit_code

    print(f"""
\n{'=' * 80}
✅ ALL STEPS COMPLETED SUCCESSFULLY
{'=' * 80}

Tournament data is ready for preview!

Next steps:
1. Review the generated HTML: american_express_2026.html
2. Update crew picks if needed
3. Upload images to Shopify
4. Deploy to Shopify

To re-run individual steps, use:
  --skip-historical    Skip historical results (already collected)
  --skip-owgr          Skip OWGR updates (already collected)
  --skip-recent-form   Skip recent form (already collected)
  --skip-weather       Skip weather forecast (not needed)
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
