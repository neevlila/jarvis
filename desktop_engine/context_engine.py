"""
Context Awareness Engine for J.A.R.V.I.S. Desktop Engine.

Synthesizes environmental observations, UI perception, OCR detections,
user goals, and session history into a structured context model.

CRITICAL RULE:
Strictly distinguishes OBSERVED facts from INFERRED activities and UNKNOWN elements.
Never hallucinates context.
"""

from typing import Dict, Any, List, Optional
import time

from desktop_engine.models import (
    ContextState,
    ContextItem,
    ContextSource,
    ObservationState,
    PerceptionState
)


class ContextEngine:
    """
    Synthesizes multi-source state into an authoritative, grounded ContextState.
    """

    @classmethod
    def build_context(
        cls,
        observation: ObservationState,
        perception: PerceptionState,
        goal: Optional[str] = None,
        recent_actions: Optional[List[Dict[str, Any]]] = None
    ) -> ContextState:
        """
        Builds a verified ContextState from observation and perception data.
        """
        # 1. Application: Directly observed from OS process metadata
        app_name = observation.process_name or "unknown"
        if app_name and app_name != "unknown":
            app_item = ContextItem(value=app_name, source=ContextSource.OBSERVED, confidence=0.99)
        else:
            app_item = ContextItem(value="unknown", source=ContextSource.UNKNOWN, confidence=0.0)

        # 2. Window Title: Directly observed from OS window manager
        win_title = observation.active_window_title or ""
        if win_title:
            win_item = ContextItem(value=win_title, source=ContextSource.OBSERVED, confidence=0.99)
        else:
            win_item = ContextItem(value="unknown", source=ContextSource.UNKNOWN, confidence=0.0)

        # 3. Activity: Inferred from application name, window title, and visible text
        activity_val, activity_conf = cls._infer_activity(app_name, win_title, perception)
        if activity_val != "unknown":
            act_item = ContextItem(value=activity_val, source=ContextSource.INFERRED, confidence=activity_conf)
        else:
            act_item = ContextItem(value="unknown", source=ContextSource.UNKNOWN, confidence=0.0)

        # 4. Visible Text: Observed from OCR detections
        visible_text = [t.label for t in perception.ocr_detections[:25]]

        # 5. UI Elements: Observed from UI Automation tree
        ui_elements = [f"[{t.type}] {t.label}" for t in perception.ui_controls[:25]]

        # 6. System State: Observed from system metrics
        system_state = dict(observation.system_metrics)
        system_state["screen_dimensions"] = observation.screen_dimensions
        if observation.active_window_bounds:
            system_state["active_window_bounds"] = observation.active_window_bounds

        # 7. Action history
        actions_list = recent_actions or []

        # 8. Compute composite context confidence
        weights = [app_item.confidence * 0.3, win_item.confidence * 0.3, act_item.confidence * 0.2]
        if perception.total_targets > 0:
            weights.append(0.2)
        else:
            weights.append(0.05)
        overall_confidence = sum(weights)

        return ContextState(
            application=app_item,
            window_title=win_item,
            activity=act_item,
            visible_text=visible_text,
            ui_elements=ui_elements,
            system_state=system_state,
            current_goal=goal,
            recent_actions=actions_list,
            confidence=min(1.0, max(0.0, overall_confidence)),
            timestamp=time.time()
        )

    @staticmethod
    def _infer_activity(
        app_name: str,
        win_title: str,
        perception: PerceptionState
    ) -> tuple[str, float]:
        """
        Infers the user's current activity type with a calibrated confidence score.
        Never states an inference with 1.0 confidence.
        """
        combined = f"{app_name.lower()} {win_title.lower()}"

        # Code / Software Development
        if any(k in combined for k in ["code.exe", "visual studio", "pycharm", "sublime", "notepad++", "git", "terminal", "powershell", "cmd.exe"]):
            return "software_development", 0.88

        # Web Browsing / Research
        if any(k in combined for k in ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe", "opera.exe"]):
            if "youtube" in combined:
                return "media_streaming", 0.90
            elif "github" in combined:
                return "software_development", 0.85
            elif "google search" in combined:
                return "web_search", 0.85
            return "web_browsing", 0.80

        # Document Editing / Productivity
        if any(k in combined for k in ["winword.exe", "word", "excel.exe", "excel", "powerpnt.exe", "powerpoint", "notepad.exe"]):
            return "document_editing", 0.85

        # Calculations
        if any(k in combined for k in ["calc.exe", "calculator"]):
            return "calculation", 0.92

        # Communication
        if any(k in combined for k in ["slack.exe", "teams.exe", "discord.exe", "telegram.exe", "whatsapp", "mail"]):
            return "communication", 0.85

        # Media Playback
        if any(k in combined for k in ["spotify.exe", "vlc.exe", "wmplayer.exe"]):
            return "media_playback", 0.90

        # Scan visible OCR text for clues if app name was ambiguous
        all_text = " ".join([t.label.lower() for t in perception.ocr_detections[:10]])
        if "def " in all_text or "import " in all_text or "class " in all_text:
            return "software_development", 0.65
        if "http" in all_text or "www." in all_text:
            return "web_browsing", 0.60

        return "unknown", 0.0
