#!/usr/bin/env python3
"""
Weekly Tournament Orchestrator

Master automation script that runs the complete tournament preview pipeline:

1. Determine this week's tournament from schedule
2. Move previous week's tournament to historical/ (clean main editor list)
3. Fetch odds (Data Golf API: outright, top 5, top 10)
4. Fetch historical results (cached if available)
5. Fetch tournament result caches from Data Golf (Pebble, Genesis, Cognizant, etc.) and build recent form
6. Fetch OWGR rankings
6. Generate AI storylines (Claude API with fallback)
7. Generate HTML preview
8. Optionally deploy to Shopify

Usage:
    # Automatic - determines tournament from schedule
    python scripts/weekly_tournament_orchestrator.py

    # Override tournament
    python scripts/weekly_tournament_orchestrator.py --tournament "Farmers Insurance Open"

    # Skip specific steps
    python scripts/weekly_tournament_orchestrator.py --skip-archive --skip-storylines

    # Deploy to Shopify
    python scripts/weekly_tournament_orchestrator.py --deploy
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _slugify(name: str) -> str:
    """Convert tournament name to slug."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _now_iso() -> str:
    return datetime.now().isoformat()


def load_schedule() -> dict:
    """Load the PGA schedule database."""
    schedule_path = PROJECT_ROOT / "data" / "pga_schedule_2026.json"
    if schedule_path.exists():
        return json.loads(schedule_path.read_text(encoding="utf-8"))
    return {"tournaments": [], "fall_schedule": []}


def get_this_weeks_tournament(schedule: dict) -> Optional[dict]:
    """
    Find the tournament happening this week.

    Returns the tournament that starts within the next 7 days,
    or the most recent upcoming tournament.
    """
    today = datetime.now().date()
    week_ahead = today + timedelta(days=7)

    all_tournaments = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])

    # Find tournaments starting this week
    candidates = []
    for t in all_tournaments:
        dates = t.get("dates", {})
        start_str = dates.get("start", "")
        if not start_str:
            continue

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()

            # Tournament starts within next 7 days
            if today <= start_date <= week_ahead:
                candidates.append((t, start_date))

            # Or tournament is currently ongoing
            end_str = dates.get("end", start_str)
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            if start_date <= today <= end_date:
                candidates.append((t, start_date))

        except ValueError:
            continue

    if candidates:
        # Return the earliest upcoming tournament
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    # No tournament this week - find next upcoming
    future = []
    for t in all_tournaments:
        dates = t.get("dates", {})
        start_str = dates.get("start", "")
        if not start_str:
            continue

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            if start_date > today:
                future.append((t, start_date))
        except ValueError:
            continue

    if future:
        future.sort(key=lambda x: x[1])
        return future[0][0]

    return None


def get_previous_tournament(schedule: dict, current: dict) -> Optional[dict]:
    """Find the tournament before the current one."""
    all_tournaments = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])

    # Sort by start date
    dated = []
    for t in all_tournaments:
        dates = t.get("dates", {})
        start_str = dates.get("start", "")
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                dated.append((t, start_date))
            except ValueError:
                pass

    dated.sort(key=lambda x: x[1])

    # Find current tournament index
    current_slug = current.get("slug", "")
    for i, (t, _) in enumerate(dated):
        if t.get("slug") == current_slug and i > 0:
            return dated[i - 1][0]

    return None


