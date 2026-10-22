"""
Issue Prioritizer and Action Plan Generator for J.A.R.V.I.S. SEO Intelligence.

Prioritizes findings based on severity, impact, effort, and confidence,
synthesizing an actionable "WHAT TO FIX FIRST" plan.
"""

from typing import List
from seo_engine.models import (
    SEOFinding,
    FindingSeverity,
    SEOActionItem
)


class SEOPrioritizer:
    """
    Ranks issues by remediation impact and generates an ordered action plan.
    """

    SEVERITY_WEIGHT = {
        FindingSeverity.CRITICAL: 100.0,
        FindingSeverity.HIGH: 50.0,
        FindingSeverity.MEDIUM: 20.0,
        FindingSeverity.LOW: 5.0,
        FindingSeverity.PASSED: 0.0
    }

    IMPACT_WEIGHT = {
        "Critical": 4.0,
        "High": 3.0,
        "Medium": 2.0,
        "Low": 1.0
    }

    EFFORT_FACTOR = {
        "Low": 1.5,     # Quick wins prioritized
        "Medium": 1.0,
        "High": 0.7
    }

    @classmethod
    def prioritize_findings(cls, findings: List[SEOFinding]) -> List[SEOFinding]:
        """
        Sorts findings with critical and high impact issues first.
        Passed checks are placed at the end.
        """
        def sort_key(f: SEOFinding) -> float:
            sev = f.severity if isinstance(f.severity, FindingSeverity) else FindingSeverity(f.severity)
            if sev == FindingSeverity.PASSED:
                return -1.0
            
            sev_w = cls.SEVERITY_WEIGHT.get(sev, 10.0)
            imp_w = cls.IMPACT_WEIGHT.get(f.impact, 2.0)
            eff_f = cls.EFFORT_FACTOR.get(f.effort, 1.0)
            conf = f.confidence or 1.0

            # Priority score: High severity + high impact + quick effort + high confidence = top rank
            return sev_w * imp_w * eff_f * conf

        return sorted(findings, key=sort_key, reverse=True)

    @classmethod
    def generate_action_plan(cls, findings: List[SEOFinding], max_items: int = 7) -> List[SEOActionItem]:
        """
        Synthesizes an ordered "WHAT TO FIX FIRST" action plan from prioritized non-passed findings.
        """
        prioritized = cls.prioritize_findings(findings)
        actionable = [f for f in prioritized if f.severity != FindingSeverity.PASSED and f.recommendation]

        action_plan: List[SEOActionItem] = []
        for idx, f in enumerate(actionable[:max_items], start=1):
            category_name = f.category.value if hasattr(f.category, "value") else str(f.category)
            action_plan.append(SEOActionItem(
                rank=idx,
                title=f.title,
                action=f.recommendation,
                impact=f.impact,
                effort=f.effort,
                category=category_name,
                why_it_matters=f.why_it_matters
            ))

        return action_plan
