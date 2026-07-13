#!/usr/bin/env python3
"""
Audit (and optionally refresh) The American Express 2026 preview data.

What this does:
- Scrapes official PGA TOUR past-results pages for 2025/2024/2023 finishes.
- Scrapes a public DraftKings odds list article for current win odds.
- Writes `data/amex_2026_players.json` for `scripts/generate_american_express.py` to consume.
- Writes `AMEX_ODDS_HISTORY_AUDIT.md` with a per-player diff.

Usage:
  python3 scripts/audit_american_express.py

Optional:
  python3 scripts/generate_american_express.py
  python3 scripts/update_american_express.py
"""

from __future__ import annotations

import json
import re
import sys
import html as html_lib
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).parent.parent
DATA_OUT = PROJECT_ROOT / "data" / "amex_2026_players.json"
AUDIT_MD_OUT = PROJECT_ROOT / "AMEX_ODDS_HISTORY_AUDIT.md"

DEFAULT_ODDS_SOURCE_URL = (
    "https://dknetwork.draftkings.com/2026/01/18/2026-the-american-express-odds-full-field/"
)

PGATOUR_EVENT_SLUG = "the-american-express"
# The PGA TOUR event id embedded in the URL for this event appears stable as R{year}002.
PGATOUR_EVENT_ID_SUFFIX = "002"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_finish(value: Any) -> str:
    """Normalize a PGA TOUR position string to COSMOS display conventions."""
    if value is None:
        return "NA"
    v = str(value).strip()
    if not v:
        return "NA"

    upper = v.upper()
    if upper in {"CUT", "MDF", "MC"}:
        return "MC"
    if upper in {"W/D", "WD"}:
        return "WD"
    if upper in {"DQ", "DNS"}:
        return upper
    # Ordinals (rare)
    if upper.endswith(("ST", "ND", "RD", "TH")) and upper[:-2].isdigit():
        return upper[:-2]
    return v


def _normalize_american_odds(value: Any) -> str | None:
    """Normalize to '+####' or '-###' strings if possible."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.match(r"^[+-]\d{2,6}$", s)
    if m:
        return s
    # Handle raw integers like 240 -> +240
    if re.match(r"^\d{2,6}$", s):
        return f"+{s}"
    return None


def _parse_american_odds_int(value: Any) -> int | None:
    """Parse an American odds string like '+240' or '-110' to int."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s in {"—", "-", "NA", "TBD"}:
        return None
    if re.match(r"^[+-]\d{2,6}$", s):
        return int(s)
    if re.match(r"^\d{2,6}$", s):
        return int(s)
    return None


def _format_american_odds(value: Any) -> str:
    """Format an American odds value to '+###'/'-###'/'—'."""
    n = _parse_american_odds_int(value)
    if n is None:
        return "—"
    return f"{n:+d}" if n > 0 else str(n)


