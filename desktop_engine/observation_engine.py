"""
Observation Engine for J.A.R.V.I.S. Desktop Engine.
Captures deterministic environmental state: active window, process metadata, screen dimensions,
screenshot files, and hardware metrics.
"""

import os
import time
try:
    import pyautogui
except Exception:
    pyautogui = None
import psutil
from typing import Optional, Dict, Any

from desktop_engine.models import ObservationState
from desktop_engine.coordinates import BoundingBox, CoordinateSpace


class ObservationEngine:
    """
    Centralized observation layer. Collects and structure desktop metadata.
    Prevents duplicate screenshot operations and uncoordinated screen queries.
    """

    @staticmethod
    def capture_screenshot(path: str = "screenshot.png") -> bool:
        """Captures a full desktop screenshot safely."""
        try:
            pyautogui.screenshot(path)
            return True
        except Exception as e:
            print(f"[ObservationEngine Warning] Full screenshot capture failed: {e}")
            return False

    @staticmethod
    def capture_window_screenshot(bounds: Optional[Dict[str, int]], path: str = "active_window.png") -> bool:
        """
        Captures a cropped screenshot targeting the specified window bounds.
        If bounds are missing or invalid, falls back to a full desktop screenshot.
        """
        try:
            if bounds and bounds.get("width", 0) > 0 and bounds.get("height", 0) > 0:
                region = (
                    bounds["left"],
                    bounds["top"],
                    bounds["width"],
                    bounds["height"]
                )
                pyautogui.screenshot(path, region=region)
                return True
            else:
                pyautogui.screenshot(path)
                return True
        except Exception as e:
            print(f"[ObservationEngine Warning] Window screenshot capture failed: {e}")
            return False

    @classmethod
    def get_active_window_details(cls, capture_window_image: bool = True) -> Dict[str, Any]:
        """
        Retrieves title, bounding dimensions, process name, and cropped image of the focused window.
        Returns a dictionary for backward compatibility and internal usage.
        """
        try:
            import win32gui
            import win32process

            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) if hwnd else ""

            proc_name = "unknown"
            if hwnd:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                except Exception:
                    pass

            bounds = None
            if hwnd:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    x, y, right, bottom = rect
                    w = right - x
                    h = bottom - y
                    if w > 0 and h > 0:
                        bounds = {
                            "left": int(x),
                            "top": int(y),
                            "width": int(w),
                            "height": int(h)
                        }
                except Exception:
                    pass

            # Capture cropped window screenshot if requested
            if capture_window_image:
                cls.capture_window_screenshot(bounds, "active_window.png")

            return {
                "title": title,
                "process_name": proc_name,
                "bounds": bounds,
                "screenshot_path": "active_window.png"
            }
        except Exception as e:
            return {"error": str(e), "title": "", "process_name": "unknown", "bounds": None}

    @classmethod
    def observe(cls, capture_images: bool = True) -> ObservationState:
        """
        Gathers a complete ObservationState containing screen dimensions,
        active window, process details, and system hardware telemetry.
        """
        try:
            scr_w, scr_h = pyautogui.size()
        except Exception:
            scr_w, scr_h = 1920, 1080

        win_info = cls.get_active_window_details(capture_window_image=capture_images)

        # Capture full screenshot
        if capture_images:
            cls.capture_screenshot("screenshot.png")

        # System telemetry
        metrics = {}
        try:
            metrics["cpu_percent"] = psutil.cpu_percent(interval=None)
            metrics["ram_percent"] = psutil.virtual_memory().percent
        except Exception:
            pass

        return ObservationState(
            timestamp=time.time(),
            screen_dimensions={"width": scr_w, "height": scr_h},
            active_window_title=win_info.get("title", ""),
            process_name=win_info.get("process_name", "unknown"),
            active_window_bounds=win_info.get("bounds"),
            is_fullscreen_capture=True,
            screenshot_path="screenshot.png",
            active_window_screenshot_path="active_window.png",
            system_metrics=metrics
        )
