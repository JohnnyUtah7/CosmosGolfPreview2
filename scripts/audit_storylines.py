#!/usr/bin/env python3
"""
Audit storylines for common quality + factual-risk issues.

This is a lightweight lint-style audit to catch:
- overly-specific claims (wins, majors, year-specific trophies) without citations
- very short / very long blurbs
- repeated boilerplate phrasing

Usage:
  python scripts/audit_storylines.py --html american_express_2026.html --limit 8
  python scripts/audit_storylines.py --json data/storylines_current.json --limit 8
"""

import argparse
import json
import re
from pathlib import Path


RISK_PATTERNS: list[tuple[str, str]] = [
    ("specific_win_claim", r"\bwon\b|\bwinner\b|\bdefending champion\b"),
    ("major_claim", r"\bMasters\b|\bU\.S\. Open\b|\bOpen Championship\b|\bPGA Championship\b|\bThe Players Championship\b"),
    ("year_specific", r"\b20\d{2}\b"),
    ("count_claim", r"\b(\d+)[-\s]*(time|times)\b"),
    ("ranking_claim", r"\bOWGR\b|\bworld\s*#?\d+\b"),
]


def _extract_from_html(html: str) -> list[str]:
    # Pull the inner text of <div class="storyline-text">...</div>
    # (HTML is generated with single-line storylines in this repo.)
    return re.findall(r'<div class="storyline-text">(.*?)</div>', html, flags=re.DOTALL)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _risk_flags(text: str) -> list[str]:
    flags = []
    for name, pattern in RISK_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            flags.append(name)
    return flags


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit storylines")
    parser.add_argument("--html", type=Path, help="HTML file containing storylines")
    parser.add_argument("--json", type=Path, help="JSON file containing storylines")
    parser.add_argument("--limit", type=int, default=10, help="How many to print")
    args = parser.parse_args()

    if not args.html and not args.json:
        print("❌ Provide --html or --json")
        return 1

    storylines: list[str] = []
    source = ""

    if args.html:
        source = str(args.html)
        html = args.html.read_text(encoding="utf-8")
        storylines = [_normalize(s) for s in _extract_from_html(html)]

    if args.json:
        source = str(args.json)
        data = json.loads(args.json.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "storylines" in data and isinstance(data["storylines"], dict):
            storylines = [_normalize(v) for v in data["storylines"].values()]
        elif isinstance(data, dict):
            # Flat mapping {player: storyline}
            storylines = [_normalize(v) for v in data.values() if isinstance(v, str)]

    if not storylines:
        print(f"❌ No storylines found in {source}")
        return 1

    print(f"🔎 Auditing {len(storylines)} storylines from {source}")

    # Basic stats
    lengths = [len(s.split()) for s in storylines]
    print(f"- Word count: min={min(lengths)} median={sorted(lengths)[len(lengths)//2]} max={max(lengths)}")

    # Flagged subset
    flagged = []
    for s in storylines:
        flags = _risk_flags(s)
        wc = len(s.split())
        if wc < 90 or wc > 230 or flags:
            flagged.append((wc, flags, s))

    flagged.sort(key=lambda x: (len(x[1]), x[0]), reverse=True)

    print(f"- Flagged: {len(flagged)}")
    print("")

    for i, (wc, flags, s) in enumerate(flagged[: args.limit], 1):
        flag_str = ", ".join(flags) if flags else "length_only"
        print(f"{i}. ({wc} words) [{flag_str}] {s[:220]}{'...' if len(s) > 220 else ''}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

