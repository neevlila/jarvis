"""
Unit tests for SEO Data Models & Schemas.
"""

import unittest
from seo_engine.models import (
    EvidenceType,
    FindingSeverity,
    SEOCategory,
    ScoreTier,
    SEOFinding,
    CategoryScore,
    SEOActionItem,
    PerformanceSignalsData,
    SEOAuditReport
)


class TestSEOModels(unittest.TestCase):

    def test_enums(self):
        self.assertEqual(EvidenceType.OBSERVED.value, "OBSERVED")
        self.assertEqual(EvidenceType.INFERRED.value, "INFERRED")
        self.assertEqual(EvidenceType.UNAVAILABLE.value, "UNAVAILABLE")

        self.assertEqual(FindingSeverity.CRITICAL.value, "CRITICAL")
        self.assertEqual(FindingSeverity.PASSED.value, "PASSED")

        self.assertEqual(SEOCategory.TECHNICAL.value, "Technical SEO")
        self.assertEqual(ScoreTier.EXCEPTIONAL.value, "Exceptional")

    def test_finding_to_dict(self):
        finding = SEOFinding(
            category=SEOCategory.TECHNICAL,
            severity=FindingSeverity.HIGH,
            title="Missing meta description",
            problem="No description tag found",
            evidence="<head> lacks meta description",
            evidence_type=EvidenceType.OBSERVED,
            recommendation="Add meta description tag",
            impact="High",
            effort="Low",
            confidence=1.0
        )
        d = finding.to_dict()
        self.assertEqual(d["category"], "Technical SEO")
        self.assertEqual(d["severity"], "HIGH")
        self.assertEqual(d["impact"], "High")
        self.assertEqual(d["evidence_type"], "OBSERVED")
        self.assertEqual(d["confidence"], 1.0)

    def test_category_score_to_dict(self):
        cs = CategoryScore(
            category=SEOCategory.ON_PAGE,
            score=85.5,
            weight=0.20,
            passed_count=4,
            warning_count=1,
            critical_count=0,
            checks_summary=["✓ Title present", "⚠ Short description"]
        )
        d = cs.to_dict()
        self.assertEqual(d["category"], "On-Page SEO")
        self.assertEqual(d["score"], 85.5)
        self.assertEqual(d["weight"], 0.20)
        self.assertEqual(len(d["checks_summary"]), 2)

    def test_action_item_to_dict(self):
        item = SEOActionItem(
            rank=1,
            title="Add Title Tag",
            action="Include <title> element in head",
            impact="High",
            effort="Low",
            category="Technical SEO"
        )
        d = item.to_dict()
        self.assertEqual(d["rank"], 1)
        self.assertEqual(d["title"], "Add Title Tag")

    def test_audit_report_serialization(self):
        report = SEOAuditReport(
            target="https://example.com",
            mode="url",
            overall_score=92.5,
            tier=ScoreTier.EXCEPTIONAL,
            summary="Exceptional health",
            word_count=550,
            html_title="Test Page"
        )
        d = report.to_dict()
        self.assertEqual(d["target"], "https://example.com")
        self.assertEqual(d["overall_score"], 92.5)
        self.assertEqual(d["tier"], "Exceptional")
        self.assertIn("SEO Score is a technical", d["disclaimer"])


if __name__ == "__main__":
    unittest.main()