def _norm_name(name: str) -> str:
    """Normalize names to improve cross-source matching."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_next_data_json(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("Could not find __NEXT_DATA__ payload in PGA TOUR HTML")
    return json.loads(m.group(1))


def _find_best_players_list(next_data: dict) -> list[dict]:
    """Pick the 'players' list that looks like the final leaderboard."""
    queries = (
        next_data.get("props", {})
        .get("pageProps", {})
        .get("dehydratedState", {})
        .get("queries", [])
    )

    best: list[dict] | None = None
    for q in queries:
        data = q.get("state", {}).get("data")
        if not isinstance(data, dict):
            continue
        players = data.get("players")
        if not isinstance(players, list) or len(players) < 80:
            continue
        sample = players[0] if players else None
        if not isinstance(sample, dict):
            continue
        if "position" not in sample or "player" not in sample:
            continue
        if best is None or len(players) > len(best):
            best = players

    if best is None:
        raise ValueError("Could not locate leaderboard players list in PGA TOUR payload")
    return best


def fetch_pgatour_past_results(year: int) -> dict[str, str]:
    """Return displayName -> normalized finish for a given year."""
    url = f"https://www.pgatour.com/tournaments/{year}/{PGATOUR_EVENT_SLUG}/R{year}{PGATOUR_EVENT_ID_SUFFIX}/past-results"
    html = httpx.get(url, timeout=30.0, follow_redirects=True).text
    next_data = _extract_next_data_json(html)
    players = _find_best_players_list(next_data)

    results: dict[str, str] = {}
    for row in players:
        player = row.get("player") or {}
        name = player.get("displayName")
        if not isinstance(name, str) or not name.strip():
            continue
        pos = row.get("position")
        results[name.strip()] = _normalize_finish(pos)

    return results


def fetch_dk_network_win_odds(url: str) -> dict[str, str]:
    """
    Scrape DK Network odds list article.

    Expected markup includes list items like:
      <li>Scottie Scheffler <strong>+240</strong></li>
    """
    html = httpx.get(url, timeout=30.0, follow_redirects=True).text
    html = html_lib.unescape(html)

    odds: dict[str, str] = {}

    # Prefer strict LI + STRONG pattern.
    for m in re.finditer(r"<li>\s*([^<]+?)\s*<strong>\s*([+-]?\d{2,6})\s*</strong>\s*</li>", html):
        name = m.group(1).strip()
        raw = m.group(2).strip()
        val = _normalize_american_odds(raw)
        if name and val:
            odds[name] = val

    # Fall back: sometimes names include extra tokens like (a) for amateurs.
    cleaned: dict[str, str] = {}
    for name, val in odds.items():
        name2 = name.replace("(a)", "").replace("(A)", "").strip()
        cleaned[name2] = val
    return cleaned


@dataclass(frozen=True)
class PlayerDiff:
    name: str
    win_odds_old: str
    win_odds_new: str
    h2025_old: str
    h2025_new: str
    h2024_old: str
    h2024_new: str
    h2023_old: str
    h2023_new: str


def main() -> int:
    # Import fallback PLAYERS list (no side effects).
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.generate_american_express import PLAYERS  # noqa: WPS433

    print("📊 Auditing The American Express preview data…")
    print(f"   - Odds source: {DEFAULT_ODDS_SOURCE_URL}")
    print("   - Past results source: PGA TOUR past-results pages (2023-2025)")

    print("\n🌐 Fetching PGA TOUR past results…")
    past_2025 = fetch_pgatour_past_results(2025)
    past_2024 = fetch_pgatour_past_results(2024)
    past_2023 = fetch_pgatour_past_results(2023)

    print("\n🌐 Fetching win odds list…")
    dk_odds = fetch_dk_network_win_odds(DEFAULT_ODDS_SOURCE_URL)

    # Build updated players list (preserve rank/storylines/tiers).
    updated_players: list[dict] = []
    diffs: list[PlayerDiff] = []

    for p in PLAYERS:
        name = p["name"]
        p2 = dict(p)

        h25_new = _normalize_finish(past_2025.get(name, "NA"))
        h24_new = _normalize_finish(past_2024.get(name, "NA"))
        h23_new = _normalize_finish(past_2023.get(name, "NA"))

        p2["history_2025"] = h25_new
        p2["history_2024"] = h24_new
        p2["history_2023"] = h23_new

        win_new = dk_odds.get(name)
        if win_new:
            p2["win_odds"] = win_new

        # Normalize Top-5/Top-10 odds: keep, but make it obvious if unknown.
        if str(p2.get("top5_odds", "")).strip().upper() in {"TBD", "", "NA"}:
            p2["top5_odds"] = "—"
        if str(p2.get("top10_odds", "")).strip().upper() in {"TBD", "", "NA"}:
            p2["top10_odds"] = "—"

        updated_players.append(p2)

        diffs.append(
            PlayerDiff(
                name=name,
                win_odds_old=str(p.get("win_odds", "")),
                win_odds_new=str(p2.get("win_odds", "")),
                h2025_old=str(p.get("history_2025", "")),
                h2025_new=h25_new,
                h2024_old=str(p.get("history_2024", "")),
                h2024_new=h24_new,
                h2023_old=str(p.get("history_2023", "")),
                h2023_new=h23_new,
            )
        )

    # Optional: quota-light multi-book odds audit via The Odds API
    odds_api_section_lines: list[str] = []
    odds_api_payload: dict[str, Any] | None = None

    try:
        # Import lazily so audit still works without keys/deps configured.
        from mcp_server.tools.odds import OddsAPIClient  # type: ignore

        print("\n🌐 Auditing win odds across books (The Odds API)…")
        with OddsAPIClient() as client:
            sports = client.get_golf_sports()

            # Match tournament (best-effort) – do NOT call odds endpoint if no match found.
            needle = "american express"
            matches = [
                s for s in sports
                if needle in str(s.get("title", "")).lower()
                or needle in str(s.get("description", "")).lower()
                or needle in str(s.get("key", "")).lower()
            ]

            if not matches:
                # Keep it quota-light: only /sports call was made.
                odds_api_section_lines.append("\n## Multi-book odds audit (The Odds API)\n")
                odds_api_section_lines.append(
                    "- Status: **SKIPPED** (no matching golf event found in The Odds API sports list)\n"
                )
                odds_api_section_lines.append(
                    "- Note: This is still useful — it confirms the API currently isn’t offering an outright market keyed to this event.\n"
                )
                odds_api_section_lines.append("\n### Available golf events (first 25)\n")
                odds_api_section_lines.append("| Title | Key |\n")
                odds_api_section_lines.append("|---|---|\n")
                for s in sports[:25]:
                    odds_api_section_lines.append(f"| {s.get('title','')} | `{s.get('key','')}` |\n")
            else:
                chosen = matches[0]
                sport_key = chosen.get("key")
                sport_title = chosen.get("title")

                tournament_odds = client.get_tournament_odds(
                    sport_key=sport_key,
                    markets="outrights",
                    odds_format="american",
                )

                if not tournament_odds:
                    odds_api_section_lines.append("\n## Multi-book odds audit (The Odds API)\n")
                    odds_api_section_lines.append(
                        f"- Status: **SKIPPED** (no odds returned for `{sport_key}`)\n"
                    )
                else:
                    # Compute best odds across books for each API name
                    best_api: dict[str, tuple[str, int]] = {}
                    for bookmaker in tournament_odds.bookmakers:
                        for po in bookmaker.players:
                            nm = str(getattr(po, "player_name", "")).strip()
                            odds_val = _parse_american_odds_int(getattr(po, "odds", None))
                            if not nm or odds_val is None:
                                continue
                            cur = best_api.get(nm)
                            if cur is None or odds_val > cur[1]:
                                best_api[nm] = (bookmaker.bookmaker_name, odds_val)

                    api_by_norm = {_norm_name(nm): (nm, book, odds) for nm, (book, odds) in best_api.items()}

                    rows: list[dict[str, Any]] = []
                    missing: list[str] = []

                    for p in updated_players:
                        name = p["name"]
                        our_odds_int = _parse_american_odds_int(p.get("win_odds"))
                        our_odds_str = _format_american_odds(p.get("win_odds"))

                        match = api_by_norm.get(_norm_name(name))
                        if not match:
                            missing.append(name)
                            rows.append(
                                {
                                    "player": name,
                                    "preview_win_odds": our_odds_str,
                                    "best_book": None,
                                    "best_win_odds": None,
                                    "delta_best_minus_preview": None,
                                }
                            )
                            continue

                        _api_raw, best_book, best_odds = match
                        delta = (best_odds - our_odds_int) if (our_odds_int is not None) else None

                        rows.append(
                            {
                                "player": name,
                                "preview_win_odds": our_odds_str,
                                "best_book": best_book,
                                "best_win_odds": best_odds,
                                "delta_best_minus_preview": delta,
                            }
                        )

                    odds_api_payload = {
                        "fetched_at": _utc_now_iso(),
                        "sport_key": sport_key,
                        "sport_title": sport_title,
                        "players_compared": len(updated_players),
                        "api_players": len(best_api),
                        "missing_from_api": missing,
                        "rows": rows,
                    }

                    odds_api_section_lines.append("\n## Multi-book odds audit (The Odds API)\n")
                    odds_api_section_lines.append("- Status: **OK**\n")
                    odds_api_section_lines.append(f"- Sport key: `{sport_key}`\n")
                    odds_api_section_lines.append(f"- Sport title: `{sport_title}`\n")
                    odds_api_section_lines.append(
                        "- Quota usage: typically **2 requests** (sports list + outrights odds)\n"
                    )
                    odds_api_section_lines.append("\n### Preview vs best available (best - preview)\n")
                    odds_api_section_lines.append("| Player | Preview win odds | Best book | Best win odds | Δ |\n")
                    odds_api_section_lines.append("|---|---:|---|---:|---:|\n")
                    for r in rows:
                        best_book = r["best_book"] or "—"
                        best_odds_str = _format_american_odds(r["best_win_odds"])
                        delta_str = "—" if r["delta_best_minus_preview"] is None else f"{int(r['delta_best_minus_preview']):+d}"
                        odds_api_section_lines.append(
                            f"| {r['player']} | {r['preview_win_odds']} | {best_book} | {best_odds_str} | {delta_str} |\n"
                        )
                    odds_api_section_lines.append("\n### Coverage\n")
                    odds_api_section_lines.append(f"- Missing from Odds API (from our roster): **{len(missing)}**\n")

    except Exception as e:
        # Any failure here should not block the main (history + DK) audit.
        odds_api_section_lines.append("\n## Multi-book odds audit (The Odds API)\n")
        odds_api_section_lines.append("- Status: **SKIPPED** (Odds API not configured or request failed)\n")
        odds_api_section_lines.append(f"- Error: `{type(e).__name__}: {e}`\n")
        odds_api_section_lines.append(
            "- Fix: ensure `ODDS_API_KEY` is set in your local `.env`, then rerun.\n"
        )

    # Write JSON used by the generator.
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    out_payload = {
        "generated_at": _utc_now_iso(),
        "sources": {
            "win_odds": DEFAULT_ODDS_SOURCE_URL,
            "past_results": {
                "2025": f"https://www.pgatour.com/tournaments/2025/{PGATOUR_EVENT_SLUG}/R2025002/past-results",
                "2024": f"https://www.pgatour.com/tournaments/2024/{PGATOUR_EVENT_SLUG}/R2024002/past-results",
                "2023": f"https://www.pgatour.com/tournaments/2023/{PGATOUR_EVENT_SLUG}/R2023002/past-results",
            },
        },
        "players": updated_players,
    }
    if odds_api_payload is not None:
        out_payload["sources"]["odds_api"] = "The Odds API (multi-book outrights)"
        out_payload["odds_api"] = odds_api_payload
    DATA_OUT.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")

    # Write audit markdown.
    lines: list[str] = []
    lines.append("# AMEX 2026 Odds + History Audit\n")
    lines.append(f"- Generated: `{out_payload['generated_at']}`\n")
    lines.append(f"- Win odds source: `{DEFAULT_ODDS_SOURCE_URL}`\n")
    lines.append("- Past results source:\n")
    lines.append(f"  - 2025: `{out_payload['sources']['past_results']['2025']}`\n")
    lines.append(f"  - 2024: `{out_payload['sources']['past_results']['2024']}`\n")
    lines.append(f"  - 2023: `{out_payload['sources']['past_results']['2023']}`\n")
    lines.append("\n## Per-player diffs (generator fallback → audited)\n")
    lines.append("| Player | Win Odds | 2025 | 2024 | 2023 |\n")
    lines.append("|---|---:|---:|---:|---:|\n")

    changed_odds = 0
    changed_hist = 0

    for d in diffs:
        odds_cell = d.win_odds_new
        if d.win_odds_old != d.win_odds_new:
            changed_odds += 1
            odds_cell = f"**{d.win_odds_old} → {d.win_odds_new}**"

        def fmt(old: str, new: str) -> str:
            nonlocal changed_hist
            old_n = _normalize_finish(old)
            new_n = _normalize_finish(new)
            if old_n != new_n:
                changed_hist += 1
                return f"**{old_n} → {new_n}**"
            return new_n

        lines.append(
            f"| {d.name} | {odds_cell} | {fmt(d.h2025_old, d.h2025_new)} | {fmt(d.h2024_old, d.h2024_new)} | {fmt(d.h2023_old, d.h2023_new)} |\n"
        )

    lines.append("\n## Summary\n")
    lines.append(f"- Players audited: **{len(updated_players)}**\n")
    lines.append(f"- Win odds updated from source: **{changed_odds}** players\n")
    lines.append(f"- Historical finish cells changed: **{changed_hist}** cells\n")
    lines.extend(odds_api_section_lines)
    lines.append("\n## Next step\n")
    lines.append("- Run `python3 scripts/generate_american_express.py` to regenerate `american_express_2026.html` using the audited data.\n")

    AUDIT_MD_OUT.write_text("".join(lines), encoding="utf-8")

    print("\n✅ Audit complete")
    print(f"   - Wrote data: {DATA_OUT}")
    print(f"   - Wrote report: {AUDIT_MD_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

