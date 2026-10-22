"""
End-to-End Unit Tests for Closed-Loop Desktop Orchestrator.
"""

import unittest
from unittest.mock import patch
from desktop_engine.orchestrator import DesktopOrchestrator
from desktop_engine.decision_engine import DecisionEngine
from desktop_engine.models import (
    ObservationState,
    PerceptionState,
    PerceptionTarget,
    BoundingBox,
    CoordinateSpace
)


class TestDesktopOrchestrator(unittest.TestCase):

    @patch("desktop_engine.action_executor.pyautogui")
    @patch("desktop_engine.observation_engine.pyautogui")
    def test_complete_closed_loop_task_lifecycle(self, mock_obs_gui, mock_exec_gui):
        mock_obs_gui.size.return_value = (1920, 1080)
        mock_exec_gui.size.return_value = (1920, 1080)

        # Sequence of 2 steps: 1. Click 'Calculate', 2. Goal Complete
        step_responses = [
            """{
                "completed": false,
                "action": "click",
                "target": "500, 400",
                "reason": "Click the calculate trigger",
                "expected_outcome": "Result computed",
                "confidence": 0.95,
                "risk": "low"
            }""",
            """{
                "completed": true,
                "action": "complete",
                "target": "none",
                "reason": "Result is computed and visible",
                "expected_outcome": "Finished",
                "confidence": 1.0,
                "risk": "low"
            }"""
        ]

        step_idx = 0
        def mocked_llm(prompt):
            nonlocal step_idx
            res = step_responses[step_idx]
            step_idx += 1
            return res

        engine = DecisionEngine(llm_callable=mocked_llm)
        logged_events = []
        spoken_events = []

        orchestrator = DesktopOrchestrator(
            decision_engine=engine,
            ui_available=False,
            ocr_available=False,
            max_steps=5,
            log_callback=lambda stage, msg: logged_events.append((stage, msg)),
            speak_callback=lambda msg: spoken_events.append(msg)
        )

        summary = orchestrator.run_task("Compute summary calculation")

        # Verify summary and steps
        self.assertFalse(summary["is_active"])
        self.assertEqual(summary["steps_taken"], 2)
        self.assertEqual(summary["current_goal"], "Compute summary calculation")

        # Verify structured trace logs emitted all pipeline stages
        log_stages = [stage for stage, _ in logged_events]
        self.assertIn("OBSERVE", log_stages)
        self.assertIn("PERCEIVE", log_stages)
        self.assertIn("CONTEXT", log_stages)
        self.assertIn("DECIDE", log_stages)
        self.assertIn("VALIDATE", log_stages)
        self.assertIn("EXECUTE", log_stages)
        self.assertIn("VERIFY", log_stages)
        self.assertIn("COMPLETE", log_stages)

        # Verify PyAutoGUI executed the approved click
        mock_exec_gui.click.assert_called_with(500, 400)


if __name__ == "__main__":
    unittest.main()
