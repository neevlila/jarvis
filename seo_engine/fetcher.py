"""
Secure URL Fetcher and Local Project Source Reader for J.A.R.V.I.S. SEO Intelligence.

Features:
- Enterprise-grade SSRF defense (blocking loopback, private ranges, link-local, cloud metadata, IPv6).
- Redirect-based SSRF defense with step-by-step target validation.
- Stream size limiting (max 5MB) to protect against memory exhaustion.
- Connection pooling and thread-safe in-memory caching.
- Safe local repository file discovery and source extraction.
"""

import os
import re
import time
import socket
import ipaddress
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
import requests

class FetchResult:
    def __init__(
        self,
        success: bool,
        content: str = "",
        status_code: int = 0,
        headers: Optional[Dict[str, str]] = None,
        latency_ms: float = 0.0,
        content_length: int = 0,
        final_url: str = "",
        error: Optional[str] = None,
        robots_txt: Optional[str] = None,
        sitemap_xml: Optional[str] = None,
        is_local: bool = False
    ):
        self.success = success
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.latency_ms = latency_ms
        self.content_length = content_length or len(content.encode("utf-8", errors="ignore"))
        self.final_url = final_url
        self.error = error
        self.robots_txt = robots_txt
        self.sitemap_xml = sitemap_xml
        self.is_local = is_local


