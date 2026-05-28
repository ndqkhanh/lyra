"""
Fleet Manager for agent lifecycle and resource allocation.

Implements:
- Agent lifecycle: spawn, monitor, terminate
- Resource allocation and tracking
- Health checking with heartbeat monitoring
- Auto-scaling based on system load
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import uuid4


class AgentStatus(Enum):
    """Lifecycle status of an agent in the fleet."""

    PENDING = auto()
    RUNNING = auto()
    IDLE = auto()
    BUSY = auto()
    DEGRADED = auto()
    FAILED = auto()
    TERMINATED = auto()


@dataclass(frozen=True)
class ResourceProfile:
    """Resource allocation for an agent."""

    cpu_cores: float = 1.0
    memory_mb: int = 512
    gpu_count: int = 0
    gpu_memory_mb: int = 0
    bandwidth_mbps: int = 100
    storage_mb: int = 1024


@dataclass
class AgentInstance:
    """A managed agent instance in the fleet."""

    agent_id: str = field(default_factory=lambda: f"agent_{uuid4().hex[:8]}")
    name: str = ""
    agent_type: str = "generic"
    status: AgentStatus = AgentStatus.PENDING
    resources: ResourceProfile = field(default_factory=ResourceProfile)
    current_load: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat: str | None = None
    spawned_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_success_rate(self) -> float:
        """Calculate the agent's task success rate."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 1.0
        return self.tasks_completed / total


@dataclass
class FleetConfig:
    """Configuration for the fleet manager."""

    min_agents: int = 2
    max_agents: int = 20
    scale_up_threshold: float = 0.75
    scale_down_threshold: float = 0.25
    health_check_interval: float = 10.0
    heartbeat_timeout: float = 30.0
    default_resource_profile: ResourceProfile = field(default_factory=ResourceProfile)
    auto_scaling_enabled: bool = True


