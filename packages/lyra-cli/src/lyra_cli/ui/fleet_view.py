"""Fleet view — multi-agent fleet monitoring and coordination display.

Shows the status, load, and health of all agents in the swarm fleet
with color-coded status indicators and aggregate statistics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class AgentStatus(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    BLOCKED = "blocked"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass(frozen=True)
class FleetAgent:
    agent_id: str
    name: str
    status: AgentStatus
    task_count: int
    success_rate: float
    avg_response_ms: float
    last_heartbeat: float

    @property
    def is_healthy(self) -> bool:
        return self.status != AgentStatus.OFFLINE and self.status != AgentStatus.ERROR


@dataclass(frozen=True)
class FleetSummary:
    total_agents: int
    healthy_agents: int
    idle_agents: int
    busy_agents: int
    total_tasks: int
    fleet_success_rate: float
    avg_response_ms: float
    generated_at: float


class FleetView:
    """Monitors and displays the status of all agents in the swarm fleet.

    Tracks heartbeat, task load, success rates, and response times
    for each agent. Generates aggregate fleet health summaries.
    """

    HEARTBEAT_TIMEOUT_SEC = 30.0

    def __init__(self) -> None:
        self._agents: dict[str, FleetAgent] = {}
        self._task_history: dict[str, list[bool]] = {}

    def register(
        self,
        agent_id: str,
        name: str,
        status: AgentStatus = AgentStatus.IDLE,
    ) -> FleetAgent:
        agent = FleetAgent(
            agent_id=agent_id,
            name=name,
            status=status,
            task_count=0,
            success_rate=1.0,
            avg_response_ms=0.0,
            last_heartbeat=time.time(),
        )
        self._agents[agent_id] = agent
        self._task_history[agent_id] = []
        return agent

    def heartbeat(self, agent_id: str) -> FleetAgent | None:
        agent = self._agents.get(agent_id)
        if agent is None:
            return None

        updated = FleetAgent(
            agent_id=agent.agent_id,
            name=agent.name,
            status=agent.status,
            task_count=agent.task_count,
            success_rate=agent.success_rate,
            avg_response_ms=agent.avg_response_ms,
            last_heartbeat=time.time(),
        )
        self._agents[agent_id] = updated
        return updated

    def update_status(self, agent_id: str, status: AgentStatus) -> FleetAgent | None:
        agent = self._agents.get(agent_id)
        if agent is None:
            return None

        updated = FleetAgent(
            agent_id=agent.agent_id,
            name=agent.name,
            status=status,
            task_count=agent.task_count,
            success_rate=agent.success_rate,
            avg_response_ms=agent.avg_response_ms,
            last_heartbeat=agent.last_heartbeat,
        )
        self._agents[agent_id] = updated
        return updated

    def record_task(self, agent_id: str, success: bool, response_ms: float) -> None:
        agent = self._agents.get(agent_id)
        if agent is None:
            return

        self._task_history.setdefault(agent_id, []).append(success)
        recent = self._task_history[agent_id][-50:]
        success_rate = sum(1 for s in recent if s) / max(len(recent), 1)

        updated = FleetAgent(
            agent_id=agent.agent_id,
            name=agent.name,
            status=agent.status,
            task_count=agent.task_count + 1,
            success_rate=round(success_rate, 3),
            avg_response_ms=round(
                (agent.avg_response_ms * agent.task_count + response_ms)
                / (agent.task_count + 1),
                1,
            ),
            last_heartbeat=agent.last_heartbeat,
        )
        self._agents[agent_id] = updated

    def summary(self) -> FleetSummary:
        now = time.time()
        agents = list(self._agents.values())

        for agent in agents:
            if now - agent.last_heartbeat > self.HEARTBEAT_TIMEOUT_SEC:
                self.update_status(agent.agent_id, AgentStatus.OFFLINE)

        healthy = [a for a in agents if a.is_healthy]
        return FleetSummary(
            total_agents=len(agents),
            healthy_agents=len(healthy),
            idle_agents=sum(1 for a in agents if a.status == AgentStatus.IDLE),
            busy_agents=sum(1 for a in agents if a.status == AgentStatus.BUSY),
            total_tasks=sum(a.task_count for a in agents),
            fleet_success_rate=round(
                sum(a.success_rate for a in healthy) / max(len(healthy), 1), 3
            ),
            avg_response_ms=round(
                sum(a.avg_response_ms for a in healthy) / max(len(healthy), 1), 1
            ),
            generated_at=now,
        )

    def get_agent(self, agent_id: str) -> FleetAgent | None:
        return self._agents.get(agent_id)

    def stats(self) -> dict:
        s = self.summary()
        return {
            "total_agents": s.total_agents,
            "healthy": s.healthy_agents,
            "fleet_success_rate": s.fleet_success_rate,
            "total_tasks_completed": s.total_tasks,
        }
