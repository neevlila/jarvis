"""
Automated Unit Tests for J.A.R.V.I.S. Idea -> Blueprint -> Master Build Prompt Engine.
Tests Blueprint ingestion, Creative Direction, 3D justification, Platform Adapters,
25+ section specification synthesis, and Completeness Scoring.
"""

import unittest

from idea_engine.models import (
    ProjectIdea,
    TechnologyMapping,
    DevelopmentPhase,
    ScoreBreakdown,
    ScoreTier,
    MasterPromptConfig,
    VisualDirection,
    MotionLevel,
    ThreeDIntensity,
    TargetPlatform,
    MasterBuildPrompt
)
from idea_engine.creative_director import CreativeDirector, CreativeDesignSpec
from idea_engine.adapters import PlatformAdapters
from idea_engine.prompt_engine import MasterPromptEngine
from idea_engine.engine import IdeaEngine


class TestMasterPromptEngine(unittest.TestCase):
    def setUp(self):
        self.sample_idea = ProjectIdea(
            id="idea-cyber-01",
            title="Sentinel AI Defense Core",
            one_line_pitch="Real-time autonomous threat detection and network vulnerability scanner.",
            problem="Security operations centers are overwhelmed by high-volume unvalidated alerts.",
            target_users="Cybersecurity engineers and DevSecOps teams",
            solution="Continuous packet analysis pipeline with AI risk prioritization.",
            core_features=[
                "Real-time packet inspection engine",
                "Automated anomaly scoring and threat correlation",
                "Visual interactive network topology map",
                "Instant firewall policy remediation generator"
            ],
            technology_usage=[
                TechnologyMapping(technology="FastAPI", role="API Backend", justification="High-throughput asynchronous event handling"),
                TechnologyMapping(technology="React", role="Frontend Dashboard", justification="Real-time interactive telemetry rendering"),
                TechnologyMapping(technology="Supabase", role="Database & Auth", justification="PostgreSQL persistence and role-based access control"),
                TechnologyMapping(technology="Docker", role="Deployment", justification="Containerized microservice architecture")
            ],
            architecture_summary="React Client -> FastAPI Event Router -> AI Threat Model -> Supabase PostgreSQL DB",
            difficulty="Hard",
            estimated_time="3 weeks",
            score=ScoreBreakdown(overall_score=94.0, tier=ScoreTier.EXCEPTIONAL),
            roadmap=[
                DevelopmentPhase(phase_name="Core Pipeline", duration="Week 1", key_tasks=["Scaffold FastAPI router", "Configure packet listener"], deliverables=["Working ingestion endpoint"]),
                DevelopmentPhase(phase_name="AI & UI", duration="Week 2", key_tasks=["Build React dashboard", "Integrate threat model"], deliverables=["Interactive HUD UI"]),
                DevelopmentPhase(phase_name="Remediation & Hardening", duration="Week 3", key_tasks=["Implement policy generator", "Security audit"], deliverables=["Production-ready MVP"])
            ],
            risks=[{"risk": "Packet drop under extreme traffic", "mitigation": "Buffer incoming packets using Redis queue."}],
            future_expansion=["Multi-cloud Kubernetes cluster support", "Autonomous honeypot deployment"]
        )

        self.engine = MasterPromptEngine()

    def test_creative_director_domain_detection(self):
        spec = CreativeDirector.analyze_design(
            idea=self.sample_idea,
            requested_visual=VisualDirection.AUTO,
            requested_motion=MotionLevel.BALANCED,
            requested_3d=ThreeDIntensity.AUTO
        )
        self.assertIsInstance(spec, CreativeDesignSpec)
        # Verify cybersecurity domain detection
        self.assertIn("cybersecurity", spec.visual_direction.lower())
        self.assertEqual(spec.palette.primary, "#00d2ff")
        self.assertTrue(spec.threed_strategy.is_justified)

    def test_creative_director_productivity_no_3d(self):
        prod_idea = ProjectIdea(
            id="idea-prod-02",
            title="Markdown Task Tracker",
            one_line_pitch="Minimalist note and task tracking tool.",
            problem="Complex bloated project management tools.",
            target_users="Individual writers and developers",
            solution="Blazing fast local-first markdown notebook.",
            core_features=["Fast markdown editing", "Local SQLite sync"],
            technology_usage=[TechnologyMapping(technology="React", role="Frontend", justification="Fast local UI")],
            architecture_summary="React Client -> Local SQLite Storage"
        )
        spec = CreativeDirector.analyze_design(
            idea=prod_idea,
            requested_visual=VisualDirection.AUTO,
            requested_motion=MotionLevel.SUBTLE,
            requested_3d=ThreeDIntensity.AUTO
        )
        # Should not force heavy WebGL 3D for simple markdown notebook
        self.assertFalse(spec.threed_strategy.is_justified)

    def test_all_25_sections_generated(self):
        config = MasterPromptConfig(
            visual_direction=VisualDirection.CINEMATIC,
            motion_level=MotionLevel.CINEMATIC,
            threed_intensity=ThreeDIntensity.IMMERSIVE,
            target_platform=TargetPlatform.UNIVERSAL
        )
        prompt = self.engine.generate_master_prompt(self.sample_idea, config)
        
        self.assertIsInstance(prompt, MasterBuildPrompt)
        self.assertEqual(prompt.idea_id, "idea-cyber-01")
        self.assertGreaterEqual(len(prompt.sections), 25)

        # Check required section keys
        required_keys = [
            "role", "vision", "requirements", "target_users",
            "information_architecture", "technical_architecture",
            "database_design", "api_design", "ai_architecture",
            "design_system", "creative_direction", "ui_requirements",
            "threed_strategy", "motion_design", "parallax",
            "responsive_design", "accessibility", "performance",
            "mobile_performance", "security", "error_handling",
            "testing", "implementation_phases", "acceptance_criteria",
            "agent_behavior"
        ]
        for k in required_keys:
            self.assertIn(k, prompt.sections)
            self.assertTrue(len(prompt.sections[k]) > 50)

    def test_platform_adapters(self):
        universal_text = "# Test Spec"
        
        antigravity_out = PlatformAdapters.adapt(universal_text, TargetPlatform.ANTIGRAVITY, "Sentinel")
        self.assertIn("antigravity_execution_rules", antigravity_out)
        self.assertIn("implementation_plan.md", antigravity_out)

        cursor_out = PlatformAdapters.adapt(universal_text, TargetPlatform.CURSOR, "Sentinel")
        self.assertIn(".cursorrules", cursor_out)

        claude_out = PlatformAdapters.adapt(universal_text, TargetPlatform.CLAUDE_CODE, "Sentinel")
        self.assertIn("CLAUDE.md", claude_out)

        lovable_out = PlatformAdapters.adapt(universal_text, TargetPlatform.LOVABLE, "Sentinel")
        self.assertIn("LOVABLE RAPID SCAFFOLDING", lovable_out)

    def test_idea_engine_master_prompt_workflow(self):
        idea_engine = IdeaEngine()
        idea_engine._session_ideas[self.sample_idea.id] = self.sample_idea

        prompt = idea_engine.generate_master_prompt(self.sample_idea.id)
        self.assertIsNotNone(prompt)
        self.assertGreaterEqual(prompt.completeness_scores.overall, 90.0)

        # Retrieve by prompt_id
        retrieved = idea_engine.get_master_prompt(prompt.prompt_id)
        self.assertEqual(retrieved.prompt_id, prompt.prompt_id)

        # Retrieve by idea_id
        by_idea = idea_engine.get_prompt_for_idea(self.sample_idea.id)
        self.assertEqual(by_idea.prompt_id, prompt.prompt_id)


if __name__ == '__main__':
    unittest.main()
