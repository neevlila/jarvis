"""
Unit tests for SEO Issue Prioritizer & Action Plan Generation.
"""

import unittest
from seo_engine.models import SEOFinding, FindingSeverity, SEOCategory
from seo_engine.prioritizer import SEOPrioritizer


class TestSEOPrioritizer(unittest.TestCase):

    def test_prioritization_order(self):
        low_finding = SEOFinding(
            category=SEOCategory.CONTENT_STRUCTURE,
            severity=FindingSeverity.LOW,
            title="Skipped heading levels",
            recommendation="Fix sequential heading levels",
            impact="Low",
            effort="Low"
        )
        crit_finding = SEOFinding(
            category=SEOCategory.TECHNICAL,
            severity=FindingSeverity.CRITICAL,
            title="Missing viewport meta tag",
            recommendation="Add meta viewport tag",
            impact="Critical",
            effort="Low"
        )
        med_finding = SEOFinding(
            category=SEOCategory.SOCIAL_METADATA,
            severity=FindingSeverity.MEDIUM,
            title="Missing Open Graph image",
            recommendation="Add og:image tag",
            impact="Medium",
            effort="Low"
        )
        passed_finding = SEOFinding(
            category=SEOCategory.TECHNICAL,
            severity=FindingSeverity.PASSED,
            title="Title tag well-configured",
            recommendation=""
        )

        findings = [low_finding, passed_finding, med_finding, crit_finding]
        prioritized = SEOPrioritizer.prioritize_findings(findings)

        # Critical should be first, passed should be last
        self.assertEqual(prioritized[0].title, "Missing viewport meta tag")
        self.assertEqual(prioritized[-1].title, "Title tag well-configured")

    def test_action_plan_generation(self):
        findings = [
            SEOFinding(
                category=SEOCategory.TECHNICAL,
                severity=FindingSeverity.CRITICAL,
                title="Missing title tag",
                recommendation="Add descriptive title",
                impact="Critical",
                effort="Low",
                why_it_matters="Primary search headline."
            ),
            SEOFinding(
                category=SEOCategory.TECHNICAL,
                severity=FindingSeverity.HIGH,
                title="Missing meta description",
                recommendation="Add 150-char description",
                impact="High",
                effort="Low"
            ),
            SEOFinding(
                category=SEOCategory.TECHNICAL,
                severity=FindingSeverity.PASSED,
                title="Canonical tag present",
                recommendation=""
            )
        ]

        action_plan = SEOPrioritizer.generate_action_plan(findings, max_items=5)
        self.assertEqual(len(action_plan), 2)
        self.assertEqual(action_plan[0].rank, 1)
        self.assertEqual(action_plan[0].title, "Missing title tag")
        self.assertEqual(action_plan[1].rank, 2)
        self.assertEqual(action_plan[1].title, "Missing meta description")


if __name__ == "__main__":
    unittest.main()
