"""
Unit tests for Deterministic SEO Scoring Model & Category Weighting.
"""

import unittest
import os
from seo_engine.models import ScoreTier
from seo_engine.fetcher import FetchResult
from seo_engine.analyzer import SEOAnalyzer
from seo_engine.scoring import SEOScoringEngine


class TestSEOScoring(unittest.TestCase):

    def _read_fixture(self, name: str) -> str:
        path = os.path.join(os.path.dirname(__file__), "fixtures", "seo", name)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_category_weights_sum_to_one(self):
        total_weight = sum(SEOScoringEngine.CATEGORY_WEIGHTS.values())
        self.assertAlmostEqual(total_weight, 1.0, places=5)

    def test_determine_tier_thresholds(self):
        self.assertEqual(SEOScoringEngine.determine_tier(95.0), ScoreTier.EXCEPTIONAL)
        self.assertEqual(SEOScoringEngine.determine_tier(90.0), ScoreTier.EXCEPTIONAL)
        self.assertEqual(SEOScoringEngine.determine_tier(85.0), ScoreTier.STRONG)
        self.assertEqual(SEOScoringEngine.determine_tier(75.0), ScoreTier.GOOD)
        self.assertEqual(SEOScoringEngine.determine_tier(65.0), ScoreTier.MODERATE)
        self.assertEqual(SEOScoringEngine.determine_tier(45.0), ScoreTier.NEEDS_IMPROVEMENT)

    def test_monotonic_scoring_relationship(self):
        # 1. Excellent page
        html_good = self._read_fixture("excellent.html")
        fetch_good = FetchResult(
            success=True,
            content=html_good,
            status_code=200,
            final_url="https://example.com",
            latency_ms=100.0,
            content_length=len(html_good),
            robots_txt="User-agent: *\nDisallow:",
            sitemap_xml="<?xml version='1.0'?><urlset></urlset>"
        )
        findings_good, _, _ = SEOAnalyzer.analyze(fetch_good)
        score_good, tier_good, cats_good = SEOScoringEngine.score_audit(findings_good)

        # 2. Poor page (missing metadata)
        html_bad = self._read_fixture("missing_metadata.html")
        fetch_bad = FetchResult(
            success=True,
            content=html_bad,
            status_code=200,
            final_url="https://example.com",
            content_length=len(html_bad)
        )
        findings_bad, _, _ = SEOAnalyzer.analyze(fetch_bad)
        score_bad, tier_bad, cats_bad = SEOScoringEngine.score_audit(findings_bad)

        # Better website must have strictly higher score than worse website
        self.assertGreater(score_good, score_bad)
        self.assertGreaterEqual(score_good, 90.0)
        self.assertEqual(tier_good, ScoreTier.EXCEPTIONAL)
        self.assertLess(score_bad, 85.0)

    def test_category_breakdown_transparency(self):
        html = self._read_fixture("excellent.html")
        fetch_res = FetchResult(success=True, content=html, status_code=200, final_url="https://example.com")
        findings, _, _ = SEOAnalyzer.analyze(fetch_res)
        _, _, category_scores = SEOScoringEngine.score_audit(findings)

        self.assertIn("Technical SEO", category_scores)
        self.assertIn("On-Page SEO", category_scores)
        self.assertIn("Content Structure", category_scores)
        self.assertIn("Structured Data", category_scores)

        for name, cs in category_scores.items():
            self.assertGreaterEqual(cs.score, 0.0)
            self.assertLessEqual(cs.score, 100.0)
            self.assertTrue(hasattr(cs, "passed_count"))
            self.assertTrue(hasattr(cs, "warning_count"))
            self.assertTrue(hasattr(cs, "critical_count"))


if __name__ == "__main__":
    unittest.main()
