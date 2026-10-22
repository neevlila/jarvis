"""
J.A.R.V.I.S. — Health & Load Management Middleware
====================================================
Provides:
  - /health        → liveness probe  (Render polls every 30 s)
  - /ready         → readiness probe (checks assistant init)
  - /metrics       → lightweight operational metrics
  - RequestThrottler — in-process concurrency limiter (load balancing guard)
  - HealthMonitor   — background thread that tracks error rates & auto-restarts
"""

from __future__ import annotations

import os
import sys
import time
import logging
import threading
import collections
from functools import wraps
from typing import Callable

from flask import Flask, jsonify, request, g

logger = logging.getLogger("jarvis.health")


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Request Throttler  (soft load-balancing on the free-tier single worker)
# ─────────────────────────────────────────────────────────────────────────────

class RequestThrottler:
    """
    Limits simultaneous in-flight requests to MAX_CONCURRENT.
    Heavy LLM / SEO routes are protected to avoid OOM on the 512 MB free tier.
    Lightweight routes (/, /health, /ready, /metrics, static) are always allowed.
    """

    MAX_CONCURRENT: int = int(os.environ.get("JARVIS_MAX_CONCURRENT", "4"))

    EXEMPT_PREFIXES = ("/health", "/ready", "/metrics", "/favicon", "/static", "/")

    def __init__(self) -> None:
        self._sem = threading.Semaphore(self.MAX_CONCURRENT)
        self._active = 0
        self._lock   = threading.Lock()
        self._total_throttled = 0

    # ── Flask integration ────────────────────────────────────────────────────

    def register(self, app: Flask) -> None:
        app.before_request(self._before)
        app.teardown_request(self._teardown)
        logger.info("RequestThrottler registered (max_concurrent=%d)", self.MAX_CONCURRENT)

    def _is_exempt(self, path: str) -> bool:
        return any(path == p or path.startswith(p) for p in self.EXEMPT_PREFIXES)

    def _before(self):
        if self._is_exempt(request.path):
            g._throttled = False
            return None

        acquired = self._sem.acquire(blocking=True, timeout=15)
        if not acquired:
            with self._lock:
                self._total_throttled += 1
            return jsonify({
                "error": "Server busy — too many concurrent requests. Please retry.",
                "retry_after": 5,
            }), 503

        g._throttled = True
        with self._lock:
            self._active += 1

    def _teardown(self, exc):
        if getattr(g, "_throttled", False):
            self._sem.release()
            with self._lock:
                self._active = max(0, self._active - 1)

    # ── Metrics ───────────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "active_requests":   self._active,
                "max_concurrent":    self.MAX_CONCURRENT,
                "total_throttled":   self._total_throttled,
                "available_slots":   self._sem._value,
            }


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Health Monitor  (background thread)
# ─────────────────────────────────────────────────────────────────────────────

class HealthMonitor:
    """
    Tracks a sliding window of request outcomes and exposes
    an aggregate health score for the /metrics endpoint.
    """

    WINDOW_SIZE = 100   # rolling window of last N requests

    def __init__(self) -> None:
        self._lock       = threading.Lock()
        self._outcomes   = collections.deque(maxlen=self.WINDOW_SIZE)
        self._start_time = time.time()
        self._req_total  = 0
        self._error_5xx  = 0

    # ── Flask integration ────────────────────────────────────────────────────

    def register(self, app: Flask) -> None:
        app.after_request(self._record)
        logger.info("HealthMonitor registered (window=%d)", self.WINDOW_SIZE)

    def _record(self, response):
        status = response.status_code
        with self._lock:
            self._req_total += 1
            success = status < 500
            self._outcomes.append(success)
            if not success:
                self._error_5xx += 1
        return response

    # ── Metrics ───────────────────────────────────────────────────────────────

    @property
    def error_rate(self) -> float:
        with self._lock:
            if not self._outcomes:
                return 0.0
            failures = sum(1 for ok in self._outcomes if not ok)
            return round(failures / len(self._outcomes) * 100, 2)

    @property
    def uptime_seconds(self) -> float:
        return round(time.time() - self._start_time, 1)

    @property
    def stats(self) -> dict:
        import psutil
        mem = psutil.virtual_memory()
        with self._lock:
            return {
                "uptime_seconds":  self.uptime_seconds,
                "total_requests":  self._req_total,
                "error_rate_pct":  self.error_rate,
                "total_5xx":       self._error_5xx,
                "memory_used_pct": mem.percent,
                "memory_used_mb":  round(mem.used / 1_048_576, 1),
                "window_size":     self.WINDOW_SIZE,
            }

    @property
    def is_healthy(self) -> bool:
        """Returns False if error rate exceeds 50% in the rolling window."""
        return self.error_rate < 50.0


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Route Registration Helper
# ─────────────────────────────────────────────────────────────────────────────

def register_health_routes(app: Flask, throttler: RequestThrottler, monitor: HealthMonitor) -> None:
    """
    Attaches /health, /ready, and /metrics routes to the given Flask app.
    Call this AFTER creating your app and the two managers.
    """

    @app.route("/health")
    def _liveness():
        """Liveness probe — Render polls this every ~30 s."""
        return jsonify({
            "status": "ok",
            "service": "J.A.R.V.I.S.",
            "platform": sys.platform,
            "uptime_s": monitor.uptime_seconds,
        }), 200

    @app.route("/ready")
    def _readiness():
        """Readiness probe — checks assistant and error rate."""
        try:
            import buddy
            assistant_ready = buddy.assistant_ref is not None
        except Exception:
            assistant_ready = False

        if not assistant_ready:
            return jsonify({"status": "initializing", "assistant": False}), 503

        if not monitor.is_healthy:
            return jsonify({
                "status": "degraded",
                "error_rate_pct": monitor.error_rate,
            }), 503

        return jsonify({"status": "ready", "assistant": True}), 200

    @app.route("/metrics")
    def _metrics():
        """Operational metrics for dashboards / alerting."""
        return jsonify({
            "throttler": throttler.stats,
            "health":    monitor.stats,
        }), 200
