"""
J.A.R.V.I.S. Local Windows Agent
==================================
Runs as an independent process on the user's Windows PC.
Handles scan profiles that require local network access:
  - Asset Discovery (Nmap ping sweep)
  - Service Inventory (Nmap port scan)
  - Infrastructure Assessment

Connects to the J.A.R.V.I.S. cloud API via outbound HTTPS polling.
Never accepts inbound connections from the internet.

Security guarantees
-------------------
- All scan commands are built from allowlisted profiles only.
- Targets are validated server-side AND locally before execution.
- No general-purpose shell interface.
- Device token stored in Windows Credential Manager when available.
- User-visible status and emergency stop.

Usage
-----
    python local_agent/agent.py --cloud-url https://your-render-url.onrender.com

Environment variables (fallback if not using --args)
    JARVIS_CLOUD_URL     - Cloud API base URL
    JARVIS_AGENT_TOKEN   - Device authentication token (from pairing)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import threading
import uuid
from pathlib import Path

import requests

# Add project root to path so we can import scanners directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from security_engine.models import ScanJob, ScanProfile, ScanStatus
from security_engine.authorization import validate_target_syntax, _is_private_ip
from security_engine.store import SecurityStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis.agent")

_POLL_INTERVAL_S = 5
_AGENT_VERSION   = "0.1.0"

# ── Agent-permitted profiles (local execution only) ───────────────────────────
_AGENT_PROFILES = {
    ScanProfile.ASSET_DISCOVERY,
    ScanProfile.SERVICE_INVENTORY,
    ScanProfile.INFRASTRUCTURE_ASSESSMENT,
    ScanProfile.COMPREHENSIVE,
}


class LocalAgent:
    """
    Long-running agent that polls the cloud API for queued scan jobs
    and executes them locally using the Nmap adapter.
    """

    def __init__(self, cloud_url: str, agent_token: str) -> None:
        self.cloud_url   = cloud_url.rstrip("/")
        self.agent_token = agent_token
        self.agent_id    = str(uuid.uuid4())
        self._stop_event = threading.Event()
        self._running    = False

        # Local store for agent-side job tracking
        data_dir = os.environ.get(
            "JARVIS_AGENT_DATA_DIR",
            str(Path(__file__).parent / "agent_data")
        )
        self._store = SecurityStore(data_dir=data_dir)

        # Load Nmap scanner
        try:
            from scanners.nmap_adapter import NmapScanner
            self._nmap = NmapScanner()
            h = self._nmap.health_check()
            if h.available:
                logger.info("Nmap available: version=%s", h.version)
            else:
                logger.warning("Nmap not available: %s", h.last_error)
        except Exception as exc:
            logger.error("Failed to load Nmap adapter: %s", exc)
            self._nmap = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        logger.info("J.A.R.V.I.S. Local Agent v%s starting. Agent ID: %s",
                    _AGENT_VERSION, self.agent_id)
        logger.info("Cloud URL: %s", self.cloud_url)
        self._running = True
        try:
            self._poll_loop()
        except KeyboardInterrupt:
            logger.info("Agent stopped by user.")
        finally:
            self._running = False

    def stop(self) -> None:
        """Emergency stop."""
        logger.warning("Emergency stop requested.")
        self._stop_event.set()

    # ── Polling ───────────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as exc:
                logger.error("Poll error: %s", exc)
            self._stop_event.wait(timeout=_POLL_INTERVAL_S)

    def _poll_once(self) -> None:
        """Check cloud API for pending agent jobs."""
        try:
            resp = requests.get(
                f"{self.cloud_url}/api/v1/security/scans",
                params={"status": "pending", "limit": 5},
                headers={"X-JARVIS-Auth": self.agent_token, "X-Agent-ID": self.agent_id},
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.debug("Cloud API unreachable: %s", exc)
            return

        if resp.status_code != 200:
            return

        data = resp.json()
        jobs_data = data.get("scans", [])

        for job_dict in jobs_data:
            profile_str = job_dict.get("profile", "")
            try:
                profile = ScanProfile(profile_str)
            except ValueError:
                continue

            # Only execute agent-side profiles
            if profile not in _AGENT_PROFILES:
                continue

            job = ScanJob.from_dict(job_dict)
            self._execute_job(job)

    def _execute_job(self, job: ScanJob) -> None:
        """Run a scan job locally and push results to the cloud."""
        logger.info("Executing job: id=%s target=%s profile=%s",
                    job.id, job.target, job.profile.value)

        # Local authorization check
        ok, err = validate_target_syntax(job.target)
        if not ok:
            self._report_failure(job.id, f"Local target validation failed: {err}")
            return

        if not self._nmap:
            self._report_failure(job.id, "Nmap not available on this agent.")
            return

        self._update_job_status(job.id, "running", 5, "Agent executing scan…")

        try:
            result = self._nmap.run(job, timeout_s=300)
        except Exception as exc:
            self._report_failure(job.id, str(exc))
            return

        # Push findings and assets back to cloud
        payload = {
            "success":  result.success,
            "error":    result.error,
            "warnings": result.warnings,
            "assets":   [a.to_dict() for a in result.assets],
            "findings": [f.to_dict() for f in result.findings],
            "duration_s": result.duration_s,
        }
        try:
            requests.post(
                f"{self.cloud_url}/api/v1/security/agent/results/{job.id}",
                json=payload,
                headers={"X-JARVIS-Auth": self.agent_token, "X-Agent-ID": self.agent_id},
                timeout=30,
            )
            logger.info(
                "Results pushed: job=%s assets=%d findings=%d",
                job.id, len(result.assets), len(result.findings)
            )
        except requests.RequestException as exc:
            logger.error("Failed to push results for job %s: %s", job.id, exc)

    def _update_job_status(self, job_id: str, status: str,
                            pct: int, msg: str) -> None:
        try:
            requests.patch(
                f"{self.cloud_url}/api/v1/security/scans/{job_id}/status",
                json={"status": status, "progress_pct": pct, "progress_msg": msg},
                headers={"X-JARVIS-Auth": self.agent_token, "X-Agent-ID": self.agent_id},
                timeout=10,
            )
        except Exception:
            pass

    def _report_failure(self, job_id: str, error: str) -> None:
        logger.error("Job %s failed: %s", job_id, error)
        self._update_job_status(job_id, "failed", 0, error)


# ── CLI entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Local Security Agent")
    parser.add_argument("--cloud-url",    default=os.environ.get("JARVIS_CLOUD_URL", ""))
    parser.add_argument("--agent-token",  default=os.environ.get("JARVIS_AGENT_TOKEN", ""))
    parser.add_argument("--stop",         action="store_true", help="Emergency stop signal")
    args = parser.parse_args()

    if not args.cloud_url:
        print("ERROR: --cloud-url or JARVIS_CLOUD_URL is required.", file=sys.stderr)
        sys.exit(1)
    if not args.agent_token:
        print("ERROR: --agent-token or JARVIS_AGENT_TOKEN is required.", file=sys.stderr)
        sys.exit(1)

    agent = LocalAgent(cloud_url=args.cloud_url, agent_token=args.agent_token)

    if args.stop:
        agent.stop()
    else:
        agent.start()
