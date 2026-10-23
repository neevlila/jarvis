"""
J.A.R.V.I.S. Security Assessment Engine — Scan Orchestrator
============================================================
Coordinates the full assessment lifecycle:
  Authorize → Discover → Scan → Normalize → Store → Report

Thread-safe.  Long-running scans execute in daemon threads so the Flask
worker thread is never blocked.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from .models import (
    AuthorizedScope, ScanJob, ScanProfile, ScanStatus,
    Finding, Asset, RemediationRecord,
)
from .authorization import authorize_scan, validate_target_syntax
from .scanner_base import ScannerRegistry, ScanResult
from .store import SecurityStore

logger = logging.getLogger("jarvis.security.orchestrator")


class SecurityOrchestrator:
    """
    Entry point for all security assessment operations.

    Usage
    -----
    orchestrator = SecurityOrchestrator(store, registry)
    job = orchestrator.submit_scan(target, profile, scope, initiated_by)
    # job.id can be polled via orchestrator.get_job(job.id)
    """

    def __init__(
        self,
        store: SecurityStore,
        registry: ScannerRegistry,
        max_concurrent_scans: int = 2,
    ) -> None:
        self._store     = store
        self._registry  = registry
        self._sem       = threading.Semaphore(max_concurrent_scans)
        self._lock      = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def submit_scan(
        self,
        target: str,
        profile: ScanProfile,
        scope: AuthorizedScope,
        initiated_by: str = "api",
        from_cloud: bool = True,
        timeout_s: int = 300,
        project_path: str | None = None,
        packages: list[dict] | None = None,
    ) -> tuple[ScanJob, str | None]:
        """
        Validate authorization and enqueue a scan.

        Returns (job, error_message).  If error_message is not None,
        the job was rejected and no scan thread was started.
        """
        # Syntax check
        ok, syntax_err = validate_target_syntax(target)
        if not ok:
            return self._reject(target, profile, scope, initiated_by, syntax_err)

        # Authorization check
        authz = authorize_scan(target, profile, scope, from_cloud=from_cloud)
        if not authz:
            return self._reject(target, profile, scope, initiated_by, authz.reason)

        # Find capable scanners
        capable = self._registry.scanners_for_profile(profile)
        if not capable:
            return self._reject(
                target, profile, scope, initiated_by,
                f"No available scanner supports profile '{profile.value}'."
            )

        # Create and persist the job
        job = ScanJob(
            target=target,
            profile=profile,
            initiated_by=initiated_by,
            scope_id=scope.id,
            scanners=[s.name for s in capable],
            status=ScanStatus.PENDING,
            progress_msg="Queued — waiting for scan slot.",
        )
        # Attach extra data for scanners that need it
        if project_path:
            job.raw_output["project_path"] = project_path
        if packages:
            job.raw_output["packages"] = packages

        self._store.save_scan_job(job)

        # Start background thread
        t = threading.Thread(
            target=self._run_scan,
            args=(job.id, capable, timeout_s),
            daemon=True,
            name=f"jarvis-scan-{job.id[:8]}",
        )
        t.start()

        logger.info(
            "Scan submitted: job=%s target=%s profile=%s scanners=%s",
            job.id, target, profile.value, [s.name for s in capable]
        )
        return job, None

    def cancel_scan(self, job_id: str) -> tuple[bool, str]:
        """Request cancellation of a pending or running scan."""
        job = self._store.get_scan_job(job_id)
        if not job:
            return False, "Job not found."
        if job.status in (ScanStatus.COMPLETED, ScanStatus.FAILED,
                          ScanStatus.CANCELLED, ScanStatus.TIMEOUT):
            return False, f"Job is already in terminal state '{job.status.value}'."
        job.cancelled = True
        self._store.save_scan_job(job)
        self._store.update_job_status(job_id, ScanStatus.CANCELLED, 0, "Cancelled by user.")
        return True, "Cancellation requested."

    def get_job(self, job_id: str) -> ScanJob | None:
        return self._store.get_scan_job(job_id)

    def list_jobs(self, limit: int = 50) -> list[ScanJob]:
        return self._store.list_scan_jobs(limit=limit)

    def overview(self) -> dict:
        return self._store.overview()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _reject(
        self, target: str, profile: ScanProfile,
        scope: AuthorizedScope, initiated_by: str, reason: str
    ) -> tuple[ScanJob, str]:
        job = ScanJob(
            target=target,
            profile=profile,
            initiated_by=initiated_by,
            scope_id=scope.id,
            status=ScanStatus.FAILED,
            error_summary=reason,
            progress_msg=f"Rejected: {reason}",
        )
        job.start_time = time.time()
        job.end_time   = time.time()
        self._store.save_scan_job(job)
        logger.warning("Scan rejected: target=%s reason=%s", target, reason)
        return job, reason

    def _run_scan(
        self, job_id: str, scanners: list, timeout_s: int
    ) -> None:
        """Background thread: acquire slot, run scanners, persist results."""
        # Acquire concurrency slot
        acquired = self._sem.acquire(blocking=True, timeout=60)
        if not acquired:
            self._store.update_job_status(
                job_id, ScanStatus.FAILED,
                error="Server busy — too many concurrent scans. Please retry."
            )
            return

        try:
            job = self._store.get_scan_job(job_id)
            if not job or job.cancelled:
                return

            self._store.update_job_status(
                job_id, ScanStatus.RUNNING, 5, "Scan starting…"
            )

            all_assets:   list[Asset]   = []
            all_findings: list[Finding] = []
            n = len(scanners)

            for idx, scanner in enumerate(scanners):
                job = self._store.get_scan_job(job_id)
                if job and job.cancelled:
                    self._store.update_job_status(
                        job_id, ScanStatus.CANCELLED, 0, "Cancelled during execution."
                    )
                    return

                pct = 10 + int(((idx) / n) * 80)
                self._store.update_job_status(
                    job_id, ScanStatus.RUNNING, pct,
                    f"Running {scanner.name} ({idx+1}/{n})…"
                )

                try:
                    job = self._store.get_scan_job(job_id)
                    result: ScanResult = scanner.run(job, timeout_s=timeout_s)
                except Exception as exc:
                    logger.error("Scanner %s raised: %s", scanner.name, exc, exc_info=True)
                    result = ScanResult(
                        scanner_name=scanner.name,
                        scan_job_id=job_id,
                        success=False,
                        error=str(exc),
                    )

                # Persist assets
                for asset in result.assets:
                    saved = self._store.find_or_create_asset(
                        ip=asset.ip_address,
                        hostname=asset.hostname,
                        display_name=asset.display_name,
                        asset_type=asset.asset_type,
                        discovery_source=scanner.name,
                    )
                    # Remap finding asset IDs to the de-duplicated asset
                    for f in result.findings:
                        if f.asset_id == asset.id:
                            f.asset_id = saved.id
                    all_assets.append(saved)

                # Persist findings
                for finding in result.findings:
                    finding.scan_job_id = job_id
                    self._store.save_finding(finding)
                    all_findings.append(finding)

                if result.warnings:
                    logger.warning(
                        "Scanner %s warnings: %s", scanner.name, result.warnings
                    )

            # Update job with final state
            final_job = self._store.get_scan_job(job_id)
            if final_job:
                final_job.result_ids = [f.id for f in all_findings]
                final_job.asset_ids  = list({a.id for a in all_assets})
                self._store.save_scan_job(final_job)

            self._store.update_job_status(
                job_id, ScanStatus.COMPLETED, 100,
                f"Complete — {len(all_assets)} assets, {len(all_findings)} findings."
            )
            logger.info(
                "Scan complete: job=%s assets=%d findings=%d",
                job_id, len(all_assets), len(all_findings)
            )

        except Exception as exc:
            logger.error("Orchestrator error for job %s: %s", job_id, exc, exc_info=True)
            self._store.update_job_status(
                job_id, ScanStatus.FAILED,
                error=f"Internal orchestrator error: {exc}"
            )
        finally:
            self._sem.release()
