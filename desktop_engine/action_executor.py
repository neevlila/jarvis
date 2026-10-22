"""
Action Executor for J.A.R.V.I.S. Desktop Engine.

Deterministic, allowlisted action execution layer.
Translates approved and validated action decisions into OS inputs.
"""

import time
import os
import subprocess
from typing import Dict, Any, Optional, Union, Tuple
import pyautogui

from desktop_engine.coordinates import Point
from desktop_engine.models import ActionDecision, ValidationResult, ExecutionResult


class ActionExecutor:
    """
    Executes only validated action payloads. Never executes arbitrary Python or shell strings.
    """

    @classmethod
    def execute(
        cls,
        action: Union[ActionDecision, Dict[str, Any], ValidationResult],
        target_coords: Optional[Point] = None
    ) -> ExecutionResult:
        """
        Executes a validated action command deterministically.
        """
        start_time = time.perf_counter()

        # Unpack input
        if isinstance(action, ValidationResult):
            if not action.is_valid or not action.validated_action:
                return ExecutionResult(
                    success=False,
                    action="unknown",
                    target=None,
                    error=f"Cannot execute invalid action: {action.reason}",
                    duration_ms=0.0
                )
            decision = action.validated_action
            if not target_coords and action.target_screen_coords:
                target_coords = action.target_screen_coords
        elif isinstance(action, ActionDecision):
            decision = action
        elif isinstance(action, dict):
            # Parse into ActionDecision
            decision = ActionDecision(
                action=action.get("action", ""),
                target=action.get("target"),
                reason=action.get("reason", ""),
                expected_outcome=action.get("expected_outcome", ""),
                confidence=float(action.get("confidence", 1.0))
            )
        else:
            return ExecutionResult(
                success=False,
                action="unknown",
                target=None,
                error=f"Unsupported action type: {type(action)}",
                duration_ms=0.0
            )

        act_name = decision.action.lower().strip()
        target = decision.target
        executed_pos = None

        try:
            # 1. Terminal Actions
            if act_name in ["complete", "abort"]:
                return ExecutionResult(
                    success=True,
                    action=act_name,
                    target=target,
                    duration_ms=(time.perf_counter() - start_time) * 1000.0
                )

            # 2. Mouse Actions
            if act_name in ["click", "double_click", "right_click", "move"]:
                coords = cls._get_screen_coords(target, target_coords)
                if not coords:
                    return ExecutionResult(
                        success=False,
                        action=act_name,
                        target=target,
                        error=f"Could not resolve screen coordinates for target: '{target}'",
                        duration_ms=(time.perf_counter() - start_time) * 1000.0
                    )

                x, y = coords
                executed_pos = (x, y)

                if act_name == "click":
                    pyautogui.click(x, y)
                elif act_name == "double_click":
                    pyautogui.doubleClick(x, y)
                elif act_name == "right_click":
                    pyautogui.rightClick(x, y)
                elif act_name == "move":
                    pyautogui.moveTo(x, y)

            # 3. Typing Actions
            elif act_name == "type":
                text_to_type = str(target)
                pyautogui.typewrite(text_to_type, interval=0.03)

            # 4. Keyboard Shortcuts & Key Presses
            elif act_name == "hotkey":
                if isinstance(target, str):
                    keys = [k.strip().lower() for k in target.split("+") if k.strip()]
                    pyautogui.hotkey(*keys)
                elif isinstance(target, (list, tuple)):
                    pyautogui.hotkey(*target)
                else:
                    pyautogui.press(str(target))

            elif act_name == "press":
                key = str(target).strip().lower()
                pyautogui.press(key)

            # 5. Scrolling
            elif act_name == "scroll":
                amount = -250 if "down" in str(target).lower() else 250
                if isinstance(target, (int, float)):
                    amount = int(target)
                pyautogui.scroll(amount)

            # 6. Dragging
            elif act_name == "drag":
                if isinstance(target, str) and "->" in target:
                    parts = target.split("->")
                    start_coords = [int(p.strip()) for p in parts[0].split(",")]
                    end_coords = [int(p.strip()) for p in parts[1].split(",")]
                    pyautogui.moveTo(start_coords[0], start_coords[1])
                    pyautogui.dragTo(end_coords[0], end_coords[1], duration=0.8)
                    executed_pos = (end_coords[0], end_coords[1])

            # 7. Waiting
            elif act_name == "wait":
                duration = 1.0
                try:
                    duration = float(target)
                except (ValueError, TypeError):
                    pass
                time.sleep(min(10.0, max(0.1, duration)))

            # 8. Window Activation
            elif act_name == "activate_window":
                cls._activate_window_by_title(str(target))

            # 9. Application Launch
            elif act_name == "launch_application":
                cls._launch_app(str(target))

            else:
                return ExecutionResult(
                    success=False,
                    action=act_name,
                    target=target,
                    error=f"Unrecognized action verb: '{act_name}'",
                    duration_ms=(time.perf_counter() - start_time) * 1000.0
                )

            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                success=True,
                action=act_name,
                target=target,
                executed_coords=executed_pos,
                duration_ms=duration
            )

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                success=False,
                action=act_name,
                target=target,
                error=str(e),
                executed_coords=executed_pos,
                duration_ms=duration
            )

    @staticmethod
    def _get_screen_coords(target: Any, target_coords: Optional[Point]) -> Optional[Tuple[int, int]]:
        if target_coords:
            return target_coords.to_tuple()
        if isinstance(target, Point):
            return target.to_tuple()
        if isinstance(target, (list, tuple)) and len(target) == 2:
            try:
                return int(target[0]), int(target[1])
            except Exception:
                pass
        if isinstance(target, str) and "," in target:
            try:
                parts = [int(x.strip()) for x in target.split(",")]
                if len(parts) == 2:
                    return parts[0], parts[1]
            except Exception:
                pass
        return None

    @staticmethod
    def _activate_window_by_title(target_title: str) -> bool:
        try:
            import win32gui
            import win32con

            matched_hwnd = None
            def enum_cb(hwnd, extra):
                nonlocal matched_hwnd
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if target_title.lower() in title.lower():
                        matched_hwnd = hwnd
                        return False
                return True

            win32gui.EnumWindows(enum_cb, None)
            if matched_hwnd:
                win32gui.ShowWindow(matched_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(matched_hwnd)
                return True
        except Exception as e:
            print(f"[ActionExecutor Warning] Activate window failed: {e}")
        return False

    @staticmethod
    def _launch_app(app_target: str) -> bool:
        try:
            if os.path.exists(app_target):
                subprocess.Popen(app_target)
                return True
            else:
                import shutil
                resolved = shutil.which(app_target)
                if resolved:
                    subprocess.Popen(resolved)
                    return True
                os.startfile(app_target)
                return True
        except Exception as e:
            print(f"[ActionExecutor Warning] Launch application failed: {e}")
            return False
