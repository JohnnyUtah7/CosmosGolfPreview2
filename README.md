# COSMOS Golf Betting Preview

A space-themed, interactive golf betting preview website for PGA Tour events. This project features a futuristic NASA-inspired design with comprehensive player analysis, historical results, and betting odds.

## 🚀 Overview

COSMOS Golf Betting Preview provides detailed betting analysis for PGA Tour events with a unique space-themed aesthetic. The preview includes player storylines, historical course performance, betting odds, and visual design elements that create an immersive experience.

**The system is fully automated** - it runs weekly to generate betting previews for every PGA Tour tournament automatically.

## 🔄 Weekly Automated Workflow

The system automatically generates betting previews for every PGA Tour tournament using a fully automated pipeline.

### How It Works

**Automated Schedule:**
- **GitHub Actions** runs every Monday at 12 PM PST (8 PM UTC)
- Automatically detects the upcoming tournament from the PGA schedule
- Generates complete betting preview with all data sources
- Can also be triggered manually via GitHub Actions UI

**Complete Pipeline:**

1. **Tournament Detection** - Automatically finds this week's tournament from `data/pga_schedule_2026.json`
2. **Move Previous to Historical** - Moves last week's tournament (HTML + data) into `historical/{slug}/` so the main editor list shows only the current tournament
3. **Fetch Odds** - Gets win/top 5/top 10 odds from Data Golf (refresh_odds_from_datagolf)
4. **Historical Results** - Uses cached 3-year course history (fetch/apply manually if needed for new events)
5. **Recent Form** - Fetches tournament result caches from Data Golf (Pebble, Genesis, Cognizant, etc.) and builds recent form automatically (no more manual pulling)
6. **OWGR Rankings** - Updates Official World Golf Rankings (apply_owgr)
7. **Data Golf Analytics** - Applies strokes gained, predictions, course fit (apply_datagolf_to_players)
8. **AI Storylines** - Generates player narratives using Claude API (with template fallback)
9. **HTML Generation** - Creates the final space-themed betting preview (main + v2 for Shopify)
10. **Optional Deploy** - Can deploy to Shopify if configured (`--deploy`)

### Weekly generation (one command)

On **Monday or Tuesday**, generate this week's preview:

```bash
./run_weekly.sh
# or: make weekly
# or: python scripts/weekly_tournament_orchestrator.py
```

**Prerequisites:** Keep `data/pga_schedule_2026.json` updated (source of "this week's tournament"; update when the season advances). Set Data Golf API key and optionally `ANTHROPIC_API_KEY` for AI storylines.

**Output:** `{slug}_{year}.html` (e.g. `wm_phoenix_open_2026.html`) plus `data/{slug}_{year}_players_data.json` and `data/{slug}_{year}_storylines.json`.

**Override or skip steps:**

```bash
# Override tournament
python scripts/weekly_tournament_orchestrator.py --tournament "Farmers Insurance Open"

# Skip specific steps (if data already exists)
python scripts/weekly_tournament_orchestrator.py --skip-archive --skip-historical --skip-datagolf

# Dry run (show steps without running)
python scripts/weekly_tournament_orchestrator.py --dry-run

# Deploy to Shopify after generation
python scripts/weekly_tournament_orchestrator.py --deploy
```

### Data Collection Process

For each tournament, the system collects:

- **Betting Odds** - Win, Top 5, Top 10 from Data Golf API
- **Historical Results** - Last 3 years at this specific course/venue
- **Recent Form** - Last 3 tournaments played (any tour)
- **OWGR Rankings** - Current world rankings
- **Weather Forecast** - Tournament week conditions
- **AI Storylines** - Context-aware narratives for each player

### Tournament Data Files

**Current tournament only** lives at repo root and in `data/`; after each weekly run, the previous week's tournament is moved to `historical/{slug}/` so the main list stays clean.

```
data/                                          # Current tournament only
├── {tournament_slug}_{year}_players_data.json  # Master player data
├── {tournament_slug}_{year}_storylines.json    # AI-generated storylines
├── {tournament_slug}_{year}_insights.json      # AI matchup insights (optional)
├── {tournament_slug}_{year}_matchups.json      # Round 1 matchups (optional)
├── {tournament_slug}_{year}_recent_form.json   # Recent form (optional)
├── tournament_results_cache/                   # Cached historical leaderboards
└── pga_schedule_2026.json                      # Full season schedule
```

