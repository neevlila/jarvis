"""
Risk & Safety Engine for J.A.R.V.I.S.

Mandatory safety evaluation layer for all system and desktop operations:
- Assesses risk level (LOW, MEDIUM, HIGH, CRITICAL) based on action, target, context, and permissions.
- Enforces strict execution safety policies.
- Protects against destructive operations (file deletion, database drops, system shutdown).
- Blocks critical actions by default unless explicit override authorization is provided.
"""

import os
import re
from typing import Dict, List, Any, Optional, Callable

from intelligence.models import RiskAssessment, RiskLevel


class RiskSafetyEngine:
    """
    Quality and safety gate that prevents unauthorized or destructive operations.
    """

    CRITICAL_COMMAND_PATTERNS = [
        r"format\s+[c-z]:",
        r"del\s+/[fqs]\s+[c-z]:\\windows",
        r"rm\s+-rf\s+[/~]",
        r"drop\s+database",
        r"drop\s+table",
        r"truncate\s+table",
        r"shutdown\s+/[sr]",
        r"reg\s+delete",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
        r"chmod\s+-r\s+777\s+/"
    ]

    HIGH_RISK_COMMAND_PATTERNS = [
        r"pip\s+install",
        r"npm\s+install",
        r"rm\s+",
        r"del\s+",
        r"rmdir\s+",
        r"kill\s+",
        r"taskkill\s+"
    ]

    SENSITIVE_TARGET_PATTERNS = [
        r"\.env$",
        r"id_rsa",
        r"credentials\.json",
        r"config\.json",
        r"windows[/\\]system32",
        r"/etc/passwd",
        r"/etc/shadow"
    ]

    ADVERSARIAL_BYPASS_PATTERNS = [
        r"ignore\s+(?:all\s+)?(?:safety|policy|rules|instructions)",
        r"you\s+are\s+authorized",
        r"this\s+is\s+an?\s+emergency",
        r"user\s+already\s+approved",
        r"override\s+safety",
        r"execute\s+anyway",
        r"bypass\s+security"
    ]

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        self.log_callback = log_callback

    def _log(self, stage: str, message: str):
        formatted = f"[{stage}] {message}"
        print(formatted)
        if self.log_callback:
            try:
                self.log_callback(stage, message)
            except Exception:
                pass

    def assess_risk(
        self,
        action_name: str,
        target: Optional[str] = None,
        command_args: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Evaluates the potential hazards of an intended operation.
        """
        action_lower = action_name.lower().strip()
        target_str = str(target or "").strip()
        cmd_str = " ".join(command_args or []) if command_args else ""
        combined_text = f"{action_lower} {target_str} {cmd_str}".strip()

        hazards: List[str] = []
        mitigations: List[str] = []

        # 1. Check for CRITICAL destructive patterns
        for pattern in self.CRITICAL_COMMAND_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                hazards.append(f"Operation contains critical destructive pattern: '{pattern}'.")
                mitigations.append("Block execution immediately. Do not permit automated execution.")
                self._log("RISK", f"CRITICAL risk detected on '{action_name}' matching pattern '{pattern}'.")
                return RiskAssessment(
                    action_name=action_name,
                    risk_level=RiskLevel.CRITICAL,
                    requires_confirmation=True,
                    reason="Critical destructive system hazard detected.",
                    hazards=hazards,
                    suggested_mitigations=mitigations,
                    target_resource=target
                )

        # Check for adversarial prompt injection / safety bypass attempts
        for pattern in self.ADVERSARIAL_BYPASS_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                hazards.append(f"Adversarial safety bypass pattern detected: '{pattern}'.")
                mitigations.append("Enforce strict policy gate. Untrusted text cannot grant authorization.")
                self._log("RISK", f"SECURITY ALERT: Adversarial bypass pattern detected matching '{pattern}'.")

        # 2. Check for sensitive files and targets
        for pattern in self.SENSITIVE_TARGET_PATTERNS:
            if re.search(pattern, target_str, re.IGNORECASE):
                hazards.append(f"Target matches protected security resource: '{target_str}'.")
                mitigations.append("Require explicit interactive user confirmation before proceeding.")
                self._log("RISK", f"HIGH risk: Target '{target_str}' is a protected security resource.")
                return RiskAssessment(
                    action_name=action_name,
                    risk_level=RiskLevel.HIGH,
                    requires_confirmation=True,
                    reason="Access to sensitive security asset requested.",
                    hazards=hazards,
                    suggested_mitigations=mitigations,
                    target_resource=target
                )

        # 3. Check for HIGH risk action patterns
        if any(kw in action_lower for kw in ["delete", "remove", "drop", "terminate", "kill", "format", "purge"]):
            hazards.append(f"Action '{action_name}' is potentially destructive or irreversible.")
            mitigations.append("Require user confirmation with resource preview.")
            return RiskAssessment(
                action_name=action_name,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                reason="Destructive or irreversible modification requested.",
                hazards=hazards,
                suggested_mitigations=mitigations,
                target_resource=target
            )

        for pattern in self.HIGH_RISK_COMMAND_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                hazards.append(f"Command execution introduces external packages or process termination: '{pattern}'.")
                mitigations.append("Log execution context and verify environment safety.")
                return RiskAssessment(
                    action_name=action_name,
                    risk_level=RiskLevel.HIGH,
                    requires_confirmation=True,
                    reason="High impact environment modification requested.",
                    hazards=hazards,
                    suggested_mitigations=mitigations,
                    target_resource=target
                )

        # 4. Check for MEDIUM risk action patterns
        if any(kw in action_lower for kw in ["write", "modify", "edit", "save", "launch", "open_app", "send_email"]):
            return RiskAssessment(
                action_name=action_name,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=False,
                reason="Standard state-modifying operation.",
                hazards=["Local file or application state will be altered."],
                suggested_mitigations=["Verify file backups if modifying existing source files."],
                target_resource=target
            )

        # 5. Default LOW risk (read-only operations, queries, perception)
        return RiskAssessment(
            action_name=action_name,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            reason="Read-only or non-destructive observation operation.",
            hazards=[],
            suggested_mitigations=[],
            target_resource=target
        )

    def is_action_permitted(
        self,
        assessment: RiskAssessment,
        user_authorized: bool = False
    ) -> tuple[bool, str]:
        """
        Determines whether an action may proceed based on policy and user authorization.
        """
        if assessment.risk_level == RiskLevel.LOW:
            return True, "Action permitted automatically (LOW risk)."

        if assessment.risk_level == RiskLevel.MEDIUM:
            return True, "Action permitted with logging (MEDIUM risk)."

        if assessment.risk_level == RiskLevel.HIGH:
            if user_authorized:
                return True, "Action permitted via explicit user authorization (HIGH risk)."
            return False, f"Action BLOCKED: Requires explicit user confirmation. Hazards: {', '.join(assessment.hazards)}"

        if assessment.risk_level == RiskLevel.CRITICAL:
            if user_authorized:
                self._log("RISK", f"WARNING: Critical action forced by user authorization override: '{assessment.action_name}'")
                return True, "Action OVERRIDDEN by user authorization (CRITICAL risk)."
            return False, f"Action BLOCKED: Critical security policy violation. Hazards: {', '.join(assessment.hazards)}"

        return False, "Action denied by default safety rule."
