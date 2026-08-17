#!/usr/bin/env python3
"""
Generate Tournament Betting Preview HTML

A generic, parameterized template generator for any PGA Tour tournament.
Takes tournament configuration and player data as input, outputs production-ready HTML.

Usage:
    python scripts/generate_tournament_html.py --tournament "Farmers Insurance Open" --year 2026
    python scripts/generate_tournament_html.py --config data/farmers_insurance_open_2026_config.json

The script loads:
1. Tournament config from pga_schedule_2026.json (or custom config)
2. Player data from {slug}_{year}_players_data.json
3. Storylines from {slug}_{year}_storylines.json (if exists)
4. Crew picks from crew_picks.json (if exists)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent


def _slugify(name: str) -> str:
    """Convert tournament name to slug."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def page_handle(slug_or_name: str, year: int) -> str:
    """Shopify page handle for a tournament; MUST stay in sync with the
    email newsletter's default CTA link (generate_email_newsletter.py).

    Pass the SCHEDULE slug when available — sponsor/location-named events
    (Memorial, Pebble, etc.) use short schedule slugs that differ from
    _slugify(name). _slugify is idempotent on slugs, so either form works
    for events whose slug matches their name.

    An optional `page_handle` field in the schedule entry overrides the
    derived value, for pages published under a shortened handle (FedEx
    St. Jude lives at 2026-fedex-st-jude, not -championship). The year
    prefix is still added here, so the override is the bare stem."""
    override = _schedule_page_handle(slug_or_name)
    stem = override or _slugify(slug_or_name).replace("_", "-")
    return f"{year}-{stem}"


def _schedule_page_handle(slug_or_name: str) -> Optional[str]:
    """`page_handle` override from the schedule entry, if one is set."""
    try:
        schedule = load_schedule()
    except (OSError, ValueError):
        return None
    slug = _slugify(slug_or_name)
    for t in schedule.get("tournaments", []) + schedule.get("fall_schedule", []):
        if t.get("slug") == slug or _slugify(t.get("name", "")) == slug:
            return t.get("page_handle") or None
    return None


def page_title(tournament: dict, year: int) -> str:
    """Shopify page title: '{Year} {Name}', honoring an optional
    page_nickname override from the schedule JSON (title only — the
    handle always derives from the official name)."""
    return f"{year} {tournament.get('page_nickname') or tournament.get('name', '')}".strip()


def _format_purse(purse: str) -> str:
    """Ensure purse is formatted nicely."""
    if purse.startswith("$"):
        return purse
    return f"${purse}"


def _format_odds(odds: int) -> str:
    """Format odds integer to display string."""
    if odds is None:
        return "N/A"
    if odds >= 0:
        return f"+{odds}"
    return str(odds)


def _normalize_finish(value: Any) -> str:
    """Normalize tournament finish for display."""
    if value is None:
        return "NA"
    s = str(value).strip().upper()
    if s in {"", "N/A", "NONE", "NULL", "-"}:
        return "NA"
    return s


def _result_class(value: str) -> str:
    """Determine CSS class for historical result."""
    v = _normalize_finish(value)

    if v == "1":
        return "win"

    # Numeric finishes
    pos = None
    if v.startswith("T") and v[1:].isdigit():
        pos = int(v[1:])
    elif v.isdigit():
        pos = int(v)

    if pos is not None:
        if pos <= 5:
            return "top5"
        if pos <= 10:
            return "top10"
        if pos <= 25:
            return "top25"
        return "made"

    if v in {"MC", "CUT", "MDF", "WD", "DQ", "DNS"}:
        return "mc"

    if v in {"NA", "-", "N/A"}:
        return "na"

    return "made"


def _get_tier_from_odds(odds: int) -> tuple[str, str]:
    """Determine tier based on win odds."""
    if odds is None:
        return "LONGSHOT", "tier-longshot"
    if odds <= 800:
        return "FAVORITE", "tier-favorite"
    elif odds <= 5000:
        return "CONTENDER", "tier-contender"
    elif odds <= 15000:
        return "VALUE", "tier-value"
    else:
        return "LONGSHOT", "tier-longshot"


def _get_odds_class(odds: int) -> str:
    """Get CSS class for odds highlighting."""
    if odds is None:
        return ""
    if odds <= 500:
        return "odds-favorite"
    return ""


def load_schedule() -> dict:
    """Load the PGA schedule database."""
    schedule_path = PROJECT_ROOT / "data" / "pga_schedule_2026.json"
    if schedule_path.exists():
        return json.loads(schedule_path.read_text(encoding="utf-8"))
    return {"tournaments": [], "fall_schedule": []}


def find_tournament_in_schedule(tournament_name: str, schedule: dict) -> Optional[dict]:
    """Find tournament config in schedule by name."""
    name_lower = tournament_name.lower()
    slug = _slugify(tournament_name)

    all_tournaments = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])

    for t in all_tournaments:
        if t.get("slug") == slug:
            return t
        if name_lower in t.get("name", "").lower():
            return t
        if t.get("name", "").lower() in name_lower:
            return t

    return None


def load_player_data(tournament_slug: str, year: int) -> dict:
    """Load player data from JSON file."""
    data_path = PROJECT_ROOT / "data" / f"{tournament_slug}_{year}_players_data.json"
    if data_path.exists():
        return json.loads(data_path.read_text(encoding="utf-8"))
    return {"odds": {}, "players": {}, "historical": {}}


def load_weather_forecast() -> str:
    """Load tournament weather forecast from data/tournament_weather.json (from fetch_tournament_weather.py)."""
    weather_path = PROJECT_ROOT / "data" / "tournament_weather.json"
    if weather_path.exists():
        try:
            data = json.loads(weather_path.read_text(encoding="utf-8"))
            return (data.get("forecast") or "").strip()
        except Exception:
            pass
    return "Weather forecast will be updated for tournament week."


def load_weather_periods() -> list:
    """Load the per-day AM/PM wind breakdown (`wind_by_day`) written by
    fetch_tournament_weather.py. Returns [] when absent (older data), so the wind
    renderer cleanly omits the table rather than erroring."""
    weather_path = PROJECT_ROOT / "data" / "tournament_weather.json"
    if weather_path.exists():
        try:
            data = json.loads(weather_path.read_text(encoding="utf-8"))
            return data.get("wind_by_day") or []
        except Exception:
            pass
    return []


def _render_wind_by_day_html(wind_by_day: list) -> str:
    """Compact AM/PM wind panel (8am + 12pm per day) with a links-golf wave read.

    Inline-styled so it renders identically in the full and v2/Shopify HTML, and a
    horizontal-scroll wrapper keeps it phone-safe. Returns '' when there's no data.
    """
    if not wind_by_day:
        return ""

    def _cell(block: Optional[dict]) -> str:
        if not block or block.get("speed_mph") is None:
            return '<span style="color:#999;">—</span>'
        deg = block.get("deg")
        arrow = ""
        if deg is not None:
            # Up-arrow rotated to point the way the wind travels (from-dir + 180°).
            arrow = (f'<span style="display:inline-block;transform:rotate({(int(deg) + 180) % 360}deg);'
                     f'color:#b8860b;font-weight:700;" title="Wind from {block.get("dir","")} ({deg}°)">↑</span> ')
        gust = block.get("gust_mph")
        gust_txt = f' <span style="color:#777;font-size:11px;">G{gust}</span>' if gust else ""
        return (f'{arrow}<strong>{block.get("speed_mph")}</strong>'
                f'<span style="font-size:11px;color:#555;"> mph {_escape_html(block.get("dir",""))}</span>{gust_txt}')

    rows = ""
    am_speeds: list[int] = []
    pm_speeds: list[int] = []
    for day in wind_by_day:
        am, pm = day.get("am"), day.get("pm")
        if am and am.get("speed_mph") is not None:
            am_speeds.append(am["speed_mph"])
        if pm and pm.get("speed_mph") is not None:
            pm_speeds.append(pm["speed_mph"])
        rows += (
            '<tr>'
            f'<td style="padding:6px 10px;font-weight:700;white-space:nowrap;">{_escape_html(day.get("weekday",""))}</td>'
            f'<td style="padding:6px 10px;">{_cell(am)}</td>'
            f'<td style="padding:6px 10px;">{_cell(pm)}</td>'
            '</tr>'
        )

    # Wave read: which half of the draw gets the lighter wind on average.
    wave = ""
    if am_speeds and pm_speeds:
        am_avg = sum(am_speeds) / len(am_speeds)
        pm_avg = sum(pm_speeds) / len(pm_speeds)
        if abs(am_avg - pm_avg) < 1.5:
            wave = "Little AM/PM split in the forecast — wind stays fairly even across the draw."
        elif am_avg < pm_avg:
            wave = f"Mornings play calmer (~{round(am_avg)} vs ~{round(pm_avg)} mph) — a slight edge to AM-wave tee times."
        else:
            wave = f"Afternoons play calmer (~{round(pm_avg)} vs ~{round(am_avg)} mph) — a slight edge to PM-wave tee times."
    wave_html = f'<div style="margin-top:10px;font-size:13px;color:#333;">🌊 <em>{_escape_html(wave)}</em></div>' if wave else ""

    return (
        '<div class="wind-by-day" style="background:#f8f9fa;border-left:4px solid #b8860b;'
        'padding:16px 20px;margin:24px 0;font-size:14px;line-height:1.5;">'
        '<strong style="font-size:16px;display:block;margin-bottom:10px;">🌬️ Wind by Day — Morning &amp; Afternoon</strong>'
        '<div style="overflow-x:auto;">'
        '<table style="border-collapse:collapse;width:100%;max-width:520px;">'
        '<thead><tr style="text-align:left;color:#666;font-size:12px;text-transform:uppercase;letter-spacing:.04em;">'
        '<th style="padding:6px 10px;">Day</th><th style="padding:6px 10px;">8 AM</th><th style="padding:6px 10px;">12 PM</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>{wave_html}</div>'
    )


def load_storylines(tournament_slug: str, year: int) -> dict:
    """Load AI-generated storylines if available."""
    storylines_path = PROJECT_ROOT / "data" / f"{tournament_slug}_{year}_storylines.json"
    if storylines_path.exists():
        data = json.loads(storylines_path.read_text(encoding="utf-8"))
        return data.get("storylines", {})
    return {}


def load_recent_form(tournament_slug: str, year: int) -> dict:
    """Load recent form data if available."""
    recent_form_path = PROJECT_ROOT / "data" / f"{tournament_slug}_{year}_recent_form.json"
    if recent_form_path.exists():
        return json.loads(recent_form_path.read_text(encoding="utf-8"))
    return {}


# --- Climber selection (shared by the v2 site HTML and the email newsletter) ---
# The email imports these via `gt.` — keep the selection logic here so both
# surfaces pick the same players; only the rendering differs per surface.

def finish_num(v) -> "int | None":
    """Numeric finish (T28->28, '1'->1). None for NA/—/MC/WD — non-finishes break a trend."""
    s = (str(v) if v is not None else "").strip().upper()
    if s in ("", "NA", "N/A", "—", "MC", "WD", "CUT", "DQ"):
        return None
    s = s.replace("T", "")
    return int(s) if s.isdigit() else None


def finish_disp(v) -> str:
    s = (str(v) if v is not None else "").strip()
    return "—" if s.upper() in ("", "NA", "N/A", "—") else s


def pick_trending_player(players: list, year: int):
    """Biggest climber AT THIS VENUE across the 3 prior years.

    Returns (player, [(year, finish_num, finish_display)]) or (None, None).
    Requires 2+ made cuts, an 8-spot jump, and a newest finish inside the top 25.
    """
    best = None
    for p in players:
        yearly = [
            (year - 3, p.get("history_prev3")),
            (year - 2, p.get("history_prev2")),
            (year - 1, p.get("history_prev1")),
        ]
        pts = [(y, finish_num(v), finish_disp(v)) for y, v in yearly]
        pts = [(y, n, d) for (y, n, d) in pts if n is not None]
        if len(pts) < 2:
            continue
        improvement = pts[0][1] - pts[-1][1]
        if improvement < 8 or pts[-1][1] > 25:
            continue
        score = (improvement, len(pts), -pts[-1][1])
        if best is None or score > best[0]:
            best = (score, p, pts)
    return (best[1], best[2]) if best else (None, None)


_FORM_LEG_RE = re.compile(r"\s*(.+?)\s*\(([^)]*)\):\s*(\S+?)\s*$")


def parse_recent_form(blob: str) -> list:
    """Parse a recent-form string into chronological [(event, when, finish)].

    Source format is newest-first, bullet-separated:
        "Rocket Classic (Jul 2026): T8 • 3M Open (Jul 2026): T31 • ..."
    Returned oldest-first so a climb reads left-to-right.
    """
    legs = []
    for chunk in (blob or "").split("•"):
        m = _FORM_LEG_RE.match(chunk.strip())
        if m:
            legs.append((m.group(1), m.group(2), m.group(3)))
    return legs[::-1]


def pick_form_climbers(players: list, count: int = 3, exclude: str = "") -> list:
    """Players whose last 3 starts show an improving finish trend.

    Strict pass: three consecutive made cuts, each better than the last
    (the "T53 -> T24 -> T15" shape). If that yields fewer than `count`, a
    relaxed pass fills the rest with players who still improved overall
    (first -> last) across three made cuts.

    Returns [{name, legs: [(event, finish)], improvement, best}] ranked by
    total improvement, then by how strong the most recent finish is.
    """
    def _rank(p, strict: bool):
        legs = parse_recent_form(p.get("recent_form", ""))
        if len(legs) < 3:
            return None
        last3 = legs[-3:]
        fins = [finish_num(f) for _, _, f in last3]
        if any(f is None for f in fins):          # an MC/WD breaks the story
            return None
        improved = fins[0] > fins[1] > fins[2] if strict else fins[0] > fins[2]
        if not improved:
            return None
        return {
            "name": p["name"],
            "legs": [(e, f) for e, _, f in last3],
            "improvement": fins[0] - fins[2],
            "best": fins[2],
        }

    picked, seen = [], {exclude} if exclude else set()
    for strict in (True, False):
        pool = [r for r in (_rank(p, strict) for p in players) if r and r["name"] not in seen]
        pool.sort(key=lambda r: (-r["improvement"], r["best"]))
        for r in pool:
            if len(picked) >= count:
                break
            picked.append(r)
            seen.add(r["name"])
        if len(picked) >= count:
            break
    return picked[:count]


def shorten_event(name: str) -> str:
    """Trim sponsor cruft so three legs fit on one line."""
    n = re.sub(r"\s+presented by .*$", "", name or "", flags=re.I)
    for long, short in (
        ("The Open Championship", "The Open"), ("Genesis Scottish Open", "Scottish Open"),
        ("Corales Puntacana Championship", "Corales"), ("The CJ Cup Byron Nelson", "Byron Nelson"),
        ("The Memorial Tournament", "The Memorial"), ("Charles Schwab Challenge", "Colonial"),
        ("John Deere Classic", "John Deere"), ("Travelers Championship", "Travelers"),
        ("RBC Canadian Open", "Canadian Open"), ("ISCO Championship", "ISCO"),
        ("Myrtle Beach Classic", "Myrtle Beach"), ("Rocket Classic", "Rocket"),
    ):
        if n == long:
            return short
    return n


def _render_climbers_v2(trending: tuple, climbers: list, course: str) -> str:
    """Trend bands for the v2/Shopify page: venue climber (gold) + form climbers (green).

    Mirrors the email's two bands so the site and the newsletter tell the same story.
    Returns '' when neither has data, so the section never renders as an empty shell.
    """
    blocks = ""

    tp, tpts = (trending or (None, None))
    if tp and tpts:
        path = ' <span class="clmb-arrow">&rarr;</span> '.join(
            f'<span class="clmb-leg{" clmb-now" if i == len(tpts) - 1 else ""}">'
            f'{_escape_html(str(y))} <strong>{_escape_html(d)}</strong></span>'
            for i, (y, n, d) in enumerate(tpts)
        )
        gain = tpts[0][1] - tpts[-1][1]
        blocks += f"""
            <div class="clmb-band clmb-venue">
                <div class="clmb-kicker">&#128200; Biggest Climber &middot; {_escape_html(course or "the host course")}</div>
                <div class="clmb-row">
                    <div class="clmb-who">{_escape_html(tp["name"])}</div>
                    <div class="clmb-path">{path}</div>
                    <div class="clmb-gain">&#9650;{gain}<span>spots</span></div>
                </div>
            </div>"""

    if climbers:
        rows = ""
        for c in climbers:
            path = ' <span class="clmb-arrow">&rarr;</span> '.join(
                f'<span class="clmb-leg{" clmb-now" if i == len(c["legs"]) - 1 else ""}">'
                f'{_escape_html(shorten_event(e))} <strong>{_escape_html(f)}</strong></span>'
                for i, (e, f) in enumerate(c["legs"])
            )
            rows += f"""
                    <div class="clmb-row">
                        <div class="clmb-who">{_escape_html(c["name"])}</div>
                        <div class="clmb-path">{path}</div>
                        <div class="clmb-gain">&#9650;{c["improvement"]}<span>spots</span></div>
                    </div>"""
        blocks += f"""
            <div class="clmb-band clmb-form">
                <div class="clmb-kicker">&#128293; Form Climbers &middot; Last 3 Starts</div>{rows}
            </div>"""

    return f'<div class="climbers-v2">{blocks}</div>' if blocks else ""


def load_datagolf_data(tournament_slug: str, year: int) -> dict:
    """Load Data Golf analytics data if available."""
    data_path = PROJECT_ROOT / "data" / f"{tournament_slug}_{year}_players_data.json"
    if data_path.exists():
        data = json.loads(data_path.read_text(encoding="utf-8"))
        return data.get("datagolf", {})
    return {}


def load_ai_insights(tournament_slug: str, year: int) -> dict:
    """Load AI-generated insights if available."""
    insights_path = PROJECT_ROOT / "data" / f"{tournament_slug}_{year}_insights.json"
    if insights_path.exists():
        return json.loads(insights_path.read_text(encoding="utf-8"))
    return {"executive_summary": "", "insights": []}


def load_matchups(tournament_slug: str, year: int) -> Optional[dict]:
    """Load matchup odds (2-ball, 3-ball) if available.

    Returns None when the file is missing OR every market is empty (e.g. early in
    the week before tee times post), so callers cleanly show "Coming Soon".
    """
    matchups_path = PROJECT_ROOT / "data" / f"{tournament_slug}_{year}_matchups.json"
    if matchups_path.exists():
        data = json.loads(matchups_path.read_text(encoding="utf-8"))
        if not any(
            data.get(k)
            for k in ("tournament_matchups", "round_matchups", "three_balls", "daily_three_balls")
        ):
            return None
        return data
    return None


def load_crew_placeholder() -> str | None:
    """Return placeholder text when crew picks aren't finalized yet (interim build).

    Set ``"placeholder": true`` (+ optional ``"placeholder_text"``) at the top of
    data/crew_picks.json to show a single "picks drop soon" card instead of the
    per-member grid. Flip it off once the real picks are filled in.
    """
    picks_path = PROJECT_ROOT / "data" / "crew_picks.json"
    if picks_path.exists():
        data = json.loads(picks_path.read_text(encoding="utf-8"))
        if data.get("placeholder"):
            return data.get("placeholder_text") or "Crew picks drop soon"
    return None


