#!/usr/bin/env python3
"""Generate a templated HTML email newsletter for the weekly COSMOS Golf send.

Another output of the weekly run: reuses the same data the HTML preview uses
(players_data, AI insights/storylines, weather, crew picks) and renders an
email-client-safe digest of the top storylines, each with the featured player's
headshot. Paste the output into Shopify Email (or any campaign tool).

Player photos are resolved from ESPN's public search API (free, no key) and
cached to data/player_headshot_cache.json so we only fetch once. Photos use
HOSTED urls (not base64) because Gmail strips inlined images.

Usage:
    python3 scripts/generate_email_newsletter.py --tournament "Charles Schwab Challenge" --year 2026
    python3 scripts/generate_email_newsletter.py --tournament "..." --no-network   # cache/fallback only

Output: {slug}_{year}_email.html (repo root) and out/{slug}_{year}_email.html
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import generate_tournament_html as gt  # noqa: E402  (reuse loaders/helpers)

try:
    # Reuse the existing Wikipedia headshot resolver as an ESPN fallback (prior art).
    from send_rcs_preview import _wikipedia_photo as _wiki_headshot  # noqa: E402
except Exception:  # pragma: no cover - degrade gracefully if unavailable
    def _wiki_headshot(_name: str) -> str:
        return ""

# --- Brand --------------------------------------------------------------------
# Logo art has ~460px of transparent space above/below the wordmark; Shopify's CDN
# center-crop (height=170) trims it to a tight band so the header sits flush.
LOGO_URL = "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/COSMOS_Research-Logo.001.png?v=1779767810&width=1920&height=170&crop=center"
SITE_BASE = "https://www.golfinthecosmos.com"


def default_preview_link(slug_or_name: str, year: int) -> str:
    """Per-tournament Shopify page URL, e.g. .../pages/2026-charles-schwab-challenge."""
    return f"{SITE_BASE}/pages/{gt.page_handle(slug_or_name, year)}"
HEADSHOT_CACHE = ROOT / "data" / "player_headshot_cache.json"
NEWS_CACHE = ROOT / "data" / "player_news_cache.json"

PRIMARY = "#0B3D91"
DARK = "#1a1a1a"
MUTED = "#6c757d"
BORDER = "#dee2e6"
BG_LIGHT = "#f8f9fa"
FONT = "Arial, Helvetica, 'Segoe UI', sans-serif"

# Insight card category -> (accent color, label)
CATEGORY = {
    "favorite": ("#0a7a3f", "FAVORITE"),
    "value": ("#005bbb", "VALUE"),
    "longshot": ("#b07d00", "LONGSHOT"),
    "avoid": ("#b00020", "AVOID"),
    "course_fit": ("#005bbb", "COURSE FIT"),
    "form": ("#0a7a3f", "FORM"),
}
# Deterministic avatar background colors for the initials fallback
AVATAR_COLORS = ["#0B3D91", "#0a7a3f", "#005bbb", "#b07d00", "#7d3c98", "#1a5276"]


# --- Player headshots (ESPN, cached) -----------------------------------------
def _espn_headshot(name: str) -> str:
    """Best-effort golf headshot URL via ESPN's public search API ("" on miss)."""
    try:
        r = requests.get(
            "https://site.web.api.espn.com/apis/search/v2",
            params={"query": name, "limit": 8},
            headers={"User-Agent": "Mozilla/5.0 (compatible; CosmosGolf/1.0)"},
            timeout=8,
        )
        data = r.json()
        for group in data.get("results", []):
            if group.get("type") != "player":
                continue
            for c in group.get("contents", []):
                if c.get("sport") == "golf":
                    return (c.get("image") or {}).get("default") or ""
    except Exception:
        return ""
    return ""


