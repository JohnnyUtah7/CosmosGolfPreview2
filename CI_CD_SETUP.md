# CI/CD Pipeline Setup - GitHub Actions → Shopify

Complete guide for setting up automated deployment from GitHub to Shopify.

## 🏗️ Architecture Overview

```
GitHub Repository (main branch)
         ↓
   [GitHub Actions Trigger]
    - Schedule: Tuesday 10 AM
    - Manual: workflow_dispatch
    - Push: main branch changes
         ↓
   [Generate Preview Job]
    1. Fetch tournament data
    2. Get odds from sportsbooks
    3. Generate JSON
    4. (Future) Generate HTML
         ↓
   [Deploy to Shopify]
    - Upload HTML to Shopify Page
    - Update existing or create new
         ↓
   Live on Shopify Store
```

---

## 📋 Prerequisites

### 1. GitHub Repository

Your code needs to be in a GitHub repository:

```bash
cd /Users/chrismiller/Documents/CosmosGolfBetting

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Automated PGA preview system"

# Create GitHub repo and push
# (Do this on github.com first, then:)
git remote add origin https://github.com/YOUR_USERNAME/CosmosGolfBetting.git
git push -u origin main
```

### 2. Shopify Admin API Access

You need a **Custom App** in Shopify to get API access:

#### Step 1: Enable Custom App Development
1. Log in to your Shopify Admin
2. Go to **Settings** → **Apps and sales channels**
3. Click **Develop apps** (top right)
4. Click **Allow custom app development**
5. Click **Allow custom app development** again to confirm

#### Step 2: Create Custom App
1. Click **Create an app**
2. App name: `COSMOS Golf Preview Automation`
3. Click **Create app**

#### Step 3: Configure API Scopes
1. Click **Configure Admin API scopes**
2. Enable these scopes:
   - ✅ `read_content` - Read access to pages
   - ✅ `write_content` - Write access to pages
3. Click **Save**

