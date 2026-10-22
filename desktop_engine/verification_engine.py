"""
Verification Engine for J.A.R.V.I.S. Desktop Engine.

Compares pre-action and post-action states to verify if an action's
expected outcome actually occurred.
"""

from typing import Optional, Dict, Any, List
from desktop_engine.models import (
    ObservationState,
    PerceptionState,
    ActionDecision,
    ExecutionResult,
    VerificationResult,
    VerificationStatus
)


class VerificationEngine:
    """
    Evaluates measurable environmental changes against expected outcomes.
    """

    @classmethod
    def verify_outcome(
        cls,
        decision: ActionDecision,
        execution: ExecutionResult,
        pre_observation: Optional[ObservationState],
        post_observation: Optional[ObservationState],
        pre_perception: Optional[PerceptionState] = None,
        post_perception: Optional[PerceptionState] = None
    ) -> VerificationResult:
        """
        Verifies whether the action produced the expected environmental change.
        """
        if not execution.success:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                reason=f"Action execution reported failure: {execution.error}",
                state_changed=False,
                matched_expectation=False,
                pre_observation=pre_observation,
                post_observation=post_observation
            )

        act_name = decision.action.lower().strip()
        expected = (decision.expected_outcome or "").lower()

        # Terminal actions
        if act_name in ["complete", "abort"]:
            return VerificationResult(
                status=VerificationStatus.SUCCESS,
                reason="Terminal action executed successfully",
                state_changed=True,
                matched_expectation=True,
                pre_observation=pre_observation,
                post_observation=post_observation
            )

        # Passive actions (wait, move)
        if act_name in ["wait", "move"]:
            return VerificationResult(
                status=VerificationStatus.SUCCESS,
                reason=f"Passive action '{act_name}' completed",
                state_changed=True,
                matched_expectation=True,
                pre_observation=pre_observation,
                post_observation=post_observation
            )

        # If observations are not available (mocked/test mode without pre/post state)
        if not pre_observation or not post_observation:
            return VerificationResult(
                status=VerificationStatus.SUCCESS,
                reason="Execution succeeded (no pre/post telemetry for visual diff)",
                state_changed=True,
                matched_expectation=True,
                pre_observation=pre_observation,
                post_observation=post_observation
            )

        # 1. Window change verification (for launch_application, activate_window, open)
        window_changed = (
            pre_observation.active_window_title != post_observation.active_window_title or
            pre_observation.process_name != post_observation.process_name
        )

        if act_name in ["launch_application", "activate_window"] or "window" in expected or "open" in expected:
            if window_changed or (str(decision.target).lower() in post_observation.active_window_title.lower()):
                return VerificationResult(
                    status=VerificationStatus.SUCCESS,
                    reason=f"Active window successfully updated to '{post_observation.active_window_title}'",
                    state_changed=True,
                    matched_expectation=True,
                    pre_observation=pre_observation,
                    post_observation=post_observation
                )

        # 2. Perception comparison (controls and text)
        if pre_perception and post_perception:
            pre_labels = set(c.label.lower() for c in pre_perception.ui_controls + pre_perception.ocr_detections)
            post_labels = set(c.label.lower() for c in post_perception.ui_controls + post_perception.ocr_detections)

            new_labels = post_labels - pre_labels
            removed_labels = pre_labels - post_labels

            # Check if expected text/control appeared
            for word in expected.split():
                if len(word) > 3 and any(word in lbl for lbl in new_labels):
                    return VerificationResult(
                        status=VerificationStatus.SUCCESS,
                        reason=f"Expected element containing '{word}' appeared in post-action state",
                        state_changed=True,
                        matched_expectation=True,
                        pre_observation=pre_observation,
                        post_observation=post_observation
                    )

            if new_labels or removed_labels or window_changed:
                return VerificationResult(
                    status=VerificationStatus.SUCCESS,
                    reason=f"UI state changed measurably ({len(new_labels)} new elements, {len(removed_labels)} dismissed elements)",
                    state_changed=True,
                    matched_expectation=True,
                    pre_observation=pre_observation,
                    post_observation=post_observation
                )

        # 3. For typing/hotkey actions, if execution succeeded and no crash
        if act_name in ["type", "hotkey", "press"]:
            return VerificationResult(
                status=VerificationStatus.SUCCESS,
                reason=f"Input keystrokes dispatched successfully to focused window",
                state_changed=True,
                matched_expectation=True,
                pre_observation=pre_observation,
                post_observation=post_observation
            )

        # 4. If nothing changed at all
        if not window_changed:
            return VerificationResult(
                status=VerificationStatus.UNCERTAIN,
                reason="Action executed, but no measurable visual change was detected on screen",
                state_changed=False,
                matched_expectation=False,
                pre_observation=pre_observation,
                post_observation=post_observation
            )

        return VerificationResult(
            status=VerificationStatus.SUCCESS,
            reason="Action completed with observed state transition",
            state_changed=True,
            matched_expectation=True,
            pre_observation=pre_observation,
            post_observation=post_observation
        )
