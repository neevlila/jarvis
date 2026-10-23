"""
J.A.R.V.I.S. Security Assessment Engine — Authorization & Scope Enforcement
============================================================================
Server-side enforcement of:
  - Target allowlisting against authorized scopes
  - Profile permissioning
  - Private-range protection
  - SSRF prevention (cloud APIs must not scan internal infrastructure)

All validation happens in Python before any scanner command is constructed.
"""

from __future__ import annotations

import ipaddress
import re
import logging
from dataclasses import dataclass
from typing import Tuple

from .models import AuthorizedScope, ScanProfile

logger = logging.getLogger("jarvis.security.authz")


# ─────────────────────────────────────────────────────────────────────────────
# Private / reserved ranges that cloud routes must NEVER scan
# (local agent may scan its own LAN when explicitly scoped)
# ─────────────────────────────────────────────────────────────────────────────

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),     # link-local
    ipaddress.ip_network("100.64.0.0/10"),       # shared address space
    ipaddress.ip_network("::1/128"),             # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),            # IPv6 ULA
]

_LOCALHOST_PATTERNS = re.compile(
    r"^(localhost|local|127\.\d+\.\d+\.\d+|::1)$", re.IGNORECASE
)

# Scan profiles that the cloud API is permitted to initiate
_CLOUD_ALLOWED_PROFILES = {
    ScanProfile.DEPENDENCY_AUDIT,
    ScanProfile.WEB_BASELINE,
}

# Scan profiles that require the local agent
_AGENT_REQUIRED_PROFILES = {
    ScanProfile.ASSET_DISCOVERY,
    ScanProfile.SERVICE_INVENTORY,
    ScanProfile.INFRASTRUCTURE_ASSESSMENT,
    ScanProfile.COMPREHENSIVE,
}


# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuthorizationResult:
    allowed:    bool
    reason:     str
    requires_agent: bool = False

    def __bool__(self) -> bool:
        return self.allowed


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_private_ip(addr: str) -> bool:
    """Return True if addr resolves to a private/reserved address."""
    try:
        ip = ipaddress.ip_address(addr)
        return any(ip in net for net in _PRIVATE_RANGES)
    except ValueError:
        return False


def _is_localhost(addr: str) -> bool:
    return bool(_LOCALHOST_PATTERNS.match(addr.strip()))


def _extract_hostname_or_ip(target: str) -> str:
    """Strip scheme and path from a target string, return the host part."""
    target = target.strip()
    # Remove scheme
    if "://" in target:
        target = target.split("://", 1)[1]
    # Remove path
    target = target.split("/")[0]
    # Remove port
    if ":" in target and not target.startswith("["):
        target = target.rsplit(":", 1)[0]
    return target


def _target_in_scope(target: str, scope: AuthorizedScope) -> bool:
    """
    Check whether target is covered by at least one entry in scope.targets.
    Supports exact match, URL normalization, host matching, wildcard prefix (*.example.com), and CIDR notation.
    """
    target_clean = target.strip()
    host = _extract_hostname_or_ip(target_clean)
    for allowed in scope.targets:
        allowed_clean = allowed.strip()

        # 1. Exact raw match
        if allowed_clean.lower() == target_clean.lower():
            return True

        # 2. Match without trailing slash
        if allowed_clean.rstrip("/").lower() == target_clean.rstrip("/").lower():
            return True

        # 3. Match extracted hostname or IP
        allowed_host = _extract_hostname_or_ip(allowed_clean)
        if allowed_host and host and allowed_host.lower() == host.lower():
            return True

        # 4. Wildcard hostname: *.example.com matches sub.example.com
        if allowed_host.startswith("*."):
            suffix = allowed_host[2:].lower()
            if host.lower().endswith("." + suffix) or host.lower() == suffix:
                return True

        # 5. CIDR block (use raw allowed_clean to preserve /prefix)
        try:
            network = ipaddress.ip_network(allowed_clean, strict=False)
            ip = ipaddress.ip_address(host)
            if ip in network:
                return True
        except ValueError:
            pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def authorize_scan(
    target: str,
    profile: ScanProfile,
    scope: AuthorizedScope,
    from_cloud: bool = True,
) -> AuthorizationResult:
    """
    Perform server-side authorization for a proposed scan.

    Parameters
    ----------
    target      : The user-supplied scan target (host / IP / URL).
    profile     : The requested scan profile.
    scope       : The authorized scope record that must cover this target.
    from_cloud  : True when the request originates from the cloud API.
                  Private-range targets are blocked when from_cloud=True.

    Returns
    -------
    AuthorizationResult with allowed=True only when every check passes.
    """
    if not target or not target.strip():
        return AuthorizationResult(False, "Target must not be empty.")

    if not scope.is_valid():
        return AuthorizationResult(False, "The authorization scope has expired or is invalid.")

    host = _extract_hostname_or_ip(target)

    # Block localhost
    if _is_localhost(host):
        return AuthorizationResult(
            False,
            "Localhost targets are not permitted."
        )

    # Cloud API must not scan private/internal ranges (SSRF protection)
    if from_cloud and _is_private_ip(host):
        return AuthorizationResult(
            False,
            f"The cloud API cannot scan private/internal addresses ({host}). "
            "Use the local agent for LAN targets."
        )

    # Target must be within the authorized scope
    if not _target_in_scope(target, scope):
        return AuthorizationResult(
            False,
            f"Target '{target}' is not within the authorized scope. "
            f"Authorized targets: {scope.targets}"
        )

    # Profile must be permitted by the scope
    if profile not in scope.profiles_allowed:
        return AuthorizationResult(
            False,
            f"Profile '{profile.value}' is not permitted by this scope. "
            f"Allowed profiles: {[p.value for p in scope.profiles_allowed]}"
        )

    # Agent-only profiles must not be run from cloud
    if from_cloud and profile in _AGENT_REQUIRED_PROFILES:
        return AuthorizationResult(
            allowed=False,
            reason=(
                f"Profile '{profile.value}' requires the local Windows agent. "
                "Submit this scan through the agent endpoint."
            ),
            requires_agent=True,
        )

    logger.info(
        "Scan authorized: target=%s profile=%s scope=%s from_cloud=%s",
        target, profile.value, scope.id, from_cloud
    )
    return AuthorizationResult(
        allowed=True,
        reason="Authorized.",
        requires_agent=profile in _AGENT_REQUIRED_PROFILES,
    )


def validate_target_syntax(target: str) -> Tuple[bool, str]:
    """
    Lightweight structural validation of a target string before scope check.
    Returns (ok, error_message).
    """
    target = target.strip()
    if not target:
        return False, "Target is empty."
    if len(target) > 512:
        return False, "Target string too long (max 512 chars)."
    # Reject null bytes and shell metacharacters
    forbidden = set('\x00\n\r`$;|&<>{}()\\')
    bad = [c for c in target if c in forbidden]
    if bad:
        return False, f"Target contains forbidden characters: {bad}"
    return True, ""
