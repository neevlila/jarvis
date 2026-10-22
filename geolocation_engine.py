"""
J.A.R.V.I.S. Geolocation Engine
================================
Core intelligence module for IP entity extraction, IP address syntax validation,
private/reserved address detection, provider-agnostic geolocation resolution,
data normalization, and 3D visual target dispatch.
"""

from __future__ import annotations
import ipaddress
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import requests

try:
    from config import GeolocationConfig
except ImportError:
    class GeolocationConfig:
        IP_GEOLOCATION_API_URL = None
        IP_GEOLOCATION_API_KEY = None

logger = logging.getLogger("jarvis.geolocation")


# ----------------------------------------------------------------------
# Data Models
# ----------------------------------------------------------------------

@dataclass
class GeolocationResult:
    """Normalized IP Geolocation Data Model."""
    ip: str
    is_valid: bool = True
    is_private: bool = False
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    organization: Optional[str] = None
    accuracy: str = "approximate"
    source: str = "IP Geolocation Provider"
    timestamp: float = field(default_factory=time.time)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary omitting nulls or internal artifacts."""
        data = asdict(self)
        if self.latitude is not None and self.longitude is not None:
            lat_dir = "N" if self.latitude >= 0 else "S"
            lon_dir = "E" if self.longitude >= 0 else "W"
            data["coordinates_formatted"] = f"{abs(self.latitude):.4f}° {lat_dir}, {abs(self.longitude):.4f}° {lon_dir}"
        return data

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


# ----------------------------------------------------------------------
# IP Validation & Subnet Inspection
# ----------------------------------------------------------------------

class IPValidator:
    """Validates and inspects IPv4 and IPv6 addresses."""

    # Pre-compiled strict IPv4 and IPv6 candidate extractors
    IPV4_CANDIDATE_REGEX = re.compile(
        r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\b'
    )
    
    IPV6_CANDIDATE_REGEX = re.compile(
        r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|'
        r'\b(?:[0-9a-fA-F]{1,4}:){1,7}:|'
        r'\b:[0-9a-fA-F]{1,7}:|'
        r'\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b|'
        r'\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b'
    )

    @classmethod
    def validate_ip(cls, ip_str: str) -> Tuple[bool, Optional[ipaddress.IPv4Address | ipaddress.IPv6Address], Optional[str]]:
        """
        Validates IP syntax strictly.
        Returns (is_valid, ip_object, error_message).
        """
        if not ip_str or not isinstance(ip_str, str):
            return False, None, "No IP address provided."
        
        clean_ip = ip_str.strip().strip("[]\"'")
        try:
            ip_obj = ipaddress.ip_address(clean_ip)
            return True, ip_obj, None
        except ValueError as err:
            return False, None, f"Malformed or invalid IP address format: '{clean_ip}'."

    @classmethod
    def is_private_or_reserved(cls, ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """
        Checks if the IP address belongs to private, loopback, link-local,
        multicast, or reserved address ranges.
        """
        return (
            ip_obj.is_private or
            ip_obj.is_loopback or
            ip_obj.is_reserved or
            ip_obj.is_link_local or
            ip_obj.is_multicast or
            ip_obj.is_unspecified
        )

    @classmethod
    def extract_ip_candidates(cls, text: str) -> List[str]:
        """Extracts potential IPv4 and IPv6 string tokens from natural language text."""
        if not text:
            return []
        
        candidates = []
        for match in cls.IPV4_CANDIDATE_REGEX.finditer(text):
            candidates.append(match.group(0))
            
        for match in cls.IPV6_CANDIDATE_REGEX.finditer(text):
            candidate = match.group(0).strip(":")
            if candidate and ":" in candidate:
                candidates.append(candidate)
                
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique


# ----------------------------------------------------------------------
# Natural Language Intent Detection
# ----------------------------------------------------------------------

class IPIntentDetector:
    """Detects geolocation & IP analysis intent from natural-language instructions."""

    LOCATION_INTENT_KEYWORDS = [
        "where is", "where's", "locate", "location of", "track", "trace",
        "find", "geolocate", "geolocation", "coordinates of", "map", "pinpoint",
        "whois", "analyze", "lookup", "show me where", "position of", "ip info"
    ]

    CLIENT_IP_KEYWORDS = [
        "what is my ip", "what's my ip", "whats my ip", "my ip", "my ip address",
        "what is my location", "what's my location", "my location", "where am i",
        "current location", "my current ip", "get my ip", "show my ip", "check my ip",
        "find my ip", "my current location", "my public ip", "what is my public ip", "whats my public ip"
    ]

    @classmethod
    def detect_intent(cls, command: str) -> Optional[Tuple[str, str]]:
        """
        Analyzes command text for IP address and geolocation intent.
        Returns (ip_str, intent_type) if found, otherwise None.
        """
        if not command:
            return None
        
        # Clean trailing punctuation for robust matching
        clean_cmd = re.sub(r'[\?\,\!\;\:]+$', '', command.strip())
        cmd_lower = clean_cmd.lower().strip()

        # 1. Check for client/self IP query intent (e.g. "what's my ip", "where am i")
        if any(cmd_lower == kw or cmd_lower.startswith(kw) or f" {kw}" in cmd_lower for kw in cls.CLIENT_IP_KEYWORDS):
            return "auto", "CLIENT_IP_LOOKUP"
        
        # 2. Extract strict IP tokens
        ip_tokens = IPValidator.extract_ip_candidates(clean_cmd)
        
        # 3. Extract potential malformed IPs if no strict candidate found
        if not ip_tokens:
            words = re.findall(r'[\w\.\:]+', clean_cmd)
            for w in words:
                w_clean = w.strip("?.,!;:")
                if (w_clean.count('.') == 3 and any(c.isdigit() for c in w_clean)) or (w_clean.count(':') >= 2 and any(c.isalnum() for c in w_clean)):
                    ip_tokens.append(w_clean)
                    break

        if not ip_tokens:
            return None
        
        target_ip = ip_tokens[0].strip("?.,!;:")
        
        # If an explicit IP token is present in the prompt, route to Geolocation
        return target_ip, "GEOLOCATION_LOOKUP"


# ----------------------------------------------------------------------
# Geolocation Service Provider
# ----------------------------------------------------------------------

class GeolocationService:
    """
    Provider-agnostic IP Geolocation client.
    Supports environment configuration, timeouts, fallback providers,
    response normalization, and secure error boundaries.
    """

    DEFAULT_TIMEOUT_SECONDS = 4.0

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS
    ):
        self.api_url = api_url or GeolocationConfig.IP_GEOLOCATION_API_URL
        self.api_key = api_key or GeolocationConfig.IP_GEOLOCATION_API_KEY
        self.timeout = timeout

    def lookup(self, ip_str: str) -> GeolocationResult:
        """
        Executes complete lookup pipeline for an IP address.
        """
        # If client IP query ("auto" or empty)
        if not ip_str or ip_str == "auto":
            return self._query_provider("")

        # 1. Validate IP syntax
        is_valid, ip_obj, err = IPValidator.validate_ip(ip_str)
        if not is_valid or ip_obj is None:
            return GeolocationResult(
                ip=ip_str,
                is_valid=False,
                error_message=err or "Invalid IP address syntax."
            )
        
        clean_ip = str(ip_obj)

        # 2. Check for private/reserved/loopback address
        if IPValidator.is_private_or_reserved(ip_obj):
            return GeolocationResult(
                ip=clean_ip,
                is_valid=True,
                is_private=True,
                accuracy="n/a",
                source="Local Network Filter",
                error_message="That is a private/local IP address, so a public geographic location cannot be determined from it."
            )

        # 3. Query External Provider securely
        return self._query_provider(clean_ip)

    def _query_provider(self, ip: str) -> GeolocationResult:
        """Queries configured or fallback external IP geolocation service."""
        # Provider 1: Configured URL if provided
        if self.api_url:
            try:
                url = self.api_url.replace("{ip}", ip)
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    headers["X-API-KEY"] = self.api_key
                resp = requests.get(url, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    return self._normalize_response(ip, data, source="Custom Geolocation API")
                elif resp.status_code == 429:
                    return GeolocationResult(
                        ip=ip,
                        is_valid=True,
                        error_message="Geolocation provider rate limit exceeded. Please try again in a moment."
                    )
            except Exception as e:
                logger.warning(f"Custom geolocation provider failed for {ip}: {e}")

        # Provider 2: Standard Open IP Geolocation Endpoint (ipwho.is)
        try:
            resp = requests.get(f"https://ipwho.is/{ip}", timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") is False:
                    msg = data.get("message", "Provider could not resolve IP.")
                    return GeolocationResult(ip=ip, is_valid=True, error_message=msg)
                return self._normalize_ipwhois(ip, data)
        except Exception as e:
            logger.warning(f"Primary open provider ipwho.is failed for {ip}: {e}")

        # Provider 3: Fallback Open IP Geolocation Endpoint (ip-api.com)
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,lat,lon,timezone,isp,org,as", timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "fail":
                    msg = data.get("message", "IP resolution failed.")
                    return GeolocationResult(ip=ip, is_valid=True, error_message=msg)
                return self._normalize_ipapi(ip, data)
        except Exception as e:
            logger.warning(f"Fallback open provider ip-api.com failed for {ip}: {e}")

        # All providers failed / network timeout
        return GeolocationResult(
            ip=ip,
            is_valid=True,
            error_message="Unable to resolve geographic information for this IP address (network timeout or provider unavailable)."
        )

    def _normalize_ipwhois(self, ip: str, data: Dict[str, Any]) -> GeolocationResult:
        """Normalizes ipwho.is JSON payload."""
        resolved_ip = data.get("ip") or ip
        lat = data.get("latitude")
        lon = data.get("longitude")
        connection = data.get("connection", {}) or {}
        timezone = data.get("timezone", {}) or {}

        return GeolocationResult(
            ip=resolved_ip,
            is_valid=True,
            is_private=False,
            city=data.get("city") or None,
            region=data.get("region") or None,
            country=data.get("country") or None,
            country_code=data.get("country_code") or None,
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
            timezone=timezone.get("id") if isinstance(timezone, dict) else None,
            isp=connection.get("isp") or None,
            organization=connection.get("org") or connection.get("domain") or None,
            accuracy="approximate",
            source="ipwho.is"
        )

    def _normalize_ipapi(self, ip: str, data: Dict[str, Any]) -> GeolocationResult:
        """Normalizes ip-api.com JSON payload."""
        resolved_ip = data.get("query") or ip
        lat = data.get("lat")
        lon = data.get("lon")

        return GeolocationResult(
            ip=resolved_ip,
            is_valid=True,
            is_private=False,
            city=data.get("city") or None,
            region=data.get("regionName") or data.get("region") or None,
            country=data.get("country") or None,
            country_code=data.get("countryCode") or None,
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
            timezone=data.get("timezone") or None,
            isp=data.get("isp") or None,
            organization=data.get("org") or data.get("as") or None,
            accuracy="approximate",
            source="ip-api.com"
        )

    def _normalize_response(self, ip: str, data: Dict[str, Any], source: str) -> GeolocationResult:
        """Generic normalizer for custom API responses."""
        resolved_ip = data.get("ip") or data.get("query") or ip
        lat = data.get("latitude") or data.get("lat")
        lon = data.get("longitude") or data.get("lon") or data.get("lng")
        
        return GeolocationResult(
            ip=resolved_ip,
            is_valid=True,
            is_private=False,
            city=data.get("city") or None,
            region=data.get("region") or data.get("regionName") or None,
            country=data.get("country") or data.get("countryName") or None,
            country_code=data.get("country_code") or data.get("countryCode") or None,
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
            timezone=data.get("timezone") if isinstance(data.get("timezone"), str) else None,
            isp=data.get("isp") or None,
            organization=data.get("organization") or data.get("org") or None,
            accuracy="approximate",
            source=source
        )


# ----------------------------------------------------------------------
# J.A.R.V.I.S. Natural Language Synthesizer & Context Integration
class GeolocationSynthesizer:
    """Builds executive natural language responses and context assertions."""

    @classmethod
    def build_chat_response(cls, result: GeolocationResult) -> str:
        """Synthesizes human-friendly, accurate J.A.R.V.I.S. response."""
        if not result.is_valid:
            return f"Sir, the IP address format appears to be invalid: {result.error_message or 'Please provide a valid IPv4 or IPv6 address.'}"
            
        if result.is_private:
            return f"IP {result.ip} is a private local network address. A public geographic location cannot be determined from private subnets."
            
        if not result.has_coordinates and result.error_message:
            return f"I was unable to resolve location coordinates for {result.ip}. {result.error_message}"

        parts = []
        if result.city:
            parts.append(result.city)
        if result.region and result.region != result.city:
            parts.append(result.region)
        if result.country:
            parts.append(result.country)
            
        location_desc = ", ".join(parts) if parts else "an approximate location"
        
        resp = f"{result.ip} is associated with an approximate location in {location_desc}."
        if result.isp or result.organization:
            provider_name = result.organization or result.isp
            resp += f" Routed via {provider_name}."
            
        resp += " I've marked it on the global intelligence display."
        return resp

    @classmethod
    def build_context_assertions(cls, result: GeolocationResult) -> Dict[str, List[str]]:
        """
        Integrates with J.A.R.V.I.S. Context Engine ontology:
        OBSERVED, INFERRED, UNKNOWN
        """
        observed = [f"Target IP: {result.ip}"]
        inferred = []
        unknown = ["Exact physical device location (IP geolocation is approximate)"]

        if result.is_private:
            observed.append("Network scope: Private/Local Network")
            inferred.append("Device is on a private subnet (LAN/VPC)")
        elif result.has_coordinates:
            observed.append(f"Geographic Coordinates: {result.latitude:.4f}, {result.longitude:.4f}")
            if result.city:
                observed.append(f"City: {result.city}")
            if result.region:
                observed.append(f"Region: {result.region}")
            if result.country:
                observed.append(f"Country: {result.country}")
            if result.timezone:
                observed.append(f"Timezone: {result.timezone}")
            if result.isp or result.organization:
                observed.append(f"ISP / Autonomous System: {result.organization or result.isp}")
            inferred.append(f"Approximate geographic vicinity: {result.city or result.country or 'Global'}")
        else:
            unknown.append("Geographic coordinates unavailable from provider")

        return {
            "OBSERVED": observed,
            "INFERRED": inferred,
            "UNKNOWN": unknown
        }


# Global singleton service instance
default_geolocation_service = GeolocationService()