def load_crew_picks() -> list[dict]:
    """Load crew picks template."""
    picks_path = PROJECT_ROOT / "data" / "crew_picks.json"
    if picks_path.exists():
        data = json.loads(picks_path.read_text(encoding="utf-8"))
        return data.get("crew", [])

    # Default crew with TBD picks
    return [
        {
            "name": "Miller",
            "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/miller.jpg",
            "picks": [
                {"label": "Win", "player": "TBD", "odds": "TBD"},
                {"label": "Top 5", "player": "TBD", "odds": "TBD"},
                {"label": "Top 10", "player": "TBD", "odds": "TBD"}
            ]
        },
        {
            "name": "Kevin",
            "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kham.jpg",
            "picks": [
                {"label": "Win", "player": "TBD", "odds": "TBD"},
                {"label": "Top 5", "player": "TBD", "odds": "TBD"},
                {"label": "Top 10", "player": "TBD", "odds": "TBD"}
            ]
        },
        {
            "name": "Andrew",
            "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/andrew_hammond.jpg",
            "picks": [
                {"label": "Win", "player": "TBD", "odds": "TBD"},
                {"label": "Top 5", "player": "TBD", "odds": "TBD"},
                {"label": "Top 10", "player": "TBD", "odds": "TBD"}
            ]
        },
        {
            "name": "Kcon",
            "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kcon.jpg",
            "picks": [
                {"label": "Win", "player": "TBD", "odds": "TBD"},
                {"label": "Top 5", "player": "TBD", "odds": "TBD"},
                {"label": "Top 10", "player": "TBD", "odds": "TBD"}
            ]
        },
        {
            "name": "JB",
            "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/jb.png?v=1775705102",
            "picks": [
                {"label": "Win", "player": "TBD", "odds": "TBD"},
                {"label": "Top 5", "player": "TBD", "odds": "TBD"},
                {"label": "Top 10", "player": "TBD", "odds": "TBD"}
            ]
        }
    ]


# Country -> International flag mapping
INTERNATIONAL_COUNTRIES = {
    "SWE", "SCO", "ENG", "KOR", "AUS", "RSA", "JPN", "GER", "FRA", "IRL",
    "NZL", "ESP", "ITA", "NOR", "DEN", "BEL", "ARG", "CHI", "COL", "MEX",
    "CAN", "WAL", "NIR", "CHN", "TWN", "THA", "IND", "FIN", "AUT", "VEN"
}


def _format_sg(value: float | None, rank: int | None = None) -> str:
    """Format strokes gained value with optional rank."""
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    if rank:
        return f"{sign}{value:.2f} (#{rank})"
    return f"{sign}{value:.2f}"


def _format_prob(value: float | None) -> str:
    """Format probability as percentage."""
    if value is None:
        return "—"
    return f"{value:.1f}%"


def _format_course_fit(value: float | None) -> str:
    """Format course fit adjustment."""
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}"


def _is_raw_finish_storyline(text: str, history_2025: str = "") -> bool:
    """True if text looks like a raw finish or finish-only sentence rather than a real 'Why to Win' narrative."""
    if not text or not isinstance(text, str):
        return True
    t = text.strip()
    if len(t) <= 2:
        return True
    # Never use the actual 2025 history value as the storyline (e.g. "T25", "MC")
    if history_2025 and t == str(history_2025).strip():
        return True
    # Known finish codes that must never appear as the storyline
    if t.upper() in ("NA", "MC", "WD", "CUT", "DQ", "—", "-"):
        return True
    # T3, T25, 1, 2, 12 etc.
    if t.isdigit() or (t.startswith("T") and t[1:].isdigit()):
        return True
    # Too short to be a real narrative (avoid 2025 finish leaking into Why to Win)
    if len(t) < 40:
        return True
    # Reject "finish-only" sentences: short text that's mainly "finished T25 in 2025" / "2025: T12" with no real narrative
    if len(t) < 120 and "2025" in t:
        has_finish_code = bool(re.search(r"\b(T\d+|\d+th|MC|WD)\b", t, re.I)) or "finished" in t.lower() or "placed" in t.lower()
        has_narrative = any(w in t.lower() for w in ("odds", "value", "course", "iron", "win", "could", "should", "makes him", "thrive", "fit"))
        if has_finish_code and not has_narrative:
            return True
    return False


def build_player_list(
    player_data: dict,
    storylines: dict,
    recent_form: dict,
    current_year: int
) -> list[dict]:
    """Build sorted player list with all required fields."""
    odds_data = player_data.get("odds", {})
    historical = player_data.get("historical", {})
    # Support both old "players" structure and new separate sections
    players_info = player_data.get("players", {})
    countries_data = player_data.get("countries", {})
    owgr_data = player_data.get("owgr", {})
    datagolf = player_data.get("datagolf", {})

    players = []

    for name, odds_info in odds_data.items():
        win_odds = odds_info.get("odds", 9999)
        top5_odds = odds_info.get("top5")
        top10_odds = odds_info.get("top10")

        # Get player info - support both old nested structure and new flat structure
        info = players_info.get(name, {})
        country = info.get("country") or countries_data.get(name, "USA")
        owgr = info.get("owgr") or owgr_data.get(name, "-")

        # Get historical results (show 3 prior years: 2025, 2024, 2023 for a 2026 tournament)
        hist = historical.get(name, {})
        h_prev1 = hist.get(str(current_year - 1), "NA")  # 2025
        h_prev2 = hist.get(str(current_year - 2), "NA")  # 2024
        h_prev3 = hist.get(str(current_year - 3), "NA")  # 2023

        # Get tier
        tier, tier_class = _get_tier_from_odds(win_odds)
        odds_class = _get_odds_class(win_odds)

        # Get storyline: never use raw finish data (e.g. 2025 result) as "Why to Win"
        fallback_storyline = f"{name} looks to make an impact at this tournament."
        storyline = storylines.get(name, fallback_storyline)
        if _is_raw_finish_storyline(storyline, history_2025=h_prev1):
            storyline = fallback_storyline
        # Final safeguard: never show 2025 history value in the storyline cell (e.g. if they match by accident)
        display_storyline = fallback_storyline if (h_prev1 and storyline == str(h_prev1).strip()) else storyline

        # Check if international
        is_international = country.upper() in INTERNATIONAL_COUNTRIES

        # Get Data Golf analytics
        dg = datagolf.get(name, {})

        players.append({
            "name": name,
            "country": country,
            "owgr": str(owgr),
            "tier": tier,
            "tier_class": tier_class,
            "win_odds": _format_odds(win_odds),
            "win_odds_raw": win_odds,
            "top5_odds": _format_odds(top5_odds) if top5_odds else "N/A",
            "top10_odds": _format_odds(top10_odds) if top10_odds else "N/A",
            "odds_class": odds_class,
            "storyline": storyline,
            "_display_storyline": display_storyline,
            "history_prev1": _normalize_finish(h_prev1),
            "history_prev2": _normalize_finish(h_prev2),
            "history_prev3": _normalize_finish(h_prev3),
            "international": is_international,
            # Data Golf fields
            "sg_total": _format_sg(dg.get("sg_total"), dg.get("sg_total_rank")),
            "sg_total_raw": dg.get("sg_total"),
            "sg_ott": _format_sg(dg.get("sg_ott")),
            "sg_app": _format_sg(dg.get("sg_app")),
            "sg_arg": _format_sg(dg.get("sg_arg")),
            "sg_putt": _format_sg(dg.get("sg_putt")),
            "win_prob": _format_prob(dg.get("win_prob")),
            "win_prob_raw": dg.get("win_prob"),
            "top10_prob": _format_prob(dg.get("top_10_prob")),
            "course_fit": _format_course_fit(dg.get("course_fit")),
            "course_history_adj": _format_course_fit(dg.get("course_history")),
            "has_dg_data": bool(dg),
            "recent_form": recent_form.get(name, "—") or "—",
        })

    # Sort by win odds (favorites first)
    players.sort(key=lambda x: x["win_odds_raw"] if x["win_odds_raw"] is not None else 999999)

    # Add rank
    for i, p in enumerate(players, 1):
        p["rank"] = i

    return players


def _normalize_name_for_lookup(name: str) -> str:
    """Normalize player name for odds lookup (case-insensitive, strip, collapse accents)."""
    if not name or not isinstance(name, str):
        return ""
    s = name.strip().lower()
    # Collapse common accent variants so "Højgaard" matches "Hojgaard"
    for old, new in [("ø", "o"), ("ö", "o"), ("ó", "o"), ("ñ", "n"), ("á", "a"), ("é", "e"), ("í", "i"), ("ú", "u")]:
        s = s.replace(old, new)
    return s


def _player_odds_lookup(players: list[dict]) -> dict[str, dict]:
    """Build lookup: normalized_name -> { win_odds, top5_odds, top10_odds } for crew pick odds from GolfData API."""
    lookup = {}
    for p in players:
        key = _normalize_name_for_lookup(p.get("name", ""))
        if not key:
            continue
        lookup[key] = {
            "win_odds": p.get("win_odds") or "—",
            "top5_odds": p.get("top5_odds") or "—",
            "top10_odds": p.get("top10_odds") or "—",
        }
    return lookup


def _crew_pick_odds(pick: dict, odds_lookup: dict[str, dict]) -> str:
    """Resolve odds for a crew pick from GolfData API lookup; fallback to pick.odds or —."""
    label = (pick.get("label") or "").strip().lower()
    player_name = (pick.get("player") or "").strip()
    if not player_name or player_name.upper() == "TBD":
        return pick.get("odds") or "—"
    key = _normalize_name_for_lookup(player_name)
    row = odds_lookup.get(key) if key else None
    if not row:
        return pick.get("odds") or "—"
    if "win" in label or label == "1":
        return row["win_odds"]
    if "top 5" in label or "top5" in label or label == "5":
        return row["top5_odds"]
    if "top 10" in label or "top10" in label or label == "10":
        return row["top10_odds"]
    return pick.get("odds") or "—"


def format_dates(dates: dict) -> str:
    """Format tournament dates for display."""
    start = dates.get("start", "")
    end = dates.get("end", "")

    if not start:
        return "TBD"

    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else start_dt

        if start_dt.month == end_dt.month:
            return f"{start_dt.strftime('%B')} {start_dt.day}-{end_dt.day}, {start_dt.year}"
        else:
            return f"{start_dt.strftime('%B %d')} - {end_dt.strftime('%B %d')}, {start_dt.year}"
    except Exception:
        return f"{start} - {end}"


def _render_matchups_html(matchups: dict) -> str:
    """Render matchups section HTML (2-ball and 3-ball tables) for page and PDF."""
    out = []
    # Tournament 2-ball matchups
    two_ball = (matchups.get("tournament_matchups") or []) + (matchups.get("round_matchups") or [])
    if two_ball:
        out.append('<div class="matchups-section pdf-matchups"><h3 class="matchups-heading">Head-to-Head (2-Ball)</h3>')
        out.append('<table class="matchups-table"><thead><tr><th>Player</th><th class="center">Odds</th><th></th><th>Player</th><th class="center">Odds</th></tr></thead><tbody>')
        for m in two_ball[:40]:  # cap for PDF
            p1 = m.get("player_1_name", "—")
            p2 = m.get("player_2_name", "—")
            o1 = m.get("player_1_odds", "—")
            o2 = m.get("player_2_odds", "—")
            lean1 = m.get("player_1_lean", "")
            lean2 = m.get("player_2_lean", "")
            out.append(f'<tr class="matchup-row"><td>{p1}</td><td class="center">{o1}</td><td class="vs">vs</td><td>{p2}</td><td class="center">{o2}</td></tr>')
            if lean1 or lean2:
                out.append(f'<tr class="matchup-lean"><td colspan="2" class="lean">{lean1}</td><td></td><td colspan="2" class="lean">{lean2}</td></tr>')
        out.append("</tbody></table></div>")
    # 3-ball (daily_three_balls)
    three_ball = matchups.get("daily_three_balls") or matchups.get("three_balls") or []
    if three_ball:
        # DataGolf returns Round 1 twosomes as 2-ball + Tie markets (player_3 == "Tie").
        # Label those as head-to-head pairings; only call it "3-Balls" when there's a real third player.
        tie_mode = all((m.get("player_3_name") or "") in ("Tie", "") for m in three_ball)
        heading = "Round 1 — Head-to-Head Pairings" if tie_mode else "Round 1 — 3-Balls"
        p3_header = "Tie" if tie_mode else "Player 3"
        out.append(f'<div class="matchups-section pdf-matchups"><h3 class="matchups-heading">{heading}</h3>')
        out.append(f'<table class="matchups-table matchups-3ball"><thead><tr><th>Grp</th><th>Tee Time</th><th>Hole</th><th>Player 1</th><th>Odds</th><th>Player 2</th><th>Odds</th><th>{p3_header}</th><th>Odds</th></tr></thead><tbody>')
        for m in three_ball:
            teetime = m.get("teetime", "")
            if " " in teetime:
                teetime = teetime.split(" ")[1][:5]  # "HH:MM"
            hole = m.get("start_hole", "")
            out.append(
                f'<tr class="matchup-row">'
                f'<td>{m.get("group", "")}</td><td>{teetime}</td><td>{hole}</td>'
                f'<td>{m.get("player_1_name", "—")}</td><td class="center">{m.get("player_1_odds", "—")}</td>'
                f'<td>{m.get("player_2_name", "—")}</td><td class="center">{m.get("player_2_odds", "—")}</td>'
                f'<td>{m.get("player_3_name", "—")}</td><td class="center">{m.get("player_3_odds", "—")}</td>'
                f'</tr>'
            )
        out.append("</tbody></table></div>")
    return "\n".join(out) if out else ""