class FleetManager:
    """
    Manages the lifecycle and resources of the agent fleet.

    Features:
    - Agent lifecycle management (spawn, monitor, terminate)
    - Resource allocation per agent
    - Health checking with heartbeat monitoring
    - Auto-scaling based on fleet load metrics
    """

    def __init__(self, config: FleetConfig | None = None) -> None:
        self.config = config or FleetConfig()
        self.agents: dict[str, AgentInstance] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._running: bool = False
        self._health_task: asyncio.Task | None = None
        self._scale_task: asyncio.Task | None = None
        self._stats: dict[str, int] = {
            "agents_spawned": 0,
            "agents_terminated": 0,
            "health_checks_passed": 0,
            "health_checks_failed": 0,
            "scale_ups": 0,
            "scale_downs": 0,
        }

    async def spawn_agent(
        self,
        name: str,
        agent_type: str = "generic",
        resources: ResourceProfile | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentInstance:
        """
        Spawn a new agent in the fleet.

        Args:
            name: Human-readable name for the agent
            agent_type: Type/category of agent
            resources: Resource allocation profile
            metadata: Optional metadata

        Returns:
            The newly created AgentInstance
        """
        async with self._lock:
            agent = AgentInstance(
                name=name,
                agent_type=agent_type,
                resources=resources or self.config.default_resource_profile,
                status=AgentStatus.PENDING,
                spawned_at=datetime.now().isoformat(),
                metadata=metadata or {},
            )
            self.agents[agent.agent_id] = agent
            self._stats["agents_spawned"] += 1

        await asyncio.sleep(0.05)
        async with self._lock:
            agent.status = AgentStatus.RUNNING
        return agent

    async def terminate_agent(self, agent_id: str) -> bool:
        """
        Terminate an agent and remove it from the fleet.

        Args:
            agent_id: The agent to terminate

        Returns:
            True if terminated, False if not found
        """
        async with self._lock:
            agent = self.agents.get(agent_id)
            if agent is None:
                return False
            agent.status = AgentStatus.TERMINATED
            agent.last_heartbeat = datetime.now().isoformat()
            del self.agents[agent_id]
            self._stats["agents_terminated"] += 1
        return True

    async def get_agent(self, agent_id: str) -> AgentInstance | None:
        """Get an agent by ID."""
        async with self._lock:
            return self.agents.get(agent_id)

    async def get_idle_agents(self) -> list[AgentInstance]:
        """Get all agents that are currently idle."""
        async with self._lock:
            return [
                a for a in self.agents.values()
                if a.status in (AgentStatus.RUNNING, AgentStatus.IDLE)
                and a.current_load < self.config.scale_up_threshold
            ]

    async def assign_task_to_agent(self, agent_id: str) -> bool:
        """
        Mark an agent as busy handling a task.

        Args:
            agent_id: The agent to assign to

        Returns:
            True if assigned, False if not available
        """
        async with self._lock:
            agent = self.agents.get(agent_id)
            if agent is None or agent.status in (AgentStatus.FAILED, AgentStatus.TERMINATED):
                return False
            agent.status = AgentStatus.BUSY
            agent.current_load = min(1.0, agent.current_load + 0.1)
        return True

    async def complete_task_for_agent(self, agent_id: str, success: bool = True) -> None:
        """Record task completion for an agent."""
        async with self._lock:
            agent = self.agents.get(agent_id)
            if agent is None:
                return
            if success:
                agent.tasks_completed += 1
            else:
                agent.tasks_failed += 1
            agent.current_load = max(0.0, agent.current_load - 0.1)
            if agent.current_load < 0.3:
                agent.status = AgentStatus.IDLE
            else:
                agent.status = AgentStatus.RUNNING

    async def record_heartbeat(self, agent_id: str) -> bool:
        """
        Record a heartbeat from an agent.

        Args:
            agent_id: The agent sending the heartbeat

        Returns:
            True if recorded, False if agent not found
        """
        async with self._lock:
            agent = self.agents.get(agent_id)
            if agent is None:
                return False
            agent.last_heartbeat = datetime.now().isoformat()
            if agent.status == AgentStatus.FAILED:
                agent.status = AgentStatus.RUNNING
        return True

    async def start(self) -> None:
        """Start the fleet manager background tasks."""
        self._running = True
        self._health_task = asyncio.create_task(self._health_check_loop())
        if self.config.auto_scaling_enabled:
            self._scale_task = asyncio.create_task(self._auto_scale_loop())

    async def stop(self) -> None:
        """Stop the fleet manager and terminate all agents."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
        if self._scale_task:
            self._scale_task.cancel()
        if self._health_task:
            await asyncio.gather(self._health_task, return_exceptions=True)
        if self._scale_task:
            await asyncio.gather(self._scale_task, return_exceptions=True)
        async with self._lock:
            for agent_id in list(self.agents.keys()):
                agent = self.agents[agent_id]
                agent.status = AgentStatus.TERMINATED
            self.agents.clear()

    async def _health_check_loop(self) -> None:
        """Periodic health check loop that detects failed agents."""
        while self._running:
            await asyncio.sleep(self.config.health_check_interval)
            now = datetime.now()
            async with self._lock:
                for agent in list(self.agents.values()):
                    if agent.last_heartbeat is None:
                        continue
                    last = datetime.fromisoformat(agent.last_heartbeat)
                    elapsed = (now - last).total_seconds()
                    if elapsed > self.config.heartbeat_timeout:
                        agent.status = AgentStatus.FAILED
                        self._stats["health_checks_failed"] += 1
                    else:
                        self._stats["health_checks_passed"] += 1

    async def _auto_scale_loop(self) -> None:
        """Periodic auto-scaling loop based on fleet load."""
        while self._running:
            await asyncio.sleep(self.config.health_check_interval * 2)
            await self._evaluate_scaling()

    async def _evaluate_scaling(self) -> None:
        """Evaluate current fleet load and scale up or down."""
        async with self._lock:
            active_agents = [
                a for a in self.agents.values()
                if a.status not in (AgentStatus.FAILED, AgentStatus.TERMINATED)
            ]
            current_count = len(active_agents)
            if current_count == 0:
                return

            avg_load = sum(a.current_load for a in active_agents) / current_count

        if avg_load > self.config.scale_up_threshold and current_count < self.config.max_agents:
            scale_count = min(
                self.config.max_agents - current_count,
                max(1, int((avg_load - self.config.scale_up_threshold) * current_count)),
            )
            for _ in range(scale_count):
                await self.spawn_agent(
                    name=f"auto_agent_{uuid4().hex[:6]}",
                    agent_type="auto_scaled",
                )
            async with self._lock:
                self._stats["scale_ups"] += scale_count

        elif avg_load < self.config.scale_down_threshold and current_count > self.config.min_agents:
            idle_agents = await self.get_idle_agents()
            scale_count = min(
                current_count - self.config.min_agents,
                len(idle_agents),
            )
            for agent in idle_agents[:scale_count]:
                await self.terminate_agent(agent.agent_id)
            async with self._lock:
                self._stats["scale_downs"] += scale_count

    def get_fleet_summary(self) -> dict[str, Any]:
        """Get a summary of the fleet state."""
        status_counts: dict[str, int] = {}
        total_load = 0.0
        for agent in self.agents.values():
            status_counts[agent.status.name] = status_counts.get(agent.status.name, 0) + 1
            total_load += agent.current_load

        active_count = len(self.agents)
        return {
            "total_agents": active_count,
            "status_breakdown": status_counts,
            "average_load": total_load / active_count if active_count > 0 else 0.0,
            "min_agents": self.config.min_agents,
            "max_agents": self.config.max_agents,
        }

    def get_stats(self) -> dict[str, int]:
        """Get fleet manager statistics."""
        return dict(self._stats)