class SEOFetcher:
    """
    Secure fetcher with strict SSRF filtering, redirect protection, size limits, and caching.
    """

    MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MB max
    REQUEST_TIMEOUT_SECONDS = 10
    MAX_REDIRECTS = 5
    CACHE_TTL_SECONDS = 300  # 5 minutes

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (J.A.R.V.I.S. SEO Intelligence/3.12)"
    )

    BLOCKED_HOSTNAMES = {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "instance-data",
        "169.254.169.254"
    }

    _cache: Dict[str, Tuple[float, FetchResult]] = {}
    _session: Optional[requests.Session] = None

    @classmethod
    def _get_session(cls) -> requests.Session:
        if cls._session is None:
            cls._session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=1
            )
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)
        return cls._session

    @classmethod
    def validate_url_syntax(cls, url: str) -> Tuple[bool, str]:
        """
        Validates URL syntax and protocol.
        """
        if not url or not isinstance(url, str):
            return False, "URL cannot be empty."

        clean = url.strip()
        if clean.startswith("file://") or clean.startswith("ftp://") or clean.startswith("gopher://") or clean.startswith("data:"):
            return False, f"Unsupported URL protocol '{clean.split('://')[0]}://'. Only HTTP and HTTPS are permitted."

        if not clean.startswith("http://") and not clean.startswith("https://"):
            # Auto-prepend https if missing scheme
            clean = "https://" + clean

        try:
            parsed = urllib.parse.urlparse(clean)
            if not parsed.netloc:
                return False, "Invalid URL structure: Hostname missing."
            
            hostname = parsed.hostname
            if not hostname:
                return False, "Invalid URL structure: Unable to extract hostname."

            return True, clean
        except Exception as e:
            return False, f"Malformed URL: {str(e)}"

    @classmethod
    def is_safe_ip(cls, ip_str: str) -> Tuple[bool, str]:
        """
        Validates that an IP address is not private, loopback, link-local, reserved, or multicast.
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_loopback:
                return False, f"Access to loopback address ({ip_str}) is forbidden."
            if ip.is_private:
                return False, f"Access to private/internal network ({ip_str}) is forbidden."
            if ip.is_link_local:
                return False, f"Access to link-local address ({ip_str}) is forbidden."
            if ip.is_reserved:
                return False, f"Access to reserved IP range ({ip_str}) is forbidden."
            if ip.is_unspecified:
                return False, f"Access to unspecified address ({ip_str}) is forbidden."
            if ip.is_multicast:
                return False, f"Access to multicast address ({ip_str}) is forbidden."
            
            # Specifically block AWS / Azure / GCP cloud metadata 169.254.169.254
            if str(ip) == "169.254.169.254":
                return False, "Access to cloud metadata endpoints is forbidden."

            return True, "Safe IP"
        except ValueError:
            return False, f"Invalid IP address format '{ip_str}'."

    @classmethod
    def check_ssrf_safety(cls, url: str) -> Tuple[bool, str]:
        """
        Resolves hostname to IP addresses and enforces SSRF restrictions.
        """
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False, "Missing hostname in URL."

            hostname_lower = hostname.lower()
            if hostname_lower in cls.BLOCKED_HOSTNAMES:
                return False, f"Access to restricted hostname '{hostname}' is forbidden."

            # If hostname is an IP string directly
            try:
                ip = ipaddress.ip_address(hostname_lower)
                return cls.is_safe_ip(str(ip))
            except ValueError:
                pass  # It is a domain name, resolve via DNS

            # Resolve DNS
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            try:
                addr_infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
            except socket.gaierror as e:
                return False, f"DNS resolution failed for '{hostname}': {str(e)}"

            if not addr_infos:
                return False, f"Could not resolve host '{hostname}'."

            for addr_info in addr_infos:
                sockaddr = addr_info[4]
                ip_resolved = sockaddr[0]
                safe, reason = cls.is_safe_ip(ip_resolved)
                if not safe:
                    return False, f"Host '{hostname}' resolved to unsafe IP ({ip_resolved}): {reason}"

            return True, "Safe host"
        except Exception as e:
            return False, f"Security verification error: {str(e)}"

    @classmethod
    def fetch_url(cls, url: str, use_cache: bool = True) -> FetchResult:
        """
        Safely retrieves the web page at URL with SSRF protection, redirect verification,
        size limits, and error diagnostics.
        """
        valid, validated_url = cls.validate_url_syntax(url)
        if not valid:
            return FetchResult(success=False, error=validated_url)

        # Check cache
        now = time.time()
        if use_cache and validated_url in cls._cache:
            timestamp, cached_res = cls._cache[validated_url]
            if (now - timestamp) < cls.CACHE_TTL_SECONDS:
                return cached_res

        # Check SSRF safety
        safe, sec_reason = cls.check_ssrf_safety(validated_url)
        if not safe:
            return FetchResult(success=False, error=f"Security Policy Violation: {sec_reason}")

        session = cls._get_session()
        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close"
        }

        current_url = validated_url
        redirect_count = 0
        start_time = time.time()

        try:
            while redirect_count <= cls.MAX_REDIRECTS:
                # Validate redirect destination on each hop
                safe, hop_reason = cls.check_ssrf_safety(current_url)
                if not safe:
                    return FetchResult(
                        success=False,
                        error=f"Redirect to unsafe destination blocked ({current_url}): {hop_reason}"
                    )

                response = session.get(
                    current_url,
                    headers=headers,
                    timeout=cls.REQUEST_TIMEOUT_SECONDS,
                    allow_redirects=False,
                    stream=True,
                    verify=True
                )

                # Handle manual redirect inspection
                if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
                    redirect_location = response.headers.get("Location")
                    if not redirect_location:
                        break
                    # Resolve relative redirect URLs
                    current_url = urllib.parse.urljoin(current_url, redirect_location)
                    redirect_count += 1
                    continue

                # We reached final destination
                latency_ms = (time.time() - start_time) * 1000

                # Check HTTP status
                if response.status_code == 403:
                    return FetchResult(
                        success=False,
                        status_code=403,
                        latency_ms=latency_ms,
                        final_url=current_url,
                        error=f"J.A.R.V.I.S. could not retrieve the page because the server returned HTTP 403 (Forbidden/Access Denied)."
                    )
                if response.status_code == 404:
                    return FetchResult(
                        success=False,
                        status_code=404,
                        latency_ms=latency_ms,
                        final_url=current_url,
                        error=f"J.A.R.V.I.S. could not find the page at HTTP 404 (Not Found)."
                    )
                if response.status_code == 429:
                    return FetchResult(
                        success=False,
                        status_code=429,
                        latency_ms=latency_ms,
                        final_url=current_url,
                        error=f"The remote web server is rate-limiting requests (HTTP 429 Too Many Requests)."
                    )
                if response.status_code >= 500:
                    return FetchResult(
                        success=False,
                        status_code=response.status_code,
                        latency_ms=latency_ms,
                        final_url=current_url,
                        error=f"Remote server error (HTTP {response.status_code}). Website is currently unavailable."
                    )

                # Read body content safely with size cap
                content_chunks = []
                total_bytes = 0
                for chunk in response.iter_content(chunk_size=16384):
                    total_bytes += len(chunk)
                    if total_bytes > cls.MAX_CONTENT_BYTES:
                        return FetchResult(
                            success=False,
                            status_code=response.status_code,
                            error=f"Document exceeds maximum permitted size of {cls.MAX_CONTENT_BYTES / (1024*1024):.0f}MB."
                        )
                    content_chunks.append(chunk)

                raw_bytes = b"".join(content_chunks)

                # Decode encoding
                encoding = response.encoding or response.apparent_encoding or "utf-8"
                try:
                    text_content = raw_bytes.decode(encoding, errors="replace")
                except Exception:
                    text_content = raw_bytes.decode("utf-8", errors="replace")

                # Fetch companion robots.txt & sitemap.xml if applicable
                parsed_root = urllib.parse.urlparse(current_url)
                root_origin = f"{parsed_root.scheme}://{parsed_root.netloc}"
                robots_txt = cls._try_fetch_companion(root_origin + "/robots.txt", session)
                sitemap_xml = cls._try_fetch_companion(root_origin + "/sitemap.xml", session)

                res = FetchResult(
                    success=True,
                    content=text_content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    latency_ms=latency_ms,
                    content_length=len(raw_bytes),
                    final_url=current_url,
                    robots_txt=robots_txt,
                    sitemap_xml=sitemap_xml
                )

                # Store in cache
                cls._cache[validated_url] = (time.time(), res)
                return res

            return FetchResult(
                success=False,
                error=f"Exceeded maximum redirect limit ({cls.MAX_REDIRECTS}). Potential redirect loop detected."
            )

        except requests.exceptions.SSLError as e:
            return FetchResult(success=False, error=f"SSL/TLS Certificate verification failed: {str(e)}")
        except requests.exceptions.Timeout:
            return FetchResult(success=False, error=f"Request timed out after {cls.REQUEST_TIMEOUT_SECONDS}s. Server took too long to respond.")
        except requests.exceptions.ConnectionError as e:
            return FetchResult(success=False, error=f"Unable to connect to host: {str(e)}")
        except Exception as e:
            return FetchResult(success=False, error=f"Retrieval error: {str(e)}")

    @classmethod
    def _try_fetch_companion(cls, url: str, session: requests.Session) -> Optional[str]:
        """Silently attempts to fetch robots.txt or sitemap.xml."""
        try:
            safe, _ = cls.check_ssrf_safety(url)
            if not safe:
                return None
            resp = session.get(url, timeout=3, headers={"User-Agent": cls.USER_AGENT}, verify=True)
            if resp.status_code == 200 and len(resp.content) < 500000:
                return resp.text
        except Exception:
            pass
        return None

    @classmethod
    def read_local_project_html(cls, project_path: str) -> FetchResult:
        """
        Scans a local directory for primary HTML/JSX/Astro templates to perform source-level SEO analysis.
        """
        if not os.path.exists(project_path):
            return FetchResult(success=False, error=f"Local project path does not exist: '{project_path}'")

        if os.path.isfile(project_path):
            try:
                with open(project_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return FetchResult(
                    success=True,
                    content=content,
                    status_code=200,
                    final_url=os.path.abspath(project_path),
                    content_length=len(content),
                    is_local=True
                )
            except Exception as e:
                return FetchResult(success=False, error=f"Error reading file '{project_path}': {str(e)}")

        # Directory mode: search for index.html, App.jsx, index.tsx, page.tsx, etc.
        priority_files = [
            "index.html",
            "public/index.html",
            "src/index.html",
            "web/index.html",
            "app/layout.tsx",
            "app/page.tsx",
            "src/App.tsx",
            "src/App.jsx",
            "pages/index.tsx",
            "pages/index.vue",
            "src/pages/index.astro"
        ]

        for rel in priority_files:
            candidate = os.path.join(project_path, rel)
            if os.path.isfile(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    return FetchResult(
                        success=True,
                        content=content,
                        status_code=200,
                        final_url=os.path.abspath(candidate),
                        content_length=len(content),
                        is_local=True
                    )
                except Exception:
                    pass

        # Fallback: find the first .html or .tsx file
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build", ".next", "__pycache__"}]
            for file in files:
                if file.endswith(".html") or file.endswith(".tsx") or file.endswith(".jsx"):
                    full = os.path.join(root, file)
                    try:
                        with open(full, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        return FetchResult(
                            success=True,
                            content=content,
                            status_code=200,
                            final_url=os.path.abspath(full),
                            content_length=len(content),
                            is_local=True
                        )
                    except Exception:
                        pass

        return FetchResult(
            success=False,
            error=f"No suitable HTML or frontend template found in directory '{project_path}'."
        )
