#!/usr/bin/env python3
"""
Audit player country codes + flag rendering for a tournament dataset.

Primary use:
- Detect players missing a country
- Detect country codes we can't render a flag for (mapping/ISO issues)
- Detect duplicate player keys (case-only differences)

Usage:
  python3 scripts/audit_player_countries.py \
    --players-data data/amex_2026_players_data.json \
    --out AMEX_COUNTRY_FLAGS_AUDIT.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from country_utils import country_code_to_flag_render, normalize_country_code


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit player country codes + flag rendering")
    parser.add_argument("--players-data", type=Path, required=True, help="Players-data JSON bundle")
    parser.add_argument("--out", type=Path, default=Path("AMEX_COUNTRY_FLAGS_AUDIT.md"), help="Markdown report path")
    args = parser.parse_args()

    raw = _load_json(args.players_data)
    odds = _as_dict(raw.get("odds"))
    players = _as_dict(raw.get("players"))

    # We care about the players we actually display (odds list).
    names = [str(n) for n in odds.keys()]

    missing_country: list[str] = []
    unknown_flag: list[tuple[str, str]] = []
    has_country = 0

    # Detect duplicates that can lead to split data (e.g. "Erik van Rooyen" vs "Erik Van Rooyen").
    norm_to_names: dict[str, list[str]] = defaultdict(list)
    for name in names:
        norm_to_names[name.strip().casefold()].append(name)

    duplicates = {k: v for k, v in norm_to_names.items() if len(v) > 1}

    for name in names:
        info = _as_dict(players.get(name))
        code = normalize_country_code(info.get("country"))

        if not code:
            missing_country.append(name)
            continue

        has_country += 1
        fr = country_code_to_flag_render(code)
        if not fr or not fr.flagcdn_slug:
            unknown_flag.append((name, code))

    # Markdown report
    lines: list[str] = []
    lines.append("# AMEX Country + Flag Audit")
    lines.append("")
    lines.append(f"- Players with odds: **{len(names)}**")
    lines.append(f"- Players with country filled: **{has_country}**")
    lines.append(f"- Players missing country: **{len(missing_country)}**")
    lines.append(f"- Players with unknown/unrenderable flags: **{len(unknown_flag)}**")
    lines.append(f"- Duplicate player keys (case/spacing): **{len(duplicates)}**")
    lines.append("")

    if duplicates:
        lines.append("## Duplicate player keys (case/spacing)")
        lines.append("")
        for _, group in sorted(duplicates.items(), key=lambda kv: (-len(kv[1]), kv[1][0].lower())):
            lines.append(f"- {', '.join(group)}")
        lines.append("")

    if missing_country:
        lines.append("## Missing country (needs enrichment)")
        lines.append("")
        for name in sorted(missing_country, key=str.lower):
            lines.append(f"- {name}")
        lines.append("")

    if unknown_flag:
        lines.append("## Country codes we can't render a flag for (mapping needed)")
        lines.append("")
        for name, code in sorted(unknown_flag, key=lambda x: (x[1], x[0].lower())):
            lines.append(f"- {name}: `{code}`")
        lines.append("")

    args.out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"✅ Wrote audit report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

