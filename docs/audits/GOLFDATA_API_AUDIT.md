# Data Golf (Golfdata) API – Audit Report

**Date:** February 4, 2026  
**Scope:** MCP server Data Golf integration, WM Phoenix Open weekly tournament data, and player dropdown fields.

---

## 1. API status: **LIVE AND WORKING**

The **Data Golf API** (referred to in config as “golfdata”) is the same as the `mcp_server` **Data Golf** client (`mcp_server/tools/datagolf.py`). It uses:

- **Config:** `DATAGOLF_API_KEY` and `DATAGOLF_API_BASE_URL = "https://feeds.datagolf.com"` in `mcp_server/config.py`
- **.env:** `DATAGOLF_API_KEY` (see `.env.example`)

**Verification:** `python3 scripts/test_datagolf_api.py` was run successfully. Results:

| Test | Result |
|------|--------|
| Player list | 3,398 players |
| DG rankings | 500 ranked |
| Current field updates | 123 players (PGA) |
| Pre-tournament predictions | WM Phoenix Open, 123 players, last updated 2026-02-03 |
| Skill ratings (SG) | 445 players |
| Course decompositions | TPC Scottsdale (WM Phoenix) |
| Outright odds | 123 players, DraftKings + DG fair values |
| Tour schedule | 47 events in 2026 |

**Conclusion:** The Data Golf API is live and correctly used by the MCP server package. The Cursor MCP panel only lists external servers (e.g. Supabase, browser); the in-repo `mcp_server` is a Python package used by scripts (e.g. `test_datagolf_api.py`, `generate_storylines_with_datagolf.py`), not a separate Cursor MCP process.

---

## 2. What populates recent form and odds for WM Phoenix

### Current sources (as of this audit)

| Data | Current source | Data Golf used? |
|------|----------------|------------------|
| **Odds** (win, top 5, top 10) | **Data Golf** via `scripts/refresh_odds_from_datagolf.py` → `players_data.json` (DraftKings lines from DG). Manual DraftKings paste / `import_draftkings_odds` is legacy fallback. | Yes – primary source. |
| **Recent form** | `scripts/refresh_recent_form.py` (BallDontLie PGA API) → `data/player_recent_form_cache.json`; then `scripts/generate_wm_phoenix_recent_form.py` → `data/wm_phoenix_open_2026_recent_form.json` | No – DG has historical event finishes; not yet used for recent form. |
| **Strokes gained** | `data/player_strokes_gained.json` (source: “Data Golf 2026 YTD”) → `scripts/apply_strokes_gained_to_html.py` → HTML | Yes – SG data is from Data Golf (script that writes this file uses DG skill ratings). |

To have Data Golf **directly** populate odds and recent form for the weekly tournament, two scripts were added and are documented below.

---

## 3. Scripts added so Data Golf populates the weekly tournament

### 3.1 Refresh odds from Data Golf

**Script:** `scripts/refresh_odds_from_datagolf.py`

- Calls Data Golf `get_outright_odds()` for `win`, `top_5`, `top_10` (PGA = current event, e.g. WM Phoenix).
- Uses the **DraftKings** odds from the DG response (DG aggregates books).
- Updates `data/wm_phoenix_open_2026_players_data.json` (or the tournament file you pass) so the “odds” section and `data_sources.odds` reflect Data Golf as the source.

**Usage:**

```bash
python3 scripts/refresh_odds_from_datagolf.py
# or for a specific tournament data file:
python3 scripts/refresh_odds_from_datagolf.py --players-data data/wm_phoenix_open_2026_players_data.json
```

### 3.2 Refresh recent form from Data Golf

**Script:** `scripts/refresh_recent_form_from_datagolf.py`

- Tries Data Golf `get_event_finishes(tour="pga", year=2025)` and `year=2026` to build “last 4 events” strings.
- If the historical-event-data endpoint is unavailable (e.g. 404 on your plan), the script falls back to the existing **master cache** and still writes the tournament recent-form file so the pipeline is unchanged.
- Updates `data/player_recent_form_cache.json` when DG returns data, and writes `data/wm_phoenix_open_2026_recent_form.json` (or the path you pass).

