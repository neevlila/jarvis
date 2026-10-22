"""
Unit Tests for Closed-Loop Decision Engine and Failure Adaptation.
"""

import unittest
from desktop_engine.decision_engine import DecisionEngine
from desktop_engine.models import (
    ContextState,
    ContextItem,
    ContextSource,
    ObservationState,
    PerceptionState,
    PerceptionTarget,
    BoundingBox,
    CoordinateSpace
)


class TestDecisionEngine(unittest.TestCase):

    def test_decision_with_mocked_llm(self):
        # Mock LLM returning valid action
        def mock_llm(prompt):
            self.assertIn("Calculate 5 + 5", prompt)
            return """{
                "completed": false,
                "action": "click",
                "target": "Five",
                "reason": "Click 5 on calculator",
                "expected_outcome": "5 appears in display",
                "confidence": 0.95,
                "risk": "low"
            }"""

        engine = DecisionEngine(llm_callable=mock_llm)

        obs = ObservationState(active_window_title="Calculator", process_name="calc.exe")
        target = PerceptionTarget(
            source="ui_automation",
            type="ButtonControl",
            label="Five",
            bounds=BoundingBox(100, 100, 40, 40, CoordinateSpace.SCREEN)
        )
        perception = PerceptionState(ui_controls=[target])

        context = ContextState(
            application=ContextItem("calc.exe", ContextSource.OBSERVED, 0.99),
            window_title=ContextItem("Calculator", ContextSource.OBSERVED, 0.99),
            activity=ContextItem("calculation", ContextSource.INFERRED, 0.90),
            visible_text=["Five", "Plus"],
            ui_elements=["[ButtonControl] Five"],
            system_state={},
            current_goal="Calculate 5 + 5",
            recent_actions=[],
            confidence=0.92
        )

        res = engine.get_next_action(
            goal="Calculate 5 + 5",
            desktop_state=context,
            observation=obs,
            perception=perception
        )

        self.assertTrue(res.is_valid)
        self.assertEqual(res.validated_action.action, "click")
        self.assertEqual(res.validated_action.target, "Five")
        self.assertEqual(res.target_screen_coords.to_tuple(), (120, 120))

    def test_failure_memory_prompt_inclusion(self):
        recorded_prompt = {}

        def mock_llm_check_failures(prompt):
            recorded_prompt["prompt"] = prompt
            return """{
                "completed": true,
                "action": "complete",
                "target": "none",
                "reason": "Goal achieved",
                "expected_outcome": "Finished",
                "confidence": 1.0,
                "risk": "low"
            }"""

        engine = DecisionEngine(llm_callable=mock_llm_check_failures)

        failures = [
            {"action": "click", "target": "Save", "reason": "Target unreachable", "attempt": 1}
        ]

        res = engine.get_next_action(
            goal="Save file",
            desktop_state={"app": "notepad"},
            failure_memory=failures
        )

        self.assertTrue(res.is_valid)
        self.assertIn("FAILURE MEMORY", recorded_prompt["prompt"])
        self.assertIn("Target unreachable", recorded_prompt["prompt"])


if __name__ == "__main__":
    unittest.main()
