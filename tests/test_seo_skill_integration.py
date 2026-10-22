"""
Integration tests for SEOSkill, Skill Registry & Intelligence Coordinator.
"""

import unittest
from intelligence.models import SkillPermission, MemoryType
from intelligence.skill_engine import SkillRegistry, SEOSkill
from intelligence.coordinator import IntelligenceCoordinator
from seo_engine.engine import SEOEngine


class TestSEOSkillIntegration(unittest.TestCase):

    def setUp(self):
        self.seo_engine = SEOEngine()
        self.coordinator = IntelligenceCoordinator(seo_engine_ref=self.seo_engine)

    def test_skill_registration_and_permissions(self):
        skill = self.coordinator.skill_registry.get_skill("seo_analyzer")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.metadata.name, "seo_analyzer")

        # Verify least privilege permissions
        perms = skill.metadata.permissions
        self.assertIn(SkillPermission.NETWORK, perms)
        self.assertIn(SkillPermission.READ_FILES, perms)
        self.assertNotIn(SkillPermission.EXECUTE_COMMAND, perms)
        self.assertNotIn(SkillPermission.SYSTEM_CONTROL, perms)

    def test_intent_discovery(self):
        matches = self.coordinator.skill_registry.discover_skills("Please run an SEO audit on website")
        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0][0].metadata.name, "seo_analyzer")

    def test_coordinator_analyze_seo_local_fixture(self):
        report = self.coordinator.analyze_seo(
            url_or_path="tests/fixtures/seo/excellent.html",
            mode="project",
            use_llm=False
        )

        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.overall_score, 85.0)

        # Check memory storage
        memories = self.coordinator.memory_engine.retrieve("SEO Audit", limit=5)
        self.assertTrue(len(memories) > 0)
        self.assertTrue(any("SEO Audit for" in m.content for m in memories))

        # Check performance metrics
        snapshot = self.coordinator.get_performance_snapshot()
        self.assertGreater(snapshot.total_operations, 0)


if __name__ == "__main__":
    unittest.main()
