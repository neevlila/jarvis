"""
Data Models and Types for J.A.R.V.I.S. Idea Engine.
Strongly-typed dataclasses for request inputs, stack analysis, scoring, and output project ideas.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import time


class GenerationMode(str, Enum):
    STACK_TO_IDEAS = "stack_to_ideas"              # Mode A: Tech stack -> Ranked ideas
    PROBLEM_TO_STACK = "problem_to_stack"          # Mode B: Problem -> Recommended stack + Ideas
    STACK_AND_PROBLEM = "stack_and_problem"        # Mode C: Tech stack + Specific problem -> Complete Blueprint
    PROJECT_IMPROVEMENTS = "project_improvements"  # Mode D: Existing project -> Enhancements


class ScoreTier(str, Enum):
    EXCEPTIONAL = "Exceptional"  # 90 - 100
    STRONG = "Strong"            # 80 - 89
    GOOD = "Good"                # 70 - 79
    MODERATE = "Moderate"        # 60 - 69
    WEAK = "Weak"                # < 60


@dataclass
class TechnologyProfile:
    """Detailed profile of a single technology and its capabilities."""
    name: str
    category: str
    primary_capabilities: List[str] = field(default_factory=list)
    secondary_capabilities: List[str] = field(default_factory=list)
    best_for: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "primary_capabilities": self.primary_capabilities,
            "secondary_capabilities": self.secondary_capabilities,
            "best_for": self.best_for,
            "limitations": self.limitations
        }


@dataclass
class TechnologyMapping:
    """Specific role and justification for a technology used in a project idea."""
    technology: str
    role: str
    justification: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "technology": self.technology,
            "role": self.role,
            "justification": self.justification
        }


@dataclass
class ScoreBreakdown:
    """Transparent multi-criteria scoring breakdown."""
    stack_compatibility: float = 0.0   # Weight: 25%
    feasibility: float = 0.0           # Weight: 20%
    real_world_value: float = 0.0      # Weight: 20%
    technical_depth: float = 0.0       # Weight: 15%
    innovation: float = 0.0            # Weight: 10%
    portfolio_value: float = 0.0       # Weight: 10%
    overall_score: float = 0.0         # 0 - 100
    tier: ScoreTier = ScoreTier.GOOD

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stack_compatibility": round(self.stack_compatibility, 1),
            "feasibility": round(self.feasibility, 1),
            "real_world_value": round(self.real_world_value, 1),
            "technical_depth": round(self.technical_depth, 1),
            "innovation": round(self.innovation, 1),
            "portfolio_value": round(self.portfolio_value, 1),
            "overall_score": round(self.overall_score, 1),
            "tier": self.tier.value
        }


@dataclass
class DevelopmentPhase:
    """A single implementation phase in the project roadmap."""
    phase_name: str
    duration: str
    key_tasks: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "duration": self.duration,
            "key_tasks": self.key_tasks,
            "deliverables": self.deliverables
        }


@dataclass
class ProjectIdea:
    """Comprehensive, production-grade project idea."""
    id: str
    title: str
    one_line_pitch: str
    problem: str
    target_users: List[str]
    solution: str
    core_features: List[str]
    technology_usage: List[TechnologyMapping]
    architecture_summary: str
    data_flow: List[str] = field(default_factory=list)
    difficulty: str = "Medium"
    estimated_time: str = "2 weeks"
    score: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    risks: List[Dict[str, str]] = field(default_factory=list)  # [{"risk": "...", "mitigation": "..."}]
    future_expansion: List[str] = field(default_factory=list)
    roadmap: List[DevelopmentPhase] = field(default_factory=list)
    why_this_stack: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "one_line_pitch": self.one_line_pitch,
            "problem": self.problem,
            "target_users": self.target_users,
            "solution": self.solution,
            "core_features": self.core_features,
            "technology_usage": [t.to_dict() for t in self.technology_usage],
            "architecture_summary": self.architecture_summary,
            "data_flow": self.data_flow,
            "difficulty": self.difficulty,
            "estimated_time": self.estimated_time,
            "score": self.score.to_dict(),
            "risks": self.risks,
            "future_expansion": self.future_expansion,
            "roadmap": [r.to_dict() for r in self.roadmap],
            "why_this_stack": self.why_this_stack
        }


@dataclass
class StackAnalysis:
    """Synthesized capability analysis of the input technology stack."""
    technologies: List[TechnologyProfile] = field(default_factory=list)
    categories_present: List[str] = field(default_factory=list)
    missing_categories: List[str] = field(default_factory=list)
    synergies: List[str] = field(default_factory=list)
    recommended_problem_domains: List[str] = field(default_factory=list)
    architectural_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "technologies": [t.to_dict() for t in self.technologies],
            "categories_present": self.categories_present,
            "missing_categories": self.missing_categories,
            "synergies": self.synergies,
            "recommended_problem_domains": self.recommended_problem_domains,
            "architectural_warnings": self.architectural_warnings
        }


@dataclass
class IdeaGenerationRequest:
    """User input payload requesting idea generation."""
    technologies: List[str] = field(default_factory=list)
    problem_statement: Optional[str] = None
    mode: GenerationMode = GenerationMode.STACK_TO_IDEAS
    experience_level: str = "Intermediate"  # Beginner, Intermediate, Advanced, Expert
    project_type: str = "Portfolio Project"  # College, Portfolio, Research, Startup, Open Source, Hackathon
    time_available: str = "2 weeks"         # 2 days, 1 week, 2 weeks, 1 month, 3 months
    budget: str = "Free"                    # Free, Low, Moderate, No restriction
    goal: str = "Solve real-world problem"  # Learn new tech, Build portfolio, Startup, Hackathon
    domain: str = "Open-ended"              # Healthcare, Cybersecurity, Agriculture, FinTech, DevTools, etc.
    difficulty: str = "Medium"              # Easy, Medium, Hard, Advanced
    number_of_ideas: int = 5                # Default 5 to 10
    existing_project_details: Optional[Dict[str, Any]] = None  # For Mode D: {"title": "", "stack": [], "features": []}

    def clean_technologies(self) -> List[str]:
        """Normalizes and deduplicates technology names."""
        cleaned = []
        seen = set()
        for t in self.technologies:
            clean = t.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                cleaned.append(clean)
        return cleaned


@dataclass
class IdeaGenerationResult:
    """Complete structured result returned by the Idea Engine."""
    success: bool
    mode: str
    stack_analysis: StackAnalysis
    ideas: List[ProjectIdea] = field(default_factory=list)
    total_generated: int = 0
    top_recommendation: Optional[ProjectIdea] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode,
            "stack_analysis": self.stack_analysis.to_dict(),
            "ideas": [idea.to_dict() for idea in self.ideas],
            "total_generated": self.total_generated,
            "top_recommendation": self.top_recommendation.to_dict() if self.top_recommendation else None,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "error": self.error
        }


# ─────────────────────────────────────────────────────────────────────────────
# Master Build Prompt Models & Enums
# ─────────────────────────────────────────────────────────────────────────────

class VisualDirection(str, Enum):
    AUTO = "Auto (AI-Determined)"
    PREMIUM_MINIMAL = "Premium Minimal"
    CINEMATIC = "Cinematic"
    FUTURISTIC = "Futuristic"
    IMMERSIVE_3D = "Immersive 3D"
    EDITORIAL = "Editorial"
    ENTERPRISE = "Enterprise"
    DATA_DRIVEN = "Data-Driven"
    GLASS = "Glass"
    NEO_BRUTALIST = "Neo-Brutalist"
    CREATIVE = "Creative"
    CUSTOM = "Custom"


class MotionLevel(str, Enum):
    SUBTLE = "Subtle"
    BALANCED = "Balanced"
    CINEMATIC = "Cinematic"
    EXPERIMENTAL = "Experimental"


class ThreeDIntensity(str, Enum):
    AUTO = "Auto (AI-Determined)"
    NONE = "None"
    SUBTLE = "Subtle"
    MODERATE = "Moderate"
    IMMERSIVE = "Immersive"


class TargetPlatform(str, Enum):
    UNIVERSAL = "Universal"
    ANTIGRAVITY = "Antigravity"
    CURSOR = "Cursor"
    CLAUDE_CODE = "Claude Code"
    LOVABLE = "Lovable"
    V0 = "v0"
    BOLT = "Bolt"
    OTHER = "Other AI Coding Agent"


@dataclass
class MasterPromptConfig:
    """User preferences and configuration for prompt generation."""
    visual_direction: VisualDirection = VisualDirection.AUTO
    motion_level: MotionLevel = MotionLevel.BALANCED
    threed_intensity: ThreeDIntensity = ThreeDIntensity.AUTO
    target_platform: TargetPlatform = TargetPlatform.UNIVERSAL
    custom_visual_notes: Optional[str] = None
    project_scope: str = "Full-stack Production MVP"
    technical_depth: str = "High / Production-ready"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "visual_direction": self.visual_direction.value if isinstance(self.visual_direction, VisualDirection) else str(self.visual_direction),
            "motion_level": self.motion_level.value if isinstance(self.motion_level, MotionLevel) else str(self.motion_level),
            "threed_intensity": self.threed_intensity.value if isinstance(self.threed_intensity, ThreeDIntensity) else str(self.threed_intensity),
            "target_platform": self.target_platform.value if isinstance(self.target_platform, TargetPlatform) else str(self.target_platform),
            "custom_visual_notes": self.custom_visual_notes,
            "project_scope": self.project_scope,
            "technical_depth": self.technical_depth
        }


@dataclass
class PromptCompletenessScores:
    """Multi-dimensional completeness evaluation for generated master prompts."""
    overall: float = 95.0
    technical: float = 96.0
    ux_ui: float = 94.0
    visual_direction: float = 95.0
    implementation: float = 95.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "overall": round(self.overall, 1),
            "technical": round(self.technical, 1),
            "ux_ui": round(self.ux_ui, 1),
            "visual_direction": round(self.visual_direction, 1),
            "implementation": round(self.implementation, 1)
        }


@dataclass
class MasterBuildPrompt:
    """Comprehensive, production-ready Master Build Specification for AI Coding Agents."""
    prompt_id: str
    idea_id: str
    project_title: str
    config: MasterPromptConfig
    completeness_scores: PromptCompletenessScores
    full_markdown_prompt: str
    sections: Dict[str, str] = field(default_factory=dict)
    platform_adapted_prompt: str = ""
    created_at: float = field(default_factory=time.time)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "idea_id": self.idea_id,
            "project_title": self.project_title,
            "config": self.config.to_dict(),
            "completeness_scores": self.completeness_scores.to_dict(),
            "full_markdown_prompt": self.full_markdown_prompt,
            "sections": self.sections,
            "platform_adapted_prompt": self.platform_adapted_prompt or self.full_markdown_prompt,
            "created_at": self.created_at,
            "version": self.version
        }