def run_script(script_name: str, args: list[str] = None, description: str = "") -> int:
    """Run a Python script and return exit code."""
    script_path = PROJECT_ROOT / "scripts" / script_name

    if not script_path.exists():
        print(f"[SKIP] Script not found: {script_name}")
        return 0

    cmd = ["python3", str(script_path)]
    if args:
        cmd.extend(args)

    print(f"\n{'=' * 60}")
    print(f"[STEP] {description or script_name}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def fetch_historical_results(tournament_name: str, slug: str, year: int, years: list[int]) -> int:
    """Fetch historical tournament results, apply to players_data, and sync historical section."""
    cache_dir = PROJECT_ROOT / "data" / "tournament_results_cache"
    players_data_path = PROJECT_ROOT / "data" / f"{slug}_{year}_players_data.json"

    # Step A: Fetch from Data Golf if cache is missing
    history_years = [y for y in years if y != year]  # exclude current year
    missing = [y for y in history_years if not (cache_dir / f"{slug}_{y}.json").exists()]

    if missing:
        print(f"[INFO] Fetching historical results for missing years: {missing}")
        fetch_script = PROJECT_ROOT / "scripts" / "fetch_historical_from_datagolf.py"
        if fetch_script.exists():
            exit_code = run_script(
                "fetch_historical_from_datagolf.py",
                ["--tournament", tournament_name, "--years"] + [str(y) for y in missing],
                f"Fetching historical results ({missing})"
            )
            if exit_code != 0:
                print(f"[WARNING] Historical fetch failed for some years")
    else:
        cached = [y for y in history_years if (cache_dir / f"{slug}_{y}.json").exists()]
        print(f"[OK] Historical cache already exists for: {cached}")

    # Step B: Apply historical results to players_data
    if players_data_path.exists():
        apply_script = PROJECT_ROOT / "scripts" / "apply_historical_results.py"
        if apply_script.exists():
            exit_code = run_script(
                "apply_historical_results.py",
                ["--tournament", tournament_name, "--data", str(players_data_path),
                 "--years"] + [str(y) for y in history_years],
                "Applying historical results to players_data"
            )
            if exit_code != 0:
                print(f"[WARNING] Historical apply failed")
                return exit_code

        # Step C: Sync players[name]["history_YYYY"] -> historical[name]["YYYY"]
        print(f"[INFO] Syncing historical section...")
        try:
            data = json.loads(players_data_path.read_text(encoding="utf-8"))
            year_strs = [str(y) for y in history_years]

            for name, info in data.get("players", {}).items():
                if name not in data.get("historical", {}):
                    data.setdefault("historical", {})[name] = {}
                for yr in year_strs:
                    key = f"history_{yr}"
                    if key in info:
                        data["historical"][name][yr] = info[key]

            data["historical_years"] = sorted(year_strs, reverse=True)
            players_data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"[OK] Synced historical for {len(data.get('historical', {}))} players")
        except Exception as e:
            print(f"[WARNING] Historical sync failed: {e}")

    return 0


