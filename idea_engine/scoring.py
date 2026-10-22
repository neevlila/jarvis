"""
Deterministic Scoring Engine for J.A.R.V.I.S. Idea Engine.
Evaluates and scores project ideas using multi-criteria weighted heuristics and threshold tiers.
"""

from typing import Dict, Any
from idea_engine.models import ScoreBreakdown, ScoreTier


class ScoringEngine:
    """
    Computes a transparent, weighted multi-criteria score for project ideas.
    
    Formula:
    Overall Score = 0.25 * StackCompatibility
                  + 0.20 * Feasibility
                  + 0.20 * RealWorldValue
                  + 0.15 * TechnicalDepth
                  + 0.10 * Innovation
                  + 0.10 * PortfolioValue
    """

    WEIGHTS = {
        "stack_compatibility": 0.25,
        "feasibility": 0.20,
        "real_world_value": 0.20,
        "technical_depth": 0.15,
        "innovation": 0.10,
        "portfolio_value": 0.10
    }

    @classmethod
    def calculate_score(
        cls,
        stack_compatibility: float,
        feasibility: float,
        real_world_value: float,
        technical_depth: float,
        innovation: float,
        portfolio_value: float
    ) -> ScoreBreakdown:
        """
        Calculates normalized scores and maps to qualitative tiers.
        All input scores are clamped to [0.0, 100.0].
        """
        sc = max(0.0, min(100.0, float(stack_compatibility)))
        fe = max(0.0, min(100.0, float(feasibility)))
        rw = max(0.0, min(100.0, float(real_world_value)))
        td = max(0.0, min(100.0, float(technical_depth)))
        inno = max(0.0, min(100.0, float(innovation)))
        pv = max(0.0, min(100.0, float(portfolio_value)))

        overall = (
            sc * cls.WEIGHTS["stack_compatibility"]
            + fe * cls.WEIGHTS["feasibility"]
            + rw * cls.WEIGHTS["real_world_value"]
            + td * cls.WEIGHTS["technical_depth"]
            + inno * cls.WEIGHTS["innovation"]
            + pv * cls.WEIGHTS["portfolio_value"]
        )
        overall = max(0.0, min(100.0, overall))

        tier = cls.determine_tier(overall)

        return ScoreBreakdown(
            stack_compatibility=sc,
            feasibility=fe,
            real_world_value=rw,
            technical_depth=td,
            innovation=inno,
            portfolio_value=pv,
            overall_score=overall,
            tier=tier
        )

    @staticmethod
    def determine_tier(overall_score: float) -> ScoreTier:
        """Categorizes overall score into calibrated qualitative tiers."""
        if overall_score >= 90.0:
            return ScoreTier.EXCEPTIONAL
        elif overall_score >= 80.0:
            return ScoreTier.STRONG
        elif overall_score >= 70.0:
            return ScoreTier.GOOD
        elif overall_score >= 60.0:
            return ScoreTier.MODERATE
        else:
            return ScoreTier.WEAK