**Usage:**

```bash
python3 scripts/refresh_recent_form_from_datagolf.py --tournament "WM Phoenix Open" --year 2026
```

**Note:** The Data Golf `historical-event-data/finishes` endpoint returned 404 in testing; recent form for WM Phoenix therefore remains populated from the existing cache (BallDontLie + manual updates). If your Data Golf plan includes historical event data, the script will use it when available.

After running these, regenerate the HTML (e.g. `assemble_wm_phoenix_html.py` or your existing flow) so the preview shows DG-sourced odds and recent form.

---

## 4. Player “dropdown” and row fields (what’s shown per player)

The table is one row per player; the only expandable “dropdown” is the **Strokes Gained** panel. Below are **all data fields** shown for each player.

### 4.1 Main table row (always visible)

| Field | Source | Populates? |
|-------|--------|------------|
| **#** | Rank by win odds | Yes |
| **Player name** | `players_data.odds` keys | Yes (link to Google search) |
| **Country** | `players_data.countries` | Yes (e.g. USA, JPN) |
| **OWGR** | `players_data.owgr` or assembler fallback | Yes (e.g. OWGR #1) |
| **Tier badge** | Derived from win odds (FAVORITE / CONTENDER / VALUE / LONGSHOT) | Yes |
| **Why They Could Win** | `wm_phoenix_open_2026_storylines.json` | Yes (storyline text) |
| **2025 / 2024 / 2023** | `players_data.historical` (past WM Phoenix finish) | Yes (e.g. T25, T3, 1, MC, NA) |
| **Win odds** | `players_data.odds[player].odds` | Yes (e.g. +225) |
| **Top 5** | `players_data.odds[player].top5` | Yes |
| **Top 10** | `players_data.odds[player].top10` | Yes |
| **Recent form** | `wm_phoenix_open_2026_recent_form.json` | Yes (e.g. “American Express (Jan 2026): 1st • …”) |

### 4.2 Expandable panel (click SG button)

| Field | Source | Populates? |
|-------|--------|------------|
| **Strokes Gained (2026 Season)** | `data/player_strokes_gained.json` (Data Golf 2026 YTD) | Yes |
| **Off-the-Tee** | `sg_off_tee` | Yes (e.g. +1.45) |
| **Approach** | `sg_approach` | Yes |
| **Around Green** | `sg_around_green` | Yes |
| **Putting** | `sg_putting` | Yes |
| **Source line** | “PGA Tour Stats · Last 50 rounds” (or Data Golf in data) | Yes |

### 4.3 Summary: new/notable data fields

- **Strokes Gained** (expandable): Off-the-Tee, Approach, Around Green, Putting (from Data Golf 2026 YTD in `player_strokes_gained.json`).
- **Recent form** (column): Last few events with finish (from BallDontLie cache or, after running the new script, from Data Golf historical finishes).
- **Odds** (columns): Win, Top 5, Top 10 (from DraftKings; after running the new script, sourced via Data Golf).
- **Storyline** (column): “Why They Could Win” from `wm_phoenix_open_2026_storylines.json`.
- **Historical finishes** (columns): 2025, 2024, 2023 at WM Phoenix from `players_data.historical`.
- **Country + OWGR** (under name): From `players_data.countries` and `players_data.owgr`.

All of the above are present and populating in the current WM Phoenix Open preview; the SG panel is the only “dropdown” and it is populated from Data Golf.

---

## 5. Quick checks

- **Data Golf API:** `python3 scripts/test_datagolf_api.py`
- **Odds (DG):** `python3 scripts/refresh_odds_from_datagolf.py`
- **Recent form (DG):** `python3 scripts/refresh_recent_form_from_datagolf.py --tournament "WM Phoenix Open" --year 2026`
- **Regenerate HTML:** run your existing assemble/generate step so the HTML uses the updated `players_data` and `recent_form` files.
