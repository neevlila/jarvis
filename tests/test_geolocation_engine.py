"""
Tests for J.A.R.V.I.S. Geolocation Engine & Global Intelligence Globe
====================================================================
Comprehensive test suite verifying IP parsing, private subnet filtering,
natural-language intent detection, provider mocking, error boundaries,
and assistant end-to-end integration.
"""

import unittest
from unittest.mock import MagicMock, patch
import requests

from geolocation_engine import (
    IPValidator,
    IPIntentDetector,
    GeolocationResult,
    GeolocationService,
    GeolocationSynthesizer
)
import buddy


class TestIPValidation(unittest.TestCase):
    """Tests for IPv4 and IPv6 syntax validation and extraction."""

    def test_valid_ipv4(self):
        valid_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "208.67.222.222",
            "192.168.1.1",
            "10.0.0.1",
            "172.16.254.1",
            "127.0.0.1",
            "0.0.0.0",
            "255.255.255.255"
        ]
        for ip in valid_ips:
            is_valid, ip_obj, err = IPValidator.validate_ip(ip)
            self.assertTrue(is_valid, f"Expected {ip} to be valid IPv4")
            self.assertIsNotNone(ip_obj)
            self.assertIsNone(err)

    def test_invalid_ipv4(self):
        invalid_ips = [
            "999.999.999.999",
            "256.0.0.1",
            "1.2.3.4.5",
            "1.2.3",
            "1.2.3.4.",
            "abcd",
            "8.8.8.8.com",
            "",
            None
        ]
        for ip in invalid_ips:
            is_valid, ip_obj, err = IPValidator.validate_ip(ip)
            self.assertFalse(is_valid, f"Expected {ip} to be invalid")
            self.assertIsNone(ip_obj)
            self.assertIsNotNone(err)

    def test_valid_ipv6(self):
        valid_ipv6 = [
            "2001:4860:4860::8888",
            "2606:4700:4700::1111",
            "::1",
            "fe80::1"
        ]
        for ip in valid_ipv6:
            is_valid, ip_obj, err = IPValidator.validate_ip(ip)
            self.assertTrue(is_valid, f"Expected {ip} to be valid IPv6")
            self.assertIsNotNone(ip_obj)
            self.assertIsNone(err)

    def test_candidate_extraction_from_sentence(self):
        text = "Please check 8.8.8.8 and also 1.1.1.1 for security."
        candidates = IPValidator.extract_ip_candidates(text)
        self.assertEqual(candidates, ["8.8.8.8", "1.1.1.1"])


class TestPrivateSubnetDetection(unittest.TestCase):
    """Tests private/reserved IP detection without external calls."""

    def test_private_subnets(self):
        private_ips = [
            "10.0.0.1",
            "10.254.254.254",
            "172.16.0.1",
            "172.31.255.255",
            "192.168.0.1",
            "192.168.1.100",
            "127.0.0.1",
            "169.254.1.1",
            "::1"
        ]
        for ip_str in private_ips:
            _, ip_obj, _ = IPValidator.validate_ip(ip_str)
            self.assertTrue(IPValidator.is_private_or_reserved(ip_obj), f"{ip_str} should be detected as private/reserved")

    def test_public_subnets(self):
        public_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "9.9.9.9",
            "208.67.222.222",
            "140.82.121.4"
        ]
        for ip_str in public_ips:
            _, ip_obj, _ = IPValidator.validate_ip(ip_str)
            self.assertFalse(IPValidator.is_private_or_reserved(ip_obj), f"{ip_str} should be recognized as public")

    def test_service_lookup_private_ip(self):
        service = GeolocationService()
        result = service.lookup("192.168.1.1")
        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_private)
        self.assertFalse(result.has_coordinates)
        self.assertIn("private/local IP address", result.error_message)


class TestIPIntentDetection(unittest.TestCase):
    """Tests natural language intent extraction."""

    def test_location_intents(self):
        test_queries = [
            ("Where is 8.8.8.8?", "8.8.8.8"),
            ("Locate 8.8.8.8", "8.8.8.8"),
            ("Track this IP: 8.8.8.8", "8.8.8.8"),
            ("What's the location of 8.8.8.8?", "8.8.8.8"),
            ("Analyze 8.8.8.8", "8.8.8.8"),
            ("Show me where 1.1.1.1 is.", "1.1.1.1"),
            ("Where's 208.67.222.222 located?", "208.67.222.222"),
            ("8.8.8.8", "8.8.8.8"),
            ("ip: 1.1.1.1", "1.1.1.1")
        ]
        for query, expected_ip in test_queries:
            detection = IPIntentDetector.detect_intent(query)
            self.assertIsNotNone(detection, f"Failed to detect intent for: '{query}'")
            self.assertEqual(detection[0], expected_ip)
            self.assertEqual(detection[1], "GEOLOCATION_LOOKUP")

    def test_non_ip_or_domain_queries(self):
        non_geo_queries = [
            "Locate google.com",
            "What is the weather today?",
            "Write python code for a binary search",
            "Open youtube and play jazz",
            "How are you doing today?"
        ]
        for query in non_geo_queries:
            detection = IPIntentDetector.detect_intent(query)
            self.assertIsNone(detection, f"Query should not trigger IP intent: '{query}'")


