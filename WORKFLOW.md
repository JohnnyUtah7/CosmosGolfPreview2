# COSMOS Golf Betting - Complete Workflow

This document explains the complete weekly workflow for generating PGA tournament betting previews with historical data and AI-generated storylines.

**Historical tournaments:** Past previews (American Express, Farmers Insurance Open, Sony Open) and their data/scripts live under **`historical/`** (e.g. `historical/amex/american_express_2026.html`, `historical/amex/data/`, `historical/amex/scripts/`). The weekly flow uses repo root and `data/` for the current tournament only.

## 🔄 Weekly Automation Workflow

**One command** (run Monday or Tuesday):

```bash
python scripts/weekly_tournament_orchestrator.py
# or: ./run_weekly.sh
# or: make weekly
```

**Prerequisites:**
- `data/pga_schedule_2026.json` — source of "this week's tournament" (keep updated)
- Data Golf API key (and optional `ANTHROPIC_API_KEY` for AI storylines)

The orchestrator runs the full pipeline:

| Step | Script | What it does |
|------|--------|----------------|
| 1. Archive | [archive_tournament.py](scripts/archive_tournament.py) | Archives previous week's preview |
| 2. Odds | [refresh_odds_from_datagolf.py](scripts/refresh_odds_from_datagolf.py) | Fetches win/top 5/top 10 odds from Data Golf; creates or updates `data/{slug}_{year}_players_data.json` |
| 3. OWGR | [apply_owgr.py](scripts/apply_owgr.py) | Writes Official World Golf Ranking into players_data |
| 4. Historical | (cache check only) | Uses cached results in `data/tournament_results_cache/` if present; optional manual fetch via [fetch_historical_results.py](scripts/fetch_historical_results.py) + [apply_historical_results.py](scripts/apply_historical_results.py) |
| 5. Storylines | [generate_ai_storylines_claude.py](scripts/generate_ai_storylines_claude.py) or [generate_storylines.py](scripts/generate_storylines.py) | AI storylines (Claude API) or template fallback → `data/{slug}_{year}_storylines.json` |
| 6. HTML | [generate_tournament_html.py](scripts/generate_tournament_html.py) | Builds `{slug}_{year}.html` + `{slug}_{year}_v2.html` from players_data + storylines. The **v2/Shopify HTML is mobile-responsive** (`@media` 768/480px in `generate_v2_html()` — committed `c7d8fe2`; never strip) so the pasted Shopify page renders on phones |
| 7. Deploy (optional) | [deploy_to_shopify.py](scripts/deploy_to_shopify.py) | Use `--deploy` to deploy after generation |

**Override tournament or skip steps:**

```bash
python scripts/weekly_tournament_orchestrator.py --tournament "Farmers Insurance Open"
python scripts/weekly_tournament_orchestrator.py --skip-archive --skip-storylines
python scripts/weekly_tournament_orchestrator.py --dry-run   # show steps without running
```

**Optional: recent form** — For richer storylines, run once before the orchestrator (or add a step that runs [refresh_recent_form_from_datagolf.py](scripts/refresh_recent_form_from_datagolf.py)) so `data/{slug}_{year}_recent_form.json` exists; Claude storylines use it when present.

### Crew Picks (manual step before HTML generation)

Edit `data/crew_picks.json` with each crew member's Win / Top 5 / Top 10 picks for the week. The HTML generator reads this file and auto-populates odds from the players_data JSON.

**Display order** (maintained in the JSON array): **Miller, Kevin, Andrew, Kcon, Parbeh**.

Each pick needs:
- `label`: "Win", "Top 5", or "Top 10"
- `player`: Full player name (must match players_data)
- `odds`: Leave empty (`""`) — the HTML generator fills odds automatically from the tournament's players_data

---

## 📊 Data Flow Diagram

```
data/pga_schedule_2026.json (this week)
         ↓
  [weekly_tournament_orchestrator.py]
         ↓
  archive_tournament.py (previous week)
         ↓
  refresh_odds_from_datagolf.py  →  data/{slug}_{year}_players_data.json
         ↓
  apply_owgr.py  →  (updates players_data)
         ↓
  generate_ai_storylines_claude.py  →  data/{slug}_{year}_storylines.json
         ↓
  generate_tournament_html.py  →  {slug}_{year}.html
         ↓
  (optional) deploy_to_shopify.py
```

---

## 🎯 Building the Foundation

Your current setup from `sony_open_preview.html` has:

