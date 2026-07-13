# WM Phoenix Open 2026 — HTML & Shopify Audit

**Date:** 2026-02-04

## 1. OWGR and country (fixed)

- **Issue:** Every player showed `USA - OWGR #-` in the HTML.
- **Cause:** The static `wm_phoenix_open_2026.html` was not built from the assembler that injects OWGR; it had placeholder content.
- **Fix:**
  - Added `scripts/inject_owgr_into_html.py` to read `data/wm_phoenix_open_2026_players_data.json` (keys `countries`, `owgr`) and update each `<div class="player-country">` in the HTML.
  - Ran the script; OWGR and country now show correctly (e.g. `USA - OWGR #1`, `JPN - OWGR #15`).
- **Going forward:** After updating `wm_phoenix_open_2026_players_data.json` (e.g. new odds or OWGR), run:
  ```bash
  python scripts/inject_owgr_into_html.py
  ```

## 2. Shopify vs localhost — why you might see “old” content

- **Single source of truth:** The main preview is produced **only** by `generate_tournament_html.py` → `wm_phoenix_open_2026.html` (4-col, dropdowns, exec summary). Do **not** use `assemble_wm_phoenix_html.py` output for Shopify; that script writes the flat wide table to `*_cheatsheet.html` only.
- **Shopify page body limit is 64 KB.** The full HTML is ~1.17 MB and `wm_phoenix_open_2026_shopify.html` is ~204 KB — both get truncated if pasted. Use the **iframe method**: upload `wm_phoenix_open_2026.html` to Shopify Files, then paste the small snippet from `wm_phoenix_open_2026_shopify_embed.html` (with the file URL) into the page. See **docs/DEPLOY_FULL_PREVIEW_TO_SHOPIFY.md**.
- **Reasons Shopify can look different:**
  1. **Wrong file** — Using assembler output (wide table) or an old copy. Fix: Regenerate with `generate_tournament_html.py --shopify` and use the iframe + Files flow.
  2. **Caching** — Browser or Shopify CDN cache. Fix: Hard-refresh (Ctrl+Shift+R / Cmd+Shift+R) or incognito.
  3. **Truncation** — Pasting the full HTML into the page body truncates at 64 KB. Fix: Use iframe + Files (upload full HTML to Files, paste only the iframe snippet on the page).
  4. **No `data/` on Shopify** — The script fetches `data/wm_phoenix_open_2026_matchups.json` for dynamic matchups. On Shopify that URL 404s; the code catches the error and leaves the **embedded** 3-ball table in place, so matchups still show (from the inline HTML).

## 3. What’s inside the file (self-contained)

- **CSS:** Inline in `<style>`. No external stylesheets.
- **Fonts:** Google Fonts (Orbitron, Rajdhani, Share Tech Mono) — load from the internet; work on Shopify.
- **Content:** All visible content is in the HTML:
  - AI insights block and executive summary
  - Crew picks
  - Search box and full betting board (players, odds, past performance 2025/2024/2023, SG, etc.)
  - Daily Matchups tab: 3-ball table is **embedded** in the HTML; 2-ball would only appear if the fetch to `data/...matchups.json` succeeded (e.g. on localhost with that file served).
- **No other external data:** No `src="data/..."` or `href="data/..."`. Only the one `fetch('data/wm_phoenix_open_2026_matchups.json')` for optional dynamic matchups; failure is handled.

## 5. Which script generates the HTML (full vs simple)

- **Full layout (use for deploy):** `python3 scripts/generate_tournament_html.py --tournament "WM Phoenix Open" --year 2026 --output wm_phoenix_open_2026.html --shopify`  
  Produces: Executive summary, AI insights, 4-column table, expandable rows (dropdowns), search, tabs (Tournament Odds / Daily Matchups), PDF button. This is the only output used for the live preview and Shopify.
- **Cheatsheet (flat table only):** `python3 historical/wm_phoenix_open/scripts/assemble_wm_phoenix_html.py --tournament "WM Phoenix Open" --year 2026` (run from project root)  
  Produces: **wm_phoenix_open_2026_cheatsheet.html** — wide table, no dropdowns. Do **not** use for Shopify.

## 6. Deployment checklist

**For Shopify (recommended — iframe + Files, no 64 KB truncation):**

