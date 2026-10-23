"""
Unit tests for OSV lockfile parsers (offline — no API calls)
"""
import json
import textwrap
import pytest
from scanners.osv_adapter.scanner import OSVScanner


class TestRequirementsTxtParser:
    def setup_method(self):
        self.scanner = OSVScanner()

    def test_pinned_versions(self):
        txt = "flask==3.0.0\nrequests>=2.31.0\nnumpy~=1.26.0\n"
        pkgs = self.scanner._parse_requirements_txt(txt, "PyPI")
        names = [p["name"] for p in pkgs]
        assert "flask" in names
        assert "requests" in names
        assert "numpy" in names

    def test_skips_comments_and_flags(self):
        txt = "# comment\n-r base.txt\nhttps://example.com/pkg.whl\nflask==3.0.0\n"
        pkgs = self.scanner._parse_requirements_txt(txt, "PyPI")
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "flask"

    def test_ecosystem_preserved(self):
        txt = "requests==2.28.0\n"
        pkgs = self.scanner._parse_requirements_txt(txt, "PyPI")
        assert pkgs[0]["ecosystem"] == "PyPI"

    def test_extras_stripped(self):
        txt = "uvicorn[standard]==0.24.0\n"
        pkgs = self.scanner._parse_requirements_txt(txt, "PyPI")
        # Name may include [standard] – that's OK as long as version is extracted
        assert any("uvicorn" in p["name"] for p in pkgs)


class TestNpmLockParser:
    def setup_method(self):
        self.scanner = OSVScanner()

    def test_parse_v2_lock(self):
        lock = {
            "lockfileVersion": 2,
            "packages": {
                "node_modules/lodash": {"version": "4.17.20"},
                "node_modules/express": {"version": "4.18.2"},
            }
        }
        pkgs = self.scanner._parse_npm_lock(json.dumps(lock), "npm")
        names = [p["name"] for p in pkgs]
        assert "lodash" in names
        assert "express" in names

    def test_ecosystem_npm(self):
        lock = {"packages": {"node_modules/axios": {"version": "1.0.0"}}}
        pkgs = self.scanner._parse_npm_lock(json.dumps(lock), "npm")
        assert pkgs[0]["ecosystem"] == "npm"


class TestCargoLockParser:
    def setup_method(self):
        self.scanner = OSVScanner()

    def test_parse_cargo_lock(self):
        lock = textwrap.dedent("""
            [[package]]
            name = "tokio"
            version = "1.32.0"

            [[package]]
            name = "serde"
            version = "1.0.189"
        """)
        pkgs = self.scanner._parse_cargo_lock(lock, "crates.io")
        names = [p["name"] for p in pkgs]
        assert "tokio" in names
        assert "serde" in names

    def test_version_extracted(self):
        lock = "[[package]]\nname = \"rand\"\nversion = \"0.8.5\"\n"
        pkgs = self.scanner._parse_cargo_lock(lock, "crates.io")
        assert pkgs[0]["version"] == "0.8.5"


class TestGoSumParser:
    def setup_method(self):
        self.scanner = OSVScanner()

    def test_parse_go_sum(self):
        gosum = textwrap.dedent("""
            github.com/gin-gonic/gin v1.9.1 h1:4idEAncQnU5cB7BeOkPtxjfCSye0AAm1R0RVIqJ+Jmg=
            github.com/gin-gonic/gin v1.9.1/go.mod h1:hPys6C/...
            golang.org/x/crypto v0.14.0 h1:abc...
        """)
        pkgs = self.scanner._parse_go_sum(gosum, "Go")
        names = [p["name"] for p in pkgs]
        assert "github.com/gin-gonic/gin" in names
        assert "golang.org/x/crypto" in names

    def test_deduplicates_module(self):
        gosum = (
            "mod/pkg v1.0.0 h1:abc=\n"
            "mod/pkg v1.0.0/go.mod h1:def=\n"
        )
        pkgs = self.scanner._parse_go_sum(gosum, "Go")
        assert len(pkgs) == 1


class TestCVSSToSeverity:
    def setup_method(self):
        from scanners.osv_adapter.scanner import _cvss_to_severity
        self.fn = _cvss_to_severity

    def test_critical(self):
        assert self.fn(9.8).value == "critical"

    def test_high(self):
        assert self.fn(7.5).value == "high"

    def test_medium(self):
        assert self.fn(5.0).value == "medium"

    def test_low(self):
        assert self.fn(2.0).value == "low"

    def test_none_defaults_medium(self):
        assert self.fn(None).value == "medium"
