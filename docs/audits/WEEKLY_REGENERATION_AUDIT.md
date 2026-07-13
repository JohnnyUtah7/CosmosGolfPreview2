# Weekly Regeneration Audit

**Purpose:** Document where mistakes tend to happen each week so you can catch them early or fix the pipeline.

**Weekly run (one command):** `python scripts/weekly_tournament_orchestrator.py` (or `./run_weekly.sh` or `make weekly`).

---

## 1. What the Orchestrator Actually Runs (and Doesn’t)

When you run `python scripts/weekly_tournament_orchestrator.py` (with or without `--tournament "WM Phoenix Open"`), it runs:

| Step | What runs | Common failure / mistake |
|------|------------|---------------------------|
| 1. Archive | `archive_tournament.py` for *previous* week’s tournament | Wrong previous tournament if schedule is off. |
| 2. Odds | `refresh_odds_from_datagolf.py` → creates/updates `data/{slug}_{year}_players_data.json` (Data Golf win/top 5/top 10) | Data Golf API/keys; script requires `--players-data` or `--tournament` + `--year` when run standalone. |
| 3. OWGR | `apply_owgr.py` → writes OWGR into `players_data` | OWGR is now in the pipeline. |
| 4. Historical | **Cache check only** – no script that fetches historical results for the *current* tournament. | For a new tournament, historical stays empty unless you’ve already run something else (e.g. manual fetch) and cached it. |
| 5. Storylines | `generate_ai_storylines_claude.py --tournament "…" --year …` (or fallback `generate_storylines.py` with correct args) | Claude uses `data/{slug}_{year}_recent_form.json` if present; if missing, recent form in storylines is blank/—. |
| 6. HTML | `generate_tournament_html.py --tournament "…" --year …` → `{slug}_{year}.html` | Reads `players_data`, `storylines`. **Does not load a separate “recent form” file** – only what’s in storylines. |

So by default the pipeline **does not**:

- Fetch historical results for this week’s event (only checks cache).
- Run a “recent form” step (so `{slug}_{year}_recent_form.json` may be missing or stale).
- Use any tournament-specific “assembler” (e.g. `assemble_wm_phoenix_html.py`; those scripts live under `historical/wm_phoenix_open/scripts/`).

---

## 2. Two HTML Paths (Source of Confusion)

There are two ways the repo can produce HTML:

| Path | Script | When it’s used | Notes |
|------|--------|-----------------|--------|
| **Generic** | `generate_tournament_html.py` | By the orchestrator for *any* tournament. | Uses `data/{slug}_{year}_players_data.json` and `data/{slug}_{year}_storylines.json`. OWGR comes from `players_data` (filled by `apply_owgr.py`). |
| **Tournament-specific** | e.g. `assemble_wm_phoenix_html.py` | When you run it manually for that event. | Run from project root; can include recent form, custom layout, etc. |

If you sometimes run the orchestrator and sometimes run a tournament-specific assembler, the “mistakes” can be: wrong file set (generic vs WM-specific), or missing OWGR/recent form because the orchestrator never runs the scripts that fill them.

---

## 3. Scripts Not Used by the Orchestrator

- **WM Phoenix–specific scripts** are under `historical/wm_phoenix_open/scripts/` (e.g. `assemble_wm_phoenix_html.py`, `apply_owgr_to_wm_phoenix.py`, `generate_wm_phoenix_*.py`). Run from project root only when you want that event’s custom assembly.
- **Legacy storyline generators** are under `scripts/legacy/` (e.g. `generate_ai_storylines.py`, `generate_ai_storylines_batch.py`). The pipeline uses `generate_ai_storylines_claude.py` and `generate_storylines.py` only.
- **Other scripts** (e.g. `refresh_recent_form.py`, `apply_historical_results.py`, `audit_*.py`) may have AMEX or WM in defaults/examples; pass explicit `--tournament`/`--players-data` or you may hit the wrong tournament.

---

## 4. Gaps That Cause Missing or Wrong Data

| Gap | Effect | Possible fix |
|-----|--------|----------------|
| **Historical not fetched** | `players_data.historical` empty for new event → “NA” in history columns. | Add a step (or use a generic script) that fetches/caches results and runs something like `apply_historical_results.py` for the current tournament. |
| **OWGR not in pipeline** | (Fixed: orchestrator runs `apply_owgr.py` after odds.) | N/A. |
| **Recent form not in pipeline** | No step creates/updates `{slug}_{year}_recent_form.json`; Claude storylines then have no recent form. Generic HTML doesn’t show a recent-form column. | Add a “generate recent form” step that writes `data/{slug}_{year}_recent_form.json`, or accept that recent form is manual/tournament-specific. |
| **Schedule mismatch** | Wrong “this week” or “previous” tournament. | Keep `data/pga_schedule_2026.json` in sync with reality; confirm dates. |
| **Two HTML paths** | Orchestrator writes generic HTML; you might expect the “fancy” tournament-specific HTML. | Decide: either always use orchestrator + generic HTML, or add a clear step (“run assemble_X_html.py for WM Phoenix only”) and document when to use which. |

---

## 5. Pre-Regeneration Checklist (Optional)

- [ ] `data/pga_schedule_2026.json` has correct dates for this week and last week.
- [ ] You know which tournament you’re building: `--tournament "WM Phoenix Open"` (or rely on auto-detect).
- [ ] If you need historical: ensure cache exists or run a fetch/apply step for **this** tournament before or after the orchestrator.
- [ ] If you use tournament-specific HTML (e.g. `historical/wm_phoenix_open/scripts/assemble_wm_phoenix_html.py`): run that from project root **after** data is ready; the orchestrator only runs the generic HTML generator.

---

## 6. Post-Regeneration Spot Checks

- [ ] **Odds:** Open `data/{slug}_{year}_players_data.json` and confirm `odds` has entries and values look sane.
- [ ] **OWGR:** In the same file, check `players.<name>.owgr` – if many are missing, run an OWGR step for this tournament.
- [ ] **Historical:** In the same file, check `historical` – if empty, historical step wasn’t run or cache was missing.
- [ ] **Storylines:** Open `data/{slug}_{year}_storylines.json` – confirm `storylines` (and optionally `recent_form_analyses`) exist and aren’t all generic.
- [ ] **HTML:** Open `{slug}_{year}.html` (or the tournament-specific one if you used an assembler) – confirm title and dates match this week’s event, and spot-check a few players for OWGR, history, and storyline text.

---

## 7. Summary

- **Mistakes each week** often come from: (1) running scripts that default to one tournament (pass explicit `--tournament`/`--year` or `--players-data`), (2) orchestrator not running historical/recent-form (OWGR is in pipeline), (3) mixing the generic HTML path with tournament-specific assemblers (orchestrator uses generic only).
- **MCP/orchestrator fixes** (Claude storylines + fallback args) are done; see `MCP_AUDIT.md`.
- **This doc** is the audit for “why did regeneration go wrong?” – use the checklists and tables above to align your weekly run with the pipeline you actually use (generic vs tournament-specific) and to add or run any missing steps (e.g. historical, recent form). CI/CD runs weekly (Monday 12 PM PST / 20:00 UTC) including OWGR.
