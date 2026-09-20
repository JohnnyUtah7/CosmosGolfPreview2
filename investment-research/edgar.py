"""Official SEC EDGAR client for the COSMOS equity research plugin.

Every HTTP call goes to SEC-operated hosts (www.sec.gov, data.sec.gov,
efts.sec.gov). Third-party wrappers (edgar.tools, sec-api.io, etc.) are
not used.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import urljoin

import httpx

from config import (
    ARCHIVES_DATA_BASE,
    COMPANY_CONCEPT_URL,
    COMPANY_FACTS_URL,
    EFTS_SEARCH_URL,
    FRAMES_URL,
    MAX_RETRIES,
    MIN_REQUEST_INTERVAL_S,
    REQUEST_TIMEOUT_S,
    SEC_DATA_BASE,
    SEC_EDGAR_USER_AGENT,
    SEC_EFTS_BASE,
    SEC_WWW_BASE,
    SUBMISSIONS_URL,
    TICKER_MAP_TTL_S,
    TICKERS_EXCHANGE_URL,
    TICKERS_URL,
)

# Prefer these US-GAAP tags when summarizing companyfacts for research.
CORE_FINANCIAL_TAGS: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "eps_basic": ["EarningsPerShareBasic"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "stockholders_equity": ["StockholdersEquity"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
}


def pad_cik(cik: int | str) -> str:
    """Return the 10-digit CIK string required by data.sec.gov URLs."""
    digits = "".join(ch for ch in str(cik).strip() if ch.isdigit())
    if not digits:
        raise ValueError(f"Invalid CIK: {cik!r}")
    return digits.zfill(10)


def cik_no_pad(cik: int | str) -> str:
    return str(int(pad_cik(cik)))


def accession_nodash(accession: str) -> str:
    return accession.replace("-", "").strip()


def filing_index_url(cik: int | str, accession: str) -> str:
    return f"{ARCHIVES_DATA_BASE}/{cik_no_pad(cik)}/{accession_nodash(accession)}/index.json"


def filing_document_url(cik: int | str, accession: str, filename: str) -> str:
    return (
        f"{ARCHIVES_DATA_BASE}/{cik_no_pad(cik)}/"
        f"{accession_nodash(accession)}/{filename.lstrip('/')}"
    )


class EdgarClient:
    """Thin client for the public SEC EDGAR data APIs."""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = (user_agent or SEC_EDGAR_USER_AGENT).strip()
        if not self.user_agent or "@" not in self.user_agent:
            raise ValueError(
                "SEC_EDGAR_USER_AGENT must include a contact email "
                "(SEC fair-access requirement). "
                "Example: 'Cosmos Research you@example.com'"
            )
        self._client = httpx.Client(
            timeout=REQUEST_TIMEOUT_S,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, text/plain, */*",
            },
            follow_redirects=True,
        )
        self._last_request_at = 0.0
        self._ticker_rows: list[dict[str, Any]] = []
        self._ticker_loaded_at = 0.0

    def __enter__(self) -> "EdgarClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        wait = MIN_REQUEST_INTERVAL_S - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)

    def _get_json(self, url: str, params: Optional[dict[str, Any]] = None) -> Any:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            self._throttle()
            try:
                resp = self._client.get(url, params=params)
                self._last_request_at = time.monotonic()
                if resp.status_code == 403:
                    raise PermissionError(
                        "SEC EDGAR returned 403. Declare a descriptive User-Agent "
                        "with a contact email (SEC_EDGAR_USER_AGENT). "
                        f"URL: {url}"
                    )
                if resp.status_code == 404:
                    raise FileNotFoundError(f"SEC EDGAR 404: {url}")
                if resp.status_code == 429 or 500 <= resp.status_code <= 599:
                    time.sleep(min(20.0, 0.6 * (2**attempt)))
                    last_exc = httpx.HTTPStatusError(
                        f"SEC EDGAR {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    continue
                resp.raise_for_status()
                return resp.json()
            except (PermissionError, FileNotFoundError):
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(min(10.0, 0.4 * (2**attempt)))
                    continue
                raise
        raise RuntimeError(f"SEC EDGAR request failed after {MAX_RETRIES} tries: {url}") from last_exc

    # ------------------------------------------------------------------
    # Ticker / CIK directory
    # ------------------------------------------------------------------

    def _load_ticker_map(self, force: bool = False) -> list[dict[str, Any]]:
        age = time.time() - self._ticker_loaded_at
        if self._ticker_rows and not force and age < TICKER_MAP_TTL_S:
            return self._ticker_rows

        rows: list[dict[str, Any]] = []
        try:
            payload = self._get_json(TICKERS_EXCHANGE_URL)
            fields = payload.get("fields") or ["cik", "name", "ticker", "exchange"]
            for raw in payload.get("data") or []:
                record = dict(zip(fields, raw))
                rows.append(
                    {
                        "cik": pad_cik(record.get("cik")),
                        "ticker": str(record.get("ticker") or "").upper(),
                        "name": str(record.get("name") or ""),
                        "exchange": str(record.get("exchange") or ""),
                    }
                )
        except Exception:
            payload = self._get_json(TICKERS_URL)
            for item in payload.values() if isinstance(payload, dict) else payload:
                rows.append(
                    {
                        "cik": pad_cik(item.get("cik_str")),
                        "ticker": str(item.get("ticker") or "").upper(),
                        "name": str(item.get("title") or ""),
                        "exchange": "",
                    }
                )

        self._ticker_rows = rows
        self._ticker_loaded_at = time.time()
        return rows

    def lookup_company(self, query: str) -> dict[str, Any]:
        """Resolve a ticker, CIK, or company-name fragment via SEC ticker files."""
        q = (query or "").strip()
        if not q:
            raise ValueError("query is required")

        rows = self._load_ticker_map()
        q_upper = q.upper()
        digits = "".join(ch for ch in q if ch.isdigit())

        exact_ticker = [r for r in rows if r["ticker"] == q_upper]
        if exact_ticker:
            return {
                "source": TICKERS_EXCHANGE_URL,
                "query": q,
                "match_type": "ticker",
                "company": exact_ticker[0],
                "alternates": exact_ticker[1:5],
            }

        if digits and (q.upper().startswith("CIK") or q.isdigit()):
            try:
                padded = pad_cik(digits)
            except ValueError:
                padded = ""
            cik_hits = [r for r in rows if r["cik"] == padded] if padded else []
            if cik_hits:
                return {
                    "source": TICKERS_EXCHANGE_URL,
                    "query": q,
                    "match_type": "cik",
                    "company": cik_hits[0],
                    "alternates": cik_hits[1:5],
                }

        needle = q_upper
        name_hits = [r for r in rows if needle in r["name"].upper()]
        name_hits.sort(key=lambda r: (0 if r["name"].upper().startswith(needle) else 1, r["name"]))
        if name_hits:
            return {
                "source": TICKERS_EXCHANGE_URL,
                "query": q,
                "match_type": "name",
                "company": name_hits[0],
                "alternates": name_hits[1:8],
            }

        raise FileNotFoundError(f"No SEC filer matched {query!r} in company_tickers*.json")

    def resolve_cik(self, ticker_or_cik: str) -> str:
        q = (ticker_or_cik or "").strip()
        digits = "".join(ch for ch in q if ch.isdigit())
        if q.isdigit() or q.upper().startswith("CIK"):
            return pad_cik(digits)
        return self.lookup_company(q)["company"]["cik"]

    # ------------------------------------------------------------------
    # Submissions + filings
    # ------------------------------------------------------------------

    def get_submissions(self, ticker_or_cik: str) -> dict[str, Any]:
        cik = self.resolve_cik(ticker_or_cik)
        url = SUBMISSIONS_URL.format(cik=cik)
        data = self._get_json(url)
        data["_source"] = url
        data["_cik"] = cik
        return data

    def company_profile(self, ticker_or_cik: str) -> dict[str, Any]:
        data = self.get_submissions(ticker_or_cik)
        return {
            "source": data["_source"],
            "api": "data.sec.gov/submissions",
            "cik": data.get("cik") or data["_cik"],
            "name": data.get("name"),
            "tickers": data.get("tickers") or [],
            "exchanges": data.get("exchanges") or [],
            "sic": data.get("sic"),
            "sic_description": data.get("sicDescription"),
            "entity_type": data.get("entityType"),
            "ein": data.get("ein"),
            "lei": data.get("lei"),
            "fiscal_year_end": data.get("fiscalYearEnd"),
            "state_of_incorporation": data.get("stateOfIncorporation"),
            "state_of_incorporation_description": data.get(
                "stateOfIncorporationDescription"
            ),
            "phone": data.get("phone"),
            "addresses": data.get("addresses"),
            "former_names": data.get("formerNames") or [],
            "category": data.get("category"),
            "filings_recent_count": len(
                (data.get("filings") or {}).get("recent", {}).get("accessionNumber") or []
            ),
        }

    def list_filings(
        self,
        ticker_or_cik: str,
        forms: Optional[Iterable[str]] = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        data = self.get_submissions(ticker_or_cik)
        recent = (data.get("filings") or {}).get("recent") or {}
        columns = list(recent.keys())
        count = len(recent.get("accessionNumber") or [])
        wanted = {f.upper() for f in forms} if forms else None

        rows: list[dict[str, Any]] = []
        cik = data.get("cik") or data["_cik"]
        for i in range(count):
            form = recent.get("form", [None] * count)[i]
            if wanted and str(form).upper() not in wanted:
                continue
            accession = recent.get("accessionNumber", [None] * count)[i]
            primary = recent.get("primaryDocument", [None] * count)[i]
            row = {col: (recent.get(col) or [None] * count)[i] for col in columns}
            row["index_url"] = filing_index_url(cik, accession) if accession else None
            row["document_url"] = (
                filing_document_url(cik, accession, primary) if accession and primary else None
            )
            rows.append(row)
            if len(rows) >= max(1, int(limit)):
                break

        return {
            "source": data["_source"],
            "api": "data.sec.gov/submissions",
            "cik": cik,
            "name": data.get("name"),
            "forms": sorted(wanted) if wanted else None,
            "count": len(rows),
            "filings": rows,
        }

    # ------------------------------------------------------------------
    # XBRL
    # ------------------------------------------------------------------

    def get_company_facts(self, ticker_or_cik: str) -> dict[str, Any]:
        cik = self.resolve_cik(ticker_or_cik)
        url = COMPANY_FACTS_URL.format(cik=cik)
        data = self._get_json(url)
        data["_source"] = url
        return data

    def company_financials(self, ticker_or_cik: str) -> dict[str, Any]:
        """Latest FY + most-recent quarter for the core research tags."""
        facts = self.get_company_facts(ticker_or_cik)
        taxonomies = facts.get("facts") or {}
        us_gaap = taxonomies.get("us-gaap") or {}
        ifrs = taxonomies.get("ifrs-full") or {}

        extracted: dict[str, Any] = {}
        for label, tags in CORE_FINANCIAL_TAGS.items():
            picked = None
            used_tag = None
            taxonomy = None
            for tag in tags:
                if tag in us_gaap:
                    picked = _latest_facts(us_gaap[tag])
                    used_tag = tag
                    taxonomy = "us-gaap"
                    break
                if tag in ifrs:
                    picked = _latest_facts(ifrs[tag])
                    used_tag = tag
                    taxonomy = "ifrs-full"
                    break
            extracted[label] = {
                "taxonomy": taxonomy,
                "tag": used_tag,
                "annual": picked.get("annual") if picked else None,
                "quarterly": picked.get("quarterly") if picked else None,
            }

        return {
            "source": facts["_source"],
            "api": "data.sec.gov/api/xbrl/companyfacts",
            "cik": facts.get("cik"),
            "entity_name": facts.get("entityName"),
            "taxonomies": list(taxonomies.keys()),
            "metrics": extracted,
        }

    def get_company_concept(
        self,
        ticker_or_cik: str,
        tag: str,
        taxonomy: str = "us-gaap",
        limit: int = 20,
    ) -> dict[str, Any]:
        cik = self.resolve_cik(ticker_or_cik)
        url = COMPANY_CONCEPT_URL.format(cik=cik, taxonomy=taxonomy, tag=tag)
        data = self._get_json(url)
        units = data.get("units") or {}
        unit_name, observations = _preferred_unit_series(units)
        series = observations[-max(1, int(limit)) :]
        return {
            "source": url,
            "api": "data.sec.gov/api/xbrl/companyconcept",
            "cik": data.get("cik") or cik,
            "entity_name": data.get("entityName"),
            "taxonomy": data.get("taxonomy") or taxonomy,
            "tag": data.get("tag") or tag,
            "label": data.get("label"),
            "description": data.get("description"),
            "unit": unit_name,
            "count": len(series),
            "observations": series,
        }

    def get_xbrl_frame(
        self,
        tag: str,
        period: str,
        taxonomy: str = "us-gaap",
        unit: str = "USD",
        limit: int = 25,
    ) -> dict[str, Any]:
        url = FRAMES_URL.format(taxonomy=taxonomy, tag=tag, unit=unit, period=period)
        data = self._get_json(url)
        facts = data.get("data") or []
        return {
            "source": url,
            "api": "data.sec.gov/api/xbrl/frames",
            "taxonomy": taxonomy,
            "tag": tag,
            "unit": unit,
            "period": period,
            "label": data.get("label"),
            "count": min(len(facts), max(1, int(limit))),
            "facts": facts[: max(1, int(limit))],
        }

    # ------------------------------------------------------------------
    # Archives + full-text search
    # ------------------------------------------------------------------

    def get_filing_documents(self, ticker_or_cik: str, accession: str) -> dict[str, Any]:
        cik = self.resolve_cik(ticker_or_cik)
        url = filing_index_url(cik, accession)
        data = self._get_json(url)
        directory = data.get("directory") or {}
        items = directory.get("item") or []
        base = f"{ARCHIVES_DATA_BASE}/{cik_no_pad(cik)}/{accession_nodash(accession)}/"
        docs = []
        for item in items:
            name = item.get("name")
            docs.append(
                {
                    "name": name,
                    "type": item.get("type"),
                    "size": item.get("size"),
                    "last_modified": item.get("last-modified"),
                    "url": urljoin(base, name) if name else None,
                }
            )
        return {
            "source": url,
            "api": "www.sec.gov/Archives/edgar",
            "cik": cik,
            "accession": accession,
            "count": len(docs),
            "documents": docs,
        }

    def search_filings(
        self,
        query: str,
        forms: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "q": query,
            "from": 0,
            "size": max(1, min(int(limit), 100)),
        }
        if forms:
            params["forms"] = forms
        if start_date or end_date:
            params["dateRange"] = "custom"
            if start_date:
                params["startdt"] = start_date
            if end_date:
                params["enddt"] = end_date
        data = self._get_json(EFTS_SEARCH_URL, params=params)
        hits = ((data.get("hits") or {}).get("hits")) or []
        results = []
        for hit in hits:
            src = hit.get("_source") or {}
            accession = src.get("adsh")
            ciks = src.get("ciks") or []
            cik = ciks[0] if ciks else None
            results.append(
                {
                    "accession": accession,
                    "form": src.get("form") or (src.get("root_forms") or [None])[0],
                    "file_date": src.get("file_date"),
                    "period_ending": src.get("period_ending"),
                    "display_names": src.get("display_names"),
                    "ciks": ciks,
                    "file_type": src.get("file_type"),
                    "file_description": src.get("file_description"),
                    "index_url": filing_index_url(cik, accession) if cik and accession else None,
                }
            )
        return {
            "source": EFTS_SEARCH_URL,
            "api": "efts.sec.gov/LATEST/search-index",
            "query": query,
            "total": (data.get("hits") or {}).get("total"),
            "count": len(results),
            "results": results,
        }

    def healthcheck(self) -> dict[str, Any]:
        """Hit each official EDGAR surface and report status."""
        checks: list[dict[str, Any]] = []

        def _run(name: str, url: str, fn) -> None:
            started = time.monotonic()
            try:
                fn()
                checks.append(
                    {
                        "name": name,
                        "url": url,
                        "ok": True,
                        "latency_ms": int((time.monotonic() - started) * 1000),
                    }
                )
            except Exception as exc:
                checks.append(
                    {
                        "name": name,
                        "url": url,
                        "ok": False,
                        "error": str(exc),
                        "latency_ms": int((time.monotonic() - started) * 1000),
                    }
                )

        _run("ticker_map", TICKERS_EXCHANGE_URL, lambda: self._load_ticker_map(force=True))
        _run(
            "submissions",
            SUBMISSIONS_URL.format(cik="0000320193"),
            lambda: self._get_json(SUBMISSIONS_URL.format(cik="0000320193")),
        )
        _run(
            "companyfacts",
            COMPANY_FACTS_URL.format(cik="0000320193"),
            lambda: self._get_json(COMPANY_FACTS_URL.format(cik="0000320193")),
        )
        _run(
            "companyconcept",
            COMPANY_CONCEPT_URL.format(
                cik="0000320193", taxonomy="us-gaap", tag="NetIncomeLoss"
            ),
            lambda: self._get_json(
                COMPANY_CONCEPT_URL.format(
                    cik="0000320193", taxonomy="us-gaap", tag="NetIncomeLoss"
                )
            ),
        )
        _run(
            "efts_search",
            EFTS_SEARCH_URL,
            lambda: self._get_json(EFTS_SEARCH_URL, params={"q": "AAPL", "forms": "10-K", "size": 1}),
        )

        ok = all(c["ok"] for c in checks)
        return {
            "ok": ok,
            "provider": "U.S. Securities and Exchange Commission EDGAR",
            "hosts": [SEC_WWW_BASE, SEC_DATA_BASE, SEC_EFTS_BASE],
            "user_agent": self.user_agent,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }


def _preferred_unit_series(units: dict[str, Any]) -> tuple[Optional[str], list[dict[str, Any]]]:
    if not units:
        return None, []
    for preferred in ("USD", "USD/shares", "pure"):
        if preferred in units:
            series = sorted(units[preferred], key=lambda x: x.get("end") or "")
            return preferred, series
    name = next(iter(units))
    series = sorted(units[name], key=lambda x: x.get("end") or "")
    return name, series


def _latest_facts(concept: dict[str, Any]) -> dict[str, Any]:
    units = concept.get("units") or {}
    unit_name, series = _preferred_unit_series(units)
    annual = None
    quarterly = None
    for obs in reversed(series):
        fp = str(obs.get("fp") or "").upper()
        form = str(obs.get("form") or "").upper()
        packed = {
            "unit": unit_name,
            "value": obs.get("val"),
            "end": obs.get("end"),
            "fy": obs.get("fy"),
            "fp": obs.get("fp"),
            "form": obs.get("form"),
            "filed": obs.get("filed"),
            "accession": obs.get("accn"),
        }
        if annual is None and (fp == "FY" or form.startswith("10-K") or form.startswith("20-F")):
            annual = packed
        if quarterly is None and (
            fp in {"Q1", "Q2", "Q3", "Q4"} or form.startswith("10-Q")
        ):
            quarterly = packed
        if annual and quarterly:
            break
    return {"annual": annual, "quarterly": quarterly}
