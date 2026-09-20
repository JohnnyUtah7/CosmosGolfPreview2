# COSMOS Equity Research plugin

Cursor / MCP plugin for equity research. It is wired only to the **official SEC EDGAR APIs** — no edgar.tools, sec-api.io, or other third-party filing hosts.

## Official endpoints used

| Surface | Host | Purpose |
|---|---|---|
| Ticker / CIK map | `https://www.sec.gov/files/company_tickers.json` and `company_tickers_exchange.json` | Resolve ticker, CIK, name |
| Submissions | `https://data.sec.gov/submissions/CIK##########.json` | Company profile + filing history |
| Company facts | `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` | Structured financials |
| Company concept | `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/{taxonomy}/{tag}.json` | One metric over time |
| Frames | `https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json` | Cross-company snapshot |
| Archives | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json` | Filing document list |
| Full-text search | `https://efts.sec.gov/LATEST/search-index` | Keyword search across filings |

SEC does not require an API key. Fair-access rules do require a descriptive `User-Agent` with a contact email and ≤ 10 requests/second.

Docs: [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).

## Hook up in Cursor

Copy the repo-root example config (or merge the `equity-research` block into an existing `.mcp.json`):

```bash
cp .mcp.json.example .mcp.json
```

Then set a User-Agent if you do not want the default:

```bash
cp investment-research/.env.example investment-research/.env
```

Restart MCP / Cursor so the `equity-research` server loads.

## Tools

- `edgar_healthcheck` — ping every official surface
- `lookup_company` — ticker / CIK / name
- `company_profile` — SIC, exchanges, fiscal year, addresses
- `list_filings` — 10-K / 10-Q / 8-K / Form 4 / …
- `company_financials` — latest FY + quarter for core GAAP tags
- `company_concept` — full time series for one tag
- `search_filings` — EFTS full-text search
- `filing_documents` — archive `index.json` for one accession

## Verify the SEC hookup

```bash
python3 investment-research/test_edgar_api.py
```

This hits live `sec.gov` hosts (Apple / AAPL as the public smoke-test filer).
