#!/usr/bin/env python3
"""
Audit AMEX win odds using The Odds API (multi-book).

This is intentionally quota-light:
- 1 request: /sports (list golf events)
- 1 request: /sports/{sport_key}/odds (outrights)

It compares:
- Our current preview win odds (from `data/amex_2026_players.json` if present)
  or the fallback `PLAYERS` list in `scripts/generate_american_express.py`
vs
- Best available odds across all bookmakers returned by The Odds API.

Usage:
  python3 scripts/audit_odds_api_amex.py --tournament "The American Express"
  python3 scripts/audit_odds_api_amex.py --sport-key golf_pga_tour_the_american_express

Outputs:
  - AMEX_ODDS_API_AUDIT.md
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parent.parent
AUDIT_OUT = PROJECT_ROOT / "AMEX_ODDS_API_AUDIT.md"
DATA_PLAYERS_PATH = PROJECT_ROOT / "data" / "amex_2026_players.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_name(name: str) -> str:
    """
    Normalize player names for fuzzy matching across sources.
    - lower
    - strip accents
    - remove punctuation
    - collapse whitespace
    """
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9\\s]", " ", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s


def _norm_american_odds(v: Any) -> int | None:
    """
    Convert an Odds API price to int American odds if possible.
    The Odds API typically returns int already for american format.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s:
        return None
    if re.match(r"^[+-]?\\d{2,6}$", s):
        return int(s)
    return None


def _parse_preview_odds(s: str) -> int | None:
    if s is None:
        return None
    t = str(s).strip()
    if not t or t in {"—", "-", "NA", "TBD"}:
        return None
    if re.match(r"^[+-]\\d{2,6}$", t):
        return int(t)
    # Accept raw ints like "240"
    if re.match(r"^\\d{2,6}$", t):
        return int(t)
    return None


def _load_preview_players() -> list[dict]:
    # Prefer audited JSON
    if DATA_PLAYERS_PATH.exists():
        data = json.loads(DATA_PLAYERS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("players"), list):
            return data["players"]
        if isinstance(data, list):
            return data

    # Fall back to hardcoded list
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.generate_american_express import PLAYERS  # noqa: WPS433

    return PLAYERS


@dataclass(frozen=True)
class OddsComparison:
    player: str
    our_odds: str
    api_best_odds: str
    api_best_book: str
    delta: str