def resolve_headshots(names: list[str], use_network: bool = True, refresh: bool = False) -> dict:
    """Return {name: headshot_url}. Cached to disk; only the missing ones hit the network."""
    cache = {}
    if HEADSHOT_CACHE.exists():
        try:
            cache = json.loads(HEADSHOT_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    changed = False
    for name in names:
        cached = cache.get(name, None)
        have = isinstance(cached, str) and cached.strip()
        if have and not refresh:
            continue
        if not use_network:
            cache.setdefault(name, "")
            continue
        # ESPN first (great coverage incl. lesser-knowns); Wikipedia covers
        # common-name collisions ESPN can't disambiguate (e.g. "Justin Thomas").
        url = _espn_headshot(name) or _wiki_headshot(name)
        cache[name] = url
        changed = True
        time.sleep(0.15)  # be polite to the source APIs

    if changed:
        HEADSHOT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        HEADSHOT_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return cache


# --- Player news (Google News RSS, free/no key, cached daily) -----------------
def _google_news_top(query: str) -> dict:
    """Top recent headline for a query via Google News RSS. {} on miss/failure."""
    try:
        r = requests.get(
            "https://news.google.com/rss/search",
            params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            headers={"User-Agent": "Mozilla/5.0 (compatible; CosmosGolf/1.0)"},
            timeout=8,
        )
        root = ET.fromstring(r.content)
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            if not (title and link):
                continue
            source = ""
            if " - " in title:  # Google News appends " - Source"
                title, source = title.rsplit(" - ", 1)
            return {"title": title.strip(), "link": link, "source": source.strip()}
    except Exception:
        return {}
    return {}


def resolve_news(names: list[str], use_network: bool = True, refresh: bool = False) -> list:
    """Return [(player, {title,link,source})] for names with a headline. Cached per day."""
    cache = {}
    if NEWS_CACHE.exists():
        try:
            cache = json.loads(NEWS_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    changed = False
    for name in names:
        entry = cache.get(name)
        fresh = isinstance(entry, dict) and entry.get("fetched") == today and entry.get("link")
        if fresh and not refresh:
            continue
        if not use_network:
            continue
        news = _google_news_top(f'"{name}" golf')
        if news:
            news["fetched"] = today
            cache[name] = news
            changed = True
        time.sleep(0.15)  # be polite to Google News

    if changed:
        NEWS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        NEWS_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    out = []
    for name in names:
        e = cache.get(name)
        if isinstance(e, dict) and e.get("link"):
            out.append((name, e))
    return out


# --- HTML fragments -----------------------------------------------------------
def _avatar(name: str, url: str, size: int = 64, ring: str = "#ffffff") -> str:
    """Circular player photo with an accent ring, or colored initials fallback. Email-safe."""
    initials = "".join(p[0] for p in name.split()[:2]).upper() or "?"
    color = AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]
    if url:
        inner = (
            f'<img src="{escape(url)}" width="{size}" height="{size}" alt="{escape(name)}" '
            f'style="display:block;width:{size}px;height:{size}px;border-radius:{size}px;'
            f'object-fit:cover;border:3px solid {ring};" />'
        )
    else:
        fs = int(size * 0.4)
        inner = (
            f'<span style="font-family:{FONT};font-size:{fs}px;font-weight:bold;'
            f'color:#ffffff;line-height:{size}px;">{escape(initials)}</span>'
        )
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td width="{size}" height="{size}" align="center" valign="middle" '
        f'bgcolor="{color}" style="width:{size}px;height:{size}px;border-radius:{size}px;'
        f'text-align:center;vertical-align:middle;background:{color};border:3px solid {ring};">{inner}</td>'
        f'</tr></table>'
    )


GOLD = "#b8902f"


def _stat_tile(label: str, value: str, color: str, right: bool = True, bottom: bool = False) -> str:
    borders = ""
    if right:
        borders += f"border-right:1px solid {BORDER};"
    if bottom:
        borders += f"border-bottom:1px solid {BORDER};"
    return (
        f'<td align="center" valign="middle" width="33%" style="padding:9px 6px;{borders}">'
        f'<div style="font-family:{FONT};font-size:17px;font-weight:bold;color:{color};line-height:1;">{escape(value)}</div>'
        f'<div style="font-family:{FONT};font-size:8.5px;letter-spacing:1.2px;color:{MUTED};text-transform:uppercase;margin-top:5px;">{escape(label)}</div>'
        f'</td>'
    )


def _fmt_sg(raw) -> str:
    try:
        return f"{float(raw):+.2f}"
    except (TypeError, ValueError):
        return "—"


def _finish_disp(v) -> str:
    s = (str(v) if v is not None else "").strip()
    return "—" if s.upper() in ("", "NA", "N/A", "—") else s


def _finish_color(v) -> str:
    s = (str(v) if v is not None else "").strip().upper()
    if s in ("MC", "WD", "CUT", "DQ"):
        return "#b00020"
    if s in ("", "NA", "N/A", "—"):
        return "#9aa1aa"
    n = s.replace("T", "")
    if n.isdigit() and int(n) <= 10:
        return "#0a7a3f"
    return DARK


