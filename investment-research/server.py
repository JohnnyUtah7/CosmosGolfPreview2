"""COSMOS equity research MCP plugin — official SEC EDGAR only."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP

from edgar import EdgarClient

mcp = FastMCP("equity-research")


def _client() -> EdgarClient:
    return EdgarClient()


@mcp.tool()
def edgar_healthcheck() -> Any:
    """Verify the plugin can reach official SEC EDGAR APIs (tickers, submissions, XBRL, EFTS)."""
    with _client() as edgar:
        return edgar.healthcheck()


@mcp.tool()
def lookup_company(query: str) -> Any:
    """Resolve a ticker, CIK, or company name using SEC company_tickers files."""
    with _client() as edgar:
        return edgar.lookup_company(query)


@mcp.tool()
def company_profile(ticker_or_cik: str) -> Any:
    """Company metadata from data.sec.gov/submissions (name, SIC, exchanges, fiscal year end)."""
    with _client() as edgar:
        return edgar.company_profile(ticker_or_cik)


@mcp.tool()
def list_filings(ticker_or_cik: str, forms: Optional[str] = None, limit: int = 25) -> Any:
    """Recent EDGAR filings from the submissions API. forms is a comma list such as '10-K,10-Q,8-K,4'."""
    form_list = [f.strip() for f in forms.split(",") if f.strip()] if forms else None
    with _client() as edgar:
        return edgar.list_filings(ticker_or_cik, forms=form_list, limit=limit)


@mcp.tool()
def company_financials(ticker_or_cik: str) -> Any:
    """Latest annual and quarterly core financials from data.sec.gov XBRL companyfacts."""
    with _client() as edgar:
        return edgar.company_financials(ticker_or_cik)


@mcp.tool()
def company_concept(
    ticker_or_cik: str,
    tag: str,
    taxonomy: str = "us-gaap",
    limit: int = 20,
) -> Any:
    """Time series for one XBRL tag (e.g. NetIncomeLoss, Revenues) via companyconcept."""
    with _client() as edgar:
        return edgar.get_company_concept(
            ticker_or_cik, tag=tag, taxonomy=taxonomy, limit=limit
        )


@mcp.tool()
def search_filings(
    query: str,
    forms: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
) -> Any:
    """Full-text search across SEC filings via efts.sec.gov (official EDGAR search index)."""
    with _client() as edgar:
        return edgar.search_filings(
            query,
            forms=forms,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )


@mcp.tool()
def filing_documents(ticker_or_cik: str, accession: str) -> Any:
    """List documents in one filing from www.sec.gov/Archives/edgar index.json."""
    with _client() as edgar:
        return edgar.get_filing_documents(ticker_or_cik, accession)


if __name__ == "__main__":
    mcp.run()