def generate_html(
    tournament: dict,
    players: list[dict],
    crew_picks: list[dict],
    year: int,
    insights: dict = None,
    matchups: Optional[dict] = None,
) -> str:
    """Generate the complete HTML preview. Table is always 4-column (#, Player, Why They Could Win, Win Odds) with expandable details."""

    tournament_name = tournament.get("name", "PGA Tour Tournament")
    tournament_dates = format_dates(tournament.get("dates", {}))
    tournament_location = tournament.get("location", "TBD")
    tournament_course = tournament.get("course", "TBD")
    purse = _format_purse(tournament.get("purse", "$0"))
    winner_share = _format_purse(tournament.get("winner_share", "$0"))
    par = tournament.get("par", 72)
    yards = tournament.get("yards", "TBD")
    field_size = tournament.get("field_size", 156)
    fedex_points = tournament.get("fedex_points", 500)

    course_img_src_full = course_image_src(tournament_name)

    if insights is None:
        insights = {"executive_summary": "", "insights": []}

    weather_forecast = load_weather_forecast()
    wind_by_day_html_full = _render_wind_by_day_html(load_weather_periods())

    matchups_html = _render_matchups_html(matchups) if matchups else ""
    # When matchups exist, lead the tab with the AI analysis placeholder so
    # inject_matchup_insights_into_html.py can drop in the styled AI block.
    matchups_tab_content = ("<!-- MATCHUP_AI_INSIGHTS -->\n" + matchups_html) if matchups_html else ""
    # Only surface the Daily Matchups tab when real matchup data exists. With no
    # data we omit the tab (and its nav) entirely rather than showing a "Coming
    # Soon" placeholder — cleaner for co-sanctioned/early-week builds with no matchups.
    show_matchups = bool(matchups_html)
    tab_nav_html = ('''<div class="tab-navigation">
            <button class="tab-button active" onclick="switchTab(event, 'tournament-odds')">
                Tournament Odds
            </button>
            <button class="tab-button" onclick="switchTab(event, 'daily-matchups')">
                Daily Matchups
            </button>
        </div>''' if show_matchups else '')
    matchups_panel_html = ('<div id="daily-matchups" class="tab-content">'
                           + matchups_tab_content + '</div>') if show_matchups else ''

    mission_tag = f"// BETTING PREVIEW - {tournament_dates.split(',')[0].upper()}"

    # Calculate history column headers (show prior 3 years since current year hasn't happened)
    prev_year1 = year - 1  # 2025
    prev_year2 = year - 2  # 2024
    prev_year3 = year - 3  # 2023

    # Always 4-column table; details in expandable row (no legacy full-table layout)
    table_header = """<tr>
                            <th>#</th>
                            <th>Player</th>
                            <th>Why They Could Win</th>
                            <th class="center">Win Odds</th>
                        </tr>"""

    html = f'''<div class="cosmos-betting-preview">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        .cosmos-betting-preview {{
            --primary-blue: #0B3D91;
            --accent-green: #0a7a3f;
            --accent-red: #b00020;
            --accent-gold: #b07d00;
            --accent-cyan: #005bbb;
            --bg-white: #ffffff;
            --bg-light: #f8f9fa;
            --text-dark: #1a1a1a;
            --text-muted: #6c757d;
            --border-light: #dee2e6;
            --border-medium: #adb5bd;
        }}

        .cosmos-betting-preview * {{
            box-sizing: border-box;
        }}

        .cosmos-betting-preview {{
            font-family: 'Rajdhani', sans-serif;
            background: var(--bg-white) !important;
            color: var(--text-dark) !important;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
            padding: 0;
            margin: 0;
            width: 100%;
        }}

        .cosmos-betting-preview .container {{
            max-width: 100%;
            width: 100%;
            margin: 0 auto;
            padding: 15px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 20px 15px;
            border-bottom: 1px solid var(--border-light);
            background: var(--bg-white);
            position: relative;
            z-index: 1;
            flex-wrap: wrap;
            gap: 15px;
        }}

        .cosmos-betting-preview .header-left {{
            flex: 1;
        }}

        .cosmos-betting-preview .mission-tag {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
            color: var(--primary-blue);
            letter-spacing: 3px;
            margin-bottom: 8px;
            opacity: 0.8;
        }}

        .cosmos-betting-preview h1 {{
            font-family: 'Orbitron', sans-serif;
            font-size: 28px;
            font-weight: 800;
            color: var(--text-dark);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 10px;
        }}

        .cosmos-betting-preview .subtitle {{
            font-family: 'Rajdhani', sans-serif;
            font-size: 14px;
            color: var(--text-muted);
            font-weight: 500;
            letter-spacing: 1px;
        }}

        .cosmos-betting-preview .logo-container {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }}

        .cosmos-betting-preview .logo-container img {{
            height: 60px;
            width: auto;
            opacity: 1;
        }}

        .cosmos-betting-preview .pdf-button {{
            font-family: 'Orbitron', sans-serif;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            padding: 10px 12px;
            border-radius: 8px;
            border: 1px solid var(--text-dark);
            background: var(--text-dark);
            color: var(--bg-white);
            cursor: pointer;
            line-height: 1;
            user-select: none;
            margin-left: 12px;
        }}

        .cosmos-betting-preview .pdf-button:hover {{
            background: var(--bg-white);
            color: var(--text-dark);
        }}

        .cosmos-betting-preview .pdf-button:focus-visible {{
            outline: 2px solid var(--text-dark);
            outline-offset: 2px;
        }}

        .cosmos-betting-preview .event-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            padding: 20px 15px;
            background: var(--bg-light);
            border: 1px solid var(--border-light);
            margin: 20px 15px;
            border-radius: 8px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .info-block {{
            text-align: center;
            padding: 15px;
            border-right: 1px solid var(--border-light);
        }}

        .cosmos-betting-preview .info-block:last-child {{
            border-right: none;
        }}

        .cosmos-betting-preview .info-label {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 2px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }}

        .cosmos-betting-preview .info-value {{
            font-family: 'Orbitron', sans-serif;
            font-size: 18px;
            color: var(--text-dark);
            font-weight: 600;
        }}

        .cosmos-betting-preview .course-image {{
            width: calc(100% - 30px);
            max-width: 100%;
            margin: 20px 15px;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            overflow: hidden;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .course-image img {{
            width: 100%;
            height: auto;
            display: block;
        }}

        /* AI Insights Section */
        .cosmos-betting-preview .ai-insights {{
            margin: 20px 15px;
            padding: 25px;
            background: linear-gradient(135deg, #f0f7ff 0%, #e8f4f8 100%);
            border: 1px solid var(--primary-blue);
            border-radius: 12px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .ai-insights-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
        }}

        .cosmos-betting-preview .ai-badge {{
            font-family: 'Orbitron', sans-serif;
            font-size: 10px;
            font-weight: 600;
            background: var(--primary-blue);
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            letter-spacing: 1px;
        }}

        .cosmos-betting-preview .ai-insights-title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 16px;
            font-weight: 700;
            color: var(--text-dark);
            margin: 0;
        }}

        .cosmos-betting-preview .executive-summary {{
            font-size: 15px;
            line-height: 1.7;
            color: var(--text-dark);
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid var(--primary-blue);
        }}

        .cosmos-betting-preview .insights-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
        }}

        .cosmos-betting-preview .insight-card {{
            background: white;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            padding: 15px;
            transition: all 0.2s ease;
        }}

        .cosmos-betting-preview .insight-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}

        .cosmos-betting-preview .insight-card.value {{
            border-left: 4px solid var(--accent-green);
        }}

        .cosmos-betting-preview .insight-card.favorite {{
            border-left: 4px solid var(--accent-gold);
        }}

        .cosmos-betting-preview .insight-card.longshot {{
            border-left: 4px solid var(--accent-cyan);
        }}

        .cosmos-betting-preview .insight-card.course_fit {{
            border-left: 4px solid var(--primary-blue);
        }}

        .cosmos-betting-preview .insight-card.avoid {{
            border-left: 4px solid var(--accent-red);
        }}

        .cosmos-betting-preview .insight-card.form {{
            border-left: 4px solid #6f42c1;
        }}

        .cosmos-betting-preview .insight-title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 8px;
        }}

        .cosmos-betting-preview .insight-text {{
            font-size: 13px;
            line-height: 1.5;
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .insight-players {{
            margin-top: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .cosmos-betting-preview .insight-player-tag {{
            font-size: 11px;
            background: var(--bg-light);
            color: var(--text-dark);
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}

        .cosmos-betting-preview .crew-picks {{
            margin: 20px 15px;
            padding: 25px 20px;
            background: var(--bg-light);
            border: 1px solid var(--border-light);
            border-radius: 8px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .crew-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .crew-card {{
            display: flex;
            gap: 15px;
            align-items: flex-start;
            background: var(--bg-white);
            border: 1px solid var(--border-light);
            border-radius: 8px;
            padding: 18px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .cosmos-betting-preview .crew-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .cosmos-betting-preview .crew-card:hover::before {{
            opacity: 1;
        }}

        .cosmos-betting-preview .crew-photo {{
            width: 70px;
            height: 70px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
            border: 2px solid var(--primary-blue);
            transition: all 0.3s ease;
        }}

        .cosmos-betting-preview .crew-card:hover .crew-photo {{
            transform: scale(1.05);
        }}

        .cosmos-betting-preview .crew-name {{
            font-family: 'Orbitron', sans-serif;
            font-size: 16px;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 10px;
            letter-spacing: 1px;
        }}

        .cosmos-betting-preview .crew-picks-list {{
            list-style: none;
            margin: 0;
            padding: 0;
            font-size: 13px;
            color: var(--text-dark);
        }}

        .cosmos-betting-preview .crew-picks-list li {{
            margin-bottom: 4px;
            display: flex;
            gap: 6px;
            align-items: baseline;
            line-height: 1.25;
        }}

        .cosmos-betting-preview .pick-label {{
            color: var(--primary-blue);
            font-weight: 600;
            min-width: 48px;
            flex-shrink: 0;
        }}

        .cosmos-betting-preview .pick-player {{
            color: var(--text-dark);
            margin-right: 4px;
        }}

        .cosmos-betting-preview .pick-odds {{
            color: var(--accent-green);
            font-family: 'Share Tech Mono', monospace;
            font-weight: 700;
        }}

        .cosmos-betting-preview .section-header {{
            margin: 30px 15px 20px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .section-header h2 {{
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: var(--text-dark);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 10px;
        }}

        .cosmos-betting-preview .section-line {{
            height: 2px;
            background: linear-gradient(90deg, var(--primary-blue) 0%, transparent 100%);
        }}

        .cosmos-betting-preview .tab-navigation {{
            display: flex;
            gap: 10px;
            margin: 0 15px 20px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .tab-button {{
            background: var(--bg-white);
            border: 1px solid var(--border-light);
            color: var(--text-dark);
            padding: 12px 24px;
            font-family: 'Rajdhani', sans-serif;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.3s ease;
            border-radius: 6px;
        }}

        .cosmos-betting-preview .tab-button:hover {{
            background: var(--bg-light);
            border-color: var(--primary-blue);
        }}

        .cosmos-betting-preview .tab-button.active {{
            background: var(--primary-blue);
            border-color: var(--primary-blue);
            color: #fff;
        }}

        .cosmos-betting-preview .tab-content {{
            display: none;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .tab-content.active {{
            display: block;
        }}

        .cosmos-betting-preview .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding: 15px;
            margin: 0 15px 20px;
            background: var(--bg-light);
            border: 1px solid var(--border-light);
            border-radius: 8px;
            font-size: 12px;
        }}

        .cosmos-betting-preview .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .cosmos-betting-preview .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }}

        .cosmos-betting-preview .expand-hint {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            background: linear-gradient(135deg, #f0f7ff 0%, #e8f4f8 100%);
            border: 1px solid var(--accent-cyan);
            border-radius: 8px;
            padding: 12px 20px;
            margin: 0 15px 15px;
            color: var(--text-dark);
        }}

        .cosmos-betting-preview .expand-hint-icon {{
            font-size: 20px;
        }}

        .cosmos-betting-preview .expand-hint-text {{
            font-size: 13px;
            font-weight: 500;
        }}

        .cosmos-betting-preview .search-container {{
            margin: 0 15px 15px;
        }}

        .cosmos-betting-preview #player-search {{
            width: 100%;
            max-width: 400px;
            padding: 12px 16px;
            font-size: 14px;
            border: 2px solid var(--border-light);
            border-radius: 8px;
            background: white;
            color: var(--text-dark);
            transition: border-color 0.2s;
        }}

        .cosmos-betting-preview #player-search:focus {{
            outline: none;
            border-color: var(--accent-cyan);
        }}

        .cosmos-betting-preview #player-search::placeholder {{
            color: #999;
        }}

        .cosmos-betting-preview .table-container {{
            overflow-x: auto;
            margin: 0 15px;
            border: 1px solid var(--border-light);
            border-radius: 8px;
        }}

        .cosmos-betting-preview table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .cosmos-betting-preview th {{
            background: var(--bg-light);
            color: var(--text-dark);
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 12px 8px;
            text-align: left;
            border-bottom: 2px solid var(--border-light);
            white-space: nowrap;
        }}

        .cosmos-betting-preview th.center {{
            text-align: center;
        }}

        .cosmos-betting-preview td {{
            padding: 12px 8px;
            border-bottom: 1px solid var(--border-light);
            vertical-align: top;
        }}

        .cosmos-betting-preview tr:hover {{
            background: var(--bg-light);
        }}

        .cosmos-betting-preview tr.global-player {{
            background: rgba(10, 122, 63, 0.05);
        }}

        .cosmos-betting-preview tr.global-player:hover {{
            background: rgba(10, 122, 63, 0.1);
        }}

        .cosmos-betting-preview .player-cell {{
            min-width: 180px;
        }}

        .cosmos-betting-preview .player-name {{
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 4px;
        }}

        .cosmos-betting-preview .player-name a {{
            color: var(--text-dark);
            text-decoration: none;
            transition: color 0.2s;
        }}

        .cosmos-betting-preview .player-name a:hover {{
            color: var(--primary-blue);
        }}

        .cosmos-betting-preview .player-country {{
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }}

        .cosmos-betting-preview .tier-badge {{
            display: inline-block;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-radius: 3px;
        }}

        .cosmos-betting-preview .tier-favorite {{
            background: #ffd700;
            color: #000;
        }}

        .cosmos-betting-preview .tier-contender {{
            background: #c0c0c0;
            color: #000;
        }}

        .cosmos-betting-preview .tier-value {{
            background: #cd7f32;
            color: #fff;
        }}

        .cosmos-betting-preview .tier-longshot {{
            background: var(--text-muted);
            color: #fff;
        }}

        .cosmos-betting-preview .storyline-cell {{
            max-width: 350px;
            min-width: 250px;
        }}

        .cosmos-betting-preview .storyline-text {{
            font-size: 12px;
            line-height: 1.5;
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .recent-form-cell {{
            max-width: 280px;
            min-width: 180px;
        }}

        .cosmos-betting-preview .recent-form-cell .recent-form-text {{
            font-size: 11px;
            line-height: 1.4;
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .result-cell {{
            text-align: center;
            width: 60px;
        }}

        .cosmos-betting-preview .result-value {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
            font-weight: 600;
        }}

        .cosmos-betting-preview .result-win {{
            background: rgba(10, 122, 63, 0.2);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
        }}

        .cosmos-betting-preview .result-top5 {{
            background: rgba(176, 125, 0, 0.15);
            color: var(--accent-gold);
        }}

        .cosmos-betting-preview .result-top10 {{
            background: rgba(0, 91, 187, 0.15);
            color: var(--accent-cyan);
        }}

        .cosmos-betting-preview .result-top25 {{
            background: rgba(0, 119, 182, 0.1);
            color: #0077b6;
        }}

        .cosmos-betting-preview .result-made {{
            background: rgba(108, 117, 125, 0.1);
            color: #6c757d;
        }}

        .cosmos-betting-preview .result-mc {{
            background: rgba(220, 53, 69, 0.2);
            color: #dc3545;
        }}

        .cosmos-betting-preview .result-na {{
            color: #555;
        }}

        .cosmos-betting-preview .odds-cell {{
            text-align: center;
            width: 70px;
        }}

        .cosmos-betting-preview .odds-value {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 13px;
            color: var(--text-dark);
            font-weight: 600;
        }}

        .cosmos-betting-preview .odds-favorite {{
            color: var(--accent-gold);
            font-weight: 700;
        }}

        .cosmos-betting-preview .sg-cell {{
            text-align: center;
            width: 85px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
        }}

        .cosmos-betting-preview .sg-positive {{
            color: var(--accent-green);
        }}

        .cosmos-betting-preview .sg-negative {{
            color: var(--accent-red);
        }}

        .cosmos-betting-preview .sg-neutral {{
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .prob-cell {{
            text-align: center;
            width: 70px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
        }}

        .cosmos-betting-preview .prob-high {{
            color: var(--accent-gold);
            font-weight: 600;
        }}

        .cosmos-betting-preview .prob-medium {{
            color: var(--primary-blue);
        }}

        .cosmos-betting-preview .prob-low {{
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .fit-cell {{
            text-align: center;
            width: 70px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
        }}

        .cosmos-betting-preview .fit-positive {{
            color: var(--accent-green);
        }}

        .cosmos-betting-preview .fit-negative {{
            color: var(--accent-red);
        }}

        .cosmos-betting-preview .dg-section {{
            background: rgba(11, 61, 145, 0.03);
        }}

        /* Expandable Player Detail Panel */
        .cosmos-betting-preview .player-row {{
            cursor: pointer;
            transition: background 0.2s ease;
        }}

        .cosmos-betting-preview .player-row:hover {{
            background: rgba(11, 61, 145, 0.05) !important;
        }}

        .cosmos-betting-preview .player-row.expanded {{
            background: rgba(11, 61, 145, 0.08) !important;
        }}

        .cosmos-betting-preview .player-detail {{
            display: none;
            background: linear-gradient(135deg, #f0f4f8 0%, #e8ecf1 100%);
            border-left: 3px solid var(--primary-blue);
            padding: 20px 25px;
            animation: slideDown 0.3s ease;
        }}

        .cosmos-betting-preview .player-detail.show {{
            display: table-row;
        }}

        .cosmos-betting-preview .player-detail td {{
            padding: 0;
        }}

        .cosmos-betting-preview .detail-content {{
            padding: 20px 25px;
        }}

        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .cosmos-betting-preview .detail-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
        }}

        .cosmos-betting-preview .detail-section {{
            background: var(--bg-white);
            border: 1px solid var(--border-light);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .cosmos-betting-preview .detail-section-title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 11px;
            font-weight: 600;
            color: var(--primary-blue);
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 18px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-light);
        }}

        /* Strokes Gained Bar Visualization */
        .cosmos-betting-preview .sg-bar-container {{
            margin-bottom: 16px;
        }}

        .cosmos-betting-preview .sg-bar-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .cosmos-betting-preview .sg-bar-label {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .sg-bar-icon {{
            width: 18px;
            height: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0.7;
        }}

        .cosmos-betting-preview .sg-bar-value {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 14px;
            font-weight: 600;
        }}

        .cosmos-betting-preview .sg-bar-value.positive {{
            color: var(--accent-green);
        }}

        .cosmos-betting-preview .sg-bar-value.negative {{
            color: var(--accent-red);
        }}

        .cosmos-betting-preview .sg-bar-track {{
            height: 8px;
            background: var(--border-light);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }}

        .cosmos-betting-preview .sg-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
            position: relative;
        }}

        .cosmos-betting-preview .sg-bar-fill.positive {{
            background: linear-gradient(90deg, var(--accent-green) 0%, #34d399 100%);
        }}

        .cosmos-betting-preview .sg-bar-fill.negative {{
            background: linear-gradient(90deg, var(--accent-red) 0%, #f87171 100%);
        }}

        /* Model Predictions Section */
        .cosmos-betting-preview .prediction-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}

        .cosmos-betting-preview .prediction-card {{
            background: var(--bg-light);
            border: 1px solid var(--border-light);
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }}

        .cosmos-betting-preview .prediction-label {{
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }}

        .cosmos-betting-preview .prediction-value {{
            font-family: 'Orbitron', sans-serif;
            font-size: 24px;
            font-weight: 700;
            color: var(--primary-blue);
        }}

        .cosmos-betting-preview .prediction-value.highlight {{
            color: var(--accent-gold);
        }}

        /* Course Fit Section */
        .cosmos-betting-preview .fit-indicator {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 12px 0;
            border-bottom: 1px solid var(--border-light);
        }}

        .cosmos-betting-preview .fit-indicator:last-child {{
            border-bottom: none;
        }}

        .cosmos-betting-preview .fit-label {{
            font-size: 13px;
            color: var(--text-muted);
            min-width: 120px;
        }}

        .cosmos-betting-preview .fit-value {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 15px;
            font-weight: 600;
        }}

        .cosmos-betting-preview .fit-value.good {{
            color: var(--accent-green);
        }}

        .cosmos-betting-preview .fit-value.neutral {{
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .fit-value.bad {{
            color: var(--accent-red);
        }}

        .cosmos-betting-preview .recent-form-text {{
            font-size: 13px;
            line-height: 1.6;
            color: var(--text-muted);
            padding: 10px 0;
        }}

        /* Expand indicator */
        .cosmos-betting-preview .expand-indicator {{
            font-size: 10px;
            color: var(--primary-blue);
            opacity: 0.6;
            margin-left: 8px;
            transition: transform 0.3s ease;
        }}

        .cosmos-betting-preview .player-row.expanded .expand-indicator {{
            transform: rotate(180deg);
        }}

        .cosmos-betting-preview .matchups-section {{
            margin-bottom: 28px;
        }}

        .cosmos-betting-preview .matchup-ai-section {{
            background: var(--bg-light);
            border: 1px solid var(--border-light);
            border-left: 4px solid var(--primary-blue);
            border-radius: 8px;
            padding: 16px 18px;
            margin: 0 0 20px 0;
        }}
        .cosmos-betting-preview .matchup-ai-heading {{
            font-family: 'Orbitron', sans-serif;
            font-size: 15px;
            font-weight: 700;
            margin: 0 0 8px 0;
            color: var(--primary-blue);
        }}
        .cosmos-betting-preview .matchup-ai-summary {{
            font-size: 13px;
            line-height: 1.5;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}
        .cosmos-betting-preview .matchup-ai-picks {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 10px;
        }}
        .cosmos-betting-preview .matchup-ai-card {{
            background: #fff;
            border: 1px solid var(--border-light);
            border-radius: 6px;
            padding: 10px 12px;
        }}
        .cosmos-betting-preview .matchup-ai-card-header {{
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 6px;
        }}
        .cosmos-betting-preview .matchup-ai-pick-name {{
            font-weight: 700;
            color: var(--primary-blue);
        }}
        .cosmos-betting-preview .matchup-ai-confidence {{
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 2px 6px;
            border-radius: 3px;
            margin-left: 6px;
            color: #fff;
        }}
        .cosmos-betting-preview .matchup-ai-strong {{ background: #1a7f37; }}
        .cosmos-betting-preview .matchup-ai-value {{ background: #b8860b; }}
        .cosmos-betting-preview .matchup-ai-lean {{ background: #6c757d; }}
        .cosmos-betting-preview .matchup-ai-analysis {{
            font-size: 12px;
            line-height: 1.45;
            color: var(--text-dark, #333);
        }}

        .cosmos-betting-preview .matchups-heading {{
            font-family: 'Orbitron', sans-serif;
            font-size: 16px;
            font-weight: 700;
            margin: 0 0 10px 0;
            color: var(--primary-blue);
        }}

        .cosmos-betting-preview .matchups-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 16px;
        }}

        .cosmos-betting-preview .matchups-table th {{
            background: var(--bg-light);
            padding: 8px 6px;
            text-align: left;
            border: 1px solid var(--border-light);
            font-weight: 600;
        }}

        .cosmos-betting-preview .matchups-table th.center {{
            text-align: center;
        }}

        .cosmos-betting-preview .matchups-table td {{
            padding: 6px 8px;
            border: 1px solid var(--border-light);
        }}

        .cosmos-betting-preview .matchups-table td.center {{
            text-align: center;
        }}

        .cosmos-betting-preview .matchups-table td.vs {{
            text-align: center;
            font-weight: 700;
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .coming-soon {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }}

        .cosmos-betting-preview .coming-soon h3 {{
            font-family: 'Orbitron', sans-serif;
            color: var(--primary-blue);
            margin-bottom: 15px;
        }}

        .cosmos-betting-preview footer {{
            margin-top: 40px;
            padding: 20px 15px;
            border-top: 1px solid var(--border-light);
            text-align: center;
            position: relative;
            z-index: 1;
            background: var(--bg-light);
        }}

        .cosmos-betting-preview .footer-text {{
            font-family: 'Orbitron', sans-serif;
            font-size: 12px;
            color: var(--primary-blue);
            letter-spacing: 3px;
            margin-bottom: 10px;
        }}

        .cosmos-betting-preview .data-source {{
            font-size: 11px;
            color: var(--text-muted);
            max-width: 600px;
            margin: 0 auto;
        }}

        @media (max-width: 1200px) {{
            .cosmos-betting-preview .sg-cell:not(:first-of-type),
            .cosmos-betting-preview th.dg-section:not(:nth-of-type(10)):not(:nth-of-type(15)):not(:nth-of-type(16)) {{
                display: none;
            }}
        }}

        @media (max-width: 768px) {{
            .cosmos-betting-preview h1 {{
                font-size: 20px;
            }}
            .cosmos-betting-preview .storyline-cell,
            .cosmos-betting-preview .recent-form-cell {{
                display: none;
            }}
            .cosmos-betting-preview .result-cell {{
                width: 45px;
            }}
            .cosmos-betting-preview .result-value {{
                padding: 3px 5px;
                font-size: 11px;
            }}
            .cosmos-betting-preview .sg-cell,
            .cosmos-betting-preview .prob-cell,
            .cosmos-betting-preview .fit-cell,
            .cosmos-betting-preview .dg-section {{
                display: none;
            }}
        }}

        @media print {{
            .cosmos-betting-preview .pdf-button {{
                display: none;
            }}
        }}
    </style>

    <header>
        <div class="header-left">
            <div class="mission-tag">{mission_tag}</div>
            <h1>{tournament_name}</h1>
            <div class="subtitle">{tournament_dates} | {tournament_location}</div>
        </div>
        <div class="logo-container">
            <img src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/COSMOS_Golf-Dec-Logo_001.png" alt="COSMOS Golf">
            <button class="pdf-button" type="button" onclick="downloadPdf()" title="Opens print dialog — choose Save as PDF">Download PDF</button>
        </div>
    </header>

    <div class="container">
        <div class="event-info">
            <div class="info-block">
                <div class="info-label">Total Purse</div>
                <div class="info-value">{purse}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Winner Share</div>
                <div class="info-value">{winner_share}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Course</div>
                <div class="info-value">{yards}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Par</div>
                <div class="info-value">{par}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Field Size</div>
                <div class="info-value">{field_size}</div>
            </div>
            <div class="info-block">
                <div class="info-label">FedExCup Pts</div>
                <div class="info-value">{fedex_points}</div>
            </div>
        </div>

        <div class="course-image">
            <img src="{course_img_src_full}" alt="{tournament_course}">
        </div>

        <div class="weather-forecast" style="background: #f8f9fa; border-left: 4px solid #000; padding: 16px 20px; margin: 24px 0; font-size: 15px; line-height: 1.6;">
            <strong style="font-size: 16px; display: block; margin-bottom: 8px;">⛅ Tournament Weather Forecast</strong>
            {_escape_html(weather_forecast)}
        </div>

        {wind_by_day_html_full}

        <div class="crew-picks">
            <div class="crew-grid">
'''

    # Crew picks — interim builds (picks not finalized) show a placeholder card instead of the grid
    crew_placeholder = load_crew_placeholder()
    if crew_placeholder:
        html += f'''                <div class="crew-card" style="grid-column:1/-1;text-align:center;font-style:italic;color:#555;padding:32px 20px;">🔒 {_escape_html(crew_placeholder)}</div>
'''
    else:
        # Add crew picks (odds from GolfData API via player lookup)
        odds_lookup = _player_odds_lookup(players)
        for crew_member in crew_picks:
            html += f'''                <div class="crew-card">
                    <img class="crew-photo" src="{crew_member['photo_url']}" alt="{crew_member['name']}">
                    <div class="crew-info">
                        <div class="crew-name">{crew_member['name']}</div>
                        <ul class="crew-picks-list">
'''
            for pick in crew_member.get('picks', []):
                odds_display = _crew_pick_odds(pick, odds_lookup)
                html += f'''                            <li>
                                <span class="pick-label">{pick['label']}:</span>
                                <span class="pick-player">{pick['player']}</span>
                                <span class="pick-odds">{odds_display}</span>
                            </li>
'''
            html += '''                        </ul>
                    </div>
                </div>
'''

    html += f'''            </div>
        </div>
'''

    # Add AI Insights section if available
    if insights.get("executive_summary") or insights.get("insights"):
        html += '''
        <div class="ai-insights">
            <div class="ai-insights-header">
                <span class="ai-badge">AI ANALYSIS</span>
                <h3 class="ai-insights-title">Data-Driven Betting Insights</h3>
            </div>
'''
        if insights.get("executive_summary"):
            html += f'''            <div class="executive-summary">{insights["executive_summary"]}</div>
'''

        if insights.get("insights"):
            html += '''            <div class="insights-grid">
'''
            for insight in insights.get("insights", []):
                category = insight.get("category", "value")
                html += f'''                <div class="insight-card {category}">
                    <div class="insight-title">{insight.get("title", "")}</div>
                    <div class="insight-text">{insight.get("insight", "")}</div>
                    <div class="insight-players">
'''
                for player in insight.get("players", []):
                    html += f'''                        <span class="insight-player-tag">{player}</span>
'''
                html += '''                    </div>
                </div>
'''
            html += '''            </div>
'''

        html += '''        </div>
'''

    html += f'''
        <div class="section-header">
            <h2>Complete Betting Board</h2>
            <div class="section-line"></div>
        </div>

        ''' + tab_nav_html + '''

        <div id="tournament-odds" class="tab-content active">
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: var(--accent-green);"></div>
                    <span>WIN / 1st</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: var(--accent-gold);"></div>
                    <span>TOP 5 (2nd-5th)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: var(--accent-cyan);"></div>
                    <span>TOP 10 (6th-10th)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #8ecae6;"></div>
                    <span>TOP 25 (11th-25th)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #6c757d;"></div>
                    <span>MADE CUT (26th+)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: var(--accent-red);"></div>
                    <span>MC = MISSED CUT</span>
                </div>
            </div>

            <div class="expand-hint">
                <span class="expand-hint-icon">👆</span>
                <span class="expand-hint-text">Click any player row for tournament history (2025–2023), Win/Top 5/Top 10 odds, recent form, strokes gained, and model predictions</span>
            </div>

            <div class="search-container">
                <input type="text" id="player-search" placeholder="🔍 Search players by name..." oninput="filterPlayers(this.value)">
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        {table_header}
                    </thead>
                    <tbody>
'''

    # Helper function for SG color class
    def _sg_class(val):
        if val is None:
            return "sg-neutral"
        return "sg-positive" if val >= 0 else "sg-negative"

    # Helper function for probability color class
    def _prob_class(val):
        if val is None:
            return "prob-low"
        if val >= 5:
            return "prob-high"
        if val >= 1:
            return "prob-medium"
        return "prob-low"

    # Helper function for fit color class
    def _fit_class(val_str):
        if val_str == "—":
            return "sg-neutral"
        try:
            val = float(val_str.replace("+", ""))
            return "fit-positive" if val >= 0 else "fit-negative"
        except:
            return "sg-neutral"

    # Helper function to calculate bar width percentage (0-100)
    def _bar_width(val, max_val=2.0):
        if val is None:
            return 0
        # Scale: -2.0 to +2.0 maps to 0% to 100%
        normalized = (val + max_val) / (max_val * 2)
        return max(0, min(100, normalized * 100))

    # Generate player rows
    for player in players:
        global_class = 'global-player ' if player['international'] else ''
        h_prev1 = player.get("history_prev1", "NA")
        h_prev2 = player.get("history_prev2", "NA")
        h_prev3 = player.get("history_prev3", "NA")
        player_id = f"player-{player['rank']}"

        # Get SG class colors
        sg_total_class = _sg_class(player.get("sg_total_raw"))
        win_prob_class = _prob_class(player.get("win_prob_raw"))
        fit_class = _fit_class(player.get("course_fit", "—"))

        # Get raw SG values for bars
        sg_ott_raw = player.get("sg_total_raw", 0) if player.get("has_dg_data") else None
        sg_app_raw = player.get("sg_total_raw", 0) if player.get("has_dg_data") else None
        sg_arg_raw = player.get("sg_total_raw", 0) if player.get("has_dg_data") else None
        sg_putt_raw = player.get("sg_total_raw", 0) if player.get("has_dg_data") else None

        # Parse the raw SG values from formatted strings
        def parse_sg(formatted):
            if formatted == "—":
                return None
            try:
                # Remove rank part if present, e.g., "+1.30 (#1)" -> "+1.30"
                val = formatted.split(" ")[0].replace("+", "")
                return float(val)
            except:
                return None

        sg_ott_val = parse_sg(player.get("sg_ott", "—"))
        sg_app_val = parse_sg(player.get("sg_app", "—"))
        sg_arg_val = parse_sg(player.get("sg_arg", "—"))
        sg_putt_val = parse_sg(player.get("sg_putt", "—"))
        sg_total_val = player.get("sg_total_raw")

        main_row = f'''                        <tr class="player-row {global_class}" onclick="togglePlayerDetail('{player_id}')" data-player="{player_id}">
                            <td>{player['rank']}</td>
                            <td class="player-cell">
                                <div class="player-name">{player['name']}<span class="expand-indicator">▼</span></div>
                                <div class="player-country">{player['country']} - OWGR #{player['owgr']}</div>
                                <span class="tier-badge {player['tier_class']}">{player['tier']}</span>
                            </td>
                            <td class="storyline-cell">
                                <div class="storyline-text">{player.get('_display_storyline', player['storyline'])}</div>
                            </td>
                            <td class="odds-cell"><span class="odds-value {player['odds_class']}">{player['win_odds']}</span></td>
                        </tr>'''
        html += main_row + f'''
                        <tr class="player-detail" id="{player_id}-detail">
                            <td colspan="4">
                                <div class="detail-content">
                                    <div class="detail-grid">
                                        <div class="detail-section">
                                            <div class="detail-section-title">Tournament History &amp; Odds</div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">{prev_year1}</span>
                                                <span class="fit-value"><span class="result-value result-{_result_class(h_prev1)}">{h_prev1}</span></span>
                                            </div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">{prev_year2}</span>
                                                <span class="fit-value"><span class="result-value result-{_result_class(h_prev2)}">{h_prev2}</span></span>
                                            </div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">{prev_year3}</span>
                                                <span class="fit-value"><span class="result-value result-{_result_class(h_prev3)}">{h_prev3}</span></span>
                                            </div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">Win</span>
                                                <span class="fit-value {player['odds_class']}">{player['win_odds']}</span>
                                            </div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">Top 5</span>
                                                <span class="fit-value">{player['top5_odds']}</span>
                                            </div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">Top 10</span>
                                                <span class="fit-value">{player['top10_odds']}</span>
                                            </div>
                                            <div class="detail-section-title" style="margin-top: 16px;">Recent Form</div>
                                            <div class="recent-form-text">{(player.get("recent_form") or "—")}</div>
                                        </div>
                                        <div class="detail-section">
                                            <div class="detail-section-title">Strokes Gained <span style="font-weight:400;font-size:9px;opacity:.7;">(2025-26 PGA TOUR Season)</span></div>
                                            <div class="sg-bar-container">
                                                <div class="sg-bar-header">
                                                    <span class="sg-bar-label"><span class="sg-bar-icon">🎯</span> Off-the-Tee</span>
                                                    <span class="sg-bar-value {'positive' if sg_ott_val and sg_ott_val >= 0 else 'negative'}">{player['sg_ott']}</span>
                                                </div>
                                                <div class="sg-bar-track">
                                                    <div class="sg-bar-fill {'positive' if sg_ott_val and sg_ott_val >= 0 else 'negative'}" style="width: {_bar_width(sg_ott_val)}%;"></div>
                                                </div>
                                            </div>
                                            <div class="sg-bar-container">
                                                <div class="sg-bar-header">
                                                    <span class="sg-bar-label"><span class="sg-bar-icon">🏌️</span> Approach</span>
                                                    <span class="sg-bar-value {'positive' if sg_app_val and sg_app_val >= 0 else 'negative'}">{player['sg_app']}</span>
                                                </div>
                                                <div class="sg-bar-track">
                                                    <div class="sg-bar-fill {'positive' if sg_app_val and sg_app_val >= 0 else 'negative'}" style="width: {_bar_width(sg_app_val)}%;"></div>
                                                </div>
                                            </div>
                                            <div class="sg-bar-container">
                                                <div class="sg-bar-header">
                                                    <span class="sg-bar-label"><span class="sg-bar-icon">⛳</span> Around Green</span>
                                                    <span class="sg-bar-value {'positive' if sg_arg_val and sg_arg_val >= 0 else 'negative'}">{player['sg_arg']}</span>
                                                </div>
                                                <div class="sg-bar-track">
                                                    <div class="sg-bar-fill {'positive' if sg_arg_val and sg_arg_val >= 0 else 'negative'}" style="width: {_bar_width(sg_arg_val)}%;"></div>
                                                </div>
                                            </div>
                                            <div class="sg-bar-container">
                                                <div class="sg-bar-header">
                                                    <span class="sg-bar-label"><span class="sg-bar-icon">🕳️</span> Putting</span>
                                                    <span class="sg-bar-value {'positive' if sg_putt_val and sg_putt_val >= 0 else 'negative'}">{player['sg_putt']}</span>
                                                </div>
                                                <div class="sg-bar-track">
                                                    <div class="sg-bar-fill {'positive' if sg_putt_val and sg_putt_val >= 0 else 'negative'}" style="width: {_bar_width(sg_putt_val)}%;"></div>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="detail-section">
                                            <div class="detail-section-title">Model Predictions</div>
                                            <div class="prediction-grid">
                                                <div class="prediction-card">
                                                    <div class="prediction-label">Win Probability</div>
                                                    <div class="prediction-value {'highlight' if player.get('win_prob_raw') and player.get('win_prob_raw') >= 5 else ''}">{player['win_prob']}</div>
                                                </div>
                                                <div class="prediction-card">
                                                    <div class="prediction-label">Top 10 Probability</div>
                                                    <div class="prediction-value">{player['top10_prob']}</div>
                                                </div>
                                            </div>
                                            <div class="detail-section-title" style="margin-top: 20px;">Course Fit</div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">Skill Fit Adj</span>
                                                <span class="fit-value {('good' if player.get('course_fit', '—') != '—' and float(player.get('course_fit', '0').replace('+', '')) >= 0 else 'bad') if player.get('course_fit', '—') != '—' else 'neutral'}">{player['course_fit']}</span>
                                            </div>
                                            <div class="fit-indicator">
                                                <span class="fit-label">Course History</span>
                                                <span class="fit-value {('good' if player.get('course_history_adj', '—') != '—' and float(player.get('course_history_adj', '0').replace('+', '')) >= 0 else 'bad') if player.get('course_history_adj', '—') != '—' else 'neutral'}">{player.get('course_history_adj', '—')}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
'''

    html += '''                    </tbody>
                </table>
            </div>
        </div>

        ''' + matchups_panel_html + '''

        <footer>
            <div class="footer-text">COSMOS GOLF BETTING PREVIEW</div>
            <div class="data-source">Strokes Gained & Model Predictions powered by Data Golf. Odds from DraftKings. Course history from PGA TOUR. Research your book for latest lines.</div>
        </footer>
    </div>

    <script>
        function switchTab(event, tabName) {
            document.querySelectorAll('.cosmos-betting-preview .tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.cosmos-betting-preview .tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        function togglePlayerDetail(playerId) {
            const row = document.querySelector(`[data-player="${playerId}"]`);
            const detail = document.getElementById(`${playerId}-detail`);

            if (row && detail) {
                const isExpanded = row.classList.contains('expanded');

                // Close all other expanded rows
                document.querySelectorAll('.cosmos-betting-preview .player-row.expanded').forEach(r => {
                    if (r !== row) {
                        r.classList.remove('expanded');
                        const otherDetail = document.getElementById(`${r.dataset.player}-detail`);
                        if (otherDetail) otherDetail.classList.remove('show');
                    }
                });

                // Toggle current row
                if (isExpanded) {
                    row.classList.remove('expanded');
                    detail.classList.remove('show');
                } else {
                    row.classList.add('expanded');
                    detail.classList.add('show');
                }
            }
        }

        function filterPlayers(searchTerm) {
            const term = searchTerm.toLowerCase().trim();
            const rows = document.querySelectorAll('.cosmos-betting-preview table tbody tr');

            rows.forEach(row => {
                if (row.classList.contains('player-row')) {
                    const playerName = row.querySelector('.player-name');
                    if (playerName) {
                        const name = playerName.textContent.toLowerCase();
                        const shouldShow = term === '' || name.includes(term);
                        row.style.display = shouldShow ? '' : 'none';

                        // Also hide/show the detail row
                        const playerId = row.dataset.player;
                        const detailRow = document.getElementById(playerId + '-detail');
                        if (detailRow) {
                            detailRow.style.display = shouldShow ? '' : 'none';
                            if (!shouldShow) {
                                row.classList.remove('expanded');
                                detailRow.classList.remove('show');
                            }
                        }
                    }
                }
            });
        }

        function downloadPdf() {
            const rows = document.querySelectorAll('.cosmos-betting-preview table tbody tr.player-row');
            const players = [];
            const theadTh = document.querySelectorAll('.cosmos-betting-preview table thead th');
            rows.forEach((row) => {
                const cells = row.querySelectorAll('td');
                const isCompact = cells.length === 4 || cells.length === 5;
                if (!isCompact && cells.length < 17) return;
                const hasRecentForm = !isCompact && cells.length >= 18;
                const r1i = isCompact ? -1 : (hasRecentForm ? 4 : 3);
                const r2i = isCompact ? -1 : (hasRecentForm ? 5 : 4);
                const r3i = isCompact ? -1 : (hasRecentForm ? 6 : 5);
                const wini = isCompact ? 3 : (hasRecentForm ? 7 : 6);
                const t5i = isCompact ? -1 : (hasRecentForm ? 8 : 7);
                const t10i = (isCompact && cells.length === 5) ? 4 : (isCompact ? -1 : (hasRecentForm ? 9 : 8));
                const winPcti = isCompact ? -1 : (hasRecentForm ? 15 : 14);
                const fiti = isCompact ? -1 : (hasRecentForm ? 17 : 16);
                const pc = cells[1];
                const nameEl = pc.querySelector('.player-name');
                let name = '';
                if (nameEl) {
                    const clone = nameEl.cloneNode(true);
                    const expand = clone.querySelector('.expand-indicator');
                    if (expand) expand.remove();
                    name = clone.textContent.trim();
                }
                const tierEl = pc.querySelector('.tier-badge');
                const tier = tierEl ? tierEl.textContent.trim() : 'LONGSHOT';
                const countryEl = pc.querySelector('.player-country');
                let cty = '', owgr = '';
                if (countryEl) {
                    const text = countryEl.textContent.trim();
                    const dash = text.indexOf(' - ');
                    if (dash > 0) {
                        cty = text.substring(0, dash).trim();
                        const owgrMatch = text.match(/OWGR\\s*#([^\\s]*)/i);
                        owgr = owgrMatch ? '#' + owgrMatch[1] : '';
                    } else { cty = text; }
                }
                const storylineEl = cells[2].querySelector('.storyline-text');
                let storyline = storylineEl ? storylineEl.textContent.trim() : '';
                const r1 = (r1i >= 0 && cells[r1i]) ? cells[r1i].textContent.trim() : '—';
                const r2 = (r2i >= 0 && cells[r2i]) ? cells[r2i].textContent.trim() : '—';
                const r3 = (r3i >= 0 && cells[r3i]) ? cells[r3i].textContent.trim() : '—';
                const win = cells[wini] ? cells[wini].textContent.trim() : '—';
                const t5 = (t5i >= 0 && cells[t5i]) ? cells[t5i].textContent.trim() : '—';
                const t10 = cells[t10i] ? cells[t10i].textContent.trim() : '—';
                const winPct = (winPcti >= 0 && cells[winPcti]) ? cells[winPcti].textContent.trim() : '—';
                const fit = (fiti >= 0 && cells[fiti]) ? cells[fiti].textContent.trim() : '—';
                players.push({ rk: players.length + 1, nm: name.length > 16 ? name.substring(0, 14) + '..' : name, tier,
                    ts: tier === 'FAVORITE' ? 'FAV' : tier === 'CONTENDER' ? 'CON' : tier === 'VALUE' ? 'VAL' : 'LSH',
                    cty, owgr, r1, r2, r3, win, t5, t10, winPct, fit, storyline });
            });
            const rb = r => {
                if (!r || r === '—' || r === 'NA') return 'background:#f5f5f5;color:#999;';
                if (r === 'WIN' || r === '1st') return 'background:#1e8449;color:#fff;font-weight:700;';
                if (r === 'MC' || r === 'WD') return 'background:#e74c3c;color:#fff;';
                const n = parseInt(String(r).replace('T', ''), 10);
                if (isNaN(n)) return 'background:#f5f5f5;color:#999;';
                if (n <= 3) return 'background:#27ae60;color:#fff;font-weight:600;';
                if (n <= 5) return 'background:#58d68d;color:#000;';
                if (n <= 10) return 'background:#abebc6;color:#000;';
                if (n <= 20) return 'background:#f9e79f;color:#000;';
                if (n <= 30) return 'background:#f5cba7;color:#000;';
                return 'background:#fadbd8;color:#000;';
            };
            const ob = o => {
                if (!o || o === '—') return 'background:#fff;';
                const v = parseInt(String(o).replace(/[+−-]/g, '').replace(/,/g, ''), 10);
                if (isNaN(v)) return 'background:#fff;';
                if (o.startsWith('-') || o.includes('−')) return 'background:#1e8449;color:#fff;font-weight:700;';
                if (v <= 500) return 'background:#27ae60;color:#fff;font-weight:600;';
                if (v <= 1500) return 'background:#58d68d;color:#000;';
                if (v <= 3000) return 'background:#abebc6;color:#000;';
                if (v <= 6000) return 'background:#d5f5e3;color:#000;';
                if (v <= 10000) return 'background:#fcf3cf;color:#000;';
                if (v <= 20000) return 'background:#fef9e7;color:#000;';
                return 'background:#fff;color:#666;';
            };
            const tc = t => { if (t === 'FAV') return 'background:#f4c430;color:#000;'; if (t === 'CON') return 'background:#27ae60;color:#fff;'; if (t === 'VAL') return 'background:#3498db;color:#fff;'; return 'background:#95a5a6;color:#fff;'; };
            const pp = 28, pgs = [];
            for (let i = 0; i < players.length; i += pp) pgs.push(players.slice(i, i + pp));
            const y1h = theadTh.length >= 7 ? theadTh[4].textContent.trim() : ((theadTh.length === 4 || theadTh.length === 5) ? "'25" : (theadTh.length >= 6 ? theadTh[3].textContent.trim() : "'25"));
            const y2h = theadTh.length >= 7 ? theadTh[5].textContent.trim() : ((theadTh.length === 4 || theadTh.length === 5) ? "'24" : (theadTh.length >= 6 ? theadTh[4].textContent.trim() : "'24"));
            const y3h = theadTh.length >= 7 ? theadTh[6].textContent.trim() : ((theadTh.length === 4 || theadTh.length === 5) ? "'23" : (theadTh.length >= 6 ? theadTh[5].textContent.trim() : "'23"));
            const bR = list => list.map(p => '<tr class="main"><td class="c">' + p.rk + '</td><td class="c"><span class="tier" style="' + tc(p.ts) + '">' + p.ts + '</span></td><td class="nm">' + p.nm + '</td><td class="c">' + p.cty + '</td><td class="c rk">' + p.owgr + '</td><td class="c" style="' + rb(p.r1) + '">' + (p.r1 || '—') + '</td><td class="c" style="' + rb(p.r2) + '">' + (p.r2 || '—') + '</td><td class="c" style="' + rb(p.r3) + '">' + (p.r3 || '—') + '</td><td class="c" style="' + ob(p.win) + '">' + p.win + '</td><td class="c" style="' + ob(p.t5) + '">' + p.t5 + '</td><td class="c" style="' + ob(p.t10) + '">' + p.t10 + '</td><td class="c">' + p.winPct + '</td><td class="c">' + p.fit + '</td><td class="storyline-col">' + (p.storyline || '') + '</td></tr>').join('');
            const titleText = document.querySelector('.cosmos-betting-preview h1') ? document.querySelector('.cosmos-betting-preview h1').textContent.trim().toUpperCase() : 'BETTING BOARD';
            const subText = document.querySelector('.cosmos-betting-preview .subtitle') ? document.querySelector('.cosmos-betting-preview .subtitle').textContent.trim() : '';
            const bP = (list, pn, tot) => '<div class="pg"><div class="hdr"><div class="hdr-l"><strong>' + titleText + '</strong> <span class="sub">' + subText + '</span></div><div class="hdr-r"><span class="leg"><b style="background:#1e8449">&nbsp;</b>WIN <b style="background:#58d68d">&nbsp;</b>T5 <b style="background:#abebc6">&nbsp;</b>T10 <b style="background:#f9e79f">&nbsp;</b>T20 <b style="background:#e74c3c">&nbsp;</b>MC</span><span class="pn">' + pn + '/' + tot + '</span></div></div><table><thead><tr><th>#</th><th>T</th><th class="l">PLAYER</th><th>CTY</th><th>RK</th><th>' + y1h + '</th><th>' + y2h + '</th><th>' + y3h + '</th><th>WIN</th><th>T5</th><th>T10</th><th>Win%</th><th>Fit</th><th>Why</th></tr></thead><tbody>' + bR(list) + '</tbody></table><div class="ftr">COSMOS GOLF · Odds &amp; Data as of ' + new Date().toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) + '</div></div>';
            const css = '@page{size:landscape;margin:0.15in}*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial,Helvetica,sans-serif;font-size:7px;background:#fff;color:#222;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}.pg{margin:0 auto 8px;padding:4px;page-break-after:always}.pg:last-child{page-break-after:avoid}.hdr{display:flex;justify-content:space-between;align-items:center;padding:4px 6px;background:#2c3e50;color:#fff;margin-bottom:3px}.hdr-l{font-size:11px}.hdr-l .sub{font-size:7px;font-weight:400;margin-left:8px;opacity:0.8}.hdr-r{display:flex;align-items:center;gap:10px}.leg{font-size:6px;display:flex;align-items:center;gap:4px}.leg b{display:inline-block;width:10px;height:8px;margin-right:1px}.pn{font-size:8px;font-weight:700;background:#f4c430;color:#000;padding:2px 6px;border-radius:2px}table{width:100%;border-collapse:collapse;font-size:6.5px;border:1px solid #bdc3c7}th{background:#ecf0f1;font-size:6px;font-weight:700;padding:2px 3px;text-align:center;border:1px solid #bdc3c7}th.l{text-align:left}td{padding:1px 2px;border:1px solid #ecf0f1;vertical-align:middle}td.c{text-align:center}td.nm{font-weight:600;white-space:nowrap;font-size:6.5px}td.rk{color:#7f8c8d;font-size:5.5px}.tier{display:inline-block;padding:1px 3px;border-radius:2px;font-size:5px;font-weight:700}tr.main td{border-bottom:none}td.storyline-col{white-space:normal;word-wrap:break-word;overflow-wrap:break-word;width:2.5in;max-width:3in;vertical-align:top;font-size:5.5px;color:#555;font-style:italic;padding:2px 4px;line-height:1.3}.ftr{text-align:center;padding:3px;font-size:6px;color:#7f8c8d;margin-top:2px}.pg .matchups-section{margin-bottom:12px}.pg .matchups-heading{font-size:9px;font-weight:700;margin:0 0 4px 0}.pg .matchups-table{font-size:6px}.pg .matchups-table th,.pg .matchups-table td{padding:2px 3px}@media print{.pg{margin:0}}';
            const pageTitle = document.querySelector('.cosmos-betting-preview h1') ? document.querySelector('.cosmos-betting-preview h1').textContent.trim() : 'Cheat Sheet';
            let bodyHtml = pgs.map((p, i) => bP(p, i + 1, pgs.length)).join('');
            const matchupsEl = document.getElementById('daily-matchups');
            if (matchupsEl && matchupsEl.querySelector('.matchups-table')) {
                const matchupsBlocks = matchupsEl.querySelectorAll('.pdf-matchups');
                const matchupsInner = matchupsBlocks.length ? Array.from(matchupsBlocks).map(function(b) { return b.outerHTML; }).join('') : matchupsEl.innerHTML;
                const mupTitle = titleText;
                const mupSub = subText;
                bodyHtml += '<div class="pg"><div class="hdr"><div class="hdr-l"><strong>DAILY MATCHUPS</strong> <span class="sub">' + mupSub + '</span></div><div class="hdr-r"><span class="pn">Matchups</span></div></div>' + matchupsInner + '<div class="ftr">COSMOS GOLF · Odds &amp; Data as of ' + new Date().toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) + '</div></div>';
            }
            const printHtml = '<!DOCTYPE html><html><head><meta charset="UTF-8"><' + 'title>' + pageTitle + '</' + 'title><style>' + css + '</style></head><body>' + bodyHtml + '<script>window.onload=function(){setTimeout(function(){window.print()},300)};<\\/script></body></html>';
            const w = window.open('', '_blank', 'width=1100,height=800');
            w.document.write(printHtml);
            w.document.close();
        }
    </script>
</div>
'''

    return html


