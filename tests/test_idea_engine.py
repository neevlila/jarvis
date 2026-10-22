import unittest
import json
from idea_engine.engine import IdeaEngine
from idea_engine.models import (
    IdeaGenerationRequest,
    GenerationMode,
    ScoreTier
)


class TestIdeaEngine(unittest.TestCase):
    def setUp(self):
        self.mock_llm_json = json.dumps([
            {
                "title": "Smart Edge Vision Inspector",
                "one_line_pitch": "Real-time edge defect detection using lightweight models",
                "problem": "Manual QA inspection in micro-manufacturing is slow and error-prone.",
                "target_users": ["Plant Operations Managers", "QA Engineers"],
                "solution": "Deploy quantized vision models locally with immediate defect alerting.",
                "core_features": [
                    "Sub-100ms video frame inspection",
                    "Defect bounding box localization",
                    "Telemetry export to dashboard"
                ],
                "technology_usage": [
                    {"technology": "Python", "role": "Pipeline Orchestrator", "justification": "Ecosystem compatibility"},
                    {"technology": "OpenCV", "role": "Video Preprocessing", "justification": "Low-latency frame acquisition"},
                    {"technology": "FastAPI", "role": "Telemetry API", "justification": "Asynchronous event distribution"}
                ],
                "architecture_summary": "Camera -> OpenCV Preprocessor -> Model Inference -> FastAPI -> Dashboard",
                "data_flow": [
                    "1. Stream frame from industrial camera",
                    "2. Run inference via edge runtime",
                    "3. Post alerts to FastAPI queue"
                ],
                "difficulty": "Hard",
                "estimated_time": "3 weeks",
                "why_this_stack": "Combines C++ optimized OpenCV with Python ML agility.",
                "scores": {
                    "stack_compatibility": 95,
                    "feasibility": 90,
                    "real_world_value": 94,
                    "technical_depth": 92,
                    "innovation": 88,
                    "portfolio_value": 95
                },
                "risks": [
                    {"risk": "Edge device overheating", "mitigation": "Dynamic frame-rate throttling"}
                ],
                "future_expansion": ["Multi-camera sync", "Cloud telemetry aggregator"],
                "roadmap": [
                    {
                        "phase_name": "Phase 1: Pipeline MVP",
                        "duration": "1 week",
                        "key_tasks": ["Camera acquisition", "Model load"],
                        "deliverables": ["Live preview CLI"]
                    }
                ]
            }
        ])

        def mock_llm(sys_prompt, user_prompt):
            return self.mock_llm_json

        self.engine = IdeaEngine(llm_callable=mock_llm)

    def test_full_pipeline_stack_to_ideas(self):
        req = IdeaGenerationRequest(
            technologies=["Python", "OpenCV", "FastAPI"],
            mode=GenerationMode.STACK_TO_IDEAS,
            experience_level="Intermediate",
            project_type="Portfolio Project",
            number_of_ideas=1
        )
        res = self.engine.generate_ideas(req)

        self.assertTrue(res.success)
        self.assertEqual(res.total_generated, 1)
        self.assertIsNotNone(res.top_recommendation)
        self.assertEqual(res.top_recommendation.title, "Smart Edge Vision Inspector")
        self.assertEqual(res.top_recommendation.score.tier, ScoreTier.EXCEPTIONAL)
        self.assertTrue(res.execution_time_ms > 0)

    def test_empty_stack_validation_error(self):
        req = IdeaGenerationRequest(
            technologies=[],
            mode=GenerationMode.STACK_TO_IDEAS
        )
        res = self.engine.generate_ideas(req)
        self.assertFalse(res.success)
        self.assertIn("cannot be empty", res.error)

    def test_problem_to_stack_validation(self):
        req = IdeaGenerationRequest(
            technologies=[],
            mode=GenerationMode.PROBLEM_TO_STACK,
            problem_statement="Reduce food waste in urban supermarkets"
        )
        res = self.engine.generate_ideas(req)
        self.assertTrue(res.success)
        self.assertEqual(res.total_generated, 1)

    def test_standalone_stack_analyzer(self):
        analysis = self.engine.analyze_stack(["Python", "PostgreSQL", "Docker"])
        self.assertIn("Relational Database", analysis.categories_present)
        self.assertTrue(len(analysis.synergies) > 0)

    def test_improve_existing_project(self):
        res = self.engine.improve_existing_project(
            title="Old Chatbot",
            technologies=["Python", "Flask"],
            features=["Basic keyword matching"]
        )
        self.assertTrue(res.success)
        self.assertEqual(res.mode, "project_improvements")


if __name__ == "__main__":
    unittest.main()
