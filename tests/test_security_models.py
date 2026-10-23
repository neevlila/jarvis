"""
Unit tests for security_engine.models
Tests cover: serialization, deserialization, contextual_priority
"""
import time
import uuid
import pytest
from security_engine.models import (
    Asset, AssetType, Criticality,
    AuthorizedScope, ScanProfile,
    ScanJob, ScanStatus,
    Finding, Severity, Confidence, VerificationStatus,
    RemediationRecord, RemediationStatus,
)


class TestAsset:
    def test_round_trip(self):
        a = Asset(
            display_name="test-host",
            asset_type=AssetType.HOST,
            ip_address="192.168.1.1",
            hostname="test.local",
        )
        d = a.to_dict()
        b = Asset.from_dict(d)
        assert b.id == a.id
        assert b.display_name == "test-host"
        assert b.asset_type == AssetType.HOST
        assert b.ip_address == "192.168.1.1"

    def test_default_id_is_uuid(self):
        a = Asset(display_name="x")
        assert uuid.UUID(a.id)

    def test_from_dict_defaults(self):
        a = Asset.from_dict({"display_name": "bare"})
        assert a.asset_type == AssetType.UNKNOWN
        assert a.criticality == Criticality.MEDIUM


class TestAuthorizedScope:
    def test_valid_scope(self):
        scope = AuthorizedScope(
            targets=["192.168.1.0/24"],
            profiles_allowed=[ScanProfile.ASSET_DISCOVERY],
            owner="alice",
            expires_at=time.time() + 3600,
        )
        assert scope.is_valid()

    def test_expired_scope(self):
        scope = AuthorizedScope(
            targets=["10.0.0.1"],
            profiles_allowed=[ScanProfile.SERVICE_INVENTORY],
            owner="bob",
            expires_at=time.time() - 1,
        )
        assert not scope.is_valid()

    def test_empty_targets_invalid(self):
        scope = AuthorizedScope(targets=[], profiles_allowed=[], owner="bob")
        assert not scope.is_valid()

    def test_round_trip(self):
        scope = AuthorizedScope(
            targets=["example.com"],
            profiles_allowed=[ScanProfile.DEPENDENCY_AUDIT],
            owner="carol",
        )
        d = scope.to_dict()
        scope2 = AuthorizedScope.from_dict(d)
        assert scope2.id == scope.id
        assert scope2.targets == ["example.com"]
        assert ScanProfile.DEPENDENCY_AUDIT in scope2.profiles_allowed


class TestScanJob:
    def test_round_trip(self):
        j = ScanJob(
            target="example.com",
            profile=ScanProfile.DEPENDENCY_AUDIT,
            status=ScanStatus.RUNNING,
        )
        j.start_time = time.time()
        d = j.to_dict()
        j2 = ScanJob.from_dict(d)
        assert j2.id == j.id
        assert j2.profile == ScanProfile.DEPENDENCY_AUDIT
        assert j2.status == ScanStatus.RUNNING

    def test_duration(self):
        j = ScanJob(target="x", profile=ScanProfile.ASSET_DISCOVERY)
        j.start_time = 1000.0
        j.end_time   = 1060.0
        assert j.duration_seconds() == 60.0

    def test_duration_none_if_not_complete(self):
        j = ScanJob(target="x", profile=ScanProfile.ASSET_DISCOVERY)
        j.start_time = time.time()
        assert j.duration_seconds() is None


class TestFinding:
    def test_round_trip(self):
        f = Finding(
            title="Open SSH port",
            description="Port 22 is open.",
            severity=Severity.INFORMATIONAL,
            confidence=Confidence.HIGH,
            scanner="nmap",
        )
        d = f.to_dict()
        f2 = Finding.from_dict(d)
        assert f2.id == f.id
        assert f2.severity == Severity.INFORMATIONAL
        assert f2.confidence == Confidence.HIGH

    @pytest.mark.parametrize("sev,conf,crit,expected_priority", [
        (Severity.CRITICAL, Confidence.CONFIRMED, Criticality.CRITICAL, "critical"),
        (Severity.HIGH,     Confidence.HIGH,      Criticality.HIGH,     "critical"),
        (Severity.MEDIUM,   Confidence.MEDIUM,    Criticality.MEDIUM,   "medium"),
        (Severity.LOW,      Confidence.LOW,       Criticality.LOW,      "informational"),
        (Severity.INFORMATIONAL, Confidence.UNCERTAIN, Criticality.LOW, "informational"),
    ])
    def test_contextual_priority(self, sev, conf, crit, expected_priority):
        f = Finding(title="t", description="d", severity=sev, confidence=conf)
        assert f.contextual_priority(crit) == expected_priority

    def test_false_positive_defaults_false(self):
        f = Finding(title="t", description="d")
        assert f.false_positive is False

    def test_cvss_fields_preserved(self):
        f = Finding(
            title="t", description="d",
            cvss_score=9.8, cvss_version="CVSS v3.1",
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        )
        d = f.to_dict()
        f2 = Finding.from_dict(d)
        assert f2.cvss_score == 9.8
        assert "3.1" in f2.cvss_version


class TestRemediationRecord:
    def test_round_trip(self):
        r = RemediationRecord(
            finding_id="abc",
            recommended_action="Upgrade the package.",
            status=RemediationStatus.IN_PROGRESS,
        )
        d = r.to_dict()
        r2 = RemediationRecord.from_dict(d)
        assert r2.id == r.id
        assert r2.status == RemediationStatus.IN_PROGRESS

    def test_default_status_open(self):
        r = RemediationRecord(finding_id="x")
        assert r.status == RemediationStatus.OPEN
