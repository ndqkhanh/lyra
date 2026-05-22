"""Trace Inspector — inspect, replay, and debug agent execution traces."""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["TraceEvent", "AgentTrace", "TraceInspector"]

@dataclass
class TraceEvent: step: int; action: str; duration_ms: float; success: bool; details: str = ""

@dataclass
class AgentTrace: agent_id: str; events: list[TraceEvent]; total_duration_ms: float = 0.0; created_at: float = 0.0

class TraceInspector:
    def __init__(self): self.traces: dict[str, AgentTrace] = {}; self._counter = 0

    def start_trace(self, agent_id: str) -> str:
        self._counter += 1; trace_id = f"trace_{self._counter}"
        self.traces[trace_id] = AgentTrace(agent_id=agent_id, events=[], created_at=time.time()); return trace_id

    def record_event(self, trace_id: str, action: str, duration_ms: float, success: bool, details: str = "") -> None:
        t = self.traces.get(trace_id)
        if not t: return
        event = TraceEvent(step=len(t.events)+1, action=action, duration_ms=duration_ms, success=success, details=details)
        t.events.append(event); t.total_duration_ms += duration_ms

    def get_slowest_steps(self, trace_id: str, n: int = 3) -> list[TraceEvent]:
        t = self.traces.get(trace_id)
        if not t: return []
        return sorted(t.events, key=lambda e: -e.duration_ms)[:n]

    def get_failure_rate(self, trace_id: str) -> float:
        t = self.traces.get(trace_id)
        if not t or not t.events: return 0.0
        return sum(1 for e in t.events if not e.success) / len(t.events)

    def replay(self, trace_id: str) -> list[TraceEvent]:
        t = self.traces.get(trace_id)
        return t.events if t else []

    @property
    def stats(self) -> dict: return {"traces": len(self.traces)}
