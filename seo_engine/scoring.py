"""
Deterministic Scoring Engine for J.A.R.V.I.S. SEO Intelligence.

Evaluates findings across weighted categories, enforces score transparency,
and maps composite results into qualitative tiers.
"""

from typing import Dict, List, Any, Tuple
from seo_engine.models import (
    SEOFinding,
    FindingSeverity,
    SEOCategory,
    CategoryScore,
    ScoreTier
)


class SEOScoringEngine:
    """
    Computes transparent, weighted category scores and composite overall SEO scores.
    """

    # Centrally defined and documented category weights (Total sum = 1.00)
    CATEGORY_WEIGHTS: Dict[SEOCategory, float] = {
        SEOCategory.TECHNICAL: 0.20,
        SEOCategory.ON_PAGE: 0.20,
        SEOCategory.CONTENT_STRUCTURE: 0.15,
        SEOCategory.PERFORMANCE_SIGNALS: 0.10,
        SEOCategory.ACCESSIBILITY_SIGNALS: 0.10,
        SEOCategory.SOCIAL_METADATA: 0.10,
        SEOCategory.STRUCTURED_DATA: 0.10,
        SEOCategory.CRAWLABILITY: 0.05,
    }

    SEVERITY_PENALTIES = {
        FindingSeverity.CRITICAL: 25.0,
        FindingSeverity.HIGH: 15.0,
        FindingSeverity.MEDIUM: 8.0,
        FindingSeverity.LOW: 3.0,
        FindingSeverity.PASSED: 0.0
    }

    @classmethod
    def score_audit(
        cls,
        findings: List[SEOFinding],
        is_local: bool = False
    ) -> Tuple[float, ScoreTier, Dict[str, CategoryScore]]:
        """
        Calculates category scores, applies weights, and returns:
            overall_score: float (0.0 to 100.0)
            tier: ScoreTier
            category_scores: Dict mapping category name to CategoryScore object
        """
        # Group findings by category
        grouped: Dict[SEOCategory, List[SEOFinding]] = {cat: [] for cat in SEOCategory}
        for f in findings:
            cat = f.category if isinstance(f.category, SEOCategory) else SEOCategory(f.category)
            if cat in grouped:
                grouped[cat].append(f)

        category_scores_map: Dict[str, CategoryScore] = {}
        weighted_sum = 0.0
        total_active_weight = 0.0

        for cat, weight in cls.CATEGORY_WEIGHTS.items():
            # If in local project mode, crawlability (robots/sitemap) may be neutral or redistributed
            if is_local and cat == SEOCategory.CRAWLABILITY and not grouped[cat]:
                continue

            cat_findings = grouped[cat]
            passed_count = 0
            warning_count = 0
            critical_count = 0
            checks_summary: List[str] = []
            penalty_total = 0.0

            for f in cat_findings:
                sev = f.severity if isinstance(f.severity, FindingSeverity) else FindingSeverity(f.severity)
                if sev == FindingSeverity.PASSED:
                    passed_count += 1
                    checks_summary.append(f"✓ {f.title}")
                elif sev in (FindingSeverity.LOW, FindingSeverity.MEDIUM):
                    warning_count += 1
                    penalty_total += cls.SEVERITY_PENALTIES[sev]
                    checks_summary.append(f"⚠ {f.title}")
                elif sev in (FindingSeverity.HIGH, FindingSeverity.CRITICAL):
                    critical_count += 1
                    penalty_total += cls.SEVERITY_PENALTIES[sev]
                    checks_summary.append(f"✗ {f.title}")

            # Base score of 100 minus penalties, clamped to [0.0, 100.0]
            raw_score = 100.0 - penalty_total
            clamped_score = max(0.0, min(100.0, raw_score))

            cat_score_obj = CategoryScore(
                category=cat,
                score=clamped_score,
                weight=weight,
                passed_count=passed_count,
                warning_count=warning_count,
                critical_count=critical_count,
                checks_summary=checks_summary
            )
            category_scores_map[cat.value] = cat_score_obj

            weighted_sum += clamped_score * weight
            total_active_weight += weight

        # Normalize overall score if total active weight differs slightly (e.g. local mode)
        if total_active_weight > 0:
            overall_score = weighted_sum / total_active_weight
        else:
            overall_score = 0.0

        overall_score = max(0.0, min(100.0, overall_score))
        tier = cls.determine_tier(overall_score)

        return overall_score, tier, category_scores_map

    @staticmethod
    def determine_tier(score: float) -> ScoreTier:
        """Categorizes overall score into qualitative evaluation tiers."""
        if score >= 90.0:
            return ScoreTier.EXCEPTIONAL
        elif score >= 80.0:
            return ScoreTier.STRONG
        elif score >= 70.0:
            return ScoreTier.GOOD
        elif score >= 60.0:
            return ScoreTier.MODERATE
        else:
            return ScoreTier.NEEDS_IMPROVEMENT
