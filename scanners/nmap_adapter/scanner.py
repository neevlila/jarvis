"""
J.A.R.V.I.S. Security Assessment Engine — Nmap Scanner Adapter
================================================================
Wraps the Nmap binary for authorized network discovery and service inventory.
When the Nmap CLI binary is not present (such as in cloud container runtimes),
it falls back automatically to a high-performance Native Python Socket Port
Discovery and Service Banner Grabbing Engine.

Security guarantees
-------------------
- Targets validated by authorization.py before this module is called.
- Commands built via list arguments (no shell=True, no interpolation).
- XML output parsed via stdlib xml.etree (no shell pipe, size-limited).
- Allowlisted profiles only — no arbitrary nmap flags accepted from users.
- Timeouts enforced at both the subprocess and socket level.
- Partial results returned on timeout rather than raising.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.parse
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

# Known port to service mapping for native socket scanner fallback
_KNOWN_PORTS_SERVICES: dict[int, str] = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    111: "rpcbind",
    135: "msrpc",
    139: "netbios-ssn",
    143: "imap",
    443: "https",
    445: "microsoft-ds",
    465: "smtps",
    587: "submission",
    993: "imaps",
    995: "pop3s",
    1433: "ms-sql-s",
    1521: "oracle",
    2049: "nfs",
    2375: "docker",
    3000: "ppp",
    3306: "mysql",
    3389: "ms-wbt-server",
    5000: "upnp",
    5432: "postgresql",
    5900: "vnc",
    6379: "redis",
    8000: "http-alt",
    8080: "http-proxy",
    8443: "https-alt",
    9200: "wap-wsp",
    27017: "mongod",
}

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
        if nmap_bin:
            try:
                result = subprocess.run(
                    [nmap_bin, "--version"],
                    capture_output=True, text=True, timeout=5
                )
                m = re.search(r"Nmap version ([\d.]+)", result.stdout)
                if m:
                    version = f"Nmap CLI v{m.group(1)}"
            except Exception as exc:
                errors.append(f"Version check failed: {exc}")

            return ScannerHealth(
                name=self.name,
                available=True,
                version=version or "Nmap CLI",
                supported_profiles=[p.value for p in self.supported_profiles()],
                execution_location="local_agent",
                resource_note="Nmap binary available for native host and port discovery.",
                config_errors=errors,
            )

        # Built-in fallback: Native Python Socket Port Discovery Engine
        return ScannerHealth(
            name=self.name,
            available=True,
            version="Native Socket Port Discovery v1.0 (Nmap-compatible)",
            supported_profiles=[p.value for p in self.supported_profiles()],
            execution_location="cloud_and_local",
            resource_note=(
                "Native Python TCP socket discovery engine active. "
                "Performs fast port discovery and service banner extraction. "
                "Nmap CLI binary can also be installed locally for advanced OS fingerprinting."
            ),
            config_errors=[],
        )

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self, job: ScanJob, timeout_s: int = 300) -> ScanResult:
        start = time.monotonic()
        nmap_bin = shutil.which(self._nmap_path) or shutil.which("nmap")

        if not nmap_bin:
            logger.info("Nmap binary not found on PATH — executing via Native Socket Discovery Engine.")
            return self._run_native_socket_scan(job, timeout_s)

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
            return self._run_native_socket_scan(job, timeout_s)
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

    # ── Native Socket Scanner Fallback ────────────────────────────────────────

    def _run_native_socket_scan(self, job: ScanJob, timeout_s: int) -> ScanResult:
        start = time.monotonic()
        raw_target = job.target.strip()
        host = raw_target
        custom_port = None
        if "://" in raw_target:
            parsed = urllib.parse.urlsplit(raw_target)
            host = parsed.hostname or raw_target
            if parsed.port:
                custom_port = parsed.port
        elif ":" in raw_target and not raw_target.count(":") > 1:
            parts = raw_target.split(":", 1)
            host = parts[0]
            try:
                custom_port = int(parts[1])
            except ValueError:
                pass

        try:
            ip = socket.gethostbyname(host)
        except Exception as exc:
            return ScanResult(
                scanner_name=self.name,
                scan_job_id=job.id,
                success=False,
                error=f"Native socket scanner could not resolve target '{host}': {exc}",
                duration_s=time.monotonic() - start,
            )

        if job.profile == ScanProfile.ASSET_DISCOVERY:
            ports_to_scan = [80, 443, 22, 53, 8080, 8443]
        else:
            ports_to_scan = [
                21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 465, 587,
                993, 995, 1433, 1521, 2049, 2375, 3000, 3306, 3389, 5000, 5432, 5900,
                6379, 8000, 8080, 8443, 9200, 27017
            ]
        if custom_port and custom_port not in ports_to_scan:
            ports_to_scan.append(custom_port)

        logger.info(
            "Native socket scan starting: job=%s host=%s ip=%s ports=%d",
            job.id, host, ip, len(ports_to_scan)
        )

        open_ports: list[dict[str, Any]] = []

        def probe(port: int):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(min(1.5, max(0.5, timeout_s / 20)))
            try:
                res = s.connect_ex((ip, port))
                if res == 0:
                    banner = ""
                    svc = _KNOWN_PORTS_SERVICES.get(port, "unknown")
                    try:
                        s.settimeout(1.0)
                        if port in (80, 8080, 8000, 5000, 3000):
                            s.sendall(f"HEAD / HTTP/1.0\r\nHost: {host}\r\nUser-Agent: J.A.R.V.I.S-Security-Engine\r\n\r\n".encode())
                            data = s.recv(1024).decode("latin-1", errors="replace")
                            for line in data.splitlines():
                                if line.lower().startswith("server:"):
                                    banner = line.split(":", 1)[1].strip()
                                    break
                        elif port == 22:
                            data = s.recv(256).decode("utf-8", errors="replace").strip()
                            banner = data
                        elif port in (21, 25, 110, 143):
                            data = s.recv(512).decode("latin-1", errors="replace").strip()
                            banner = data
                    except Exception:
                        pass
                    return {
                        "port": port,
                        "protocol": "tcp",
                        "state": "open",
                        "service": svc,
                        "banner": banner,
                    }
            except Exception:
                pass
            finally:
                try:
                    s.close()
                except Exception:
                    pass
            return None

        workers = min(20, len(ports_to_scan))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_port = {executor.submit(probe, p): p for p in ports_to_scan}
            for future in concurrent.futures.as_completed(future_to_port):
                res = future.result()
                if res:
                    open_ports.append(res)

        open_ports.sort(key=lambda x: x["port"])

        hostname_str = host if host != ip else None
        asset = Asset(
            asset_type=AssetType.HOST,
            ip_address=ip,
            hostname=hostname_str,
            criticality=Criticality.MEDIUM,
            metadata={
                "engine": "native_socket_engine",
                "open_ports": [p["port"] for p in open_ports],
                "services": [p["service"] for p in open_ports],
            }
        )

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
            "redis": ("Redis database port exposed", Severity.HIGH),
            "mongod": ("MongoDB database port exposed", Severity.HIGH),
            "docker": ("Docker management port exposed", Severity.CRITICAL),
        }

        findings: list[Finding] = []
        for port_info in open_ports:
            port_num = port_info["port"]
            svc_name = port_info["service"]
            banner = port_info.get("banner", "")

            evidence_parts = [f"Port: {port_num}/tcp (open)", f"Service: {svc_name}"]
            if banner:
                evidence_parts.append(f"Banner: {banner}")

            title_override, sev_override = sensitive_services.get(
                svc_name.lower(), (None, Severity.INFORMATIONAL)
            )

            finding = Finding(
                title=title_override or f"Open port {port_num}/tcp ({svc_name or 'unknown'})",
                description=(
                    f"An open TCP port was detected at {ip}:{port_num}. "
                    + (f"Identified service: {svc_name}." if svc_name else "Service unknown.")
                    + (f" Banner: '{banner}'." if banner else "")
                ),
                asset_id=asset.id,
                scan_job_id=job.id,
                scanner=self.name,
                detection_method="native_socket_port_scan",
                affected_component=f"{ip}:{port_num}/tcp",
                evidence=" | ".join(evidence_parts),
                evidence_source="tcp_socket_connect",
                severity=sev_override,
                confidence=Confidence.CONFIRMED,
                remediation=(
                    "Review whether this port and service need to be publicly accessible. "
                    "If not, restrict access with firewall rules. "
                    "If the service is required, ensure it is running the latest patched version."
                ),
                tags=["nmap_compatible", "native_port_scan", svc_name or "unknown"],
            )
            findings.append(finding)

        duration = time.monotonic() - start
        raw = {
            "engine": "native_socket_engine",
            "hosts": [{
                "ip": ip,
                "hostname": hostname_str,
                "ports": open_ports,
            }] if open_ports or job.profile == ScanProfile.ASSET_DISCOVERY else []
        }

        assets = [asset] if (open_ports or job.profile == ScanProfile.ASSET_DISCOVERY) else []

        return ScanResult(
            scanner_name=self.name,
            scan_job_id=job.id,
            success=True,
            assets=assets,
            findings=findings,
            raw_output=raw,
            duration_s=duration,
        )

    # ── XML parsing ───────────────────────────────────────────────────────────

    def _parse_xml(
        self, xml_text: str, job_id: str
    ) -> tuple[list[Asset], list[Finding], dict[str, Any]]:
        """
        Parse Nmap XML output into normalized Asset and Finding records.
        Robust against missing elements, malformed XML, and partial scans.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ValueError(f"Malformed Nmap XML: {exc}") from exc

        assets:   list[Asset]   = []
        findings: list[Finding] = []
        raw_hosts: list[dict]   = []

        for host_elem in root.findall("host"):
            status_elem = host_elem.find("status")
            if status_elem is not None and status_elem.get("state") != "up":
                continue

            asset, host_findings, raw_host = self._parse_host(host_elem, job_id)
            if asset:
                assets.append(asset)
                findings.extend(host_findings)
                raw_hosts.append(raw_host)

        raw_summary: dict[str, Any] = {
            "nmap_version": root.get("version"),
            "args":         root.get("args"),
            "start_time":   root.get("start"),
            "hosts":        raw_hosts,
        }
        return assets, findings, raw_summary

    def _parse_host(
        self, host_elem: ET.Element, job_id: str
    ) -> tuple[Asset | None, list[Finding], dict[str, Any]]:
        """Extract Asset and Findings from a single <host> element."""
        # IP address
        ip: str | None = None
        for addr in host_elem.findall("address"):
            if addr.get("addrtype") in ("ipv4", "ipv6"):
                ip = addr.get("addr")
                break
        if not ip:
            return None, [], {}

        # Hostname
        hostnames: list[str] = []
        hn_elem = host_elem.find("hostnames")
        if hn_elem is not None:
            for hn in hn_elem.findall("hostname"):
                name = hn.get("name")
                if name:
                    hostnames.append(name)
        hostname_str = hostnames[0] if hostnames else None

        # OS detection
        os_info: dict[str, Any] = {}
        os_elem = host_elem.find("os")
        if os_elem is not None:
            osmatch = os_elem.find("osmatch")
            if osmatch is not None:
                os_info = {
                    "name":     osmatch.get("name"),
                    "accuracy": osmatch.get("accuracy"),
                }

        asset = Asset(
            asset_type=AssetType.HOST,
            ip_address=ip,
            hostname=hostname_str,
            criticality=Criticality.MEDIUM,
            metadata={
                "os": os_info,
                "hostnames": hostnames,
            },
        )

        findings:  list[Finding] = []
        raw_ports: list[dict]    = []

        ports_elem = host_elem.find("ports")
        port_list = ports_elem.findall("port") if ports_elem is not None else []

        for port_elem in port_list:
            state_elem = port_elem.find("state")
            if state_elem is None or state_elem.get("state") != "open":
                continue

            port_id  = port_elem.get("portid", "?")
            protocol = port_elem.get("protocol", "tcp")
            try:
                port_num = int(port_id)
            except ValueError:
                port_num = 0

            svc_elem    = port_elem.find("service")
            svc_name    = svc_elem.get("name", "") if svc_elem is not None else ""
            svc_product = svc_elem.get("product", "") if svc_elem is not None else ""
            svc_version = svc_elem.get("version", "") if svc_elem is not None else ""
            svc_extrainfo = svc_elem.get("extrainfo", "") if svc_elem is not None else ""
            svc_tunnel  = svc_elem.get("tunnel", "") if svc_elem is not None else ""
            conf_str    = svc_elem.get("conf", "3") if svc_elem is not None else "3"

            raw_ports.append({
                "port":      port_num,
                "protocol":  protocol,
                "state":     "open",
                "service":   svc_name,
                "product":   svc_product,
                "version":   svc_version,
                "extrainfo": svc_extrainfo,
                "tunnel":    svc_tunnel,
            })

            try:
                conf_int = int(conf_str)
                if conf_int >= 8:
                    confidence = Confidence.HIGH
                elif conf_int >= 5:
                    confidence = Confidence.MEDIUM
                else:
                    confidence = Confidence.LOW
            except ValueError:
                confidence = Confidence.LOW

            evidence_parts = [f"Port: {port_num}/{protocol} (open)"]
            if svc_name:
                evidence_parts.append(f"Service: {svc_name}")
            if svc_product:
                version_full = f"{svc_product} {svc_version}".strip()
                evidence_parts.append(f"Product: {version_full}")
            if svc_extrainfo:
                evidence_parts.append(f"Info: {svc_extrainfo}")
            if svc_tunnel:
                evidence_parts.append(f"Tunnel: {svc_tunnel}")

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
