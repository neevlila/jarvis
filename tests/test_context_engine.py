"""
Unit Tests for Context Awareness Engine.
"""

import unittest
from desktop_engine.models import (
    ObservationState,
    PerceptionState,
    PerceptionTarget,
    BoundingBox,
    CoordinateSpace,
    ContextSource
)
from desktop_engine.context_engine import ContextEngine


class TestContextAwarenessEngine(unittest.TestCase):

    def test_observed_vs_inferred_classification(self):
        obs = ObservationState(
            active_window_title="buddy.py - J.A.R.V.I.S. - Visual Studio Code",
            process_name="Code.exe",
            system_metrics={"cpu_percent": 12.5, "ram_percent": 45.0}
        )
        t1 = PerceptionTarget(
            source="ui_automation",
            type="ButtonControl",
            label="Run and Debug",
            bounds=BoundingBox(10, 10, 50, 30, CoordinateSpace.SCREEN)
        )
        per = PerceptionState(ui_controls=[t1], ocr_detections=[])

        context = ContextEngine.build_context(obs, per, goal="Debug script")

        # 1. Application and Window Title must be strictly OBSERVED
        self.assertEqual(context.application.source, ContextSource.OBSERVED)
        self.assertEqual(context.application.value, "Code.exe")
        self.assertGreater(context.application.confidence, 0.95)

        self.assertEqual(context.window_title.source, ContextSource.OBSERVED)
        self.assertIn("Visual Studio Code", context.window_title.value)

        # 2. Activity must be strictly INFERRED
        self.assertEqual(context.activity.source, ContextSource.INFERRED)
        self.assertEqual(context.activity.value, "software_development")
        self.assertLess(context.activity.confidence, 1.0)

        # 3. Overall confidence heuristic
        self.assertGreater(context.confidence, 0.70)
        self.assertLessEqual(context.confidence, 1.0)

    def test_unknown_application_handling(self):
        obs = ObservationState(
            active_window_title="",
            process_name="",
            system_metrics={}
        )
        per = PerceptionState()

        context = ContextEngine.build_context(obs, per)
        self.assertEqual(context.application.source, ContextSource.UNKNOWN)
        self.assertEqual(context.window_title.source, ContextSource.UNKNOWN)
        self.assertEqual(context.activity.source, ContextSource.UNKNOWN)
        self.assertLess(context.confidence, 0.40)


if __name__ == "__main__":
    unittest.main()
