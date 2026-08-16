#!/usr/bin/env python3
"""
One-command automated weekly publish: build → deploy page live → swap menu →
verify outputs → email the review copy via Zapier.

Designed for the scheduled Monday run (.claude/skills/weekly-publish.md).
Retry-friendly: the Data Golf freshness preflight runs BEFORE any writes, so
a stale Monday-noon attempt exits 2 without mutating anything.

Exit codes:
    0  success (page live, menu updated, review email sent)
    2  Data Golf data is stale — retry later (nothing was changed/deployed)
    3  content audit failed — nothing deployed, human review needed
    4  page is LIVE but the menu update failed (partial success)
    1  other failure

Usage:
    python3 scripts/publish_weekly.py                       # auto-detect tournament
    python3 scripts/publish_weekly.py --tournament "The Open Championship"
    python3 scripts/publish_weekly.py --skip-event-check    # DG names event differently
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS))

from dotenv import load_dotenv
load_dotenv()

from generate_tournament_html import page_handle, page_title, has_hero_image  # noqa: E402
from weekly_tournament_orchestrator import (  # noqa: E402
    load_schedule, get_this_weeks_tournament, _slugify,
)
from refresh_odds_from_datagolf import _events_match  # noqa: E402

SITE_BASE = "https://www.golfinthecosmos.com"


def run(script: str, args: list[str]) -> int:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args], cwd=str(PROJECT_ROOT)
    ).returncode


def freshness_preflight(tournament_name: str) -> tuple[bool, str]:
    """Side-effect-free check that Data Golf outrights rolled over to this event."""
    from mcp_server.tools.datagolf import DataGolfClient
    with DataGolfClient() as dg:
        result = dg.get_outright_odds(tour="pga", market="win")
    dg_event = result.get("event_name", "")
    return _events_match(tournament_name, dg_event), dg_event


def shopify_auth_preflight() -> bool:
    """Fail fast (before the expensive build) if the Shopify token can't read pages."""
    import os
    import httpx
    store = (os.getenv("SHOPIFY_STORE_URL") or "").replace("https://", "").replace("http://", "")
    token = os.getenv("SHOPIFY_ACCESS_TOKEN") or ""
    if not store or not token:
        return False
    try:
        resp = httpx.get(f"https://{store}/admin/api/2024-01/pages.json?limit=1",
                         headers={"X-Shopify-Access-Token": token}, timeout=15.0)
        return resp.status_code == 200
    except Exception:
        return False