#### Step 4: Get Access Token
1. Go to **API credentials** tab
2. Click **Install app**
3. Click **Install** to confirm
4. **Copy the Admin API access token** (you'll only see this once!)
5. Save it securely - you'll add it to GitHub Secrets

**Your Shopify credentials**:
- Store URL: `YOUR_STORE.myshopify.com`
- Access Token: `shpat_xxxxx...` (starts with `shpat_`)

---

## 🔐 GitHub Secrets Configuration

Add your API keys as GitHub repository secrets:

### Navigate to Secrets
1. Go to your GitHub repository
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret**

### Add These Secrets

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `ODDS_API_KEY` | Your Odds API key | From the-odds-api.com |
| `BALLDONTLIE_API_KEY` | Your BallDontLie key | From balldontlie.io |
| `SHOPIFY_STORE_URL` | `yourstore.myshopify.com` | Your Shopify store URL |
| `SHOPIFY_ACCESS_TOKEN` | `shpat_xxxxx...` | Admin API access token |

**Important**: Never commit these values to your code!

---

## 🚀 Workflow File Explained

The workflow file [.github/workflows/deploy-preview.yml](.github/workflows/deploy-preview.yml) automates everything:

### Triggers

```yaml
# Manual trigger - Run anytime from GitHub UI
workflow_dispatch:

# Scheduled - Every Tuesday at 10 AM EST
schedule:
  - cron: '0 15 * * 2'  # 3 PM UTC = 10 AM EST

# Auto-run when code changes
push:
  branches: [main]
  paths: ['scripts/**', 'mcp_server/**']
```

### Jobs

1. **Setup Environment**
   - Checkout code
   - Install Python 3.9
   - Install dependencies

2. **Test APIs**
   - Verify API connections
   - Check credentials

3. **Generate Preview**
   - Fetch tournament data
   - Get odds from sportsbooks
   - Save JSON data

4. **Deploy to Shopify** (when ready)
   - Upload HTML to Shopify page
   - Update existing or create new

5. **Report Results**
   - Create summary
   - Upload artifacts
   - Notify on failure

---

## 📦 Deployment Script

[scripts/deploy_to_shopify.py](scripts/deploy_to_shopify.py) handles Shopify uploads:

### Features
- ✅ Create new Shopify pages
- ✅ Update existing pages
- ✅ Smart handle-based lookup
- ✅ Error handling
- ✅ Environment variable support

### Usage

```bash
# Deploy HTML to Shopify
python scripts/deploy_to_shopify.py \
  --html previews/tournament_preview.html \
  --page-handle weekly-pga-preview \
  --page-title "Sony Open Preview - January 2026"

# Or use environment variables
export SHOPIFY_STORE_URL=yourstore.myshopify.com
export SHOPIFY_ACCESS_TOKEN=shpat_xxxxx...

python scripts/deploy_to_shopify.py \
  --html previews/tournament_preview.html
```

---

## 🎯 Manual Workflow Trigger

Run the workflow manually from GitHub:

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Click **Generate and Deploy PGA Preview** (left sidebar)
4. Click **Run workflow** (right side)
5. (Optional) Enter tournament name
6. Click **Run workflow**

Watch the progress in real-time!

---

## ⏰ Scheduled Workflow

The workflow automatically runs **every Tuesday at 10 AM EST**:

```yaml
schedule:
  - cron: '0 15 * * 2'
```

**Cron schedule breakdown**:
- `0` = Minute (0 = top of the hour)
- `15` = Hour in UTC (15:00 UTC = 10:00 AM EST)
- `* * 2` = Every Tuesday

**Change schedule**:
- Mondays: `0 15 * * 1`
- Sundays: `0 15 * * 0`
- Daily: `0 15 * * *`
- Different time: Change `15` to desired hour (UTC)

---

## 🔍 Monitoring & Logs

### View Workflow Runs
1. Go to **Actions** tab on GitHub
2. See all workflow runs (success/failure)
3. Click any run to see detailed logs

### Download Artifacts
1. Open a workflow run
2. Scroll to **Artifacts** section
3. Download `preview-data` (JSON files)

### Check Logs
- Each step shows detailed output
- API quota remaining
- Player count
- Sportsbook coverage
- Error messages

---

## 🛠️ Shopify Page Setup

### Automatic Page Creation

The workflow will create a page at:
```
https://yourstore.com/pages/weekly-pga-preview
```

### Page Handle Options

Change the page URL by modifying `--page-handle`:

```python
# Weekly rotating preview
--page-handle weekly-pga-preview

# Tournament-specific
--page-handle sony-open-2026

# Date-based
--page-handle preview-2026-01-16
```

### Add Page to Navigation

After first deployment:
1. Shopify Admin → **Online Store** → **Navigation**
2. Click your main menu
3. Click **Add menu item**
4. Name: `Weekly Preview`
5. Link: `/pages/weekly-pga-preview`
6. Click **Save**

---

## 📊 Workflow Outputs

### Success Output
```
✅ Preview data generated successfully

Files Created:
- previews/preview_data_20260116.json (45.2K)

Tournament: Sony Open in Hawaii
Players: 85
Sportsbooks: 8
- DraftKings: 85 players
- FanDuel: 85 players
- BetMGM: 82 players
- Caesars: 80 players

Deployed to: https://yourstore.com/pages/weekly-pga-preview
```

### Failure Notifications
- GitHub sends email on failure
- Workflow summary shows error details
- Check API quotas and credentials

---

## 🔄 Workflow Evolution

### Phase 1 (Current - This Week)
- ✅ Automated data collection
- ✅ JSON generation
- ✅ GitHub Actions setup
- 📝 Manual HTML creation
- 📝 Manual Shopify upload

### Phase 2 (Next 2 Weeks)
- 🔧 HTML generation from JSON
- 🔧 Automated Shopify deployment
- 🔧 Historical data integration

### Phase 3 (1 Month)
- 🤖 AI storyline generation
- 📰 News integration
- 📧 Email notifications
- 📱 Social media graphics

---

## 🚨 Troubleshooting

### Workflow Fails: "API keys not configured"
**Solution**: Add secrets to GitHub repository settings

### Workflow Fails: "No upcoming tournaments"
**Solution**:
- Check PGA Tour season (Feb-Aug typically)
- In off-season, manually specify tournament

### Shopify Deployment Fails: "401 Unauthorized"
**Solution**:
- Verify Shopify access token is correct
- Check token has `write_content` scope
- Regenerate token if needed

### Workflow Doesn't Run on Schedule
**Solution**:
- Workflows only run on active repos
- Make a commit if no activity for 60 days
- Check GitHub Actions are enabled

---

## 💡 Pro Tips

1. **Test First**: Use manual trigger before relying on schedule
2. **Check Artifacts**: Download JSON to verify data quality
3. **Monitor Quotas**: Watch API request counts in logs
4. **Version Control**: Keep old previews in artifacts (30 days)
5. **Backup Pages**: Shopify auto-saves page history

---

## 📞 Support Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Shopify Admin API**: https://shopify.dev/docs/api/admin-rest
- **The Odds API**: https://the-odds-api.com/liveapi/guides/v4/
- **BallDontLie**: https://pga.balldontlie.io

---

## ✅ Setup Checklist

- [ ] Code pushed to GitHub repository
- [ ] GitHub Secrets configured (4 secrets)
- [ ] Shopify Custom App created
- [ ] Shopify API scopes enabled
- [ ] Workflow file committed
- [ ] Manual workflow test run successful
- [ ] Schedule verified (Tuesday 10 AM)
- [ ] Shopify page auto-created
- [ ] Page added to site navigation

---

**Status**: Ready for deployment
**Next**: Push to GitHub and run first workflow
**Automation Level**: 90% (HTML generation is final step)
