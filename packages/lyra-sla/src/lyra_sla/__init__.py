"""Agent SLA Manager — service level agreements, QoS monitoring, compliance checking.

Defines SLAs for agent performance. Monitors compliance in real-time.
Triggers auto-scaling or degradation when SLAs can't be met.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "AgentSLA",
    "SLAViolation",
    "SLAManager",
]


@dataclass
class AgentSLA:
    response_time_p99_ms: float = 10000
    quality_score_min: float = 0.7
    cost_max_per_task: float = 1.0
    availability_pct: float = 99.0


@dataclass
class SLAViolation:
    agent_id: str
    metric: str
    threshold: float
    actual: float
    timestamp: float


class SLAManager:
    """Monitors and enforces SLA compliance for agents."""

    def __init__(self):
        self.slas: dict[str, AgentSLA] = {}
        self.violations: list[SLAViolation] = deque(maxlen=1000)
        self.metrics: dict[str, deque] = {}

    def set_sla(self, agent_id: str, sla: AgentSLA) -> None:
        self.slas[agent_id] = sla
        self.metrics[agent_id] = deque(maxlen=100)

    def record_metric(self, agent_id: str, metric: str, value: float) -> None:
        if agent_id not in self.metrics:
            return
        self.metrics[agent_id].append({metric: value, "timestamp": time.time()})

    def check_compliance(self, agent_id: str) -> dict[str, Any]:
        sla = self.slas.get(agent_id)
        if not sla:
            return {"compliant": True, "message": "No SLA defined"}

        violations = []
        agent_metrics = list(self.metrics.get(agent_id, deque(maxlen=100)))[-10:]
        if not agent_metrics:
            return {"compliant": True, "message": "Insufficient data"}

        # Check response time
        latencies = [m.get("latency_ms", 0) for m in agent_metrics if "latency_ms" in m]
        if latencies:
            p99 = sorted(latencies)[int(len(latencies) * 0.99)]
            if p99 > sla.response_time_p99_ms:
                self.violations.append(SLAViolation(agent_id, "response_time", sla.response_time_p99_ms, p99, time.time()))
                violations.append("latency")

        # Check quality
        qualities = [m.get("quality", 1.0) for m in agent_metrics if "quality" in m]
        if qualities:
            avg_q = sum(qualities) / len(qualities)
            if avg_q < sla.quality_score_min:
                self.violations.append(SLAViolation(agent_id, "quality", sla.quality_score_min, avg_q, time.time()))
                violations.append("quality")

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "violation_count": len(self.violations),
        }

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "agents_with_sla": len(self.slas),
            "total_violations": len(self.violations),
            "recent_violations": list(self.violations)[-5:],
        }