def resolve_tournament(name_override: str | None) -> dict | None:
    schedule = load_schedule()
    if name_override:
        slug = _slugify(name_override)
        for t in schedule.get("tournaments", []) + schedule.get("fall_schedule", []):
            if t.get("slug") == slug or name_override.lower() in t.get("name", "").lower():
                return t
        return {"name": name_override, "slug": slug}
    return get_this_weeks_tournament(schedule)


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated weekly build + publish + notify")
    parser.add_argument("--tournament", default=None, help="Override tournament name")
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--skip-event-check", action="store_true",
                        help="Bypass the Data Golf expected-event guard")
    parser.add_argument("--force-deploy", action="store_true",
                        help="Deploy even if the content audit failed")
    parser.add_argument("--skip-archive", action="store_true",
                        help="Pass through to the orchestrator (re-runs after a partial attempt)")
    parser.add_argument("--no-notify", action="store_true", help="Skip the Zapier review email")
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip crew reset + orchestrator; just redeploy/menu/verify/notify from existing outputs")
    args = parser.parse_args()

    tournament = resolve_tournament(args.tournament)
    if not tournament:
        print("❌ No upcoming tournament found in schedule")
        return 1

    name = tournament.get("name", "")
    slug = tournament.get("slug", _slugify(name))
    year = args.year
    handle = page_handle(slug, year)
    title = page_title(tournament, year)
    page_url = f"{SITE_BASE}/pages/{handle}"
    email_file = PROJECT_ROOT / f"{slug}_{year}_email.html"

    print(f"{'=' * 70}\n WEEKLY PUBLISH — {title}\n"
          f" slug={slug}  handle={handle}\n page: {page_url}\n{'=' * 70}\n")

    # ── 0a. Shopify auth preflight (no writes) ────────────────────────
    if not shopify_auth_preflight():
        print("❌ Shopify Admin API auth failed (SHOPIFY_STORE_URL / SHOPIFY_ACCESS_TOKEN).")
        print("   Create a custom-app token with content+files+navigation scopes (see .env.example).")
        print("   Aborting BEFORE the build so nothing is wasted. Exit 1.")
        return 1

    # ── 0b. Freshness preflight (no writes) ───────────────────────────
    if not args.skip_event_check and not args.skip_build:
        ok, dg_event = freshness_preflight(name)
        if not ok:
            print(f"⏳ STALE: Data Golf outrights still serve '{dg_event}', expected '{name}'.")
            print("   Nothing was changed. Retry after DG rolls over (~Mon night/Tue). Exit 2.")
            return 2
        print(f"✅ Data Golf is serving this week's event: '{dg_event}'")

    exit_code = 0
    if not args.skip_build:
        # ── 1. Crew picks → placeholder ───────────────────────────────
        if run("reset_crew_picks.py", []) != 0:
            print("⚠️  Crew-picks reset failed — continuing (renderer tolerates stale picks)")

        # ── 2. Full build + deploy (orchestrator gates stale data + audit) ──
        orch_args = ["--tournament", name, "--year", str(year), "--deploy"]
        if args.skip_event_check:
            orch_args.append("--skip-event-check")
        if args.force_deploy:
            orch_args.append("--force-deploy")
        if args.skip_archive:
            orch_args.append("--skip-archive")
        exit_code = run("weekly_tournament_orchestrator.py", orch_args)
        if exit_code == 2:
            print("⏳ Orchestrator hit stale Data Golf data. Exit 2 (retry later).")
            return 2
        if exit_code == 3:
            print("🛑 Content audit failed — NOTHING was deployed. Fix storylines/insights.")
            return 3
        if exit_code != 0:
            print(f"⚠️  Orchestrator finished with failures (exit {exit_code}) — checking outputs before continuing")
    else:
        # Redeploy existing outputs (e.g. Wednesday crew-picks update)
        v2 = PROJECT_ROOT / f"{slug}_{year}_v2.html"
        if run("deploy_to_shopify.py", ["--html", str(v2), "--page-handle", handle,
                                        "--page-title", title]) != 0:
            print("❌ Redeploy failed")
            return 1

    # ── 3. Menu swap ──────────────────────────────────────────────────
    menu_ok = run("update_shopify_menu.py", ["--handle", handle]) == 0
    if not menu_ok:
        print("⚠️  Menu update failed — page is live but nav still points at last week")

    # ── 4. Output files present in repo root ─────────────────────────
    outputs = {
        "full HTML": PROJECT_ROOT / f"{slug}_{year}.html",
        "Shopify v2 HTML": PROJECT_ROOT / f"{slug}_{year}_v2.html",
        "email HTML": email_file,
    }
    missing = [label for label, p in outputs.items() if not p.exists()]

    hero_mapped = has_hero_image(name)

    # ── 5. Summary (machine-greppable) + review email ────────────────
    summary_lines = [
        f"PAGE_TITLE: {title}",
        f"LIVE_URL: {page_url}",
        f"MENU_UPDATED: {'yes' if menu_ok else 'NO — swap manually in Shopify admin'}",
        f"EMAIL_FILE: {email_file}",
        f"HERO_IMAGE: {'tournament-specific' if hero_mapped else 'DEFAULT FALLBACK — no mapping for this event'}",
        f"OUTPUTS_MISSING: {', '.join(missing) if missing else 'none'}",
        f"CREW_PICKS: placeholder ('drop Wednesday night') — update data/crew_picks.json then run: "
        f"python3 scripts/publish_weekly.py --skip-build",
        "NEXT_STEP: paste the email HTML into Shopify Email (custom code) and send",
    ]
    summary = "\n".join(summary_lines)
    print(f"\n{'=' * 70}\n PUBLISH SUMMARY\n{'=' * 70}\n{summary}\n{'=' * 70}")

    if not args.no_notify:
        notify_args = [
            "--subject", f"🏌️ {title} is LIVE — review & send the email",
            "--body", summary,
        ]
        if email_file.exists():
            notify_args += ["--newsletter-file", str(email_file)]
        if run("notify_email.py", notify_args) != 0:
            print("⚠️  Review-email notification failed (page is still live)")

    if missing:
        return 1
    if not menu_ok:
        return 4
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
