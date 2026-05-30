"""Trace Command — user-facing `/trace` CLI command for distributed trace inspection.

Provides trace initiation, span recording, timeline generation, span filtering,
and latency breakdown for debugging distributed agent workflows.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SpanDetail:
    span_id: str
    trace_id: str
    operation: str
    duration_ms: float
    start_time: float = 0.0
    error: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def has_error(self) -> bool:
        return bool(self.error)


@dataclass
class TraceFilter:
    min_duration_ms: float | None = None
    has_error: bool | None = None
    operation_prefix: str | None = None


@dataclass(frozen=True)
class TraceTimeline:
    trace_id: str
    spans: tuple[SpanDetail, ...]
    total_duration_ms: float


class TraceCommand:
    """User-facing `/trace` command for inspecting distributed traces.

    Records spans, generates timelines, filters by duration/error/operation,
    and provides latency breakdowns for performance debugging.

    Usage::

        cmd = TraceCommand()
        trace_id = cmd.start_trace(operation="workflow.run")
        cmd.add_span(trace_id=trace_id, operation="agent.execute", duration_ms=100.0)
        timeline = cmd.get_trace_timeline(trace_id)
        print(f"Total duration: {timeline.total_duration_ms}ms")
    """

    def __init__(self) -> None:
        self._spans: dict[str, SpanDetail] = {}
        self._traces: dict[str, list[str]] = {}  # trace_id → [span_ids]

    @property
    def trace_count(self) -> int:
        return len(self._traces)

    def start_trace(self, operation: str) -> str:
        _ = operation
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        self._traces[trace_id] = []
        return trace_id

    def add_span(
        self,
        trace_id: str,
        operation: str,
        duration_ms: float,
        error: str = "",
        tags: dict[str, str] | None = None,
    ) -> str:
        span_id = f"span-{uuid.uuid4().hex[:12]}"
        span = SpanDetail(
            span_id=span_id,
            trace_id=trace_id,
            operation=operation,
            duration_ms=duration_ms,
            start_time=time.monotonic(),
            error=error,
            tags=tags or {},
        )
        self._spans[span_id] = span
        if trace_id in self._traces:
            self._traces[trace_id].append(span_id)
        return span_id

    def get_span(self, span_id: str) -> SpanDetail | None:
        return self._spans.get(span_id)

    def get_trace_timeline(self, trace_id: str) -> TraceTimeline | None:
        span_ids = self._traces.get(trace_id)
        if span_ids is None:
            return None
        spans = tuple(
            self._spans[sid] for sid in span_ids if sid in self._spans
        )
        total = sum(s.duration_ms for s in spans)
        return TraceTimeline(trace_id=trace_id, spans=spans, total_duration_ms=total)

    def filter_spans(self, filter_: TraceFilter) -> list[SpanDetail]:
        results = list(self._spans.values())
        if filter_.min_duration_ms is not None:
            results = [s for s in results if s.duration_ms >= filter_.min_duration_ms]
        if filter_.has_error is not None:
            if filter_.has_error:
                results = [s for s in results if s.has_error]
            else:
                results = [s for s in results if not s.has_error]
        if filter_.operation_prefix is not None:
            prefix = filter_.operation_prefix
            results = [s for s in results if s.operation.startswith(prefix)]
        return results

    def get_span_breakdown(self, trace_id: str) -> dict[str, Any]:
        span_ids = self._traces.get(trace_id, [])
        spans = [self._spans[sid] for sid in span_ids if sid in self._spans]
        if not spans:
            return {"total_duration_ms": 0, "span_count": 0}
        total = sum(s.duration_ms for s in spans)
        by_operation: dict[str, float] = {}
        for s in spans:
            by_operation[s.operation] = by_operation.get(s.operation, 0) + s.duration_ms
        return {
            "total_duration_ms": total,
            "span_count": len(spans),
            "by_operation": by_operation,
            "slowest_span": max(spans, key=lambda s: s.duration_ms).operation,
            "error_spans": sum(1 for s in spans if s.has_error),
        }

    def list_traces(self) -> list[str]:
        return sorted(self._traces.keys())

    def reset(self) -> None:
        self._spans.clear()
        self._traces.clear()
