# API Data & Matchup System - Complete Audit

**Date**: January 16, 2026
**Focus**: API data validation + Matchup tab functionality
**Status**: ✅ Enhanced with matchup support

---

## 🔍 API DATA AUDIT

### The Odds API - Data Verification

#### What We GET ✅
```json
{
  "sport_key": "golf_pga_championship",
  "sport_title": "PGA Championship Winner",
  "commence_time": "2026-05-14T12:00:00Z",
  "bookmakers": [
    {
      "bookmaker_key": "draftkings",
      "bookmaker_name": "DraftKings",
      "last_update": "2026-01-16T18:30:00Z",
      "markets": [
        {
          "key": "outrights",
          "outcomes": [
            {"name": "Scottie Scheffler", "price": 450},
            {"name": "Rory McIlroy", "price": 800},
            // ... more players
          ]
        }
      ]
    }
    // ... more bookmakers
  ]
}
```

#### Data Points Captured ✅
- ✅ **Player names** - Full names from bookmakers
- ✅ **Win odds** - American format (e.g., +450, -110)
- ✅ **Bookmaker names** - 8+ sportsbooks (DraftKings, FanDuel, BetMGM, Caesars, etc.)
- ✅ **Last update timestamp** - When odds were last refreshed
- ✅ **Tournament info** - Name, start date
- ✅ **Quota tracking** - API requests remaining/used

#### What's NOT in The Odds API ❌
- ❌ Top 5 odds (not provided)
- ❌ Top 10 odds (not provided)
- ❌ Player rankings (not in odds data)
- ❌ Historical results (not in odds data)
- ❌ Player photos (not in odds data)
- ⚠️ **Matchup odds** (h2h) - MAY be available but not guaranteed for golf

---

### BallDontLie PGA API - Data Verification

#### What We GET ✅
```json
{
  "data": [
    {
      "id": "player_12345",
      "first_name": "Scottie",
      "last_name": "Scheffler",
      "country": "USA",
      "turned_pro": 2018,
      // ... more player info
    }
  ]
}
```

#### Data Points Captured ✅
- ✅ **Player IDs** - Unique identifiers
- ✅ **Full names** - First + last
- ✅ **Countries** - 3-letter codes
- ✅ **Tournament schedules** - Dates, status
- ✅ **Course information** - Name, yardage, par

#### What's NOT in Free Tier ❌
- ❌ **Historical tournament results** (requires GOAT tier - $39.99/mo)
- ❌ **Player stats** (requires GOAT tier)
- ❌ **Leaderboards** (requires ALL-STAR tier - $9.99/mo)
- ❌ **Round-by-round data** (requires GOAT tier)

---

## 🎯 MATCHUP SYSTEM - NEW FEATURE

### Matchup Data Availability

**Status**: ⚠️ **Conditionally Available**

The Odds API supports h2h (head-to-head) markets for sports, but **golf matchups are not consistently available** across all tournaments.

#### When Matchups ARE Available
- Some sportsbooks offer player vs. player matchups
- Usually announced closer to tournament (e.g., Monday/Tuesday before)
- Common matchups: "Featured Groups" or "Round 1 Matchups"
- Example: "Scottie Scheffler vs. Rory McIlroy"

#### When Matchups are NOT Available
- Off-season or early in week
- Smaller tournaments
- Not all sportsbooks offer golf matchups
- The Odds API may not have golf h2h market

---

## 🆕 ENHANCED API CLIENT

### New Methods Added to [mcp_server/tools/odds.py](mcp_server/tools/odds.py)

#### 1. `get_matchup_odds(sport_key)`
**Purpose**: Fetch head-to-head player matchup odds

**Returns**:
```python
[
  {
    "id": "matchup_12345",
    "player1": "Scottie Scheffler",
    "player2": "Rory McIlroy",
    "commence_time": "2026-05-15T08:00:00Z",
    "bookmakers": [
      {
        "bookmaker_name": "DraftKings",
        "player1_odds": -120,
        "player2_odds": +100
      }
    ]
  }
]
```

#### 2. `get_all_markets_for_tournament(sport_key)`
**Purpose**: Get BOTH tournament odds AND matchups in one call

**Returns**:
```python
{
  "outrights": TournamentOdds(...),
  "matchups": [...],
  "has_matchups": True/False
}
```

---

## 🎨 TAB TOGGLE SYSTEM

### UI Design

```
┌────────────────────────────────────────────┐
│  [TOURNAMENT ODDS] [DAILY MATCHUPS]        │  ← Tab Navigation
├────────────────────────────────────────────┤
│                                            │
│  Currently showing content based on        │
│  active tab (toggled by JavaScript)        │
│                                            │
└────────────────────────────────────────────┘
```

### Tab 1: Tournament Odds (Default)
**Shows**: Win odds for all players
**Table Columns**:
- Rank
- Player
- OWGR (World Ranking)
- Historical Results (2025, 2024, 2023)
- Win Odds
- Top 5 (placeholder - not from API)
- Top 10 (placeholder - not from API)
- Tier Badge
- Analysis

### Tab 2: Daily Matchups
**Shows**: Head-to-head player battles
**Table Columns**:
- #
- Player 1
- VS
- Player 2
- P1 Odds
- P2 Odds
- Best Bookmaker

**If No Matchups**: Shows message "No matchup data available"

---

