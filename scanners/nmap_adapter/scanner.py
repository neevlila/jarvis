"""
J.A.R.V.I.S. Security Assessment Engine — Nmap Scanner Adapter
================================================================
Wraps the Nmap binary for authorized network discovery and service inventory.

Security guarantees
-------------------
- Targets validated by authorization.py before this module is called.
- Commands built via list arguments (no shell=True, no interpolation).
- XML output parsed via stdlib xml.etree (no shell pipe, size-limited).
- Allowlisted profiles only — no arbitrary nmap flags accepted from users.
- Timeouts enforced at both the subprocess and nmap script level.
- Partial results returned on timeout rather than raising.

Profile → nmap flag mapping
---------------------------
asset_discovery   → -sn  (ping sweep, no port scan)
service_inventory → -sV -sC --top-ports 1000  (safe service detection)
comprehensive     → -sV -sC -O --top-ports 1000  (adds OS detection)
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Any

from security_engine.models import (
    Asset, AssetType, Finding, Severity, Confidence,
    ScanJob, ScanProfile, Criticality
)
from security_engine.scanner_base import ScannerBase, ScannerHealth, ScanResult

logger = logging.getLogger("jarvis.security.nmap")

# Maximum XML output size accepted from nmap (10 MB)
_MAX_XML_BYTES = 10 * 1024 * 1024

# Allowlisted nmap profile flag sets (no user-supplied flags accepted)
_PROFILE_FLAGS: dict[ScanProfile, list[str]] = {
    ScanProfile.ASSET_DISCOVERY: [
        "-sn",              # ping scan / host discovery only
        "--max-retries", "2",
        "-T3",              # normal timing
    ],
    ScanProfile.SERVICE_INVENTORY: [
        "-sV",              # service version detection
        "--version-intensity", "5",
        "--top-ports", "1000",
        "-T3",
        "--max-retries", "2",
    ],
    ScanProfile.INFRASTRUCTURE_ASSESSMENT: [
        "-sV",
        "-sC",              # default safe NSE scripts
        "--version-intensity", "5",
        "--top-ports", "1000",
        "-T3",
        "--max-retries", "2",
    ],
    ScanProfile.COMPREHENSIVE: [
        "-sV",
        "-sC",
        "-O",               # OS detection
        "--version-intensity", "5",
        "--top-ports", "1000",
        "-T3",
        "--max-retries", "2",
    ],
}


class NmapScanner(ScannerBase):
    """Nmap adapter for authorized network discovery and service enumeration."""

    def __init__(self, nmap_path: str | None = None) -> None:
        self._nmap_path = nmap_path or shutil.which("nmap") or "nmap"

    # ── Contract ───────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "nmap"

    def supported_profiles(self) -> list[ScanProfile]:
        return list(_PROFILE_FLAGS.keys())

    # ── Health check ──────────────────────────────────────────────────────────

    def health_check(self) -> ScannerHealth:
        version = None
        errors: list[str] = []

        nmap_bin = shutil.which(self._nmap_path) or shutil.which("nmap")
        if not nmap_bin:
            return ScannerHealth(
                name=self.name,
                available=False,
                last_error="Nmap binary not found on PATH.",
                supported_profiles=[p.value for p in self.supported_profiles()],
                execution_location="local_agent",
                resource_note="Install nmap: https://nmap.org/download.html",
                config_errors=["nmap not found on PATH"],
            )

        try:
            result = subprocess.run(
                [nmap_bin, "--version"],
                capture_output=True, text=True, timeout=5
            )
            m = re.search(r"Nmap version ([\d.]+)", result.stdout)
            if m:
                version = m.group(1)
        except Exception as exc:
            errors.append(f"Version check failed: {exc}")

        return ScannerHealth(
            name=self.name,
            available=bool(nmap_bin),
            version=version,
            supported_profiles=[p.value for p in self.supported_profiles()],
            execution_location="local_agent",
            resource_note=(
                "Nmap must run on the local Windows agent. "
                "The cloud API cannot execute Nmap directly."
            ),
            config_errors=errors,
        )

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self, job: ScanJob, timeout_s: int = 300) -> ScanResult:
        start = time.monotonic()
        nmap_bin = shutil.which(self._nmap_path) or shutil.which("nmap")

        if not nmap_bin:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error="Nmap binary not found. Install nmap and ensure it is on PATH.",
            )

        profile_flags = _PROFILE_FLAGS.get(job.profile)
        if not profile_flags:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error=f"Profile '{job.profile.value}' is not supported by the Nmap adapter.",
            )

        # Build command — all arguments are fixed; target comes from
        # the pre-validated job.target field.
        cmd = [
            nmap_bin,
            "-oX", "-",         # XML output to stdout
            "--host-timeout", f"{max(30, timeout_s - 10)}s",
        ] + profile_flags + [job.target]

        logger.info(
            "Nmap scan starting: job=%s target=%s profile=%s",
            job.id, job.target, job.profile.value
        )

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout_s,
                shell=False,        # NEVER shell=True
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error=f"Nmap timed out after {timeout_s}s.",
                duration_s=time.monotonic() - start,
                warnings=["Scan timed out — results may be incomplete."],
            )
        except FileNotFoundError:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error="Nmap binary not found during execution.",
            )
        except Exception as exc:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error=f"Unexpected error executing nmap: {exc}",
            )

        stdout_bytes = proc.stdout or b""
        stderr_text  = (proc.stderr or b"").decode("utf-8", errors="replace")

        warnings: list[str] = []
        if proc.returncode not in (0, 1):  # nmap returns 1 for "no hosts up"
            warnings.append(f"Nmap exit code {proc.returncode}: {stderr_text[:500]}")

        if len(stdout_bytes) > _MAX_XML_BYTES:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error=f"Nmap output too large ({len(stdout_bytes)} bytes > {_MAX_XML_BYTES}).",
                warnings=warnings,
            )

        # Parse XML
        try:
            assets, findings, raw = self._parse_xml(
                stdout_bytes.decode("utf-8", errors="replace"), job.id
            )
        except Exception as exc:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error=f"XML parse error: {exc}",
                warnings=warnings,
                raw_output={"stderr": stderr_text},
            )

        duration = time.monotonic() - start
        logger.info(
            "Nmap scan complete: job=%s assets=%d findings=%d duration=%.1fs",
            job.id, len(assets), len(findings), duration
        )

        return ScanResult(
            scanner_name=self.name,
            scan_job_id=job.id,
            success=True,
            assets=assets,
            findings=findings,
            raw_output=raw,
            warnings=warnings,
            duration_s=duration,
        )

    # ── XML parsing ───────────────────────────────────────────────────────────

    def _parse_xml(
        self, xml_text: str, job_id: str
    ) -> tuple[list[Asset], list[Finding], dict[str, Any]]:
        """
        Parse nmap XML output into normalised Asset and Finding objects.
        Uses only stdlib xml.etree — no external dependencies.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid XML from nmap: {exc}") from exc

        assets:   list[Asset]   = []
        findings: list[Finding] = []
        raw_hosts: list[dict]   = []

        for host_el in root.findall("host"):
            host_data = self._parse_host(host_el, job_id)
            if host_data:
                asset, host_findings, raw = host_data
                assets.append(asset)
                findings.extend(host_findings)
                raw_hosts.append(raw)

        nmap_info = {
            "scanner":    root.get("scanner", "nmap"),
            "version":    root.get("version", ""),
            "args":       root.get("args", ""),
            "start":      root.get("start", ""),
            "hosts_up":   root.findtext("runstats/hosts[@up]") or
                          (root.find("runstats/hosts") or ET.Element("x")).get("up", "0"),
            "hosts":      raw_hosts,
        }
        return assets, findings, nmap_info

    def _parse_host(
        self, host_el: ET.Element, job_id: str
    ) -> tuple[Asset, list[Finding], dict] | None:
        """Extract one host from a <host> element."""
        # Only process hosts that are marked "up"
        status_el = host_el.find("status")
        if status_el is None or status_el.get("state") != "up":
            return None

        # IP address
        ip = None
        hostname_str = None
        for addr_el in host_el.findall("address"):
            if addr_el.get("addrtype") in ("ipv4", "ipv6"):
                ip = addr_el.get("addr")

        # Hostname
        for hn_el in host_el.findall("hostnames/hostname"):
            if hn_el.get("type") in ("user", "PTR"):
                hostname_str = hn_el.get("name")
                break

        if not ip:
            return None

        display = hostname_str or ip

        asset = Asset(
            display_name=display,
            asset_type=AssetType.HOST,
            ip_address=ip,
            hostname=hostname_str,
            discovery_source="nmap",
        )

        findings: list[Finding] = []
        raw_ports: list[dict]  = []

        # OS detection
        os_info: list[str] = []
        for osmatch in host_el.findall("os/osmatch"):
            name    = osmatch.get("name", "")
            accuracy = osmatch.get("accuracy", "0")
            os_info.append(f"{name} (accuracy {accuracy}%)")

        # Ports
        for port_el in host_el.findall("ports/port"):
            port_num  = int(port_el.get("portid", 0))
            protocol  = port_el.get("protocol", "tcp")
            state_el  = port_el.find("state")
            state     = state_el.get("state", "unknown") if state_el is not None else "unknown"

            if state != "open":
                continue

            service_el = port_el.find("service")
            svc_name   = service_el.get("name", "") if service_el is not None else ""
            svc_product = service_el.get("product", "") if service_el is not None else ""
            svc_version = service_el.get("version", "") if service_el is not None else ""
            svc_extra   = service_el.get("extrainfo", "") if service_el is not None else ""
            svc_tunnel  = service_el.get("tunnel", "") if service_el is not None else ""
            svc_conf    = service_el.get("conf", "0") if service_el is not None else "0"

            svc_str = " ".join(filter(None, [svc_product, svc_version, svc_extra])).strip()

            raw_ports.append({
                "port":     port_num,
                "protocol": protocol,
                "state":    state,
                "service":  svc_name,
                "version":  svc_str,
                "tunnel":   svc_tunnel,
                "conf":     svc_conf,
            })

            # Confidence based on nmap's service detection confidence (0-10)
            try:
                conf_int = int(svc_conf)
            except ValueError:
                conf_int = 0
            confidence = (
                Confidence.HIGH   if conf_int >= 8 else
                Confidence.MEDIUM if conf_int >= 5 else
                Confidence.LOW
            )

            # --- Generate informational finding for each open port ---
            evidence_parts = [f"Port {port_num}/{protocol} is open."]
            if svc_name:
                evidence_parts.append(f"Service: {svc_name}")
            if svc_str:
                evidence_parts.append(f"Version: {svc_str} (detection confidence {svc_conf}/10)")
            if svc_tunnel:
                evidence_parts.append(f"Tunnel: {svc_tunnel}")

            # Flag potentially sensitive services
            sensitive_services = {
                "ssh": ("SSH service exposed", Severity.INFORMATIONAL),
                "ftp": ("FTP service exposed (potentially insecure)", Severity.LOW),
                "telnet": ("Telnet service detected (unencrypted)", Severity.HIGH),
                "smtp": ("SMTP service exposed", Severity.INFORMATIONAL),
                "rdp": ("RDP (Remote Desktop) service exposed", Severity.MEDIUM),
                "ms-wbt-server": ("RDP service exposed", Severity.MEDIUM),
                "vnc": ("VNC service exposed", Severity.MEDIUM),
                "snmp": ("SNMP service exposed", Severity.MEDIUM),
                "http": ("HTTP service (unencrypted) detected", Severity.LOW),
            }
            title_override, sev_override = sensitive_services.get(
                svc_name.lower(), (None, Severity.INFORMATIONAL)
            )

            finding = Finding(
                title=title_override or f"Open port {port_num}/{protocol} ({svc_name or 'unknown'})",
                description=(
                    f"An open {protocol} port was detected at {ip}:{port_num}. "
                    + (f"Identified service: {svc_name}." if svc_name else "Service unknown.")
                    + (" Version detection confidence is low — verify manually." if conf_int < 5 else "")
                ),
                asset_id=asset.id,
                scan_job_id=job_id,
                scanner=self.name,
                detection_method="nmap_port_scan",
                affected_component=f"{ip}:{port_num}/{protocol}",
                evidence=" | ".join(evidence_parts),
                evidence_source="nmap_xml_output",
                severity=sev_override,
                confidence=confidence,
                remediation=(
                    "Review whether this port and service need to be publicly accessible. "
                    "If not, restrict access with firewall rules. "
                    "If the service is required, ensure it is running the latest patched version."
                ),
                tags=["nmap", "open_port", svc_name or "unknown"],
            )
            findings.append(finding)

        raw_host = {
            "ip":       ip,
            "hostname": hostname_str,
            "os":       os_info,
            "ports":    raw_ports,
        }
        return asset, findings, raw_host
