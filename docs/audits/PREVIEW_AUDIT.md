# WM Phoenix Open 2026 – Preview pipeline audit

**Date:** February 4, 2026  
**Scope:** Data Golf (golfdata) API, data files, and HTML preview – confirm everything is populating and working.

---

## 1. Data Golf API ✅

- **Status:** Live and responding.
- **Check:** `python3 scripts/test_datagolf_api.py` – all tests pass (player list, rankings, field, predictions, skill ratings, outright odds, schedule).
- **Config:** `DATAGOLF_API_KEY` in `.env`; base URL `https://feeds.datagolf.com`.

---

## 2. Data files (populating)

| File | Status | Notes |
|------|--------|------|
| **wm_phoenix_open_2026_players_data.json** | ✅ | 123 players. `odds` from Data Golf (fair odds). `data_sources.odds`: "Data Golf". Has `historical`, `countries`, `owgr`. |
| **wm_phoenix_open_2026_recent_form.json** | ✅ | 120+ players with recent form text (cache + BallDontLie). Some "—" where no data. |
| **wm_phoenix_open_2026_storylines.json** | ✅ | Storylines keyed by player name; used for "Why They Could Win". |
| **wm_phoenix_open_2026_matchups.json** | ✅ | `daily_three_balls`: 41 Round 1 groups with Data Golf fair odds. `tournament_matchups` / `round_matchups` empty until books post. |
| **player_strokes_gained.json** | ✅ | SG stats (Data Golf 2026 YTD) for player detail panels. |

---

## 3. Refresh scripts (working)

| Script | Purpose | Last run result |
|--------|--------|------------------|
| **refresh_odds_from_datagolf.py** | Outright win, top 5, top 10 from Data Golf fair odds | ✅ 123 players → players_data.json |
| **fetch_matchups_from_datagolf.py** | Tournament/round matchups + Round 1 three-balls from DG | ✅ 41 daily groups → matchups.json |
| **generate_wm_phoenix_recent_form.py** | Merge recent form from cache for tournament | ✅ Populates recent_form.json from cache |
| **apply_owgr.py** | Apply OWGR ranks into players_data | ✅ Used by orchestrator |

---

## 4. HTML preview (working)

- **Tournament Odds tab:** Table built from `players_data.json` (odds, historical, storylines, recent form, OWGR, countries). Odds shown are Data Golf.
- **Daily Matchups tab:** Loads `data/wm_phoenix_open_2026_matchups.json` via `fetch()`. Renders Round 1 groups (3-ball) with tee time, hole start, player odds, and DG favorite. Tournament H2H section appears when `tournament_matchups` has data.
- **Serving:** Must be served from project root (e.g. `python3 scripts/preview_server.py`) so `data/wm_phoenix_open_2026_matchups.json` is same-origin. Open http://localhost:8000/ and use the Daily Matchups tab to confirm.

---

## 5. Single source: Data Golf

- **Outright odds:** Data Golf fair odds (`baseline_history_fit`); labeled "Data Golf" in `data_sources` and `bookmaker`.
- **Matchups:** Round 1 groups and odds from Data Golf all-pairings; tournament/round H2H from Data Golf when available.
- **Footer:** "Strokes Gained, model predictions & odds from Data Golf (golfdata API)."

---

## 6. Quick verification commands

```bash
# 1. API
python3 scripts/test_datagolf_api.py

# 2. Refresh data
python3 scripts/refresh_odds_from_datagolf.py
python3 scripts/fetch_matchups_from_datagolf.py

# 3. Serve and test in browser
python3 scripts/preview_server.py --default wm_phoenix_open_2026.html
# Open http://localhost:8000/ → Tournament Odds (main table) and Daily Matchups (round 1 groups)
```

---

## 7. Fix applied during audit

- **Daily Matchups tab** was still "Coming Soon" and did not load matchups JSON. The preview HTML was updated to:
  - Add a matchups container (loading, empty, content).
  - Add CSS for the matchups table.
  - Add `formatTeetime`, `buildMatchupsContent`, and a `fetch()` to load `data/wm_phoenix_open_2026_matchups.json` and render Round 1 groups (and tournament H2H when present).

With that in place, the pipeline is populating and the preview is working end-to-end.
