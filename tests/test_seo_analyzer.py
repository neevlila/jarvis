"""
Unit tests for Deterministic SEO Analyzer across synthetic HTML fixtures.
"""

import unittest
import os
from seo_engine.models import FindingSeverity, SEOCategory
from seo_engine.fetcher import FetchResult
from seo_engine.analyzer import SEOAnalyzer


class TestSEOAnalyzer(unittest.TestCase):

    def _read_fixture(self, name: str) -> str:
        path = os.path.join(os.path.dirname(__file__), "fixtures", "seo", name)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_analyze_excellent_fixture(self):
        html = self._read_fixture("excellent.html")
        fetch_res = FetchResult(
            success=True,
            content=html,
            status_code=200,
            final_url="https://example.com/quantum-shield",
            latency_ms=120.0,
            content_length=len(html)
        )

        findings, meta, perf = SEOAnalyzer.analyze(fetch_res, target_keyword="Cloud Security")

        # Verify extracted metadata
        self.assertEqual(meta["html_title"], "Quantum Shield - Next-Generation Cloud Security & Compliance")
        self.assertTrue(len(meta["meta_description"]) > 50)
        self.assertEqual(meta["canonical_url"], "https://example.com/quantum-shield")
        self.assertEqual(len(meta["h1_headings"]), 1)
        self.assertTrue(meta["word_count"] > 50)

        # Check for passing criteria
        severities = [f.severity for f in findings]
        self.assertNotIn(FindingSeverity.CRITICAL, severities)

        passed_titles = [f.title for f in findings if f.severity == FindingSeverity.PASSED]
        self.assertTrue(any("Title tag" in t for t in passed_titles))
        self.assertTrue(any("Meta description" in t for t in passed_titles))
        self.assertTrue(any("viewport" in t.lower() for t in passed_titles))
        self.assertTrue(any("JSON-LD" in t for t in passed_titles))
        self.assertTrue(any("alt" in t.lower() for t in passed_titles))

    def test_analyze_missing_metadata(self):
        html = self._read_fixture("missing_metadata.html")
        fetch_res = FetchResult(
            success=True,
            content=html,
            status_code=200,
            final_url="https://example.com/missing",
            content_length=len(html)
        )

        findings, meta, perf = SEOAnalyzer.analyze(fetch_res)

        critical_and_high = [f for f in findings if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)]
        issue_titles = [f.title for f in critical_and_high]

        self.assertTrue(any("Missing <title>" in t for t in issue_titles))
        self.assertTrue(any("Missing meta description" in t for t in issue_titles))
        self.assertTrue(any("Missing mobile viewport" in t for t in issue_titles))

    def test_analyze_bad_headings(self):
        html = self._read_fixture("bad_headings.html")
        fetch_res = FetchResult(
            success=True,
            content=html,
            status_code=200,
            final_url="https://example.com/headings",
            content_length=len(html)
        )

        findings, meta, perf = SEOAnalyzer.analyze(fetch_res)

        heading_findings = [f for f in findings if f.category == SEOCategory.CONTENT_STRUCTURE]
        titles = [f.title for f in heading_findings]

        self.assertTrue(any("Multiple <h1>" in t for t in titles))
        self.assertTrue(any("Empty sub-headings" in t for t in titles))
        self.assertTrue(any("Skipped heading levels" in t for t in titles))

    def test_analyze_missing_alt(self):
        html = self._read_fixture("missing_alt.html")
        fetch_res = FetchResult(
            success=True,
            content=html,
            status_code=200,
            final_url="https://example.com/images",
            content_length=len(html)
        )

        findings, meta, perf = SEOAnalyzer.analyze(fetch_res)

        img_findings = [f for f in findings if "alt" in f.title.lower()]
        titles = [f.title for f in img_findings]

        self.assertTrue(any("Images missing alt attribute" in t for t in titles))
        self.assertTrue(any("Generic image alt" in t for t in titles))

    def test_analyze_structured_data(self):
        html = self._read_fixture("structured_data.html")
        fetch_res = FetchResult(
            success=True,
            content=html,
            status_code=200,
            final_url="https://example.com/schema",
            content_length=len(html)
        )

        findings, meta, perf = SEOAnalyzer.analyze(fetch_res)
        schema_findings = [f for f in findings if f.category == SEOCategory.STRUCTURED_DATA]
        self.assertTrue(any(f.severity == FindingSeverity.PASSED for f in schema_findings))

    def test_analyze_malformed_schema(self):
        html = self._read_fixture("malformed_schema.html")
        fetch_res = FetchResult(
            success=True,
            content=html,
            status_code=200,
            final_url="https://example.com/broken-schema",
            content_length=len(html)
        )

        findings, meta, perf = SEOAnalyzer.analyze(fetch_res)
        schema_findings = [f for f in findings if f.category == SEOCategory.STRUCTURED_DATA]
        self.assertTrue(any(f.severity == FindingSeverity.HIGH and "Malformed" in f.title for f in schema_findings))

    def test_keyword_stuffing_warning(self):
        # 10 words total, repeated 'crypto' 5 times = 50% density -> should flag stuffing
        html = "<html><head><title>crypto</title></head><body><h1>crypto</h1><p>crypto crypto crypto buy coin now.</p></body></html>"
        fetch_res = FetchResult(
            success=True,
            content=html,
            status_code=200,
            final_url="https://example.com/spam",
            content_length=len(html)
        )

        findings, meta, perf = SEOAnalyzer.analyze(fetch_res, target_keyword="crypto")
        self.assertTrue(any("keyword stuffing" in f.title.lower() for f in findings))


if __name__ == "__main__":
    unittest.main()