def generate_storylines(tournament_name: str, slug: str, year: int) -> int:
    """Generate AI storylines for players using Claude API.

    Always uses --force to regenerate fresh storylines (never skip).
    Requires ANTHROPIC_API_KEY in .env.
    """
    # Always use Claude API for storylines (--force to overwrite existing)
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if api_key:
        script_path = PROJECT_ROOT / "scripts" / "generate_ai_storylines_claude.py"
        if script_path.exists():
            return run_script(
                "generate_ai_storylines_claude.py",
                ["--tournament", tournament_name, "--year", str(year), "--slug", slug, "--force"],
                "Generating AI Storylines (Claude API)"
            )

    # No API key — fatal error, don't fall back to templates
    print("[ERROR] ANTHROPIC_API_KEY is NOT set — cannot generate storylines.")
    print("        Set it in .env and retry. Template fallback is disabled.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Weekly tournament preview orchestrator"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        help="Override tournament name (auto-detects from schedule by default)"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Tournament year (default: current year)"
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Skip moving previous tournament to historical"
    )
    parser.add_argument(
        "--skip-odds",
        action="store_true",
        help="Skip fetching odds"
    )
    parser.add_argument(
        "--skip-historical",
        action="store_true",
        help="Skip fetching historical results"
    )
    parser.add_argument(
        "--skip-storylines",
        action="store_true",
        help="Skip generating storylines"
    )
    parser.add_argument(
        "--skip-html",
        action="store_true",
        help="Skip generating HTML"
    )
    parser.add_argument(
        "--skip-datagolf",
        action="store_true",
        help="Skip applying Data Golf analytics (strokes gained, predictions, course fit)"
    )
    parser.add_argument(
        "--skip-recent-form",
        action="store_true",
        help="Skip fetching tournament result caches from Data Golf and building recent form"
    )
    parser.add_argument(
        "--skip-insights",
        action="store_true",
        help="Skip generating AI insights (executive summary + insight cards)"
    )
    parser.add_argument(
        "--skip-weather",
        action="store_true",
        help="Skip fetching tournament weather from NOAA"
    )
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Skip the content fact-check audit (champions/venue/finishes vs data)"
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip generating the email newsletter HTML"
    )
    parser.add_argument(
        "--email-link",
        default=None,
        help="CTA URL for the email newsletter (changes weekly). If omitted, auto-builds the per-tournament page URL on golfinthecosmos.com."
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy to Shopify after generation"
    )
    parser.add_argument(
        "--force-deploy",
        action="store_true",
        help="Deploy even if the content audit failed (escape hatch — normally audit failures block deploy)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )

    args = parser.parse_args()

    print(f"""
{'=' * 70}
{'=' * 70}
     COSMOS GOLF - WEEKLY TOURNAMENT ORCHESTRATOR
     {datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}
{'=' * 70}
{'=' * 70}
""")

    # ── Pre-flight API key audit ──────────────────────────────────────
    print(f"{'=' * 60}")
    print("[AUDIT] Checking required API keys and environment...")
    print(f"{'=' * 60}\n")

    from dotenv import load_dotenv
    load_dotenv()

    audit_ok = True
    # DataGolf API key (required for odds, analytics, historical, recent form)
    dg_key = os.environ.get("DATAGOLF_API_KEY", "")
    if dg_key:
        print(f"  [OK] DATAGOLF_API_KEY is set ({len(dg_key)} chars)")
    else:
        print("  [FAIL] DATAGOLF_API_KEY is NOT set — odds, analytics, historical, and recent form steps will fail")
        audit_ok = False

    # Anthropic API key (required for storylines + insights)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        print(f"  [OK] ANTHROPIC_API_KEY is set ({len(anthropic_key)} chars)")
    else:
        print("  [WARN] ANTHROPIC_API_KEY is NOT set — storylines will use fallback templates, insights/exec summary will be skipped")

    # Shopify keys (only needed for deploy)
    if args.deploy:
        shopify_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
        if shopify_token:
            print(f"  [OK] SHOPIFY_ACCESS_TOKEN is set")
        else:
            print("  [FAIL] SHOPIFY_ACCESS_TOKEN is NOT set — deploy step will fail")
            audit_ok = False

    if not audit_ok:
        print("\n  [ERROR] Critical API keys are missing. Fix .env and re-run.")
        return 1

    print()

    # Load schedule
    schedule = load_schedule()
    if not schedule.get("tournaments"):
        print("[ERROR] No tournament schedule found!")
        print("Create data/pga_schedule_2026.json first.")
        return 1

    # Determine tournament
    if args.tournament:
        # Find tournament in schedule
        tournament_name = args.tournament
        slug = _slugify(tournament_name)

        tournament = None
        for t in schedule.get("tournaments", []) + schedule.get("fall_schedule", []):
            if t.get("slug") == slug or tournament_name.lower() in t.get("name", "").lower():
                tournament = t
                break

        if not tournament:
            print(f"[WARNING] Tournament not in schedule, using minimal config")
            tournament = {"name": tournament_name, "slug": slug}
    else:
        # Auto-detect from schedule
        tournament = get_this_weeks_tournament(schedule)

        if not tournament:
            print("[ERROR] No upcoming tournament found in schedule!")
            return 1

    tournament_name = tournament.get("name", "Unknown Tournament")
    slug = tournament.get("slug", _slugify(tournament_name))
    year = args.year

    print(f"""
{'=' * 70}
 THIS WEEK'S TOURNAMENT
{'=' * 70}
 Name: {tournament_name}
 Dates: {tournament.get('dates', {}).get('start', 'TBD')} - {tournament.get('dates', {}).get('end', 'TBD')}
 Location: {tournament.get('location', 'TBD')}
 Course: {tournament.get('course', 'TBD')}
 Purse: {tournament.get('purse', 'TBD')}
{'=' * 70}
""")

    if args.dry_run:
        print("\n[DRY RUN] Would execute the following steps:")
        print("  1. Move previous tournament to historical (clean main list)")
        print("  2. Fetch odds from Data Golf (outright, top 5, top 10)")
        print("  2.5. Apply OWGR to players_data")
        print("  2.75. Apply Data Golf analytics (strokes gained, predictions, course fit)")
        print("  3. Fetch historical tournament results")
        print("  4. Fetch tournament result caches from Data Golf + build recent form")
        print("  5. Generate AI storylines")
        print("  5.5. Generate AI insights (executive summary + betting insight cards)")
        print("  5.75. Fetch tournament weather (NOAA)")
        print("  6. Generate HTML preview (main + v2 for Shopify)")
        if args.deploy:
            print("  7. Deploy to Shopify")
        return 0

    steps_completed = 0
    steps_failed = 0
    content_audit_failed = False

    # Step 1: Clean up previous tournament (move to historical so main editor list shows only current)
    if not args.skip_archive:
        previous = get_previous_tournament(schedule, tournament)
        if previous:
            prev_name = previous.get("name", "")

            # Move previous tournament to historical/ (root HTML + data/*)
            exit_code = run_script(
                "move_tournament_to_historical.py",
                ["--tournament", prev_name, "--year", str(year)],
                f"Moving Previous Tournament to Historical: {prev_name}"
            )
            if exit_code == 0:
                steps_completed += 1
            else:
                steps_failed += 1
        else:
            print("[SKIP] No previous tournament to clean up")

    # Step 2: Fetch odds from Data Golf (replaces manual DraftKings paste / fetch_draftkings_odds)
    if not args.skip_odds:
        players_data_path = PROJECT_ROOT / "data" / f"{slug}_{year}_players_data.json"
        exit_code = run_script(
            "refresh_odds_from_datagolf.py",
            ["--players-data", str(players_data_path), "--year", str(year),
             "--expected-event", tournament_name],
            "Fetching Tournament Odds (Data Golf)"
        )
        if exit_code == 0:
            steps_completed += 1
        elif exit_code == 2:
            # Expected-event guard tripped: DataGolf is still serving LAST
            # week's event. Everything downstream would be built from stale
            # data, so abort the whole run. Exit 2 = retryable.
            print("\n" + "!" * 70)
            print("[ABORT] DataGolf is still serving a different event than")
            print(f"        '{tournament_name}' (expected-event guard, exit 2).")
            print("        Aborting before building stale content. Retry after")
            print("        DataGolf rolls over (~Mon night/Tue morning).")
            print("!" * 70 + "\n")
            return 2
        else:
            print("[WARNING] Odds fetch failed - continuing with available data")
            steps_failed += 1

    # Step 2.5: Apply OWGR to players_data (so HTML shows OWGR #N instead of #-)
    players_data_path = PROJECT_ROOT / "data" / f"{slug}_{year}_players_data.json"
    if players_data_path.exists():
        exit_code = run_script(
            "apply_owgr.py",
            ["--tournament", tournament_name, "--year", str(year), "--slug", slug],
            "Applying OWGR to players_data"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            print("[WARNING] OWGR apply failed - continuing with available data")
    else:
        print("[SKIP] No players_data yet; run odds step first")

    # Step 2.75: Apply Data Golf analytics (strokes gained, predictions, course fit) for player detail panels
    if not args.skip_datagolf and players_data_path.exists():
        exit_code = run_script(
            "apply_datagolf_to_players.py",
            ["--tournament", tournament_name, "--year", str(year), "--slug", slug],
            "Applying Data Golf analytics (SG, predictions, course fit)"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            print("[WARNING] Data Golf apply failed - continuing with available data")
    elif args.skip_datagolf:
        print("[SKIP] Data Golf step skipped (--skip-datagolf)")
    else:
        print("[SKIP] No players_data yet; run odds step first")

    # Step 3: Fetch historical results
    if not args.skip_historical:
        print(f"\n{'=' * 60}")
        print("[STEP] Fetching Historical Results")
        print(f"{'=' * 60}\n")

        exit_code = fetch_historical_results(
            tournament_name, slug, year,
            [year, year - 1, year - 2, year - 3]
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            steps_failed += 1

    # Step 3.5: Fetch tournament result caches from Data Golf (Pebble, Genesis, Cognizant, etc.) + build recent form
    if not args.skip_recent_form:
        exit_code = run_script(
            "fetch_recent_form_caches_from_datagolf.py",
            ["--tournament", tournament_name, "--year", str(year)],
            "Fetching tournament result caches from Data Golf (recent form)"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            print("[WARNING] Some tournament result fetches failed (event may not be completed yet)")
        exit_code = run_script(
            "build_recent_form_from_cache.py",
            ["--tournament", tournament_name, "--year", str(year), "--max-events", "13", "--slug", slug],
            "Building recent form from cache"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            steps_failed += 1
    else:
        print("[SKIP] Recent form step skipped (--skip-recent-form)")

    # Step 4: Generate storylines
    if not args.skip_storylines:
        print(f"\n{'=' * 60}")
        print("[STEP] Generating Storylines")
        print(f"{'=' * 60}\n")

        exit_code = generate_storylines(tournament_name, slug, year)
        if exit_code == 0:
            steps_completed += 1
        else:
            steps_failed += 1

    # Step 4.5: Generate AI insights (executive summary + insight cards)
    # Always regenerate fresh insights so they reflect the latest data
    if not args.skip_insights and not args.skip_storylines:
        if os.environ.get("ANTHROPIC_API_KEY"):
            exit_code = run_script(
                "generate_ai_insights.py",
                ["--tournament", tournament_name, "--year", str(year), "--slug", slug],
                "Generating AI Insights (executive summary + betting insights)"
            )
            if exit_code == 0:
                steps_completed += 1
            else:
                print("[WARNING] AI insights generation failed - HTML will render without exec summary")
                steps_failed += 1
        else:
            print("[SKIP] No ANTHROPIC_API_KEY — skipping AI insights (exec summary will be blank)")

    # Step 4.6: Content fact-check audit — catches hallucinated champions /
    # venues / finishes in storylines+insights BEFORE we publish HTML or email.
    if not args.skip_audit and not args.skip_storylines:
        exit_code = run_script(
            "audit_tournament_content.py",
            ["--tournament", tournament_name, "--year", str(year), "--slug", slug],
            "Auditing AI content (champions / venue / finishes vs data)"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            content_audit_failed = True
            steps_failed += 1
            print("\n" + "!" * 70)
            print("[ERROR] CONTENT AUDIT FAILED — storylines/insights contain factual")
            print("        errors (listed above). FIX the data and regenerate BEFORE")
            print("        publishing to Shopify or sending the email.")
            print("!" * 70 + "\n")

    # Step 4.75: Fetch tournament weather (NOAA)
    if not args.skip_weather:
        exit_code = run_script(
            "fetch_tournament_weather.py",
            ["--tournament", tournament_name, "--year", str(year)],
            "Fetching Tournament Weather (NOAA)"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            print("[WARNING] Weather fetch failed - HTML will render without weather data")
            steps_failed += 1
    else:
        print("[SKIP] Weather step skipped (--skip-weather)")

    # Step 5: Generate HTML (main + v2 compact for Shopify)
    if not args.skip_html:
        exit_code = run_script(
            "generate_tournament_html.py",
            ["--tournament", tournament_name, "--year", str(year), "--slug", slug, "--v2"],
            "Generating HTML Preview (main + v2 for Shopify)"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            print("[ERROR] HTML generation failed!")
            steps_failed += 1

    # Step 5.5: Generate email newsletter (top storylines + player photos) for Shopify Email
    if not args.skip_email:
        email_args = ["--tournament", tournament_name, "--year", str(year), "--slug", slug]
        if args.email_link:
            email_args += ["--link", args.email_link]
        exit_code = run_script(
            "generate_email_newsletter.py",
            email_args,
            "Generating Email Newsletter (top storylines + player photos)"
        )
        if exit_code == 0:
            steps_completed += 1
        else:
            print("[WARNING] Email newsletter generation failed - continuing")
            steps_failed += 1
    else:
        print("[SKIP] Email newsletter step skipped (--skip-email)")

    # Step 6: Deploy to Shopify (optional)
    audit_blocked_deploy = False
    if args.deploy and content_audit_failed and not args.force_deploy:
        # Never publish content with known factual errors. Local HTML/email
        # outputs are kept for inspection; re-run with --force-deploy to override.
        audit_blocked_deploy = True
        print("\n" + "!" * 70)
        print("[BLOCKED] Deploy skipped: content audit failed. Fix storylines/")
        print("          insights and re-run, or use --force-deploy to override.")
        print("!" * 70 + "\n")
    elif args.deploy:
        deploy_script = PROJECT_ROOT / "scripts" / "deploy_to_shopify.py"
        if deploy_script.exists():
            from generate_tournament_html import page_handle, page_title
            html_file = PROJECT_ROOT / f"{slug}_{year}_v2.html"
            exit_code = run_script(
                "deploy_to_shopify.py",
                ["--html", str(html_file),
                 "--page-handle", page_handle(slug, year),
                 "--page-title", page_title(tournament, year)],
                "Deploying to Shopify"
            )
            if exit_code == 0:
                steps_completed += 1
            else:
                steps_failed += 1
        else:
            print("[SKIP] deploy_to_shopify.py not found")

    # Summary
    output_file = PROJECT_ROOT / f"{slug}_{year}.html"
    v2_file = PROJECT_ROOT / f"{slug}_{year}_v2.html"
    email_file = PROJECT_ROOT / f"{slug}_{year}_email.html"

    print(f"""

{'=' * 70}
{'=' * 70}
     ORCHESTRATION COMPLETE
{'=' * 70}
     Tournament: {tournament_name}
     Year: {year}

     Steps completed: {steps_completed}
     Steps failed: {steps_failed}
{"     ❌ CONTENT AUDIT FAILED — DO NOT PUBLISH until storylines/insights are fixed (see above)." if content_audit_failed else "     ✅ Content audit passed (no hallucinated champions/venues/finishes)."}

     Output: {output_file.name} (full preview)
     Shopify paste: {v2_file.name} (compact, ~2k lines)
     Email newsletter: {email_file.name} (paste into Shopify Email)
     Files exist: main={output_file.exists()}, v2={v2_file.exists()}, email={email_file.exists()}
{'=' * 70}

Next steps:
  1. Review the generated HTML: {output_file.name}
  2. For Shopify: paste {v2_file.name} into Custom HTML
  3. Email send: paste {email_file.name} into Shopify Email (custom code)
  4. Upload course image to Shopify Files
  5. Update crew picks (data/crew_picks.json)
  6. Deploy to Shopify (--deploy flag or manual upload)

{'=' * 70}
""")

    if audit_blocked_deploy:
        return 3  # built OK locally but deploy was blocked by the content audit
    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
