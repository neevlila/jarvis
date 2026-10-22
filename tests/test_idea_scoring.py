import unittest
from idea_engine.scoring import ScoringEngine
from idea_engine.models import ScoreTier


class TestScoringEngine(unittest.TestCase):
    def test_weighted_formula_calculation(self):
        # 100 on all metrics should give 100
        score = ScoringEngine.calculate_score(
            stack_compatibility=100.0,
            feasibility=100.0,
            real_world_value=100.0,
            technical_depth=100.0,
            innovation=100.0,
            portfolio_value=100.0
        )
        self.assertEqual(score.overall_score, 100.0)
        self.assertEqual(score.tier, ScoreTier.EXCEPTIONAL)

    def test_tier_thresholds(self):
        self.assertEqual(ScoringEngine.determine_tier(95.0), ScoreTier.EXCEPTIONAL)
        self.assertEqual(ScoringEngine.determine_tier(89.9), ScoreTier.STRONG)
        self.assertEqual(ScoringEngine.determine_tier(75.0), ScoreTier.GOOD)
        self.assertEqual(ScoringEngine.determine_tier(65.0), ScoreTier.MODERATE)
        self.assertEqual(ScoringEngine.determine_tier(55.0), ScoreTier.WEAK)

    def test_clamping_behavior(self):
        score = ScoringEngine.calculate_score(
            stack_compatibility=150.0,
            feasibility=-20.0,
            real_world_value=80.0,
            technical_depth=80.0,
            innovation=80.0,
            portfolio_value=80.0
        )
        self.assertEqual(score.stack_compatibility, 100.0)
        self.assertEqual(score.feasibility, 0.0)
        self.assertTrue(0.0 <= score.overall_score <= 100.0)


if __name__ == "__main__":
    unittest.main()
