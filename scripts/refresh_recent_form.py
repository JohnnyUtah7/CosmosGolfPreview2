#!/usr/bin/env python3
"""
Refresh recent form JSON with real "last start" results.

Primary source: BallDontLie PGA API (BALLDONTLIE_API_KEY).
For each player in the tournament odds roster, build a "Last start: EVENT (Mon YYYY) T##" blurb.

Usage:
  python scripts/refresh_recent_form.py --tournament "WM Phoenix Open" --year 2026
  python scripts/refresh_recent_form.py --players-data data/wm_phoenix_open_2026_players_data.json --output data/wm_phoenix_open_2026_recent_form.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from mcp_server.tools.pga import PGAAPIClient  # noqa: E402


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _is_recent_form_junk(value: str) -> bool:
    v = (value or "").strip()
    if not v or v == "—":
        return True
    return bool(
        re.search(
            r"(american express|odds|picks|predictions|best bets|full field|tickets|parking|schedule|prize money|how much|betting tips)",
            v,
            re.IGNORECASE,
        )
    )


def _fmt_month_year(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.strftime("%b %Y")
    except Exception:
        return ""


def _normalize_finish_token(pos: object) -> str:
    s = str(pos or "").strip()
    if not s:
        return ""
    u = s.upper()
    if u in {"CUT", "MDF", "MC"}:
        return "MC"
    if u in {"W/D", "WD"}:
        return "WD"
    if u in {"DQ", "DNS"}:
        return u
    return s


def _recent_form_from_results(rows: list[dict], max_events: int = 4) -> str:
    """
    Build a recent form string showing last 3-4 tournaments.

    Format: "Tournament (Mon YYYY): Position • Tournament2 (Mon YYYY): Position"
    Always shows MC (missed cut) explicitly - important for betting context.
    """
    if not rows:
        return "—"

    def _status_ok(r: dict) -> bool:
        t = r.get("tournament") if isinstance(r.get("tournament"), dict) else {}
        status = str(t.get("status") or "").strip().lower()
        return status in {"completed", "complete", ""}  # tolerate missing

    rows = [r for r in rows if _status_ok(r)]
    if not rows:
        return "—"

    def _dt(r: dict) -> datetime | None:
        t = r.get("tournament") if isinstance(r.get("tournament"), dict) else {}
        iso = t.get("start_date")
        if not iso:
            return None
        try:
            return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

    # Sort by date (most recent first) and take top N events
    ordered = sorted(rows, key=lambda r: _dt(r) or datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)
    ordered = ordered[:max_events]

    # Build event strings: "Tournament (Mon YYYY): Position"
    parts = []
    for r in ordered:
        t = r.get("tournament") if isinstance(r.get("tournament"), dict) else {}
        t_name = str(t.get("name") or "").strip()
        if not t_name:
            continue

        when = _fmt_month_year(t.get("start_date"))
        pos = _normalize_finish_token(r.get("position"))

        if not pos:
            continue

        # Format: "Tournament Name (Mon YYYY): Position"
        if when:
            part = f"{t_name} ({when}): {pos}"
        else:
            part = f"{t_name}: {pos}"

        parts.append(part)

    if not parts:
        return "—"

    # Join with bullet separator
    return " • ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh recent form from BallDontLie API")
    parser.add_argument("--players-data", type=Path, help="Path to players_data.json (source of player names)")
    parser.add_argument("--output", type=Path, help="Path to recent_form.json output")
    parser.add_argument("--tournament", type=str, help="Tournament name (e.g. WM Phoenix Open)")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--force", action="store_true", help="Overwrite all players (default: only update junk/empty)")
    parser.add_argument("--max-events", type=int, default=5, help="Max tournaments per player")
    args = parser.parse_args()

    if args.players_data is not None and args.output is not None:
        players_data_path = Path(args.players_data)
        recent_form_path = Path(args.output)
        if not players_data_path.is_absolute():
            players_data_path = ROOT / players_data_path
        if not recent_form_path.is_absolute():
            recent_form_path = ROOT / recent_form_path
    elif args.tournament:
        slug = _slugify(args.tournament)
        players_data_path = ROOT / "data" / f"{slug}_{args.year}_players_data.json"
        recent_form_path = ROOT / "data" / f"{slug}_{args.year}_recent_form.json"
    else:
        raise SystemExit("Provide --players-data and --output, or --tournament (and optional --year)")

    if not players_data_path.exists():
        raise SystemExit(f"Missing players data: {players_data_path}")

    data = json.loads(players_data_path.read_text(encoding="utf-8"))
    odds = data.get("odds", {})
    if not isinstance(odds, dict):
        raise SystemExit("players_data must have an 'odds' mapping")
    names = list(odds.keys())

    cache: dict[str, str] = {}
    if recent_form_path.exists():
        try:
            raw = json.loads(recent_form_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cache = {str(k): str(v or "—") for k, v in raw.items()}
        except Exception:
            cache = {}

    # If we don't have a key (or the endpoint is gated), keep cache as-is.
    try:
        pga_ctx = PGAAPIClient()
    except Exception as e:
        print(f"ℹ️  Skipping BallDontLie refresh (API not configured/available): {type(e).__name__}: {e}")
        recent_form_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
        return 0

    with pga_ctx as pga:
        players = pga.get_all_players_paginated(max_pages=10)

        def norm(n: str) -> str:
            s = (n or "").lower()
            s = re.sub(r"[^a-z0-9\\s]", " ", s)
            return re.sub(r"\\s+", " ", s).strip()

        by_norm: dict[str, int] = {}
        for pl in players:
            dn = str(pl.get("display_name") or "").strip()
            pid = pl.get("id")
            if dn and isinstance(pid, int):
                by_norm.setdefault(norm(dn), pid)

        wanted_ids: dict[str, int] = {}
        for name in names:
            # Only overwrite when existing is junk/empty (unless --force)
            if not args.force and name in cache and not _is_recent_form_junk(cache.get(name, "")):
                continue
            pid = by_norm.get(norm(name))
            if isinstance(pid, int):
                wanted_ids[name] = pid

        rows_by_player: dict[int, list[dict]] = {pid: [] for pid in wanted_ids.values()}
        ids = list(set(wanted_ids.values()))
        chunks = [ids[i : i + 40] for i in range(0, len(ids), 40)]

        for season in [2026, 2025]:
            for chunk in chunks:
                cursor = None
                pages = 0
                while True:
                    pages += 1
                    if pages > 50:
                        break
                    try:
                        resp = pga.get_tournament_results(season=season, player_ids=chunk, per_page=100, cursor=cursor)
                    except Exception as e:
                        # Tournament results may require a higher plan tier.
                        print(f"ℹ️  Skipping tournament_results fetch: {type(e).__name__}: {e}")
                        cursor = None
                        break
                    data = resp.get("data") if isinstance(resp, dict) else None
                    if isinstance(data, list):
                        for r in data:
                            player = r.get("player") if isinstance(r.get("player"), dict) else {}
                            pid = player.get("id")
                            if isinstance(pid, int) and pid in rows_by_player:
                                rows_by_player[pid].append(r)
                    meta = resp.get("meta") if isinstance(resp, dict) else {}
                    cursor = meta.get("next_cursor") if isinstance(meta, dict) else None
                    if not cursor:
                        break

        updated = 0
        for name, pid in wanted_ids.items():
            blurb = _recent_form_from_results(
                rows_by_player.get(pid, []),
                max_events=args.max_events,
            )
            if blurb and blurb != "—":
                cache[name] = blurb
                updated += 1

    recent_form_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    print(f"✅ Wrote {recent_form_path} (updated {updated} players)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

