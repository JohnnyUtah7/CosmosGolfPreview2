#!/usr/bin/env python3
"""
Audit generated preview content for hallucination risk.

This is NOT a fact-checking oracle. It is a safety net that:
- scans storylines/recent-form for high-risk factual-claim patterns
- checks internal consistency (e.g., "course history: 2025/2024/2023" matches players_data.historical)
- flags "news headline" style recent-form blurbs (not necessarily wrong, but not a result)

Usage:
  python3 scripts/audit_hallucinations.py --html american_express_2026.html --players-data data/amex_2026_players_data.json
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Row:
    name: str
    storyline: str
    recent_form: str


STORYLINE_RE = re.compile(r'<div class="storyline-text">(.*?)</div>', re.S)
RECENT_RE = re.compile(r'<div class="recent-text">(.*?)</div>', re.S)
NAME_RE = re.compile(r'<div class="player-name"><a [^>]*>(.*?)</a></div>', re.S)

# Strip the 🌍 glyph that can be appended to names.
GLOBE_RE = re.compile(r"\s*🌍\s*$")

COURSE_HISTORY_RE = re.compile(
    r"course history:\s*2025:\s*([^,\.]+)(?:,\s*2024:\s*([^,\.]+))?(?:,\s*2023:\s*([^,\.]+))?",
    re.IGNORECASE,
)

NEWS_CYCLE_RE = re.compile(r"the week[’']s news cycle has touched on", re.IGNORECASE)

HIGH_RISK_TERMS = [
    # Strong factual claims we should treat with suspicion unless sourced.
    r"\bdefending champion\b",
    r"\bwon here\b",
    # Avoid matching "won’t" / "won't" which appears in generic copy.
    r"\bwon\b(?![’'])",
    r"\bmajor\b",
    r"\bmasters\b",
    r"\bu\.s\. open\b",
    r"\bpga championship\b",
    r"\bopen champion(ship)?\b",
    r"\bryder cup\b",
    r"\bolympic\b",
    r"\bworld\s*#?\s*1\b",
    r"\bworld no\.\s*1\b",
    r"\bthree[-\s]?time\b",
    r"\bfour[-\s]?time\b",
    r"\bfive[-\s]?time\b",
    r"\bsix[-\s]?time\b",
]
HIGH_RISK_RE = re.compile("|".join(HIGH_RISK_TERMS), re.IGNORECASE)

# Recent form is "result-like" if it contains an event + outcome token.
RESULT_TOKEN_RE = re.compile(r"\b(T\d+|MC|WD|DQ|DNS)\b")


def _extract_rows(html_text: str) -> list[Row]:
    names = [html_lib.unescape(x).strip() for x in NAME_RE.findall(html_text)]
    storylines = [html_lib.unescape(x).strip() for x in STORYLINE_RE.findall(html_text)]
    recent = [html_lib.unescape(x).strip() for x in RECENT_RE.findall(html_text)]

    # The generator should keep these aligned.
    n = min(len(names), len(storylines), len(recent))
    rows: list[Row] = []
    for i in range(n):
        nm = GLOBE_RE.sub("", names[i]).strip()
        rows.append(Row(name=nm, storyline=storylines[i], recent_form=recent[i]))
    return rows


def _load_historical(players_data_path: Path) -> dict[str, dict]:
    raw = json.loads(players_data_path.read_text(encoding="utf-8"))
    hist = raw.get("historical") if isinstance(raw, dict) else {}
    return hist if isinstance(hist, dict) else {}


def _norm(s: str) -> str:
    return (s or "").strip().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit preview content for hallucination risk")
    parser.add_argument("--html", type=Path, required=True, help="Generated HTML file")
    parser.add_argument("--players-data", type=Path, default=None, help="Optional players data JSON for consistency checks")
    parser.add_argument("--sample", type=int, default=12, help="Random sample size for displaying flagged rows")
    parser.add_argument("--seed", type=int, default=2026, help="RNG seed for reproducible sampling")
    args = parser.parse_args()

    html_text = args.html.read_text(encoding="utf-8", errors="replace")
    rows = _extract_rows(html_text)

    print(f"🔎 Hallucination-risk audit for {args.html} ({len(rows)} rows)")

    # 1) High-risk term scan
    high_risk = [r for r in rows if HIGH_RISK_RE.search(r.storyline)]
    news_cycle = [r for r in rows if NEWS_CYCLE_RE.search(r.storyline)]

    print("\n## Storyline scans")
    print(f"- Contains high-risk factual-claim terms: {len(high_risk)}")
    print(f"- Mentions 'week’s news cycle…' sentence: {len(news_cycle)}")

    # 2) Internal consistency: course history snippet vs players_data.historical
    mismatches: list[str] = []
    if args.players_data and args.players_data.exists():
        hist = _load_historical(args.players_data)
        for r in rows:
            mh = COURSE_HISTORY_RE.search(r.storyline)
            if not mh:
                continue
            want = hist.get(r.name)
            if not isinstance(want, dict):
                continue
            got_2025 = mh.group(1).strip() if mh.group(1) else None
            got_2024 = mh.group(2).strip() if mh.group(2) else None
            got_2023 = mh.group(3).strip() if mh.group(3) else None

            for yr, got in [(2025, got_2025), (2024, got_2024), (2023, got_2023)]:
                if got is None:
                    continue
                w = str(want.get(str(yr)) or want.get(yr) or "").strip()
                if w and _norm(w) != _norm(got):
                    mismatches.append(f"{r.name}: history {yr} storyline={got} data={w}")

        print("\n## Internal consistency")
        print(f"- Course-history mismatches vs players_data: {len(mismatches)}")
        if mismatches:
            for line in mismatches[:25]:
                print(f"  - {line}")
            if len(mismatches) > 25:
                print(f"  - … {len(mismatches) - 25} more")

    # 3) Recent form: headline-style vs result-style (not necessarily wrong)
    headline_style = [r for r in rows if r.recent_form.strip() and r.recent_form.strip() != "—" and not RESULT_TOKEN_RE.search(r.recent_form)]
    print("\n## Recent form formatting")
    print(f"- Non-empty but not result-like (headline-ish): {len(headline_style)}")

    # 4) Show random sample of flagged items
    random.seed(args.seed)
    flagged_union = list({r.name: r for r in (high_risk + mismatches and [] or [])}.values())  # keep stable type
    # If there are no high-risk items, sample from news-cycle (since it’s the biggest hallucination surface).
    candidates = high_risk if high_risk else news_cycle
    if candidates:
        sample = candidates[:]
        random.shuffle(sample)
        sample = sample[: max(0, args.sample)]
        print("\n## Sample flagged rows")
        for r in sample:
            blurb = r.storyline
            blurb = re.sub(r"\s+", " ", blurb).strip()
            print(f"- {r.name}: {blurb[:220]}{'…' if len(blurb) > 220 else ''}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