def main() -> int:
    import argparse

    # Add project root to import path for OddsAPIClient
    sys.path.insert(0, str(PROJECT_ROOT))
    from mcp_server.tools.odds import OddsAPIClient  # noqa: WPS433

    parser = argparse.ArgumentParser(description="Audit AMEX win odds via The Odds API")
    parser.add_argument(
        "--tournament",
        default="The American Express",
        help="Tournament name substring to match in The Odds API sports list",
    )
    parser.add_argument(
        "--sport-key",
        default=None,
        help="If provided, skip matching and use this sport key directly",
    )
    parser.add_argument(
        "--output",
        default=str(AUDIT_OUT),
        help="Output markdown path",
    )

    args = parser.parse_args()

    preview_players = _load_preview_players()
    preview_by_norm = {_norm_name(p["name"]): p for p in preview_players}
    preview_names = [p["name"] for p in preview_players]

    with OddsAPIClient() as client:
        sports = client.get_golf_sports()
        if not sports:
            raise SystemExit("No golf sports returned by The Odds API.")

        sport_key = args.sport_key
        sport_title = None

        if not sport_key:
            needle = args.tournament.lower().strip()
            matches = [
                s for s in sports
                if needle in str(s.get("title", "")).lower()
                or needle in str(s.get("description", "")).lower()
                or needle in str(s.get("key", "")).lower()
            ]

            if not matches:
                # Provide a helpful list and exit without making the odds call.
                out_lines = [
                    "# AMEX Odds API Audit (No Match Found)\n",
                    f"- Generated: `{_utc_now_iso()}`\n",
                    f"- Tournament filter: `{args.tournament}`\n",
                    "\n## Available golf events from The Odds API\n",
                    "| Title | Key |\n",
                    "|---|---|\n",
                ]
                for s in sports[:50]:
                    out_lines.append(f"| {s.get('title','')} | `{s.get('key','')}` |\n")
                Path(args.output).write_text("".join(out_lines), encoding="utf-8")
                print(f"⚠️  No sport match found. Wrote: {args.output}")
                print("Provide --sport-key from the list above to run the full odds audit.")
                return 2

            # Choose the first match (sports list is typically already ordered by relevance/availability).
            chosen = matches[0]
            sport_key = chosen.get("key")
            sport_title = chosen.get("title")

        if not sport_key:
            raise SystemExit("Could not determine sport_key to fetch odds.")

        tournament_odds = client.get_tournament_odds(sport_key, markets="outrights", odds_format="american")
        if not tournament_odds:
            raise SystemExit(f"No odds returned for sport_key={sport_key}")

        # Build best odds per API player, tracking best book
        best_api: dict[str, tuple[str, int]] = {}
        for bookmaker in tournament_odds.bookmakers:
            for po in bookmaker.players:
                nm = str(po.player_name).strip()
                val = _norm_american_odds(po.odds)
                if not nm or val is None:
                    continue
                cur = best_api.get(nm)
                if cur is None or val > cur[1]:
                    best_api[nm] = (bookmaker.bookmaker_name, val)

        # Match API names to our preview roster
        comparisons: list[OddsComparison] = []
        missing_in_api: list[str] = []
        matched_api_norms: set[str] = set()

        # Build quick lookup from API normalized name -> (raw_name, book, odds)
        api_by_norm: dict[str, tuple[str, str, int]] = {}
        for api_name, (book, odds_val) in best_api.items():
            api_by_norm[_norm_name(api_name)] = (api_name, book, odds_val)

        for p in preview_players:
            name = p["name"]
            our_val = _parse_preview_odds(p.get("win_odds"))
            our_str = p.get("win_odds", "—")

            api_match = api_by_norm.get(_norm_name(name))
            if not api_match:
                missing_in_api.append(name)
                comparisons.append(
                    OddsComparison(
                        player=name,
                        our_odds=str(our_str),
                        api_best_odds="—",
                        api_best_book="—",
                        delta="—",
                    )
                )
                continue

            api_raw, api_book, api_odds = api_match
            matched_api_norms.add(_norm_name(api_raw))

            # Delta only meaningful if we have numeric odds
            if our_val is None:
                delta = "—"
            else:
                delta = f"{api_odds - our_val:+d}"

            comparisons.append(
                OddsComparison(
                    player=name,
                    our_odds=str(our_str),
                    api_best_odds=f"{api_odds:+d}" if api_odds > 0 else str(api_odds),
                    api_best_book=api_book,
                    delta=delta,
                )
            )

        # Players present in API but not in our preview roster
        extra_api = []
        for api_name, (book, odds_val) in best_api.items():
            if _norm_name(api_name) not in preview_by_norm:
                extra_api.append((api_name, book, odds_val))
        extra_api = sorted(extra_api, key=lambda x: x[2])

        # Write markdown
        lines: list[str] = []
        lines.append("# AMEX Odds API Audit (Multi-book)\n")
        lines.append(f"- Generated: `{_utc_now_iso()}`\n")
        lines.append(f"- Sport key: `{sport_key}`\n")
        if sport_title:
            lines.append(f"- Sport title: `{sport_title}`\n")
        lines.append(f"- Preview roster: **{len(preview_players)}** players\n")
        lines.append(f"- API players (best odds set): **{len(best_api)}** players\n")
        lines.append("\n## Comparison (preview vs best available across books)\n")
        lines.append("| Player | Preview win odds | Best book | Best win odds | Δ (best - preview) |\n")
        lines.append("|---|---:|---|---:|---:|\n")
        for c in comparisons:
            lines.append(f"| {c.player} | {c.our_odds} | {c.api_best_book} | {c.api_best_odds} | {c.delta} |\n")

        lines.append("\n## Coverage notes\n")
        lines.append(f"- Missing in Odds API (from preview roster): **{len(missing_in_api)}**\n")
        if missing_in_api:
            lines.append("  - " + ", ".join(missing_in_api) + "\n")

        lines.append(f"- Present in Odds API but not in preview roster: **{len(extra_api)}**\n")
        if extra_api:
            lines.append("\n### Extra API players (favorites first)\n")
            lines.append("| Player | Best book | Best win odds |\n")
            lines.append("|---|---|---:|\n")
            for nm, book, odds_val in extra_api[:50]:
                odds_str = f"{odds_val:+d}" if odds_val > 0 else str(odds_val)
                lines.append(f"| {nm} | {book} | {odds_str} |\n")

        Path(args.output).write_text("".join(lines), encoding="utf-8")
        print(f"✅ Wrote: {args.output}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

