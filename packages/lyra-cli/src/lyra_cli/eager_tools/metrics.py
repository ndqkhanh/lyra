"""Metrics and observability for eager tools."""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SealMetrics:
    """Metrics for seal detection and tool execution."""

    seal_detected_ms: list[float] = field(default_factory=list)
    tool_dispatch_ms: list[float] = field(default_factory=list)
    tool_complete_ms: list[float] = field(default_factory=list)

    def record_seal(self, elapsed_ms: float) -> None:
        """Record time from stream start to seal detection."""
        self.seal_detected_ms.append(elapsed_ms)

    def record_dispatch(self, elapsed_ms: float) -> None:
        """Record time from seal to tool dispatch."""
        self.tool_dispatch_ms.append(elapsed_ms)

    def record_completion(self, elapsed_ms: float) -> None:
        """Record tool execution duration."""
        self.tool_complete_ms.append(elapsed_ms)

    def overlap_savings(self, sequential_ms: float, eager_ms: float) -> float:
        """Calculate time saved by eager execution."""
        return sequential_ms - eager_ms

    def summary(self) -> dict:
        """Return metrics summary."""
        return {
            "seals_detected": len(self.seal_detected_ms),
            "avg_seal_ms": sum(self.seal_detected_ms) / len(self.seal_detected_ms) if self.seal_detected_ms else 0,
            "avg_dispatch_ms": sum(self.tool_dispatch_ms) / len(self.tool_dispatch_ms) if self.tool_dispatch_ms else 0,
            "avg_complete_ms": sum(self.tool_complete_ms) / len(self.tool_complete_ms) if self.tool_complete_ms else 0,
        }


class MetricsCollector:
    """Collect and track eager tools metrics."""

    def __init__(self):
        self.metrics = SealMetrics()
        self.stream_start: Optional[float] = None
        self.last_seal: Optional[float] = None

    def start_stream(self) -> None:
        """Mark stream start time."""
        self.stream_start = time.perf_counter()

    def on_seal_detected(self, tool_id: str) -> None:
        """Record seal detection event."""
        if self.stream_start is None:
            return

        now = time.perf_counter()
        elapsed_ms = (now - self.stream_start) * 1000
        self.metrics.record_seal(elapsed_ms)
        self.last_seal = now

    def on_tool_dispatched(self, tool_id: str) -> None:
        """Record tool dispatch event."""
        if self.last_seal is None:
            return

        now = time.perf_counter()
        elapsed_ms = (now - self.last_seal) * 1000
        self.metrics.record_dispatch(elapsed_ms)

    def on_tool_completed(self, tool_id: str, duration_ms: float) -> None:
        """Record tool completion event."""
        self.metrics.record_completion(duration_ms)

    def get_summary(self) -> dict:
        """Get metrics summary."""
        return self.metrics.summary()
