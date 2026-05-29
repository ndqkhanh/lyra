"""Standardized health signal format consumed by the health monitor."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class SignalSeverity(str, Enum):
    OK = "ok"
    WARN = "warn"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class SignalSource(str, Enum):
    MEMORY = "memory"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    TOKEN_USAGE = "token_usage"
    TOOL_SUCCESS = "tool_success"
    SAFETY_TRIP = "safety_trip"
    CRASH_LOOP = "crash_loop"
    RECOVERY = "recovery"


@dataclass(frozen=True)
class HealthSignal:
    """A single health observation from a specific source at a point in time.

    Every signal carries a numeric ``value`` whose interpretation depends on
    ``source`` and ``metric``. For example, ``ERROR_RATE`` with ``value=0.15``
    means a 15 % error rate, while ``LATENCY`` with ``value=2.3`` means 2.3 s
    average response time.
    """

    source: SignalSource
    severity: SignalSeverity
    value: float
    metric: str = "default"
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""
    session_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "severity": self.severity.value,
            "value": self.value,
            "metric": self.metric,
            "message": self.message,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> HealthSignal:
        _val = payload["value"]
        value: float = float(_val) if isinstance(_val, (int, float)) else 0.0

        _ts = payload.get("timestamp", time.time())
        timestamp: float = float(_ts) if isinstance(_ts, (int, float)) else time.time()

        return cls(
            source=SignalSource(str(payload["source"])),
            severity=SignalSeverity(str(payload["severity"])),
            value=value,
            metric=str(payload.get("metric", "default")),
            message=str(payload.get("message", "")),
            timestamp=timestamp,
            agent_id=str(payload.get("agent_id", "")),
            session_id=str(payload.get("session_id", "")),
        )
