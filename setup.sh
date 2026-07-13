#!/bin/bash
# COSMOS Golf Betting - Quick Setup Script
# Run this to set up everything for this week's preview

set -e  # Exit on error

echo "🏌️  COSMOS Golf Betting - Quick Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python $python_version"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is required but not found${NC}"
    exit 1
fi

# Create virtual environment (optional but recommended)
echo ""
read -p "Create Python virtual environment? (recommended) [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "   To activate: source venv/bin/activate"
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

# Check if .env exists
echo ""
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"

    # Check if it has placeholder keys
    if grep -q "your_.*_key_here" .env; then
        echo -e "${YELLOW}⚠️  Warning: .env contains placeholder keys${NC}"
        echo "   Edit .env and add your real API keys"
    else
        echo -e "${GREEN}✓ .env appears to be configured${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "   Creating from template..."
    cp .env.example .env
    echo -e "${YELLOW}   📝 Action required: Edit .env and add your API keys${NC}"
    echo ""
    echo "   Get API keys:"
    echo "   - The Odds API: https://the-odds-api.com"
    echo "   - BallDontLie PGA: https://www.balldontlie.io"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p previews logs data/historical data/storylines
echo -e "${GREEN}✓ Directories created${NC}"

# Make scripts executable
echo ""
echo "🔧 Making scripts executable..."
chmod +x scripts/*.py
chmod +x setup.sh
echo -e "${GREEN}✓ Scripts are now executable${NC}"

# Test API connections (if .env is configured)
echo ""
if [ -f .env ] && ! grep -q "your_.*_key_here" .env; then
    echo "🧪 Testing API connections..."
    if python3 scripts/test_apis.py; then
        echo -e "${GREEN}✅ All systems ready!${NC}"
    else
        echo -e "${RED}❌ API tests failed${NC}"
        echo "   Check your API keys in .env file"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping API test (configure .env first)${NC}"
fi

# Print next steps
echo ""
echo "======================================"
echo "🎯 Next Steps"
echo "======================================"
echo ""

if [ -f .env ] && ! grep -q "your_.*_key_here" .env; then
    echo "✅ Setup complete! You're ready to run your first preview."
    echo ""
    echo "Run this to generate this week's preview:"
    echo "   python3 scripts/generate_preview.py --save-data"
    echo ""
    echo "For automated weekly runs, see:"
    echo "   - DEPLOYMENT_CHECKLIST.md (local cron jobs)"
    echo "   - CI_CD_SETUP.md (GitHub Actions automation)"
else
    echo "1. Edit .env file and add your API keys"
    echo "   - The Odds API: https://the-odds-api.com"
    echo "   - BallDontLie PGA: https://www.balldontlie.io"
    echo ""
    echo "2. Test API connections:"
    echo "   python3 scripts/test_apis.py"
    echo ""
    echo "3. Generate your first preview:"
    echo "   python3 scripts/generate_preview.py --save-data"
fi

echo ""
echo "📚 Documentation:"
echo "   - SETUP.md - Complete setup guide"
echo "   - WORKFLOW.md - Weekly automation workflow"
echo "   - CI_CD_SETUP.md - GitHub → Shopify deployment"
echo ""
echo "🚀 Happy betting analysis!"
echo ""
