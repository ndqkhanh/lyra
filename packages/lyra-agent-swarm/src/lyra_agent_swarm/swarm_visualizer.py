"""Tmux split-pane agent monitoring and swarm dashboard."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class AgentState(Enum):
    """Runtime state of a monitored agent."""

    IDLE = auto()
    BUSY = auto()
    BLOCKED = auto()
    ERROR = auto()
    OFFLINE = auto()


@dataclass(frozen=True)
class AgentStatus:
    """Snapshot of a single agent's runtime state."""

    agent_id: str
    state: AgentState = AgentState.IDLE
    current_task: str | None = None
    utilization: float = 0.0
    last_active: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SwarmSnapshot:
    """Point-in-time view of the entire swarm."""

    timestamp: float = field(default_factory=time.time)
    agents: tuple[AgentStatus, ...] = ()
    active_tasks: int = 0
    metrics: SwarmMetrics | None = None


@dataclass(frozen=True)
class SwarmMetrics:
    """Aggregate swarm health metrics."""

    total_agents: int = 0
    busy: int = 0
    idle: int = 0
    blocked: int = 0
    throughput: float = 0.0


class SwarmVisualizer:
    """Generates agent status snapshots and tmux dashboard panes for swarm monitoring."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentStatus] = {}

    def register_agent(self, agent_id: str, status: AgentStatus | None = None) -> None:
        self._agents[agent_id] = status or AgentStatus(agent_id=agent_id)

    def update_status(self, agent_id: str, status: AgentStatus) -> None:
        self._agents[agent_id] = status

    def get_snapshot(self) -> SwarmSnapshot:
        agents = tuple(self._agents.values())
        active_tasks = sum(1 for a in agents if a.state == AgentState.BUSY)
        busy = sum(1 for a in agents if a.state == AgentState.BUSY)
        idle = sum(1 for a in agents if a.state == AgentState.IDLE)
        blocked = sum(1 for a in agents if a.state == AgentState.BLOCKED)
        metrics = SwarmMetrics(
            total_agents=len(agents),
            busy=busy,
            idle=idle,
            blocked=blocked,
            throughput=float(busy) / max(len(agents), 1),
        )
        return SwarmSnapshot(
            agents=agents,
            active_tasks=active_tasks,
            metrics=metrics,
        )

    def get_agent_status(self, agent_id: str) -> AgentStatus | None:
        return self._agents.get(agent_id)

    def format_tmux_pane(self, agent_id: str) -> str:
        """Format a single agent's status for display in a tmux pane."""
        status = self._agents.get(agent_id)
        if status is None:
            return f"Agent '{agent_id}' — OFFLINE"
        lines = [
            f"Agent: {status.agent_id}",
            f"State: {status.state.name}",
            f"Task:  {status.current_task or 'none'}",
            f"Util:  {status.utilization:.1%}",
            f"Active: {time.strftime('%H:%M:%S', time.localtime(status.last_active))}",
        ]
        return "\n".join(lines)

    def format_dashboard(self) -> str:
        """Format a full swarm dashboard with all agents in a tmux split layout."""
        snapshot = self.get_snapshot()
        lines = [
            "=" * 50,
            "  LYRA AGENT SWARM DASHBOARD",
            "=" * 50,
            f"  Agents: {snapshot.metrics.total_agents if snapshot.metrics else 0}  "
            f"Active: {snapshot.active_tasks}  "
            f"Time: {time.strftime('%H:%M:%S')}",
            "-" * 50,
        ]
        priority = {AgentState.BUSY: 0, AgentState.BLOCKED: 1, AgentState.IDLE: 2, AgentState.ERROR: 3, AgentState.OFFLINE: 4}
        sorted_agents = sorted(snapshot.agents, key=lambda a: priority.get(a.state, 99))
        for agent in sorted_agents:
            lines.append(f"  [{agent.state.name[:4]}] {agent.agent_id:<20} {agent.current_task or '-'}")
        lines.append("-" * 50)
        if snapshot.metrics:
            lines.append(
                f"  Busy: {snapshot.metrics.busy}  Idle: {snapshot.metrics.idle}  "
                f"Blocked: {snapshot.metrics.blocked}  "
                f"Throughput: {snapshot.metrics.throughput:.2f}"
            )
        lines.append("=" * 50)
        return "\n".join(lines)
