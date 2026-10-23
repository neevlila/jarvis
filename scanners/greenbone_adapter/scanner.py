"""
Greenbone/OpenVAS Scanner Adapter — Stub
==========================================
Status: NOT IMPLEMENTED — placeholder only.

Greenbone requires:
  - Greenbone Community Edition on a separately provisioned Linux host
  - GVM protocol API credentials (GREENBONE_HOST, GREENBONE_USER, GREENBONE_PASSWORD)
  - Minimum 2 GB RAM — cannot run on Render free tier

This stub reports the scanner as unavailable so the dashboard shows
its correct status. Implement run() when a Greenbone host is available.
"""

from __future__ import annotations

import os
from security_engine.models import ScanJob, ScanProfile
from security_engine.scanner_base import ScannerBase, ScannerHealth, ScanResult


class GreenboneScanner(ScannerBase):

    @property
    def name(self) -> str:
        return "greenbone"

    def supported_profiles(self) -> list[ScanProfile]:
        return [ScanProfile.INFRASTRUCTURE_ASSESSMENT, ScanProfile.COMPREHENSIVE]

    def health_check(self) -> ScannerHealth:
        host = os.environ.get("GREENBONE_HOST", "")
        errors = []
        if not host:
            errors.append("GREENBONE_HOST is not configured.")
        if not os.environ.get("GREENBONE_USER"):
            errors.append("GREENBONE_USER is not configured.")
        if not os.environ.get("GREENBONE_PASSWORD"):
            errors.append("GREENBONE_PASSWORD is not configured.")
        return ScannerHealth(
            name=self.name,
            available=False,
            last_error="Greenbone adapter not yet implemented.",
            supported_profiles=[p.value for p in self.supported_profiles()],
            execution_location="worker",
            resource_note=(
                "Requires Greenbone Community Edition on a dedicated Linux host. "
                "See https://greenbone.github.io/docs/latest/ for setup. "
                "Set GREENBONE_HOST, GREENBONE_USER, GREENBONE_PASSWORD."
            ),
            config_errors=errors or ["Greenbone adapter not yet implemented."],
        )

    def run(self, job: ScanJob, timeout_s: int = 300) -> ScanResult:
        return ScanResult(
            scanner_name=self.name,
            scan_job_id=job.id,
            success=False,
            error=(
                "Greenbone scanner is not yet implemented. "
                "Provision a Greenbone CE host and implement this adapter."
            ),
        )
