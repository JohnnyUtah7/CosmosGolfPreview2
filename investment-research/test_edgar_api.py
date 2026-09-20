#!/usr/bin/env python3
"""Live + unit checks that the equity research plugin talks to official SEC EDGAR APIs.

Usage:
    python3 investment-research/test_edgar_api.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    COMPANY_CONCEPT_URL,
    COMPANY_FACTS_URL,
    EFTS_SEARCH_URL,
    SEC_DATA_BASE,
    SEC_EFTS_BASE,
    SEC_WWW_BASE,
    SUBMISSIONS_URL,
    TICKERS_EXCHANGE_URL,
    TICKERS_URL,
)
from edgar import (
    EdgarClient,
    accession_nodash,
    filing_document_url,
    filing_index_url,
    pad_cik,
)


class UrlHelpersTest(unittest.TestCase):
    def test_pad_cik(self) -> None:
        self.assertEqual(pad_cik(320193), "0000320193")
        self.assertEqual(pad_cik("CIK320193"), "0000320193")
        self.assertEqual(pad_cik("0000320193"), "0000320193")

    def test_urls_point_at_sec_hosts(self) -> None:
        self.assertTrue(TICKERS_URL.startswith("https://www.sec.gov/"))
        self.assertTrue(TICKERS_EXCHANGE_URL.startswith("https://www.sec.gov/"))
        self.assertTrue(SUBMISSIONS_URL.startswith("https://data.sec.gov/"))
        self.assertTrue(COMPANY_FACTS_URL.startswith("https://data.sec.gov/api/xbrl/"))
        self.assertTrue(COMPANY_CONCEPT_URL.startswith("https://data.sec.gov/api/xbrl/"))
        self.assertTrue(EFTS_SEARCH_URL.startswith("https://efts.sec.gov/"))
        self.assertIn("sec.gov", SEC_WWW_BASE)
        self.assertIn("sec.gov", SEC_DATA_BASE)
        self.assertIn("sec.gov", SEC_EFTS_BASE)

    def test_archive_url(self) -> None:
        url = filing_index_url("0000320193", "0000320193-25-000079")
        self.assertEqual(
            url,
            "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/index.json",
        )
        self.assertEqual(accession_nodash("0000320193-25-000079"), "000032019325000079")
        doc = filing_document_url(320193, "0000320193-25-000079", "aapl-20250927.htm")
        self.assertTrue(doc.startswith("https://www.sec.gov/Archives/edgar/data/320193/"))


class LiveEdgarHookupTest(unittest.TestCase):
    """Requires network. Confirms the plugin is hooked to live SEC EDGAR."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = EdgarClient()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_healthcheck_all_official_endpoints(self) -> None:
        result = self.client.healthcheck()
        failed = [c for c in result["checks"] if not c["ok"]]
        self.assertTrue(result["ok"], msg=failed)
        self.assertEqual(result["provider"], "U.S. Securities and Exchange Commission EDGAR")
        for host in result["hosts"]:
            self.assertIn("sec.gov", host)
        self.assertGreaterEqual(len(result["checks"]), 5)

    def test_lookup_aapl(self) -> None:
        hit = self.client.lookup_company("AAPL")
        self.assertEqual(hit["company"]["ticker"], "AAPL")
        self.assertEqual(hit["company"]["cik"], "0000320193")
        self.assertIn("sec.gov", hit["source"])

    def test_submissions_profile(self) -> None:
        profile = self.client.company_profile("AAPL")
        self.assertIn("Apple", profile["name"])
        self.assertIn("AAPL", profile["tickers"])
        self.assertTrue(profile["source"].startswith("https://data.sec.gov/submissions/"))

    def test_list_10k_filings(self) -> None:
        filings = self.client.list_filings("AAPL", forms=["10-K"], limit=3)
        self.assertGreaterEqual(filings["count"], 1)
        first = filings["filings"][0]
        self.assertEqual(first["form"], "10-K")
        self.assertTrue(first["index_url"].startswith("https://www.sec.gov/Archives/edgar/"))

    def test_companyfacts_net_income(self) -> None:
        financials = self.client.company_financials("AAPL")
        self.assertTrue(financials["source"].startswith("https://data.sec.gov/api/xbrl/companyfacts/"))
        net = financials["metrics"]["net_income"]
        self.assertEqual(net["tag"], "NetIncomeLoss")
        self.assertIsNotNone(net["annual"])
        self.assertIsInstance(net["annual"]["value"], (int, float))

    def test_companyconcept_net_income(self) -> None:
        concept = self.client.get_company_concept("AAPL", "NetIncomeLoss", limit=5)
        self.assertTrue(concept["source"].startswith("https://data.sec.gov/api/xbrl/companyconcept/"))
        self.assertEqual(concept["tag"], "NetIncomeLoss")
        self.assertGreaterEqual(concept["count"], 1)

    def test_filing_documents_index(self) -> None:
        filings = self.client.list_filings("AAPL", forms=["10-K"], limit=1)
        accession = filings["filings"][0]["accessionNumber"]
        docs = self.client.get_filing_documents("AAPL", accession)
        self.assertTrue(docs["source"].startswith("https://www.sec.gov/Archives/edgar/"))
        self.assertGreater(docs["count"], 0)

    def test_efts_search(self) -> None:
        search = self.client.search_filings("AAPL", forms="10-K", limit=3)
        self.assertEqual(search["api"], "efts.sec.gov/LATEST/search-index")
        self.assertGreaterEqual(search["count"], 1)


def main() -> int:
    print("=" * 64)
    print("COSMOS equity research — SEC EDGAR hookup test")
    print("=" * 64)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print()
    if result.wasSuccessful():
        print("EDGAR hookup verified against official SEC hosts.")
        return 0
    print("EDGAR hookup FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
