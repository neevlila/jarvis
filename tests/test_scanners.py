"""
Unit tests for Scanner Adapters health check and availability.
Verifies that all adapters (Nmap, Greenbone, OSV, ZAP) report available=True
and can be registered in ScannerRegistry.
"""
import pytest
from scanners.nmap_adapter import NmapScanner
from scanners.greenbone_adapter import GreenboneScanner
from scanners.osv_adapter import OSVScanner
from scanners.zap_adapter import ZAPScanner
from security_engine.scanner_base import ScannerRegistry
from security_engine.models import ScanProfile


def test_nmap_scanner_health():
    scanner = NmapScanner()
    health = scanner.health_check()
    assert health.available is True
    assert health.name == "nmap"
    assert "asset_discovery" in health.supported_profiles
    assert "service_inventory" in health.supported_profiles


def test_greenbone_scanner_health():
    scanner = GreenboneScanner()
    health = scanner.health_check()
    assert health.available is True
    assert health.name == "greenbone"
    assert "infrastructure_assessment" in health.supported_profiles


def test_osv_scanner_health():
    scanner = OSVScanner()
    health = scanner.health_check()
    assert health.available is True
    assert health.name == "osv"
    assert "dependency_audit" in health.supported_profiles


def test_zap_scanner_health():
    scanner = ZAPScanner()
    health = scanner.health_check()
    assert health.available is True
    assert health.name == "zap"
    assert "web_baseline" in health.supported_profiles


def test_scanner_registry_all_online():
    registry = ScannerRegistry()
    registry.register(NmapScanner())
    registry.register(GreenboneScanner())
    registry.register(OSVScanner())
    registry.register(ZAPScanner())

    health_list = registry.health_all()
    assert len(health_list) == 4
    for h in health_list:
        assert h["available"] is True, f"Scanner {h['name']} is unexpectedly OFFLINE: {h}"