- [ ] Regenerate: `python3 scripts/generate_tournament_html.py --tournament "WM Phoenix Open" --year 2026 --output wm_phoenix_open_2026.html --shopify`
- [ ] Upload **wm_phoenix_open_2026.html** to Shopify **Settings → Files** and copy its URL.
- [ ] Open **wm_phoenix_open_2026_shopify_embed.html**, replace `REPLACE_WITH_PREVIEW_URL` with that URL, then paste the entire snippet into your Shopify page (Custom HTML). Or run `deploy_to_shopify.py --html wm_phoenix_open_2026_shopify_embed.html` after editing the URL in the file.
- [ ] Hard-refresh the page (Ctrl+Shift+R / Cmd+Shift+R) to avoid cached old content.

See **docs/DEPLOY_FULL_PREVIEW_TO_SHOPIFY.md** for full steps. Do not paste the full HTML or `wm_phoenix_open_2026_shopify.html` into the page body — both exceed 64 KB and will truncate.

## 7. Localhost preview — see it in the browser

**Start the server:**
```bash
python3 scripts/preview_server.py --default wm_phoenix_open_2026.html
```
If port 8000 is in use: `--port 8765` (or any free port).

**URLs:**
- **Main:** http://localhost:8000/ (redirects to WM Phoenix) or http://localhost:8000/wm_phoenix_open_2026.html
- **Direct:** Use the port shown in the terminal (e.g. http://localhost:8765/wm_phoenix_open_2026.html)

**Matchups on localhost:** The script fetches `data/wm_phoenix_open_2026_matchups.json` from the same origin. With the server serving from the project root, `data/` is at http://localhost:PORT/data/..., so the fetch succeeds and the Daily Matchups tab shows the same 3-ball data (embedded table is the fallback when fetch fails, e.g. on Shopify).

---

## 8. Cross-the-board verification checklist

Use this when auditing the HTML (localhost + Shopify).

| Check | What to verify |
|-------|----------------|
| **Tabs** | “Tournament Odds” is default; “Daily Matchups” switches to 3-ball table. |
| **Search** | Typing in the search box filters the player table; clear to see all again. |
| **Expand** | Click a player row to expand SG / predictions / course fit; click again or another row to collapse. |
| **Matchups** | Daily Matchups tab shows 3-balls (tee times, players, odds). On localhost, data can come from JSON; on Shopify, embedded table is used. |
| **Responsive** | Resize to ~768px: storyline column hides, smaller type; at ~1200px some SG columns hide. Table scrolls horizontally on small screens. |
| **Fonts** | Orbitron (headings), Rajdhani (body), Share Tech Mono (labels/odds) load from Google Fonts. |
| **Images** | Logo and crew photos from Shopify CDN; course image uses WM_teeshot.avif on Shopify CDN (set in generated HTML). |
| **No console errors** | Open DevTools → Console; no red errors. Fetch 404 for matchups on Shopify is caught and ignored. |

---

## 9. V2 paste-ready file

**wm_phoenix_open_2026_v2.html** — Streamlined build for copy-paste into Shopify: same light-mode design, betting preview header, WM image, crew picks, exec summary, **compact AI insight cards**, search, Tournament Odds / Daily Matchups tabs, 4-col table with expandable dropdowns, and **Download PDF** + print script. No event-info grid; insight cards use a lighter layout. Generated with:

```bash
python3 scripts/generate_tournament_html.py --tournament "WM Phoenix Open" --year 2026 --v2
```

Use `--v2-max-players 40` (or lower) if you need a smaller file for a strict paste limit. Then paste the entire contents of `wm_phoenix_open_2026_v2.html` into your Shopify page (Custom HTML).

## 10. Files involved

| File | Purpose |
|------|--------|
| `wm_phoenix_open_2026.html` | Main preview (4-col, dropdowns, exec summary). Upload to Shopify Files; use with iframe snippet. |
| `wm_phoenix_open_2026_v2.html` | Paste-ready v2: compact design, PDF button, insight cards; generate with `--v2`. |
| `wm_phoenix_open_2026_shopify_embed.html` | Small iframe snippet; paste into Shopify page after replacing the preview URL. |
| `wm_phoenix_open_2026_cheatsheet.html` | Flat wide table from `assemble_wm_phoenix_html.py`; do not use for Shopify. |
| `data/wm_phoenix_open_2026_players_data.json` | Source for OWGR and country (and odds, historical, etc.) when running `inject_owgr_into_html.py`. |
| `data/wm_phoenix_open_2026_matchups.json` | Optional: used on localhost to populate Daily Matchups; embedded table is fallback. |
| `scripts/inject_owgr_into_html.py` | Updates OWGR and country in the HTML from the JSON. |
| `scripts/preview_server.py` | Local preview server to test the HTML. |