def _escape_html(s: str) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_HERO_IMAGES_PATH = PROJECT_ROOT / "data" / "course_hero_images.json"
_hero_images_cache: Optional[dict] = None


def _load_hero_images() -> dict:
    global _hero_images_cache
    if _hero_images_cache is None:
        try:
            _hero_images_cache = json.loads(_HERO_IMAGES_PATH.read_text())
        except Exception:
            _hero_images_cache = {"entries": [], "default": ""}
    return _hero_images_cache


def _match_hero_entry(tournament_name: str) -> Optional[dict]:
    _tn_lower = (tournament_name or "").lower()
    for entry in _load_hero_images().get("entries", []):
        if any(kw in _tn_lower for kw in entry.get("keywords", [])):
            return entry
    return None


def has_hero_image(tournament_name: str) -> bool:
    """True when a tournament-specific hero mapping exists (not the default fallback)."""
    return _match_hero_entry(tournament_name) is not None


def course_image_src(tournament_name: str) -> str:
    """Return the hero course image URL (Shopify CDN) for a tournament.

    Single source of truth shared by the full HTML, v2 HTML, and the email
    newsletter. Mappings live in data/course_hero_images.json (first entry
    whose keyword appears in the name wins — keep 'scottish' before 'genesis');
    add new events with scripts/upload_hero_to_shopify.py --add-mapping.
    """
    entry = _match_hero_entry(tournament_name)
    if entry:
        return entry["url"]
    return _load_hero_images().get("default", "")


