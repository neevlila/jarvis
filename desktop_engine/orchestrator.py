"""
Desktop Orchestrator for J.A.R.V.I.S.

Canonical closed-loop agent loop:
Observe -> Perceive -> Build Context -> Decide -> Validate -> Execute -> Verify -> Adapt / Replan
"""

import time
from typing import Dict, Any, Optional, Callable, List

from desktop_engine.models import (
    ObservationState,
    PerceptionState,
    ContextState,
    ActionDecision,
    ValidationResult,
    ExecutionResult,
    VerificationResult,
    VerificationStatus
)
from desktop_engine.observation_engine import ObservationEngine
from desktop_engine.perception_engine import PerceptionEngine
from desktop_engine.context_engine import ContextEngine
from desktop_engine.decision_engine import DecisionEngine
from desktop_engine.validation_engine import ValidationEngine
from desktop_engine.action_executor import ActionExecutor
from desktop_engine.verification_engine import VerificationEngine
from desktop_engine.session_manager import SessionManager


class DesktopOrchestrator:
    """
    Authoritative orchestrator for J.A.R.V.I.S. desktop automation tasks.
    """

    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        ui_available: bool = True,
        ocr_available: bool = True,
        max_steps: int = 12,
        log_callback: Optional[Callable[[str, str], None]] = None,
        speak_callback: Optional[Callable[[str], None]] = None
    ):
        self.decision_engine = decision_engine or DecisionEngine()
        self.ui_available = ui_available
        self.ocr_available = ocr_available
        self.session_manager = SessionManager(max_steps=max_steps)
        self.log_callback = log_callback
        self.speak_callback = speak_callback

    def _log(self, stage: str, message: str):
        """Structured traceable logging."""
        formatted = f"[{stage}] {message}"
        print(formatted)
        if self.log_callback:
            try:
                self.log_callback(stage, message)
            except Exception:
                pass

    def _speak(self, message: str):
        if self.speak_callback:
            try:
                self.speak_callback(message)
            except Exception:
                pass

    def run_task(self, goal: str) -> Dict[str, Any]:
        """
        Executes a user task autonomously in a reliable, closed-loop cycle.
        """
        self.session_manager.start_session(goal)
        self._log("ORCHESTRATOR", f"Starting task session for goal: '{goal}'")
        self._speak(f"Beginning automation for: {goal}")

        step = 0
        while self.session_manager.is_active:
            step += 1
            if self.session_manager.is_step_limit_reached():
                self._log("ADAPT", f"Reached maximum allowed steps or failure limit ({step}). Stopping.")
                self._speak("Task step limit reached. Aborting automation for safety.")
                break

            self._log("CYCLE", f"--- Step {step} ---")

            # 1. OBSERVE
            self._log("OBSERVE", "Capturing environmental state...")
            pre_obs = ObservationEngine.observe(capture_images=True)
            self._log(
                "OBSERVE",
                f"Active Window: '{pre_obs.active_window_title}' | Process: '{pre_obs.process_name}'"
            )

            # 2. PERCEIVE
            self._log("PERCEIVE", "Extracting UI controls and OCR text...")
            pre_per = PerceptionEngine.perceive(
                ui_available=self.ui_available,
                ocr_available=self.ocr_available,
                observation=pre_obs,
                image_path=pre_obs.active_window_screenshot_path or "active_window.png"
            )
            self._log(
                "PERCEIVE",
                f"Found {len(pre_per.ui_controls)} UI controls and {len(pre_per.ocr_detections)} text detections"
            )

            # 3. BUILD CONTEXT
            self._log("CONTEXT", "Synthesizing grounded context awareness model...")
            context = ContextEngine.build_context(
                observation=pre_obs,
                perception=pre_per,
                goal=goal,
                recent_actions=[a.get("action", {}) for a in self.session_manager.action_history[-3:]]
            )
            self._log(
                "CONTEXT",
                f"App: '{context.application.value}' ({context.application.source.value}) | "
                f"Activity: '{context.activity.value}' ({context.activity.source.value}, conf={context.activity.confidence:.2f})"
            )

            # 4. DECIDE
            self._log("DECIDE", "Evaluating next single action...")
            val_result = self.decision_engine.get_next_action(
                goal=goal,
                desktop_state=context,
                action_history=[a.get("action", {}) for a in self.session_manager.action_history],
                failure_memory=self.session_manager.failure_memory,
                observation=pre_obs,
                perception=pre_per
            )

            # 5. VALIDATE
            if not val_result.is_valid or not val_result.validated_action:
                self._log("VALIDATE", f"Action REJECTED: {val_result.reason}")
                self.session_manager.log_failure("unknown", "none", val_result.reason)
                # Allow one replan attempt before breaking if validation failed
                continue

            decision = val_result.validated_action
            self._log(
                "VALIDATE",
                f"Action APPROVED: {decision.action} -> target: {decision.target} (Confidence: {val_result.composite_confidence:.2f}, Risk: {decision.risk.value})"
            )

            # Check if goal is complete
            if decision.completed or decision.action == "complete":
                self._log("COMPLETE", f"Goal accomplished: {decision.reason}")
                self._speak("Task completed successfully, Sir.")
                self.session_manager.log_action(decision.to_dict())
                self.session_manager.end_session()
                return self.session_manager.get_session_summary()

            if decision.action == "abort":
                self._log("ABORT", f"Task aborted: {decision.reason}")
                self._speak("Task aborted.")
                self.session_manager.log_action(decision.to_dict())
                self.session_manager.end_session()
                return self.session_manager.get_session_summary()

            # 6. EXECUTE
            self._log("EXECUTE", f"Executing {decision.action} on {decision.target}...")
            exec_result = ActionExecutor.execute(
                action=val_result,
                target_coords=val_result.target_screen_coords
            )

            if not exec_result.success:
                self._log("EXECUTE", f"Execution FAILED: {exec_result.error}")
                self.session_manager.log_failure(decision.action, decision.target, exec_result.error or "execution error")
                self.session_manager.log_action(decision.to_dict(), execution_result=exec_result.to_dict())
                continue

            self._log("EXECUTE", f"Executed in {exec_result.duration_ms:.1f}ms")

            # Short settlement delay before post-observation
            time.sleep(0.6)

            # 7. VERIFY
            self._log("VERIFY", f"Verifying expected outcome: '{decision.expected_outcome}'...")
            post_obs = ObservationEngine.observe(capture_images=True)
            post_per = PerceptionEngine.perceive(
                ui_available=self.ui_available,
                ocr_available=self.ocr_available,
                observation=post_obs,
                image_path=post_obs.active_window_screenshot_path or "active_window.png"
            )

            verif_result = VerificationEngine.verify_outcome(
                decision=decision,
                execution=exec_result,
                pre_observation=pre_obs,
                post_observation=post_obs,
                pre_perception=pre_per,
                post_perception=post_per
            )

            # 8. ADAPT / REPLAN
            if verif_result.status == VerificationStatus.SUCCESS:
                self._log("VERIFY", f"VERIFIED: {verif_result.reason}")
                self.session_manager.log_action(
                    action_dict=decision.to_dict(),
                    execution_result=exec_result.to_dict(),
                    verification_result=verif_result.to_dict()
                )
            else:
                self._log("ADAPT", f"Outcome NOT verified: {verif_result.reason}. Recording failure and adapting strategy.")
                self.session_manager.log_failure(decision.action, decision.target, verif_result.reason)
                self.session_manager.log_action(
                    action_dict=decision.to_dict(),
                    execution_result=exec_result.to_dict(),
                    verification_result=verif_result.to_dict()
                )

        self.session_manager.end_session()
        return self.session_manager.get_session_summary()
