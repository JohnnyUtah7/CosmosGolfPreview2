#!/usr/bin/env python3
"""
Fill missing player countries in a players-data bundle.

This uses the BallDontLie PGA API (via `BALLDONTLIE_API_KEY`) when available.
It only updates players with missing/blank `country` unless you pass --force.

Usage:
  python3 scripts/enrich_player_countries.py \
    --players-data data/amex_2026_players_data.json

Optional:
  python3 scripts/enrich_player_countries.py \
    --players-data data/amex_2026_players_data.json \
    --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from country_utils import normalize_country_code


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _norm_name(s: str) -> str:
    s = s.strip().casefold()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass(frozen=True)
class Match:
    country_code: str
    country: Optional[str]
    score: float


def _best_match_for_name(name: str, candidates: list[dict[str, Any]]) -> Optional[Match]:
    """Choose the best API match for a given player name."""
    target = _norm_name(name)
    if not target or not candidates:
        return None

    best: Optional[Match] = None

    # Lazy import so script can still run without network/key (it will just exit early).
    import difflib

    for c in candidates:
        first = str(c.get("first_name") or "").strip()
        last = str(c.get("last_name") or "").strip()
        full = " ".join(p for p in [first, last] if p).strip() or str(c.get("name") or "").strip()
        cand_name = _norm_name(full)
        if not cand_name:
            continue

        score = difflib.SequenceMatcher(a=target, b=cand_name).ratio()

        code = normalize_country_code(c.get("country_code") or c.get("countryCode") or c.get("country"))
        country = str(c.get("country") or "").strip() or None

        if not code:
            continue

        m = Match(country_code=code, country=country, score=score)
        if best is None or m.score > best.score:
            best = m

    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich missing player countries via BallDontLie PGA API")
    parser.add_argument("--players-data", type=Path, required=True, help="Players-data JSON bundle to update")
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="BallDontLie API key (optional; otherwise uses BALLDONTLIE_API_KEY from env/.env).",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=Path("data/player_country_overrides.json"),
        help="Optional overrides JSON mapping player name -> country code",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing countries with API results")
    parser.add_argument("--min-score", type=float, default=0.86, help="Min name-match score to accept")
    parser.add_argument("--limit", type=int, default=0, help="Limit players processed (0 = all)")
    args = parser.parse_args()

    # Load env vars from local `.env` if present (matches repo conventions).
    load_dotenv()

    api_key = (args.api_key or "").strip() or os.getenv("BALLDONTLIE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("BALLDONTLIE_API_KEY not set; cannot enrich countries.")

    # Local import so a missing key doesn't break other scripts.
    from mcp_server.tools.pga import PGAAPIClient  # noqa: WPS433

    raw = _load_json(args.players_data)
    odds = _as_dict(raw.get("odds"))
    players = _as_dict(raw.get("players"))
    raw["players"] = players

    overrides: dict[str, str] = {}
    if args.overrides.exists():
        try:
            o = json.loads(args.overrides.read_text(encoding="utf-8"))
            if isinstance(o, dict):
                overrides = {str(k): str(v) for k, v in o.items()}
        except Exception:
            overrides = {}

    names = [str(n) for n in odds.keys()]
    if args.limit and args.limit > 0:
        names = names[: args.limit]

    updated = 0
    skipped = 0
    unresolved: list[str] = []
    low_confidence: list[tuple[str, float]] = []

    with PGAAPIClient(api_key=api_key) as client:
        for name in names:
            info = _as_dict(players.get(name))
            existing = normalize_country_code(info.get("country"))

            if not args.force and existing:
                skipped += 1
                continue

            # Apply manual override if present (always wins).
            if name in overrides and normalize_country_code(overrides[name]):
                info["country"] = normalize_country_code(overrides[name])
                players[name] = info
                updated += 1
                continue

            # Query API; pull multiple results and choose best name match.
            try:
                resp = client.get_players(search=name, per_page=25)
                candidates = resp.get("data", []) if isinstance(resp, dict) else []
                if not isinstance(candidates, list) or not candidates:
                    unresolved.append(name)
                    continue
            except Exception:
                unresolved.append(name)
                continue

            m = _best_match_for_name(name, candidates)
            if not m:
                unresolved.append(name)
                continue

            if m.score < args.min_score:
                low_confidence.append((name, m.score))
                continue

            info["country"] = m.country_code
            players[name] = info
            updated += 1

    _dump_json(args.players_data, raw)
    print(f"✅ Updated {updated} player countries in {args.players_data}")
    print(f"↪️  Skipped (already had country): {skipped}" if not args.force else f"↪️  Skipped: {skipped}")
    print(f"⚠️  Unresolved: {len(unresolved)}")
    print(f"⚠️  Low-confidence (score < {args.min_score}): {len(low_confidence)}")

    if unresolved:
        print("\nUnresolved (first 30):")
        for n in unresolved[:30]:
            print(f"- {n}")

    if low_confidence:
        print("\nLow-confidence (first 30):")
        for n, s in sorted(low_confidence, key=lambda x: x[1])[:30]:
            print(f"- {n}: {s:.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