Past tournaments and their data live under `historical/{slug}/` and `historical/{slug}/data/`.

### GitHub Actions Automation

The workflow (`.github/workflows/deploy-preview.yml`) provides:

- **Scheduled runs** - Every Monday at 12 PM PST
- **Manual triggers** - Run on-demand with custom parameters
- **Artifact uploads** - Generated HTML and data files available for download
- **Error notifications** - Automatic failure alerts
- **Deployment options** - Optional Shopify deployment

### Key Scripts

| Script | Purpose |
|--------|---------|
| `run_weekly.sh` / `make weekly` | One-command entry point (runs orchestrator) |
| `weekly_tournament_orchestrator.py` | Master orchestrator - runs full pipeline |
| `move_tournament_to_historical.py` | Moves a tournament's files to `historical/{slug}/` (run automatically by orchestrator for previous week) |
| `fetch_recent_form_caches_from_datagolf.py` | Fetches tournament result caches from Data Golf for events before current (Pebble, Genesis, Cognizant, etc.); run automatically in weekly pipeline |
| `fetch_historical_from_datagolf.py` | Fetches one tournament's results from Data Golf and writes to `data/tournament_results_cache/` |
| `build_recent_form_from_cache.py` | Builds `{slug}_{year}_recent_form.json` from tournament result caches (schedule-aware) |
| `refresh_odds_from_datagolf.py` | Fetches odds from Data Golf; creates/updates players_data |
| `apply_owgr.py` | Writes OWGR into players_data |
| `apply_datagolf_to_players.py` | Applies Data Golf analytics (SG, predictions, course fit) |
| `generate_ai_storylines_claude.py` | AI storyline generation (Claude API) |
| `generate_storylines.py` | Fallback template storylines |
| `generate_tournament_html.py` | Creates final HTML preview (main + v2) |
| `archive_tournament.py` | Optional: archive HTML to `archive/` (manual use) |
| `deploy_to_shopify.py` | Deploy generated HTML to Shopify |

### Setup for New Tournaments

The system automatically handles new tournaments, but for manual setup:

1. **Add to schedule** - Update `data/pga_schedule_2026.json` with tournament details
2. **Run orchestrator** - The system handles everything else automatically
3. **Review output** - Check generated HTML and data files
4. **Deploy** - Upload to Shopify or host elsewhere

### Documentation

- **[WORKFLOW.md](WORKFLOW.md)** - Detailed workflow documentation
- **[TOURNAMENT_DATA_WORKFLOW.md](TOURNAMENT_DATA_WORKFLOW.md)** - Data collection process
- **[SETUP.md](SETUP.md)** - Initial setup instructions

## 📁 Project Structure

```
CosmosGolfBetting/
├── README.md                      # This file
├── WORKFLOW.md                    # Detailed workflow documentation
├── TOURNAMENT_DATA_WORKFLOW.md    # Data collection process guide
├── AUDIT_REPORT.md                # Security and API audit report
├── .env.example                   # Environment variables template
├── requirements.txt               # Python dependencies
├── .github/
│   └── workflows/
│       └── deploy-preview.yml     # GitHub Actions automation
├── mcp_server/                    # MCP Server for API integrations
│   ├── __init__.py
│   ├── config.py                  # Configuration and environment variables
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic data models
│   └── tools/
│       ├── __init__.py
│       ├── odds.py                # The Odds API client
│       ├── pga.py                 # BallDontLie PGA API client
│       └── news.py                # News/RSS integration
├── scripts/                       # Automation scripts
│   ├── weekly_tournament_orchestrator.py  # Master orchestrator
│   ├── move_tournament_to_historical.py   # Move previous week to historical/
│   ├── refresh_odds_from_datagolf.py      # Data Golf odds
│   ├── apply_owgr.py                      # OWGR into players_data
│   ├── apply_datagolf_to_players.py       # Data Golf analytics
│   ├── generate_tournament_html.py        # HTML generation
│   ├── generate_ai_storylines_claude.py   # AI storylines
│   └── [other utility scripts]
├── data/                          # Current tournament data only
│   ├── pga_schedule_2026.json     # Full season schedule
│   ├── {slug}_{year}_players_data.json
│   ├── {slug}_{year}_storylines.json
│   ├── tournament_results_cache/  # Cached historical leaderboards
│   └── ...
├── historical/                    # Past tournaments (moved here by weekly run)
│   └── {slug}/                    # e.g. cognizant_classic_in_the_palm_beaches/
│       ├── *.html
│       ├── data/
│       └── assets/                # Optional source images for that event
├── assets/                        # Brand logos + loose reference images
│   ├── brand/                     # COSMOS_Golf-Dec-Logo_001*.png
│   └── misc/                      # Screenshots / unassigned JPEGs
├── {tournament}_{year}.html       # Current tournament preview (root)
```

