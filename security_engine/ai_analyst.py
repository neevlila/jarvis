"""
J.A.R.V.I.S. Security Assessment Engine — AI Security Analyst
===============================================================
Provides source-grounded vulnerability interpretation, technical
and executive summaries, false-positive rationale, and contextual
remediation advice.

Security & Safety Principles (Strictly Enforced)
------------------------------------------------
1. Grounding: All conclusions strictly refer to the scanner facts provided.
   The AI must NEVER invent CVEs, CVSS scores, affected versions, or exploitability.
2. Prompt Isolation: Scanner output and evidence are treated as untrusted text.
   They are placed within delimited blocks to prevent prompt injection.
3. Clear Distinction: Output clearly separates verified facts from analytical
   interpretation.
4. Fallback: If no LLM provider is available or configured, deterministic
   structured summaries are returned without failing.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import Finding, ScanJob, Severity

logger = logging.getLogger("jarvis.security.ai_analyst")


class AISecurityAnalyst:
    """Provides grounded AI analysis for security findings and scan jobs."""

    @classmethod
    def explain_finding(cls, finding: Finding, asset_criticality: str = "medium") -> dict[str, Any]:
        """
        Generate an evidence-grounded explanation of a finding,
        including realistic impact, false-positive possibilities, and next steps.
        """
        prompt = (
            "You are the J.A.R.V.I.S. AI Security Analyst. "
            "Analyze the following scanner finding strictly based on the provided evidence. "
            "Do NOT invent CVEs, exploit details, or hypothetical vulnerabilities not in evidence.\n\n"
            "=== UNTRUSTED SCANNER EVIDENCE START ===\n"
            f"Title: {finding.title}\n"
            f"Scanner: {finding.scanner}\n"
            f"Detection Method: {finding.detection_method}\n"
            f"Vulnerability/Advisory ID: {finding.vuln_id or 'None'}\n"
            f"Affected Component: {finding.affected_component}\n"
            f"Reported Severity: {finding.severity.value}\n"
            f"Detection Confidence: {finding.confidence.value}\n"
            f"Evidence: {finding.evidence}\n"
            f"Asset Criticality Context: {asset_criticality}\n"
            "=== UNTRUSTED SCANNER EVIDENCE END ===\n\n"
            "Provide a JSON response with the following keys:\n"
            "- 'executive_summary': A concise 1-2 sentence summary for stakeholders.\n"
            "- 'technical_analysis': Grounded technical breakdown of what was actually detected.\n"
            "- 'uncertainty_and_fp_risk': Potential reasons for false positives or detection uncertainty.\n"
            "- 'prioritized_action': Specific, verifiable steps to remediate or confirm the issue."
        )

        try:
            from providers.provider_manager import ProviderManager
            response_text = ProviderManager.chat(
                prompt=prompt,
                system_prompt="You are a senior Application Security Analyst. Always return valid JSON only."
            )
            import json
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
        except Exception as exc:
            logger.debug("AI Provider unavailable or parse error (%s). Falling back to deterministic summary.", exc)
            return cls._deterministic_finding_explanation(finding, asset_criticality)

    @classmethod
    def generate_executive_summary(cls, job: ScanJob, findings: list[Finding]) -> dict[str, Any]:
        """Generate an executive-level assessment overview."""
        sev_counts: dict[str, int] = {s.value: 0 for s in Severity}
        for f in findings:
            sev_counts[f.severity.value] += 1

        top_findings = sorted(findings, key=lambda x: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1, "informational": 0}.get(x.severity.value, 0)
        ), reverse=True)[:5]

        top_titles = [f"{f.severity.value.upper()}: {f.title} ({f.affected_component})" for f in top_findings]

        return {
            "target": job.target,
            "profile": job.profile.value,
            "scan_id": job.id,
            "status": job.status.value,
            "total_findings": len(findings),
            "severity_breakdown": sev_counts,
            "primary_concerns": top_titles,
            "assessment_coverage_note": (
                f"Scan conducted using {', '.join(job.scanners) or 'registered adapters'} "
                f"under profile '{job.profile.value}'. Results reflect observed evidence at scan time."
            )
        }

    @classmethod
    def _deterministic_finding_explanation(cls, finding: Finding, asset_criticality: str) -> dict[str, str]:
        """Safe deterministic fallback when LLM is offline or not configured."""
        is_low_conf = finding.confidence.value in ("low", "uncertain")
        fp_note = (
            "Service or version banners can be misleading, customized, or backported by OS distributions. "
            "Verification via local package audit or targeted inspection is recommended."
            if is_low_conf else
            "Detection is backed by specific version matching or observed service behavior. "
            "Verify whether compensating controls or firewall rules mitigate external access."
        )

        return {
            "executive_summary": (
                f"A {finding.severity.value.upper()} finding was observed on {finding.affected_component} "
                f"via {finding.scanner}. Contextual priority reflects {asset_criticality} asset criticality."
            ),
            "technical_analysis": (
                f"Scanner evidence indicates: {finding.evidence or 'Observation recorded during scan.'} "
                f"Vulnerability ID: {finding.vuln_id or 'N/A'}."
            ),
            "uncertainty_and_fp_risk": fp_note,
            "prioritized_action": finding.remediation or "Investigate affected component and apply vendor updates."
        }
