"""
Unit tests for security_engine.store (SecurityStore)
Tests cover: CRUD, deduplication, find_or_create_asset, overview, findings_summary
"""
import os
import tempfile
import time
import pytest

from security_engine.store import SecurityStore
from security_engine.models import (
    Asset, AssetType, Criticality,
    AuthorizedScope, ScanProfile,
    ScanJob, ScanStatus,
    Finding, Severity, Confidence, VerificationStatus,
    RemediationRecord, RemediationStatus,
)


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield SecurityStore(data_dir=tmpdir)


class TestAssetCRUD:
    def test_save_and_get(self, store):
        a = Asset(display_name="host1", ip_address="1.2.3.4", asset_type=AssetType.HOST)
        store.save_asset(a)
        got = store.get_asset(a.id)
        assert got is not None
        assert got.display_name == "host1"
        assert got.ip_address == "1.2.3.4"

    def test_get_missing_returns_none(self, store):
        assert store.get_asset("nonexistent") is None

    def test_list_assets(self, store):
        store.save_asset(Asset(display_name="a1", asset_type=AssetType.HOST))
        store.save_asset(Asset(display_name="a2", asset_type=AssetType.WEB_APP))
        all_assets = store.list_assets()
        assert len(all_assets) == 2

    def test_list_assets_filter_by_type(self, store):
        store.save_asset(Asset(display_name="a1", asset_type=AssetType.HOST))
        store.save_asset(Asset(display_name="a2", asset_type=AssetType.WEB_APP))
        hosts = store.list_assets(asset_type=AssetType.HOST)
        assert len(hosts) == 1
        assert hosts[0].display_name == "a1"

    def test_delete_asset(self, store):
        a = Asset(display_name="to-delete")
        store.save_asset(a)
        assert store.delete_asset(a.id)
        assert store.get_asset(a.id) is None

    def test_find_or_create_deduplicates_by_ip(self, store):
        a1 = store.find_or_create_asset("10.0.0.1", None, "host1", AssetType.HOST)
        a2 = store.find_or_create_asset("10.0.0.1", "host.local", "host1-again", AssetType.HOST)
        assert a1.id == a2.id
        # Hostname should be backfilled
        assert store.get_asset(a1.id).hostname == "host.local"

    def test_find_or_create_deduplicates_by_hostname(self, store):
        a1 = store.find_or_create_asset(None, "srv.local", "srv", AssetType.HOST)
        a2 = store.find_or_create_asset("172.16.0.5", "srv.local", "srv2", AssetType.HOST)
        assert a1.id == a2.id


class TestScanJobCRUD:
    def test_save_and_get(self, store):
        j = ScanJob(target="example.com", profile=ScanProfile.DEPENDENCY_AUDIT)
        store.save_scan_job(j)
        got = store.get_scan_job(j.id)
        assert got is not None
        assert got.target == "example.com"

    def test_update_status_running(self, store):
        j = ScanJob(target="x", profile=ScanProfile.DEPENDENCY_AUDIT)
        store.save_scan_job(j)
        updated = store.update_job_status(j.id, ScanStatus.RUNNING, 10, "Starting…")
        assert updated.status == ScanStatus.RUNNING
        assert updated.start_time is not None

    def test_update_status_completed_sets_end_time(self, store):
        j = ScanJob(target="x", profile=ScanProfile.DEPENDENCY_AUDIT)
        store.save_scan_job(j)
        store.update_job_status(j.id, ScanStatus.RUNNING)
        updated = store.update_job_status(j.id, ScanStatus.COMPLETED, 100, "Done")
        assert updated.end_time is not None

    def test_list_scan_jobs_by_status(self, store):
        j1 = ScanJob(target="a", profile=ScanProfile.DEPENDENCY_AUDIT, status=ScanStatus.COMPLETED)
        j2 = ScanJob(target="b", profile=ScanProfile.DEPENDENCY_AUDIT, status=ScanStatus.FAILED)
        store.save_scan_job(j1)
        store.save_scan_job(j2)
        completed = store.list_scan_jobs(status=ScanStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].target == "a"


class TestFindingCRUD:
    def test_save_and_get(self, store):
        f = Finding(title="Open port", description="Port 22 open",
                    severity=Severity.LOW, scanner="nmap")
        store.save_finding(f)
        got = store.get_finding(f.id)
        assert got is not None
        assert got.title == "Open port"

    def test_list_findings_by_severity(self, store):
        store.save_finding(Finding(title="c", description="d", severity=Severity.CRITICAL))
        store.save_finding(Finding(title="l", description="d", severity=Severity.LOW))
        crits = store.list_findings(severity=Severity.CRITICAL)
        assert len(crits) == 1
        assert crits[0].severity == Severity.CRITICAL

    def test_false_positives_excluded_by_default(self, store):
        f = Finding(title="fp", description="d", severity=Severity.HIGH)
        f.false_positive = True
        store.save_finding(f)
        results = store.list_findings()
        assert all(not r.false_positive for r in results)

    def test_false_positives_included_when_requested(self, store):
        f = Finding(title="fp", description="d", severity=Severity.HIGH)
        f.false_positive = True
        store.save_finding(f)
        results = store.list_findings(include_false_positives=True)
        assert any(r.false_positive for r in results)

    def test_findings_summary(self, store):
        store.save_finding(Finding(title="c", description="d", severity=Severity.CRITICAL))
        store.save_finding(Finding(title="h", description="d", severity=Severity.HIGH))
        store.save_finding(Finding(title="m", description="d", severity=Severity.MEDIUM))
        summary = store.findings_summary()
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["high"] == 1
        assert summary["total"] == 3


class TestRemediationCRUD:
    def test_save_and_get(self, store):
        r = RemediationRecord(finding_id="fid", recommended_action="Patch it.")
        store.save_remediation(r)
        got = store.get_remediation(r.id)
        assert got is not None
        assert got.finding_id == "fid"

    def test_get_for_finding(self, store):
        r = RemediationRecord(finding_id="fid2")
        store.save_remediation(r)
        got = store.get_remediation_for_finding("fid2")
        assert got is not None
        assert got.id == r.id

    def test_get_for_missing_finding_returns_none(self, store):
        assert store.get_remediation_for_finding("no-such-finding") is None


class TestOverview:
    def test_overview_structure(self, store):
        ov = store.overview()
        assert "assets_total" in ov
        assert "scans_total" in ov
        assert "findings" in ov
        assert "by_severity" in ov["findings"]

    def test_overview_counts(self, store):
        store.save_asset(Asset(display_name="h"))
        j = ScanJob(target="x", profile=ScanProfile.DEPENDENCY_AUDIT,
                    status=ScanStatus.RUNNING)
        store.save_scan_job(j)
        ov = store.overview()
        assert ov["assets_total"] == 1
        assert ov["scans_running"] == 1


class TestPersistence:
    def test_data_survives_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            s1 = SecurityStore(data_dir=tmpdir)
            a = Asset(display_name="persistent-host", ip_address="9.9.9.9")
            s1.save_asset(a)

            s2 = SecurityStore(data_dir=tmpdir)
            got = s2.get_asset(a.id)
            assert got is not None
            assert got.ip_address == "9.9.9.9"
