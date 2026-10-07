"""Prometheus-compatible application metrics engine with strict cardinality control."""

import bisect
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# Restrict allowed label dimensions to prevent unbounded cardinality
ALLOWED_LABEL_KEYS = {
    "dataset",
    "status",
    "endpoint",
    "decision",
    "severity",
    "stage",
    "provider",
    "model",
    "http_status_family",
}


class Counter:
    """A cumulative counter metric that only increases."""

    def __init__(self, name: str, description: str, label_names: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = sorted(label_names or [])
        self._values: Dict[Tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, **labels: str) -> None:
        """Increment counter with specified bounded labels."""
        if value < 0:
            return
        key = self._format_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def get(self, **labels: str) -> float:
        """Get current counter value for labels."""
        key = self._format_key(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def _format_key(self, labels: Dict[str, str]) -> Tuple[str, ...]:
        filtered = {k: str(v) for k, v in labels.items() if k in self.label_names and k in ALLOWED_LABEL_KEYS}
        return tuple(f'{k}="{filtered.get(k, "")}"' for k in self.label_names)

    def collect(self) -> List[str]:
        """Format metric into Prometheus exposition format lines."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            if not self._values:
                if not self.label_names:
                    lines.append(f"{self.name} 0.0")
            else:
                for label_tuple, val in sorted(self._values.items()):
                    if label_tuple:
                        lbl_str = "{" + ",".join(label_tuple) + "}"
                        lines.append(f"{self.name}{lbl_str} {val}")
                    else:
                        lines.append(f"{self.name} {val}")
        return lines


class Gauge:
    """A gauge metric representing a value that can go up or down."""

    def __init__(self, name: str, description: str, label_names: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = sorted(label_names or [])
        self._values: Dict[Tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **labels: str) -> None:
        """Set gauge value."""
        key = self._format_key(labels)
        with self._lock:
            self._values[key] = float(value)

    def get(self, **labels: str) -> float:
        """Get gauge value."""
        key = self._format_key(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def _format_key(self, labels: Dict[str, str]) -> Tuple[str, ...]:
        filtered = {k: str(v) for k, v in labels.items() if k in self.label_names and k in ALLOWED_LABEL_KEYS}
        return tuple(f'{k}="{filtered.get(k, "")}"' for k in self.label_names)

    def collect(self) -> List[str]:
        """Format gauge into Prometheus lines."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            if not self._values:
                if not self.label_names:
                    lines.append(f"{self.name} 0.0")
            else:
                for label_tuple, val in sorted(self._values.items()):
                    if label_tuple:
                        lbl_str = "{" + ",".join(label_tuple) + "}"
                        lines.append(f"{self.name}{lbl_str} {val}")
                    else:
                        lines.append(f"{self.name} {val}")
        return lines


class Histogram:
    """Tracks frequency distributions in fixed buckets."""

    def __init__(
        self,
        name: str,
        description: str,
        buckets: List[float],
        label_names: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.buckets = sorted(buckets)
        self.label_names = sorted(label_names or [])
        # {key: {"counts": [int], "sum": float, "count": int}}
        self._data: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def observe(self, value: float, **labels: str) -> None:
        """Observe a measured value."""
        val = float(value)
        key = self._format_key(labels)
        with self._lock:
            if key not in self._data:
                self._data[key] = {
                    "counts": [0] * len(self.buckets),
                    "sum": 0.0,
                    "count": 0,
                }
            entry = self._data[key]
            entry["sum"] += val
            entry["count"] += 1
            idx = bisect.bisect_right(self.buckets, val)
            for i in range(idx, len(self.buckets)):
                entry["counts"][i] += 1

    def _format_key(self, labels: Dict[str, str]) -> Tuple[str, ...]:
        filtered = {k: str(v) for k, v in labels.items() if k in self.label_names and k in ALLOWED_LABEL_KEYS}
        return tuple(f'{k}="{filtered.get(k, "")}"' for k in self.label_names)

    def collect(self) -> List[str]:
        """Format histogram into Prometheus lines."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for key, entry in sorted(self._data.items()):
                base_lbls = list(key)
                for b_val, b_count in zip(self.buckets, entry["counts"]):
                    b_str = f'le="{b_val}"'
                    lbl_parts = base_lbls + [b_str]
                    lines.append(f'{self.name}_bucket{{{",".join(lbl_parts)}}} {b_count}')
                inf_lbl_parts = base_lbls + ['le="+Inf"']
                lines.append(f'{self.name}_bucket{{{",".join(inf_lbl_parts)}}} {entry["count"]}')
                lbl_suffix = f'{{{",".join(base_lbls)}}}' if base_lbls else ""
                lines.append(f"{self.name}_sum{lbl_suffix} {round(entry['sum'], 4)}")
                lines.append(f"{self.name}_count{lbl_suffix} {entry['count']}")
        return lines


class MetricsRegistry:
    """Registry maintaining application metrics and rendering /metrics text."""

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._init_standard_metrics()

    def _init_standard_metrics(self) -> None:
        """Initialize all standard Phase 13 operational metrics."""
        # 1. HTTP Request Metrics
        self.create_counter("request_count", "Total HTTP requests received", ["endpoint", "status"])
        self.create_counter("request_errors", "Total HTTP request errors", ["endpoint", "status"])
        self.create_counter("http_requests_by_family", "HTTP requests grouped by status code family", ["http_status_family"])
        self.create_histogram(
            "request_latency",
            "HTTP request latency distribution in ms",
            [5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0],
            ["endpoint"],
        )

        # 2. Pipeline Analysis Metrics
        self.create_counter("analysis_count", "Total log triage analysis requests", ["dataset", "status"])
        self.create_counter("analysis_errors", "Total log triage analysis errors", ["dataset", "stage"])
        self.create_histogram(
            "analysis_latency",
            "Total analysis pipeline latency in ms",
            [10.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0],
            ["dataset"],
        )

        # 3. Pipeline Stage Counters & Failures
        self.create_counter("ingestion_count", "Total ingestion operations", ["dataset", "status"])
        self.create_counter("ingestion_failures", "Total ingestion failures", ["dataset"])

        self.create_counter("scoring_count", "Total scoring operations", ["dataset", "status"])
        self.create_counter("scoring_failures", "Total scoring failures", ["dataset"])

        self.create_counter("auto_clear_count", "Total windows auto-cleared by selective gate", ["dataset"])
        self.create_counter("escalation_count", "Total windows escalated by selective gate", ["dataset"])
        self.create_gauge("escalation_rate", "Observed escalation rate ratio (escalated / total)", ["dataset"])

        self.create_counter("retrieval_count", "Total retrieval operations", ["dataset", "status"])
        self.create_counter("retrieval_failures", "Total retrieval failures", ["dataset"])

        self.create_counter("reranking_count", "Total MMR reranking operations", ["dataset", "status"])

        self.create_counter("provenance_count", "Total provenance validations", ["dataset", "status"])
        self.create_counter("provenance_verified_total", "Total verified citations", ["dataset"])
        self.create_counter("provenance_rejected_total", "Total rejected citations", ["dataset"])
        self.create_counter("citation_validation_failures", "Total citation validation failures", ["dataset"])

        self.create_counter("reasoning_count", "Total deterministic reasoning assessments", ["dataset", "status"])
        self.create_counter("reasoning_failures", "Total reasoning failures", ["dataset"])
        self.create_counter("decisions_total", "Triage decisions categorized by outcome", ["dataset", "decision"])

        self.create_counter("explanation_count", "Total LLM explanations executed", ["dataset", "status"])
        self.create_counter("explanation_generated_total", "Total explanations generated", ["dataset"])
        self.create_counter("explanation_failed_total", "Total explanations failed", ["dataset"])
        self.create_counter("explanation_skipped_total", "Total explanations skipped", ["dataset"])
        self.create_counter("faithfulness_verified_total", "Total faithful explanations", ["dataset"])
        self.create_counter("faithfulness_failed_total", "Total unfaithful explanations", ["dataset"])

        # 4. Security & Hardening Metrics (Phase 14)
        self.create_counter("authentication_failures_total", "Total failed authentication attempts")
        self.create_counter("authorization_denials_total", "Total authorization rejections")
        self.create_counter("rate_limit_exceeded_total", "Total requests rejected due to rate limits")
        self.create_counter("request_validation_failures_total", "Total input validation rejections", ["endpoint"])

        # 5. LLM Operational Metrics
        self.create_counter("llm_requests_total", "Total LLM API requests invoked", ["provider", "status"])
        self.create_counter("llm_success_total", "Total successful LLM API calls", ["provider"])
        self.create_counter("llm_failure_total", "Total failed LLM API calls", ["provider"])
        self.create_counter("llm_timeout_total", "Total timed-out LLM API calls", ["provider"])
        self.create_counter("llm_calls_by_dataset", "Total LLM invocations by dataset", ["dataset"])
        self.create_histogram(
            "llm_latency",
            "LLM provider response latency in ms",
            [50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 15000.0],
            ["provider"],
        )

        # 5. Pipeline Latency Breakdown Histograms
        for stage in ("retrieval", "reranking", "provenance", "reasoning", "explanation"):
            self.create_histogram(
                f"{stage}_latency",
                f"Latency of {stage} pipeline stage in ms",
                [1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0],
                ["dataset"],
            )

    def create_counter(self, name: str, description: str, label_names: Optional[List[str]] = None) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description, label_names)
            return self._counters[name]

    def create_gauge(self, name: str, description: str, label_names: Optional[List[str]] = None) -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description, label_names)
            return self._gauges[name]

    def create_histogram(
        self,
        name: str,
        description: str,
        buckets: List[float],
        label_names: Optional[List[str]] = None,
    ) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, buckets, label_names)
            return self._histograms[name]

    def get_counter(self, name: str) -> Optional[Counter]:
        return self._counters.get(name)

    def get_gauge(self, name: str) -> Optional[Gauge]:
        return self._gauges.get(name)

    def get_histogram(self, name: str) -> Optional[Histogram]:
        return self._histograms.get(name)

    def generate_exposition(self) -> str:
        """Render all metrics into standard Prometheus text format."""
        lines: List[str] = []
        with self._lock:
            for c in self._counters.values():
                lines.extend(c.collect())
            for g in self._gauges.values():
                lines.extend(g.collect())
            for h in self._histograms.values():
                lines.extend(h.collect())
        return "\n".join(lines) + "\n"

    def reset_all(self) -> None:
        """Clear all metrics values (used for testing)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
        self._init_standard_metrics()


_GLOBAL_REGISTRY: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Retrieve global MetricsRegistry instance."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = MetricsRegistry()
    return _GLOBAL_REGISTRY
