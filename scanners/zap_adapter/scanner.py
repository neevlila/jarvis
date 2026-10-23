"""
OWASP ZAP Scanner Adapter — Stub
=================================
Status: NOT IMPLEMENTED — placeholder only.

ZAP requires:
  - A running ZAP instance (local Docker or dedicated worker)
  - ZAP API key configured in environment (ZAP_API_KEY, ZAP_API_URL)
  - Explicit authorized web application targets
  - Passive-only mode by default; active scan requires explicit opt-in

This stub reports ZAP as unavailable so the dashboard correctly shows
its status.  Implement run() when a ZAP instance is provisioned.

Resource note: ZAP requires a separate process (minimum 512 MB RAM).
Do NOT run ZAP inside the Render free-tier web service.
"""

from __future__ import annotations

import os
from security_engine.models import ScanJob, ScanProfile
from security_engine.scanner_base import ScannerBase, ScannerHealth, ScanResult


class ZAPScanner(ScannerBase):

    @property
    def name(self) -> str:
        return "zap"

    def supported_profiles(self) -> list[ScanProfile]:
        return [ScanProfile.WEB_BASELINE]

    def health_check(self) -> ScannerHealth:
        api_url = os.environ.get("ZAP_API_URL", "")
        api_key = os.environ.get("ZAP_API_KEY", "")
        errors = []
        if not api_url:
            errors.append("ZAP_API_URL is not configured.")
        if not api_key:
            errors.append("ZAP_API_KEY is not configured.")
        return ScannerHealth(
            name=self.name,
            available=False,
            last_error="ZAP adapter not yet implemented." if not errors else None,
            supported_profiles=[p.value for p in self.supported_profiles()],
            execution_location="worker",
            resource_note=(
                "Requires a separately provisioned OWASP ZAP instance. "
                "See https://www.zaproxy.org/docs/docker/about/ for setup. "
                "Set ZAP_API_URL and ZAP_API_KEY environment variables."
            ),
            config_errors=errors or ["ZAP adapter not yet implemented."],
        )

    def run(self, job: ScanJob, timeout_s: int = 300) -> ScanResult:
        return ScanResult(
            scanner_name=self.name,
            scan_job_id=job.id,
            success=False,
            error=(
                "ZAP scanner is not yet implemented. "
                "Configure ZAP_API_URL and ZAP_API_KEY, then implement this adapter."
            ),
        )
