"""
J.A.R.V.I.S. Security Assessment Engine — Unified Data Models
==============================================================
Defines the normalized data model for assets, scan jobs, findings,
and remediation records.  All IDs use uuid4.  Serialisation via to_dict().

No ORM dependency — models are plain dataclasses stored in the JSON-backed
SecurityStore.  SQLAlchemy / Supabase can be added later without changing
these schemas.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class AssetType(str, Enum):
    HOST      = "host"
    WEB_APP   = "web_app"
    NETWORK   = "network"
    CONTAINER = "container"
    REPO      = "repository"
    UNKNOWN   = "unknown"


class ScanStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"
    TIMEOUT    = "timeout"


class ScanProfile(str, Enum):
    ASSET_DISCOVERY           = "asset_discovery"
    SERVICE_INVENTORY         = "service_inventory"
    WEB_BASELINE              = "web_baseline"
    DEPENDENCY_AUDIT          = "dependency_audit"
    INFRASTRUCTURE_ASSESSMENT = "infrastructure_assessment"
    COMPREHENSIVE             = "comprehensive"


class Severity(str, Enum):
    CRITICAL      = "critical"
    HIGH          = "high"
    MEDIUM        = "medium"
    LOW           = "low"
    INFORMATIONAL = "informational"


class Confidence(str, Enum):
    CONFIRMED = "confirmed"
    HIGH      = "high"
    MEDIUM    = "medium"
    LOW       = "low"
    UNCERTAIN = "uncertain"


class VerificationStatus(str, Enum):
    UNVERIFIED   = "unverified"
    CONFIRMED    = "confirmed"
    FALSE_POSITIVE = "false_positive"
    NOT_RETESTED = "not_retested"
    RESOLVED     = "resolved"
    STILL_PRESENT = "still_present"
    INCONCLUSIVE = "inconclusive"


class RemediationStatus(str, Enum):
    OPEN        = "open"
    IN_PROGRESS = "in_progress"
    PENDING_RETEST = "pending_retest"
    RESOLVED    = "resolved"
    ACCEPTED_RISK = "accepted_risk"
    WONT_FIX    = "wont_fix"


class Criticality(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


# ─────────────────────────────────────────────────────────────────────────────
# Asset
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Asset:
    display_name:   str             = ""
    asset_type:     AssetType       = AssetType.UNKNOWN
    ip_address:     str | None      = None
    hostname:       str | None      = None
    port:           int | None      = None
    protocol:       str | None      = None
    scope_id:       str | None      = None
    owner:          str | None      = None
    environment:    str             = "unknown"
    criticality:    Criticality     = Criticality.MEDIUM
    discovery_source: str           = "manual"
    tags:           list[str]       = field(default_factory=list)
    metadata:       dict[str, Any]  = field(default_factory=dict)
    first_seen:     float           = field(default_factory=time.time)
    last_seen:      float           = field(default_factory=time.time)
    id:             str             = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "display_name":     self.display_name,
            "asset_type":       self.asset_type.value,
            "ip_address":       self.ip_address,
            "hostname":         self.hostname,
            "port":             self.port,
            "protocol":         self.protocol,
            "scope_id":         self.scope_id,
            "owner":            self.owner,
            "environment":      self.environment,
            "criticality":      self.criticality.value,
            "discovery_source": self.discovery_source,
            "tags":             self.tags,
            "metadata":         self.metadata,
            "first_seen":       self.first_seen,
            "last_seen":        self.last_seen,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Asset":
        obj = cls.__new__(cls)
        obj.id               = d.get("id", str(uuid.uuid4()))
        obj.display_name     = d.get("display_name", "")
        obj.asset_type       = AssetType(d.get("asset_type", "unknown"))
        obj.ip_address       = d.get("ip_address")
        obj.hostname         = d.get("hostname")
        obj.port             = d.get("port")
        obj.protocol         = d.get("protocol")
        obj.scope_id         = d.get("scope_id")
        obj.owner            = d.get("owner")
        obj.environment      = d.get("environment", "unknown")
        obj.criticality      = Criticality(d.get("criticality", "medium"))
        obj.discovery_source = d.get("discovery_source", "manual")
        obj.tags             = d.get("tags", [])
        obj.metadata         = d.get("metadata", {})
        obj.first_seen       = d.get("first_seen", time.time())
        obj.last_seen        = d.get("last_seen", time.time())
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Authorized Scope
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuthorizedScope:
    """Defines what targets are permitted for a scan job."""
    targets:          list[str]         # IP, CIDR, hostname, or URL
    profiles_allowed: list[ScanProfile]
    owner:            str
    notes:            str               = ""
    acknowledged_at:  float             = field(default_factory=time.time)
    expires_at:       float | None      = None
    id:               str               = field(default_factory=lambda: str(uuid.uuid4()))

    def is_valid(self) -> bool:
        if self.expires_at and time.time() > self.expires_at:
            return False
        return bool(self.targets)

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "targets":          self.targets,
            "profiles_allowed": [p.value for p in self.profiles_allowed],
            "owner":            self.owner,
            "notes":            self.notes,
            "acknowledged_at":  self.acknowledged_at,
            "expires_at":       self.expires_at,
            "is_valid":         self.is_valid(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AuthorizedScope":
        obj = cls.__new__(cls)
        obj.id               = d.get("id", str(uuid.uuid4()))
        obj.targets          = d.get("targets", [])
        obj.profiles_allowed = [ScanProfile(p) for p in d.get("profiles_allowed", [])]
        obj.owner            = d.get("owner", "")
        obj.notes            = d.get("notes", "")
        obj.acknowledged_at  = d.get("acknowledged_at", time.time())
        obj.expires_at       = d.get("expires_at")
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Scan Job
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScanJob:
    target:          str
    profile:         ScanProfile
    initiated_by:    str                        = "system"
    scope_id:        str | None                 = None
    scanners:        list[str]                  = field(default_factory=list)
    status:          ScanStatus                 = ScanStatus.PENDING
    progress_pct:    int                        = 0
    progress_msg:    str                        = "Queued"
    start_time:      float | None               = None
    end_time:        float | None               = None
    error_summary:   str | None                 = None
    result_ids:      list[str]                  = field(default_factory=list)  # finding IDs
    asset_ids:       list[str]                  = field(default_factory=list)
    raw_output:      dict[str, Any]             = field(default_factory=dict)
    cancelled:       bool                       = False
    created_at:      float                      = field(default_factory=time.time)
    id:              str                        = field(default_factory=lambda: str(uuid.uuid4()))

    def duration_seconds(self) -> float | None:
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 2)
        return None

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "target":        self.target,
            "profile":       self.profile.value,
            "initiated_by":  self.initiated_by,
            "scope_id":      self.scope_id,
            "scanners":      self.scanners,
            "status":        self.status.value,
            "progress_pct":  self.progress_pct,
            "progress_msg":  self.progress_msg,
            "start_time":    self.start_time,
            "end_time":      self.end_time,
            "duration_s":    self.duration_seconds(),
            "error_summary": self.error_summary,
            "result_ids":    self.result_ids,
            "asset_ids":     self.asset_ids,
            "cancelled":     self.cancelled,
            "created_at":    self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScanJob":
        obj = cls.__new__(cls)
        obj.id            = d.get("id", str(uuid.uuid4()))
        obj.target        = d.get("target", "")
        obj.profile       = ScanProfile(d.get("profile", "asset_discovery"))
        obj.initiated_by  = d.get("initiated_by", "system")
        obj.scope_id      = d.get("scope_id")
        obj.scanners      = d.get("scanners", [])
        obj.status        = ScanStatus(d.get("status", "pending"))
        obj.progress_pct  = d.get("progress_pct", 0)
        obj.progress_msg  = d.get("progress_msg", "")
        obj.start_time    = d.get("start_time")
        obj.end_time      = d.get("end_time")
        obj.error_summary = d.get("error_summary")
        obj.result_ids    = d.get("result_ids", [])
        obj.asset_ids     = d.get("asset_ids", [])
        obj.raw_output    = d.get("raw_output", {})
        obj.cancelled     = d.get("cancelled", False)
        obj.created_at    = d.get("created_at", time.time())
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Finding
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    title:              str
    description:        str
    asset_id:           str                 = ""
    scan_job_id:        str                 = ""
    scanner:            str                 = "unknown"
    detection_method:   str                 = ""
    vuln_id:            str | None          = None  # CVE, advisory, rule ID
    affected_component: str                 = ""
    evidence:           str                 = ""
    evidence_source:    str                 = ""
    severity:           Severity            = Severity.INFORMATIONAL
    confidence:         Confidence          = Confidence.MEDIUM
    cvss_score:         float | None        = None
    cvss_version:       str | None          = None
    cvss_vector:        str | None          = None
    cwe_id:             str | None          = None
    references:         list[str]           = field(default_factory=list)
    remediation:        str                 = ""
    verification:       VerificationStatus  = VerificationStatus.UNVERIFIED
    false_positive:     bool                = False
    fp_justification:   str                 = ""
    related_finding_ids: list[str]          = field(default_factory=list)
    tags:               list[str]           = field(default_factory=list)
    detected_at:        float               = field(default_factory=time.time)
    first_seen:         float               = field(default_factory=time.time)
    last_seen:          float               = field(default_factory=time.time)
    id:                 str                 = field(default_factory=lambda: str(uuid.uuid4()))

    def contextual_priority(self, asset_criticality: Criticality = Criticality.MEDIUM) -> str:
        """
        Derive a contextual priority that considers both scanner severity
        and asset criticality.  Keeps original scanner severity separate.
        """
        sev_rank = {
            Severity.CRITICAL: 4, Severity.HIGH: 3,
            Severity.MEDIUM: 2, Severity.LOW: 1, Severity.INFORMATIONAL: 0
        }
        crit_rank = {
            Criticality.CRITICAL: 2, Criticality.HIGH: 1,
            Criticality.MEDIUM: 0, Criticality.LOW: -1
        }
        conf_penalty = {
            Confidence.CONFIRMED: 0, Confidence.HIGH: 0,
            Confidence.MEDIUM: -1, Confidence.LOW: -1, Confidence.UNCERTAIN: -2
        }
        score = (
            sev_rank.get(self.severity, 0) * 2
            + crit_rank.get(asset_criticality, 0)
            + conf_penalty.get(self.confidence, 0)
        )
        if score >= 7:
            return "critical"
        if score >= 5:
            return "high"
        if score >= 3:
            return "medium"
        if score >= 1:
            return "low"
        return "informational"

    def to_dict(self, asset_criticality: Criticality = Criticality.MEDIUM) -> dict:
        return {
            "id":                  self.id,
            "title":               self.title,
            "description":         self.description,
            "asset_id":            self.asset_id,
            "scan_job_id":         self.scan_job_id,
            "scanner":             self.scanner,
            "detection_method":    self.detection_method,
            "vuln_id":             self.vuln_id,
            "affected_component":  self.affected_component,
            "evidence":            self.evidence,
            "evidence_source":     self.evidence_source,
            "severity":            self.severity.value,
            "confidence":          self.confidence.value,
            "cvss_score":          self.cvss_score,
            "cvss_version":        self.cvss_version,
            "cvss_vector":         self.cvss_vector,
            "cwe_id":              self.cwe_id,
            "references":          self.references,
            "remediation":         self.remediation,
            "verification":        self.verification.value,
            "false_positive":      self.false_positive,
            "fp_justification":    self.fp_justification,
            "related_finding_ids": self.related_finding_ids,
            "tags":                self.tags,
            "detected_at":         self.detected_at,
            "first_seen":          self.first_seen,
            "last_seen":           self.last_seen,
            "contextual_priority": self.contextual_priority(asset_criticality),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Finding":
        obj = cls.__new__(cls)
        obj.id                  = d.get("id", str(uuid.uuid4()))
        obj.title               = d.get("title", "")
        obj.description         = d.get("description", "")
        obj.asset_id            = d.get("asset_id", "")
        obj.scan_job_id         = d.get("scan_job_id", "")
        obj.scanner             = d.get("scanner", "unknown")
        obj.detection_method    = d.get("detection_method", "")
        obj.vuln_id             = d.get("vuln_id")
        obj.affected_component  = d.get("affected_component", "")
        obj.evidence            = d.get("evidence", "")
        obj.evidence_source     = d.get("evidence_source", "")
        obj.severity            = Severity(d.get("severity", "informational"))
        obj.confidence          = Confidence(d.get("confidence", "medium"))
        obj.cvss_score          = d.get("cvss_score")
        obj.cvss_version        = d.get("cvss_version")
        obj.cvss_vector         = d.get("cvss_vector")
        obj.cwe_id              = d.get("cwe_id")
        obj.references          = d.get("references", [])
        obj.remediation         = d.get("remediation", "")
        obj.verification        = VerificationStatus(d.get("verification", "unverified"))
        obj.false_positive      = d.get("false_positive", False)
        obj.fp_justification    = d.get("fp_justification", "")
        obj.related_finding_ids = d.get("related_finding_ids", [])
        obj.tags                = d.get("tags", [])
        obj.detected_at         = d.get("detected_at", time.time())
        obj.first_seen          = d.get("first_seen", time.time())
        obj.last_seen           = d.get("last_seen", time.time())
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Remediation Record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RemediationRecord:
    finding_id:          str
    recommended_action:  str                    = ""
    assigned_owner:      str                    = ""
    status:              RemediationStatus       = RemediationStatus.OPEN
    notes:               list[str]              = field(default_factory=list)
    retest_job_id:       str | None             = None
    verification_result: VerificationStatus     = VerificationStatus.NOT_RETESTED
    closed_at:           float | None           = None
    created_at:          float                  = field(default_factory=time.time)
    id:                  str                    = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id":                  self.id,
            "finding_id":          self.finding_id,
            "recommended_action":  self.recommended_action,
            "assigned_owner":      self.assigned_owner,
            "status":              self.status.value,
            "notes":               self.notes,
            "retest_job_id":       self.retest_job_id,
            "verification_result": self.verification_result.value,
            "closed_at":           self.closed_at,
            "created_at":          self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RemediationRecord":
        obj = cls.__new__(cls)
        obj.id                  = d.get("id", str(uuid.uuid4()))
        obj.finding_id          = d.get("finding_id", "")
        obj.recommended_action  = d.get("recommended_action", "")
        obj.assigned_owner      = d.get("assigned_owner", "")
        obj.status              = RemediationStatus(d.get("status", "open"))
        obj.notes               = d.get("notes", [])
        obj.retest_job_id       = d.get("retest_job_id")
        obj.verification_result = VerificationStatus(d.get("verification_result", "not_retested"))
        obj.closed_at           = d.get("closed_at")
        obj.created_at          = d.get("created_at", time.time())
        return obj
