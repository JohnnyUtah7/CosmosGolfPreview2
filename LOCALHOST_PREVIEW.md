# 🌐 Local Preview Guide - See Everything in Your Browser

This guide shows you how to preview your betting previews locally before deploying to Shopify.

---

## 🚀 Quick Start (Preview Existing Files)

### View Your Current (Latest) Preview

```bash
# Start the preview server
python3 scripts/preview_server.py
```

**What happens**:
1. Server starts at `http://localhost:8000`
2. Browser opens automatically
3. `http://localhost:8000/` redirects to your **most recently updated** preview HTML

**Available URLs**:
- Main preview: http://localhost:8000/ (redirects to latest build)
- Direct file: http://localhost:8000/wm_phoenix_open_2026.html (current) or historical/amex/american_express_2026.html (past) (if that’s the latest)
- Shopify embed: http://localhost:8000/docs/shopify-embed.html
- Images: Auto-loaded from project directory

**Stop server**: Press `Ctrl+C`

---

## 🎨 Generate New HTML (Weekly Pipeline)

**Recommended:** Run the weekly orchestrator to generate this week’s preview in one go:

```bash
python3 scripts/weekly_tournament_orchestrator.py
# or: ./run_weekly.sh
```

This produces `data/{slug}_{year}_players_data.json`, `data/{slug}_{year}_storylines.json`, and `{slug}_{year}.html` (e.g. `wm_phoenix_open_2026.html`).

### Preview in Browser
```bash
python3 scripts/preview_server.py
```

**Then open**: http://localhost:8000/ (redirects to latest) or http://localhost:8000/wm_phoenix_open_2026.html

**Legacy:** The old flow used `generate_preview.py` and `generate_html.py` (different data shape). Prefer the orchestrator + `generate_tournament_html.py`.

---

## 🔧 Local Development Workflow

### Option 1: View Existing HTML (No Setup Required)

```bash
# Preview your latest build
cd /Users/chrismiller/Documents/CosmosGolfBetting
python3 scripts/preview_server.py

# Opens: http://localhost:8000/  (redirects to latest build)
```

### Pin a specific file (optional)

```bash
python3 scripts/preview_server.py --default wm_phoenix_open_2026.html
```

### Option 2: Full Workflow (Requires API Keys)

```bash
# 1. Generate this week’s preview (one command)
python3 scripts/weekly_tournament_orchestrator.py

# 2. Preview
python3 scripts/preview_server.py

# Opens: http://localhost:8000/ (latest) or open the generated {slug}_{year}.html
```

---

## 🎯 Compare Your Template with Generated HTML

You can compare side-by-side:

```bash
# Start server
python3 scripts/preview_server.py
```

**Open two browser tabs**:
1. **Your original**: http://localhost:8000/sony_open_preview.html
2. **Auto-generated**: http://localhost:8000/previews/test_preview.html

**Compare**:
- Styling matches ✅
- Data structure ✅
- Player layout ✅
- Odds display ✅

---

## 📁 File Organization for Preview

```
CosmosGolfBetting/
├── {slug}_{year}.html              ← Current week preview (repo root)
├── docs/
│   ├── shopify-embed.html          ← Shopify embed template
│   └── examples/tab_toggle_example.html
├── historical/{slug}/              ← Past events (+ optional assets/)
├── assets/brand/                   ← COSMOS logos (local / upload to Shopify)
└── scripts/preview_server.py       ← Local server
```

**Server serves from project root**, so all files are accessible:
- Root files: `http://localhost:8000/filename.html`
- Docs / examples: `http://localhost:8000/docs/...`
- Logos: `http://localhost:8000/assets/brand/COSMOS_Golf-Dec-Logo_001.png`

---

## 🛠️ Advanced Options

### Custom Port

```bash
# Use port 3000 instead
python3 scripts/preview_server.py --port 3000

# Opens: http://localhost:3000
```

### No Auto-Browser

```bash
# Start server without opening browser
python3 scripts/preview_server.py --no-browser

# Then manually open: http://localhost:8000
```

### Watch for Changes (Manual Refresh)

The server doesn't auto-reload, so after editing HTML:
1. Save your changes
2. Refresh browser (`Cmd+R` / `F5`)

---

## 🎨 Live Editing Workflow

### Edit → Preview → Refine

```bash
# Terminal 1: Start server (keep running)
python3 scripts/preview_server.py

# Terminal 2: Edit and regenerate
# ... edit scripts/generate_html.py ...
python3 scripts/generate_html.py --data previews/preview_data_*.json

# Browser: Refresh to see changes
```