## 🎨 Features

### Design Elements
- **Space-themed UI**: NASA-inspired color palette with cyber-cyan, grid-green, and space-black
- **Animated backgrounds**: Radial gradients and grid overlays for depth
- **Typography**: Orbitron, Rajdhani, and Share Tech Mono fonts for futuristic feel
- **Responsive design**: Works on desktop and mobile devices

### Content Features
- **Complete betting board**: Comprehensive player rankings with odds
- **Historical results**: 3-year course history for each player
- **Player storylines**: Detailed analysis of why each player could win
- **Tier badges**: Visual categorization (Favorite, Contender, Value Play, Longshot)
- **Asian player highlights**: Special indicators for Asian players
- **Event information**: Purse, course details, field size, and more

## 📄 Files Description

### Generated Tournament Previews
**Format**: `{tournament_slug}_{year}.html` at repo root for the **current** tournament only. Past tournaments are moved to `historical/<slug>/` by the weekly run so the main editor list shows only this week's event.

These are automatically generated by the weekly orchestrator. Each preview includes:
- Complete betting board with all players
- Historical course results (3-year history)
- Recent tournament form
- AI-generated player storylines
- Betting odds (Win, Top 5, Top 10)
- Weather forecast
- Event information (purse, course details, field size)

**Features:**
- Full-page space-themed betting preview
- Self-contained HTML (no external dependencies)
- Responsive design for mobile and desktop
- Can be opened directly in browser or hosted on any web server

### Historical tournaments

Past tournament previews and their data live under **`historical/`**. The weekly orchestrator **automatically moves the previous week's tournament** (HTML + all data files) into `historical/{slug}/` when it generates the new one, so the main list always shows only the current event.

