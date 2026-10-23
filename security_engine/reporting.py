"""
J.A.R.V.I.S. Security Assessment Engine — Report Generator
===========================================================
Produces HTML and CSV reports from scan results.
No external rendering dependencies — uses stdlib only.
"""

from __future__ import annotations

import csv
import io
import html
import time
from datetime import datetime, timezone

from .models import ScanJob, Finding, Asset, Severity
from .store import SecurityStore


def _ts(epoch: float | None) -> str:
    if not epoch:
        return "N/A"
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _sev_color(sev: str) -> str:
    return {
        "critical":      "#dc2626",
        "high":          "#ea580c",
        "medium":        "#d97706",
        "low":           "#2563eb",
        "informational": "#6b7280",
    }.get(sev, "#6b7280")


class ReportGenerator:
    """Generate HTML and CSV security assessment reports."""

    def __init__(self, store: SecurityStore) -> None:
        self._store = store

    # ── HTML report ───────────────────────────────────────────────────────────

    def html_report(self, job_id: str) -> str:
        job = self._store.get_scan_job(job_id)
        if not job:
            return "<h1>Scan job not found.</h1>"

        findings = self._store.list_findings(scan_job_id=job_id)
        assets   = [self._store.get_asset(aid) for aid in job.asset_ids]
        assets   = [a for a in assets if a]

        sev_counts = {s.value: 0 for s in Severity}
        for f in findings:
            sev_counts[f.severity.value] += 1

        rows = ""
        for f in findings:
            color = _sev_color(f.severity.value)
            rows += f"""
            <tr>
              <td><span style="color:{color};font-weight:600">{html.escape(f.severity.value.upper())}</span></td>
              <td>{html.escape(f.vuln_id or "–")}</td>
              <td>{html.escape(f.title)}</td>
              <td>{html.escape(f.affected_component)}</td>
              <td>{html.escape(f.scanner)}</td>
              <td>{html.escape(f.confidence.value)}</td>
              <td>{html.escape(f.verification.value.replace("_"," "))}</td>
              <td style="max-width:300px;word-break:break-word">{html.escape(f.remediation[:300])}</td>
            </tr>"""

        asset_rows = ""
        for a in assets:
            asset_rows += f"""
            <tr>
              <td>{html.escape(a.display_name)}</td>
              <td>{html.escape(a.asset_type.value)}</td>
              <td>{html.escape(a.ip_address or "–")}</td>
              <td>{html.escape(a.hostname or "–")}</td>
              <td>{html.escape(a.discovery_source)}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>J.A.R.V.I.S. Security Assessment Report</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px }}
  h1 {{ color:#38bdf8; }} h2 {{ color:#94a3b8; border-bottom:1px solid #1e293b; padding-bottom:8px }}
  .meta {{ background:#1e293b; border-radius:8px; padding:16px; margin-bottom:24px }}
  .meta span {{ color:#94a3b8; font-size:0.85em }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.8em; font-weight:600; margin:2px }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:32px; font-size:0.85em }}
  th {{ background:#1e293b; color:#94a3b8; padding:8px 12px; text-align:left }}
  td {{ padding:8px 12px; border-bottom:1px solid #1e293b }}
  tr:hover td {{ background:#1e293b40 }}
  .disclaimer {{ background:#1e3a5f; border-left:4px solid #38bdf8; padding:12px 16px; border-radius:0 6px 6px 0; font-size:0.85em; color:#94a3b8 }}
</style>
</head>
<body>
<h1>🛡️ J.A.R.V.I.S. Security Assessment Report</h1>
<div class="meta">
  <b>Job ID:</b> {html.escape(job.id)}<br>
  <b>Target:</b> {html.escape(job.target)}<br>
  <b>Profile:</b> {html.escape(job.profile.value.replace("_"," ").title())}<br>
  <b>Scanners:</b> {html.escape(", ".join(job.scanners))}<br>
  <b>Status:</b> {html.escape(job.status.value)}<br>
  <b>Started:</b> {_ts(job.start_time)} &nbsp;|&nbsp; <b>Completed:</b> {_ts(job.end_time)}<br>
  <b>Duration:</b> {f"{job.duration_seconds():.1f}s" if job.duration_seconds() else "N/A"}<br>
  <b>Initiated by:</b> {html.escape(job.initiated_by)}<br>
  <br>
  <b>Severity summary:</b>
  {"".join(f'<span class="badge" style="background:{_sev_color(s)}">{s.upper()}: {sev_counts[s]}</span>' for s in ["critical","high","medium","low","informational"])}
</div>

<div class="disclaimer">
  ⚠️ <b>Coverage disclaimer:</b> This report reflects findings from the scanners listed above
  at the time of scan. Results are not exhaustive. Version detection confidence may be low;
  verify manually before drawing definitive conclusions. This report covers only authorized targets
  within the defined scope. Do not rely solely on this report for compliance decisions.
</div>

<h2>Assets Discovered ({len(assets)})</h2>
<table>
  <tr><th>Display Name</th><th>Type</th><th>IP</th><th>Hostname</th><th>Discovered By</th></tr>
  {asset_rows or "<tr><td colspan='5'>No assets discovered.</td></tr>"}
</table>

<h2>Findings ({len(findings)})</h2>
<table>
  <tr><th>Severity</th><th>ID</th><th>Title</th><th>Affected Component</th>
      <th>Scanner</th><th>Confidence</th><th>Status</th><th>Remediation</th></tr>
  {rows or "<tr><td colspan='8'>No findings.</td></tr>"}
</table>

<p style="color:#475569;font-size:0.8em">
  Generated by J.A.R.V.I.S. Security Assessment Engine · {_ts(time.time())}
</p>
</body>
</html>"""

    # ── CSV report ────────────────────────────────────────────────────────────

    def csv_report(self, job_id: str) -> str:
        job = self._store.get_scan_job(job_id)
        if not job:
            return "error,Job not found"

        findings = self._store.list_findings(scan_job_id=job_id)

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([
            "Finding ID", "Severity", "Confidence", "Title",
            "Vuln ID", "Affected Component", "Scanner", "Detection Method",
            "CVSS Score", "CVSS Version", "CWE",
            "Evidence", "Remediation", "Verification Status",
            "First Seen", "Last Seen",
        ])
        for f in findings:
            w.writerow([
                f.id, f.severity.value, f.confidence.value, f.title,
                f.vuln_id or "", f.affected_component, f.scanner, f.detection_method,
                f.cvss_score or "", f.cvss_version or "", f.cwe_id or "",
                f.evidence[:500], f.remediation[:500], f.verification.value,
                _ts(f.first_seen), _ts(f.last_seen),
            ])
        return buf.getvalue()
