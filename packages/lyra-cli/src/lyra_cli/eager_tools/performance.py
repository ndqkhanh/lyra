"""Performance metrics for eager tools."""

import time
from dataclasses import dataclass, field


@dataclass
class EagerMetrics:
    """Performance metrics for eager tool dispatch."""

    # Seal detection
    seals_detected: int = 0
    seals_dispatched: int = 0
    seal_latency_ms: list[float] = field(default_factory=list)

    # Tool execution
    tools_executed: int = 0
    tool_durations_ms: dict[str, list[float]] = field(default_factory=dict)

    # Stream timing
    stream_start: float = 0.0
    stream_end: float = 0.0

    # Speedup calculation
    traditional_latency_ms: float = 0.0
    eager_latency_ms: float = 0.0

    def record_seal(self, latency_ms: float, dispatched: bool) -> None:
        """Record seal detection."""
        self.seals_detected += 1
        if dispatched:
            self.seals_dispatched += 1
        self.seal_latency_ms.append(latency_ms)

    def record_tool_execution(self, tool_name: str, duration_ms: float) -> None:
        """Record tool execution."""
        self.tools_executed += 1
        if tool_name not in self.tool_durations_ms:
            self.tool_durations_ms[tool_name] = []
        self.tool_durations_ms[tool_name].append(duration_ms)

    def start_stream(self) -> None:
        """Mark stream start."""
        self.stream_start = time.perf_counter()

    def end_stream(self) -> None:
        """Mark stream end."""
        self.stream_end = time.perf_counter()

    def calculate_speedup(self) -> float:
        """Calculate speedup from eager dispatch.

        Traditional: stream_duration + max(tool_durations)
        Eager: max(stream_duration, max(tool_durations))
        Speedup: traditional / eager
        """
        if not self.tool_durations_ms:
            return 1.0

        stream_duration_ms = (self.stream_end - self.stream_start) * 1000

        # Find max tool duration
        max_tool_duration = 0.0
        for durations in self.tool_durations_ms.values():
            if durations:
                max_tool_duration = max(max_tool_duration, max(durations))

        # Traditional: sequential
        self.traditional_latency_ms = stream_duration_ms + max_tool_duration

        # Eager: parallel
        self.eager_latency_ms = max(stream_duration_ms, max_tool_duration)

        if self.eager_latency_ms > 0:
            return self.traditional_latency_ms / self.eager_latency_ms
        return 1.0

    def get_summary(self) -> dict:
        """Get metrics summary."""
        speedup = self.calculate_speedup()

        return {
            "seals_detected": self.seals_detected,
            "seals_dispatched": self.seals_dispatched,
            "dispatch_rate": (
                self.seals_dispatched / self.seals_detected
                if self.seals_detected > 0
                else 0.0
            ),
            "avg_seal_latency_ms": (
                sum(self.seal_latency_ms) / len(self.seal_latency_ms)
                if self.seal_latency_ms
                else 0.0
            ),
            "tools_executed": self.tools_executed,
            "stream_duration_ms": (self.stream_end - self.stream_start) * 1000,
            "traditional_latency_ms": self.traditional_latency_ms,
            "eager_latency_ms": self.eager_latency_ms,
            "speedup": speedup,
            "cost_reduction_pct": (1 - 1 / speedup) * 100 if speedup > 1 else 0.0,
        }
