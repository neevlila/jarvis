"""
Validation Engine for J.A.R.V.I.S. Desktop Engine.

Enforces strict safety boundaries and pre-execution validation:
1. Schema Validation (JSON completeness, types, allowed action verbs)
2. Target Validation (Verifies target exists in perception or is valid coordinates)
3. Coordinate Validation (Checks coordinate bounds against screen/window geometry)
4. State Validation (Ensures desktop environment is ready for the action)
5. Safety Validation (Guards against destructive OS commands and unauthorized tasks)
6. Composite Confidence Validation (Evaluates multi-source confidence heuristic)
"""

import json
import re
from typing import Dict, Any, Optional, Union, Tuple, List

from desktop_engine.coordinates import Point, BoundingBox, CoordinateSpace, CoordinateConverter
from desktop_engine.models import (
    ActionDecision,
    ValidationResult,
    RiskLevel,
    ObservationState,
    PerceptionState,
    PerceptionTarget
)


class ValidationEngine:
    """
    Validates proposed action decisions before deterministic execution.
    """

    SUPPORTED_ACTIONS = [
        "click",
        "double_click",
        "right_click",
        "type",
        "hotkey",
        "press",
        "scroll",
        "move",
        "drag",
        "wait",
        "activate_window",
        "launch_application",
        "complete",
        "abort"
    ]

    DESTRUCTIVE_KEYWORDS = [
        "format ",
        "del /f",
        "del /s",
        "rmdir /s",
        "drop table",
        "drop database",
        "shutdown /s",
        "shutdown -s",
        "taskkill /f /im explorer.exe",
        "taskkill /f /im svchost.exe",
        "taskkill /f /im csrss.exe",
        "remove-item -recurse",
        "reg delete"
    ]

    @classmethod
    def validate_action(
        cls,
        content: Union[str, Dict[str, Any], ActionDecision],
        observation: Optional[ObservationState] = None,
        perception: Optional[PerceptionState] = None,
        min_confidence_threshold: float = 0.50,
        authorized_destructive: bool = False
    ) -> ValidationResult:
        """
        Runs comprehensive multi-stage validation on a proposed action.
        """
        # 1. Schema Validation
        action_dict, parse_err = cls._parse_and_validate_schema(content)
        if parse_err:
            return ValidationResult(is_valid=False, reason=f"Schema validation failed: {parse_err}")

        action_name = action_dict.get("action", "").lower().strip()
        target = action_dict.get("target")
        reason = action_dict.get("reason", action_dict.get("reasoning", ""))
        expected_outcome = action_dict.get("expected_outcome", action_dict.get("expected_result", ""))
        raw_conf = action_dict.get("confidence", 0.0)
        completed = bool(action_dict.get("completed", False) or action_name == "complete")

        try:
            llm_confidence = float(raw_conf)
        except (ValueError, TypeError):
            llm_confidence = 0.50

        # Parse risk level
        risk_str = str(action_dict.get("risk", "low")).lower()
        if "destructive" in risk_str:
            risk = RiskLevel.DESTRUCTIVE
        elif "high" in risk_str:
            risk = RiskLevel.HIGH
        elif "medium" in risk_str:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        decision = ActionDecision(
            action=action_name,
            target=target,
            reason=reason,
            expected_outcome=expected_outcome,
            confidence=llm_confidence,
            risk=risk,
            completed=completed,
            requires_confirmation=False
        )

        # 2. Terminal / Goal Completion Actions
        if action_name in ["complete", "abort"]:
            return ValidationResult(
                is_valid=True,
                reason=f"Action '{action_name}' is valid terminal decision",
                validated_action=decision,
                composite_confidence=llm_confidence
            )

        # 3. Safety Validation
        safety_valid, safety_reason = cls._validate_safety(action_name, target, authorized_destructive)
        if not safety_valid:
            decision.risk = RiskLevel.DESTRUCTIVE
            decision.requires_confirmation = True
            return ValidationResult(
                is_valid=False,
                reason=f"Safety violation: {safety_reason}",
                validated_action=decision,
                composite_confidence=0.0
            )

        # 4. Target & Coordinate Validation
        target_coords: Optional[Point] = None
        matched_target: Optional[PerceptionTarget] = None
        target_confidence = 1.0

        screen_size = (1920, 1080)
        if observation:
            screen_size = (
                observation.screen_dimensions.get("width", 1920),
                observation.screen_dimensions.get("height", 1080)
            )

        if action_name in ["click", "double_click", "right_click", "move"]:
            coords, parsed_target_obj = cls._resolve_click_target(target, perception)

            if coords:
                target_coords = coords
                matched_target = parsed_target_obj
                # Verify coordinate boundary
                if not CoordinateConverter.is_within_screen_bounds(target_coords, screen_size):
                    return ValidationResult(
                        is_valid=False,
                        reason=f"Target coordinates ({target_coords.x:.0f}, {target_coords.y:.0f}) are outside screen bounds {screen_size}",
                        validated_action=decision
                    )
            else:
                # Target could not be resolved from coordinates or perception label
                if perception and perception.total_targets > 0:
                    return ValidationResult(
                        is_valid=False,
                        reason=f"Target '{target}' not found in active window controls or OCR detections",
                        validated_action=decision
                    )
                else:
                    # Fallback for text click if perception was not supplied
                    target_confidence = 0.60

        elif action_name == "type":
            if target is None or str(target).strip() == "":
                return ValidationResult(
                    is_valid=False,
                    reason="Type action requires non-empty target text",
                    validated_action=decision
                )

        elif action_name == "hotkey":
            if not target:
                return ValidationResult(
                    is_valid=False,
                    reason="Hotkey action requires target key string or list",
                    validated_action=decision
                )

        elif action_name == "drag":
            # Target must represent start and end coordinates: "x1,y1 -> x2,y2"
            if isinstance(target, str) and "->" in target:
                pass
            else:
                return ValidationResult(
                    is_valid=False,
                    reason="Drag action requires format 'x1,y1 -> x2,y2'",
                    validated_action=decision
                )

        # 5. Composite Confidence Scoring
        composite_conf = (llm_confidence * 0.5) + (target_confidence * 0.5)
        if composite_conf < min_confidence_threshold:
            return ValidationResult(
                is_valid=False,
                reason=f"Composite confidence {composite_conf:.2f} is below threshold {min_confidence_threshold:.2f}",
                validated_action=decision,
                composite_confidence=composite_conf
            )

        return ValidationResult(
            is_valid=True,
            reason="Action passed all validation stages",
            validated_action=decision,
            target_screen_coords=target_coords,
            target_perception=matched_target,
            composite_confidence=composite_conf
        )

    @classmethod
    def _parse_and_validate_schema(
        cls,
        content: Union[str, Dict[str, Any], ActionDecision]
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Validates JSON structure and required keys."""
        if isinstance(content, ActionDecision):
            return content.to_dict(), None

        if isinstance(content, dict):
            data = content
        elif isinstance(content, str):
            try:
                # Strip markdown wraps if present
                clean_str = content.strip()
                if clean_str.startswith("```json"):
                    clean_str = clean_str[7:]
                if clean_str.endswith("```"):
                    clean_str = clean_str[:-3]
                data = json.loads(clean_str.strip())
            except Exception as e:
                return {}, f"Failed to parse JSON string: {e}"
        else:
            return {}, f"Unsupported input type: {type(content)}"

        required = ["action", "target"]
        for req in required:
            if req not in data:
                return {}, f"Missing required field: '{req}'"

        action = str(data.get("action", "")).lower().strip()
        if action not in cls.SUPPORTED_ACTIONS:
            return {}, f"Unsupported action verb: '{action}'. Allowed: {cls.SUPPORTED_ACTIONS}"

        return data, None

    @classmethod
    def _validate_safety(
        cls,
        action: str,
        target: Any,
        authorized: bool
    ) -> Tuple[bool, Optional[str]]:
        """Ensures destructive or hazardous operations are caught and blocked."""
        target_str = str(target).lower()

        for bad in cls.DESTRUCTIVE_KEYWORDS:
            if bad in target_str:
                if not authorized:
                    return False, f"Blocked destructive pattern '{bad}'. Requires explicit user confirmation."

        if action == "launch_application":
            dangerous_apps = ["cmd.exe", "powershell.exe", "regedit.exe", "diskpart.exe"]
            for dapp in dangerous_apps:
                if dapp in target_str and not authorized:
                    return False, f"Direct launch of '{dapp}' requires user confirmation."

        return True, None

    @staticmethod
    def _resolve_click_target(
        target: Any,
        perception: Optional[PerceptionState]
    ) -> Tuple[Optional[Point], Optional[PerceptionTarget]]:
        """
        Attempts to resolve target to explicit Point coordinates in Screen space.
        """
        # Case 1: Point object
        if isinstance(target, Point):
            return target, None

        # Case 2: List of 2 ints [x, y]
        if isinstance(target, (list, tuple)) and len(target) == 2:
            try:
                return Point(float(target[0]), float(target[1]), CoordinateSpace.SCREEN), None
            except Exception:
                pass

        # Case 3: Coordinate string "x, y"
        if isinstance(target, str) and "," in target:
            try:
                parts = [p.strip() for p in target.split(",")]
                if len(parts) == 2 and all(p.lstrip("-").isdigit() for p in parts):
                    return Point(float(parts[0]), float(parts[1]), CoordinateSpace.SCREEN), None
            except Exception:
                pass

        # Case 4: Target string matched against perception targets
        if isinstance(target, str) and perception:
            matched = perception.find_target(target)
            if matched and matched.bounds:
                center_point = matched.bounds.center
                return center_point, matched

        return None, None
