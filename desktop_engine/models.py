"""
Core Data Models and Type Definitions for J.A.R.V.I.S. Desktop Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Tuple
import time

from desktop_engine.coordinates import BoundingBox, Point, CoordinateSpace


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DESTRUCTIVE = "destructive"


class ContextSource(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


@dataclass
class ObservationState:
    """Structured deterministic state captured from desktop and active window."""
    timestamp: float = field(default_factory=time.time)
    screen_dimensions: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    active_window_title: str = ""
    process_name: str = "unknown"
    active_window_bounds: Optional[Dict[str, int]] = None  # left, top, width, height
    is_fullscreen_capture: bool = True
    screenshot_path: str = "screenshot.png"
    active_window_screenshot_path: Optional[str] = None
    system_metrics: Dict[str, Any] = field(default_factory=dict)  # cpu, ram, battery, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "screen_dimensions": self.screen_dimensions,
            "active_window_title": self.active_window_title,
            "process_name": self.process_name,
            "active_window_bounds": self.active_window_bounds,
            "is_fullscreen_capture": self.is_fullscreen_capture,
            "screenshot_path": self.screenshot_path,
            "system_metrics": self.system_metrics
        }


@dataclass
class PerceptionTarget:
    """Represents an interactable control, text detection, or visual element."""
    source: str  # "ui_automation" | "ocr" | "vision"
    type: str    # "ButtonControl", "EditControl", "TextDetection", etc.
    label: str
    bounds: BoundingBox
    confidence: float = 1.0
    is_enabled: bool = True
    is_focused: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "type": self.type,
            "label": self.label,
            "bounds": self.bounds.to_dict(),
            "confidence": self.confidence,
            "is_enabled": self.is_enabled,
            "is_focused": self.is_focused
        }


@dataclass
class PerceptionState:
    """Aggregated perception from UI Automation, OCR, and Computer Vision."""
    ui_controls: List[PerceptionTarget] = field(default_factory=list)
    ocr_detections: List[PerceptionTarget] = field(default_factory=list)
    visual_elements: List[PerceptionTarget] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def total_targets(self) -> int:
        return len(self.ui_controls) + len(self.ocr_detections) + len(self.visual_elements)

    def find_target(self, query: str) -> Optional[PerceptionTarget]:
        """Finds matching target by label with case-insensitive search (prioritizing UI Automation)."""
        q = query.strip().lower()
        if not q:
            return None

        # Exact match in UI controls
        for ctrl in self.ui_controls:
            if ctrl.label.strip().lower() == q:
                return ctrl

        # Exact match in OCR
        for ocr in self.ocr_detections:
            if ocr.label.strip().lower() == q:
                return ocr

        # Substring match in UI controls
        for ctrl in self.ui_controls:
            if q in ctrl.label.strip().lower() or ctrl.label.strip().lower() in q:
                return ctrl

        # Substring match in OCR
        for ocr in self.ocr_detections:
            if q in ocr.label.strip().lower() or ocr.label.strip().lower() in q:
                return ocr

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ui_automation_controls": [c.to_dict() for c in self.ui_controls],
            "ocr_detections": [o.to_dict() for o in self.ocr_detections],
            "visual_elements": [v.to_dict() for v in self.visual_elements],
            "total_clickable_targets": self.total_targets,
            "timestamp": self.timestamp
        }


@dataclass
class ContextItem:
    """Individual context field with source provenance (observed, inferred, unknown)."""
    value: Any
    source: ContextSource
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source.value,
            "confidence": round(self.confidence, 3)
        }


@dataclass
class ContextState:
    """Structured context awareness state model."""
    application: ContextItem
    window_title: ContextItem
    activity: ContextItem
    visible_text: List[str]
    ui_elements: List[str]
    system_state: Dict[str, Any]
    current_goal: Optional[str]
    recent_actions: List[Dict[str, Any]]
    confidence: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application": self.application.to_dict(),
            "window_title": self.window_title.to_dict(),
            "activity": self.activity.to_dict(),
            "visible_text": self.visible_text,
            "ui_elements": self.ui_elements,
            "system_state": self.system_state,
            "current_goal": self.current_goal,
            "recent_actions": self.recent_actions,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp
        }


@dataclass
class ActionDecision:
    """A proposed single action decision emitted by the decision engine."""
    action: str  # click, double_click, right_click, type, hotkey, press, scroll, move, drag, wait, activate_window, launch_application, complete, abort
    target: Any  # label, coordinates [x, y], string key, text to type
    reason: str
    expected_outcome: str
    confidence: float
    risk: RiskLevel = RiskLevel.LOW
    completed: bool = False
    requires_confirmation: bool = False
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completed": self.completed,
            "action": self.action,
            "target": self.target,
            "reason": self.reason,
            "expected_outcome": self.expected_outcome,
            "confidence": self.confidence,
            "risk": self.risk.value if isinstance(self.risk, RiskLevel) else str(self.risk),
            "requires_confirmation": self.requires_confirmation
        }


@dataclass
class ValidationResult:
    """Result of multi-stage validation."""
    is_valid: bool
    reason: str
    validated_action: Optional[ActionDecision] = None
    target_screen_coords: Optional[Point] = None
    target_perception: Optional[PerceptionTarget] = None
    composite_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "reason": self.reason,
            "validated_action": self.validated_action.to_dict() if self.validated_action else None,
            "target_screen_coords": self.target_screen_coords.to_dict() if self.target_screen_coords else None,
            "composite_confidence": round(self.composite_confidence, 3)
        }


@dataclass
class ExecutionResult:
    """Outcome of deterministic action execution."""
    success: bool
    action: str
    target: Any
    error: Optional[str] = None
    executed_coords: Optional[Tuple[int, int]] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "target": self.target,
            "error": self.error,
            "executed_coords": self.executed_coords,
            "duration_ms": round(self.duration_ms, 2)
        }


@dataclass
class VerificationResult:
    """Result of post-action verification."""
    status: VerificationStatus
    reason: str
    state_changed: bool
    matched_expectation: bool
    pre_observation: Optional[ObservationState] = None
    post_observation: Optional[ObservationState] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "state_changed": self.state_changed,
            "matched_expectation": self.matched_expectation
        }
