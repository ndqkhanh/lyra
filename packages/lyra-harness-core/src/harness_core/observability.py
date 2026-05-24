"""Minimal observability: structured spans + in-memory metrics.

Writes JSONL spans to ``HARNESS_TRACE_FILE`` if set, else to an in-memory buffer
available via ``Tracer.spans``. Not OpenTelemetry — just enough structure to test.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional


@dataclass
class Span:
    name: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    start_ns: int = field(default_factory=time.perf_counter_ns)
    end_ns: Optional[int] = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_ns is None:
            return None
        return (self.end_ns - self.start_ns) / 1e6

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
        }


class Tracer:
    def __init__(self, trace_file: Optional[str] = None) -> None:
        self.trace_file = trace_file or os.environ.get("HARNESS_TRACE_FILE")
        self.spans: list[Span] = []
        self._stack: list[str] = []
        self.metrics: dict[str, int] = {}

    def incr(self, metric: str, amount: int = 1) -> None:
        self.metrics[metric] = self.metrics.get(metric, 0) + amount

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Iterator[Span]:
        parent = self._stack[-1] if self._stack else None
        sp = Span(name=name, parent_id=parent, attributes=dict(attrs))
        self._stack.append(sp.span_id)
        try:
            yield sp
        finally:
            sp.end_ns = time.perf_counter_ns()
            self._stack.pop()
            self.spans.append(sp)
            if self.trace_file:
                try:
                    with open(self.trace_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(sp.to_dict()) + "\n")
                except OSError:
                    pass  # best-effort
