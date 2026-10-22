"""
Unit Tests for Verification Engine and Failure Adaptation.
"""

import unittest
from desktop_engine.models import (
    ActionDecision,
    ExecutionResult,
    ObservationState,
    PerceptionState,
    PerceptionTarget,
    BoundingBox,
    CoordinateSpace,
    VerificationStatus
)
from desktop_engine.verification_engine import VerificationEngine


class TestVerificationEngine(unittest.TestCase):

    def setUp(self):
        self.pre_obs = ObservationState(
            active_window_title="Calculator",
            process_name="calc.exe"
        )
        self.pre_target = PerceptionTarget(
            source="ui_automation",
            type="ButtonControl",
            label="Five",
            bounds=BoundingBox(100, 100, 40, 40, CoordinateSpace.SCREEN)
        )
        self.pre_per = PerceptionState(ui_controls=[self.pre_target])

    def test_verify_window_transition_success(self):
        decision = ActionDecision(
            action="launch_application",
            target="notepad.exe",
            reason="Open notepad",
            expected_outcome="Notepad window opens",
            confidence=0.95
        )
        exec_res = ExecutionResult(success=True, action="launch_application", target="notepad.exe")

        post_obs = ObservationState(
            active_window_title="Untitled - Notepad",
            process_name="notepad.exe"
        )

        res = VerificationEngine.verify_outcome(
            decision=decision,
            execution=exec_res,
            pre_observation=self.pre_obs,
            post_observation=post_obs
        )
        self.assertEqual(res.status, VerificationStatus.SUCCESS)
        self.assertTrue(res.state_changed)
        self.assertTrue(res.matched_expectation)

    def test_verify_failed_execution(self):
        decision = ActionDecision(
            action="click",
            target="Save",
            reason="Save",
            expected_outcome="Saved",
            confidence=0.9
        )
        exec_res = ExecutionResult(success=False, action="click", target="Save", error="Target unreachable")

        res = VerificationEngine.verify_outcome(
            decision=decision,
            execution=exec_res,
            pre_observation=self.pre_obs,
            post_observation=self.pre_obs
        )
        self.assertEqual(res.status, VerificationStatus.FAILED)
        self.assertFalse(res.matched_expectation)

    def test_verify_uncertain_on_static_screen(self):
        decision = ActionDecision(
            action="click",
            target="500, 500",
            reason="Click somewhere",
            expected_outcome="Something changes",
            confidence=0.8
        )
        exec_res = ExecutionResult(success=True, action="click", target="500, 500")

        # Post state is identical to pre state
        res = VerificationEngine.verify_outcome(
            decision=decision,
            execution=exec_res,
            pre_observation=self.pre_obs,
            post_observation=self.pre_obs,
            pre_perception=self.pre_per,
            post_perception=self.pre_per
        )
        self.assertEqual(res.status, VerificationStatus.UNCERTAIN)
        self.assertFalse(res.state_changed)


if __name__ == "__main__":
    unittest.main()
