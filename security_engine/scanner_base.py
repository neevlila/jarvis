"""
J.A.R.V.I.S. Security Assessment Engine — Scanner Base Contract
===============================================================
All scanner adapters must implement ScannerBase.
The registry exposes availability, capabilities, and health.
"""

from __future__ import annotations

import abc
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .models import ScanJob, Finding, Asset, ScanProfile

logger = logging.getLogger("jarvis.security.scanners")


# ─────────────────────────────────────────────────────────────────────────────
# Scanner result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScanResult:
    """Normalised output from a single scanner adapter."""
    scanner_name:   str
    scan_job_id:    str
    success:        bool
    assets:         list[Asset]           = field(default_factory=list)
    findings:       list[Finding]         = field(default_factory=list)
    raw_output:     dict[str, Any]        = field(default_factory=dict)
    error:          str | None            = None
    warnings:       list[str]             = field(default_factory=list)
    duration_s:     float                 = 0.0
    scanner_version: str | None           = None


# ─────────────────────────────────────────────────────────────────────────────
# Health record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScannerHealth:
    name:            str
    available:       bool
    version:         str | None     = None
    last_check:      float          = field(default_factory=time.time)
    last_error:      str | None     = None
    supported_profiles: list[str]  = field(default_factory=list)
    execution_location: str        = "cloud"  # "cloud" | "local_agent" | "worker"
    resource_note:   str           = ""
    config_errors:   list[str]     = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name":                self.name,
            "available":           self.available,
            "version":             self.version,
            "last_check":          self.last_check,
            "last_error":          self.last_error,
            "supported_profiles":  self.supported_profiles,
            "execution_location":  self.execution_location,
            "resource_note":       self.resource_note,
            "config_errors":       self.config_errors,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────

class ScannerBase(abc.ABC):
    """
    Every scanner adapter must implement this interface.

    Implementations MUST:
    - Check availability before scanning and return ScannerHealth.available=False
      if the tool is not installed or not reachable.
    - Construct subprocess commands without shell interpolation.
    - Treat all tool output as untrusted — parse and validate before use.
    - Respect the timeout_s parameter.
    - Never expose a general-purpose shell interface.
    - Return partial results on timeout rather than raising unhandled exceptions.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Short identifier, e.g. 'nmap', 'osv', 'zap'."""

    @abc.abstractmethod
    def health_check(self) -> ScannerHealth:
        """Return current availability and configuration status."""

    @abc.abstractmethod
    def run(self, job: ScanJob, timeout_s: int = 300) -> ScanResult:
        """
        Execute the scan described by *job*.
        Must return a ScanResult even on failure — never raise.
        """

    @abc.abstractmethod
    def supported_profiles(self) -> list[ScanProfile]:
        """Profiles this scanner can service."""


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

class ScannerRegistry:
    """
    Holds all registered scanner adapters.
    Provides health aggregation and profile→scanner routing.
    """

    def __init__(self) -> None:
        self._scanners: dict[str, ScannerBase] = {}

    def register(self, scanner: ScannerBase) -> None:
        self._scanners[scanner.name] = scanner
        logger.info("Scanner registered: %s", scanner.name)

    def get(self, name: str) -> ScannerBase | None:
        return self._scanners.get(name)

    def all_scanners(self) -> list[ScannerBase]:
        return list(self._scanners.values())

    def health_all(self) -> list[dict]:
        results = []
        for scanner in self._scanners.values():
            try:
                h = scanner.health_check()
            except Exception as exc:
                h = ScannerHealth(
                    name=scanner.name,
                    available=False,
                    last_error=str(exc),
                )
            results.append(h.to_dict())
        return results

    def scanners_for_profile(self, profile: ScanProfile) -> list[ScannerBase]:
        return [
            s for s in self._scanners.values()
            if profile in s.supported_profiles()
        ]