def _storyline_card(idx: int, card: dict, player_lookup: dict, photos: dict, year: int) -> str:
    cat = (card.get("category") or "value").lower()
    accent, label = CATEGORY.get(cat, CATEGORY["value"])
    title = escape(card.get("title", ""))
    text = escape(card.get("insight", ""))
    players = card.get("players", []) or []
    lead = players[0] if players else ""
    p = player_lookup.get(lead, {})
    photo = photos.get(lead, "")

    pill = (
        f'<span style="display:inline-block;background:{accent};color:#ffffff;font-family:{FONT};'
        f'font-size:9px;font-weight:bold;letter-spacing:1.5px;padding:4px 10px;border-radius:12px;'
        f'text-transform:uppercase;">{label}</span>'
    )
    num = (
        f'<span style="font-family:{FONT};font-size:11px;font-weight:bold;letter-spacing:2px;'
        f'color:#c2c8d0;">No.{idx:02d}</span>'
    )

    # 3x3 stat grid (only when we matched the player to board data):
    #   row 1 - Win / Top 5 / Top 10 odds
    #   row 2 - finish at this event the last 3 years
    #   row 3 - Model Win / SG Total / Top 10 probability
    stat_strip = ""
    if p:
        y1, y2, y3 = year - 1, year - 2, year - 3
        h1, h2, h3 = p.get("history_prev1"), p.get("history_prev2"), p.get("history_prev3")
        row1 = (
            _stat_tile("Win", p.get("win_odds", "—"), accent, bottom=True)
            + _stat_tile("Top 5", p.get("top5_odds", "—"), DARK, bottom=True)
            + _stat_tile("Top 10", p.get("top10_odds", "—"), DARK, right=False, bottom=True)
        )
        row2 = (
            _stat_tile(str(y1), _finish_disp(h1), _finish_color(h1), bottom=True)
            + _stat_tile(str(y2), _finish_disp(h2), _finish_color(h2), bottom=True)
            + _stat_tile(str(y3), _finish_disp(h3), _finish_color(h3), right=False, bottom=True)
        )
        row3 = (
            _stat_tile("Model Win", p.get("win_prob", "—"), DARK)
            + _stat_tile("SG Total", _fmt_sg(p.get("sg_total_raw")), PRIMARY)
            + _stat_tile("Top 10%", p.get("top10_prob", "—"), DARK, right=False)
        )
        stat_strip = f"""
            <tr><td colspan="2" style="padding:14px 18px 18px 18px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                     bgcolor="{BG_LIGHT}" style="background:{BG_LIGHT};border:1px solid {BORDER};border-radius:8px;">
                <tr>{row1}</tr>
                <tr>{row2}</tr>
                <tr>{row3}</tr>
              </table>
            </td></tr>"""

    name_line = (
        f'<div style="font-family:{FONT};font-size:12px;font-weight:bold;letter-spacing:.5px;'
        f'color:{accent};text-transform:uppercase;margin:2px 0 8px 0;">{escape(lead)}</div>'
        if lead else ""
    )

    return f"""
    <tr><td style="padding:0 0 16px 0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:#ffffff;border:1px solid {BORDER};border-radius:12px;box-shadow:0 2px 10px rgba(11,61,145,0.06);">
        <tr><td colspan="2" height="4" bgcolor="{accent}" style="font-size:0;line-height:0;border-radius:12px 12px 0 0;">&nbsp;</td></tr>
        <tr>
          <td width="106" valign="top" align="center" style="padding:20px 0 6px 16px;">{_avatar(lead, photo, 76, ring=accent)}</td>
          <td valign="top" style="padding:20px 18px 6px 14px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
              <td align="left" valign="middle">{pill}</td>
              <td align="right" valign="middle">{num}</td>
            </tr></table>
            {name_line}
            <div style="font-family:{FONT};font-size:18px;font-weight:bold;color:{DARK};margin:0 0 7px 0;line-height:1.25;">{title}</div>
            <div style="font-family:{FONT};font-size:13.5px;color:#454b54;line-height:1.55;">{text}</div>
          </td>
        </tr>
        {stat_strip}
      </table>
    </td></tr>"""


def _section_header(title: str, sub: str = "") -> str:
    sub_html = (
        f'<div style="font-family:{FONT};font-size:12px;color:{MUTED};margin-top:4px;">{escape(sub)}</div>'
        if sub else ""
    )
    return f"""
    <tr><td style="padding:26px 0 14px 0;">
      <div style="width:40px;height:3px;background:{GOLD};margin-bottom:10px;"></div>
      <div style="font-family:{FONT};font-size:20px;font-weight:bold;letter-spacing:1px;color:{DARK};text-transform:uppercase;">{escape(title)}</div>
      {sub_html}
    </td></tr>"""


def _cta_button(link: str, text: str, label: str = "") -> str:
    sub = (
        f'<div style="font-family:{FONT};font-size:11px;color:{MUTED};margin-top:10px;">{escape(label)}</div>'
        if label else ""
    )
    return f"""
    <tr><td align="center" style="padding:30px 0 6px 0;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td bgcolor="{DARK}" style="border-radius:8px;background:{DARK};">
          <a href="{escape(link)}" style="display:inline-block;font-family:{FONT};font-size:14px;font-weight:bold;letter-spacing:1.5px;color:#ffffff;text-decoration:none;padding:16px 38px;text-transform:uppercase;border-radius:8px;">{escape(text)} &rarr;</a>
        </td>
      </tr></table>
      {sub}
    </td></tr>"""