def generate_v2_html(
    tournament: dict,
    players: list[dict],
    crew_picks: list[dict],
    year: int,
    insights: dict,
    matchups: Optional[dict],
    all_players: Optional[list] = None,
) -> str:
    """Generate paste-ready v2 HTML: header, WM image, crew, exec summary, compact insight cards, search, tabs, 4-col table with dropdowns, matchups, PDF script. Same light-mode design.

    `players` is the truncated board (top N by odds); `all_players` is the full field.
    The trend bands select from the full field so the site and the email — which has no
    truncation — never disagree about who's climbing.
    """
    tournament_name = tournament.get("name", "PGA Tour Tournament")
    tournament_dates = format_dates(tournament.get("dates", {}))
    tournament_location = tournament.get("location", "TBD")
    tournament_course = tournament.get("course", "TBD")
    mission_tag = f"// BETTING PREVIEW - {tournament_dates.split(',')[0].upper()}"
    prev_year1, prev_year2, prev_year3 = year - 1, year - 2, year - 3
    event_line = f"{tournament_dates} | {tournament_location}"
    course_img_alt = _escape_html(tournament_course)
    course_img_src = course_image_src(tournament_name)

    weather_forecast = _escape_html(load_weather_forecast())
    wind_by_day_html = _render_wind_by_day_html(load_weather_periods())

    matchups_rendered = _render_matchups_html(matchups) if matchups else ""
    # Only surface the Daily Matchups tab when real matchup data exists; otherwise
    # omit the tab + its nav button entirely (no "Coming Soon" placeholder).
    show_matchups = bool(matchups_rendered and "matchups-table" in matchups_rendered)
    matchups_tab_content = ('<div class="pdf-matchups">' + matchups_rendered + "</div>") if show_matchups else ""
    # Full tab-nav only when there's a second (matchups) tab to switch to; otherwise
    # omit the nav bar entirely (the "Complete Betting Board" header labels the section).
    tab_nav_v2 = (
        '<div class="tab-navigation">'
        '<button class="tab-button active" onclick="switchTab(event, \'tournament-odds\')">Tournament Odds</button>'
        '<button class="tab-button" onclick="switchTab(event, \'daily-matchups\')">Daily Matchups</button>'
        '</div>'
    ) if show_matchups else ''
    matchups_panel = ('<div id="daily-matchups" class="tab-content">' + matchups_tab_content + '</div>') if show_matchups else ''

    def _bar_width(val, max_val=2.0):
        if val is None:
            return 0
        normalized = (val + max_val) / (max_val * 2)
        return max(0, min(100, normalized * 100))

    def parse_sg(formatted):
        if not formatted or formatted == "—":
            return None
        try:
            val = str(formatted).split(" ")[0].replace("+", "")
            return float(val)
        except Exception:
            return None

    # Compact insight cards HTML
    insights_html = ""
    if insights.get("executive_summary"):
        insights_html += f'<div class="executive-summary v2-exec">{_escape_html(insights["executive_summary"])}</div>'
    if insights.get("insights"):
        insights_html += '<div class="insights-v2">'
        for inc in insights.get("insights", []):
            cat = inc.get("category", "value")
            if cat not in ("favorite", "value", "longshot", "avoid"):
                cat = "value"
            title = _escape_html(inc.get("title", ""))
            text = _escape_html(inc.get("insight", ""))
            players_list = " ".join(
                f'<span class="insight-player-tag">{_escape_html(p)}</span>'
                for p in inc.get("players", [])
            )
            insights_html += f'<div class="insight-card-v2 {cat}"><div class="insight-title-v2">{title}</div><div class="insight-text-v2">{text}</div><div class="insight-players-v2">{players_list}</div></div>'
        insights_html += "</div>"

    # Trend bands — same picks as the email newsletter (shared selection helpers,
    # run over the full field so truncating the board can't change the picks)
    _pool = all_players or players
    _trending = pick_trending_player(_pool, year)
    _climbers = pick_form_climbers(
        _pool, count=3, exclude=_trending[0]["name"] if _trending[0] else ""
    )
    climbers_html = _render_climbers_v2(_trending, _climbers, tournament_course)

    # Crew picks HTML — interim builds (picks not finalized) show a placeholder instead of the grid
    crew_placeholder = load_crew_placeholder()
    crew_html = ""
    if crew_placeholder:
        crew_html = f'<div class="crew-card" style="grid-column:1/-1;text-align:center;font-style:italic;color:#555;padding:32px 20px;">🔒 {_escape_html(crew_placeholder)}</div>'
    else:
        odds_lookup = _player_odds_lookup(players)
        for crew_member in crew_picks:
            name = _escape_html(crew_member.get("name", ""))
            photo_url = crew_member.get("photo_url", "")
            crew_html += f'<div class="crew-card"><img class="crew-photo" src="{photo_url}" alt="{name}"><div class="crew-info"><div class="crew-name">{name}</div><ul class="crew-picks-list">'
            for pick in crew_member.get("picks", []):
                odds_display = _crew_pick_odds(pick, odds_lookup)
                crew_html += f'<li><span class="pick-label">{_escape_html(pick.get("label", ""))}:</span><span class="pick-player">{_escape_html(pick.get("player", ""))}</span><span class="pick-odds">{_escape_html(odds_display)}</span></li>'
            crew_html += "</ul></div></div>"

    def _fit_value_class(val):
        if not val or val == "—":
            return "neutral"
        try:
            v = float(str(val).replace("+", "").strip())
            return "good" if v >= 0 else "bad"
        except Exception:
            return "neutral"

    # Player rows — full v1-style dropdowns (Tournament History, Recent Form, SG bars, Model Predictions, Course Fit)
    table_rows = []
    for player in players:
        pid = f"player-{player['rank']}"
        h1, h2, h3 = player.get("history_prev1", "NA"), player.get("history_prev2", "NA"), player.get("history_prev3", "NA")
        storyline = player.get("_display_storyline") or player.get("storyline") or ""
        recent = player.get("recent_form") or "—"
        sg_ott_val = parse_sg(player.get("sg_ott", "—"))
        sg_app_val = parse_sg(player.get("sg_app", "—"))
        sg_arg_val = parse_sg(player.get("sg_arg", "—"))
        sg_putt_val = parse_sg(player.get("sg_putt", "—"))
        fit_class = _fit_value_class(player.get("course_fit", "—"))
        history_class = _fit_value_class(player.get("course_history_adj", "—"))
        win_prob_raw = player.get("win_prob_raw")
        win_highlight = "highlight" if (win_prob_raw is not None and win_prob_raw >= 5) else ""

        main_row = f'''<tr class="player-row" data-player="{pid}">
                            <td>{player["rank"]}</td>
                            <td class="player-cell"><div class="player-name">{_escape_html(player["name"])}<span class="expand-indicator">▼</span></div><div class="player-country">{_escape_html(player["country"])} - OWGR #{player["owgr"]}</div><span class="tier-badge {player['tier_class']}">{player['tier']}</span></td>
                            <td class="storyline-cell"><div class="storyline-text">{_escape_html(storyline)}</div></td>
                            <td class="odds-cell"><span class="odds-value {player['odds_class']}">{player['win_odds']}</span></td>
                        </tr>
                        <tr class="player-detail" id="{pid}-detail"><td colspan="4"><div class="detail-content"><div class="detail-grid">
                        <div class="detail-section"><div class="detail-section-title">Tournament History &amp; Odds</div>
                        <div class="fit-indicator"><span class="fit-label">{prev_year1}</span><span class="fit-value"><span class="result-value result-{_result_class(h1)}">{h1}</span></span></div>
                        <div class="fit-indicator"><span class="fit-label">{prev_year2}</span><span class="fit-value"><span class="result-value result-{_result_class(h2)}">{h2}</span></span></div>
                        <div class="fit-indicator"><span class="fit-label">{prev_year3}</span><span class="fit-value"><span class="result-value result-{_result_class(h3)}">{h3}</span></span></div>
                        <div class="fit-indicator"><span class="fit-label">Win</span><span class="fit-value {player['odds_class']}">{player['win_odds']}</span></div>
                        <div class="fit-indicator"><span class="fit-label">Top 5</span><span class="fit-value">{player.get('top5_odds', '—')}</span></div>
                        <div class="fit-indicator"><span class="fit-label">Top 10</span><span class="fit-value">{player.get('top10_odds', '—')}</span></div>
                        <div class="detail-section-title" style="margin-top: 16px;">Recent Form</div>
                        <div class="recent-form-text">{_escape_html(recent)}</div>
                        </div>
                        <div class="detail-section"><div class="detail-section-title">Strokes Gained <span style="font-weight:400;font-size:9px;opacity:.7;">(2025-26 PGA TOUR Season)</span></div>
                        <div class="sg-bar-container"><div class="sg-bar-header"><span class="sg-bar-label"><span class="sg-bar-icon">🎯</span> Off-the-Tee</span><span class="sg-bar-value {'positive' if sg_ott_val is not None and sg_ott_val >= 0 else 'negative'}">{player.get('sg_ott', '—')}</span></div><div class="sg-bar-track"><div class="sg-bar-fill {'positive' if sg_ott_val is not None and sg_ott_val >= 0 else 'negative'}" style="width:{_bar_width(sg_ott_val)}%"></div></div></div>
                        <div class="sg-bar-container"><div class="sg-bar-header"><span class="sg-bar-label"><span class="sg-bar-icon">🏌️</span> Approach</span><span class="sg-bar-value {'positive' if sg_app_val is not None and sg_app_val >= 0 else 'negative'}">{player.get('sg_app', '—')}</span></div><div class="sg-bar-track"><div class="sg-bar-fill {'positive' if sg_app_val is not None and sg_app_val >= 0 else 'negative'}" style="width:{_bar_width(sg_app_val)}%"></div></div></div>
                        <div class="sg-bar-container"><div class="sg-bar-header"><span class="sg-bar-label"><span class="sg-bar-icon">⛳</span> Around Green</span><span class="sg-bar-value {'positive' if sg_arg_val is not None and sg_arg_val >= 0 else 'negative'}">{player.get('sg_arg', '—')}</span></div><div class="sg-bar-track"><div class="sg-bar-fill {'positive' if sg_arg_val is not None and sg_arg_val >= 0 else 'negative'}" style="width:{_bar_width(sg_arg_val)}%"></div></div></div>
                        <div class="sg-bar-container"><div class="sg-bar-header"><span class="sg-bar-label"><span class="sg-bar-icon">🕳️</span> Putting</span><span class="sg-bar-value {'positive' if sg_putt_val is not None and sg_putt_val >= 0 else 'negative'}">{player.get('sg_putt', '—')}</span></div><div class="sg-bar-track"><div class="sg-bar-fill {'positive' if sg_putt_val is not None and sg_putt_val >= 0 else 'negative'}" style="width:{_bar_width(sg_putt_val)}%"></div></div></div>
                        </div>
                        <div class="detail-section"><div class="detail-section-title">Model Predictions</div>
                        <div class="prediction-grid"><div class="prediction-card"><div class="prediction-label">Win Probability</div><div class="prediction-value {win_highlight}">{player.get('win_prob', '—')}</div></div>
                        <div class="prediction-card"><div class="prediction-label">Top 10 Probability</div><div class="prediction-value">{player.get('top10_prob', '—')}</div></div></div>
                        <div class="detail-section-title" style="margin-top: 20px;">Course Fit</div>
                        <div class="fit-indicator"><span class="fit-label">Skill Fit Adj</span><span class="fit-value {fit_class}">{player.get('course_fit', '—')}</span></div>
                        <div class="fit-indicator"><span class="fit-label">Course History</span><span class="fit-value {history_class}">{player.get('course_history_adj', '—')}</span></div>
                        </div></div></div></td></tr>'''
        table_rows.append(main_row)
    table_body = "\n".join(table_rows)

    html = f'''<div class="cosmos-betting-preview">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
    .cosmos-betting-preview{{--primary-blue:#0B3D91;--accent-green:#0a7a3f;--accent-red:#b00020;--accent-gold:#b07d00;--accent-cyan:#005bbb;--bg-white:#fff;--bg-light:#f8f9fa;--text-dark:#1a1a1a;--text-muted:#6c757d;--border-light:#dee2e6;box-sizing:border-box;font-family:'Rajdhani',sans-serif;background:var(--bg-white)!important;color:var(--text-dark)!important;min-height:100vh;overflow-x:hidden;margin:0;padding:0;width:100vw;position:relative;left:50%;right:50%;margin-left:-50vw;margin-right:-50vw;}}
    @media(max-width:768px){{.cosmos-betting-preview{{width:100%;position:static;left:auto;right:auto;margin-left:0;margin-right:0;}}}}
    .cosmos-betting-preview *{{box-sizing:border-box;}}
    .cosmos-betting-preview .container{{max-width:100%;width:100%;margin:0 auto;padding:15px;}}
    .cosmos-betting-preview header{{display:flex;justify-content:space-between;align-items:flex-start;padding:20px 15px;border-bottom:1px solid var(--border-light);background:var(--bg-white);flex-wrap:wrap;gap:15px;}}
    .cosmos-betting-preview .header-left{{flex:1;}}
    .cosmos-betting-preview .mission-tag{{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--primary-blue);letter-spacing:3px;margin-bottom:8px;opacity:.8;}}
    .cosmos-betting-preview h1{{font-family:'Orbitron',sans-serif;font-size:28px;font-weight:800;color:var(--text-dark);text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;}}
    .cosmos-betting-preview .subtitle{{font-family:'Rajdhani',sans-serif;font-size:14px;color:var(--text-muted);font-weight:500;}}
    .cosmos-betting-preview .logo-container{{display:flex;align-items:center;justify-content:flex-end;}}
    .cosmos-betting-preview .logo-container img{{height:60px;width:auto;}}
    .cosmos-betting-preview .pdf-button{{font-family:'Orbitron',sans-serif;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:10px 12px;border-radius:8px;border:1px solid var(--text-dark);background:var(--text-dark);color:var(--bg-white);cursor:pointer;margin-left:12px;}}
    .cosmos-betting-preview .pdf-button:hover{{background:var(--bg-white);color:var(--text-dark);}}
    .cosmos-betting-preview .course-image{{width:100%;margin:0 0 20px 0;border-radius:0;overflow:hidden;border-bottom:1px solid var(--border-light);}}
    .cosmos-betting-preview .course-image img{{width:100%;height:auto;display:block;}}
    .cosmos-betting-preview .crew-picks{{margin:16px 0 24px;}}
    .cosmos-betting-preview .crew-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;}}
    .cosmos-betting-preview .crew-card{{display:flex;align-items:flex-start;gap:14px;padding:16px;border:1px solid var(--border-light);border-radius:8px;background:var(--bg-white);}}
    .cosmos-betting-preview .crew-photo{{width:60px;height:60px;border-radius:50%;object-fit:cover;flex-shrink:0;}}
    .cosmos-betting-preview .crew-name{{font-family:'Orbitron',sans-serif;font-weight:700;font-size:15px;margin-bottom:8px;}}
    .cosmos-betting-preview .crew-picks-list{{list-style:none;padding:0;margin:0;font-size:13px;line-height:1.25;}}
    .cosmos-betting-preview .crew-picks-list li{{display:flex;gap:6px;margin-bottom:4px;align-items:baseline;flex-wrap:wrap;}}
    .cosmos-betting-preview .crew-picks-list .pick-label{{color:var(--primary-blue);font-weight:600;min-width:48px;flex-shrink:0;}}
    .cosmos-betting-preview .crew-picks-list .pick-player{{margin-right:4px;}}
    .cosmos-betting-preview .crew-picks-list .pick-odds{{color:var(--accent-green);font-family:'Share Tech Mono',monospace;font-weight:700;}}
    .cosmos-betting-preview .executive-summary.v2-exec{{margin:20px 15px;padding:16px;background:linear-gradient(135deg,#f0f7ff 0%,#e8f4f8 100%);border:1px solid var(--primary-blue);border-radius:12px;font-size:14px;line-height:1.45;}}
    .cosmos-betting-preview .insights-v2{{margin:10px 15px 20px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;}}
    .cosmos-betting-preview .insight-card-v2{{border:1px solid var(--border-light);border-radius:8px;padding:10px 12px;background:var(--bg-white);font-size:12px;}}
    .cosmos-betting-preview .insight-card-v2.favorite{{border-left:4px solid var(--accent-green);}}
    .cosmos-betting-preview .insight-card-v2.value{{border-left:4px solid var(--accent-cyan);}}
    .cosmos-betting-preview .insight-card-v2.longshot{{border-left:4px solid var(--accent-gold);}}
    .cosmos-betting-preview .insight-card-v2.avoid{{border-left:4px solid var(--accent-red);}}
    .cosmos-betting-preview .insight-title-v2{{font-weight:700;color:var(--primary-blue);margin-bottom:6px;font-size:11px;text-transform:uppercase;}}
    .cosmos-betting-preview .insight-text-v2{{line-height:1.35;margin-bottom:6px;}}
    .cosmos-betting-preview .insight-players-v2{{font-size:11px;color:var(--text-muted);}}
    /* Trend bands: venue climber (gold) + recent-form climbers (green) */
    .cosmos-betting-preview .climbers-v2{{display:flex;flex-direction:column;gap:10px;margin:16px 0 4px;}}
    .cosmos-betting-preview .clmb-band{{background:var(--bg-light,#f8f9fa);border:1px solid var(--border-light);border-radius:8px;padding:10px 14px;}}
    .cosmos-betting-preview .clmb-band.clmb-venue{{border-left:4px solid var(--accent-gold);}}
    .cosmos-betting-preview .clmb-band.clmb-form{{border-left:4px solid var(--accent-green);}}
    .cosmos-betting-preview .clmb-kicker{{font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;margin-bottom:8px;}}
    .cosmos-betting-preview .clmb-venue .clmb-kicker{{color:var(--accent-gold);}}
    .cosmos-betting-preview .clmb-form .clmb-kicker{{color:var(--accent-green);}}
    .cosmos-betting-preview .clmb-row{{display:flex;align-items:center;gap:12px;padding:6px 0;border-top:1px solid var(--border-light);}}
    .cosmos-betting-preview .clmb-row:first-of-type{{border-top:none;}}
    .cosmos-betting-preview .clmb-who{{flex:0 0 150px;min-width:0;font-size:13px;font-weight:700;color:var(--primary-blue);}}
    .cosmos-betting-preview .clmb-path{{flex:1 1 auto;min-width:0;font-size:12px;color:var(--text-muted);line-height:1.5;}}
    .cosmos-betting-preview .clmb-leg{{white-space:nowrap;}}
    .cosmos-betting-preview .clmb-now{{color:var(--accent-green);font-weight:700;}}
    .cosmos-betting-preview .clmb-arrow{{color:#c9ced3;}}
    .cosmos-betting-preview .clmb-gain{{flex:0 0 auto;text-align:right;font-size:15px;font-weight:700;color:var(--accent-green);line-height:1.1;white-space:nowrap;}}
    .cosmos-betting-preview .clmb-gain span{{display:block;font-size:9px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:var(--text-muted);}}
    .cosmos-betting-preview .insight-players-v2 .insight-player-tag{{display:inline-block;margin-right:6px;margin-top:2px;padding:2px 6px;background:var(--bg-light);border-radius:4px;}}
    .cosmos-betting-preview .section-header{{margin:24px 0 12px;}}
    .cosmos-betting-preview .section-header h2{{font-family:'Orbitron',sans-serif;font-size:18px;font-weight:800;letter-spacing:1px;margin:0 0 8px 0;}}
    .cosmos-betting-preview .section-line{{height:2px;background:var(--text-dark);width:60px;}}
    .cosmos-betting-preview .tab-navigation{{display:flex;gap:8px;margin-bottom:12px;}}
    .cosmos-betting-preview .tab-button{{font-family:'Orbitron',sans-serif;font-size:13px;font-weight:600;padding:10px 18px;border:1px solid var(--border-light);border-radius:6px;background:var(--bg-white);cursor:pointer;}}
    .cosmos-betting-preview .tab-button.active{{background:var(--text-dark);color:var(--bg-white);border-color:var(--text-dark);}}
    .cosmos-betting-preview .tab-content{{display:none;}}
    .cosmos-betting-preview .tab-content.active{{display:block;}}
    .cosmos-betting-preview .search-container{{margin-bottom:12px;}}
    .cosmos-betting-preview .search-container input{{width:100%;max-width:400px;padding:10px 12px;border:1px solid var(--border-light);border-radius:6px;font-size:14px;font-family:'Rajdhani',sans-serif;}}
    .cosmos-betting-preview .expand-hint{{font-size:12px;color:var(--text-muted);margin-bottom:10px;display:flex;align-items:center;gap:8px;font-family:'Rajdhani',sans-serif;}}
    .cosmos-betting-preview .table-container{{overflow-x:auto;margin:0 15px 20px;border:1px solid var(--border-light);border-radius:8px;}}
    .cosmos-betting-preview table{{width:100%;border-collapse:collapse;font-size:13px;font-family:'Rajdhani',sans-serif;}}
    .cosmos-betting-preview th{{background:var(--bg-light);color:var(--text-dark);font-family:'Share Tech Mono',monospace;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;padding:12px 8px;text-align:left;border-bottom:2px solid var(--border-light);}}
    .cosmos-betting-preview th.center{{text-align:center;}}
    .cosmos-betting-preview td{{padding:12px 8px;border-bottom:1px solid var(--border-light);vertical-align:top;}}
    .cosmos-betting-preview .player-row{{cursor:pointer;transition:background 0.2s ease;}}
    .cosmos-betting-preview .player-row:hover{{background:rgba(11,61,145,0.05)!important;}}
    .cosmos-betting-preview .player-row.expanded{{background:rgba(11,61,145,0.08)!important;}}
    .cosmos-betting-preview .player-cell{{min-width:180px;}}
    .cosmos-betting-preview .player-name{{font-weight:600;color:var(--text-dark);margin-bottom:4px;}}
    .cosmos-betting-preview .player-country{{font-size:11px;color:var(--text-muted);margin-bottom:6px;}}
    .cosmos-betting-preview .storyline-cell{{min-width:250px;}}
    .cosmos-betting-preview .storyline-text{{font-size:12px;line-height:1.5;color:var(--text-muted);}}
    .cosmos-betting-preview .odds-cell{{text-align:center;width:70px;font-family:'Share Tech Mono',monospace;}}
    .cosmos-betting-preview .odds-source{{display:block;font-size:9px;font-weight:400;opacity:0.7;margin-top:2px;}}
    .cosmos-betting-preview .player-detail{{display:none;background:linear-gradient(135deg,#f0f4f8 0%,#e8ecf1 100%);border-left:3px solid var(--primary-blue);}}
    .cosmos-betting-preview .player-detail.show{{display:table-row;}}
    .cosmos-betting-preview .player-detail td{{padding:20px 25px;border-top:none;border-bottom:1px solid var(--border-light);}}
    .cosmos-betting-preview .detail-content{{padding:0;}}
    .cosmos-betting-preview .detail-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:25px;}}
    .cosmos-betting-preview .detail-section{{background:var(--bg-white);border:1px solid var(--border-light);border-radius:8px;padding:20px;font-size:11px;box-shadow:0 2px 4px rgba(0,0,0,0.05);}}
    .cosmos-betting-preview .detail-section-title{{font-family:'Orbitron',sans-serif;font-weight:600;color:var(--primary-blue);margin-bottom:12px;font-size:10px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border-light);padding-bottom:6px;}}
    .cosmos-betting-preview .fit-indicator{{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border-light);}}
    .cosmos-betting-preview .fit-indicator:last-child{{border-bottom:none;}}
    .cosmos-betting-preview .fit-label{{font-size:12px;color:var(--text-muted);min-width:100px;}}
    .cosmos-betting-preview .fit-value{{font-family:'Share Tech Mono',monospace;font-size:13px;font-weight:600;}}
    .cosmos-betting-preview .fit-value.good{{color:var(--accent-green);}}
    .cosmos-betting-preview .fit-value.neutral{{color:var(--text-muted);}}
    .cosmos-betting-preview .fit-value.bad{{color:var(--accent-red);}}
    .cosmos-betting-preview .prediction-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;}}
    .cosmos-betting-preview .prediction-card{{background:var(--bg-light);border:1px solid var(--border-light);border-radius:6px;padding:12px;text-align:center;}}
    .cosmos-betting-preview .prediction-label{{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;}}
    .cosmos-betting-preview .prediction-value{{font-family:'Orbitron',sans-serif;font-size:20px;font-weight:700;color:var(--primary-blue);}}
    .cosmos-betting-preview .prediction-value.highlight{{color:var(--accent-gold);}}
    .cosmos-betting-preview .result-value{{padding:2px 4px;font-size:11px;}}
    .cosmos-betting-preview .result-win{{background:#1e8449;color:#fff;}}
    .cosmos-betting-preview .result-top5{{background:#58d68d;}}
    .cosmos-betting-preview .result-top10{{background:#abebc6;}}
    .cosmos-betting-preview .result-top25{{background:#f9e79f;}}
    .cosmos-betting-preview .result-made,.cosmos-betting-preview .result-na{{background:#f5f5f5;color:#666;}}
    .cosmos-betting-preview .result-mc{{background:#e74c3c;color:#fff;}}
    .cosmos-betting-preview .recent-form-text{{font-size:12px;line-height:1.5;color:var(--text-muted);}}
    .cosmos-betting-preview .sg-bar-container{{margin-bottom:14px;}}
    .cosmos-betting-preview .sg-bar-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}}
    .cosmos-betting-preview .sg-bar-label{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);}}
    .cosmos-betting-preview .sg-bar-icon{{opacity:0.8;}}
    .cosmos-betting-preview .sg-bar-value{{font-family:'Share Tech Mono',monospace;font-size:13px;font-weight:600;}}
    .cosmos-betting-preview .sg-bar-value.positive{{color:var(--accent-green);}}
    .cosmos-betting-preview .sg-bar-value.negative{{color:var(--accent-red);}}
    .cosmos-betting-preview .sg-bar-track{{height:8px;background:var(--border-light);border-radius:4px;overflow:hidden;}}
    .cosmos-betting-preview .sg-bar-fill{{height:100%;border-radius:4px;}}
    .cosmos-betting-preview .sg-bar-fill.positive{{background:var(--accent-green);}}
    .cosmos-betting-preview .sg-bar-fill.negative{{background:var(--accent-red);}}
    .cosmos-betting-preview .tier-badge{{font-size:10px;padding:2px 6px;border-radius:4px;margin-left:4px;}}
    .cosmos-betting-preview .tier-favorite{{background:#f4c430;color:#000;}}
    .cosmos-betting-preview .tier-contender{{background:#27ae60;color:#fff;}}
    .cosmos-betting-preview .tier-value{{background:#3498db;color:#fff;}}
    .cosmos-betting-preview .tier-longshot{{background:#95a5a6;color:#fff;}}
    .cosmos-betting-preview .odds-favorite{{font-weight:700;color:var(--accent-green);}}
    .cosmos-betting-preview footer{{margin-top:24px;padding:16px;border-top:1px solid var(--border-light);font-size:12px;color:var(--text-muted);text-align:center;}}
    @media print{{.cosmos-betting-preview .pdf-button{{display:none;}}}}
    @media(max-width:768px){{
    .cosmos-betting-preview .container{{padding:10px;}}
    .cosmos-betting-preview .table-container{{margin:0 0 16px;}}
    .cosmos-betting-preview table{{font-size:12px;}}
    .cosmos-betting-preview th{{padding:8px 5px;font-size:10px;letter-spacing:.5px;}}
    .cosmos-betting-preview td{{padding:8px 5px;}}
    .cosmos-betting-preview .player-cell{{min-width:0;}}
    .cosmos-betting-preview .storyline-cell{{min-width:0;}}
    .cosmos-betting-preview .odds-cell{{width:56px;}}
    .cosmos-betting-preview .player-name{{font-size:13px;margin-bottom:2px;}}
    .cosmos-betting-preview .player-country{{font-size:10px;margin-bottom:4px;}}
    .cosmos-betting-preview .tier-badge{{font-size:9px;padding:1px 5px;}}
    .cosmos-betting-preview .storyline-text{{font-size:11px;line-height:1.4;display:-webkit-box;-webkit-line-clamp:3;line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}}
    .cosmos-betting-preview .player-row.expanded .storyline-text{{-webkit-line-clamp:unset;line-clamp:unset;display:block;overflow:visible;}}
    .cosmos-betting-preview .player-detail td{{padding:12px;}}
    .cosmos-betting-preview .detail-grid{{grid-template-columns:1fr;gap:14px;}}
    .cosmos-betting-preview .detail-section{{padding:12px;}}
    .cosmos-betting-preview .sg-bar-container{{margin-bottom:8px;}}
    .cosmos-betting-preview .prediction-value{{font-size:16px;}}
    .cosmos-betting-preview .fit-label{{min-width:80px;font-size:11px;}}
    .cosmos-betting-preview .fit-indicator{{padding:7px 0;gap:8px;}}
    .cosmos-betting-preview h1{{font-size:20px;}}
    /* Trend bands stack: name + gain on line 1, the three legs wrap below.
       `order` puts the gain chip before the full-width path so it shares line 1. */
    .cosmos-betting-preview .clmb-band{{padding:10px 12px;}}
    .cosmos-betting-preview .clmb-row{{flex-wrap:wrap;gap:4px 10px;}}
    .cosmos-betting-preview .clmb-who{{order:1;flex:1 1 auto;font-size:13px;}}
    .cosmos-betting-preview .clmb-gain{{order:2;font-size:14px;}}
    .cosmos-betting-preview .clmb-path{{order:3;flex:1 1 100%;font-size:11px;}}
    }}
    @media(max-width:480px){{
    .cosmos-betting-preview .storyline-text{{-webkit-line-clamp:2;line-clamp:2;}}
    .cosmos-betting-preview .player-row.expanded .storyline-text{{-webkit-line-clamp:unset;line-clamp:unset;}}
    .cosmos-betting-preview .prediction-grid{{grid-template-columns:1fr;gap:8px;}}
    .cosmos-betting-preview .prediction-value{{font-size:18px;}}
    .cosmos-betting-preview th{{padding:7px 4px;}}
    .cosmos-betting-preview td{{padding:7px 4px;}}
    .cosmos-betting-preview .odds-cell{{width:50px;font-size:12px;}}
    .cosmos-betting-preview .clmb-kicker{{font-size:9px;letter-spacing:1px;}}
    .cosmos-betting-preview .clmb-path{{font-size:10px;}}
    .cosmos-betting-preview .clmb-gain{{font-size:13px;}}
    }}
    </style>
    <header>
        <div class="header-left">
            <div class="mission-tag">{mission_tag}</div>
            <h1>{_escape_html(tournament_name)}</h1>
            <div class="subtitle">{_escape_html(event_line)}</div>
        </div>
        <div class="logo-container">
            <img src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/COSMOS_Golf-Dec-Logo_001.png" alt="COSMOS Golf">
            <button class="pdf-button" type="button" onclick="downloadPdf()" title="Opens print dialog — choose Save as PDF">Download PDF</button>
        </div>
    </header>
    <div class="course-image"><img src="{course_img_src}" alt="{course_img_alt}"></div>
    <div class="weather-forecast" style="background:#f8f9fa;border-left:4px solid #000;padding:16px 20px;margin:24px 0;font-size:15px;line-height:1.6;">
        <strong style="font-size:16px;display:block;margin-bottom:8px;">⛅ Tournament Weather Forecast</strong>
        {weather_forecast}
    </div>
    {wind_by_day_html}
    <div class="container">
        <div class="crew-picks"><div class="crew-grid">{crew_html}</div></div>
        <div class="ai-insights-v2">{insights_html}</div>
        {climbers_html}
        <div class="section-header"><h2>Complete Betting Board</h2><div class="section-line"></div></div>
        {tab_nav_v2}
        <div id="tournament-odds" class="tab-content active">
            <div class="expand-hint"><span>👆</span> Click any player row for history, odds, recent form, strokes gained.</div>
            <div class="search-container"><input type="text" id="player-search" placeholder="🔍 Search players..." oninput="filterPlayers(this.value)"></div>
            <div class="table-container"><table><thead><tr><th>#</th><th>Player</th><th>Why They Could Win</th><th class="center">Win Odds <span class="odds-source">GolfData API</span></th></tr></thead><tbody>
{table_body}
                    </tbody></table></div>
        </div>
        {matchups_panel}
        <footer><div class="footer-text">COSMOS GOLF BETTING PREVIEW</div><div class="data-source">Strokes Gained &amp; Model from Data Golf. Odds from GolfData API.</div></footer>
    </div>
    <script>
        function switchTab(event, tabName) {{
            document.querySelectorAll('.cosmos-betting-preview .tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.cosmos-betting-preview .tab-button').forEach(btn => btn.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}
        function togglePlayerDetail(playerId) {{
            const row = document.querySelector('[data-player="' + playerId + '"]');
            const detail = document.getElementById(playerId + '-detail');
            if (!row || !detail) return;
            const isExpanded = row.classList.contains('expanded');
            document.querySelectorAll('.cosmos-betting-preview .player-row.expanded').forEach(r => {{
                if (r !== row) {{ r.classList.remove('expanded'); const d = document.getElementById(r.dataset.player + '-detail'); if (d) d.classList.remove('show'); }}
            }});
            if (isExpanded) {{ row.classList.remove('expanded'); detail.classList.remove('show'); }}
            else {{ row.classList.add('expanded'); detail.classList.add('show'); }}
        }}
        (function() {{
            var tbody = document.querySelector('.cosmos-betting-preview .table-container tbody');
            if (tbody) tbody.addEventListener('click', function(e) {{
                var row = e.target.closest('tr.player-row');
                if (row && row.dataset.player) togglePlayerDetail(row.dataset.player);
            }});
        }})();
        function filterPlayers(searchTerm) {{
            const term = searchTerm.toLowerCase().trim();
            document.querySelectorAll('.cosmos-betting-preview table tbody tr').forEach(row => {{
                if (row.classList.contains('player-row')) {{
                    const nameEl = row.querySelector('.player-name');
                    const name = nameEl ? nameEl.textContent.toLowerCase() : '';
                    const show = term === '' || name.includes(term);
                    row.style.display = show ? '' : 'none';
                    const detail = document.getElementById(row.dataset.player + '-detail');
                    if (detail) {{ detail.style.display = show ? '' : 'none'; if (!show) {{ row.classList.remove('expanded'); detail.classList.remove('show'); }} }}
                }}
            }});
        }}
        function downloadPdf() {{
            var rows = document.querySelectorAll('#tournament-odds table tbody tr.player-row');
            var players = [];
            var y1h = "'25", y2h = "'24", y3h = "'23";
            rows.forEach(function(row) {{
                if (row.style.display === 'none') return;
                var cells = row.querySelectorAll('td');
                if (cells.length !== 4) return;
                var rank = cells[0].textContent.trim();
                var pc = cells[1];
                var nameEl = pc.querySelector('.player-name');
                var name = '';
                if (nameEl) {{
                    var clone = nameEl.cloneNode(true);
                    var ind = clone.querySelector('.expand-indicator');
                    if (ind) ind.remove();
                    name = clone.textContent.trim();
                }}
                if (name.length > 16) name = name.substring(0, 14) + '..';
                var tierEl = pc.querySelector('.tier-badge');
                var tier = tierEl ? tierEl.textContent.trim() : 'LONGSHOT';
                var ts = (tier === 'FAVORITE') ? 'FAV' : (tier === 'CONTENDER') ? 'CON' : (tier === 'VALUE') ? 'VAL' : 'LSH';
                var countryEl = pc.querySelector('.player-country');
                var cty = '', owgr = '';
                if (countryEl) {{
                    var t = countryEl.textContent.trim();
                    var dash = t.indexOf(' - ');
                    if (dash > 0) {{
                        cty = t.substring(0, dash).trim();
                        var m = t.match(/OWGR\\s*#([^\\s]*)/i);
                        owgr = m ? '#' + m[1] : '';
                    }} else {{ cty = t; }}
                }}
                var storylineEl = cells[2].querySelector('.storyline-text');
                var storyline = storylineEl ? storylineEl.textContent.trim() : '';
                var win = cells[3].textContent.trim();
                var r1 = '—', r2 = '—', r3 = '—', t5 = '—', t10 = '—', winPct = '—', fit = '—';
                var detail = row.nextElementSibling;
                if (detail && detail.classList.contains('player-detail')) {{
                    var indicators = detail.querySelectorAll('.fit-indicator');
                    if (indicators.length >= 6) {{
                        r1 = indicators[0].querySelector('.fit-value') ? indicators[0].querySelector('.fit-value').textContent.trim() : '—';
                        r2 = indicators[1].querySelector('.fit-value') ? indicators[1].querySelector('.fit-value').textContent.trim() : '—';
                        r3 = indicators[2].querySelector('.fit-value') ? indicators[2].querySelector('.fit-value').textContent.trim() : '—';
                        if (indicators[3]) win = indicators[3].querySelector('.fit-value') ? indicators[3].querySelector('.fit-value').textContent.trim() : win;
                        t5 = indicators[4].querySelector('.fit-value') ? indicators[4].querySelector('.fit-value').textContent.trim() : '—';
                        t10 = indicators[5].querySelector('.fit-value') ? indicators[5].querySelector('.fit-value').textContent.trim() : '—';
                        if (indicators.length >= 8) fit = indicators[6].querySelector('.fit-value') ? indicators[6].querySelector('.fit-value').textContent.trim() : '—';
                    }}
                    var preds = detail.querySelectorAll('.prediction-value');
                    if (preds.length >= 1) winPct = preds[0].textContent.trim();
                }}
                players.push({{
                    rk: rank, nm: name, ts: ts, cty: cty, owgr: owgr,
                    r1: r1, r2: r2, r3: r3, win: win, t5: t5, t10: t10, winPct: winPct, fit: fit, storyline: storyline
                }});
            }});
            var rb = function(r) {{
                if (!r || r === '—' || r === 'NA') return 'background:#f5f5f5;color:#999;';
                if (r === 'WIN' || r === '1st') return 'background:#1e8449;color:#fff;font-weight:700;';
                if (r === 'MC' || r === 'WD') return 'background:#e74c3c;color:#fff;';
                var n = parseInt(String(r).replace('T', ''), 10);
                if (isNaN(n)) return 'background:#f5f5f5;color:#999;';
                if (n <= 3) return 'background:#27ae60;color:#fff;font-weight:600;';
                if (n <= 5) return 'background:#58d68d;color:#000;';
                if (n <= 10) return 'background:#abebc6;color:#000;';
                if (n <= 20) return 'background:#f9e79f;color:#000;';
                if (n <= 30) return 'background:#f5cba7;color:#000;';
                return 'background:#fadbd8;color:#000;';
            }};
            var ob = function(o) {{
                if (!o || o === '—') return 'background:#fff;';
                var v = parseInt(String(o).replace(/[+−-]/g, '').replace(/,/g, ''), 10);
                if (isNaN(v)) return 'background:#fff;';
                if (o.startsWith('-') || o.indexOf('−') >= 0) return 'background:#1e8449;color:#fff;font-weight:700;';
                if (v <= 500) return 'background:#27ae60;color:#fff;font-weight:600;';
                if (v <= 1500) return 'background:#58d68d;color:#000;';
                if (v <= 3000) return 'background:#abebc6;color:#000;';
                if (v <= 6000) return 'background:#d5f5e3;color:#000;';
                if (v <= 10000) return 'background:#fcf3cf;color:#000;';
                if (v <= 20000) return 'background:#fef9e7;color:#000;';
                return 'background:#fff;color:#666;';
            }};
            var tc = function(t) {{
                if (t === 'FAV') return 'background:#f4c430;color:#000;';
                if (t === 'CON') return 'background:#27ae60;color:#fff;';
                if (t === 'VAL') return 'background:#3498db;color:#fff;';
                return 'background:#95a5a6;color:#fff;';
            }};
            var pp = 28, pgs = [];
            for (var i = 0; i < players.length; i += pp) pgs.push(players.slice(i, i + pp));
            var bR = function(list) {{
                return list.map(function(p) {{
                    return '<tr class="main"><td class="c">' + p.rk + '</td><td class="c"><span class="tier" style="' + tc(p.ts) + '">' + p.ts + '</span></td><td class="nm">' + p.nm + '</td><td class="c">' + p.cty + '</td><td class="c rk">' + p.owgr + '</td><td class="c" style="' + rb(p.r1) + '">' + (p.r1 || '—') + '</td><td class="c" style="' + rb(p.r2) + '">' + (p.r2 || '—') + '</td><td class="c" style="' + rb(p.r3) + '">' + (p.r3 || '—') + '</td><td class="c" style="' + ob(p.win) + '">' + p.win + '</td><td class="c" style="' + ob(p.t5) + '">' + p.t5 + '</td><td class="c" style="' + ob(p.t10) + '">' + p.t10 + '</td><td class="c">' + p.winPct + '</td><td class="c">' + p.fit + '</td><td class="storyline-col">' + (p.storyline || '') + '</td></tr>';
                }}).join('');
            }};
            var titleText = document.querySelector('.cosmos-betting-preview h1') ? document.querySelector('.cosmos-betting-preview h1').textContent.trim().toUpperCase() : 'BETTING BOARD';
            var subText = document.querySelector('.cosmos-betting-preview .subtitle') ? document.querySelector('.cosmos-betting-preview .subtitle').textContent.trim() : '';
            var bP = function(list, pn, tot) {{
                return '<div class="pg"><div class="hdr"><div class="hdr-l"><strong>' + titleText + '</strong> <span class="sub">' + subText + '</span></div><div class="hdr-r"><span class="leg"><b style="background:#1e8449">&nbsp;</b>WIN <b style="background:#58d68d">&nbsp;</b>T5 <b style="background:#abebc6">&nbsp;</b>T10 <b style="background:#f9e79f">&nbsp;</b>T20 <b style="background:#e74c3c">&nbsp;</b>MC</span><span class="pn">' + pn + '/' + tot + '</span></div></div><table><thead><tr><th>#</th><th>T</th><th class="l">PLAYER</th><th>CTY</th><th>RK</th><th>' + y1h + '</th><th>' + y2h + '</th><th>' + y3h + '</th><th>WIN</th><th>T5</th><th>T10</th><th>Win%</th><th>Fit</th><th>Why</th></tr></thead><tbody>' + bR(list) + '</tbody></table><div class="ftr">COSMOS GOLF · Odds from GolfData API · ' + new Date().toLocaleDateString('en-US', {{ month: 'short', year: 'numeric' }}) + '</div></div>';
            }};
            var css = '@page{{size:landscape;margin:0.15in}}*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:Arial,Helvetica,sans-serif;font-size:7px;background:#fff;color:#222;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}}.pg{{margin:0 auto 8px;padding:4px;page-break-after:always}}.pg:last-child{{page-break-after:avoid}}.hdr{{display:flex;justify-content:space-between;align-items:center;padding:4px 6px;background:#2c3e50;color:#fff;margin-bottom:3px}}.hdr-l{{font-size:11px}}.hdr-l .sub{{font-size:7px;font-weight:400;margin-left:8px;opacity:0.8}}.hdr-r{{display:flex;align-items:center;gap:10px}}.leg{{font-size:6px;display:flex;align-items:center;gap:4px}}.leg b{{display:inline-block;width:10px;height:8px;margin-right:1px}}.pn{{font-size:8px;font-weight:700;background:#f4c430;color:#000;padding:2px 6px;border-radius:2px}}table{{width:100%;border-collapse:collapse;font-size:6.5px;border:1px solid #bdc3c7}}th{{background:#ecf0f1;font-size:6px;font-weight:700;padding:2px 3px;text-align:center;border:1px solid #bdc3c7}}th.l{{text-align:left}}td{{padding:1px 2px;border:1px solid #ecf0f1;vertical-align:middle}}td.c{{text-align:center}}td.nm{{font-weight:600;white-space:nowrap;font-size:6.5px}}td.rk{{color:#7f8c8d;font-size:5.5px}}.tier{{display:inline-block;padding:1px 3px;border-radius:2px;font-size:5px;font-weight:700}}tr.main td{{border-bottom:none}}td.storyline-col{{white-space:normal;word-wrap:break-word;overflow-wrap:break-word;width:2in;max-width:2.5in;vertical-align:top;font-size:5px;color:#555;font-style:italic;padding:2px;line-height:1.2}}.ftr{{text-align:center;padding:3px;font-size:6px;color:#7f8c8d;margin-top:2px}}@media print{{.pg{{margin:0}}}}';
            var pageTitle = document.querySelector('.cosmos-betting-preview h1') ? document.querySelector('.cosmos-betting-preview h1').textContent.trim() : 'Cheat Sheet';
            var bodyHtml = pgs.map(function(p, i) {{ return bP(p, i + 1, pgs.length); }}).join('');
            var matchupsEl = document.getElementById('daily-matchups');
            if (matchupsEl && matchupsEl.querySelector('.matchups-table')) {{
                var matchupsBlocks = matchupsEl.querySelectorAll('.pdf-matchups');
                var matchupsInner = matchupsBlocks.length ? Array.from(matchupsBlocks).map(function(b) {{ return b.outerHTML; }}).join('') : matchupsEl.innerHTML;
                bodyHtml += '<div class="pg"><div class="hdr"><div class="hdr-l"><strong>DAILY MATCHUPS</strong> <span class="sub">' + subText + '</span></div><div class="hdr-r"><span class="pn">Matchups</span></div></div>' + matchupsInner + '<div class="ftr">COSMOS GOLF · ' + new Date().toLocaleDateString('en-US', {{ month: 'short', year: 'numeric' }}) + '</div></div>';
            }}
            var printHtml = '<!DOCTYPE html><html><head><meta charset="UTF-8"><' + 'title>' + pageTitle + '</' + 'title><style>' + css + '</style></head><body>' + bodyHtml + '<script>window.onload=function(){{setTimeout(function(){{window.print()}},300)}};<\\/script></body></html>';
            var w = window.open('', '_blank', 'width=1100,height=800');
            w.document.write(printHtml);
            w.document.close();
        }}
    </script>
</div>'''
    return html


