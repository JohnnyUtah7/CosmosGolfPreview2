# Tournament Data Collection Workflow

## Overview
This document describes the automated workflow for collecting and preparing tournament betting preview data.

**Historical tournaments:** Past tournaments (American Express, Farmers, Sony Open) and their data/scripts live under **`historical/`** (e.g. `historical/amex/data/`, `historical/amex/scripts/`). Paths in this doc that reference `data/amex_*` or `american_express_2026.html` apply to the current tournament at root, or to files under `historical/amex/` for AMEX.

## Quick Start - New Tournament

For a new tournament, run the automated preparation script:

```bash
python3 scripts/prepare_tournament_data.py --tournament "american_express_2026"
```

This will automatically:
1. Fetch historical tournament results (last 3 years) for all players
2. Update OWGR rankings from ESPN
3. Fetch recent form data (last 3 tournaments played)
4. Fetch weather forecast for tournament week
5. Generate HTML betting preview

## Manual Step-by-Step Process

If you need to run steps individually:

### 1. Historical Tournament Results (RECOMMENDED: Web Search)

The most reliable method fetches complete leaderboards via web search, then applies them to your player data:

```bash
export ANTHROPIC_API_KEY="your-key-here"

# Step 1: Fetch complete leaderboards (one-time, cached for reuse)
python3 scripts/fetch_tournament_results_web.py --tournament "American Express" --years 2023 2024 2025

# Step 2: Apply cached results to player data
python3 scripts/apply_historical_results.py --tournament "American Express" --data data/amex_2026_players_data.json
```

**How web search works:**
- Uses Claude with web search enabled to find official leaderboards (ESPN, PGA Tour, CBS Sports)
- Fetches COMPLETE leaderboards (all ~150+ players), not individual player queries
- Results are cached in `data/tournament_results_cache/` for reuse
- Fuzzy name matching handles variations (e.g., "Si Woo Kim" vs "Si-Woo Kim")

**Benefits over old approach:**
- Real-time web search finds authoritative data (not training data)
- One API call per tournament/year instead of one per player
- Cached results can be reapplied to different player lists
- Much lower error rate (~95% vs ~80% accuracy)

**Legacy approach (per-player queries):**
```bash
python3 scripts/complete_amex_history.py  # Individual player searches
```

**Value:** Historical venue performance is the #1 predictor of future success. Players trending up (e.g., MC → T34 → T7) show improving course fit.

### 2. OWGR Rankings

Fetches current Official World Golf Ranking for all players:

```bash
python3 scripts/update_owgr_from_espn.py
```

**What it does:**
- Pulls ESPN's current OWGR Top 100
- Matches rankings to players in the field
- Updates `data/amex_2026_players_data.json` with OWGR

**Coverage:** Typically covers ~60-70 players (Top 100 ranked players)

### 3. Recent Form

Fetches last 3 tournaments played for each player:

```bash
export ANTHROPIC_API_KEY="your-key-here"
python3 scripts/clean_recent_form_simple.py
```

**What it does:**
- Searches for each player's last 3 tournament results
- Includes PGA Tour, DP World Tour, Korn Ferry Tour events
- Includes unofficial events (Hero World Challenge, etc.)
- Updates `data/amex_2026_recent_form.json`

**Value:** Shows current form and momentum heading into the tournament.

### 4. Weather Forecast

Fetches weather forecast for tournament week:

```bash
export ANTHROPIC_API_KEY="your-key-here"
python3 scripts/fetch_tournament_weather.py
```

**What it does:**
- Searches for weather forecast for tournament location/dates
- Generates 1-2 sentence summary for display
- Saves to `data/tournament_weather.json`

**Value:** Wind and rain conditions significantly impact scoring and betting strategy.

### 5. Generate HTML Preview

Creates the final HTML betting preview:

```bash
python3 scripts/generate_american_express.py
```

**What it does:**
- Combines all data sources
- Generates styled HTML with player board
- Includes odds, storylines, historical results, recent form
- Adds weather forecast to header
- Outputs to `american_express_2026.html`

## Data Files

| File | Purpose | Updated By |
|------|---------|------------|
| `data/amex_2026_players_data.json` | Player master data (country, OWGR, historical results) | Historical & OWGR scripts |
| `data/amex_2026_recent_form.json` | Recent tournament results | Recent form script |
| `data/american_express_2026_odds.json` | Betting odds | Manual update |
| `data/tournament_weather.json` | Weather forecast | Weather script |
| `american_express_2026.html` | Final HTML output | Generate script |

## Resuming After Errors

If a step fails, you can resume by skipping completed steps:

```bash
# Example: Historical data failed, resume from there
python3 scripts/prepare_tournament_data.py \
    --skip-owgr \
    --skip-recent-form

# Example: Everything done except weather
python3 scripts/prepare_tournament_data.py \
    --skip-historical \
    --skip-owgr \
    --skip-recent-form
```

## Performance

**Expected runtimes:**
- Historical results: ~10-15 minutes (279 API calls)
- OWGR rankings: ~5 seconds (hardcoded ESPN data)
- Recent form: ~5-10 minutes (163 API calls for missing data)
- Weather forecast: ~5 seconds (1 API call)
- HTML generation: ~1 second

**Total: ~15-25 minutes for complete data collection**

## API Rate Limits

All scripts use Claude Sonnet 4 API. Rate limits:
- Anthropic API: 50 requests/minute typical tier
- Scripts include progress saving every 20 operations
- If interrupted, re-running will skip already-completed data

## Value Propositions

### Historical Tournament Results (3 years)
- **Trending Performance:** Identify players improving at this venue (MC → T34 → T7)
- **Course Specialists:** Players who consistently perform well here
- **Red Flags:** Players trending down or with poor course history
- **First-Timers:** No course history (higher variance)

### Recent Form
- **Current Momentum:** Hot streaks or cold spells
- **Confidence:** Recent top-10s signal readiness
- **Injury Watch:** WD or MC patterns suggest issues

### OWGR Rankings
- **Skill Baseline:** World-class players (Top 50) vs field players
- **Odds Validation:** Under-priced favorites, over-priced longshots

### Weather Forecast
- **Scoring Conditions:** Wind/rain = higher scores = longshot value
- **Ideal Conditions:** Calm weather = low scores = favorite edge

## Next Tournament Setup

For the next tournament (e.g., Farmers Insurance Open 2026):

1. Create new player data file: `data/farmers_2026_players_data.json`
2. Create odds file: `data/farmers_2026_odds.json`
3. Update `TOURNAMENT_NAME`, `TOURNAMENT_DATES`, `TOURNAMENT_LOCATION` in generate script
4. Run: `python3 scripts/prepare_tournament_data.py --tournament "farmers_2026"`

## Questions?

Contact: Cosmos Golf Betting Team
