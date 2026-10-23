"""
Unit tests for security_engine.authorization
Tests cover: target syntax validation, SSRF protection, scope matching,
profile enforcement, localhost blocking, private range blocking.
"""
import time
import pytest
from security_engine.authorization import (
    authorize_scan, validate_target_syntax,
    _is_private_ip, _is_localhost, _extract_hostname_or_ip,
)
from security_engine.models import AuthorizedScope, ScanProfile


def _make_scope(
    targets: list[str],
    profiles: list[ScanProfile] | None = None,
    owner: str = "tester",
) -> AuthorizedScope:
    return AuthorizedScope(
        targets=targets,
        profiles_allowed=profiles or [ScanProfile.DEPENDENCY_AUDIT],
        owner=owner,
        expires_at=time.time() + 3600,
    )


class TestTargetSyntax:
    def test_empty_target_rejected(self):
        ok, err = validate_target_syntax("")
        assert not ok
        assert "empty" in err.lower()

    def test_normal_hostname_accepted(self):
        ok, err = validate_target_syntax("example.com")
        assert ok

    def test_ip_accepted(self):
        ok, err = validate_target_syntax("8.8.8.8")
        assert ok

    def test_null_byte_rejected(self):
        ok, err = validate_target_syntax("host\x00.com")
        assert not ok

    @pytest.mark.parametrize("char", ["|", "&", ";", "`", "$", "<", ">"])
    def test_shell_metacharacter_rejected(self, char):
        ok, err = validate_target_syntax(f"host{char}com")
        assert not ok

    def test_too_long_rejected(self):
        ok, err = validate_target_syntax("a" * 600)
        assert not ok


class TestPrivateIPDetection:
    @pytest.mark.parametrize("ip", [
        "10.0.0.1", "192.168.1.1", "172.16.0.1",
        "127.0.0.1", "169.254.1.1"
    ])
    def test_private_ips_detected(self, ip):
        assert _is_private_ip(ip)

    @pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
    def test_public_ips_not_private(self, ip):
        assert not _is_private_ip(ip)


class TestLocalhostDetection:
    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1"])
    def test_localhost_detected(self, host):
        assert _is_localhost(host)

    def test_regular_host_not_localhost(self):
        assert not _is_localhost("example.com")


class TestHostnameExtraction:
    def test_strips_scheme(self):
        assert _extract_hostname_or_ip("https://example.com/path") == "example.com"

    def test_strips_port(self):
        assert _extract_hostname_or_ip("example.com:8080") == "example.com"

    def test_plain_host(self):
        assert _extract_hostname_or_ip("example.com") == "example.com"

    def test_ip_with_scheme(self):
        assert _extract_hostname_or_ip("http://8.8.8.8/test") == "8.8.8.8"


class TestAuthorizeSccan:
    def test_authorized_dependency_scan(self):
        scope = _make_scope(["example.com"])
        result = authorize_scan("example.com", ScanProfile.DEPENDENCY_AUDIT, scope, from_cloud=True)
        assert result.allowed

    def test_target_not_in_scope_rejected(self):
        scope = _make_scope(["example.com"])
        result = authorize_scan("other.com", ScanProfile.DEPENDENCY_AUDIT, scope, from_cloud=True)
        assert not result.allowed
        assert "not within" in result.reason

    def test_private_ip_from_cloud_rejected(self):
        scope = _make_scope(
            ["192.168.1.0/24"],
            profiles=[ScanProfile.ASSET_DISCOVERY]
        )
        result = authorize_scan("192.168.1.10", ScanProfile.ASSET_DISCOVERY, scope, from_cloud=True)
        assert not result.allowed
        assert "private" in result.reason.lower() or "agent" in result.reason.lower()

    def test_agent_required_profile_from_cloud_rejected(self):
        scope = _make_scope(
            ["8.8.8.8"],
            profiles=[ScanProfile.ASSET_DISCOVERY]
        )
        result = authorize_scan("8.8.8.8", ScanProfile.ASSET_DISCOVERY, scope, from_cloud=True)
        assert not result.allowed
        assert result.requires_agent

    def test_profile_not_allowed_by_scope(self):
        scope = _make_scope(["example.com"], profiles=[ScanProfile.DEPENDENCY_AUDIT])
        result = authorize_scan("example.com", ScanProfile.WEB_BASELINE, scope, from_cloud=True)
        assert not result.allowed

    def test_expired_scope_rejected(self):
        scope = AuthorizedScope(
            targets=["example.com"],
            profiles_allowed=[ScanProfile.DEPENDENCY_AUDIT],
            owner="tester",
            expires_at=time.time() - 1,
        )
        result = authorize_scan("example.com", ScanProfile.DEPENDENCY_AUDIT, scope, from_cloud=True)
        assert not result.allowed

    def test_localhost_always_rejected(self):
        scope = _make_scope(["localhost"])
        result = authorize_scan("localhost", ScanProfile.DEPENDENCY_AUDIT, scope, from_cloud=True)
        assert not result.allowed

    def test_wildcard_scope_match(self):
        scope = _make_scope(
            ["*.example.com"],
            profiles=[ScanProfile.DEPENDENCY_AUDIT]
        )
        result = authorize_scan("sub.example.com", ScanProfile.DEPENDENCY_AUDIT, scope, from_cloud=True)
        assert result.allowed

    def test_cidr_scope_match(self):
        scope = _make_scope(
            ["8.8.8.0/24"],
            profiles=[ScanProfile.DEPENDENCY_AUDIT]
        )
        # CIDR check still passes auth (8.8.x.x is public)
        result = authorize_scan("8.8.8.8", ScanProfile.DEPENDENCY_AUDIT, scope, from_cloud=True)
        assert result.allowed

    def test_empty_target_rejected(self):
        scope = _make_scope(["example.com"])
        result = authorize_scan("", ScanProfile.DEPENDENCY_AUDIT, scope, from_cloud=True)
        assert not result.allowed
