"""
Decision Engine for J.A.R.V.I.S. Desktop Engine.

Closed-loop reasoning engine:
Receives grounded context, user goal, past action history, and failure memory.
Decides ONE single next action with explicit reason, expected outcome, confidence, and risk level.
"""

import json
from typing import Dict, Any, Optional, List, Callable, Union

from desktop_engine.models import (
    ActionDecision,
    ValidationResult,
    ContextState,
    ObservationState,
    PerceptionState
)
from desktop_engine.validation_engine import ValidationEngine
from providers.provider_manager import ProviderManager


class DecisionEngine:
    """
    Decides the single best next action to achieve a user goal based on desktop state observations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_callable: Optional[Callable[[str], str]] = None):
        self.config = config or {}
        self.llm_callable = llm_callable

    def get_next_action(
        self,
        goal: str,
        desktop_state: Union[ContextState, Dict[str, Any]],
        action_history: Optional[List[Dict[str, Any]]] = None,
        failure_memory: Optional[List[Dict[str, Any]]] = None,
        observation: Optional[ObservationState] = None,
        perception: Optional[PerceptionState] = None
    ) -> ValidationResult:
        """
        Reasons over current context, goals, and failures to produce the next validated action.
        """
        try:
            # Format desktop state
            if isinstance(desktop_state, ContextState):
                state_dict = desktop_state.to_dict()
            elif isinstance(desktop_state, dict):
                state_dict = desktop_state
            else:
                state_dict = {"state": str(desktop_state)}

            history_str = "No actions taken yet in this session."
            if action_history:
                history_str = json.dumps(action_history, indent=2)

            failure_str = "No failed actions in this session."
            if failure_memory:
                failure_str = json.dumps(failure_memory, indent=2)

            # Build structured reasoning prompt
            prompt = (
                f"You are J.A.R.V.I.S., the closed-loop Desktop Decision Engine.\n"
                f"Overall Goal: \"{goal}\"\n\n"
                f"--- CURRENT GROUNDED CONTEXT ---\n"
                f"{json.dumps(state_dict, indent=2)}\n\n"
                f"--- ACTION HISTORY IN THIS SESSION ---\n"
                f"{history_str}\n\n"
                f"--- FAILURE MEMORY (ACTIONS THAT FAILED) ---\n"
                f"{failure_str}\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Choose the SINGLE best next step. Never generate multiple steps.\n"
                "2. Review FAILURE MEMORY: Do NOT repeat the exact same failed action without an altered strategy or new target.\n"
                "3. If the goal has already been achieved (e.g. calculation is done, document is saved, search is open), set completed: true and action: \"complete\".\n"
                "4. Supported actions: click, double_click, right_click, type, hotkey, press, scroll, drag, wait, activate_window, launch_application, complete, abort.\n"
                "5. Assign a meaningful risk level: 'low', 'medium', 'high', or 'destructive'.\n"
                "6. Define an explicit expected_outcome describing what visual/state change should occur after execution.\n\n"
                "Output Schema (respond ONLY with raw valid JSON):\n"
                "{\n"
                "  \"completed\": false,\n"
                "  \"action\": \"click\",\n"
                "  \"target\": \"Save\",\n"
                "  \"reason\": \"Save button is visible and saves current file\",\n"
                "  \"expected_outcome\": \"Document state changes to saved or save dialog closes\",\n"
                "  \"confidence\": 0.95,\n"
                "  \"risk\": \"low\"\n"
                "}"
            )

            # Query LLM (or mock callable)
            if self.llm_callable:
                raw_response = self.llm_callable(prompt)
            else:
                raw_response = ProviderManager.chat(
                    system_prompt="You are J.A.R.V.I.S., a precise desktop decision engine that outputs single JSON action objects.",
                    messages_history=[],
                    user_prompt=prompt,
                    response_format_json=True
                )

            # Validate the proposed action against perception and safety bounds
            return ValidationEngine.validate_action(
                content=raw_response,
                observation=observation,
                perception=perception
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                reason=f"Decision engine encountered error: {str(e)}"
            )
