# Desktop Engine Package for J.A.R.V.I.S.
# Authoritative closed-loop desktop automation, perception, and context awareness.

from desktop_engine.coordinates import (
    CoordinateSpace,
    Point,
    BoundingBox,
    CoordinateConverter
)
from desktop_engine.models import (
    ObservationState,
    PerceptionTarget,
    PerceptionState,
    ContextItem,
    ContextState,
    ContextSource,
    ActionDecision,
    ValidationResult,
    ExecutionResult,
    VerificationResult,
    VerificationStatus,
    RiskLevel
)
from desktop_engine.session_manager import SessionManager
from desktop_engine.observation_engine import ObservationEngine
from desktop_engine.ocr_service import OCRService
from desktop_engine.ui_automation_service import UIAutomationService
from desktop_engine.perception_engine import PerceptionEngine
from desktop_engine.context_engine import ContextEngine
from desktop_engine.validation_engine import ValidationEngine
from desktop_engine.action_executor import ActionExecutor
from desktop_engine.verification_engine import VerificationEngine
from desktop_engine.decision_engine import DecisionEngine
from desktop_engine.orchestrator import DesktopOrchestrator