class TestGeolocationService(unittest.TestCase):
    """Tests provider client, response normalization, and error handling."""

    @patch("requests.get")
    def test_successful_provider_lookup(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "ip": "8.8.8.8",
            "success": True,
            "city": "Mountain View",
            "region": "California",
            "country": "United States",
            "country_code": "US",
            "latitude": 37.4056,
            "longitude": -122.0775,
            "timezone": {"id": "America/Los_Angeles"},
            "connection": {"isp": "Google LLC", "org": "Google Public DNS"}
        }
        mock_get.return_value = mock_resp

        service = GeolocationService()
        result = service.lookup("8.8.8.8")

        self.assertTrue(result.is_valid)
        self.assertFalse(result.is_private)
        self.assertEqual(result.city, "Mountain View")
        self.assertEqual(result.region, "California")
        self.assertEqual(result.country, "United States")
        self.assertEqual(result.latitude, 37.4056)
        self.assertEqual(result.longitude, -122.0775)
        self.assertEqual(result.timezone, "America/Los_Angeles")
        self.assertEqual(result.isp, "Google LLC")
        self.assertEqual(result.accuracy, "approximate")
        self.assertTrue(result.has_coordinates)

    @patch("requests.get")
    def test_rate_limit_and_fallback(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        service = GeolocationService(api_url="https://api.custom-geo.com/{ip}")
        result = service.lookup("8.8.8.8")

        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.error_message)

    @patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out"))
    def test_timeout_graceful_recovery(self, mock_get):
        service = GeolocationService()
        result = service.lookup("8.8.8.8")

        self.assertTrue(result.is_valid)
        self.assertFalse(result.has_coordinates)
        self.assertIn("Unable to resolve", result.error_message)

    def test_malformed_ip_rejection(self):
        service = GeolocationService()
        result = service.lookup("999.999.999.999")
        self.assertFalse(result.is_valid)
        self.assertIn("Malformed or invalid IP", result.error_message)


class TestSynthesizerAndContext(unittest.TestCase):
    """Tests response generation and Context Engine integration."""

    def test_chat_response_synthesis(self):
        res = GeolocationResult(
            ip="8.8.8.8",
            city="Mountain View",
            region="California",
            country="United States",
            latitude=37.4056,
            longitude=-122.0775,
            organization="Google LLC"
        )
        msg = GeolocationSynthesizer.build_chat_response(res)
        self.assertIn("8.8.8.8", msg)
        self.assertIn("Mountain View", msg)
        self.assertIn("United States", msg)
        self.assertIn("Google LLC", msg)
        self.assertIn("marked it on the global intelligence display", msg)

    def test_context_assertions(self):
        res = GeolocationResult(
            ip="1.1.1.1",
            city="Sydney",
            country="Australia",
            latitude=-33.8688,
            longitude=151.2093
        )
        assertions = GeolocationSynthesizer.build_context_assertions(res)
        self.assertIn("OBSERVED", assertions)
        self.assertIn("INFERRED", assertions)
        self.assertIn("UNKNOWN", assertions)
        self.assertTrue(any("1.1.1.1" in item for item in assertions["OBSERVED"]))
        self.assertTrue(any("Exact physical device location" in item for item in assertions["UNKNOWN"]))


class TestAssistantIntegration(unittest.TestCase):
    """Tests J.A.R.V.I.S. assistant command dispatching for Geolocation."""

    def setUp(self):
        self.assistant = buddy.JarvisAssistant()
        self.assistant.recent_responses = []

    @patch.object(GeolocationService, "lookup")
    def test_assistant_process_ip_command(self, mock_lookup):
        mock_lookup.return_value = GeolocationResult(
            ip="8.8.8.8",
            city="Mountain View",
            region="California",
            country="United States",
            latitude=37.4056,
            longitude=-122.0775,
            isp="Google LLC"
        )

        should_exit = self.assistant.process_command_with_mode("Where is 8.8.8.8?", type_mode=True)
        self.assertFalse(should_exit)
        self.assertIsNotNone(self.assistant.location_target)
        self.assertEqual(self.assistant.location_target.get("ip"), "8.8.8.8")
        self.assertEqual(self.assistant.location_target.get("city"), "Mountain View")
        self.assertEqual(self.assistant.location_target.get("latitude"), 37.4056)
        self.assertTrue(any("Mountain View" in resp for resp in self.assistant.recent_responses))

    def test_assistant_reset_globe_command(self):
        should_exit = self.assistant.process_command_with_mode("clear target", type_mode=True)
        self.assertFalse(should_exit)
        self.assertIsNotNone(self.assistant.location_target)
        self.assertEqual(self.assistant.location_target.get("action"), "reset")
        self.assertTrue(any("target cleared" in resp for resp in self.assistant.recent_responses))


if __name__ == "__main__":
    unittest.main()
