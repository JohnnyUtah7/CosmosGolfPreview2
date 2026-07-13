#!/usr/bin/env python3
"""
Generate The American Express 2026 Tournament Preview (Readable Edition).

Design rules (per request):
- White background everywhere
- Black text everywhere except:
  - odds (green)
  - tournament finishes (colored by finish tier)

Data rules:
- Scottie Scheffler should not show NAs for recent AMEX finishes
- Tournament header facts updated (purse, FedEx points, field, etc.)
- Player list should include as many players as odds are offered for
  (no hard-coded 32 cap). If The Odds API key is available, we pull all
  players with outrights. Otherwise you can pass --odds-json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.odds import OddsAPIClient
from mcp_server.tools.news import GolfNewsClient
from mcp_server.tools.pga import PGAAPIClient
from country_utils import country_display_html

ROOT_DIR = Path(__file__).parent.parent
DEFAULT_ODDS_JSON_PATH = ROOT_DIR / "data" / "american_express_2026_odds.json"
DEFAULT_PLAYERS_DATA_PATH = ROOT_DIR / "data" / "amex_2026_players_data.json"
DEFAULT_STORYLINES_JSON_PATH = ROOT_DIR / "data" / "amex_2026_storylines.json"
DEFAULT_RECENT_FORM_CACHE_PATH = ROOT_DIR / "data" / "amex_2026_recent_form.json"
DEFAULT_WEATHER_JSON_PATH = ROOT_DIR / "data" / "tournament_weather.json"


@dataclass(frozen=True)
class TournamentInfo:
    name: str
    dates: str
    location: str
    courses: str
    mission_tag: str
    total_purse: str
    winner_share: str
    stadium_yards: str
    par: str
    field_size: str
    fedex_points: str


TOURNAMENT = TournamentInfo(
    name="The American Express",
    dates="January 22-25, 2026",
    location="La Quinta, California",
    courses="PGA West (Stadium, Nicklaus) · La Quinta Country Club",
    mission_tag="// MISSION BRIEFING - JANUARY 2026",
    # PGA TOUR (Jan 2026)
    total_purse="$9.2M",
    winner_share="$1.656M",
    stadium_yards="7,210 YDS",
    par="72",
    field_size="156",
    fedex_points="500",
)


SHOPIFY_LOGO_URL = "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/COSMOS_Golf-Dec-Logo_001.png?v=1768281723"
SHOPIFY_COURSE_IMAGE_URL = "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/amex.webp?v=1768848048"

# Recent form blurbs (free text, shown in final column)
# Fill these in over time; anything missing renders as "—".
RECENT_FORM_OVERRIDES: dict[str, str] = {
    # Verified 2026 Sony Open: T4 at Waialae
    "Robert MacIntyre": "Sony Open (Waialae): T4 (last week)",
}


# Curated overrides (kept intentionally small; everything else can be blank)
MANUAL_PROFILES: dict[str, dict[str, Any]] = {
    "Scottie Scheffler": {
        "country": "USA",
        "owgr": "1",
        # Web-verified:
        # 2025: WD (hand injury)
        # 2024: T17
        # 2023: T11
        "history": {2025: "WD", 2024: "T17", 2023: "T11"},
        "storyline": (
            "OWGR #1 returns to PGA West with real course reps—no 'debut' talk. "
            "He posted T11 (2023) and T17 (2024), then withdrew in 2025. "
            "If the irons are sharp, this becomes a pure birdie hunt in his wheelhouse."
        ),
    }
}


CREW_PICKS = [
    {
        "name": "Miller",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/miller.jpg?v=1768439524",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"},
        ],
    },
    {
        "name": "Kevin",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kham.jpg?v=1768439565",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"},
        ],
    },
    {
        "name": "Andrew",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/andrew_hammond.jpg?v=1768439595",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"},
        ],
    },
    {
        "name": "Kcon",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kcon.jpg?v=1768439465",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"},
        ],
    },
]


def _round_to_step(value: float, step: int) -> int:
    if step <= 0:
        return int(round(value))
    return int(round(value / step) * step)


def _odds_to_str(odds: int) -> str:
    return f"+{odds}" if odds > 0 else str(odds)


def _estimate_place_odds(win_odds: int, divisor: int) -> int:
    # House-style approximation used in existing AMEX table:
    # top5 ~ win/4, top10 ~ win/8, rounded to nearest 5.
    if divisor <= 0:
        return win_odds
    return max(5, _round_to_step(win_odds / divisor, 5))


def _tier_for_win_odds(win_odds: int) -> tuple[str, str]:
    if win_odds <= 900:
        return ("FAVORITE", "tier-favorite")
    if win_odds <= 3000:
        return ("CONTENDER", "tier-contender")
    if win_odds <= 7000:
        return ("VALUE", "tier-value")
    return ("LONGSHOT", "tier-longshot")


def _result_class(finish: str) -> str:
    f = (finish or "").strip()
    u = f.upper()

    if u in {"", "NA", "N/A", "-"}:
        return "result-na"
    if u in {"WIN", "W", "1"}:
        return "result-win"
    if u in {"MC", "CUT", "MDF"}:
        return "result-mc"
    if u in {"WD", "DQ", "DNS"}:
        return "result-wd"

    # Ordinals like 2nd/3rd
    if len(f) >= 3 and f[-2:].lower() in {"st", "nd", "rd", "th"} and f[:-2].isdigit():
        pos = int(f[:-2])
        if pos <= 1:
            return "result-win"
        if pos <= 5:
            return "result-top5"
        if pos <= 10:
            return "result-top10"
        if pos <= 25:
            return "result-top25"
        return "result-made"

    if u.startswith("T") and u[1:].isdigit():
        pos = int(u[1:])
        if pos <= 1:
            return "result-win"
        if pos <= 5:
            return "result-top5"
        if pos <= 10:
            return "result-top10"
        if pos <= 25:
            return "result-top25"
        return "result-made"
    if u.isdigit():
        pos = int(u)
        if pos <= 1:
            return "result-win"
        if pos <= 5:
            return "result-top5"
        if pos <= 10:
            return "result-top10"
        if pos <= 25:
            return "result-top25"
        return "result-made"

    return "result-made"


def _country_display(country_code: str, owgr: str) -> str:
    return country_display_html(country_code=country_code, owgr=owgr)


def _find_sport_key_for_amex(client: OddsAPIClient) -> Optional[dict]:
    sports = client.get_golf_sports()
    if not sports:
        return None
    for s in sports:
        title = (s.get("title") or "").lower()
        if "american express" in title:
            return s
    for s in sports:
        title = (s.get("title") or "").lower()
        if "amex" in title:
            return s
    return sports[0]


def load_odds_from_json(path: Path) -> dict[str, int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "odds" in raw and isinstance(raw["odds"], dict):
        out: dict[str, int] = {}
        for name, info in raw["odds"].items():
            if isinstance(info, dict) and "odds" in info:
                out[name] = int(info["odds"])
        return out
    if isinstance(raw, dict):
        return {k: int(v) for k, v in raw.items()}
    raise ValueError("Unsupported odds JSON format")


def load_players_data(
    path: Path,
) -> tuple[dict[str, int], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, int]]]:
    """Load odds + player info + historical finishes from a bundle JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}, {}, {}, {}

    odds_block = raw.get("odds") if isinstance(raw.get("odds"), dict) else {}
    odds_by_player: dict[str, int] = {}
    place_odds: dict[str, dict[str, int]] = {}
    for name, info in odds_block.items():
        if isinstance(info, dict) and "odds" in info:
            try:
                odds_by_player[str(name)] = int(info["odds"])
            except Exception:
                continue

            # Optional placement odds (may be missing for some players)
            top5 = info.get("top5")
            top10 = info.get("top10")
            entry: dict[str, int] = {}
            try:
                if top5 is not None:
                    entry["top5"] = int(top5)
            except Exception:
                pass
            try:
                if top10 is not None:
                    entry["top10"] = int(top10)
            except Exception:
                pass
            if entry:
                place_odds[str(name)] = entry

    players_info = raw.get("players") if isinstance(raw.get("players"), dict) else {}
    historical = raw.get("historical") if isinstance(raw.get("historical"), dict) else {}
    return odds_by_player, players_info, historical, place_odds


