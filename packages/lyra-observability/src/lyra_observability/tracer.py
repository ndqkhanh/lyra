"""Tracer — span-based distributed tracing with async context manager support.

Provides Span dataclass for capturing execution context and a Tracer class
that manages span creation, nesting, and retrieval.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any


@dataclass(frozen=True)
class Span:
    """A single traced operation.

    Attributes:
        span_id: Unique identifier for this span.
        parent_id: Span ID of the parent span, or None for root spans.
        name: Human-readable operation name.
        start_time: Unix timestamp when the span started.
        end_time: Unix timestamp when the span ended, or None if not ended.
        duration: Duration in seconds, or None if not ended.
        metadata: Arbitrary key-value context attached to the span.
        error: Error message if the span captured an exception, or None.
    """

    span_id: str
    parent_id: str | None
    name: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class _TraceContext:
    """Async context manager returned by Tracer.trace()."""

    def __init__(
        self,
        tracer: Tracer,
        span_id: str,
        parent_id: str | None,
        name: str,
        start_time: float,
        metadata: dict[str, Any],
    ) -> None:
        self._tracer = tracer
        self._span_id = span_id
        self._parent_id = parent_id
        self._name = name
        self._start_time = start_time
        self._metadata = metadata

    async def __aenter__(self) -> str:
        return self._span_id

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        end_time = time.time()
        error_msg = str(exc_val) if exc_val else None
        self._tracer._spans.append(
            Span(
                span_id=self._span_id,
                parent_id=self._parent_id,
                name=self._name,
                start_time=self._start_time,
                end_time=end_time,
                duration=end_time - self._start_time,
                metadata=self._metadata,
                error=error_msg,
            )
        )
        self._tracer._stack.pop()


class Tracer:
    """Manages span creation, nesting, and retrieval.

    Maintains a stack of active spans for context propagation and stores
    completed spans for querying via trace trees, recent spans, and stats.
    """

    def __init__(self) -> None:
        self._spans: list[Span] = []
        self._stack: list[str] = []

    @property
    def active_span_id(self) -> str | None:
        """The span ID at the top of the context stack, or None."""
        return self._stack[-1] if self._stack else None

    def trace(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> _TraceContext:
        """Create an async context manager that times a span.

        Args:
            name: Human-readable operation name.
            metadata: Optional key-value context attached to the span.

        Returns:
            An async context manager; yields the new span's span_id.
        """
        span_id = str(uuid.uuid4())
        parent_id = self._stack[-1] if self._stack else None
        start_time = time.time()
        self._stack.append(span_id)
        return _TraceContext(
            self, span_id, parent_id, name, start_time, metadata or {}
        )

    def get_trace_tree(self) -> dict[str, list[dict[str, Any]]]:
        """Return spans organized as a nested tree by parent_id.

        Returns:
            A dict with a single ``"root"`` key containing a list of root
            span trees, each with optional ``"children"`` lists.
        """
        children: dict[str | None, list[dict[str, Any]]] = {}
        for span in self._spans:
            parent = span.parent_id
            if parent not in children:
                children[parent] = []
            children[parent].append(
                {
                    "span_id": span.span_id,
                    "name": span.name,
                    "duration": span.duration,
                    "error": span.error,
                }
            )

        def _build(parent_id: str | None) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for child in children.get(parent_id, []):
                child["children"] = _build(child["span_id"])
                result.append(child)
            return result

        return {"root": _build(None)}

    def get_recent_spans(self, limit: int = 50) -> list[Span]:
        """Return the most recently completed spans.

        Args:
            limit: Maximum number of spans to return.

        Returns:
            List of Span objects, newest first.
        """
        return list(reversed(self._spans))[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about all recorded spans.

        Returns:
            Dict with ``total_spans``, ``error_count``, and ``avg_duration``.
        """
        error_count = sum(1 for s in self._spans if s.error is not None)
        durations = [
            s.duration for s in self._spans if s.duration is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        return {
            "total_spans": len(self._spans),
            "error_count": error_count,
            "avg_duration": avg_duration,
        }
