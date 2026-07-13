#!/usr/bin/env python3
"""
Update The American Express 2026 HTML (safe version).

Why this exists:
- An older version injected emoji flags by string replace.
- England/Scotland often rendered as a black flag emoji (🏴) depending on platform.

What this does now:
- Updates the placeholder course image (if present)
- Optionally upgrades older HTML where `<div class="player-country">` contains only
  plain country codes like `ENG · OWGR #14` into FlagCDN-backed flag images.
- If the HTML already contains `<img class="flag-img" ...>`, it does nothing to
  player-country blocks (so it won't re-break anything).
"""

from __future__ import annotations

import re
from pathlib import Path

from country_utils import country_display_html


HTML_FILE = Path(__file__).parent.parent / "american_express_2026.html"

OLD_IMAGE = "https://via.placeholder.com/1200x600/0a0a0f/00d4ff?text=PGA+West+Stadium+Course+-+The+American+Express"
NEW_IMAGE = "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/amex.webp?v=1768848048"


def main() -> int:
    html_content = HTML_FILE.read_text(encoding="utf-8")

    # Replace placeholder course image with American Express image
    html_content = html_content.replace(OLD_IMAGE, NEW_IMAGE)

    # If flags are already images, don't touch player-country blocks.
    if 'class="flag-img"' not in html_content:
        _PLAYER_COUNTRY_RE = re.compile(
            r'(<div class="player-country">)(.*?)(</div>)',
            re.IGNORECASE | re.DOTALL,
        )
        _OWGR_RE = re.compile(r"\bOWGR\s*#\s*(\d+)\b", re.IGNORECASE)

        def _rewrite_country(m: re.Match) -> str:
            start, inner, end = m.group(1), m.group(2), m.group(3)
            txt = re.sub(r"<[^>]+>", "", inner).strip()
            if not txt or txt == "—":
                return m.group(0)

            code = ""
            owgr = ""

            # Common formats:
            # - "USA · OWGR #1"
            # - "ENG"
            parts = [p.strip() for p in re.split(r"[·•|]", txt) if p.strip()]
            if parts:
                code = parts[0].split()[0].strip().upper()

            ow = _OWGR_RE.search(txt)
            if ow:
                owgr = ow.group(1)

            rendered = country_display_html(country_code=code, owgr=owgr)
            return f"{start}{rendered}{end}"

        html_content = _PLAYER_COUNTRY_RE.sub(_rewrite_country, html_content)

    HTML_FILE.write_text(html_content, encoding="utf-8")

    print("✅ Updated American Express 2026 HTML!")
    print("   - Country flags: FlagCDN images (ENG/SCO fixed; no black emoji flags)")
    print("   - Replaced course image (if placeholder present)")
    print(f"   - File: {HTML_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

