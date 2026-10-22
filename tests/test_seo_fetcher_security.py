"""
Unit tests for SEO URL Fetcher, Syntax Validation & SSRF Security Defenses.
"""

import unittest
from unittest.mock import patch, MagicMock
from seo_engine.fetcher import SEOFetcher, FetchResult


class TestSEOFetcherSecurity(unittest.TestCase):

    def test_url_syntax_validation(self):
        # Valid URLs
        valid, url = SEOFetcher.validate_url_syntax("https://example.com")
        self.assertTrue(valid)
        self.assertEqual(url, "https://example.com")

        valid, url = SEOFetcher.validate_url_syntax("http://example.com/sub/page")
        self.assertTrue(valid)

        # Auto prepend https scheme
        valid, url = SEOFetcher.validate_url_syntax("example.com/test")
        self.assertTrue(valid)
        self.assertTrue(url.startswith("https://"))

        # Blocked dangerous schemes
        valid, err = SEOFetcher.validate_url_syntax("file:///etc/passwd")
        self.assertFalse(valid)
        self.assertIn("Unsupported URL protocol", err)

        valid, err = SEOFetcher.validate_url_syntax("ftp://ftp.example.com")
        self.assertFalse(valid)

        valid, err = SEOFetcher.validate_url_syntax("gopher://example.com")
        self.assertFalse(valid)

        # Empty / invalid
        valid, err = SEOFetcher.validate_url_syntax("")
        self.assertFalse(valid)

    def test_ssrf_ip_blocking(self):
        # Loopback
        safe, reason = SEOFetcher.is_safe_ip("127.0.0.1")
        self.assertFalse(safe)
        self.assertIn("loopback", reason.lower())

        safe, reason = SEOFetcher.is_safe_ip("::1")
        self.assertFalse(safe)

        # Private IPv4 subnets
        safe, reason = SEOFetcher.is_safe_ip("10.0.0.1")
        self.assertFalse(safe)
        self.assertIn("private", reason.lower())

        safe, reason = SEOFetcher.is_safe_ip("172.16.0.5")
        self.assertFalse(safe)

        safe, reason = SEOFetcher.is_safe_ip("192.168.1.100")
        self.assertFalse(safe)

        # Cloud metadata service (AWS/GCP/Azure link-local)
        safe, reason = SEOFetcher.is_safe_ip("169.254.169.254")
        self.assertFalse(safe)

        # Unspecified 0.0.0.0
        safe, reason = SEOFetcher.is_safe_ip("0.0.0.0")
        self.assertFalse(safe)

        # Public safe IP (e.g. 93.184.216.34)
        safe, reason = SEOFetcher.is_safe_ip("93.184.216.34")
        self.assertTrue(safe)

    def test_ssrf_hostname_checks(self):
        safe, reason = SEOFetcher.check_ssrf_safety("http://localhost:8080")
        self.assertFalse(safe)

        safe, reason = SEOFetcher.check_ssrf_safety("http://metadata.google.internal/computeMetadata/v1/")
        self.assertFalse(safe)

        safe, reason = SEOFetcher.check_ssrf_safety("http://127.0.0.1/admin")
        self.assertFalse(safe)

        safe, reason = SEOFetcher.check_ssrf_safety("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(safe)

    def test_local_project_reader(self):
        # Read from tests directory or current project
        res = SEOFetcher.read_local_project_html("tests/fixtures/seo/excellent.html")
        self.assertTrue(res.success)
        self.assertTrue(res.is_local)
        self.assertIn("Quantum Shield", res.content)

        # Non-existent directory
        res = SEOFetcher.read_local_project_html("non_existent_folder_xyz_123")
        self.assertFalse(res.success)
        self.assertIn("does not exist", res.error)

    @patch("requests.Session.get")
    def test_fetch_http_errors(self, mock_get):
        # Mock 403 Forbidden
        mock_resp = MagicMock()
        mock_resp.is_redirect = False
        mock_resp.status_code = 403
        mock_resp.headers = {}
        mock_get.return_value = mock_resp

        # Mock check_ssrf_safety to return safe for mock test
        with patch.object(SEOFetcher, "check_ssrf_safety", return_value=(True, "Safe")):
            res = SEOFetcher.fetch_url("https://example.com/restricted", use_cache=False)
            self.assertFalse(res.success)
            self.assertEqual(res.status_code, 403)
            self.assertIn("HTTP 403", res.error)


if __name__ == "__main__":
    unittest.main()
