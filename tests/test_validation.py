"""
Unit Tests for Action Validation and Safety Engine.
"""

import unittest
from desktop_engine.models import (
    ActionDecision,
    ObservationState,
    PerceptionState,
    PerceptionTarget,
    BoundingBox,
    CoordinateSpace,
    RiskLevel
)
from desktop_engine.validation_engine import ValidationEngine


class TestValidationEngine(unittest.TestCase):

    def setUp(self):
        self.obs = ObservationState(
            screen_dimensions={"width": 1920, "height": 1080},
            active_window_title="Notepad",
            process_name="notepad.exe"
        )
        self.t1 = PerceptionTarget(
            source="ui_automation",
            type="ButtonControl",
            label="Save",
            bounds=BoundingBox(500, 300, 100, 40, CoordinateSpace.SCREEN)
        )
        self.perception = PerceptionState(ui_controls=[self.t1])

    def test_valid_click_by_label(self):
        raw_json = """{
            "completed": false,
            "action": "click",
            "target": "Save",
            "reason": "Click the Save button",
            "expected_outcome": "File is saved",
            "confidence": 0.95,
            "risk": "low"
        }"""
        res = ValidationEngine.validate_action(raw_json, self.obs, self.perception)
        self.assertTrue(res.is_valid)
        self.assertIsNotNone(res.validated_action)
        self.assertEqual(res.validated_action.action, "click")
        self.assertIsNotNone(res.target_screen_coords)
        self.assertEqual(res.target_screen_coords.to_tuple(), (550, 320))

    def test_valid_click_by_coordinate(self):
        raw_json = """{
            "action": "click",
            "target": "400, 250",
            "reason": "Click canvas center",
            "expected_outcome": "Canvas focused",
            "confidence": 0.90
        }"""
        res = ValidationEngine.validate_action(raw_json, self.obs, self.perception)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.target_screen_coords.to_tuple(), (400, 250))

    def test_reject_out_of_bounds_click(self):
        raw_json = """{
            "action": "click",
            "target": "3000, 500",
            "reason": "Click offscreen coordinate",
            "expected_outcome": "Nothing",
            "confidence": 0.90
        }"""
        res = ValidationEngine.validate_action(raw_json, self.obs, self.perception)
        self.assertFalse(res.is_valid)
        self.assertIn("outside screen bounds", res.reason)

    def test_reject_missing_target_in_perception(self):
        raw_json = """{
            "action": "click",
            "target": "NonExistentButtonABC",
            "reason": "Click mystery control",
            "expected_outcome": "Nothing",
            "confidence": 0.90
        }"""
        res = ValidationEngine.validate_action(raw_json, self.obs, self.perception)
        self.assertFalse(res.is_valid)
        self.assertIn("not found", res.reason)

    def test_block_destructive_actions(self):
        raw_json = """{
            "action": "launch_application",
            "target": "cmd.exe /c format C: /fs:NTFS",
            "reason": "Format hard drive",
            "expected_outcome": "Disk erased",
            "confidence": 0.99,
            "risk": "destructive"
        }"""
        res = ValidationEngine.validate_action(raw_json, self.obs, self.perception, authorized_destructive=False)
        self.assertFalse(res.is_valid)
        self.assertIn("Safety violation", res.reason)

    def test_reject_unsupported_action_schema(self):
        raw_json = """{
            "action": "teleport_mouse",
            "target": "100, 100"
        }"""
        res = ValidationEngine.validate_action(raw_json, self.obs, self.perception)
        self.assertFalse(res.is_valid)
        self.assertIn("Unsupported action verb", res.reason)


if __name__ == "__main__":
    unittest.main()
