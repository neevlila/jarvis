import unittest
from idea_engine.models import (
    GenerationMode,
    ScoreTier,
    TechnologyProfile,
    TechnologyMapping,
    ScoreBreakdown,
    DevelopmentPhase,
    ProjectIdea,
    StackAnalysis,
    IdeaGenerationRequest,
    IdeaGenerationResult
)


class TestIdeaModels(unittest.TestCase):
    def test_score_tier_mapping(self):
        self.assertEqual(ScoreTier.EXCEPTIONAL.value, "Exceptional")
        self.assertEqual(ScoreTier.STRONG.value, "Strong")
        self.assertEqual(ScoreTier.GOOD.value, "Good")
        self.assertEqual(ScoreTier.MODERATE.value, "Moderate")
        self.assertEqual(ScoreTier.WEAK.value, "Weak")

    def test_request_cleaning(self):
        req = IdeaGenerationRequest(
            technologies=["  python  ", "FastAPI", "", "   ", "Docker"],
            mode=GenerationMode.STACK_TO_IDEAS
        )
        cleaned = req.clean_technologies()
        self.assertEqual(cleaned, ["python", "FastAPI", "Docker"])

    def test_score_breakdown_to_dict(self):
        sb = ScoreBreakdown(
            stack_compatibility=90.0,
            feasibility=85.0,
            real_world_value=88.0,
            technical_depth=82.0,
            innovation=80.0,
            portfolio_value=90.0,
            overall_score=87.0,
            tier=ScoreTier.STRONG
        )
        d = sb.to_dict()
        self.assertEqual(d["overall_score"], 87.0)
        self.assertEqual(d["tier"], "Strong")
        self.assertEqual(d["stack_compatibility"], 90.0)

    def test_project_idea_serialization(self):
        phase = DevelopmentPhase(
            phase_name="Phase 1",
            duration="1 week",
            key_tasks=["Setup API", "DB schema"],
            deliverables=["Backend endpoints"]
        )
        sb = ScoreBreakdown(
            stack_compatibility=95.0,
            feasibility=90.0,
            real_world_value=92.0,
            technical_depth=88.0,
            innovation=85.0,
            portfolio_value=90.0,
            overall_score=91.0,
            tier=ScoreTier.EXCEPTIONAL
        )
        idea = ProjectIdea(
            id="idea_123",
            title="Smart Edge Vision",
            one_line_pitch="Real-time edge object detection",
            problem="High latency in cloud CV inference",
            target_users=["Warehouse managers"],
            solution="On-premise edge processing with lightweight models",
            core_features=["Live feed OCR", "Defect detection"],
            technology_usage=[
                TechnologyMapping(technology="Python", role="Core Backend", justification="Rich CV libraries")
            ],
            architecture_summary="Edge Camera -> Python CV Service -> Local DB",
            data_flow=["Capture frame", "Run model", "Emit telemetry"],
            difficulty="Hard",
            estimated_time="3 weeks",
            score=sb,
            risks=[{"risk": "Edge thermal throttling", "mitigation": "Model quantization"}],
            future_expansion=["Multi-camera support"],
            roadmap=[phase],
            why_this_stack="Optimal balance of performance and development speed"
        )
        d = idea.to_dict()
        self.assertEqual(d["id"], "idea_123")
        self.assertEqual(d["title"], "Smart Edge Vision")
        self.assertEqual(d["score"]["tier"], "Exceptional")
        self.assertEqual(len(d["technology_usage"]), 1)
        self.assertEqual(len(d["roadmap"]), 1)


if __name__ == "__main__":
    unittest.main()
