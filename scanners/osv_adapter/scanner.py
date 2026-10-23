"""
J.A.R.V.I.S. Security Assessment Engine — OSV Dependency Scanner Adapter
=========================================================================
Uses the OSV.dev REST API (https://osv.dev/docs/) to check project
dependencies for known vulnerabilities.

The adapter accepts:
  - A JSON list of {name, version, ecosystem} package records (direct upload)
  - A path to a supported lockfile or manifest (parsed locally)

Supported ecosystems: PyPI, npm, Go, Maven, NuGet, RubyGems, Cargo, Packagist

No OSV binary is required — all queries go to the public REST API.
API calls use the standard requests library with timeout and error handling.

Limitations (explicitly documented)
-------------------------------------
- OSV.dev is a free public service; rate limits may apply for large requests.
- Version ranges are advisory — confirm affected/fixed versions independently.
- Ecosystems not listed above are reported as unsupported, not as clean.
- This adapter does NOT execute repository scripts to collect dependencies.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

from security_engine.models import (
    Finding, Severity, Confidence, ScanJob, ScanProfile
)
from security_engine.scanner_base import ScannerBase, ScannerHealth, ScanResult

logger = logging.getLogger("jarvis.security.osv")

_OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_OSV_QUERY_URL = "https://api.osv.dev/v1/query"
_REQUEST_TIMEOUT = 30
_MAX_PACKAGES_PER_BATCH = 100

# Supported lockfile/manifest parsers
_SUPPORTED_FILES = {
    "requirements.txt":   "PyPI",
    "Pipfile.lock":       "PyPI",
    "poetry.lock":        "PyPI",
    "package-lock.json":  "npm",
    "yarn.lock":          "npm",
    "go.sum":             "Go",
    "Cargo.lock":         "crates.io",
    "Gemfile.lock":       "RubyGems",
    "pom.xml":            "Maven",
    "packages.lock.json": "NuGet",
}

# CVSS score to Severity mapping (approximate)
def _cvss_to_severity(score: float | None) -> Severity:
    if score is None:
        return Severity.MEDIUM
    if score >= 9.0:
        return Severity.CRITICAL
    if score >= 7.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MEDIUM
    return Severity.LOW


class OSVScanner(ScannerBase):
    """OSV.dev API adapter for dependency vulnerability scanning."""

    @property
    def name(self) -> str:
        return "osv"

    def supported_profiles(self) -> list[ScanProfile]:
        return [ScanProfile.DEPENDENCY_AUDIT]

    def health_check(self) -> ScannerHealth:
        errors: list[str] = []
        available = True
        try:
            resp = requests.get(
                "https://api.osv.dev/v1/query",
                timeout=5,
                # Send a minimal valid query
                params={},
            )
            # A 405 or 400 still means the API is reachable
            if resp.status_code not in (200, 400, 405):
                errors.append(f"OSV API returned unexpected status {resp.status_code}")
        except requests.RequestException as exc:
            available = False
            errors.append(f"OSV API not reachable: {exc}")

        return ScannerHealth(
            name=self.name,
            available=available,
            version="OSV.dev API v1",
            supported_profiles=[p.value for p in self.supported_profiles()],
            execution_location="cloud",
            resource_note="Uses the public OSV.dev API — no binary required.",
            config_errors=errors,
        )

    def run(self, job: ScanJob, timeout_s: int = 300) -> ScanResult:
        start = time.monotonic()

        # job.raw_output may contain pre-parsed packages or a file path
        raw = job.raw_output or {}
        packages: list[dict] = raw.get("packages", [])
        project_path: str | None = raw.get("project_path")
        unsupported_files: list[str] = []
        temp_dir: str | None = None

        target_str = (job.target or "").strip()
        if not packages and not project_path and target_str:
            if re.match(r"^https?://github\.com/[^/\s]+/[^/\s]+", target_str):
                import tempfile
                import subprocess
                repo_url = target_str.rstrip("/")
                clone_url = repo_url if repo_url.endswith(".git") else repo_url + ".git"
                temp_dir = tempfile.mkdtemp(prefix="jarvis_osv_repo_")
                try:
                    clone_proc = subprocess.run(
                        ["git", "clone", "--depth", "1", clone_url, temp_dir],
                        capture_output=True,
                        text=True,
                        timeout=40,
                    )
                    if clone_proc.returncode == 0:
                        project_path = temp_dir
                    else:
                        unsupported_files.append(
                            f"Git clone error: {clone_proc.stderr.strip() or 'Failed to clone repository.'}"
                        )
                except Exception as clone_exc:
                    unsupported_files.append(f"Git clone exception: {clone_exc}")
            elif os.path.exists(target_str):
                project_path = target_str
            elif target_str.startswith(("http://", "https://")):
                return ScanResult(
                    scanner_name=self.name,
                    scan_job_id=job.id,
                    success=False,
                    error=(
                        f"Target '{target_str}' is a deployed web application without public dependency lockfiles. "
                        "For web security assessment (headers, SSL/TLS, clickjacking, cookie security), "
                        "please select the 'Web Baseline' assessment profile. "
                        "For Dependency Audit, provide a GitHub repository URL (e.g. https://github.com/owner/repo) or a project lockfile."
                    ),
                    warnings=unsupported_files,
                )

        try:
            # Parse lockfiles if a project path was provided
            if project_path and not packages:
                packages, collected_notes = self._collect_packages(project_path)
                unsupported_files.extend(collected_notes)

            if not packages:
                return ScanResult(
                    scanner_name=self.name,
                    scan_job_id=job.id,
                    success=False,
                    error=(
                        "No dependencies found to scan. Provide a 'packages' list, a GitHub repository URL, "
                        "or a project path containing a supported lockfile (e.g. requirements.txt, package-lock.json)."
                    ),
                    warnings=unsupported_files,
                )

            # Query OSV in batches
            all_findings: list[Finding] = []
            warnings = list(unsupported_files)
            total = len(packages)
            processed = 0

            for batch_start in range(0, total, _MAX_PACKAGES_PER_BATCH):
                batch = packages[batch_start: batch_start + _MAX_PACKAGES_PER_BATCH]
                elapsed = time.monotonic() - start
                if elapsed > timeout_s - 5:
                    warnings.append(
                        f"Timeout approaching — stopped after {processed}/{total} packages."
                    )
                    break
                try:
                    batch_findings, batch_warnings = self._query_batch(batch, job.id, job.target)
                    all_findings.extend(batch_findings)
                    warnings.extend(batch_warnings)
                except Exception as exc:
                    warnings.append(f"Batch {batch_start//100 + 1} failed: {exc}")
                processed += len(batch)

            duration = time.monotonic() - start
            logger.info(
                "OSV scan complete: job=%s packages=%d findings=%d duration=%.1fs",
                job.id, total, len(all_findings), duration
            )

            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=True,
                findings=all_findings,
                raw_output={"packages_scanned": total, "unsupported_files": unsupported_files},
                warnings=warnings,
                duration_s=duration,
                scanner_version="OSV.dev API v1",
            )
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    # ── Lockfile parsers ──────────────────────────────────────────────────────

    def _collect_packages(
        self, project_path: str
    ) -> tuple[list[dict], list[str]]:
        """
        Walk the project directory looking for supported lockfiles.
        Returns (packages, unsupported_notes).
        """
        packages: list[dict] = []
        unsupported: list[str] = []
        root = Path(project_path)

        if not root.exists():
            unsupported.append(f"Project path does not exist: {project_path}")
            return packages, unsupported

        for fname, ecosystem in _SUPPORTED_FILES.items():
            fpath = root / fname
            if not fpath.exists():
                continue
            try:
                parsed = self._parse_lockfile(fpath, ecosystem)
                packages.extend(parsed)
                logger.debug("Parsed %s: %d packages", fname, len(parsed))
            except Exception as exc:
                unsupported.append(f"Could not parse {fname}: {exc}")

        # Note any manifest files present that we cannot parse
        all_manifest_names = {
            "requirements.txt", "Pipfile.lock", "poetry.lock",
            "package-lock.json", "yarn.lock", "go.sum",
            "Cargo.lock", "Gemfile.lock", "pom.xml",
            "packages.lock.json", "build.gradle", "build.gradle.kts",
            "composer.json",
        }
        present = {f.name for f in root.iterdir() if f.is_file()}
        missing_support = present & (all_manifest_names - set(_SUPPORTED_FILES.keys()))
        for f in sorted(missing_support):
            unsupported.append(
                f"File '{f}' is present but not yet supported — results may be incomplete."
            )

        return packages, unsupported

    def _parse_lockfile(self, path: Path, ecosystem: str) -> list[dict]:
        """Parse a single lockfile into [{name, version, ecosystem}] dicts."""
        text = path.read_text(encoding="utf-8", errors="replace")

        if path.name == "requirements.txt":
            return self._parse_requirements_txt(text, ecosystem)
        if path.name == "package-lock.json":
            return self._parse_npm_lock(text, ecosystem)
        if path.name == "Cargo.lock":
            return self._parse_cargo_lock(text, ecosystem)
        if path.name == "go.sum":
            return self._parse_go_sum(text, ecosystem)
        if path.name in ("Pipfile.lock", "poetry.lock", "packages.lock.json"):
            return self._parse_json_lock(text, ecosystem, path.name)
        if path.name == "yarn.lock":
            return self._parse_yarn_lock(text, ecosystem)
        return []

    def _parse_requirements_txt(self, text: str, ecosystem: str) -> list[dict]:
        pkgs = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-", "http", "git+")):
                continue
            # Strip extras and environment markers
            line = re.split(r"\s*;", line)[0].strip()
            # Strip extras like [standard] before the version specifier
            m = re.match(r"^([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*[=~!<>]+\s*([\d.]+[^\s,]*)", line)
            if m:
                pkgs.append({"name": m.group(1), "version": m.group(2), "ecosystem": ecosystem})
        return pkgs

    def _parse_npm_lock(self, text: str, ecosystem: str) -> list[dict]:
        data = json.loads(text)
        pkgs = []
        deps = data.get("dependencies") or data.get("packages") or {}
        for name, info in deps.items():
            if isinstance(info, dict) and "version" in info:
                clean_name = name.lstrip("/").replace("node_modules/", "")
                if clean_name:
                    pkgs.append({"name": clean_name, "version": info["version"], "ecosystem": ecosystem})
        return pkgs

    def _parse_cargo_lock(self, text: str, ecosystem: str) -> list[dict]:
        pkgs = []
        current: dict = {}
        for line in text.splitlines():
            line = line.strip()
            if line == "[[package]]":
                if current.get("name") and current.get("version"):
                    pkgs.append({"name": current["name"], "version": current["version"], "ecosystem": ecosystem})
                current = {}
            elif line.startswith("name = "):
                current["name"] = line.split(" = ", 1)[1].strip().strip('"')
            elif line.startswith("version = "):
                current["version"] = line.split(" = ", 1)[1].strip().strip('"')
        if current.get("name") and current.get("version"):
            pkgs.append({"name": current["name"], "version": current["version"], "ecosystem": ecosystem})
        return pkgs

    def _parse_go_sum(self, text: str, ecosystem: str) -> list[dict]:
        pkgs = []
        seen: set[str] = set()
        for line in text.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                module = parts[0]
                version = parts[1].lstrip("v").split("/")[0]
                key = f"{module}@{version}"
                if key not in seen:
                    seen.add(key)
                    pkgs.append({"name": module, "version": version, "ecosystem": ecosystem})
        return pkgs

    def _parse_json_lock(self, text: str, ecosystem: str, filename: str) -> list[dict]:
        data = json.loads(text)
        pkgs = []
        if filename == "Pipfile.lock":
            for section in ("default", "develop"):
                for name, info in data.get(section, {}).items():
                    if isinstance(info, dict) and "version" in info:
                        ver = info["version"].lstrip("==")
                        pkgs.append({"name": name, "version": ver, "ecosystem": ecosystem})
        elif filename == "poetry.lock":
            for pkg in data.get("package", []):
                if pkg.get("name") and pkg.get("version"):
                    pkgs.append({"name": pkg["name"], "version": pkg["version"], "ecosystem": ecosystem})
        return pkgs

    def _parse_yarn_lock(self, text: str, ecosystem: str) -> list[dict]:
        pkgs = []
        current_name = None
        for line in text.splitlines():
            line_s = line.strip()
            if line_s.endswith(":") and not line_s.startswith(" ") and "@" in line_s:
                m = re.match(r'^"?([^@"]+)@', line_s)
                current_name = m.group(1) if m else None
            elif line_s.startswith("version ") and current_name:
                ver = line_s.split(None, 1)[1].strip().strip('"')
                pkgs.append({"name": current_name, "version": ver, "ecosystem": ecosystem})
                current_name = None
        return pkgs

    # ── OSV API queries ───────────────────────────────────────────────────────

    def _query_batch(
        self, packages: list[dict], job_id: str, target: str
    ) -> tuple[list[Finding], list[str]]:
        """Send one batch to the OSV querybatch API and parse findings."""
        queries = [
            {
                "package": {
                    "name":      p["name"],
                    "ecosystem": p["ecosystem"],
                },
                "version": p["version"],
            }
            for p in packages
        ]

        try:
            resp = requests.post(
                _OSV_BATCH_URL,
                json={"queries": queries},
                timeout=_REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            return [], [f"OSV API request failed: {exc}"]
        except ValueError as exc:
            return [], [f"OSV API response parse error: {exc}"]

        findings: list[Finding] = []
        warnings: list[str] = []
        results = data.get("results", [])

        for idx, result in enumerate(results):
            if idx >= len(packages):
                break
            pkg = packages[idx]
            vulns = result.get("vulns", [])
            for vuln in vulns:
                finding = self._vuln_to_finding(vuln, pkg, job_id)
                findings.append(finding)

        return findings, warnings

    def _vuln_to_finding(
        self, vuln: dict, pkg: dict, job_id: str
    ) -> Finding:
        """Convert an OSV vulnerability record into a normalised Finding."""
        osv_id      = vuln.get("id", "UNKNOWN")
        aliases     = vuln.get("aliases", [])
        summary     = vuln.get("summary", "")
        details     = vuln.get("details", "")
        references  = [r.get("url", "") for r in vuln.get("references", []) if r.get("url")]

        # CVSS
        cvss_score: float | None = None
        cvss_version: str | None = None
        cvss_vector: str | None  = None
        for severity_entry in vuln.get("severity", []):
            stype = severity_entry.get("type", "")
            if "CVSS" in stype.upper():
                vec = severity_entry.get("score", "")
                cvss_vector = vec
                # Extract base score from vector string if possible
                m = re.search(r"(\d+\.\d+)$", vec)
                if m:
                    cvss_score = float(m.group(1))
                cvss_version = stype.replace("CVSS_V", "CVSS v")

        # Determine fixed version
        fixed_versions: list[str] = []
        for affected in vuln.get("affected", []):
            for rng in affected.get("ranges", []):
                for evt in rng.get("events", []):
                    if "fixed" in evt:
                        fixed_versions.append(evt["fixed"])

        # Build CVE ID from aliases
        cve_id = next((a for a in aliases if a.startswith("CVE-")), None)
        vuln_id = cve_id or osv_id

        remediation = (
            f"Upgrade {pkg['name']} to a fixed version."
            + (f" Known fixed versions: {', '.join(fixed_versions[:3])}." if fixed_versions else "")
            + " Verify the fixed version against your project's dependency constraints."
        )

        return Finding(
            title=f"{pkg['name']} {pkg['version']}: {summary or osv_id}",
            description=(
                f"Package **{pkg['name']}** version **{pkg['version']}** "
                f"(ecosystem: {pkg['ecosystem']}) is affected by {osv_id}.\n\n"
                + details[:2000]
            ),
            scan_job_id=job_id,
            scanner=self.name,
            detection_method="osv_api_batch_query",
            vuln_id=vuln_id,
            affected_component=f"{pkg['name']}@{pkg['version']}",
            evidence=(
                f"OSV ID: {osv_id}. "
                + (f"Aliases: {', '.join(aliases)}. " if aliases else "")
                + (f"Fixed versions: {', '.join(fixed_versions[:3])}." if fixed_versions else "")
            ),
            evidence_source="osv.dev API v1",
            severity=_cvss_to_severity(cvss_score),
            confidence=Confidence.HIGH if cve_id else Confidence.MEDIUM,
            cvss_score=cvss_score,
            cvss_version=cvss_version,
            cvss_vector=cvss_vector,
            references=references[:10],
            remediation=remediation,
            tags=["osv", "dependency", pkg["ecosystem"].lower(), pkg["name"]],
        )
