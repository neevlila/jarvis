"""
Data models and schemas for J.A.R.V.I.S. Intelligence Subsystem.
Includes definitions for Critique, Project Analysis, Goal Decomposition,
Memory & Knowledge, Skills, Risk & Safety, and Performance Intelligence.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import time
import uuid


# ─────────────────────────────────────────────────────────────────────────────
# 1. Self-Critique Models
# ─────────────────────────────────────────────────────────────────────────────

class CritiqueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CritiqueResult:
    is_valid: bool
    confidence: float
    issues: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    recommended_changes: List[str] = field(default_factory=list)
    severity: CritiqueSeverity = CritiqueSeverity.LOW
    revised_content: Optional[str] = None
    iterations_used: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "confidence": round(self.confidence, 2),
            "issues": self.issues,
            "missing_information": self.missing_information,
            "assumptions": self.assumptions,
            "risks": self.risks,
            "recommended_changes": self.recommended_changes,
            "severity": self.severity.value if isinstance(self.severity, CritiqueSeverity) else str(self.severity),
            "revised_content": self.revised_content,
            "iterations_used": self.iterations_used
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Project Analyzer Models
# ─────────────────────────────────────────────────────────────────────────────

class FindingSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProjectFinding:
    category: str  # security, architecture, code_quality, testing, documentation, performance
    severity: FindingSeverity
    file: str
    location: str  # line or function name
    problem: str
    evidence: str
    recommendation: str
    confidence: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity.value if isinstance(self.severity, FindingSeverity) else str(self.severity),
            "file": self.file,
            "location": self.location,
            "problem": self.problem,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "confidence": round(self.confidence, 2)
        }


@dataclass
class ProjectHealthScores:
    architecture: float
    code_quality: float
    security: float
    testing: float
    documentation: float
    maintainability: float
    overall: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "architecture": round(self.architecture, 1),
            "code_quality": round(self.code_quality, 1),
            "security": round(self.security, 1),
            "testing": round(self.testing, 1),
            "documentation": round(self.documentation, 1),
            "maintainability": round(self.maintainability, 1),
            "overall": round(self.overall, 1)
        }


@dataclass
class ProjectHealthReport:
    project_path: str
    languages: Dict[str, int]
    frameworks: List[str]
    dependencies: List[str]
    total_files: int
    total_lines: int
    scores: ProjectHealthScores
    findings: List[ProjectFinding] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "dependencies": self.dependencies,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "scores": self.scores.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "timestamp": self.timestamp
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Goal Decomposition Models
# ─────────────────────────────────────────────────────────────────────────────

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class GoalTask:
    id: str
    title: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_effort: str = "1-2 hours"
    status: TaskStatus = TaskStatus.PENDING
    category: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "dependencies": self.dependencies,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else str(self.priority),
            "estimated_effort": self.estimated_effort,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "category": self.category
        }


@dataclass
class GoalPlan:
    goal: str
    tasks: List[GoalTask] = field(default_factory=list)
    critical_path: List[str] = field(default_factory=list)
    has_contradiction: bool = False
    contradictions: List[str] = field(default_factory=list)
    alternative_recommendation: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "critical_path": self.critical_path,
            "has_contradiction": self.has_contradiction,
            "contradictions": self.contradictions,
            "alternative_recommendation": self.alternative_recommendation,
            "created_at": self.created_at
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Memory / Knowledge Engine Models
# ─────────────────────────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    EPISODIC = "episodic"       # Action history, session events
    SEMANTIC = "semantic"       # General knowledge, technology facts
    PROJECT = "project"         # Codebase architecture, configs, stack facts
    TASK = "task"               # Current execution state & decisions
    PREFERENCE = "preference"   # Explicit user preferences & constraints


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    type: MemoryType = MemoryType.SEMANTIC
    source: str = "user_input"
    confidence: float = 0.95
    timestamp: float = field(default_factory=time.time)
    relevance: float = 1.0
    tags: List[str] = field(default_factory=list)
    verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type.value if isinstance(self.type, MemoryType) else str(self.type),
            "source": self.source,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
            "relevance": round(self.relevance, 2),
            "tags": self.tags,
            "verified": self.verified
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Skill / Plugin Architecture Models
# ─────────────────────────────────────────────────────────────────────────────

class SkillPermission(str, Enum):
    READ_SCREEN = "READ_SCREEN"
    READ_FILES = "READ_FILES"
    WRITE_FILES = "WRITE_FILES"
    EXECUTE_COMMAND = "EXECUTE_COMMAND"
    NETWORK = "NETWORK"
    SYSTEM_CONTROL = "SYSTEM_CONTROL"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class SkillMetadata:
    name: str
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    permissions: List[SkillPermission] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "permissions": [p.value if isinstance(p, SkillPermission) else str(p) for p in self.permissions],
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "enabled": self.enabled
        }


@dataclass
class SkillResult:
    success: bool
    skill_name: str
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "skill_name": self.skill_name,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 2)
        }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Risk & Safety Engine Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskAssessment:
    action_name: str
    risk_level: RiskLevel
    requires_confirmation: bool
    reason: str
    hazards: List[str] = field(default_factory=list)
    suggested_mitigations: List[str] = field(default_factory=list)
    target_resource: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_name": self.action_name,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "requires_confirmation": self.requires_confirmation,
            "reason": self.reason,
            "hazards": self.hazards,
            "suggested_mitigations": self.suggested_mitigations,
            "target_resource": self.target_resource
        }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Performance Intelligence Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PerformanceMetric:
    operation: str
    latency_ms: float
    success: bool
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceSnapshot:
    avg_response_ms: float
    decision_ms: float
    perception_ms: float
    ocr_ms: float
    execution_ms: float
    verification_ms: float
    memory_retrieval_ms: float
    tool_success_rate: float
    ai_failure_rate: float
    total_operations: int
    cpu_percent: float
    ram_percent: float
    anomalies: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_response_ms": round(self.avg_response_ms, 1),
            "decision_ms": round(self.decision_ms, 1),
            "perception_ms": round(self.perception_ms, 1),
            "ocr_ms": round(self.ocr_ms, 1),
            "execution_ms": round(self.execution_ms, 1),
            "verification_ms": round(self.verification_ms, 1),
            "memory_retrieval_ms": round(self.memory_retrieval_ms, 1),
            "tool_success_rate": round(self.tool_success_rate, 1),
            "ai_failure_rate": round(self.ai_failure_rate, 1),
            "total_operations": self.total_operations,
            "cpu_percent": round(self.cpu_percent, 1),
            "ram_percent": round(self.ram_percent, 1),
            "anomalies": self.anomalies,
            "timestamp": self.timestamp
        }