## 💻 JavaScript Tab Toggle

```javascript
function switchTab(tabName) {
    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}
```

---

## 📊 COMPLETE DATA FLOW

### Weekly Preview Generation with Tabs

```
1. User runs: python scripts/generate_preview.py --save-data
   ↓
2. API calls:
   - get_golf_sports() → Find tournament
   - get_all_markets_for_tournament() → Get BOTH:
     * Tournament winner odds (outrights)
     * Player matchups (h2h) if available
   ↓
3. Data processing:
   - Aggregate best odds per player
   - Group matchups by player pairs
   - Determine favorites/underdogs
   ↓
4. HTML generation:
   - Tab navigation at top
   - Tournament Odds table (default view)
   - Matchups table (hidden, toggleable)
   - JavaScript for tab switching
   ↓
5. Output:
   - preview_tournament_2026.html (with tabs!)
```

---

## ⚠️ IMPORTANT LIMITATIONS

### Data We CAN Get (100% Reliable)
1. ✅ Tournament winner odds (outrights)
2. ✅ Player names
3. ✅ Multiple sportsbook coverage
4. ✅ Best odds aggregation
5. ✅ Tournament dates/info

### Data We MIGHT Get (Conditional)
1. ⚠️ **Matchup odds (h2h)** - Only if:
   - Sportsbooks offer golf matchups
   - The Odds API has h2h market for golf
   - Tournament is close enough (usually week of)

### Data We CANNOT Get (Without Upgrade/Manual)
1. ❌ Top 5 odds - Not in API
2. ❌ Top 10 odds - Not in API
3. ❌ Historical results - Need GOAT tier or manual data
4. ❌ Player stats - Need GOAT tier
5. ❌ OWGR rankings - Not in API (manual or scrape)

---

## 🛠️ WORKAROUNDS FOR MISSING DATA

### Top 5 / Top 10 Odds
**Options**:
1. Manual entry per tournament
2. Scrape from sportsbook websites
3. Use DraftKings API (via OpticOdds - paid)
4. Leave as placeholders ("-")

### Historical Results
**Options**:
1. **Manual database** - JSON files per tournament (recommended for recurring events)
2. **Upgrade to GOAT tier** - $39.99/mo for full historical data
3. **Web scraping** - PGATour.com leaderboards
4. Use placeholders ("-") until data available

### OWGR Rankings
**Options**:
1. Manual update weekly from OWGR website
2. Scrape from DataGolf (has OWGR data)
3. Use placeholder ("-")

---

## 📋 VALIDATION CHECKLIST

When generating preview, verify:

### API Data Values
- [ ] Player names display correctly (not "undefined")
- [ ] Odds are formatted (+800, -110, not raw numbers)
- [ ] Bookmaker names show (not generic "Sportsbook")
- [ ] Dates parse correctly (not "Invalid Date")
- [ ] All tables populated (not empty)

### Matchup System
- [ ] Tab navigation visible at top
- [ ] "Tournament Odds" tab active by default
- [ ] Click "Daily Matchups" switches view
- [ ] If no matchups, shows friendly message
- [ ] If matchups exist, shows player pairs with odds

### Visual Display
- [ ] No "null" or "undefined" text
- [ ] Placeholder data clearly marked (e.g., "-" not "0")
- [ ] Colors/styling matches template
- [ ] Mobile responsive (test in browser dev tools)

---

## 🚀 NEXT STEPS

### Immediate
1. **Test matchup API** with real golf event
   ```bash
   python scripts/test_apis.py
   # Then manually test matchups:
   # python -c "from mcp_server.tools.odds import OddsAPIClient;
   #            client = OddsAPIClient();
   #            print(client.get_matchup_odds('golf_pga_championship'))"
   ```

2. **Generate preview with tabs**
   ```bash
   python scripts/generate_preview_with_tabs.py --sport-key golf_pga_championship
   ```

3. **Preview locally**
   ```bash
   python scripts/preview_server.py
   ```

### Short Term
1. Add Top 5/Top 10 manual entry system
2. Create historical results database
3. Test matchups when available (week of tournament)
4. Add OWGR rankings (manual or scraped)

### Medium Term
1. Upgrade to BallDontLie GOAT tier for historical data ($39.99/mo)
2. Integrate DataGolf API for advanced stats
3. Build admin panel for manual data entry
4. Automate OWGR updates

---

## 📞 QUICK REFERENCE

**Test APIs**:
```bash
python scripts/test_apis.py
```

**Generate with matchups**:
```bash
python scripts/generate_preview_with_tabs.py
```

**Check matchup availability**:
```python
from mcp_server.tools.odds import OddsAPIClient
client = OddsAPIClient()
markets = client.get_all_markets_for_tournament('golf_masters')
print(f"Has matchups: {markets['has_matchups']}")
print(f"Matchup count: {len(markets['matchups'])}")
```

---

**Status**: ✅ Matchup system implemented
**API Clients**: ✅ Enhanced with matchup support
**Tab UI**: ✅ Design ready for implementation
**Data Validation**: ⚠️ Needs real API testing with keys

**Sources**:
- [The Odds API Documentation](https://the-odds-api.com/liveapi/guides/v4/)
- [The Odds API Betting Markets](https://the-odds-api.com/sports-odds-data/betting-markets.html)
- [BallDontLie PGA API](https://pga.balldontlie.io)