def generate_v3_html(
    tournament: dict,
    players: list[dict],
    crew_picks: list[dict],
    year: int,
    insights: dict,
    matchups: Optional[dict],
    split_at: int = 50,
) -> str:
    """Generate v3 HTML: same design as v2 but minified rows for full 144-player field.

    - All players get full expandable dropdowns (same as v2)
    - Player HTML is minified (fewer newlines) to keep line count under ~2700
    - Players beyond split_at are hidden behind a 'Show Full Field' toggle button
    - Search auto-expands the full field when matching hidden players
    """
    # Generate base v2 HTML with all players
    html = generate_v2_html(tournament, players, crew_picks, year, insights, matchups)

    # --- Step 1: Minify player rows and split tbody ---
    # Find the tbody section containing player rows
    tbody_tag = "<tbody>"
    tbody_close = "</tbody>"
    tbody_start_idx = html.index(tbody_tag)
    tbody_end_idx = html.index(tbody_close, tbody_start_idx)

    before_tbody = html[: tbody_start_idx + len(tbody_tag)]
    tbody_content = html[tbody_start_idx + len(tbody_tag) : tbody_end_idx]
    after_tbody = html[tbody_end_idx:]  # includes </tbody></table></div>...

    # Split into individual player blocks on the player-row marker
    marker = '<tr class="player-row"'
    raw_blocks = tbody_content.split(marker)
    # raw_blocks[0] is whitespace before the first player; raw_blocks[1:] are player chunks

    player_blocks = []
    for part in raw_blocks[1:]:
        block = marker + part
        # Minify: normalize all whitespace into single spaces (safe for HTML rendering)
        block = " ".join(block.split())
        player_blocks.append(block)

    remaining_count = len(player_blocks) - split_at
    if remaining_count > 0:
        first_group = "\n".join(player_blocks[:split_at])
        second_group = "\n".join(player_blocks[split_at:])
        separator = (
            f'</tbody>'
            f'<tbody id="full-field-separator">'
            f'<tr><td colspan="4" style="padding:0;border:none;">'
            f'<button id="show-full-field-btn" '
            f'data-show-text="Show Full Field ({remaining_count} more)" '
            f'onclick="toggleFullField()" '
            f"style=\"width:100%;padding:14px;font-family:'Orbitron',sans-serif;"
            f'font-size:13px;font-weight:600;letter-spacing:1px;text-transform:uppercase;'
            f'border:1px solid #dee2e6;border-top:none;background:#f8f9fa;cursor:pointer;'
            f'color:#1a1a1a;">'
            f'Show Full Field ({remaining_count} more)'
            f'</button></td></tr></tbody>'
            f'<tbody id="full-field-body" style="display:none">'
        )
        new_tbody_content = f"\n{first_group}\n{separator}\n{second_group}\n"
    else:
        new_tbody_content = "\n" + "\n".join(player_blocks) + "\n"

    html = before_tbody + new_tbody_content + after_tbody

    # --- Step 2: Inject additional JS for full-field toggle and search override ---
    extra_js = """
        (function() {
            var fb = document.getElementById('full-field-body');
            if (fb) fb.addEventListener('click', function(e) {
                var row = e.target.closest('tr.player-row');
                if (row && row.dataset.player) togglePlayerDetail(row.dataset.player);
            });
        })();
        function toggleFullField() {
            var fb = document.getElementById('full-field-body');
            var btn = document.getElementById('show-full-field-btn');
            if (!fb || !btn) return;
            if (fb.style.display === 'none') {
                fb.style.display = '';
                btn.textContent = 'Hide Full Field';
            } else {
                fb.style.display = 'none';
                btn.textContent = btn.getAttribute('data-show-text');
            }
        }
        (function() {
            var origFilter = window.filterPlayers;
            window.filterPlayers = function(searchTerm) {
                var fb = document.getElementById('full-field-body');
                var btn = document.getElementById('show-full-field-btn');
                var term = searchTerm.toLowerCase().trim();
                if (term && fb) fb.style.display = '';
                if (origFilter) origFilter(searchTerm);
                if (!term && fb && btn && btn.textContent !== 'Hide Full Field') fb.style.display = 'none';
            };
        })();
"""

    html = html.replace("\n    </script>", extra_js + "    </script>", 1)

    return html