---

## 📊 What You'll See

### Current Sony Open Preview

Your existing [sony_open_preview.html](sony_open_preview.html) will show:
- ✅ Complete player list
- ✅ Historical results (2023-2025)
- ✅ Odds from DraftKings
- ✅ Player storylines
- ✅ Space-themed styling
- ✅ COSMOS Golf branding

### Auto-Generated Preview

The generated HTML will have:
- ✅ Same styling as Sony Open
- ✅ Live odds from 8+ sportsbooks
- ✅ Automated best odds aggregation
- ✅ Dynamic player count
- ⚠️ Placeholder historical data (needs setup)
- ⚠️ Basic storylines (AI coming)

---

## 🔍 Testing Checklist

Use local preview to verify:

### Visual Testing
- [ ] Styling matches template
- [ ] Colors look correct (NASA theme)
- [ ] Fonts load properly
- [ ] Logo displays
- [ ] Table formatting correct
- [ ] Mobile responsive (resize browser)

### Data Testing
- [ ] Tournament name displays
- [ ] Dates are correct
- [ ] Player count accurate
- [ ] Odds are formatted (+800, -110, etc.)
- [ ] Tier badges show correct colors
- [ ] Sportsbook names display

### Functionality Testing
- [ ] Table scrolls on mobile
- [ ] Links work (if any)
- [ ] Hover effects work
- [ ] No console errors (F12 → Console)

---

## 🚀 Deploy After Preview

Once you're happy with the local preview:

### Option 1: Manual Shopify Upload
1. Download HTML from `previews/` directory
2. Log into Shopify Admin
3. Go to **Online Store** → **Pages**
4. Create/edit page
5. Paste HTML into content

### Option 2: Automated Deployment
```bash
# Deploy via script
python3 scripts/deploy_to_shopify.py \
  --html previews/tournament_preview.html \
  --page-handle weekly-pga-preview
```

### Option 3: CI/CD (GitHub Actions)
- Push to GitHub
- Workflow runs automatically
- Deploys to Shopify

---

## 💡 Pro Tips

### 1. Keep Server Running
Start the server once and leave it running while you work. Just refresh the browser to see changes.

### 2. Multiple Browsers
Test in Chrome, Safari, and Firefox to ensure compatibility.

### 3. Mobile Testing
Use browser dev tools (F12 → Device toolbar) to test mobile view.

### 4. Compare Versions
Open original template and generated HTML side-by-side in different tabs.

### 5. Save Successful Versions
Keep good versions in `previews/archive/` for reference.

---

## 🔧 Troubleshooting

### "Port 8000 already in use"
```bash
# Use a different port
python3 scripts/preview_server.py --port 8001
```

### "No HTML files found"
- Make sure you're in the project directory
- Check that HTML files exist in root or `previews/`

### Images don't load
- Ensure image files are in project root
- Check image paths in HTML (should be relative)

### Styling looks broken
- Clear browser cache (`Cmd+Shift+R` / `Ctrl+Shift+R`)
- Check CSS is inline in HTML (not external file)

---

## 📱 Mobile Preview

### Test Responsive Design

```bash
# Start server
python3 scripts/preview_server.py

# In browser:
# 1. Press F12 (open DevTools)
# 2. Click device toolbar icon (Cmd+Shift+M)
# 3. Select iPhone or Android device
# 4. See how it looks on mobile
```

---

## 🎯 Next Steps

After local preview looks good:

1. **Fine-tune HTML Generator**: Edit `scripts/generate_html.py`
2. **Add Historical Data**: Integrate `fetch_historical_results.py`
3. **Add Storylines**: Integrate `generate_storylines.py`
4. **Deploy to Shopify**: Use deployment script
5. **Set Up CI/CD**: Automate with GitHub Actions

---

## 📞 Quick Reference

| Command | Purpose |
|---------|---------|
| `python3 scripts/preview_server.py` | Start local server |
| `python3 scripts/generate_html.py --data FILE` | Generate HTML |
| `http://localhost:8000` | Preview URL |
| `Ctrl+C` | Stop server |
| `Cmd+R` / `F5` | Refresh browser |

---

**Status**: ✅ Ready to preview locally
**Required**: Python 3 (no API keys needed for viewing existing files)
**Time**: Instant (just start server)

🌐 **Let's see it in the browser!**
