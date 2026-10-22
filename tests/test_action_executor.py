"""
Unit Tests for Action Executor Layer.
"""

import unittest
from unittest.mock import patch, MagicMock
from desktop_engine.models import ActionDecision, ValidationResult, Point, CoordinateSpace
from desktop_engine.action_executor import ActionExecutor


class TestActionExecutor(unittest.TestCase):

    @patch("pyautogui.click")
    def test_execute_click_with_coords(self, mock_click):
        decision = ActionDecision(
            action="click",
            target="Submit",
            reason="Click submit",
            expected_outcome="Form submitted",
            confidence=0.95
        )
        val = ValidationResult(
            is_valid=True,
            reason="Valid",
            validated_action=decision,
            target_screen_coords=Point(450, 300, CoordinateSpace.SCREEN)
        )

        res = ActionExecutor.execute(val)
        self.assertTrue(res.success)
        mock_click.assert_called_once_with(450, 300)
        self.assertEqual(res.executed_coords, (450, 300))

    @patch("pyautogui.typewrite")
    def test_execute_type_action(self, mock_typewrite):
        decision = ActionDecision(
            action="type",
            target="Hello World",
            reason="Enter text",
            expected_outcome="Text entered",
            confidence=0.99
        )
        res = ActionExecutor.execute(decision)
        self.assertTrue(res.success)
        mock_typewrite.assert_called_once_with("Hello World", interval=0.03)

    @patch("pyautogui.hotkey")
    def test_execute_hotkey_action(self, mock_hotkey):
        decision = ActionDecision(
            action="hotkey",
            target="ctrl+s",
            reason="Save file",
            expected_outcome="File saved",
            confidence=0.99
        )
        res = ActionExecutor.execute(decision)
        self.assertTrue(res.success)
        mock_hotkey.assert_called_once_with("ctrl", "s")

    def test_reject_unresolved_click(self):
        decision = ActionDecision(
            action="click",
            target="MysteryTargetWithoutCoords",
            reason="Click unknown",
            expected_outcome="Nothing",
            confidence=0.5
        )
        res = ActionExecutor.execute(decision)
        self.assertFalse(res.success)
        self.assertIn("Could not resolve screen coordinates", res.error)


if __name__ == "__main__":
    unittest.main()
