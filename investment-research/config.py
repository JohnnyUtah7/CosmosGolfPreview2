"""Configuration for the COSMOS equity research plugin.

Talks only to official SEC EDGAR hosts:
  - www.sec.gov      ticker maps + filing archives
  - data.sec.gov     submissions + XBRL APIs
  - efts.sec.gov     full-text filing search

No API key is required. SEC fair-access rules require a descriptive
User-Agent (name + contact email) and a max of 10 requests/second.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")
load_dotenv(_HERE.parent / ".env")

DEFAULT_USER_AGENT = "Cosmos Research Investment Plugin realchrismiller@gmail.com"

SEC_EDGAR_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", DEFAULT_USER_AGENT).strip()

SEC_WWW_BASE = "https://www.sec.gov"
SEC_DATA_BASE = "https://data.sec.gov"
SEC_EFTS_BASE = "https://efts.sec.gov"

TICKERS_URL = f"{SEC_WWW_BASE}/files/company_tickers.json"
TICKERS_EXCHANGE_URL = f"{SEC_WWW_BASE}/files/company_tickers_exchange.json"
SUBMISSIONS_URL = f"{SEC_DATA_BASE}/submissions/CIK{{cik}}.json"
COMPANY_FACTS_URL = f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{{cik}}.json"
COMPANY_CONCEPT_URL = (
    f"{SEC_DATA_BASE}/api/xbrl/companyconcept/CIK{{cik}}/{{taxonomy}}/{{tag}}.json"
)
FRAMES_URL = f"{SEC_DATA_BASE}/api/xbrl/frames/{{taxonomy}}/{{tag}}/{{unit}}/{{period}}.json"
EFTS_SEARCH_URL = f"{SEC_EFTS_BASE}/LATEST/search-index"
ARCHIVES_DATA_BASE = f"{SEC_WWW_BASE}/Archives/edgar/data"

CACHE_DIR = _HERE / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# SEC fair-access: stay well under 10 requests/second.
MIN_REQUEST_INTERVAL_S = 0.12
MAX_RETRIES = 4
REQUEST_TIMEOUT_S = 45.0
TICKER_MAP_TTL_S = 24 * 60 * 60
