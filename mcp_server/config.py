"""Configuration for the MCP server."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")
DATAGOLF_API_KEY = os.getenv("DATAGOLF_API_KEY", "")

# API Base URLs
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
BALLDONTLIE_API_BASE_URL = "https://api.balldontlie.io/pga/v1"
DATAGOLF_API_BASE_URL = "https://feeds.datagolf.com"

# Cache settings
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "data.json"

# Ensure cache directory exists
CACHE_DIR.mkdir(exist_ok=True)

# Supported regions for odds
SUPPORTED_REGIONS = ["us"]

# Golf sports keys for The Odds API
# These are dynamically fetched, but here are common ones
GOLF_SPORTS_PREFIX = "golf_"
