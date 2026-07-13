# MCP Server & Weekly Pipeline Audit

**Date:** 2026-02-02  
**Scope:** `mcp_server/`, `scripts/weekly_tournament_orchestrator.py`, and scripts used for weekly tournament preview generation.

---

## 1. What the "MCP Server" Actually Is

The `mcp_server/` directory is **not a running MCP (Model Context Protocol) server process**. It is a **Python API client library** used by scripts in the repo.

| Component | Purpose |
|-----------|--------|
| `mcp_server/tools/odds.py` | **OddsAPIClient** – The Odds API (sports odds). Used as **fallback** when DraftKings script fails. |
| `mcp_server/tools/pga.py` | **PGAAPIClient** – BallDontLie (PGA/stats). **Not used by the weekly orchestrator.** Used by scripts like `refresh_recent_form.py`. |
| `mcp_server/tools/news.py` | **GolfNewsClient** – Golf news/search. Used by `generate_storylines.py` (template-based storylines). |
| `mcp_server/models/` | Shared data schemas for the above clients. |

So when you "run the pipeline each week," the value you get from `mcp_server` is:

- **Odds:** Only if DraftKings fetch fails → fallback to The Odds API.
- **News:** Only if you use the template-based `generate_storylines.py` (which uses GolfNewsClient).
- **PGA/BallDontLie:** Not used in the weekly flow at all.

---

## 2. Weekly Orchestrator – What It Runs

| Step | Script / Behavior | Uses MCP? |
|------|-------------------|-----------|
| 1. Archive | `archive_tournament.py` | No |
| 2. Odds | `fetch_draftkings_odds.py` (DraftKings first, **OddsAPIClient fallback**) | Yes (fallback only) |
| 3. Historical | `fetch_historical_results()` – **cache check only**, no live fetch | No |
| 4. Storylines | `generate_ai_storylines_claude.py` (if `ANTHROPIC_API_KEY` set) or **`generate_storylines.py` with no args** | No / **Broken** |
| 5. HTML | `generate_tournament_html.py` | No |

---

## 3. Critical Bugs Fixed

### 3.1 Claude storylines script was AMEX-only

- **Issue:** `generate_ai_storylines_claude.py` had hardcoded paths and text:
  - `data/amex_2026_players_data.json`, `data/amex_2026_storylines.json`, `data/amex_2026_recent_form.json`
  - Prompt text: "The American Express 2026", "AMEX 2025/2024/2023"
- **Impact:** For WM Phoenix, Farmers, or any other tournament, the script would read/write AMEX files and produce AMEX-specific copy.
- **Fix:** Script now accepts `--tournament` and `--year`, derives paths from slug (e.g. `wm_phoenix_open_2026_*`), and uses tournament name + generic "this event" history in the prompt.

### 3.2 Orchestrator fallback to template storylines was broken

- **Issue:** When Claude storylines were skipped or failed, the orchestrator called `generate_storylines.py` with **no arguments**. That script **requires** `--tournament` and `--players-data` and expects `--output`; without them it exits with an error.
- **Impact:** Fallback never worked; storyline step failed for any non-Claude run.
- **Fix:** Orchestrator now passes `--tournament`, `--year`, `--players-data` (e.g. `data/{slug}_{year}_players_data.json`), and `--output` (e.g. `data/{slug}_{year}_storylines.json`) when invoking `generate_storylines.py`.

---

## 4. Recommendations (Post-Fix)

1. **Historical results:** Make `fetch_historical_results()` actually fetch (e.g. via a generic script or MCP client) when cache is missing instead of only checking cache.
2. **PGAAPIClient:** Consider using `mcp_server/tools/pga.py` in the weekly flow (e.g. for field/player data or results) so BallDontLie adds value every week.
3. **Odds:** Keep DraftKings as primary; document that The Odds API is the fallback and ensure API keys are set for both.
4. **Naming:** If you want a real "MCP server" (e.g. for Cursor/other tools), consider a separate process that exposes these clients over MCP; current `mcp_server/` is a library, not a server.

---

## 5. Summary

- **MCP server** = shared **client library** for odds, PGA, and news; not a running server.
- **Weekly value:** Odds fallback (The Odds API) and template storylines (GolfNewsClient) depend on this library; PGA client is unused in the weekly pipeline.
- **Fixes applied:** Claude storylines script is tournament/year-agnostic; orchestrator passes correct args to the template-based storylines script so the weekly run works for any tournament.
