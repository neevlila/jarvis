"""
Performance Intelligence Engine for J.A.R.V.I.S.

Tracks real-time telemetry, latency breakdowns, tool success rates,
resource utilization, and detects performance anomalies or degradation.
"""

import time
from typing import Dict, List, Any, Optional, Callable
from collections import deque

from intelligence.models import PerformanceMetric, PerformanceSnapshot


class PerformanceIntelligence:
    """
    Self-monitoring and health analytics engine for J.A.R.V.I.S.
    """

    def __init__(
        self,
        max_history: int = 100,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.log_callback = log_callback

    def _log(self, stage: str, message: str):
        formatted = f"[{stage}] {message}"
        print(formatted)
        if self.log_callback:
            try:
                self.log_callback(stage, message)
            except Exception:
                pass

    def record_metric(
        self,
        operation: str,
        latency_ms: float,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> PerformanceMetric:
        """
        Records an observed operation execution with its duration and outcome.
        """
        metric = PerformanceMetric(
            operation=operation,
            latency_ms=max(0.1, latency_ms),
            success=success,
            timestamp=time.time(),
            details=details or {}
        )
        self.history.append(metric)
        return metric

    def get_snapshot(self) -> PerformanceSnapshot:
        """
        Computes aggregate statistics, success rates, latency averages, and anomaly flags.
        """
        if not self.history:
            return PerformanceSnapshot(
                avg_response_ms=0.0,
                decision_ms=0.0,
                perception_ms=0.0,
                ocr_ms=0.0,
                execution_ms=0.0,
                verification_ms=0.0,
                memory_retrieval_ms=0.0,
                tool_success_rate=100.0,
                ai_failure_rate=0.0,
                total_operations=0,
                cpu_percent=0.0,
                ram_percent=0.0,
                anomalies=[]
            )

        op_latencies: Dict[str, List[float]] = {}
        successful_ops = 0
        ai_failures = 0
        total_ops = len(self.history)

        for m in self.history:
            op_latencies.setdefault(m.operation, []).append(m.latency_ms)
            if m.success:
                successful_ops += 1
            else:
                if "ai" in m.operation.lower() or "llm" in m.operation.lower():
                    ai_failures += 1

        def _avg(op_name: str) -> float:
            # Matches exact or partial operation names
            vals: List[float] = []
            for k, l in op_latencies.items():
                if op_name.lower() in k.lower():
                    vals.extend(l)
            return (sum(vals) / len(vals)) if vals else 0.0

        all_latencies = [m.latency_ms for m in self.history]
        overall_avg = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0

        tool_success_rate = (successful_ops / total_ops) * 100.0 if total_ops else 100.0
        ai_failure_rate = (ai_failures / total_ops) * 100.0 if total_ops else 0.0

        # Measure host resource utilization
        cpu_val = 0.0
        ram_val = 0.0
        try:
            import psutil
            cpu_val = psutil.cpu_percent(interval=None)
            ram_val = psutil.virtual_memory().percent
        except Exception:
            pass

        # Anomaly detection
        anomalies: List[str] = []
        
        # Check for consecutive failures
        recent_5 = list(self.history)[-5:]
        consecutive_failures = 0
        for r in reversed(recent_5):
            if not r.success:
                consecutive_failures += 1
            else:
                break
        if consecutive_failures >= 3:
            anomalies.append(f"High Error Rate: {consecutive_failures} consecutive operation failures detected.")

        # Check for latency spike
        ocr_avg = _avg("ocr")
        if ocr_avg > 1500.0:
            anomalies.append(f"OCR Latency Degraded: Average {ocr_avg:.0f}ms exceeds nominal threshold.")

        llm_avg = _avg("llm") or _avg("chat") or _avg("idea")
        if llm_avg > 8000.0:
            anomalies.append(f"LLM API Latency High: Average {llm_avg:.0f}ms observed.")

        snapshot = PerformanceSnapshot(
            avg_response_ms=overall_avg,
            decision_ms=_avg("decision"),
            perception_ms=_avg("perception"),
            ocr_ms=ocr_avg,
            execution_ms=_avg("execution") or _avg("action"),
            verification_ms=_avg("verification") or _avg("verify"),
            memory_retrieval_ms=_avg("memory"),
            tool_success_rate=tool_success_rate,
            ai_failure_rate=ai_failure_rate,
            total_operations=total_ops,
            cpu_percent=cpu_val,
            ram_percent=ram_val,
            anomalies=anomalies
        )

        return snapshot
