import unittest
from idea_engine.quality_control import QualityControlEngine
from idea_engine.models import ProjectIdea, TechnologyMapping, ScoreBreakdown, ScoreTier


class TestQualityControl(unittest.TestCase):
    def _create_sample_idea(self, title: str, pitch: str, solution: str, features=None, tech_usage=None):
        sb = ScoreBreakdown(
            stack_compatibility=85.0,
            feasibility=85.0,
            real_world_value=85.0,
            technical_depth=80.0,
            innovation=80.0,
            portfolio_value=85.0,
            overall_score=84.0,
            tier=ScoreTier.STRONG
        )
        return ProjectIdea(
            id="test_1",
            title=title,
            one_line_pitch=pitch,
            problem="Users struggle with productivity tracking.",
            target_users=["Developers"],
            solution=solution,
            core_features=features or ["Feature 1", "Feature 2"],
            technology_usage=tech_usage or [
                TechnologyMapping(technology="Python", role="Backend API", justification="Fast processing")
            ],
            architecture_summary="Client -> Server",
            data_flow=["Step 1", "Step 2"],
            difficulty="Medium",
            estimated_time="1 week",
            score=sb,
            risks=[],
            future_expansion=[],
            roadmap=[],
            why_this_stack="Good stack"
        )

    def test_filter_generic_todo_app(self):
        idea = self._create_sample_idea(
            title="Simple To-Do App",
            pitch="A basic to-do list manager for daily tasks",
            solution="Create a simple to-do list where users add and delete items."
        )
        approved, rejections = QualityControlEngine.filter_ideas([idea])
        self.assertEqual(len(approved), 0)
        self.assertTrue(any("anti-generic filter" in r for r in rejections))

    def test_filter_generic_weather_app(self):
        idea = self._create_sample_idea(
            title="Weather Dashboard",
            pitch="A basic weather widget showing current temp",
            solution="Fetch OpenWeather API and display temperature."
        )
        approved, rejections = QualityControlEngine.filter_ideas([idea])
        self.assertEqual(len(approved), 0)

    def test_pass_high_value_complex_project(self):
        idea = self._create_sample_idea(
            title="Autonomous Edge Drone Inspector",
            pitch="Real-time defect analysis using edge computer vision",
            solution="Deploy quantized YOLO models on Jetson Nano with telemetry backhaul."
        )
        approved, rejections = QualityControlEngine.filter_ideas([idea])
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(rejections), 0)

    def test_deduplication(self):
        idea1 = self._create_sample_idea("Code Vulnerability Scanner", "Scan AST", "Analyzes Python AST")
        idea2 = self._create_sample_idea("Code Vulnerability Scanner", "Scan AST", "Analyzes Python AST")
        approved, rejections = QualityControlEngine.filter_ideas([idea1, idea2])
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(rejections), 1)

    def test_technology_forcing_detection(self):
        bad_idea = self._create_sample_idea(
            title="AI Log Analyzer",
            pitch="Analyze server logs",
            solution="Processes log files",
            tech_usage=[
                TechnologyMapping(technology="Docker", role="Docker", justification="To run docker") # Invalid role
            ]
        )
        approved, rejections = QualityControlEngine.filter_ideas([bad_idea])
        self.assertEqual(len(approved), 0)
        self.assertTrue(any("technology-forcing" in r for r in rejections))


if __name__ == "__main__":
    unittest.main()