def _news_section(items: list) -> str:
    """Bottom 'Player News' block: one linked headline per featured player."""
    if not items:
        return ""
    rows = ""
    for player, n in items:
        source = (
            f'<div style="font-family:{FONT};font-size:11px;color:{MUTED};margin-top:2px;">{escape(n.get("source", ""))}</div>'
            if n.get("source") else ""
        )
        rows += f"""
        <tr><td style="padding:12px 0;border-bottom:1px solid {BORDER};">
          <div style="font-family:{FONT};font-size:11px;font-weight:bold;letter-spacing:.5px;color:{PRIMARY};text-transform:uppercase;margin-bottom:3px;">{escape(player)}</div>
          <a href="{escape(n['link'])}" style="font-family:{FONT};font-size:14px;color:{DARK};text-decoration:none;font-weight:600;line-height:1.4;">{escape(n['title'])} &rarr;</a>
          {source}
        </td></tr>"""
    return f"""
          {_section_header("Player News", "Latest headlines on this week's headliners")}
          <tr><td>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>
          </td></tr>"""


# --- Trending player (biggest course climber) ---------------------------------
def _trend_chart_url(pts: list, color: str = "#0a7a3f") -> str:
    """QuickChart line graph (hosted PNG, email-safe). Y reversed so a better finish trends up."""
    labels = [str(y) for (y, n, d) in pts]
    data = [n for (y, n, d) in pts]
    cfg = {
        "type": "line",
        "data": {"labels": labels, "datasets": [{
            "data": data, "borderColor": color, "backgroundColor": "rgba(10,122,63,0.12)",
            "fill": True, "pointRadius": 4, "pointBackgroundColor": color, "borderWidth": 3, "tension": 0.3,
        }]},
        "options": {
            "plugins": {"legend": {"display": False}},
            "scales": {
                "y": {"reverse": True, "display": False},
                "x": {"grid": {"display": False}, "ticks": {"color": "#6c757d", "font": {"size": 11}}},
            },
            "layout": {"padding": 6},
        },
    }
    # version=4 → Chart.js v4 option syntax (QuickChart defaults to v2, which ignores these options)
    return "https://quickchart.io/chart?version=4&w=200&h=72&bkg=transparent&c=" + urllib.parse.quote(json.dumps(cfg))


def _trending_section(player: dict, pts: list, course: str, photo: str) -> str:
    if not player or not pts:
        return ""
    arrows = "  &rarr;  ".join(escape(d) for (y, n, d) in pts)
    chart = _trend_chart_url(pts)
    venue = escape(course or "the host course")
    return f"""
      <tr><td style="padding:18px 0 0 0;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
               bgcolor="{BG_LIGHT}" style="background:{BG_LIGHT};border:1px solid {BORDER};border-left:4px solid {GOLD};border-radius:8px;">
          <tr>
            <td width="76" valign="middle" align="center" style="padding:12px 0 12px 12px;">{_avatar(player['name'], photo, 54, ring=GOLD)}</td>
            <td valign="middle" style="padding:12px 10px;">
              <div style="font-family:{FONT};font-size:10px;font-weight:bold;letter-spacing:1.5px;color:#9c6f00;text-transform:uppercase;">&#128200; Biggest Climber &middot; {venue}</div>
              <div style="font-family:{FONT};font-size:16px;font-weight:bold;color:{DARK};margin:3px 0 3px;">{escape(player['name'])}</div>
              <div style="font-family:{FONT};font-size:13px;font-weight:bold;color:{DARK};">{arrows} <span style="color:{'#0a7a3f'};">&#9650;</span></div>
            </td>
            <td width="212" valign="middle" align="right" style="padding:8px 12px 8px 0;">
              <img src="{escape(chart)}" width="200" height="72" alt="{escape(player['name'])} finish trend" style="display:block;width:200px;height:72px;" />
            </td>
          </tr>
        </table>
      </td></tr>"""


# --- Form climbers (improving finishes across the last 3 starts) --------------
GREEN = "#0a7a3f"

