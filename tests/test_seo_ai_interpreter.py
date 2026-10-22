"""
Unit tests for SEO AI Interpreter & Groundedness Safeguards.
"""

import unittest
from unittest.mock import patch
from seo_engine.models import SEOFinding, FindingSeverity, SEOCategory, CategoryScore, ScoreTier
from seo_engine.ai_interpreter import SEOAIInterpreter


class TestSEOAIInterpreter(unittest.TestCase):

    def setUp(self):
        self.category_scores = {
            "Technical SEO": CategoryScore(category=SEOCategory.TECHNICAL, score=85.0, weight=0.20, passed_count=3),
            "On-Page SEO": CategoryScore(category=SEOCategory.ON_PAGE, score=90.0, weight=0.20, passed_count=4)
        }
        self.findings = [
            SEOFinding(
                category=SEOCategory.TECHNICAL,
                severity=FindingSeverity.HIGH,
                title="Missing meta description",
                problem="No description in head",
                recommendation="Add 150-char description",
                why_it_matters="Controls snippet CTR"
            )
        ]
        self.metadata = {
            "html_title": "Example Page",
            "meta_description": "",
            "word_count": 320
        }

    def test_deterministic_fallback(self):
        summary = SEOAIInterpreter.interpret(
            target="https://example.com",
            overall_score=87.5,
            tier=ScoreTier.STRONG,
            category_scores=self.category_scores,
            findings=self.findings,
            metadata=self.metadata,
            use_llm=False
        )

        self.assertIn("Executive SEO Analysis", summary)
        self.assertIn("Strategic Remediation Plan", summary)
        self.assertIn("Missing meta description", summary)
        self.assertIn("87.5/100", summary)

    def test_output_sanitizer(self):
        bad_ai_text = "This will guarantee a #1 rank on Google for all keywords."
        cleaned = SEOAIInterpreter._sanitize_output(bad_ai_text)
        self.assertNotIn("guarantee a #1 rank", cleaned.lower())
        self.assertIn("significantly improve search visibility", cleaned)

    @patch("llm_service.LLMService.query_llm_with_fallback")
    def test_llm_failure_falls_back_gracefully(self, mock_llm):
        mock_llm.side_effect = Exception("LLM connection timeout")

        summary = SEOAIInterpreter.interpret(
            target="https://example.com",
            overall_score=75.0,
            tier=ScoreTier.GOOD,
            category_scores=self.category_scores,
            findings=self.findings,
            metadata=self.metadata,
            use_llm=True
        )

        self.assertIn("Executive SEO Analysis", summary)
        self.assertIn("75.0/100", summary)


if __name__ == "__main__":
    unittest.main()
