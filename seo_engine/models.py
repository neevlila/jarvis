"""
Data models and schemas for J.A.R.V.I.S. SEO Intelligence Subsystem.
Includes evidence-first classifications, category scores, findings,
prioritized action plans, and complete SEO audit reports.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import time
import uuid


class EvidenceType(str, Enum):
    OBSERVED = "OBSERVED"        # Direct observation from HTML markup, headers, or measurements
    INFERRED = "INFERRED"        # Heuristic interpretation or structural analysis
    UNAVAILABLE = "UNAVAILABLE"  # Signals not measurable from client-side inspection (e.g. Google ranking)


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    PASSED = "PASSED"


class SEOCategory(str, Enum):
    TECHNICAL = "Technical SEO"
    ON_PAGE = "On-Page SEO"
    CONTENT_STRUCTURE = "Content Structure"
    PERFORMANCE_SIGNALS = "Performance Signals"
    ACCESSIBILITY_SIGNALS = "Accessibility Signals"
    SOCIAL_METADATA = "Social Metadata"
    STRUCTURED_DATA = "Structured Data"
    CRAWLABILITY = "Crawlability Signals"


class ScoreTier(str, Enum):
    EXCEPTIONAL = "Exceptional"      # >= 90
    STRONG = "Strong"                # 80 - 89
    GOOD = "Good"                    # 70 - 79
    MODERATE = "Moderate"            # 60 - 69
    NEEDS_IMPROVEMENT = "Needs Improvement"  # < 60


@dataclass
class SEOFinding:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: SEOCategory = SEOCategory.TECHNICAL
    severity: FindingSeverity = FindingSeverity.MEDIUM
    title: str = ""
    problem: str = ""
    evidence: str = ""
    evidence_type: EvidenceType = EvidenceType.OBSERVED
    recommendation: str = ""
    impact: str = "Medium"          # High, Medium, Low
    effort: str = "Low"             # Low, Medium, High
    confidence: float = 1.0         # 0.0 to 1.0
    why_it_matters: str = ""
    source_location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value if isinstance(self.category, SEOCategory) else str(self.category),
            "severity": self.severity.value if isinstance(self.severity, FindingSeverity) else str(self.severity),
            "title": self.title,
            "problem": self.problem,
            "evidence": self.evidence,
            "evidence_type": self.evidence_type.value if isinstance(self.evidence_type, EvidenceType) else str(self.evidence_type),
            "recommendation": self.recommendation,
            "impact": self.impact,
            "effort": self.effort,
            "confidence": round(self.confidence, 2),
            "why_it_matters": self.why_it_matters,
            "source_location": self.source_location
        }


@dataclass
class CategoryScore:
    category: SEOCategory
    score: float
    weight: float
    passed_count: int = 0
    warning_count: int = 0
    critical_count: int = 0
    checks_summary: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value if isinstance(self.category, SEOCategory) else str(self.category),
            "score": round(self.score, 1),
            "weight": round(self.weight, 2),
            "passed_count": self.passed_count,
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "checks_summary": self.checks_summary
        }


@dataclass
class SEOActionItem:
    rank: int
    title: str
    action: str
    impact: str                     # Critical, High, Medium, Low
    effort: str                     # Low, Medium, High
    category: str = "Technical"
    why_it_matters: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "title": self.title,
            "action": self.action,
            "impact": self.impact,
            "effort": self.effort,
            "category": self.category,
            "why_it_matters": self.why_it_matters
        }


@dataclass
class PerformanceSignalsData:
    response_time_ms: float = 0.0
    document_size_bytes: int = 0
    script_count: int = 0
    stylesheet_count: int = 0
    image_count: int = 0
    total_resources: int = 0
    is_measured: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_time_ms": round(self.response_time_ms, 1),
            "document_size_bytes": self.document_size_bytes,
            "document_size_kb": round(self.document_size_bytes / 1024, 1),
            "script_count": self.script_count,
            "stylesheet_count": self.stylesheet_count,
            "image_count": self.image_count,
            "total_resources": self.total_resources,
            "is_measured": self.is_measured
        }


@dataclass
class SEOAuditReport:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target: str = ""                 # URL or Project directory
    mode: str = "url"                # "url" or "project"
    target_keyword: Optional[str] = None
    overall_score: float = 0.0
    tier: ScoreTier = ScoreTier.MODERATE
    summary: str = ""
    category_scores: Dict[str, CategoryScore] = field(default_factory=dict)
    findings: List[SEOFinding] = field(default_factory=list)
    action_plan: List[SEOActionItem] = field(default_factory=list)
    ai_recommendations: Optional[str] = None
    performance_signals: PerformanceSignalsData = field(default_factory=PerformanceSignalsData)
    html_title: str = ""
    meta_description: str = ""
    canonical_url: Optional[str] = None
    h1_headings: List[str] = field(default_factory=list)
    word_count: int = 0
    status_code: int = 200
    timestamp: float = field(default_factory=time.time)
    disclaimer: str = (
        "SEO Score is a technical and on-page audit score based on signals observable by J.A.R.V.I.S. "
        "It is not a Google ranking score."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target": self.target,
            "mode": self.mode,
            "target_keyword": self.target_keyword,
            "overall_score": round(self.overall_score, 1),
            "tier": self.tier.value if isinstance(self.tier, ScoreTier) else str(self.tier),
            "summary": self.summary,
            "category_scores": {k: v.to_dict() for k, v in self.category_scores.items()},
            "findings": [f.to_dict() for f in self.findings],
            "action_plan": [a.to_dict() for a in self.action_plan],
            "ai_recommendations": self.ai_recommendations,
            "performance_signals": self.performance_signals.to_dict(),
            "html_title": self.html_title,
            "meta_description": self.meta_description,
            "canonical_url": self.canonical_url,
            "h1_headings": self.h1_headings,
            "word_count": self.word_count,
            "status_code": self.status_code,
            "timestamp": self.timestamp,
            "disclaimer": self.disclaimer
        }