- **`historical/{slug}/`** – e.g. `cognizant_classic_in_the_palm_beaches/`, `arnold_palmer_invitational_presented_by_mastercard/` (after they're no longer current)
- **`historical/amex/`**, **`historical/farmers/`**, **`historical/sony/`**, etc. – Older events with optional tournament-specific scripts and docs

Current-tournament HTML and data stay at repo root and in `data/`. To run tournament-specific scripts (e.g. AMEX/Farmers), use paths under `historical/<tournament>/scripts/` and `historical/<tournament>/data/`.

### Legacy Files
- `docs/shopify-embed.html` - Shopify-compatible embed template
- `docs/examples/tab_toggle_example.html` - Tab UI example (reference)

### Shopify Deployment

For Shopify deployment:

1. Upload images to Shopify Files (Settings > Files):
   - `assets/brand/COSMOS_Golf-Dec-Logo_001.png`
   - Course image for the tournament
2. Copy the image URLs from Shopify Files
3. Replace the image URLs in the generated HTML with your Shopify file URLs
4. In Shopify Admin:
   - Go to Online Store > Pages > Add page
   - Or add to an existing page using a Custom HTML section
   - Paste the entire code block

Or use the automated deployment:
```bash
python scripts/weekly_tournament_orchestrator.py --deploy
```

## 🎯 Color Palette

The design uses a consistent NASA-inspired color scheme:

- **NASA Blue**: `#0B3D91` - Primary brand color
- **NASA Red**: `#FC3D21` - Accent color
- **Space Black**: `#0a0a0f` - Background
- **Cyber Cyan**: `#00d4ff` - Primary accent, text highlights
- **Grid Green**: `#00ff88` - Success states, wins
- **Warning Gold**: `#ffd700` - Favorites, top 5 finishes

## 📊 Data Structure

The preview includes:
- **Event Information**: Total purse, winner's share, course details, field size
- **Player Data**: Name, country, OWGR ranking, tier classification
- **Historical Results**: 3-year course history with color-coded results
- **Betting Odds**: Win, Top 5, and Top 10 odds (Data Golf API)
- **Storylines**: Detailed analysis of each player's chances

## 🛠️ Customization

### Automated System (Recommended)

The system automatically handles all updates:
- **Tournament detection** - Finds upcoming tournaments from schedule
- **Data collection** - Fetches odds, history, rankings, form
- **Storyline generation** - AI creates compelling narratives
- **HTML generation** - Produces complete preview automatically

Just run:
```bash
python scripts/weekly_tournament_orchestrator.py
```

### Manual Customization

If you need to manually edit data:

**Player Data**: Edit `data/{tournament}_{year}_players_data.json`
- Player names, countries, OWGR rankings
- Historical course results
- Country flags and metadata

**Betting Odds**: Edit `data/{tournament}_{year}_odds.json`
- Win, Top 5, Top 10 odds
- Multiple sportsbook sources

**Storylines**: Edit `data/{tournament}_{year}_storylines.json`
- Player narratives and analysis
- Course fit descriptions
- Recent form context

**Styling**: Edit `scripts/generate_tournament_html.py`
- Color variables (NASA Blue, Cyber Cyan, Grid Green, etc.)
- Font families (Orbitron, Rajdhani, Share Tech Mono)
- Grid and background effects
- Responsive breakpoints

### Adding New Tournaments

1. **Add to schedule**: Update `data/pga_schedule_2026.json` with tournament details
2. **Run orchestrator**: System handles everything else automatically
3. **Review output**: Check generated HTML and data files
4. **Customize if needed**: Edit JSON data files and regenerate

### Styling Customization

All styles are contained within the generated HTML `<style>` tags. Key customization points:
- Color variables in `:root` (NASA Blue, Cyber Cyan, Grid Green, etc.)
- Font families in the Google Fonts link
- Grid and background effects in `::before` and `::after` pseudo-elements
- Responsive breakpoints for mobile/tablet/desktop

## 📱 Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Responsive design for mobile devices
- Uses CSS Grid and Flexbox
- Google Fonts for typography

## 📝 Notes

- Odds are sourced from the Data Golf API (win, top 5, top 10)
- Data is for entertainment purposes only
- Includes responsible gambling disclaimer
- All player links open Google search results
- API integrations require valid API keys (see `.env.example`)
- Review `AUDIT_REPORT.md` before deploying to production

## 🤖 MCP Server & API Integration

This project includes a **Model Context Protocol (MCP) server** for automated golf betting data collection and analysis.

### Architecture

The MCP server is organized into modular components:

- **`config.py`**: Centralized configuration management
  - Environment variable loading
  - API endpoint configuration
  - Cache directory setup
  
- **`models/schemas.py`**: Pydantic data models
  - `TournamentOdds`: Complete odds data structure
  - `BookmakerOdds`: Individual sportsbook odds
  - `PlayerOdds`: Player-specific betting odds
  - `Tournament`: PGA Tour tournament information
  - `PlayerStats`: Player statistics and performance data
  - `CachedData`: Local cache structure

- **`tools/odds.py`**: The Odds API client
  - Tournament odds fetching
  - Best odds aggregation
  - Sportsbook comparison
  - Rate limit tracking

- **`tools/pga.py`**: BallDontLie PGA API client
  - Tournament lookup and filtering
  - Player search and statistics
  - Course information
  - Pagination support

### API Integrations

#### The Odds API
- **Purpose**: Fetch betting odds from multiple sportsbooks (DraftKings, FanDuel, BetMGM, Caesars, etc.)
- **Client**: `mcp_server/tools/odds.py`
- **Features**:
  - Tournament odds aggregation
  - Best odds finder across all sportsbooks
  - Golf tournament discovery
  - Rate limit tracking via response headers

#### BallDontLie PGA API
- **Purpose**: Get PGA Tour tournament schedules, player data, and statistics
- **Client**: `mcp_server/tools/pga.py`
- **Features**:
  - Tournament lookup and filtering
  - Player search and statistics
  - Course information retrieval
  - Pagination support for large datasets

### Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get API keys** (both free!):
   - The Odds API: [https://the-odds-api.com](https://the-odds-api.com)
   - BallDontLie PGA: [https://www.balldontlie.io](https://www.balldontlie.io)

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Use the API clients**:
   ```python
   from mcp_server.tools.odds import OddsAPIClient
   from mcp_server.tools.pga import PGAAPIClient
   
   # Get tournament odds
   with OddsAPIClient() as client:
       odds = client.get_tournament_odds("golf_pga_championship")
   
   # Get PGA tournament info
   with PGAAPIClient() as client:
       tournament = client.get_next_tournament()
   ```

### API Rate Limits
- **The Odds API**: 500 requests/month (free tier)
- **BallDontLie PGA**: 5 requests/minute
- **Note**: The code tracks remaining requests via response headers

### Security Best Practices

⚠️ **Important**: See [AUDIT_REPORT.md](AUDIT_REPORT.md) for detailed security recommendations.

**Current Security Status:**
- ✅ API keys stored in environment variables
- ✅ HTTPS used for all API calls
- ✅ Context managers for proper resource cleanup
- ⚠️ API keys passed in query parameters (consider moving to headers)
- ⚠️ Rate limiting not yet implemented
- ⚠️ Input validation needs enhancement

**Recommended Improvements:**
1. Move API keys from query params to headers (if API supports)
2. Add rate limiting to prevent exceeding API limits
3. Implement comprehensive error handling
4. Add input validation for all API parameters
5. Set up logging for API calls and errors

### Database Setup (Optional)

Database connections are **not yet implemented**. When ready to add database support:

1. **Choose a database**:
   - PostgreSQL (recommended for production)
   - SQLite (good for development)

2. **Add to `.env`**:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/cosmos_golf
   # or for SQLite:
   DATABASE_URL=sqlite:///./cosmos_golf.db
   ```

3. **Connection pooling** (when implemented):
   - Configure pool size and overflow limits
   - Enable connection health checks
   - Use SSL/TLS for production connections

See [AUDIT_REPORT.md](AUDIT_REPORT.md) for detailed database setup recommendations.

## 🔒 Security & Code Quality

### Audit Report
A comprehensive security and code quality audit has been performed. See **[AUDIT_REPORT.md](AUDIT_REPORT.md)** for:
- Detailed security findings
- API call best practices
- Database connection recommendations
- Code improvement suggestions
- Action items prioritized by severity

### Key Security Features
- Environment variable configuration (`.env` file)
- API keys never committed to git (see `.gitignore`)
- Type-safe data models with Pydantic
- Context managers for resource cleanup
- Structured error handling

### Development Guidelines
1. **Never commit `.env` files** - Use `.env.example` as a template
2. **Validate API keys at startup** - Fail fast if keys are missing
3. **Respect rate limits** - Implement throttling for API calls
4. **Log errors appropriately** - Don't expose sensitive data in logs
5. **Use type hints** - Maintain code quality and IDE support

## 🔮 Future Enhancements

Completed features:
- ✅ Automated odds fetching from multiple sportsbooks
- ✅ MCP Server API integration
- ✅ Type-safe data models with Pydantic
- ✅ Weekly automated tournament preview generation
- ✅ GitHub Actions CI/CD pipeline
- ✅ Historical results collection (3-year course history)
- ✅ AI-generated storylines (Claude API)
- ✅ Recent form tracking
- ✅ OWGR rankings integration
- ✅ Weather forecast integration
- ✅ HTML generation from API data
- ✅ Move previous tournament to historical (clean main list each week)

Potential future additions:
- 🔄 Database integration (recommendations in audit report)
- 🔄 Rate limiting implementation
- 🔄 Enhanced error handling and logging
- Interactive filtering and sorting
- Player comparison tool
- Historical trend analysis
- Live odds updates during tournaments
- Enhanced auto-deploy to Shopify
- Email notifications for preview completion
- Social media graphics generation

## 📄 License

This project is for COSMOS Golf use. All rights reserved.

---

**COSMOS Golf · Golf in the Cosmos · 2026 Season Preview**
