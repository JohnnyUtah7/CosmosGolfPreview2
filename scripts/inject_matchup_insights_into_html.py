#!/usr/bin/env python3
"""
Inject AI matchup insights (summary + per-group picks) into wm_phoenix_open_2026.html.

Reads data/wm_phoenix_open_2026_matchup_insights.json and replaces the placeholder
<!-- MATCHUP_AI_INSIGHTS --> inside the Daily Matchups tab with the rendered block.

Run after generate_matchup_ai_insights.py.

Usage:
    python scripts/inject_matchup_insights_into_html.py
    python scripts/inject_matchup_insights_into_html.py --html wm_phoenix_open_2026.html --insights data/wm_phoenix_open_2026_matchup_insights.json
"""
import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def build_matchup_insights_html(insights: dict) -> str:
    """Build the AI matchup analysis block HTML."""
    summary = insights.get("summary", "").strip()
    picks = insights.get("round_1_3ball", [])

    parts = [
        '<div class="matchup-ai-section">',
        '  <h3 class="matchup-ai-heading">AI Matchup Analysis &amp; Picks</h3>',
    ]
    if summary:
        parts.append('  <div class="matchup-ai-summary">' + html.escape(summary) + '</div>')
    elif not picks:
        parts.append('  <div class="matchup-ai-summary">Run <code>python scripts/generate_matchup_ai_insights.py</code> then <code>inject_matchup_insights_into_html.py</code> to generate AI analysis and picks for Round 1 3-balls and post-cut angles.</div>')
    if picks:
        parts.append('  <div class="matchup-ai-picks">')
        for p in picks:
            grp = p.get("group", "")
            pick = p.get("pick", "")
            conf = p.get("confidence", "Lean")
            analysis = (p.get("analysis") or "").strip()
            conf_class = "strong" if conf == "Strong" else ("value" if conf == "Value" else "lean")
            parts.append('    <div class="matchup-ai-card">')
            parts.append(f'      <div class="matchup-ai-card-header">Group {grp} · <span class="matchup-ai-pick-name">{html.escape(pick)}</span> <span class="matchup-ai-confidence matchup-ai-' + conf_class + '">' + html.escape(conf) + '</span></div>')
            if analysis:
                parts.append('      <div class="matchup-ai-analysis">' + html.escape(analysis) + '</div>')
            parts.append('    </div>')
        parts.append('  </div>')
    parts.append('</div>')
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject matchup AI insights into WM Phoenix HTML")
    parser.add_argument("--html", type=Path, default=ROOT / "wm_phoenix_open_2026.html")
    parser.add_argument("--insights", type=Path, default=ROOT / "data" / "wm_phoenix_open_2026_matchup_insights.json")
    args = parser.parse_args()

    if not args.insights.exists():
        print(f"⚠️ No insights file at {args.insights}. Run generate_matchup_ai_insights.py first.")
        # Inject placeholder so the section exists
        insights = {"summary": "", "round_1_3ball": []}
    else:
        insights = json.loads(args.insights.read_text(encoding="utf-8"))

    html_content = args.html.read_text(encoding="utf-8")
    placeholder = "<!-- MATCHUP_AI_INSIGHTS -->"
    if placeholder not in html_content:
        print("⚠️ Placeholder <!-- MATCHUP_AI_INSIGHTS --> not found in HTML. Add it inside the Daily Matchups tab.")
        return 1

    block = build_matchup_insights_html(insights)
    # Replace placeholder or existing .matchup-ai-section block
    if placeholder in html_content:
        new_html = html_content.replace(placeholder, block)
    else:
        # Replace existing block: from <div class="matchup-ai-section"> to just before next <div class="matchups-section">
        pattern = re.compile(
            r'<div class="matchup-ai-section">.*?(?=\n<div class="matchups-section")',
            re.DOTALL,
        )
        if pattern.search(html_content):
            new_html = pattern.sub(block + "\n", html_content)
        else:
            print("⚠️ No placeholder or existing .matchup-ai-section found.")
            return 1
    args.html.write_text(new_html, encoding="utf-8")
    print(f"✅ Injected matchup AI block into {args.html.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