**Player Data Structure**:
```html
<tr>
  <td>1</td>
  <td>Hideki Matsuyama 🇯🇵</td>
  <td class="owgr">6</td>
  <td class="hist-result win">1</td>      <!-- 2025 -->
  <td class="hist-result top5">T5</td>    <!-- 2024 -->
  <td class="hist-result">-</td>          <!-- 2023 -->
  <td class="odds-win">+650</td>
  <td class="odds-top5">+130</td>
  <td class="odds-top10">-160</td>
  <td class="tier-badge favorite">Favorite</td>
  <td class="storyline">
    Defending champion returns to scene of 2025 triumph...
  </td>
</tr>
```

**New Automated System Will Match This** ✅

---

## 🔧 Continuity Features

### Week-over-Week Learning

Each tournament builds on previous data:

1. **Player Performance Tracking**
   - Store results from each tournament
   - Build season-long narratives
   - Track hot/cold streaks

2. **Storyline Evolution**
   - Reference previous weeks
   - Update based on recent results
   - Maintain consistent voice

3. **Odds Analysis**
   - Track line movement
   - Identify value trends
   - Historical odds accuracy

### Database Structure

```json
{
  "season": 2026,
  "tournaments": {
    "sony_open": {
      "date": "2026-01-16",
      "players": {
        "Scottie Scheffler": {
          "finish": "T5",
          "odds": "+450",
          "storyline": "...",
          "notes": "Solid ball-striking week"
        }
      }
    },
    "the_american_express": {
      "date": "2026-01-23",
      "players": {
        "Scottie Scheffler": {
          "previous_week": "T5 at Sony Open",
          "trending": "up",
          "storyline": "Building on last week's T5..."
        }
      }
    }
  }
}
```

---

## ⏰ Recommended Cron Schedule

### Monday 12 PM PST (e.g. GitHub Actions: 20:00 UTC)

```cron
# Weekly preview generation (single command)
# 12 PM PST = 20:00 UTC
0 20 * * 1 cd /path/to/CosmosGolfBetting && \
  /usr/bin/python3 scripts/weekly_tournament_orchestrator.py \
  >> logs/weekly.log 2>&1
```

---

## 📁 File Organization

```
CosmosGolfBetting/
├── data/                                    # Current tournament data
│   ├── pga_schedule_2026.json               # Season schedule (source of "this week")
│   ├── {slug}_{year}_players_data.json      # Odds, OWGR, historical
│   ├── {slug}_{year}_storylines.json        # AI storylines
│   ├── {slug}_{year}_recent_form.json       # Optional recent form
│   ├── crew_picks.json                      # Crew picks (update weekly, order: Miller/Kevin/Andrew/Kcon/Parbeh)
│   └── tournament_results_cache/            # Cached historical leaderboards
│
├── {slug}_{year}.html                       # Generated preview (e.g. wm_phoenix_open_2026.html)
├── run_weekly.sh                            # One-command entry point
├── Makefile                                 # make weekly
│
├── scripts/                                 # Pipeline scripts
│   ├── weekly_tournament_orchestrator.py    # Main entry point
│   ├── refresh_odds_from_datagolf.py        # Odds + create players_data
│   ├── apply_owgr.py                        # OWGR into players_data
│   ├── generate_ai_storylines_claude.py     # Primary storylines
│   ├── generate_storylines.py              # Fallback storylines
│   ├── generate_tournament_html.py          # Generic HTML output
│   ├── archive_tournament.py                # Archive previous week
│   ├── deploy_to_shopify.py                 # Deploy
│   └── legacy/                              # Deprecated storyline generators
│
└── historical/                             # Past tournaments
    ├── amex/, farmers/, sony/, wm_phoenix_open/   # Tournament-specific data/scripts
```

---

## 💡 Pro Tips

1. **One command**: Use `./run_weekly.sh` or `make weekly` on Monday to generate the week's preview.
2. **Schedule**: Keep `data/pga_schedule_2026.json` in sync with the real PGA calendar so "this week" is correct.
3. **Dry run**: Use `--dry-run` to see which tournament and steps would run without executing.
4. **Optional recent form**: Run `refresh_recent_form_from_datagolf.py` for the current tournament if you want richer storylines.
5. **Crew picks**: Update `data/crew_picks.json` with this week's picks before generating HTML. Odds are auto-filled from players_data. Keep the crew order: Miller, Kevin, Andrew, Kcon, Parbeh.

---

**Status**: Weekly pipeline in place. Run `python scripts/weekly_tournament_orchestrator.py` (or `./run_weekly.sh`) to generate.
