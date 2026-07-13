# COSMOS Golf Betting - Setup Guide

Complete setup guide for running the automated PGA tournament preview generator.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Your API Keys

#### The Odds API (FREE - 500 requests/month)
1. Go to [https://the-odds-api.com](https://the-odds-api.com)
2. Sign up for a free account
3. Copy your API key from the dashboard

#### BallDontLie PGA API (FREE - 5 requests/min)
1. Go to [https://www.balldontlie.io](https://www.balldontlie.io)
2. Create a free account
3. Copy your API key from your account dashboard

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# The Odds API - Sign up at https://the-odds-api.com
ODDS_API_KEY=your_actual_odds_api_key_here

# BallDontLie PGA API - Sign up at https://pga.balldontlie.io
BALLDONTLIE_API_KEY=your_actual_balldontlie_key_here
```

⚠️ **IMPORTANT**: Never commit your `.env` file to git!

### Quota-friendly Odds API auditing (recommended)

If you want to use The Odds API **only for audits** (minimal requests), run:

```bash
python3 scripts/audit_odds_api_amex.py --tournament "The American Express"
```

This writes `AMEX_ODDS_API_AUDIT.md` and typically uses **2 requests** total:
- 1 to list golf sports
- 1 to fetch outrights for the selected sport key

If the script can’t auto-match the tournament, it will output the available golf keys; rerun with:

```bash
python3 scripts/audit_odds_api_amex.py --sport-key <paste_key_here>
```

## 🎯 Usage

### Manual Run

Generate a preview for the next upcoming tournament:

```bash
python scripts/generate_preview.py
```

Save raw data to JSON file:

```bash
python scripts/generate_preview.py --save-data
```

Specify output directory:

```bash
python scripts/generate_preview.py --output-dir ./previews --save-data
```

### Expected Output

```
🏌️  COSMOS Golf Betting Preview Generator
============================================================

📡 Connecting to APIs...

🔍 Finding next PGA tournament...
✅ Found: Sony Open in Hawaii

🎲 Fetching betting odds...
✅ Found 3 golf events with odds:
   - PGA Championship Winner (golf_pga_championship)
   - US Open Winner (golf_us_open)
   - The Masters Winner (golf_masters)

📊 Fetching odds for: PGA Championship Winner

💰 Aggregating best odds across sportsbooks...
✅ Found odds for 85 players
   Sportsbooks: 8
   - DraftKings: 85 players
   - FanDuel: 85 players
   - BetMGM: 82 players
   - Caesars: 80 players
   ...

👥 Fetching player information...
   ✓ Scottie Scheffler (USA)
   ✓ Rory McIlroy (NIR)
   ...

============================================================
📋 PREVIEW DATA SUMMARY
============================================================
Tournament: PGA Championship Winner
Start Date: 2026-05-14 12:00:00+00:00
Total Players with Odds: 85
Sportsbooks: 8
Player Details Fetched: 10

🏆 TOP 10 FAVORITES:
 1. Scottie Scheffler        +450   [DraftKings] (USA)
 2. Rory McIlroy             +800   [FanDuel] (NIR)
 3. Jon Rahm                 +900   [BetMGM] (ESP)
 ...

✅ Preview generation complete!
```

## ⏰ Automated Weekly Runs (Cron Job)

### Setup Cron Job on macOS/Linux

Edit your crontab:

```bash
crontab -e
```

Add one of these schedules:

#### Run every Tuesday at 10 AM
```cron
0 10 * * 2 cd /Users/chrismiller/Documents/CosmosGolfBetting && /usr/bin/python3 scripts/generate_preview.py --save-data --output-dir ./previews >> logs/cron.log 2>&1
```

#### Run every Monday at 9 AM
```cron
0 9 * * 1 cd /Users/chrismiller/Documents/CosmosGolfBetting && /usr/bin/python3 scripts/generate_preview.py --save-data --output-dir ./previews >> logs/cron.log 2>&1
```

#### Run every Sunday at midnight
```cron
0 0 * * 0 cd /Users/chrismiller/Documents/CosmosGolfBetting && /usr/bin/python3 scripts/generate_preview.py --save-data --output-dir ./previews >> logs/cron.log 2>&1
```

### Create Logs Directory

```bash
mkdir -p logs
```

### Verify Cron Job

List your cron jobs:

```bash
crontab -l
```

Check the log output:

```bash
tail -f logs/cron.log
```

## 📊 API Rate Limits

### The Odds API (Free Tier)
- **500 requests/month**
- **Usage**: ~4 requests per weekly run
- **Capacity**: ~125 weeks (plenty for weekly previews!)

### BallDontLie PGA API (Free Tier)
- **5 requests/minute**
- **Usage**: ~15 requests per weekly run (well within limits)

### Optimization Tips

1. **Cache data locally** - The script uses `mcp_server/cache/` to reduce redundant API calls
2. **Run once per week** - Perfect for PGA Tour schedule (most tournaments are weekly)
3. **Monitor usage** - The script displays "API Requests Remaining" in output

## 🔧 Troubleshooting

### "ODDS_API_KEY is required"
- Make sure your `.env` file exists and has the correct API keys
- Check that `.env` is in the project root directory

### "No upcoming tournaments found"
- The PGA Tour season runs Feb-Aug typically
- Check the BallDontLie API for available tournaments
- Try running manually to see available events

### "Rate limit exceeded"
- Wait a few minutes and try again
- For BallDontLie: Max 5 requests/min
- For The Odds API: Check your monthly quota

### Cron job not running
- Check cron logs: `tail -f logs/cron.log`
- Verify cron job is set: `crontab -l`
- Use full absolute paths in crontab
- Ensure script is executable: `chmod +x scripts/generate_preview.py`

## 📁 Project Structure

```
CosmosGolfBetting/
├── .env                          # Your API keys (DO NOT COMMIT!)
├── .env.example                  # Template for API keys
├── requirements.txt              # Python dependencies
├── SETUP.md                      # This file
├── README.md                     # Project overview
├── scripts/
│   └── generate_preview.py       # Main preview generator
├── mcp_server/
│   ├── config.py                 # Configuration
│   ├── tools/
│   │   ├── odds.py              # The Odds API client
│   │   └── pga.py               # BallDontLie PGA API client
│   ├── models/
│   │   └── schemas.py           # Data models
│   └── cache/                   # Local data cache
├── previews/                     # Generated preview files
└── logs/                         # Cron job logs
```

## 🎨 Next Steps

1. **HTML Generation** - Build automatic HTML generator from JSON data
2. **Smart Matching** - Match BallDontLie tournaments with The Odds API events
3. **Historical Data** - Fetch player historical performance at each course
4. **Auto-Upload** - Deploy to Shopify automatically
5. **Notifications** - Email/Slack alerts when new preview is ready

## 📞 Support

- **The Odds API**: https://the-odds-api.com/liveapi/guides/v4/
- **BallDontLie PGA**: https://pga.balldontlie.io
- **Project Issues**: Check the logs and API documentation

---

**COSMOS Golf · Automated Betting Previews · 2026 Season**

---

## 📰 News Agent + Storylines (Recommended)

The “news agent” runs inside `scripts/generate_storylines.py`. It fetches recent headlines via **Google News RSS** and generates storylines using either:
- **RSS-only fallback** (no LLM key required), or
- **Claude/Anthropic** (best quality; set `ANTHROPIC_API_KEY`)

### RSS-Only (No LLM key required)

```bash
python3 scripts/generate_storylines.py \
  --tournament "Sony Open" \
  --players-data ./previews/preview_data_YYYYMMDD.json \
  --output ./data/storylines_current.json
```

### Claude/Anthropic (Best Quality)

Add to your `.env`:

```env
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

Optional knobs:

```env
USE_NEWS=1
NEWS_DAYS=14
NEWS_MAX_ARTICLES=6
USE_LLM=1
```