def generate_shopify_html(
    tournament: dict,
    players: list[dict],
    insights: dict,
    year: int,
) -> str:
    """Generate paste-into-Shopify HTML: same 4-col + expandable design as main, all players."""
    name = tournament.get("name", "Tournament")
    course = tournament.get("course", "")
    dates = (tournament.get("dates") or {})
    start = dates.get("start", "")
    end = dates.get("end", "")
    date_str = f"{start}–{end}" if start and end else ""
    prev_year1, prev_year2, prev_year3 = year - 1, year - 2, year - 3

    exec_summary = (insights.get("executive_summary") or "").strip()
    if len(exec_summary) > 600:
        exec_summary = exec_summary[:597] + "…"
    exec_summary = _escape_html(exec_summary)

    rows = []
    for p in players:
        rank = p.get("rank", 0)
        pname = _escape_html(p.get("name", ""))
        country = _escape_html((p.get("country") or "—"))
        owgr = p.get("owgr") or "—"
        tier = (p.get("tier") or "—").replace("FAVORITE", "FAV").replace("CONTENDER", "CON").replace("VALUE", "VAL").replace("LONGSHOT", "LS")
        storyline = (p.get("_display_storyline") or p.get("storyline") or "").strip()
        storyline = _escape_html(storyline)
        odds = p.get("win_odds") or "—"
        odds_cls = p.get("odds_class") or ""
        pid = f"p-{rank}"
        h1 = p.get("history_prev1") or "—"
        h2 = p.get("history_prev2") or "—"
        h3 = p.get("history_prev3") or "—"
        rc1, rc2, rc3 = _result_class(h1), _result_class(h2), _result_class(h3)
        top5 = p.get("top5_odds") or "—"
        top10 = p.get("top10_odds") or "—"
        recent = (p.get("recent_form") or "—").strip() or "—"
        recent = _escape_html(recent)
        sg = p.get("sg_total") or "—"
        win_pct = p.get("win_prob") or "—"
        t10_pct = p.get("top10_prob") or "—"
        fit = p.get("course_fit") or "—"

        rows.append(f'''<tr class="player-row" onclick="togglePlayerDetail('{pid}')" data-player="{pid}">
<td>{rank}</td><td class="player-cell"><span class="player-name">{pname} ▼</span><br><span class="player-country">{country} · OWGR #{owgr}</span> <span class="tier-badge">{tier}</span></td>
<td class="storyline-cell"><span class="storyline-text">{storyline}</span></td>
<td class="odds-cell"><span class="odds-value {odds_cls}">{odds}</span></td>
</tr>
<tr class="player-detail" id="{pid}-detail"><td colspan="4"><div class="detail-content">
<div class="detail-section"><div class="detail-section-title">Tournament History &amp; Odds</div>
<span class="fit-label">{prev_year1}</span> <span class="result-value result-{rc1}">{h1}</span> ·
<span class="fit-label">{prev_year2}</span> <span class="result-value result-{rc2}">{h2}</span> ·
<span class="fit-label">{prev_year3}</span> <span class="result-value result-{rc3}">{h3}</span><br>
Win {odds} · Top 5 {top5} · Top 10 {top10}</div>
<div class="detail-section"><div class="detail-section-title">Recent Form</div><div class="recent-form-text">{recent}</div></div>
<div class="detail-section">SG Total {sg} · Win % {win_pct} · T10 % {t10_pct} · Fit {fit}</div>
</div></td></tr>''')

    table_body = "\n".join(rows)
    html = f'''<div class="cosmos-betting-preview">
<style>
.cosmos-betting-preview{{font-family:sans-serif;max-width:1200px;margin:0 auto;padding:12px;}}
.cosmos-betting-preview h1{{font-size:20px;margin:0 0 6px 0;}}
.cosmos-betting-preview .sub{{font-size:13px;opacity:.9;}}
.cosmos-betting-preview .exec{{font-size:12px;line-height:1.35;margin:10px 0;padding:8px;background:#f5f5f5;border-radius:6px;}}
.cosmos-betting-preview table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px;}}
.cosmos-betting-preview th,.cosmos-betting-preview td{{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top;}}
.cosmos-betting-preview th{{background:#333;color:#fff;}}
.cosmos-betting-preview td:nth-child(1){{width:26px;text-align:center;}}
.cosmos-betting-preview td:nth-child(4){{white-space:nowrap;text-align:right;}}
.cosmos-betting-preview .player-name{{font-weight:600;}}
.cosmos-betting-preview .player-country{{font-size:11px;color:#666;}}
.cosmos-betting-preview .tier-badge{{font-size:10px;background:#eee;padding:1px 4px;border-radius:3px;margin-left:4px;}}
.cosmos-betting-preview .storyline-text{{font-size:11px;}}
.cosmos-betting-preview .player-row{{cursor:pointer;}}
.cosmos-betting-preview .player-row:hover{{background:#f9f9f9;}}
.cosmos-betting-preview .player-detail{{display:none;}}
.cosmos-betting-preview .player-detail.show{{display:table-row;}}
.cosmos-betting-preview .player-detail td{{background:#fafafa;padding:12px;border-top:none;}}
.cosmos-betting-preview .detail-content{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.cosmos-betting-preview .detail-section{{background:#fff;border:1px solid #eee;border-radius:6px;padding:10px;font-size:11px;}}
.cosmos-betting-preview .detail-section-title{{font-weight:700;color:#0B3D91;margin-bottom:6px;font-size:10px;text-transform:uppercase;}}
.cosmos-betting-preview .result-value{{padding:0 2px;}}
.cosmos-betting-preview .result-win{{background:#1e8449;color:#fff;}}
.cosmos-betting-preview .result-top5{{background:#58d68d;}}
.cosmos-betting-preview .result-top10{{background:#abebc6;}}
.cosmos-betting-preview .result-top25{{background:#f9e79f;}}
.cosmos-betting-preview .result-made{{background:#f5f5f5;}}
.cosmos-betting-preview .result-na{{background:#f5f5f5;color:#999;}}
.cosmos-betting-preview .result-mc{{background:#e74c3c;color:#fff;}}
.cosmos-betting-preview .recent-form-text{{font-size:11px;line-height:1.4;}}
</style>
<h1>{_escape_html(name)}</h1>
<div class="sub">{_escape_html(course)} · {date_str}</div>
<div class="exec">{exec_summary}</div>
<table>
<thead><tr><th>#</th><th>Player</th><th>Why They Could Win</th><th>Win Odds</th></tr></thead>
<tbody>
{table_body}
</tbody>
</table>
<p style="font-size:11px;margin-top:10px;color:#666;">COSMOS Golf · Click a row to expand. Odds for reference.</p>
</div>
<script>
function togglePlayerDetail(pid){{
 var row=document.querySelector("[data-player='"+pid+"']"); var det=document.getElementById(pid+"-detail");
 if(!row||!det) return;
 document.querySelectorAll(".cosmos-betting-preview .player-row.expanded").forEach(function(r){{
  if(r!==row){{ r.classList.remove("expanded"); var d=document.getElementById(r.dataset.player+"-detail"); if(d) d.classList.remove("show"); }}
 }});
 if(row.classList.contains("expanded")){{ row.classList.remove("expanded"); det.classList.remove("show"); }}
 else{{ row.classList.add("expanded"); det.classList.add("show"); }}
}}
</script>'''
    return html


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate tournament betting preview HTML"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        required=True,
        help="Tournament name (e.g., 'Farmers Insurance Open')"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Tournament year (default: current year)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML file path (default: {slug}_{year}.html)"
    )
    parser.add_argument(
        "--shopify",
        action="store_true",
        help="Also write a Shopify paste file (4-col + expandable, same design as main)"
    )
    parser.add_argument(
        "--v2",
        action="store_true",
        help="Also write a paste-ready v2 HTML (compact design, optional player cap for Shopify)"
    )
    parser.add_argument(
        "--v2-max-players",
        type=int,
        default=55,
        help="Max players in v2 table (default 55). The full HTML has all players with PDF export."
    )
    parser.add_argument(
        "--v3",
        action="store_true",
        help="Write a v3 HTML: full 144-player field with minified rows and Show Full Field toggle"
    )
    parser.add_argument(
        "--v3-max-players",
        type=int,
        default=144,
        help="Max players in v3 table (default 144)."
    )
    parser.add_argument(
        "--v3-split-at",
        type=int,
        default=50,
        help="Number of players visible before 'Show Full Field' button (default 50)."
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Explicit data-file slug (overrides the slugified tournament name). "
             "If omitted, the schedule entry's slug is used when found.",
    )
    args = parser.parse_args()

    tournament_name = args.tournament
    year = args.year
    slug = args.slug or _slugify(tournament_name)

    print(f"""
{'=' * 70}
 COSMOS Golf - Tournament Preview Generator
 Tournament: {tournament_name}
 Year: {year}
{'=' * 70}
""")

    # Load schedule and find tournament
    schedule = load_schedule()
    tournament = find_tournament_in_schedule(tournament_name, schedule)

    # Canonical slug: prefer explicit --slug, else the schedule entry's slug.
    # This keeps sponsor/location-named events (e.g. "...presented by Workday",
    # "U.S. Open") aligned with the short slug their data files actually use.
    if not args.slug and tournament and tournament.get("slug"):
        slug = tournament["slug"]

    if not tournament:
        print(f"[WARNING] Tournament not found in schedule, using defaults")
        tournament = {
            "name": tournament_name,
            "dates": {},
            "location": "TBD",
            "course": "TBD",
            "purse": "$0",
            "winner_share": "$0",
            "par": 72,
            "yards": "TBD",
            "field_size": 156,
            "fedex_points": 500
        }
    else:
        print(f"[OK] Found tournament: {tournament.get('name')}")

    # Load player data
    player_data = load_player_data(slug, year)
    if not player_data.get("odds"):
        print(f"[ERROR] No player data found at data/{slug}_{year}_players_data.json")
        print("Run fetch_draftkings_odds.py first to fetch odds data.")
        return 1

    print(f"[OK] Loaded {len(player_data.get('odds', {}))} players")

    # Load storylines
    storylines = load_storylines(slug, year)
    print(f"[OK] Loaded {len(storylines)} storylines")

    # Load recent form
    recent_form = load_recent_form(slug, year)
    print(f"[OK] Loaded {len(recent_form)} recent form entries")

    # Load crew picks
    crew_picks = load_crew_picks()
    print(f"[OK] Loaded {len(crew_picks)} crew members")

    # Load AI insights
    insights = load_ai_insights(slug, year)
    if insights.get("executive_summary"):
        print(f"[OK] Loaded AI insights with {len(insights.get('insights', []))} insights")
    else:
        print(f"[INFO] No AI insights found")

    # Load matchups (2-ball, 3-ball)
    matchups = load_matchups(slug, year)
    if matchups:
        t2 = len(matchups.get("tournament_matchups") or []) + len(matchups.get("round_matchups") or [])
        t3 = len(matchups.get("daily_three_balls") or []) + len(matchups.get("three_balls") or [])
        print(f"[OK] Loaded matchups: {t2} 2-ball, {t3} 3-ball")
    else:
        print(f"[INFO] No matchups file found")

    # Build player list
    players = build_player_list(player_data, storylines, recent_form, year)
    print(f"[OK] Built player list with {len(players)} players")

    # Generate HTML
    html = generate_html(tournament, players, crew_picks, year, insights, matchups)

    # Write output
    output_path = args.output or (PROJECT_ROOT / f"{slug}_{year}.html")
    output_path.write_text(html, encoding="utf-8")

    msg = f"""
{'=' * 70}
 SUCCESS - Preview Generated
{'=' * 70}
 Output: {output_path}
 Players: {len(players)}
 File size: {len(html):,} bytes
"""
    if args.shopify:
        shopify_html = generate_shopify_html(tournament, players, insights, year)
        shopify_path = PROJECT_ROOT / f"{slug}_{year}_shopify.html"
        shopify_path.write_text(shopify_html, encoding="utf-8")
        size = len(shopify_html.encode("utf-8"))
        msg += f"""
 Shopify (copy-paste): {shopify_path} — {size:,} bytes
   → Same 4-column + expandable design. Copy entire file into Shopify (Custom HTML).
"""
    if args.v2:
        v2_players = players[: args.v2_max_players]
        v2_html = generate_v2_html(
            tournament, v2_players, crew_picks, year, insights, matchups,
            all_players=players,
        )
        v2_path = PROJECT_ROOT / f"{slug}_{year}_v2.html"
        v2_path.write_text(v2_html, encoding="utf-8")
        v2_size = len(v2_html.encode("utf-8"))
        msg += f"""
 V2 (paste-ready): {v2_path} — {v2_size:,} bytes ({len(v2_players)} players)
   → Compact design, PDF button, insight cards. Paste into Shopify Custom HTML.
"""
    if args.v3:
        v3_players = players[: args.v3_max_players]
        v3_html = generate_v3_html(
            tournament, v3_players, crew_picks, year, insights, matchups,
            split_at=args.v3_split_at,
        )
        v3_path = PROJECT_ROOT / f"{slug}_{year}_v3.html"
        v3_path.write_text(v3_html, encoding="utf-8")
        v3_size = len(v3_html.encode("utf-8"))
        v3_lines = v3_html.count("\n") + 1
        msg += f"""
 V3 (full field): {v3_path} — {v3_size:,} bytes ({len(v3_players)} players, {v3_lines} lines)
   → Full field with minified rows. Top {args.v3_split_at} visible, rest behind 'Show Full Field'.
"""
    msg += """
 Next steps:
 1. Upload course image to Shopify Files (if not already)
 2. Fill in crew picks (edit data/crew_picks.json)
{'=' * 70}
"""
    print(msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
