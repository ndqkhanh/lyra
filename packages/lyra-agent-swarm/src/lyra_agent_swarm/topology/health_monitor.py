"""Health Monitor — agent health probes, heartbeat tracking, and adaptive redundancy.

Implements health monitoring for agent swarms:
  - Per-agent health tracking with configurable thresholds
  - Heartbeat-based liveness detection
  - Gradual degradation: HEALTHY → DEGRADED → UNHEALTHY → DEAD
  - Squad-level health aggregation
  - Adaptive redundancy recommendations
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class HealthStatus(StrEnum):
    """Health status of an agent."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"


@dataclass(frozen=True)
class HealthProbe:
    """Result of a single health probe."""

    agent_id: str
    status: HealthStatus = HealthStatus.HEALTHY
    latency_ms: float = 0.0
    error: str = ""
    probed_at: float = field(default_factory=time.monotonic)


@dataclass
class AgentHealth:
    """Tracked health state for a single agent."""

    agent_id: str
    status: HealthStatus = HealthStatus.HEALTHY
    last_heartbeat: float = 0.0
    consecutive_failures: int = 0
    total_probes: int = 0
    failed_probes: int = 0
    avg_latency_ms: float = 0.0
    max_consecutive_failures: int = 5
    degradation_threshold: int = 2
    squad_id: str | None = None

    def record_probe(
        self,
        status: HealthStatus,
        latency_ms: float = 0.0,
        error: str = "",
    ) -> None:
        """Record a health probe result and update state."""
        self.total_probes += 1
        now = time.monotonic()

        if status == HealthStatus.HEALTHY:
            self.last_heartbeat = now
            self.consecutive_failures = 0
            self.avg_latency_ms = (
                (self.avg_latency_ms * (self.total_probes - 1) + latency_ms)
                / self.total_probes
            )
        else:
            self.consecutive_failures += 1
            self.failed_probes += 1

        self._recalculate_status(error)

    def _recalculate_status(self, error: str = "") -> None:  # noqa: ARG002
        """Recalculate health status based on failure history."""
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.status = HealthStatus.DEAD
        elif self.consecutive_failures >= self.degradation_threshold + 1:
            self.status = HealthStatus.UNHEALTHY
        elif self.consecutive_failures >= self.degradation_threshold:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.HEALTHY


class HealthMonitor:
    """Monitors health across the entire agent swarm.

    Tracks per-agent health, squad-level aggregates, heartbeat
    timeouts, and provides redundancy recommendations.

    Usage::

        hm = HealthMonitor()
        hm.register_agent("agent-1", squad_id="squad-a")
        hm.record_heartbeat("agent-1", latency_ms=5.0)
        squad_health = hm.get_squad_health("squad-a")
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentHealth] = {}

    # ── Properties ───────────────────────────────────────────────

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    # ── Agent Registration ───────────────────────────────────────

    def register_agent(
        self,
        agent_id: str,
        squad_id: str | None = None,
        max_consecutive_failures: int = 5,
    ) -> AgentHealth:
        """Register an agent for health monitoring."""
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' already registered")
        health = AgentHealth(
            agent_id=agent_id,
            squad_id=squad_id,
            max_consecutive_failures=max_consecutive_failures,
        )
        self._agents[agent_id] = health
        return health

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from monitoring."""
        self._agents.pop(agent_id, None)

    def get_health(self, agent_id: str) -> AgentHealth | None:
        """Get health state for an agent."""
        return self._agents.get(agent_id)

    # ── Heartbeat & Probes ───────────────────────────────────────

    def record_heartbeat(
        self,
        agent_id: str,
        latency_ms: float = 0.0,
        status: HealthStatus = HealthStatus.HEALTHY,
        error: str = "",
    ) -> None:
        """Record a heartbeat or health probe from an agent."""
        health = self._agents.get(agent_id)
        if health is None:
            raise ValueError(f"Agent '{agent_id}' not registered")
        health.record_probe(status=status, latency_ms=latency_ms, error=error)

    def check_heartbeat_timeout(
        self,
        timeout_ms: float = 5_000.0,
        now: float | None = None,
    ) -> list[str]:
        """Return agent IDs whose last heartbeat exceeds the timeout.

        These agents are considered potentially dead or unreachable.
        """
        current = now or time.monotonic()
        timeout_sec = timeout_ms / 1000.0
        timed_out: list[str] = []
        for agent_id, health in self._agents.items():
            if health.last_heartbeat > 0 and (
                current - health.last_heartbeat > timeout_sec
            ):
                timed_out.append(agent_id)
        return timed_out

    # ── Squad Health ─────────────────────────────────────────────

    def get_squad_health(self, squad_id: str) -> dict | None:
        """Aggregate health for all agents in a squad."""
        squad_agents = [
            h for h in self._agents.values() if h.squad_id == squad_id
        ]
        if not squad_agents:
            return None

        status_counts: dict[str, int] = defaultdict(int)
        degraded_agents: list[str] = []
        for agent in squad_agents:
            status_counts[agent.status.value] += 1
            if agent.status != HealthStatus.HEALTHY:
                degraded_agents.append(agent.agent_id)

        healthy_count = status_counts.get("healthy", 0)
        return {
            "squad_id": squad_id,
            "agent_count": len(squad_agents),
            "healthy_count": healthy_count,
            "health_ratio": healthy_count / len(squad_agents) if squad_agents else 0.0,
            "degraded_agents": degraded_agents,
            "status_breakdown": dict(status_counts),
        }

    def get_redundancy_recommendation(self, squad_id: str) -> dict | None:
        """Recommend redundancy actions based on squad health."""
        squad_health = self.get_squad_health(squad_id)
        if squad_health is None:
            return None

        health_ratio = squad_health["health_ratio"]
        if health_ratio < 0.5:
            return {
                "action": "replace_squad",
                "severity": "critical",
                "reason": f"Less than 50% healthy agents ({health_ratio:.0%})",
                "squad_id": squad_id,
            }
        if health_ratio < 0.75:
            return {
                "action": "add_redundancy",
                "severity": "warning",
                "reason": f"Less than 75% healthy agents ({health_ratio:.0%})",
                "squad_id": squad_id,
                "recommended_count": max(
                    1, squad_health["agent_count"] - squad_health["healthy_count"]
                ),
            }
        return None

    # ── Status Queries ───────────────────────────────────────────

    def get_status_summary(self) -> dict:
        """Get a summary of health across all agents."""
        status_counts: dict[str, int] = defaultdict(int)
        for health in self._agents.values():
            status_counts[health.status.value] += 1
        return {
            "total": len(self._agents),
            "healthy": status_counts.get("healthy", 0),
            "degraded": status_counts.get("degraded", 0),
            "unhealthy": status_counts.get("unhealthy", 0),
            "dead": status_counts.get("dead", 0),
        }

    def get_degraded_agents(self) -> list[str]:
        """Return agent IDs that are not healthy."""
        return [
            agent_id
            for agent_id, health in self._agents.items()
            if health.status != HealthStatus.HEALTHY
        ]

    def reset(self) -> None:
        """Reset all monitoring state."""
        self._agents.clear()
