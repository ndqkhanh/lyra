from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .exceptions import TraceError


class TraceEventType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    DECISION = "decision"
    ESCALATION = "escalation"
    ERROR = "error"


@dataclass(frozen=True)
class TraceEvent:
    event_type: TraceEventType
    timestamp: datetime
    data: dict[str, Any]
    system: str  # "system_i", "system_ii", or "system_iii"

    def __post_init__(self) -> None:
        valid_systems = {"system_i", "system_ii", "system_iii"}
        if self.system not in valid_systems:
            raise TraceError(
                f"system must be one of {valid_systems}, got {self.system!r}"
            )


@dataclass(frozen=True)
class FullTrace:
    events: tuple[TraceEvent, ...]
    start_time: datetime
    end_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ReasoningTracer:
    """Captures full reasoning traces with structured events.

    Each reasoning flow produces a trace that can be exported in JSON or
    Mermaid format for analysis and debugging.
    """

    def __init__(self) -> None:
        self._traces: dict[str, list[TraceEvent]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def start_trace(self, context: str) -> str:
        trace_id = str(uuid.uuid4())
        self._traces[trace_id] = []
        self._metadata[trace_id] = {
            "context": context,
            "start_time": datetime.now(timezone.utc),
            "system": "unknown",
        }
        return trace_id

    def set_metadata(self, trace_id: str, **kwargs: Any) -> None:
        if trace_id not in self._metadata:
            raise TraceError(f"trace {trace_id!r} not found")
        self._metadata[trace_id].update(kwargs)

    def record_event(self, trace_id: str, event: TraceEvent) -> None:
        if trace_id not in self._traces:
            raise TraceError(f"trace {trace_id!r} not found")
        self._traces[trace_id].append(event)

    def get_full_trace(self, trace_id: str) -> FullTrace:
        if trace_id not in self._traces:
            raise TraceError(f"trace {trace_id!r} not found")
        events = tuple(self._traces[trace_id])
        meta = self._metadata.get(trace_id, {})
        start = meta.get("start_time", datetime.now(timezone.utc))
        return FullTrace(events=events, start_time=start, metadata=meta)

    def export_trace(self, trace_id: str, fmt: str = "json") -> str:
        trace = self.get_full_trace(trace_id)
        if fmt == "json":
            return self._export_json(trace)
        if fmt == "mermaid":
            return self._export_mermaid(trace)
        raise TraceError(f"unsupported export format: {fmt!r}")

    def _export_json(self, trace: FullTrace) -> str:
        def _serialise(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            return obj

        raw = {
            "start_time": trace.start_time,
            "end_time": trace.end_time,
            "metadata": trace.metadata,
            "events": [
                {
                    "event_type": e.event_type,
                    "timestamp": e.timestamp,
                    "data": e.data,
                    "system": e.system,
                }
                for e in trace.events
            ],
        }
        return json.dumps(raw, default=_serialise, indent=2)

    def _export_mermaid(self, trace: FullTrace) -> str:
        lines: list[str] = ["%% Reasoning Trace", "sequenceDiagram", "    participant User"]
        seen_systems: set[str] = set()
        for e in trace.events:
            if e.system not in seen_systems:
                lines.append(f"    participant {e.system}")
                seen_systems.add(e.system)

        for i, e in enumerate(trace.events):
            summary = str(e.data.get("summary", e.event_type.value))
            lines.append(f"    {e.system}->>{e.system}: {i}: {summary}")
        lines.append(f"    User->>User: end")
        return "\n".join(lines)

    def trace_stats(self, trace_id: str) -> dict[str, Any]:
        trace = self.get_full_trace(trace_id)
        system_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for e in trace.events:
            system_counts[e.system] = system_counts.get(e.system, 0) + 1
            type_counts[e.event_type.value] = type_counts.get(e.event_type.value, 0) + 1

        return {
            "total_events": len(trace.events),
            "by_system": system_counts,
            "by_type": type_counts,
            "duration_seconds": (
                (trace.end_time - trace.start_time).total_seconds()
                if trace.end_time
                else None
            ),
            "system_count": len(system_counts),
            "escalation_count": type_counts.get("escalation", 0),
        }
