#!/usr/bin/env python3
"""Inject Recent Form section into each player-detail dropdown in WM Phoenix HTML."""
import html as html_lib
import json
import re
from pathlib import Path

# Script lives in historical/wm_phoenix_open/scripts/; ROOT = historical/wm_phoenix_open
ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT / "wm_phoenix_open_2026.html"
RECENT_FORM_PATH = ROOT / "data" / "wm_phoenix_open_2026_recent_form.json"


def main():
    html = HTML_PATH.read_text(encoding="utf-8")
    recent_form = json.loads(RECENT_FORM_PATH.read_text(encoding="utf-8"))
    recent_form = {k: (v or "—") for k, v in recent_form.items()}

    # Player names in table order (from each player-row .player-name)
    name_pattern = re.compile(
        r'<tr class="player-row[^"]*"[^>]*data-player="player-(\d+)"[^>]*>.*?'
        r'<div class="player-name">([^<]+)<',
        re.DOTALL,
    )
    names_by_id = {}
    for m in name_pattern.finditer(html):
        pid = int(m.group(1))
        name = m.group(2).strip()
        names_by_id[pid] = name

    # Each player-detail row
    row_pattern = re.compile(
        r'<tr class="player-detail" id="player-(\d+)-detail">(.*?)</tr>',
        re.DOTALL,
    )
    replacements = []
    for m in row_pattern.finditer(html):
        num = int(m.group(1))
        content = m.group(2)
        name = names_by_id.get(num, "")
        form_text = recent_form.get(name, "—") if name else "—"
        if not form_text or form_text.strip() == "":
            form_text = "—"
        escaped = html_lib.escape(form_text, quote=False)

        # Insert Recent Form block after second detail-section, before detail-grid close
        new_section = (
            '\n                                        <div class="detail-section">'
            '<div class="detail-section-title" style="margin-top: 20px;">Recent Form</div>'
            f'<div class="recent-form-text">{escaped}</div></div>\n                                    '
        )
        # Pattern: end of second detail-section then detail-grid close then </td>
        needle = "                                    </div>\n                                </div>\n                            </td>"
        insert_pos = content.rfind(needle)
        if insert_pos == -1:
            continue
        # Insert new_section between end of detail-section and </div></div></td>
        new_content = (
            content[:insert_pos]
            + "                                    </div>\n"
            + new_section
            + "                                </div>\n                            </td>"
            + content[insert_pos + len(needle) :]
        )
        full_row = f'<tr class="player-detail" id="player-{num}-detail">{new_content}</tr>'
        replacements.append((m.start(), m.end(), full_row))

    # Apply from end to start so offsets stay valid
    for start, end, replacement in sorted(replacements, key=lambda x: -x[0]):
        html = html[:start] + replacement + html[end:]

    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"✅ Injected Recent Form into {len(replacements)} player dropdowns in {HTML_PATH.name}")


if __name__ == "__main__":
    main()