def _climber_row(c: dict, photo: str, last: bool = False) -> str:
    """One climber line: avatar + name + the three legs with arrows."""
    parts = []
    for i, (event, finish) in enumerate(c["legs"]):
        newest = i == len(c["legs"]) - 1
        col = GREEN if newest else MUTED
        wt = "bold" if newest else "normal"
        parts.append(
            f'<span style="color:{col};font-weight:{wt};white-space:nowrap;">'
            f'{escape(gt.shorten_event(event))} <strong>{escape(finish)}</strong></span>'
        )
    path = ' <span style="color:#c9ced3;">&rarr;</span> '.join(parts)
    border = "" if last else f"border-bottom:1px solid {BORDER};"
    return f"""
              <tr>
                <td width="52" valign="middle" align="center" style="padding:10px 0 10px 10px;{border}">{_avatar(c['name'], photo, 38, ring=GREEN)}</td>
                <td valign="middle" style="padding:10px 10px;{border}">
                  <div style="font-family:{FONT};font-size:14px;font-weight:bold;color:{DARK};">{escape(c['name'])}</div>
                  <div style="font-family:{FONT};font-size:12px;color:{MUTED};margin-top:3px;line-height:18px;">{path}</div>
                </td>
                <td width="58" valign="middle" align="right" style="padding:10px 10px 10px 0;{border}">
                  <div style="font-family:{FONT};font-size:15px;font-weight:bold;color:{GREEN};white-space:nowrap;">&#9650;{c['improvement']}</div>
                  <div style="font-family:{FONT};font-size:9px;color:{MUTED};letter-spacing:0.5px;text-transform:uppercase;">spots</div>
                </td>
              </tr>"""


def _form_climbers_section(climbers: list, photos: dict) -> str:
    """Trend band listing players heating up across their last three starts."""
    if not climbers:
        return ""
    rows = "".join(
        _climber_row(c, photos.get(c["name"], ""), last=(i == len(climbers) - 1))
        for i, c in enumerate(climbers)
    )
    return f"""
      <tr><td style="padding:12px 0 0 0;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
               bgcolor="{BG_LIGHT}" style="background:{BG_LIGHT};border:1px solid {BORDER};border-left:4px solid {GREEN};border-radius:8px;">
          <tr><td style="padding:12px 12px 4px 12px;">
            <div style="font-family:{FONT};font-size:10px;font-weight:bold;letter-spacing:1.5px;color:{GREEN};text-transform:uppercase;">&#128293; Form Climbers &middot; Last 3 Starts</div>
          </td></tr>
          <tr><td style="padding:0 2px 4px 2px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>
          </td></tr>
        </table>
      </td></tr>"""


def _wind_email_block(wind_by_day: list) -> str:
    """Compact AM/PM wind table for the email — pure table + inline styles, no CSS
    transforms (Outlook/Gmail safe). Returns '' when there's no per-day wind data."""
    if not wind_by_day:
        return ""

    def _fmt(block):
        if not block or block.get("speed_mph") is None:
            return '<span style="color:#999999;">&mdash;</span>'
        d = escape(block.get("dir", "") or "")
        gust = block.get("gust_mph")
        g = f' <span style="color:#888888;">G{gust}</span>' if gust else ""
        return f'<strong>{block.get("speed_mph")}</strong> mph {d}{g}'

    rows = ""
    am_speeds, pm_speeds = [], []
    for day in wind_by_day:
        am, pm = day.get("am"), day.get("pm")
        if am and am.get("speed_mph") is not None:
            am_speeds.append(am["speed_mph"])
        if pm and pm.get("speed_mph") is not None:
            pm_speeds.append(pm["speed_mph"])
        rows += (
            f'<tr><td style="padding:4px 12px 4px 0;font-family:{FONT};font-size:13px;color:{DARK};font-weight:700;white-space:nowrap;">{escape(day.get("weekday",""))}</td>'
            f'<td style="padding:4px 12px 4px 0;font-family:{FONT};font-size:13px;color:#333333;">{_fmt(am)}</td>'
            f'<td style="padding:4px 0;font-family:{FONT};font-size:13px;color:#333333;">{_fmt(pm)}</td></tr>'
        )

    wave = ""
    if am_speeds and pm_speeds:
        am_avg = sum(am_speeds) / len(am_speeds)
        pm_avg = sum(pm_speeds) / len(pm_speeds)
        if abs(am_avg - pm_avg) < 1.5:
            wave = "Even AM/PM wind across the draw."
        elif am_avg < pm_avg:
            wave = f"Mornings calmer (~{round(am_avg)} vs ~{round(pm_avg)} mph) &mdash; slight edge to AM tee times."
        else:
            wave = f"Afternoons calmer (~{round(pm_avg)} vs ~{round(am_avg)} mph) &mdash; slight edge to PM tee times."
    wave_html = (f'<div style="margin-top:8px;font-family:{FONT};font-size:12px;color:#555555;font-style:italic;">&#127754; {wave}</div>'
                 if wave else "")

    return f"""
              <div style="margin-top:12px;padding-top:10px;border-top:1px solid #e2e2e2;">
                <strong style="font-family:{FONT};color:{DARK};letter-spacing:.5px;font-size:13px;">&#127788; WIND BY DAY &middot; 8AM / 12PM</strong>
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:6px;">
                  <tr><td style="padding:0 12px 4px 0;font-family:{FONT};font-size:11px;color:#888888;text-transform:uppercase;letter-spacing:.04em;">Day</td>
                      <td style="padding:0 12px 4px 0;font-family:{FONT};font-size:11px;color:#888888;text-transform:uppercase;letter-spacing:.04em;">8 AM</td>
                      <td style="padding:0 0 4px 0;font-family:{FONT};font-size:11px;color:#888888;text-transform:uppercase;letter-spacing:.04em;">12 PM</td></tr>
                  {rows}
                </table>
                {wave_html}
              </div>"""


