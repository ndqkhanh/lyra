"""Agent monitor — abtop-style real-time agent monitoring.

Provides status polling, resource usage tracking, and alert subscriptions
for monitoring agents in the Lyra system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .exceptions import MonitorError


@dataclass(frozen=True)
class AgentStatus:
    """Current status of a monitored agent.

    Attributes:
        agent_id: Unique identifier for the agent.
        state: Current state string (e.g., "idle", "busy", "error").
        cpu_pct: CPU usage percentage (0.0 to 100.0).
        mem_mb: Memory usage in megabytes.
        active_tasks: Number of currently active tasks.
        last_heartbeat: Unix timestamp of last heartbeat.
    """

    agent_id: str
    state: str
    cpu_pct: float
    mem_mb: float
    active_tasks: int
    last_heartbeat: float


@dataclass(frozen=True)
class ResourceUsage:
    """Resource usage snapshot for a monitored agent.

    Attributes:
        agent_id: Unique identifier for the agent.
        token_count: Number of tokens consumed.
        latency_ms: Average latency in milliseconds.
        cost_estimate: Estimated cost in USD.
    """

    agent_id: str
    token_count: int
    latency_ms: float
    cost_estimate: float


@dataclass(frozen=True)
class MonitorConfig:
    """Configuration for the agent monitor.

    Attributes:
        refresh_interval: Seconds between status polls.
        max_agents: Maximum number of agents to track.
        alert_threshold_cpu: CPU percentage threshold for alerts.
    """

    refresh_interval: float = 1.0
    max_agents: int = 50
    alert_threshold_cpu: float = 90.0


AlertCallback = Callable[[AgentStatus], None]


class AgentMonitor:
    """Real-time agent monitoring with status polling and alert subscriptions.

    Tracks agent status, resource usage, and fires callbacks when alert
    thresholds are breached.
    """

    def __init__(self, config: MonitorConfig | None = None) -> None:
        """Initialize the agent monitor.

        Args:
            config: Optional monitor configuration. Uses defaults if
                not provided.
        """
        self._config = config or MonitorConfig()
        self._agents: dict[str, AgentStatus] = {}
        self._resources: dict[str, list[ResourceUsage]] = {}
        self._subscribers: list[AlertCallback] = []

    @property
    def config(self) -> MonitorConfig:
        """Return the monitor configuration."""
        return self._config

    def _check_alerts(self, status: AgentStatus) -> None:
        """Check alert thresholds and notify subscribers."""
        if status.cpu_pct >= self._config.alert_threshold_cpu:
            for callback in self._subscribers:
                callback(status)

    def register_agent(self, agent_id: str) -> None:
        """Register an agent for monitoring.

        Args:
            agent_id: Unique identifier for the agent.

        Raises:
            MonitorError: If max_agents limit would be exceeded.
        """
        if len(self._agents) >= self._config.max_agents:
            raise MonitorError(
                f"Cannot register agent {agent_id}: maximum of "
                f"{self._config.max_agents} agents reached"
            )
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentStatus(
                agent_id=agent_id,
                state="unknown",
                cpu_pct=0.0,
                mem_mb=0.0,
                active_tasks=0,
                last_heartbeat=time.time(),
            )

    async def poll_agent(self, agent_id: str) -> AgentStatus:
        """Poll a single agent and return its current status.

        Args:
            agent_id: The agent to poll.

        Returns:
            An AgentStatus with current metrics.

        Raises:
            MonitorError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            raise MonitorError(f"Agent {agent_id} is not registered")

        # Simulate polling by updating heartbeat and returning current status
        current = self._agents[agent_id]
        updated = AgentStatus(
            agent_id=current.agent_id,
            state=current.state,
            cpu_pct=current.cpu_pct,
            mem_mb=current.mem_mb,
            active_tasks=current.active_tasks,
            last_heartbeat=time.time(),
        )
        self._agents[agent_id] = updated
        return updated

    async def poll_all(self) -> tuple[AgentStatus, ...]:
        """Poll all registered agents and return their statuses.

        Returns:
            A tuple of AgentStatus for every registered agent.
        """
        results: list[AgentStatus] = []
        for agent_id in list(self._agents.keys()):
            status = await self.poll_agent(agent_id)
            self._check_alerts(status)
            results.append(status)
        return tuple(results)

    async def get_resource_usage(self, agent_id: str) -> ResourceUsage:
        """Get resource usage for a specific agent.

        Args:
            agent_id: The agent to query.

        Returns:
            A ResourceUsage with token count, latency, and cost estimate.

        Raises:
            MonitorError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            raise MonitorError(f"Agent {agent_id} is not registered")

        # Simulate resource usage
        usage = ResourceUsage(
            agent_id=agent_id,
            token_count=0,
            latency_ms=0.0,
            cost_estimate=0.0,
        )
        return usage

    def record_resource_usage(
        self, agent_id: str, usage: ResourceUsage
    ) -> None:
        """Record a resource usage snapshot for an agent.

        Args:
            agent_id: The agent identifier.
            usage: The ResourceUsage to record.
        """
        if agent_id not in self._resources:
            self._resources[agent_id] = []
        self._resources[agent_id].append(usage)

    def subscribe_alerts(self, callback: AlertCallback) -> None:
        """Subscribe to alert notifications.

        Args:
            callback: A callable that receives an AgentStatus when an
                alert threshold is breached.
        """
        self._subscribers.append(callback)

    def update_status(self, status: AgentStatus) -> None:
        """Manually update the status of a monitored agent.

        Args:
            status: The new AgentStatus to store.
        """
        self._agents[status.agent_id] = status
        self._check_alerts(status)
