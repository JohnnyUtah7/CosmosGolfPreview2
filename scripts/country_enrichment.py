"""
Country enrichment for player datasets.

Goal:
- Given a players-data JSON bundle (like `data/amex_2026_players_data.json`),
  fill missing `players[name].country` using the BallDontLie PGA API.

Design:
- Prefer a low-request approach: fetch a paginated list of PGA players once,
  then match by normalized full name.
- Apply manual overrides first (data/player_country_overrides.json).
- Optionally fall back to per-player search for remaining misses (more requests).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import time

from scripts.country_utils import normalize_country_code

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _norm_name(s: str) -> str:
    s = (s or "").strip().casefold()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""

    # Join runs of single-letter initials to improve matching:
    # "j t poston" -> "jt poston", "a j ewart" -> "aj ewart", "s h kim" -> "sh kim"
    tokens = s.split()
    out: list[str] = []
    buf = ""
    for tok in tokens:
        if len(tok) == 1 and tok.isalnum():
            buf += tok
            continue
        if buf:
            out.append(buf)
            buf = ""
        out.append(tok)
    if buf:
        out.append(buf)
    return " ".join(out)


@dataclass(frozen=True)
class EnrichResult:
    updated: int
    already_had_country: int
    unresolved: int
    used_overrides: int


# Wikipedia demonym -> our 3-letter codes (golf/OWGR style).
_DEMONYM_TO_CODE: dict[str, str] = {
    "australian": "AUS",
    "american": "USA",
    "canadian": "CAN",
    "english": "ENG",
    "scottish": "SCO",
    "welsh": "WAL",
    "northern irish": "NIR",
    "irish": "IRL",
    "south african": "RSA",
    "german": "GER",
    "french": "FRA",
    "spanish": "ESP",
    "swedish": "SWE",
    "norwegian": "NOR",
    "danish": "DEN",
    "finnish": "FIN",
    "japanese": "JPN",
    "korean": "KOR",
    "chinese": "CHN",
    "taiwanese": "TPE",
    "indian": "IND",
    "argentine": "ARG",
    "colombian": "COL",
    "chilean": "CHI",
    "mexican": "MEX",
    "new zealand": "NZL",
    "new zealand-born": "NZL",
    "belgian": "BEL",
    "dutch": "NED",
    "swiss": "SUI",
    "austrian": "AUT",
    "venezuelan": "VEN",
    "puerto rican": "PRI",
}


def _guess_country_from_text(text: str) -> str:
    """
    Best-effort guess from Wikipedia description/extract.
    Example: "Australian professional golfer" -> AUS.
    """
    t = unescape((text or "")).strip().lower()
    if not t:
        return ""

    # Prefer longer keys first (e.g. "northern irish" before "irish").
    for dem, code in sorted(_DEMONYM_TO_CODE.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(rf"\b{re.escape(dem)}\b", t):
            return code
    return ""


def _wiki_title_for_player(client: "httpx.Client", name: str) -> str:
    q = f"{name} golfer"
    resp = client.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": q,
            "srlimit": 1,
            "format": "json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    hits = (((data or {}).get("query") or {}).get("search") or [])
    if not hits:
        return ""
    return str(hits[0].get("title") or "").strip()


def _wiki_country_code_for_player(client: "httpx.Client", name: str) -> str:
    """
    Best-effort Wikipedia-based country lookup.
    Returns our 3-letter code when possible, else "".
    """
    title = _wiki_title_for_player(client, name)
    if not title:
        return ""

    resp = client.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_"),
        headers={"Accept": "application/json"},
    )
    if resp.status_code >= 400:
        return ""
    try:
        summary = resp.json()
    except Exception:
        return ""
    if not isinstance(summary, dict):
        return ""

    desc = str(summary.get("description") or "").strip()
    extract = str(summary.get("extract") or "").strip()

    code = _guess_country_from_text(desc) or _guess_country_from_text(extract)
    return normalize_country_code(code)


def load_overrides(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k): normalize_country_code(str(v)) for k, v in raw.items() if normalize_country_code(str(v))}
    except Exception:
        return {}
    return {}


def enrich_players_data_countries(
    *,
    players_data_path: Path,
    overrides_path: Optional[Path] = None,
    api_key: Optional[str] = None,
    max_pages: int = 12,
    fallback_search: bool = True,
    min_search_score: float = 0.86,
    web_fallback: bool = True,
    web_cache_path: Optional[Path] = None,
    force_web_fallback: bool = False,
    web_sleep_seconds: float = 0.25,
) -> EnrichResult:
    """
    Enrich missing countries in-place in `players_data_path`.

    Uses BallDontLie PGA API when available (best quality, few requests).
    If the API key is missing or requests fail, optionally falls back to Wikipedia.
    """
    load_dotenv()
    key = (api_key or "").strip() or os.getenv("BALLDONTLIE_API_KEY", "").strip()
    has_bdl = bool(key)
    if not has_bdl and not web_fallback:
        raise RuntimeError("BALLDONTLIE_API_KEY not set (and web_fallback is disabled)")

    raw = json.loads(players_data_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("players-data JSON must be an object")

    odds = _as_dict(raw.get("odds"))
    players = _as_dict(raw.get("players"))
    raw["players"] = players

    names = [str(n) for n in odds.keys()]
    overrides = load_overrides(overrides_path) if overrides_path else {}

    # Local import to avoid requiring the key unless we actually enrich.
    from mcp_server.tools.pga import PGAAPIClient  # noqa: WPS433

    updated = 0
    already = 0
    unresolved = 0
    used_overrides = 0

    # 1) Apply overrides first (always wins)
    for name in names:
        if name in overrides:
            info = _as_dict(players.get(name))
            existing = normalize_country_code(info.get("country"))
            if existing != overrides[name]:
                info["country"] = overrides[name]
                players[name] = info
                updated += 1
                used_overrides += 1

    missing_after_bdl: list[str] = []
    bdl_failed = False

    # 2) Try BallDontLie if available.
    if has_bdl:
        # Local import to avoid requiring the key unless we actually enrich.
        from mcp_server.tools.pga import PGAAPIClient  # noqa: WPS433

        try:
            with PGAAPIClient(api_key=key) as client:
                api_players = client.get_all_players_paginated(max_pages=max_pages)

                norm_to_code: dict[str, str] = {}
                for p in api_players:
                    first = str(p.get("first_name") or "").strip()
                    last = str(p.get("last_name") or "").strip()
                    full = " ".join(x for x in [first, last] if x).strip() or str(p.get("name") or "").strip()
                    code = normalize_country_code(p.get("country_code") or p.get("countryCode") or "")
                    if not full or not code:
                        continue
                    norm_to_code[_norm_name(full)] = code

                # Fill missing countries from the map
                missing_after_map: list[str] = []
                for name in names:
                    info = _as_dict(players.get(name))
                    existing = normalize_country_code(info.get("country"))
                    if existing:
                        already += 1
                        continue

                    code = norm_to_code.get(_norm_name(name))
                    if code:
                        info["country"] = code
                        players[name] = info
                        updated += 1
                    else:
                        missing_after_map.append(name)

                # Optional: per-player search for remaining misses (more requests)
                if fallback_search and missing_after_map:
                    import difflib

                    for name in missing_after_map:
                        try:
                            resp = client.get_players(search=name, per_page=25)
                            candidates = resp.get("data", []) if isinstance(resp, dict) else []
                            if not isinstance(candidates, list) or not candidates:
                                missing_after_bdl.append(name)
                                continue
                        except Exception:
                            missing_after_bdl.append(name)
                            continue

                        target = _norm_name(name)
                        best_score = 0.0
                        best_code = ""
                        for c in candidates:
                            first = str(c.get("first_name") or "").strip()
                            last = str(c.get("last_name") or "").strip()
                            full = " ".join(x for x in [first, last] if x).strip() or str(c.get("name") or "").strip()
                            cand = _norm_name(full)
                            if not cand:
                                continue
                            score = difflib.SequenceMatcher(a=target, b=cand).ratio()
                            code = normalize_country_code(c.get("country_code") or c.get("countryCode") or "")
                            if code and score > best_score:
                                best_score = score
                                best_code = code

                        if best_code and best_score >= min_search_score:
                            info = _as_dict(players.get(name))
                            info["country"] = best_code
                            players[name] = info
                            updated += 1
                        else:
                            missing_after_bdl.append(name)
                else:
                    missing_after_bdl = list(missing_after_map)
        except Exception:
            # If BallDontLie fails (quota, etc.), fall back to web for all missing.
            bdl_failed = True
            missing_after_bdl = [
                name for name in names if not normalize_country_code(_as_dict(players.get(name)).get("country"))
            ]
    else:
        missing_after_bdl = [
            name for name in names if not normalize_country_code(_as_dict(players.get(name)).get("country"))
        ]

    # 3) Web fallback (Wikipedia) with cache.
    # By default, only use the web fallback when BallDontLie isn't available or failed.
    # If `force_web_fallback` is True, use it to fill any remaining misses too.
    if web_fallback and missing_after_bdl and (force_web_fallback or (not has_bdl or bdl_failed)):
        if httpx is None:
            unresolved += len(missing_after_bdl)
        else:
            cache_path = web_cache_path or (players_data_path.parent / "player_country_cache.json")
            cache: dict[str, str] = {}
            if cache_path.exists():
                try:
                    raw_cache = json.loads(cache_path.read_text(encoding="utf-8"))
                    if isinstance(raw_cache, dict):
                        cache = {str(k): normalize_country_code(str(v)) for k, v in raw_cache.items()}
                except Exception:
                    cache = {}

            cache_dirty = False
            wiki_rate_limited = False
            with httpx.Client(timeout=20.0, headers={"User-Agent": "CosmosGolfBetting/1.0 (country-enrichment)"}) as c:
                for name in missing_after_bdl:
                    info = _as_dict(players.get(name))
                    if normalize_country_code(info.get("country")):
                        continue

                    cached = normalize_country_code(cache.get(name))
                    if cached:
                        info["country"] = cached
                        players[name] = info
                        updated += 1
                        continue

                    if wiki_rate_limited:
                        unresolved += 1
                        continue

                    try:
                        code = _wiki_country_code_for_player(c, name)
                    except Exception as e:
                        msg = str(e)
                        if " 429 " in msg or "too many requests" in msg.lower():
                            wiki_rate_limited = True
                        unresolved += 1
                        continue
                    if code:
                        info["country"] = code
                        players[name] = info
                        updated += 1
                        cache[name] = code
                        cache_dirty = True
                    else:
                        unresolved += 1

                    if web_sleep_seconds and web_sleep_seconds > 0:
                        time.sleep(float(web_sleep_seconds))

            if cache_dirty:
                cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        unresolved += len(missing_after_bdl)

    players_data_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return EnrichResult(
        updated=updated,
        already_had_country=already,
        unresolved=unresolved,
        used_overrides=used_overrides,
    )