# --- Main render --------------------------------------------------------------
def build_email_html(
    tournament: dict,
    players: list[dict],
    insights: dict,
    weather: str,
    photos: dict,
    link: str,
    max_storylines: int,
    year: int,
    logo_url: str,
    news_items: list = None,
    trending: tuple = None,
    climbers: list = None,
) -> str:
    name = tournament.get("name", "PGA Tour Tournament")
    dates = gt.format_dates(tournament.get("dates", {}))
    location = tournament.get("location", "")
    course = tournament.get("course", "")
    hero = gt.course_image_src(name)
    exec_summary = (insights.get("executive_summary") or "").strip()
    cards = insights.get("insights", []) or []
    player_lookup = {p["name"]: p for p in players}

    event_line = " &nbsp;|&nbsp; ".join([x for x in [dates, location] if x])

    host = link.split("://")[-1].split("/")[0]
    link_label = host[4:] if host.startswith("www.") else host  # drop leading www.

    storyline_rows = "".join(
        _storyline_card(i, c, player_lookup, photos, year) for i, c in enumerate(cards[:max_storylines], 1)
    )

    preheader = exec_summary[:140] if exec_summary else f"COSMOS Golf betting preview — {name}, {dates}."

    exec_block = ""
    if exec_summary:
        exec_block = f"""
        {_section_header("The Take")}
        <tr><td style="padding:0 0 4px 0;">
          <div style="font-family:{FONT};font-size:15px;line-height:1.65;color:#2a2f36;
               border-left:3px solid {GOLD};padding:2px 0 2px 18px;font-style:italic;">{escape(exec_summary)}</div>
        </td></tr>"""

    # Mid-email CTA right after "The Take" (only when the exec summary is present)
    mid_cta = _cta_button(link, "Read the Full Preview", link_label) if exec_summary else ""

    news_block = _news_section(news_items or [])

    trending_block = ""
    if trending and trending[0]:
        _tp, _tpts = trending
        trending_block = _trending_section(_tp, _tpts, course, photos.get(_tp["name"], ""))

    climbers_block = _form_climbers_section(climbers or [], photos)

    weather_block = ""
    if weather and "will be updated" not in weather.lower():
        wind_strip = _wind_email_block(gt.load_weather_periods())
        weather_block = f"""
        <tr><td style="padding:18px 0 0 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                 bgcolor="{BG_LIGHT}" style="background:{BG_LIGHT};border-left:4px solid {GOLD};border-radius:6px;">
            <tr><td style="padding:13px 16px;font-family:{FONT};font-size:13px;line-height:1.55;color:#333333;">
              <strong style="color:{DARK};letter-spacing:.5px;">&#9925; WEATHER &middot;</strong> {escape(weather)}
              {wind_strip}
            </td></tr>
          </table>
        </td></tr>"""

    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    link_clean = link_label

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="x-apple-disable-message-reformatting" />
<meta name="color-scheme" content="light only" />
<title>{escape(name)} — Betting Preview</title>
<!-- Please note that templates must include {{{{ unsubscribe_link }}}} and {{{{ open_tracking_block }}}} variables. -->
</head>
<body style="margin:0;padding:0;background:#0e1116;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#0e1116;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0e1116;">
  <tr><td align="center" style="padding:24px 12px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
           style="width:600px;max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;">

      <!-- Brand header -->
      <tr><td bgcolor="{PRIMARY}" style="background:{PRIMARY};background-image:linear-gradient(135deg,#0B3D91 0%,#091a45 100%);padding:20px 24px 22px 24px;">
        <img src="{escape(logo_url)}" width="380" alt="COSMOS Golf" style="display:block;width:380px;max-width:80%;height:auto;margin:0 0 2px -2px;" />
        <div style="font-family:{FONT};font-size:11px;letter-spacing:3px;color:#a9bfe6;margin-top:6px;">&#47;&#47; BETTING PREVIEW</div>
        <div style="font-family:{FONT};font-size:24px;font-weight:bold;letter-spacing:1px;color:#ffffff;text-transform:uppercase;margin-top:6px;line-height:1.14;">{escape(name)}</div>
        <div style="font-family:{FONT};font-size:13px;color:#c7d2e6;margin-top:8px;">{event_line}</div>
      </td></tr>
      <tr><td height="4" bgcolor="{GOLD}" style="font-size:0;line-height:0;background:{GOLD};">&nbsp;</td></tr>

      <!-- Hero -->
      <tr><td style="font-size:0;line-height:0;">
        <img src="{hero}" width="600" alt="{escape(course)}" style="display:block;width:100%;max-width:600px;height:auto;" />
      </td></tr>

      <!-- Body -->
      <tr><td style="padding:6px 24px 26px 24px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          {weather_block}
          {exec_block}
          {mid_cta}
          {trending_block}
          {climbers_block}

          {_section_header("Top Storylines", "The plays our model and the board disagree on most")}
          <tr><td>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              {storyline_rows}
            </table>
          </td></tr>

          {_cta_button(link, "Read the Full Preview", link_label)}
          {news_block}
        </table>
      </td></tr>

      <!-- Footer -->
      <tr><td bgcolor="{DARK}" style="background:{DARK};padding:24px;text-align:center;">
        <img src="{escape(logo_url)}" width="200" alt="COSMOS Golf" style="display:block;width:200px;max-width:60%;height:auto;margin:0 auto 12px auto;" />
        <div style="font-family:{FONT};font-size:11px;color:#8a93a0;margin-top:8px;line-height:1.6;">
          <a href="{escape(link)}" style="color:{GOLD};text-decoration:none;font-weight:bold;">{escape(link_clean)}</a><br/>
          Strokes Gained &amp; model from Data Golf. Odds from GolfData API. Photos via ESPN.<br/>
          Generated {now_str}. For entertainment only &mdash; please wager responsibly.<br/>
          <a href="{{{{ unsubscribe_link }}}}" style="color:#8a93a0;text-decoration:underline;">Unsubscribe</a> from these emails.
        </div>
      </td></tr>

    </table>
  </td></tr>