def load_storylines(path: Path) -> dict[str, str]:
    """Load storylines from either a flat mapping or a structured file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("storylines"), dict):
        raw = raw["storylines"]
    if isinstance(raw, dict):
        out: dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(v, dict) and "storyline" in v:
                out[str(k)] = str(v.get("storyline") or "").strip()
            else:
                out[str(k)] = str(v or "").strip()
        return out
    return {}


def load_recent_form_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k): str(v or "—").strip() or "—" for k, v in raw.items()}
    except Exception:
        return {}
    return {}


_RECENT_FORM_HARD_JUNK_RE = re.compile(
    r"(american express|odds|picks|predictions|best bets|full field|tickets|parking|schedule|prize money|how much|betting tips)",
    re.IGNORECASE,
)

_RECENT_FORM_RESULT_TOKEN_RE = re.compile(r"\b(T\d+|MC|WD|DQ|DNS)\b")


def _is_recent_form_usable(value: str) -> bool:
    v = (value or "").strip()
    if not v or v == "—":
        return False
    # Explicit results are always fine.
    if _RECENT_FORM_RESULT_TOKEN_RE.search(v):
        return True
    # Hard junk is never fine.
    if _RECENT_FORM_HARD_JUNK_RE.search(v):
        return False
    return True


def _render_recent_form(name: str, value: str) -> str:
    """
    Render recent form for display:
    - If it looks like a real result (T##/MC/WD/etc), show it.
    - If it's hard-junk (odds/picks/etc), hide it as "—".
    - Otherwise, treat it as a headline-style signal and label it.
    """
    v = (value or "").strip() or "—"
    if v == "—":
        return "—"
    if _RECENT_FORM_HARD_JUNK_RE.search(v):
        return "—"
    if _RECENT_FORM_RESULT_TOKEN_RE.search(v):
        return v
    # Soft fallback: keep it, but make it obvious it’s not a result.
    # Clip to keep table tidy.
    clipped = v if len(v) <= 95 else (v[:92].rstrip() + "…")
    return f"In the news: {clipped}"


def _fmt_month_year(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        # Example: "2026-01-15T19:00:00.000Z"
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.strftime("%b %Y")
    except Exception:
        return ""


def _normalize_finish_token(pos: Any) -> str:
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


def _recent_form_from_results(rows: list[dict]) -> str:
    """
    Convert BallDontLie tournament_results rows into a short, readable "recent form" blurb.
    """
    if not rows:
        return "—"

    def _status_ok(r: dict) -> bool:
        t = r.get("tournament") if isinstance(r.get("tournament"), dict) else {}
        status = str(t.get("status") or "").strip().lower()
        return status in {"completed", "complete", ""}  # tolerate missing

    rows = [r for r in rows if _status_ok(r)]

    def _dt(r: dict) -> datetime | None:
        t = r.get("tournament") if isinstance(r.get("tournament"), dict) else {}
        iso = t.get("start_date")
        if not iso:
            return None
        try:
            return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

    ordered = sorted(rows, key=lambda r: _dt(r) or datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)
    last = ordered[0]
    t = last.get("tournament") if isinstance(last.get("tournament"), dict) else {}
    t_name = str(t.get("name") or "").strip() or "Last start"
    when = _fmt_month_year(t.get("start_date"))
    last_dt = _dt(last)
    pos = _normalize_finish_token(last.get("position"))
    rel = last.get("par_relative_score")
    rel_str = ""
    try:
        if isinstance(rel, (int, float)):
            rel_str = f" ({rel:+.0f})"
    except Exception:
        rel_str = ""

    # Add a little color without inventing facts.
    vibe = ""
    if pos == "1" or pos.upper() in {"WIN", "W"}:
        vibe = " — winner energy"
    elif pos.startswith("T") and pos[1:].isdigit() and int(pos[1:]) <= 10:
        vibe = " — trending"
    elif pos.isdigit() and int(pos) <= 10:
        vibe = " — trending"
    elif pos == "MC":
        vibe = " — looking to bounce back"

    # "Hasn't played since X" style when it's been a while.
    if last_dt is not None:
        gap_days = (datetime.now(timezone.utc) - last_dt).days
        if gap_days >= 45:
            left = f"Last start: {t_name}" + (f" ({when})" if when else "")
            right = f"{pos}{rel_str}".strip()
            return f"{left} {right} — quiet since".strip()

    left = f"Last start: {t_name}" + (f" ({when})" if when else "")
    right = f"{pos}{rel_str}".strip()
    if right:
        out = f"{left}: {right}{vibe}"
    else:
        out = f"{left}{vibe}".strip()

    # If we have a prior start, add it when it fits.
    if len(ordered) > 1:
        prev = ordered[1]
        pt = prev.get("tournament") if isinstance(prev.get("tournament"), dict) else {}
        p_name = str(pt.get("name") or "").strip()
        p_when = _fmt_month_year(pt.get("start_date"))
        p_pos = _normalize_finish_token(prev.get("position"))
        if p_name and p_pos:
            tail = f" · prev {p_name}" + (f" ({p_when})" if p_when else "") + f" {p_pos}"
            if len(out) + len(tail) <= 110:
                out += tail

    return out


def enrich_recent_form_from_pga_results(
    *,
    player_names: list[str],
    cache: dict[str, str],
    seasons: list[int],
    max_pages: int = 50,
) -> dict[str, str]:
    """
    Best-effort enrichment using BallDontLie PGA tournament results.

    This aims to create "Last start: EVENT (Mon YYYY) T##" style blurbs.
    """
    try:
        with PGAAPIClient() as pga:
            # Build a name->id map with a few pages to avoid 1 request per player.
            players = pga.get_all_players_paginated(max_pages=10)

            def norm(n: str) -> str:
                s = (n or "").lower()
                s = re.sub(r"[^a-z0-9\\s]", " ", s)
                return re.sub(r"\\s+", " ", s).strip()

            by_norm: dict[str, int] = {}
            for pl in players:
                dn = str(pl.get("display_name") or "").strip()
                pid = pl.get("id")
                if not dn or not isinstance(pid, int):
                    continue
                by_norm.setdefault(norm(dn), pid)

            wanted_ids: dict[str, int] = {}
            for name in player_names:
                if _is_recent_form_usable(cache.get(name, "")):
                    continue
                pid = by_norm.get(norm(name))
                if isinstance(pid, int):
                    wanted_ids[name] = pid

            if not wanted_ids:
                return cache

            # Fetch results in batches by season, then choose the latest per player.
            rows_by_player: dict[int, list[dict]] = {pid: [] for pid in wanted_ids.values()}

            # Chunk to keep query strings reasonable.
            ids = list(set(wanted_ids.values()))
            chunks = [ids[i : i + 40] for i in range(0, len(ids), 40)]

            for season in seasons:
                for chunk in chunks:
                    cursor = None
                    pages = 0
                    while True:
                        pages += 1
                        if pages > max_pages:
                            break
                        resp = pga.get_tournament_results(season=season, player_ids=chunk, per_page=100, cursor=cursor)
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

            # Write blurbs back to cache
            for name, pid in wanted_ids.items():
                blurb = _recent_form_from_results(rows_by_player.get(pid, []))
                if blurb and blurb != "—":
                    cache[name] = blurb

    except Exception:
        # Any failure (missing key, plan tier, network) -> no-op
        return cache

    return cache


def save_recent_form_cache(path: Path, data: dict[str, str]) -> None:
    try:
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        # Best-effort cache only
        return


def enrich_recent_form_from_news(
    *,
    player_names: list[str],
    tournament_name: str,
    cache: dict[str, str],
    days: int,
    max_results: int,
) -> dict[str, str]:
    """Populate recent form with a headline-driven blurb (best effort)."""
    use_news = os.getenv("USE_NEWS", "1").strip() not in {"0", "false", "False", "no", "NO"}
    if not use_news:
        return cache

    try:
        with GolfNewsClient() as news_client:
            for name in player_names:
                if name in RECENT_FORM_OVERRIDES:
                    continue
                if _is_recent_form_usable(cache.get(name, "")):
                    continue
                try:
                    # First pass: bias toward tournament-specific headlines.
                    articles = news_client.search_player_news(
                        name,
                        tournament_name=tournament_name,
                        days=days,
                        max_results=max_results,
                    )

                    # Second pass: broader query if tournament-bias yields nothing.
                    if not articles:
                        articles = news_client.search_player_news(
                            name,
                            tournament_name=None,
                            days=days,
                            max_results=max_results,
                        )

                    # Third pass: handle names with punctuation/initials (e.g. "K.H. Lee").
                    if not articles and re.search(r"[.']", name):
                        cleaned = re.sub(r"[.']", "", name).strip()
                        if cleaned and cleaned != name:
                            articles = news_client.search_player_news(
                                cleaned,
                                tournament_name=None,
                                days=days,
                                max_results=max_results,
                            )
                except Exception:
                    articles = []
                candidate = (articles[0].title.strip() if articles else "—") or "—"
                if _is_recent_form_usable(candidate):
                    cache[name] = candidate
    except Exception:
        # Network may be unavailable; degrade gracefully.
        return cache

    return cache


_ODDS_TIER_SENTENCE_RE = re.compile(
    r"\s+at\s+[+-]\d{2,6},\s+which\s+places\s+him\s+in\s+the\s+.*?\s+tier\s+by\s+market\s+expectation\.",
    re.IGNORECASE,
)

_SITS_TIER_AT_ODDS_RE = re.compile(
    r"\b(?:sits|sitting)\s+in\s+the\s+.*?\s+tier\s+at\s+[+-]\d{2,6}\.",
    re.IGNORECASE,
)

_NEWS_CYCLE_SENTENCE_RE = re.compile(
    r"\s*The week[’']s news cycle has touched on.*?override the handicap\.\s*",
    re.IGNORECASE,
)


def _sanitize_storyline(text: str) -> str:
    """
    Remove brittle, fast-stale fragments from storylines.

    - Odds/tier-inference sentences quickly fall out of sync with live odds.
    - We already show odds in dedicated columns, so keep storylines about fit.
    """
    s = (text or "").strip()
    if not s:
        return ""
    s = _ODDS_TIER_SENTENCE_RE.sub(".", s)
    s = _SITS_TIER_AT_ODDS_RE.sub("", s)
    s = _NEWS_CYCLE_SENTENCE_RE.sub(" ", s)
    s = re.sub(r"\s+\.\s+", ". ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def _finish_rank(finish: str) -> int | None:
    """
    Convert finish tokens (T5/10/WIN/MC/WD/NA) into a comparable rank.
    Lower is better. Non-numeric finishes return None.
    """
    f = (finish or "").strip()
    if not f:
        return None
    u = f.upper()
    if u in {"NA", "N/A", "—", "-"}:
        return None
    if u in {"WIN", "W", "1"}:
        return 1
    if u.startswith("T") and u[1:].isdigit():
        return int(u[1:])
    if u.isdigit():
        return int(u)
    return None


def _stable_pick(name: str, options: list[str]) -> str:
    if not options:
        return ""
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % len(options)
    return options[idx]


def _build_personalized_storyline(
    *,
    name: str,
    country: str,
    owgr: str,
    history: dict[str | int, Any],
    recent_form: str,
) -> str:
    """
    Build a personalized "Why they could win" blurb using only our known inputs:
    - 2023–2025 AMEX finishes (when present)
    - OWGR (when present)
    - Recent form string (result-like or a labeled news signal)
    """
    h25 = str(history.get(2025) or history.get("2025") or "NA")
    h24 = str(history.get(2024) or history.get("2024") or "NA")
    h23 = str(history.get(2023) or history.get("2023") or "NA")

    hist_parts = []
    for yr, val in [(2025, h25), (2024, h24), (2023, h23)]:
        v = str(val or "").strip()
        if v and v.upper() not in {"NA", "N/A", "—", "-"}:
            hist_parts.append((yr, v))

    best = None
    for yr, v in hist_parts:
        r = _finish_rank(v)
        if r is None:
            continue
        if best is None or r < best[2]:
            best = (yr, v, r)

    # Trend (best-effort): compare the numeric ranks we have in chronological order.
    numeric_by_year = []
    for yr, v in sorted(hist_parts, key=lambda x: x[0]):
        r = _finish_rank(v)
        if r is not None:
            numeric_by_year.append((yr, r))
    trend = ""
    if len(numeric_by_year) >= 2:
        (y1, r1), (y2, r2) = numeric_by_year[-2], numeric_by_year[-1]
        if r2 < r1:
            trend = "The recent trend line points the right way."
        elif r2 > r1:
            trend = "The recent trend line is mixed, but the ceiling is still there."

    intl = (country or "").strip().upper() not in {"", "USA"}
    owgr_txt = f"OWGR #{owgr}" if (owgr or "").strip().isdigit() else ""

    # Build a first sentence that actually starts with the player (reduces repetition).
    if best:
        best_clause = f"{best[1]} in {best[0]}"
    else:
        best_clause = ""

    # If recent_form is a result-like string, it tends to be a good “lead”.
    rf = (recent_form or "—").strip()
    rf_lead = ""
    if rf and rf != "—" and not rf.lower().startswith("in the news:"):
        # Keep first sentence tidy
        rf_lead = rf if len(rf) <= 70 else rf[:67].rstrip() + "…"

    lead_opts: list[str] = []
    if best_clause:
        lead_opts += [
            f"{name} has already shown a ceiling at PGA West ({best_clause}).",
            f"{name} isn’t guessing at this venue—{best_clause} is on the resume.",
            f"{name} has a real “this place fits” datapoint: {best_clause}.",
        ]
    else:
        lead_opts += [
            f"{name} doesn’t have much AMEX resume in our 2023–2025 snapshot—so this is a timing play.",
            f"{name} comes in without a loud PGA West track record in our recent data, which makes the form signal matter more.",
            f"{name} is one of the names where this week is more projection than résumé.",
        ]

    if rf_lead:
        lead_opts += [
            f"{name} arrives off {rf_lead}.",
            f"{name}’s last start reads like this: {rf_lead}.",
        ]

    if owgr_txt:
        lead_opts += [
            f"{name} ({owgr_txt}) is good enough to win if the scoring breaks his way.",
            f"{name} ({owgr_txt}) sits in that band where a clean week can turn into a real look.",
        ]

    hook = _stable_pick(name, lead_opts)

    # History sentence
    if hist_parts:
        hist_str = ", ".join([f"{yr}: {v}" for yr, v in hist_parts])
        hist_sentence = f"AMEX history: {hist_str}."
    else:
        hist_sentence = "AMEX history: no finish data in our 2023–2025 snapshot."

    if best and best[2] <= 10:
        resume = f"He’s already shown he can get into the mix here ({best[1]} in {best[0]})."
    elif best and best[2] <= 25:
        resume = f"There’s at least a baseline here ({best[1]} in {best[0]}), which matters in a birdie-fest."
    elif best:
        resume = "Course comfort is still a question, but the format keeps the door open if he starts fast."
    else:
        resume = "With less local resume to lean on, this one is more about timing than history."

    # Recent form sentence(s)
    if rf and rf != "—":
        if rf.lower().startswith("in the news:"):
            rf_sentence = f"Recent chatter: {rf.replace('In the news:', '').strip()}."
        else:
            # If the lead already used it, vary the line.
            rf_sentence = (
                "Momentum check: that last-start line is either a confidence boost or a bounce-back spot."
                if rf_lead
                else f"Last-start snapshot: {rf}."
            )
    else:
        rf_sentence = "Recent form: limited signal in the current cache."

    id_sentence = " · ".join([p for p in [("🌍" if intl else ""), owgr_txt] if p]).strip(" ·")
    if id_sentence:
        id_sentence = f"{id_sentence}."

    closer_opts = [
        "If he keeps the card quiet and turns his best stretches into birdie runs, he’ll be in the photo late.",
        "This format rewards anyone who can stack red numbers without giving them all back on one sloppy hole.",
        "The winning version is the one that converts chances in bunches—because everyone will have chances here.",
        "If he opens with two solid scoring days, the pressure flips to everyone else to keep up.",
        "The case is not perfection; it’s sustained scoring with just enough damage control to stay on script.",
    ]
    closer = _stable_pick(name + "|close", closer_opts)

    out = " ".join([s for s in [hook, id_sentence, hist_sentence, resume, trend, rf_sentence, closer] if s]).strip()
    return re.sub(r"\s{2,}", " ", out)


def build_players(
    odds_by_player: dict[str, int],
    max_players: Optional[int],
    *,
    players_info: Optional[dict[str, dict[str, Any]]] = None,
    historical: Optional[dict[str, dict[str, Any]]] = None,
    storylines: Optional[dict[str, str]] = None,
    recent_form_cache: Optional[dict[str, str]] = None,
    place_odds_by_player: Optional[dict[str, dict[str, int]]] = None,
) -> list[dict[str, Any]]:
    ordered = sorted(odds_by_player.items(), key=lambda kv: kv[1])
    if max_players is not None:
        ordered = ordered[: max_players]

    players: list[dict[str, Any]] = []
    for idx, (name, win_odds_int) in enumerate(ordered, 1):
        manual = MANUAL_PROFILES.get(name, {})
        info = (players_info or {}).get(name, {}) if players_info else {}
        country = str(manual.get("country") or info.get("country") or "")
        owgr = str(manual.get("owgr") or info.get("owgr") or "")
        history = manual.get("history") or ((historical or {}).get(name, {}) if historical else {}) or {}
        tier_label, tier_class = _tier_for_win_odds(win_odds_int)
        recent_form = str(
            RECENT_FORM_OVERRIDES.get(
                name,
                (recent_form_cache or {}).get(name, "—") if recent_form_cache else "—",
            )
        )
        if name not in RECENT_FORM_OVERRIDES:
            recent_form = _render_recent_form(name, recent_form)

        # Always prefer a personalized storyline built from our known fields.
        # Manual profiles (e.g., Scottie) can override this by providing a storyline.
        storyline = str(manual.get("storyline") or "").strip()
        if not storyline:
            storyline = _build_personalized_storyline(
                name=name,
                country=country,
                owgr=owgr,
                history=history,
                recent_form=recent_form,
            )

        # Always sanitize after fallback construction so we strip brittle fragments.
        storyline = _sanitize_storyline(storyline)

        def _hist(year: int) -> str:
            return str(history.get(year) or history.get(str(year)) or "NA")

        place = (place_odds_by_player or {}).get(name, {}) if place_odds_by_player else {}
        top5_val = place.get("top5")
        top10_val = place.get("top10")

        has_place_source = bool(place_odds_by_player)
        players.append(
            {
                "rank": idx,
                "name": name,
                "country": country,
                "owgr": owgr,
                "tier": tier_label,
                "tier_class": tier_class,
                "win_odds": _odds_to_str(win_odds_int),
                # If we have a real Top-5/Top-10 feed (DraftKings), do NOT fabricate missing prices.
                "top5_odds": (
                    _odds_to_str(int(top5_val))
                    if top5_val is not None
                    else ("—" if has_place_source else _odds_to_str(_estimate_place_odds(win_odds_int, 4)))
                ),
                "top10_odds": (
                    _odds_to_str(int(top10_val))
                    if top10_val is not None
                    else ("—" if has_place_source else _odds_to_str(_estimate_place_odds(win_odds_int, 8)))
                ),
                "storyline": storyline,
                "history_2025": _hist(2025),
                "history_2024": _hist(2024),
                "history_2023": _hist(2023),
                "recent_form": recent_form,
            }
        )
    return players


def load_legacy_players() -> list[dict[str, Any]]:
    """
    Fallback when ODDS_API_KEY isn't available.
    Uses the existing curated list in scripts/generate_american_express.py.
    """
    try:
        from scripts import generate_american_express as legacy
    except Exception as e:
        raise RuntimeError(f"Could not import legacy players list: {e}") from e

    players = []
    for p in getattr(legacy, "PLAYERS", []):
        players.append(dict(p))

    # Fix Scottie here too (legacy list had NAs + 'debut' text)
    for p in players:
        if p.get("name") == "Scottie Scheffler":
            p["history_2025"] = "WD"
            p["history_2024"] = "T17"
            p["history_2023"] = "T11"
            p["storyline"] = MANUAL_PROFILES["Scottie Scheffler"]["storyline"]
            # keep tier fields/odds as-is
            break

    # Attach recent form for all legacy players
    for p in players:
        name = str(p.get("name") or "")
        p["recent_form"] = RECENT_FORM_OVERRIDES.get(name, "—")

    return players


def generate_html(players: list[dict[str, Any]], weather_forecast: str = "") -> str:
    html = f"""<!--
SHOPIFY EMBED INSTRUCTIONS:
1. Upload these images to Shopify Files (Settings > Files):
   - COSMOS_Golf-Dec-Logo_001.png
   - american_express_course.jpg (PGA West Stadium Course image)

2. Copy the image URLs from Shopify Files

3. Replace the image URLs below with your Shopify file URLs

4. In Shopify Admin:
   - Go to Online Store > Pages > Add page
   - Or add this to an existing page using a Custom HTML section
   - Paste this entire code block
-->

<div class="cosmos-betting-preview">
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <style>
    .cosmos-betting-preview {{
      --bg: #ffffff;
      --text: #000000;
      --border: #d9d9d9;
      --odds-green: #0a7a3f;
      --finish-win: #0a7a3f;
      --finish-top5: #b07d00;
      --finish-top10: #005bbb;
      --finish-top25: #0077b6;
      --finish-made: #000000;
      --finish-bad: #b00020;
    }}

    .cosmos-betting-preview, .cosmos-betting-preview * {{
      box-sizing: border-box;
    }}

    .cosmos-betting-preview {{
      font-family: 'Rajdhani', sans-serif;
      background: var(--bg);
      color: var(--text);
      width: 100%;
      padding: 0;
      margin: 0;
      overflow-x: hidden;
    }}

    .cosmos-betting-preview header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 16px;
      padding: 18px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--bg);
    }}

    .cosmos-betting-preview .mission-tag {{
      font-family: 'Share Tech Mono', monospace;
      font-size: 12px;
      letter-spacing: 2px;
      opacity: 0.75;
      margin-bottom: 8px;
    }}

    .cosmos-betting-preview h1 {{
      font-family: 'Orbitron', sans-serif;
      font-size: 30px;
      font-weight: 900;
      letter-spacing: 1px;
      margin: 0 0 6px 0;
    }}

    .cosmos-betting-preview .subtitle {{
      font-size: 16px;
      opacity: 0.8;
    }}

    .cosmos-betting-preview .logo-container {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 10px;
      margin-left: auto;
      text-align: right;
    }}

    .cosmos-betting-preview .logo-container img {{
      height: 88px;
      width: auto;
      filter: none;
    }}

    .cosmos-betting-preview .pdf-button {{
      font-family: 'Orbitron', sans-serif;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid var(--text);
      background: var(--text);
      color: var(--bg);
      cursor: pointer;
      line-height: 1;
      user-select: none;
    }}

    .cosmos-betting-preview .pdf-button:hover {{
      background: var(--bg);
      color: var(--text);
    }}

    .cosmos-betting-preview .pdf-button:focus-visible {{
      outline: 2px solid var(--text);
      outline-offset: 2px;
    }}

    .cosmos-betting-preview .container {{
      max-width: 1680px;
      margin: 0 auto;
      padding: 16px;
    }}

    .cosmos-betting-preview .event-info {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      padding: 14px;
      margin: 16px 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--bg);
    }}

    .cosmos-betting-preview .info-block {{
      text-align: center;
      padding: 10px 8px;
    }}

    .cosmos-betting-preview .info-label {{
      font-family: 'Share Tech Mono', monospace;
      font-size: 12px;
      letter-spacing: 1px;
      text-transform: uppercase;
      opacity: 0.75;
      margin-bottom: 6px;
    }}

    .cosmos-betting-preview .info-value {{
      font-family: 'Orbitron', sans-serif;
      font-size: 16px;
      font-weight: 800;
    }}

    .cosmos-betting-preview .course-image {{
      width: 100%;
      margin: 16px 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      background: var(--bg);
    }}

    .cosmos-betting-preview .course-image img {{
      width: 100%;
      height: auto;
      display: block;
    }}

    .cosmos-betting-preview .section-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 22px 0 10px;
    }}

    .cosmos-betting-preview .section-header h2 {{
      font-family: 'Orbitron', sans-serif;
      font-size: 20px;
      font-weight: 900;
      letter-spacing: 1px;
      margin: 0;
    }}

    .cosmos-betting-preview .section-line {{
      flex: 1;
      height: 1px;
      background: var(--border);
    }}

    .cosmos-betting-preview .crew-picks {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
      background: var(--bg);
    }}

    .cosmos-betting-preview .crew-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}

    .cosmos-betting-preview .crew-card {{
      display: flex;
      gap: 12px;
      align-items: flex-start;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      background: var(--bg);
    }}

    .cosmos-betting-preview .crew-photo {{
      width: 64px;
      height: 64px;
      border-radius: 50%;
      object-fit: cover;
      border: 1px solid var(--border);
    }}

    .cosmos-betting-preview .crew-name {{
      font-family: 'Orbitron', sans-serif;
      font-size: 15px;
      font-weight: 900;
      margin-bottom: 6px;
    }}

    .cosmos-betting-preview .crew-picks-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      font-size: 14px;
    }}

    .cosmos-betting-preview .crew-picks-list li {{
      padding: 6px 0;
      border-bottom: 1px solid var(--border);
    }}

    .cosmos-betting-preview .crew-picks-list li:last-child {{
      border-bottom: none;
    }}

    .cosmos-betting-preview .pick-label {{
      font-family: 'Share Tech Mono', monospace;
      font-size: 11px;
      letter-spacing: 1px;
      text-transform: uppercase;
      opacity: 0.75;
      margin-right: 6px;
    }}

    .cosmos-betting-preview .pick-odds {{
      color: var(--odds-green);
      font-family: 'Orbitron', sans-serif;
      font-weight: 900;
    }}

    .cosmos-betting-preview .tab-navigation {{
      display: flex;
      gap: 8px;
      margin: 16px 0 0;
      border-bottom: 1px solid var(--border);
    }}

    .cosmos-betting-preview .tab-button {{
      font-family: 'Orbitron', sans-serif;
      background: var(--bg);
      border: 1px solid var(--border);
      border-bottom: none;
      color: var(--text);
      padding: 10px 12px;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 1px;
      text-transform: uppercase;
      cursor: pointer;
      border-top-left-radius: 8px;
      border-top-right-radius: 8px;
    }}

    .cosmos-betting-preview .tab-button.active {{
      border-color: var(--text);
    }}

    .cosmos-betting-preview .tab-content {{
      display: none;
    }}

    .cosmos-betting-preview .tab-content.active {{
      display: block;
    }}

    .cosmos-betting-preview .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      padding: 12px;
      margin: 12px 0 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--bg);
    }}

    .cosmos-betting-preview .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: 'Share Tech Mono', monospace;
      font-size: 11px;
    }}

    .cosmos-betting-preview .legend-color {{
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }}

    .cosmos-betting-preview .table-container {{
      margin: 12px 0 0;
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--bg);
    }}

    .cosmos-betting-preview table {{
      width: 100%;
      min-width: 1100px;
      border-collapse: collapse;
      font-size: 14px;
      color: var(--text);
      background: var(--bg);
    }}

    .cosmos-betting-preview th {{
      font-family: 'Share Tech Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding: 12px 10px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}

    .cosmos-betting-preview th.center {{
      text-align: center;
    }}

    .cosmos-betting-preview td {{
      padding: 12px 10px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
      background: var(--bg);
      color: var(--text);
    }}

    .cosmos-betting-preview .player-name {{
      font-family: 'Orbitron', sans-serif;
      font-size: 14px;
      font-weight: 900;
      margin-bottom: 4px;
    }}

    .cosmos-betting-preview .player-name a {{
      color: var(--text);
      text-decoration: none;
    }}

    .cosmos-betting-preview .player-country {{
      font-family: 'Share Tech Mono', monospace;
      font-size: 11px;
      opacity: 0.85;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .cosmos-betting-preview .player-country .flag-img {{
      width: 20px;
      height: 15px;
      border-radius: 2px;
      display: inline-block;
      vertical-align: middle;
      box-shadow: 0 0 0 1px rgba(0,0,0,0.10);
      background: #fff;
    }}

    .cosmos-betting-preview .player-country .country-code {{
      letter-spacing: 0.5px;
    }}

    .cosmos-betting-preview .player-country .owgr {{
      opacity: 0.85;
    }}

    .cosmos-betting-preview .storyline-cell {{
      min-width: 360px;
      max-width: 600px;
    }}

    .cosmos-betting-preview .storyline-text {{
      font-size: 14px;
      line-height: 1.45;
    }}

    .cosmos-betting-preview .result-value {{
      font-family: 'Share Tech Mono', monospace;
      font-size: 14px;
      font-weight: 900;
    }}

    .cosmos-betting-preview .result-win {{ color: var(--finish-win); }}
    .cosmos-betting-preview .result-top5 {{ color: var(--finish-top5); }}
    .cosmos-betting-preview .result-top10 {{ color: var(--finish-top10); }}
    .cosmos-betting-preview .result-top25 {{ color: var(--finish-top25); }}
    .cosmos-betting-preview .result-made {{ color: var(--finish-made); opacity: 0.9; }}
    .cosmos-betting-preview .result-mc {{ color: var(--finish-bad); }}
    .cosmos-betting-preview .result-wd {{ color: var(--finish-bad); }}
    .cosmos-betting-preview .result-na {{ color: var(--text); opacity: 0.55; font-style: italic; }}

    .cosmos-betting-preview .odds-value {{
      font-family: 'Orbitron', sans-serif;
      font-size: 14px;
      font-weight: 900;
      color: var(--odds-green);
    }}

    .cosmos-betting-preview .tier-badge {{
      display: inline-block;
      font-family: 'Share Tech Mono', monospace;
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 999px;
      margin-top: 6px;
      letter-spacing: 1px;
      border: 1px solid var(--border);
      background: var(--bg);
    }}

    /* Bring back the "cool" tier color coding */
    .cosmos-betting-preview .tier-badge.tier-favorite {{
      background: rgba(244, 196, 48, 0.22);
      border-color: #f4c430;
      color: #7a5a00;
    }}

    .cosmos-betting-preview .tier-badge.tier-contender {{
      background: rgba(0, 168, 107, 0.16);
      border-color: #00a86b;
      color: #0a7a3f;
    }}

    .cosmos-betting-preview .tier-badge.tier-value {{
      background: rgba(0, 102, 204, 0.14);
      border-color: #0066cc;
      color: #005bbb;
    }}

    .cosmos-betting-preview .tier-badge.tier-longshot {{
      background: rgba(220, 53, 69, 0.12);
      border-color: #dc3545;
      color: #b00020;
    }}

    /* Recent form column */
    .cosmos-betting-preview .recent-cell {{
      min-width: 220px;
      max-width: 320px;
    }}

    .cosmos-betting-preview .recent-text {{
      font-size: 13px;
      line-height: 1.35;
      color: var(--text);
    }}

    .cosmos-betting-preview footer {{
      text-align: center;
      padding: 22px 0 28px;
      margin-top: 22px;
      border-top: 1px solid var(--border);
      background: var(--bg);
    }}

    .cosmos-betting-preview .footer-text {{
      font-family: 'Share Tech Mono', monospace;
      font-size: 12px;
      letter-spacing: 2px;
    }}

    .cosmos-betting-preview .data-source {{
      font-size: 13px;
      opacity: 0.75;
      margin-top: 8px;
    }}

    @media (min-width: 768px) {{
      .cosmos-betting-preview h1 {{ font-size: 36px; }}
      .cosmos-betting-preview .logo-container img {{ height: 112px; }}
      .cosmos-betting-preview .tab-button {{ font-size: 14px; padding: 12px 14px; }}
    }}

    /* Make Shopify desktop feel wider (less boxed in) */
    @media (min-width: 1024px) {{
      .cosmos-betting-preview {{
        width: 100vw;
        margin-left: calc(50% - 50vw);
        margin-right: calc(50% - 50vw);
      }}

      .cosmos-betting-preview header {{
        padding-left: 28px;
        padding-right: 28px;
      }}

      .cosmos-betting-preview .container {{
        padding-left: 28px;
        padding-right: 28px;
      }}
    }}
  </style>

  <header>
    <div class="header-left">
      <div class="mission-tag">{TOURNAMENT.mission_tag}</div>
      <h1>{TOURNAMENT.name}</h1>
      <div class="subtitle">{TOURNAMENT.courses} · {TOURNAMENT.location} · {TOURNAMENT.dates}</div>
    </div>
    <div class="logo-container">
      <img src="{SHOPIFY_LOGO_URL}" alt="COSMOS Golf" style="max-width: 420px;">
      <button class="pdf-button" type="button" onclick="downloadPdf()" title="Opens print dialog — choose “Save as PDF”">Download PDF</button>
    </div>
  </header>

  <div class="container">
    <div class="section-header">
      <h2>Cosmos Crew Picks</h2>
      <div class="section-line"></div>
    </div>

    <div class="crew-picks">
      <div class="crew-grid">
"""

    for crew in CREW_PICKS:
        html += f"""
        <div class="crew-card">
          <img class="crew-photo" src="{crew['photo_url']}" alt="{crew['name']}">
          <div>
            <div class="crew-name">{crew['name']}</div>
            <ul class="crew-picks-list">
"""
        for pick in crew["picks"]:
            html += f"""              <li><span class="pick-label">{pick['label']}</span> {pick['player']} <span class="pick-odds">{pick['odds']}</span></li>
"""
        html += """            </ul>
          </div>
        </div>
"""

    html += f"""
      </div>
    </div>

    <div class="event-info">
      <div class="info-block"><div class="info-label">Total Purse</div><div class="info-value">{TOURNAMENT.total_purse}</div></div>
      <div class="info-block"><div class="info-label">Winner's Share</div><div class="info-value">{TOURNAMENT.winner_share}</div></div>
      <div class="info-block"><div class="info-label">Stadium Yds</div><div class="info-value">{TOURNAMENT.stadium_yards}</div></div>
      <div class="info-block"><div class="info-label">Par</div><div class="info-value">{TOURNAMENT.par}</div></div>
      <div class="info-block"><div class="info-label">Field Size</div><div class="info-value">{TOURNAMENT.field_size}</div></div>
      <div class="info-block"><div class="info-label">FedExCup Pts</div><div class="info-value">{TOURNAMENT.fedex_points}</div></div>
    </div>

    <div class="course-image">
      <img src="{SHOPIFY_COURSE_IMAGE_URL}" alt="PGA West Stadium Course - The American Express">
    </div>
"""

    # Add weather forecast if available
    if weather_forecast:
        html += f"""
    <div class="weather-forecast" style="background: #f8f9fa; border-left: 4px solid #000; padding: 16px 20px; margin: 24px 0; font-size: 15px; line-height: 1.6;">
      <strong style="font-size: 16px; display: block; margin-bottom: 8px;">⛅ Tournament Weather Forecast</strong>
      {weather_forecast}
    </div>
"""

    html += """
    <div class="section-header">
      <h2>Complete Betting Board</h2>
      <div class="section-line"></div>
    </div>

    <div class="tab-navigation">
      <button class="tab-button active" onclick="switchTab(event, 'tournament-odds')">Tournament Odds</button>
      <button class="tab-button" onclick="switchTab(event, 'daily-matchups')">Daily Matchups</button>
    </div>

    <div id="tournament-odds" class="tab-content active">
      <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-win);"></div><span>WIN / 1st</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-top5);"></div><span>TOP 5 (2nd-5th)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-top10);"></div><span>TOP 10 (6th-10th)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-top25);"></div><span>TOP 25 (11th-25th)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-made);"></div><span>MADE CUT (26th+)</span></div>
        <div class="legend-item"><div class="legend-color" style="background: var(--finish-bad);"></div><span>MC / WD</span></div>
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Why They Could Win</th>
              <th class="center">2025</th>
              <th class="center">2024</th>
              <th class="center">2023</th>
              <th class="center">Win Odds</th>
              <th class="center">Top 5</th>
              <th class="center">Top 10</th>
              <th>Recent Form</th>
            </tr>
          </thead>
          <tbody>
"""

    for p in players:
        country_disp = _country_display(p.get("country", ""), p.get("owgr", ""))
        is_international = (p.get("country") or "").strip().upper() not in {"", "USA"}
        globe = " 🌍" if is_international else ""

        h25 = str(p.get("history_2025", "NA"))
        h24 = str(p.get("history_2024", "NA"))
        h23 = str(p.get("history_2023", "NA"))
        recent = str(p.get("recent_form", "—") or "—")

        html += f"""
            <tr>
              <td>{p['rank']}</td>
              <td class="player-cell">
                <div class="player-name"><a href="https://www.google.com/search?q={p['name'].replace(' ', '+')}+PGA+Tour" target="_blank">{p['name']}{globe}</a></div>
                <div class="player-country">{country_disp}</div>
                <span class="tier-badge {p['tier_class']}">{p['tier']}</span>
              </td>
              <td class="storyline-cell"><div class="storyline-text">{p['storyline']}</div></td>
              <td class="result-cell"><span class="result-value {_result_class(h25)}">{h25}</span></td>
              <td class="result-cell"><span class="result-value {_result_class(h24)}">{h24}</span></td>
              <td class="result-cell"><span class="result-value {_result_class(h23)}">{h23}</span></td>
              <td class="odds-cell"><span class="odds-value">{p['win_odds']}</span></td>
              <td class="odds-cell"><span class="odds-value">{p['top5_odds']}</span></td>
              <td class="odds-cell"><span class="odds-value">{p['top10_odds']}</span></td>
              <td class="recent-cell"><div class="recent-text">{recent}</div></td>
            </tr>
"""

    html += """
          </tbody>
        </table>
      </div>
    </div>

    <div id="daily-matchups" class="tab-content">
      <div style="padding: 28px 12px; border: 1px solid var(--border); border-radius: 8px; margin-top: 12px;">
        <div style="font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 18px;">Daily Matchups Coming Soon</div>
        <div style="margin-top: 8px; font-size: 14px;">Head-to-head player matchups will be available closer to tournament time.</div>
      </div>
    </div>

    <footer>
      <div class="footer-text">COSMOS GOLF BETTING PREVIEW</div>
      <div class="data-source">Odds current as of January 2026 · Research your book for latest lines</div>
    </footer>
  </div>

  <script>
    function switchTab(event, tabName) {
      document.querySelectorAll('.cosmos-betting-preview .tab-content').forEach(tab => tab.classList.remove('active'));
      document.querySelectorAll('.cosmos-betting-preview .tab-button').forEach(btn => btn.classList.remove('active'));
      document.getElementById(tabName).classList.add('active');
      event.target.classList.add('active');
    }

    function downloadPdf() {
      window.print();
    }
  </script>
</div>
"""

    return html


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate readable AMEX 2026 HTML")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/Users/chrismiller/Documents/CosmosGolfBetting/american_express_2026.html"),
        help="Output HTML file path",
    )
    parser.add_argument("--max-players", type=int, default=None, help="Optional cap on players (default: all with odds)")
    parser.add_argument("--sport-key", type=str, default=None, help="The Odds API sport key (optional; auto-detect if omitted)")
    parser.add_argument("--odds-json", type=Path, default=None, help="Offline mode: JSON mapping player->odds")
    parser.add_argument(
        "--players-data",
        type=Path,
        default=None,
        help="Optional players-data JSON (odds + players + historical). Defaults to repo data if present.",
    )
    parser.add_argument(
        "--storylines-json",
        type=Path,
        default=None,
        help="Optional storylines JSON (player->storyline or {storylines:{...}}). Defaults to repo data if present.",
    )
    parser.add_argument(
        "--recent-form-cache",
        type=Path,
        default=None,
        help="Optional cache JSON (player->recent form string). Defaults to repo data path.",
    )
    parser.add_argument(
        "--enrich-recent-form",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Populate recent form via news RSS (best effort; cached).",
    )
    parser.add_argument("--news-days", type=int, default=21, help="News lookback window for recent form (days)")
    parser.add_argument("--news-max-results", type=int, default=2, help="Max news items to consider per player")
    parser.add_argument(
        "--recent-form-max-players",
        type=int,
        default=80,
        help="Max players to enrich with RSS for recent form (0 = all).",
    )
    parser.add_argument(
        "--auto-storylines",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-generate storylines (uses news RSS; LLM optional via ANTHROPIC_API_KEY).",
    )
    args = parser.parse_args()

    odds_by_player: dict[str, int] = {}
    players_info: dict[str, dict[str, Any]] = {}
    historical: dict[str, dict[str, Any]] = {}
    place_odds_by_player: dict[str, dict[str, int]] = {}

    # Load local players-data bundle first (works without ODDS_API_KEY).
    players_data_path = args.players_data or (DEFAULT_PLAYERS_DATA_PATH if DEFAULT_PLAYERS_DATA_PATH.exists() else None)
    if players_data_path and Path(players_data_path).exists():
        try:
            odds_local, players_info, historical, place_odds_by_player = load_players_data(Path(players_data_path))
            odds_by_player.update(odds_local)
        except Exception:
            pass

    # Load local odds mapping (often maintained manually).
    # If present, treat it as the roster source-of-truth (avoids stale extras).
    default_odds_map: dict[str, int] = {}
    if DEFAULT_ODDS_JSON_PATH.exists():
        try:
            default_odds_map = load_odds_from_json(DEFAULT_ODDS_JSON_PATH)
        except Exception:
            default_odds_map = {}
    if default_odds_map:
        odds_by_player = dict(default_odds_map)

    # Explicit offline odds file overrides everything else.
    if args.odds_json:
        odds_by_player = load_odds_from_json(args.odds_json)
        print(f"Loaded odds for {len(odds_by_player)} players from {args.odds_json}")
    else:
        # Try Odds API (if configured). If unavailable, keep local odds instead of forcing a curated 32.
        try:
            with OddsAPIClient() as odds_client:
                chosen = {"key": args.sport_key, "title": args.sport_key} if args.sport_key else _find_sport_key_for_amex(odds_client)
                if not chosen:
                    raise RuntimeError("No golf tournaments found in The Odds API")
                sport_key = chosen.get("key")
                sport_title = chosen.get("title")
                print(f"Fetching odds for: {sport_title} ({sport_key})")

                tournament_odds = odds_client.get_tournament_odds(sport_key)
                if not tournament_odds:
                    raise RuntimeError(f"No odds available for sport_key={sport_key}")

                api_count = 0
                for player_name in tournament_odds.get_all_players():
                    best = tournament_odds.get_player_best_odds(player_name)
                    if best:
                        odds_by_player[player_name] = int(best[1])
                        api_count += 1

            print(f"Found odds for {api_count} players via Odds API (using {len(odds_by_player)} total after merge)")
        except ValueError:
            if odds_by_player:
                print("ODDS_API_KEY not available; using local odds data.")
            else:
                print("ODDS_API_KEY not available and no local odds found; falling back to curated list.")
                players = load_legacy_players()
                if args.max_players is not None:
                    players = players[: args.max_players]
                args.output.write_text(generate_html(players), encoding="utf-8")
                print(f"Wrote {args.output} with {len(players)} players")
                return 0

    ordered_names = [name for name, _ in sorted(odds_by_player.items(), key=lambda kv: kv[1])]
    if args.max_players is not None:
        ordered_names = ordered_names[: args.max_players]

    # Load storylines (optional).
    storylines_path = args.storylines_json or (DEFAULT_STORYLINES_JSON_PATH if DEFAULT_STORYLINES_JSON_PATH.exists() else None)
    storylines: dict[str, str] = {}
    if storylines_path and Path(storylines_path).exists():
        try:
            storylines = load_storylines(Path(storylines_path))
        except Exception:
            storylines = {}

    # Auto-generate storylines (best-effort). This runs on every build by default
    # so the “Why they could win” column stays fresh.
    if args.auto_storylines and ordered_names:
        try:
            from scripts.generate_storylines import build_storyline_database
            odds_data = {n: {"odds": int(odds_by_player[n])} for n in ordered_names if n in odds_by_player}
            storylines = build_storyline_database(
                ordered_names,
                TOURNAMENT.name,
                historical or {},
                odds_data,
                players_info or {},
                None,
            )
            if storylines_path:
                output_data = {
                    "tournament": TOURNAMENT.name,
                    "generated_at": __import__("datetime").datetime.now().isoformat(),
                    "storylines": storylines,
                    "metadata": {"player_count": len(ordered_names)},
                }
                Path(storylines_path).write_text(json.dumps(output_data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"⚠️  Storyline generation skipped/failed: {e}")

    # Recent form cache + optional enrichment.
    recent_cache_path = args.recent_form_cache or DEFAULT_RECENT_FORM_CACHE_PATH
    recent_cache = load_recent_form_cache(recent_cache_path) if recent_cache_path else {}
    if args.enrich_recent_form and ordered_names:
        if args.recent_form_max_players and args.recent_form_max_players > 0:
            enrich_names = ordered_names[: args.recent_form_max_players]
        else:
            enrich_names = ordered_names
        # Prefer real results (when available) over headlines.
        recent_cache = enrich_recent_form_from_pga_results(
            player_names=enrich_names,
            cache=recent_cache,
            seasons=[2026, 2025],
        )

        # Fall back to RSS headlines only when we still have nothing usable.
        recent_cache = enrich_recent_form_from_news(
            player_names=enrich_names,
            tournament_name=TOURNAMENT.name,
            cache=recent_cache,
            days=args.news_days,
            max_results=args.news_max_results,
        )
        if recent_cache_path:
            save_recent_form_cache(recent_cache_path, recent_cache)

    players = build_players(
        odds_by_player,
        args.max_players,
        players_info=players_info,
        historical=historical,
        storylines=storylines,
        recent_form_cache=recent_cache,
        place_odds_by_player=place_odds_by_player,
    )

    # Load weather forecast
    weather_forecast = ""
    if DEFAULT_WEATHER_JSON_PATH.exists():
        try:
            weather_data = json.loads(DEFAULT_WEATHER_JSON_PATH.read_text(encoding="utf-8"))
            weather_forecast = weather_data.get("forecast", "")
        except Exception:
            weather_forecast = ""

    args.output.write_text(generate_html(players, weather_forecast), encoding="utf-8")
    print(f"Wrote {args.output} with {len(players)} players")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

