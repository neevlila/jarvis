"""
J.A.R.V.I.S. Security Assessment Engine — JSON-backed Persistence Store
========================================================================
Lightweight, file-backed store for assets, scan jobs, findings, scopes,
and remediation records.  Thread-safe via a per-collection RLock.

Designed to run without any database driver.  The store can be replaced
with SQLAlchemy / Supabase later — callers depend only on this interface.

Files are written atomically (write tmp → rename) to prevent corruption.
"""

from __future__ import annotations

import json
import os
import threading
import time
import logging
from pathlib import Path
from typing import Callable, Optional

from .models import (
    Asset, AssetType,
    AuthorizedScope, ScanProfile,
    ScanJob, ScanStatus,
    Finding, Severity, VerificationStatus,
    RemediationRecord, RemediationStatus,
    Criticality,
)

logger = logging.getLogger("jarvis.security.store")

_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "jarvis_security_data")


class SecurityStore:
    """
    Thread-safe, JSON-backed store for all security assessment data.

    Collections
    -----------
    assets          – Asset inventory
    scopes          – Authorization scopes
    scan_jobs       – Scan job lifecycle records
    findings        – Normalized findings from all scanners
    remediations    – Remediation lifecycle records
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self._dir = Path(data_dir or _DEFAULT_DATA_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)

        self._lock: dict[str, threading.RLock] = {
            "assets":       threading.RLock(),
            "scopes":       threading.RLock(),
            "scan_jobs":    threading.RLock(),
            "findings":     threading.RLock(),
            "remediations": threading.RLock(),
        }

        # In-memory cache per collection
        self._cache: dict[str, dict] = {k: {} for k in self._lock}

        # Load persisted data at startup
        for collection in self._lock:
            self._load(collection)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _path(self, collection: str) -> Path:
        return self._dir / f"{collection}.json"

    def _load(self, collection: str) -> None:
        p = self._path(collection)
        if not p.exists():
            return
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                with self._lock[collection]:
                    self._cache[collection] = data
        except Exception as exc:
            logger.error("Failed to load %s: %s", collection, exc)

    def _save(self, collection: str) -> None:
        p = self._path(collection)
        tmp = p.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._cache[collection], fh, indent=2)
            tmp.replace(p)
        except Exception as exc:
            logger.error("Failed to save %s: %s", collection, exc)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def _upsert(self, collection: str, record_id: str, record: dict) -> None:
        with self._lock[collection]:
            self._cache[collection][record_id] = record
            self._save(collection)

    def _get(self, collection: str, record_id: str) -> dict | None:
        with self._lock[collection]:
            return self._cache[collection].get(record_id)

    def _list(self, collection: str,
               predicate: Callable[[dict], bool] | None = None) -> list[dict]:
        with self._lock[collection]:
            records = list(self._cache[collection].values())
        if predicate:
            records = [r for r in records if predicate(r)]
        return records

    def _delete(self, collection: str, record_id: str) -> bool:
        with self._lock[collection]:
            if record_id in self._cache[collection]:
                del self._cache[collection][record_id]
                self._save(collection)
                return True
        return False

    # ── Assets ────────────────────────────────────────────────────────────────

    def save_asset(self, asset: Asset) -> Asset:
        self._upsert("assets", asset.id, asset.to_dict())
        return asset

    def get_asset(self, asset_id: str) -> Asset | None:
        d = self._get("assets", asset_id)
        return Asset.from_dict(d) if d else None

    def list_assets(self, asset_type: AssetType | None = None) -> list[Asset]:
        pred = (lambda r: r.get("asset_type") == asset_type.value) if asset_type else None
        return [Asset.from_dict(r) for r in self._list("assets", pred)]

    def delete_asset(self, asset_id: str) -> bool:
        return self._delete("assets", asset_id)

    def find_or_create_asset(self, ip: str | None, hostname: str | None,
                              display_name: str, asset_type: AssetType,
                              discovery_source: str = "nmap") -> Asset:
        """Return existing asset matching IP or hostname; create one if absent."""
        for asset in self.list_assets():
            if ip and asset.ip_address == ip:
                asset.last_seen = time.time()
                if hostname and not asset.hostname:
                    asset.hostname = hostname
                self.save_asset(asset)
                return asset
            if hostname and asset.hostname and asset.hostname.lower() == hostname.lower():
                asset.last_seen = time.time()
                if ip and not asset.ip_address:
                    asset.ip_address = ip
                self.save_asset(asset)
                return asset
        new_asset = Asset(
            display_name=display_name,
            asset_type=asset_type,
            ip_address=ip,
            hostname=hostname,
            discovery_source=discovery_source,
        )
        return self.save_asset(new_asset)

    # ── Authorized Scopes ─────────────────────────────────────────────────────

    def save_scope(self, scope: AuthorizedScope) -> AuthorizedScope:
        self._upsert("scopes", scope.id, scope.to_dict())
        return scope

    def get_scope(self, scope_id: str) -> AuthorizedScope | None:
        d = self._get("scopes", scope_id)
        return AuthorizedScope.from_dict(d) if d else None

    def list_scopes(self, owner: str | None = None) -> list[AuthorizedScope]:
        pred = (lambda r: r.get("owner") == owner) if owner else None
        return [AuthorizedScope.from_dict(r) for r in self._list("scopes", pred)]

    # ── Scan Jobs ─────────────────────────────────────────────────────────────

    def save_scan_job(self, job: ScanJob) -> ScanJob:
        self._upsert("scan_jobs", job.id, job.to_dict())
        return job

    def get_scan_job(self, job_id: str) -> ScanJob | None:
        d = self._get("scan_jobs", job_id)
        return ScanJob.from_dict(d) if d else None

    def list_scan_jobs(self, status: ScanStatus | None = None,
                       limit: int = 50) -> list[ScanJob]:
        pred = (lambda r: r.get("status") == status.value) if status else None
        jobs = [ScanJob.from_dict(r) for r in self._list("scan_jobs", pred)]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def update_job_status(self, job_id: str, status: ScanStatus,
                          progress_pct: int = 0, progress_msg: str = "",
                          error: str | None = None) -> ScanJob | None:
        job = self.get_scan_job(job_id)
        if not job:
            return None
        job.status       = status
        job.progress_pct = progress_pct
        job.progress_msg = progress_msg
        if error:
            job.error_summary = error
        if status == ScanStatus.RUNNING and not job.start_time:
            job.start_time = time.time()
        if status in (ScanStatus.COMPLETED, ScanStatus.FAILED,
                      ScanStatus.CANCELLED, ScanStatus.TIMEOUT):
            job.end_time = time.time()
        return self.save_scan_job(job)

    # ── Findings ──────────────────────────────────────────────────────────────

    def save_finding(self, finding: Finding) -> Finding:
        self._upsert("findings", finding.id, finding.to_dict())
        return finding

    def get_finding(self, finding_id: str) -> Finding | None:
        d = self._get("findings", finding_id)
        return Finding.from_dict(d) if d else None

    def list_findings(self,
                      asset_id: str | None = None,
                      scan_job_id: str | None = None,
                      severity: Severity | None = None,
                      include_false_positives: bool = False,
                      limit: int = 500) -> list[Finding]:
        def pred(r: dict) -> bool:
            if r.get("false_positive") and not include_false_positives:
                return False
            if asset_id and r.get("asset_id") != asset_id:
                return False
            if scan_job_id and r.get("scan_job_id") != scan_job_id:
                return False
            if severity and r.get("severity") != severity.value:
                return False
            return True
        findings = [Finding.from_dict(r) for r in self._list("findings", pred)]
        findings.sort(key=lambda f: f.detected_at, reverse=True)
        return findings[:limit]

    def findings_summary(self) -> dict:
        """Return severity counts for the dashboard overview."""
        all_findings = self.list_findings(include_false_positives=False)
        counts: dict[str, int] = {s.value: 0 for s in Severity}
        for f in all_findings:
            counts[f.severity.value] += 1
        unresolved = sum(
            1 for f in all_findings
            if f.verification not in (
                VerificationStatus.RESOLVED,
                VerificationStatus.FALSE_POSITIVE
            )
        )
        return {
            "by_severity":   counts,
            "total":         len(all_findings),
            "unresolved":    unresolved,
        }

    # ── Remediation Records ───────────────────────────────────────────────────

    def save_remediation(self, rec: RemediationRecord) -> RemediationRecord:
        self._upsert("remediations", rec.id, rec.to_dict())
        return rec

    def get_remediation(self, rec_id: str) -> RemediationRecord | None:
        d = self._get("remediations", rec_id)
        return RemediationRecord.from_dict(d) if d else None

    def get_remediation_for_finding(self, finding_id: str) -> RemediationRecord | None:
        records = [
            RemediationRecord.from_dict(r)
            for r in self._list("remediations",
                                 lambda r: r.get("finding_id") == finding_id)
        ]
        return records[0] if records else None

    def list_remediations(self,
                          status: RemediationStatus | None = None) -> list[RemediationRecord]:
        pred = (lambda r: r.get("status") == status.value) if status else None
        return [RemediationRecord.from_dict(r) for r in self._list("remediations", pred)]

    # ── Overview stats ────────────────────────────────────────────────────────

    def overview(self) -> dict:
        jobs = self.list_scan_jobs(limit=1000)
        running  = sum(1 for j in jobs if j.status == ScanStatus.RUNNING)
        completed = sum(1 for j in jobs if j.status == ScanStatus.COMPLETED)
        return {
            "assets_total":      len(self.list_assets()),
            "scans_total":       len(jobs),
            "scans_running":     running,
            "scans_completed":   completed,
            "findings":          self.findings_summary(),
            "remediations_open": len(self.list_remediations(RemediationStatus.OPEN)),
        }
