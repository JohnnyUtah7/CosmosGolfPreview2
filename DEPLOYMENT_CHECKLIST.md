# 🚀 Deployment Checklist - Ready to Run This Week

## ⚠️ **IMMEDIATE ACTIONS REQUIRED**

### 1. Install Python Dependencies (5 minutes)

```bash
cd /Users/chrismiller/Documents/CosmosGolfBetting

# Install required packages
pip3 install -r requirements.txt
```

**Required packages**:
- ✗ httpx (HTTP client for API calls)
- ✗ pydantic (Data validation)
- ✗ python-dotenv (Environment variables)
- ✗ mcp[cli] (MCP server framework)

---

### 2. Create .env File with API Keys (10 minutes)

```bash
# Copy template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

**Get your API keys**:

#### The Odds API
1. Go to https://the-odds-api.com
2. Click "Get API Key" (free account)
3. Copy your API key
4. Paste into `.env`: `ODDS_API_KEY=your_key_here`

#### BallDontLie PGA API
1. Go to https://www.balldontlie.io
2. Sign up (free account)
3. Go to dashboard and copy API key
4. Paste into `.env`: `BALLDONTLIE_API_KEY=your_key_here`

**Your `.env` should look like**:
```env
ODDS_API_KEY=abc123xyz789...
BALLDONTLIE_API_KEY=def456uvw012...
```

---

### 3. Test the System (2 minutes)

```bash
# Test API connections
python3 scripts/test_apis.py
```

**Expected output**:
```
🎲 Testing The Odds API...
✅ Connection successful!
   Found 3 golf events

🏌️  Testing BallDontLie PGA API...
✅ Connection successful!
   Found 5 tournaments for 2026

✅ All tests passed! You're ready to generate previews.
```

---

### 4. Generate Your First Preview (2 minutes)

```bash
# Create output directories
mkdir -p previews logs data/historical data/storylines

# Run the preview generator
python3 scripts/generate_preview.py --save-data --output-dir ./previews
```

**Expected output**:
- JSON file in `previews/` directory
- List of top 10 favorites with odds
- Sportsbook coverage report

---

## 🔍 **PRE-FLIGHT CHECKLIST**

Run this before your first production run:

```bash
#!/bin/bash

echo "=== COSMOS Golf Deployment Pre-Flight Check ==="

# 1. Check Python version
echo -n "Python version: "
python3 --version

# 2. Check dependencies
echo ""
echo "Checking dependencies..."
python3 -c "import httpx; print('✓ httpx')" 2>/dev/null || echo "✗ httpx MISSING"
python3 -c "import pydantic; print('✓ pydantic')" 2>/dev/null || echo "✗ pydantic MISSING"
python3 -c "import dotenv; print('✓ python-dotenv')" 2>/dev/null || echo "✗ python-dotenv MISSING"

# 3. Check .env file
echo ""
if [ -f .env ]; then
    echo "✓ .env file exists"
    if grep -q "your_.*_key_here" .env; then
        echo "⚠️  WARNING: .env contains placeholder keys"
    else
        echo "✓ .env has been configured"
    fi
else
    echo "✗ .env file NOT FOUND"
fi

# 4. Check directory structure
echo ""
echo "Checking directories..."
[ -d "previews" ] && echo "✓ previews/" || echo "✗ previews/ MISSING"
[ -d "logs" ] && echo "✓ logs/" || echo "✗ logs/ MISSING"
[ -d "data/historical" ] && echo "✓ data/historical/" || echo "✗ data/historical/ MISSING"

# 5. Check scripts are executable
echo ""
echo "Checking scripts..."
[ -x "scripts/test_apis.py" ] && echo "✓ test_apis.py executable" || echo "✗ test_apis.py not executable"
[ -x "scripts/generate_preview.py" ] && echo "✓ generate_preview.py executable" || echo "✗ generate_preview.py not executable"

echo ""
echo "=== Pre-Flight Check Complete ==="
```

Save as `preflight_check.sh` and run:
```bash
chmod +x preflight_check.sh
./preflight_check.sh
```

---

## 📅 **THIS WEEK'S TIMELINE**

### Day 1 (Today - Thursday)
- [ ] Install dependencies
- [ ] Get API keys
- [ ] Create .env file
- [ ] Run test_apis.py
- [ ] Verify successful connection

### Day 2 (Friday)
- [ ] Run first preview generation
- [ ] Verify JSON output
- [ ] Check odds data quality
- [ ] Review top 10 favorites

### Day 3 (Saturday/Sunday)
- [ ] Manual: Create historical data for next tournament
- [ ] Manual: Write initial storylines
- [ ] Test full workflow

### Day 4 (Monday)
- [ ] Set up GitHub repo (for CI/CD)
- [ ] Configure Shopify API access
- [ ] Test Shopify upload

### Day 5 (Tuesday)
- [ ] **First automated run!**
- [ ] Generate preview for this week's tournament
- [ ] Upload to Shopify
- [ ] Verify live page

---

## 🚨 **BLOCKERS & SOLUTIONS**

### Blocker 1: Missing Dependencies
**Solution**:
```bash
pip3 install httpx pydantic python-dotenv
```

### Blocker 2: No .env File
**Solution**:
```bash
cp .env.example .env
# Then add your API keys
```

### Blocker 3: API Keys Not Working
**Solution**:
- Verify keys are correct (no extra spaces)
- Check free tier is still active
- Test keys on API websites directly

### Blocker 4: No Tournament Data
**Solution**:
- PGA Tour season runs Feb-Aug typically
- In January, might have limited tournaments
- Test with any available golf event

---

## ✅ **SUCCESS CRITERIA**

You're ready to run this week when:

1. ✅ `python3 scripts/test_apis.py` passes all tests
2. ✅ `python3 scripts/generate_preview.py` produces JSON file
3. ✅ JSON contains odds from 5+ sportsbooks
4. ✅ JSON has data for 20+ players
5. ✅ Top 10 favorites list displays correctly

---

## 📊 **WHAT YOU'LL GET THIS WEEK**

### Automated Data Collection
- ✅ Next tournament name and date
- ✅ Odds from DraftKings, FanDuel, BetMGM, Caesars, etc.
- ✅ Best odds for each player
- ✅ Player names, countries, rankings
- ✅ Complete JSON data file

### Manual Steps (This Week)
- 📝 Create HTML from JSON (or use existing template)
- 📝 Add historical finishes manually
- 📝 Write player storylines

### Next Week (Automated)
- 🤖 HTML generation from JSON
- 🤖 Historical data integration
- 🤖 AI storyline generation
- 🤖 Auto-upload to Shopify

---

## 🔄 **AFTER FIRST SUCCESSFUL RUN**

Once you have your first preview:

1. **Save the JSON**: Keep it as a template
2. **Document the process**: Note any manual steps
3. **Set up cron job**: Schedule for next Tuesday
4. **Start CI/CD setup**: GitHub Actions + Shopify

---

**Status**: ⚠️ NEEDS SETUP (estimated 30 minutes total)
**Next Step**: Install dependencies and get API keys
**ETA to First Run**: Today if you have API keys ready