</table>
{{{{ open_tracking_block }}}}
</body>
</html>"""


def _force_full_width_tables(html: str) -> str:
    """Ensure every `width="100%"` table also carries inline `width:100%`.

    Shopify Email (and some clients) strip the HTML `width` attribute, which collapses
    nested tables to content width — the reported "small, left-aligned boxes". Inline
    style survives, so mirror it there.
    """
    def fix(m: "re.Match") -> str:
        tag = m.group(0)
        if 'width="100%"' not in tag or "width:100%" in tag:
            return tag
        if 'style="' in tag:
            return tag.replace('style="', 'style="width:100%;', 1)
        return tag[:-1] + ' style="width:100%;">'
    return re.sub(r"<table\b[^>]*>", fix, html)


def audit_shopify(html: str) -> list[str]:
    """Return a list of Shopify-Email compliance issues ([] == clean).

    Shopify rejects templates missing the required Liquid variables or containing
    unescaped '&'; Gmail strips base64 images and won't load non-https sources.
    """
    issues = []
    if "{{ unsubscribe_link }}" not in html:
        issues.append("missing required {{ unsubscribe_link }} variable")
    if "{{ open_tracking_block }}" not in html:
        issues.append("missing required {{ open_tracking_block }} variable")
    raw_amp = re.findall(r"&(?!#?[A-Za-z0-9]+;)", html)
    if raw_amp:
        issues.append(f"{len(raw_amp)} unescaped '&' (Shopify rejects — must be &amp;)")
    if "base64," in html:
        issues.append("base64-inlined image(s) — Gmail strips these; host them instead")
    bad_img = [s for s in re.findall(r'<img[^>]+src="([^"]+)"', html) if not s.startswith(("https://", "{{"))]
    if bad_img:
        issues.append(f"{len(bad_img)} non-https image src (won't load in email)")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tournament", required=True, help="Tournament name (e.g. 'Charles Schwab Challenge')")
    ap.add_argument("--year", type=int, default=datetime.now().year)
    ap.add_argument("--link", default=None, help="Full-preview URL the CTA opens (default: auto per-tournament page on golfinthecosmos.com)")
    ap.add_argument("--logo-url", default=LOGO_URL, help="Header logo image URL (hosted; white logo on transparent works best)")
    ap.add_argument("--max-storylines", type=int, default=10, help="Number of storyline cards (default 10)")
    ap.add_argument("--news-count", type=int, default=6, help="How many featured players to show news for (0 disables)")
    ap.add_argument("--climber-count", type=int, default=3, help="How many recent-form climbers to show (0 disables the band)")
    ap.add_argument("--no-network", action="store_true", help="Skip ESPN headshot + news lookups (cache/fallback only)")
    ap.add_argument("--refresh-photos", action="store_true", help="Re-resolve all headshots even if cached")
    ap.add_argument("--refresh-news", action="store_true", help="Re-fetch player news even if cached today")
    ap.add_argument("--out", default=None, help="Output HTML path (default: <slug>_<year>_email.html)")
    ap.add_argument("--slug", default=None, help="Explicit data-file slug (overrides slugified --tournament; matches the schedule slug)")
    args = ap.parse_args()

    slug = args.slug or gt._slugify(args.tournament)
    year = args.year

    # Load weekly-run data (reuse the HTML generator's loaders)
    schedule = gt.load_schedule()
    tournament = gt.find_tournament_in_schedule(args.tournament, schedule) or {"name": args.tournament, "slug": slug}
    player_data = gt.load_player_data(slug, year)
    storylines = gt.load_storylines(slug, year)
    recent_form = gt.load_recent_form(slug, year)
    insights = gt.load_ai_insights(slug, year)
    weather = gt.load_weather_forecast()

    if not player_data.get("odds"):
        print(f"[ERROR] No players_data found for {slug}_{year}. Run the weekly pipeline first.")
        return 1

    players = gt.build_player_list(player_data, storylines, recent_form, year)

    # Photos needed: the lead (featured) player of each storyline card
    needed = []
    for c in insights.get("insights", [])[: args.max_storylines]:
        if c.get("players"):
            needed.append(c["players"][0])
    needed = list(dict.fromkeys(needed))  # de-dup, keep order

    # Trending player (biggest course climber) — also needs a headshot
    trending_player, trending_pts = gt.pick_trending_player(players, year)
    if trending_player:
        print(f"[INFO] Trending player: {trending_player['name']} ({' -> '.join(d for _,_,d in trending_pts)})")
    # Form climbers (improving across their last 3 starts) — each needs a headshot
    climbers = gt.pick_form_climbers(
        players, count=args.climber_count,
        exclude=trending_player["name"] if trending_player else "",
    )
    for c in climbers:
        legs = " -> ".join(f"{gt.shorten_event(e)} {f}" for e, f in c["legs"])
        print(f"[INFO] Form climber: {c['name']} ({legs}, +{c['improvement']})")
    if not climbers:
        print("[INFO] Form climbers: none qualified (section omitted)")

    photo_names = needed + ([trending_player["name"]] if trending_player else [])
    photo_names += [c["name"] for c in climbers]
    photo_names = list(dict.fromkeys(photo_names))

    print(f"[INFO] Resolving {len(photo_names)} player headshots (network={'off' if args.no_network else 'on'})...")
    photos = resolve_headshots(photo_names, use_network=not args.no_network, refresh=args.refresh_photos)
    found = sum(1 for n in photo_names if photos.get(n))
    print(f"[INFO] Headshots resolved: {found}/{len(photo_names)} (missing render as initials avatars)")

    # Player news for the featured (storyline-lead) players, top N
    news_items = []
    if args.news_count > 0:
        news_players = needed[: args.news_count]
        print(f"[INFO] Resolving news for {len(news_players)} players (network={'off' if args.no_network else 'on'})...")
        news_items = resolve_news(news_players, use_network=not args.no_network, refresh=args.refresh_news)
        print(f"[INFO] News headlines resolved: {len(news_items)}/{len(news_players)}")

    link = args.link or default_preview_link(slug, year)
    print(f"[INFO] CTA link: {link}")

    html = build_email_html(
        tournament, players, insights, weather, photos,
        link=link, max_storylines=args.max_storylines, year=year, logo_url=args.logo_url,
        news_items=news_items, trending=(trending_player, trending_pts),
        climbers=climbers,
    )
    html = _force_full_width_tables(html)  # Shopify-safe: inline width:100% on layout tables

    out_path = Path(args.out) if args.out else (ROOT / f"{slug}_{year}_email.html")
    out_path.write_text(html, encoding="utf-8")
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / out_path.name).write_text(html, encoding="utf-8")

    issues = audit_shopify(html)
    print("[AUDIT] Shopify Email compliance:")
    if issues:
        for i in issues:
            print(f"        ✗ FAIL — {i}")
    else:
        print("        ✓ PASS — {{ unsubscribe_link }} + {{ open_tracking_block }} present, no raw '&', all images https")

    print(f"[OK] Email newsletter written:")
    print(f"     {out_path}")
    print(f"     {out_dir / out_path.name}")
    print(f"[REMINDER] The CTA link changes every week — confirm this is the correct page:")
    print(f"           {link}")
    print(f"[NEXT] Open it to preview, then copy the HTML into Shopify Email (custom code).")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
