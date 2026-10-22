"""
Unit Tests for Observation and Perception Layers.
"""

import unittest
from desktop_engine.models import (
    ObservationState,
    PerceptionState,
    PerceptionTarget,
    BoundingBox,
    CoordinateSpace
)
from desktop_engine.observation_engine import ObservationEngine
from desktop_engine.perception_engine import PerceptionEngine


class TestObservationAndPerception(unittest.TestCase):

    def test_observation_state_dataclass(self):
        obs = ObservationState(
            active_window_title="Visual Studio Code",
            process_name="Code.exe",
            active_window_bounds={"left": 100, "top": 50, "width": 1200, "height": 800}
        )
        data = obs.to_dict()
        self.assertEqual(data["active_window_title"], "Visual Studio Code")
        self.assertEqual(data["process_name"], "Code.exe")
        self.assertEqual(data["active_window_bounds"]["width"], 1200)

    def test_observation_engine_observe(self):
        # Test without capturing disk images to ensure safe, fast execution
        obs = ObservationEngine.observe(capture_images=False)
        self.assertIsInstance(obs, ObservationState)
        self.assertGreater(obs.screen_dimensions["width"], 0)
        self.assertGreater(obs.screen_dimensions["height"], 0)

    def test_perception_state_target_search(self):
        target1 = PerceptionTarget(
            source="ui_automation",
            type="ButtonControl",
            label="Save Document",
            bounds=BoundingBox(100, 200, 80, 30, CoordinateSpace.SCREEN)
        )
        target2 = PerceptionTarget(
            source="ocr",
            type="TextDetection",
            label="File",
            bounds=BoundingBox(10, 20, 40, 20, CoordinateSpace.SCREEN)
        )

        state = PerceptionState(ui_controls=[target1], ocr_detections=[target2])
        self.assertEqual(state.total_targets, 2)

        # Exact match
        found = state.find_target("Save Document")
        self.assertIsNotNone(found)
        self.assertEqual(found.label, "Save Document")

        # Case-insensitive substring match
        found_sub = state.find_target("save")
        self.assertIsNotNone(found_sub)
        self.assertEqual(found_sub.label, "Save Document")

        # Non-existent target
        self.assertIsNone(state.find_target("NonExistentButtonXYZ"))


if __name__ == "__main__":
    unittest.main()
