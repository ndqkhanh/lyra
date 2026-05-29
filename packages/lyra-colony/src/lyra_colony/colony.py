"""Colony manager: the main orchestrator for an agent colony runtime.

Handles agent spawning, monitoring, retirement, resource allocation,
health metrics, auto-scaling, and agent discovery/registration.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any
from uuid import uuid4

from .agent_spec import (
    AgentRole,
    AgentRoleKind,
    AgentSpec,
    InvalidSpecError,
    LifecycleHooks,
    ResourceLimits,
)
from .communication import Message, MessageBus
from .monitoring import (
    AgentStatus,
    ColonyMonitor,
)
from .scheduler import (
    ColonyScheduler,
    SchedulingStrategy,
    Task,
    TaskState,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ColonyError(Exception):
    """Base exception for colony-level errors."""


class AgentNotFoundError(ColonyError):
    """Raised when an agent ID is not found in the colony."""


class ColonyOverCapacityError(ColonyError):
    """Raised when the colony has reached max_agents."""


class SpawnFailedError(ColonyError):
    """Raised when an agent fails to spawn."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ColonyState(Enum):
    INIT = auto()
    STARTING = auto()
    RUNNING = auto()
    SCALING = auto()
    DRAINING = auto()
    STOPPED = auto()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


@dataclass
class ColonyConfig:
    """Runtime configuration for an agent colony.

    Attributes:
        max_agents: Maximum number of concurrent agents allowed.
        min_agents: Minimum number of agents (autoscaler floor).
        task_timeout: Default task timeout in seconds.
        gossip_interval: Interval between gossip cycles in seconds.
        scale_up_threshold: Queue depth or load ratio that triggers scale-up.
        scale_down_threshold: Idle ratio that triggers scale-down.
        scale_cooldown: Minimum seconds between scaling actions.
        health_check_interval: Seconds between health checks.
        agent_heartbeat_timeout: Seconds without heartbeat before agent is unresponsive.
    """

    max_agents: int = 20
    min_agents: int = 3
    task_timeout: float = 300.0
    gossip_interval: float = 30.0
    scale_up_threshold: float = 0.7
    scale_down_threshold: float = 0.2
    scale_cooldown: float = 60.0
    health_check_interval: float = 5.0
    agent_heartbeat_timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.max_agents < self.min_agents:
            raise ColonyError("max_agents must be >= min_agents")
        if self.min_agents < 1:
            raise ColonyError("min_agents must be >= 1")


@dataclass(frozen=True)
class ColonyHealth:
    """Snapshot of colony health at a point in time.

    Attributes:
        state: Current colony state.
        total_agents: Number of registered agents.
        active_agents: Agents currently executing tasks.
        idle_agents: Agents waiting for tasks.
        degraded_agents: Agents in degraded status.
        queue_depth: Current scheduler queue length.
        throughput: Tasks completed recently.
        error_rate: Fraction of recent tasks that failed.
        health_score: Composite 0.0-1.0 health score.
    """

    state: ColonyState = ColonyState.INIT
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    degraded_agents: int = 0
    queue_depth: int = 0
    throughput: float = 0.0
    error_rate: float = 0.0
    health_score: float = 0.0


# ---------------------------------------------------------------------------
# Agent Colony
# ---------------------------------------------------------------------------


class AgentColony:
    """Self-organizing agent colony runtime.

    The colony manages the full lifecycle of agents: spawning, scheduling,
    communication, monitoring, health management, auto-scaling, and retirement.
    """

    def __init__(self, config: ColonyConfig | None = None) -> None:
        self.config = config or ColonyConfig()
        self._state = ColonyState.INIT

        # Subsystems
        self.scheduler = ColonyScheduler(strategy=SchedulingStrategy.AFFINITY)
        self.message_bus = MessageBus()
        self.monitor = ColonyMonitor()

        # Agent registry
        self._agents: dict[str, AgentSpec] = {}
        self._agent_state: dict[str, AgentStatus] = {}
        self._agent_load: dict[str, float] = defaultdict(float)
        self._agent_task_count: dict[str, int] = defaultdict(int)
        self._agent_spawn_time: dict[str, float] = {}

        # Role templates for spawning
        self._role_templates: dict[str, AgentSpec] = {}

        # Scaling
        self._last_scale_action: float = 0.0

        # Background tasks
        self._running = False
        self._gossip_task: asyncio.Task[Any] | None = None
        self._health_task: asyncio.Task[Any] | None = None
        self._scale_task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the colony runtime."""
        self._state = ColonyState.STARTING
        logger.info("Starting agent colony (min=%d, max=%d)", self.config.min_agents, self.config.max_agents)

        # Start background subsystems
        self._running = True
        self._gossip_task = asyncio.create_task(self._gossip_loop())
        self._health_task = asyncio.create_task(self._health_check_loop())
        self._scale_task = asyncio.create_task(self._autoscale_loop())
        await self.monitor.start_collection()
        await self.scheduler.start_draining()

        # Spawn minimum agents
        for _ in range(self.config.min_agents):
            spec = self._get_default_spec()
            await self.spawn_agent(spec)

        self._state = ColonyState.RUNNING
        self.monitor.log_audit("colony_started", details={"config": self.config.__dict__})

    async def stop(self) -> None:
        """Gracefully stop the colony."""
        self._state = ColonyState.DRAINING
        logger.info("Draining colony...")

        self._running = False
        for task in [self._gossip_task, self._health_task, self._scale_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self.scheduler.stop_draining()
        await self.monitor.stop_collection()

        # Retire all agents
        for agent_id in list(self._agents.keys()):
            await self.retire_agent(agent_id)

        self._state = ColonyState.STOPPED
        self.monitor.log_audit("colony_stopped")
        logger.info("Colony stopped")

    # ------------------------------------------------------------------
    # Agent spawning
    # ------------------------------------------------------------------

    async def spawn_agent(self, spec: AgentSpec) -> str:
        """Spawn a new agent from a specification. Returns the agent ID."""
        if len(self._agents) >= self.config.max_agents:
            raise ColonyOverCapacityError(
                f"Colony at capacity ({len(self._agents)}/{self.config.max_agents})"
            )

        agent_id = f"{spec.role.name}-{_new_id()}"
        self._agents[agent_id] = spec
        self._agent_spawn_time[agent_id] = _now()
        self._agent_state[agent_id] = AgentStatus.INITIALIZING
        self._agent_task_count[agent_id] = 0

        # Register with subsystems
        self.monitor.register_agent(agent_id)
        self.scheduler.register_agent(
            agent_id,
            capabilities=spec.capabilities,
            labels=spec.labels,
        )

        # Fire lifecycle hooks
        hooks = LifecycleHooks()
        await hooks.fire_spawn(agent_id, spec)

        self._agent_state[agent_id] = AgentStatus.READY
        self.monitor.update_status(agent_id, AgentStatus.READY)
        self.monitor.log_audit("agent_spawned", agent_id=agent_id, details={"role": spec.role.name})

        logger.info("Spawned agent %s (role=%s, caps=%s)", agent_id, spec.role.name, spec.capabilities)
        return agent_id

    async def spawn_from_template(self, template_name: str) -> str:
        """Spawn an agent from a pre-registered role template."""
        if template_name not in self._role_templates:
            raise InvalidSpecError(f"Unknown template: {template_name}")
        return await self.spawn_agent(self._role_templates[template_name])

    # ------------------------------------------------------------------
    # Agent retirement
    # ------------------------------------------------------------------

    async def retire_agent(self, agent_id: str) -> bool:
        """Retire an agent from the colony. Returns True if successful."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        spec = self._agents.pop(agent_id)
        self._agent_state[agent_id] = AgentStatus.TERMINATED
        self._agent_spawn_time.pop(agent_id, None)
        self._agent_task_count.pop(agent_id, None)

        # Unregister from subsystems
        self.monitor.unregister_agent(agent_id)
        self.scheduler.unregister_agent(agent_id)
        self.message_bus.unsubscribe_all(agent_id)

        # Fire lifecycle hooks
        hooks = LifecycleHooks()
        await hooks.fire_retire(agent_id, spec)

        self.monitor.update_status(agent_id, AgentStatus.TERMINATED)
        self.monitor.log_audit("agent_retired", agent_id=agent_id, details={"role": spec.role.name})

        logger.info("Retired agent %s", agent_id)
        return True

    # ------------------------------------------------------------------
    # Agent discovery
    # ------------------------------------------------------------------

    def get_agent(self, agent_id: str) -> AgentSpec:
        """Get an agent's specification by ID."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        return self._agents[agent_id]

    def find_agents_by_capability(self, capability: str) -> list[str]:
        """Find agents with a specific capability."""
        return [aid for aid, spec in self._agents.items() if capability in spec.capabilities]

    def find_agents_by_role(self, kind: AgentRoleKind) -> list[str]:
        """Find agents by role kind."""
        return [aid for aid, spec in self._agents.items() if spec.role.kind == kind]

    def find_agents_by_label(self, key: str, value: str) -> list[str]:
        """Find agents with a matching label."""
        return [aid for aid, spec in self._agents.items() if spec.labels.get(key) == value]

    def list_agents(self) -> list[str]:
        """Return all registered agent IDs."""
        return list(self._agents.keys())

    def get_agent_status(self, agent_id: str) -> AgentStatus | None:
        """Get the current status of an agent."""
        return self.monitor.get_agent_status(agent_id)

    # ------------------------------------------------------------------
    # Role templates
    # ------------------------------------------------------------------

    def register_template(self, name: str, spec: AgentSpec) -> None:
        """Register a role template for future spawning."""
        self._role_templates[name] = spec
        logger.debug("Registered template: %s", name)

    def get_template(self, name: str) -> AgentSpec | None:
        """Get a registered role template."""
        return self._role_templates.get(name)

    def list_templates(self) -> list[str]:
        """List all registered template names."""
        return list(self._role_templates.keys())

    # ------------------------------------------------------------------
    # Task submission
    # ------------------------------------------------------------------

    async def submit_task(self, task: Task) -> str:
        """Submit a task to the colony scheduler. Returns task ID."""
        return self.scheduler.submit(task)

    async def submit_task_batch(self, tasks: Sequence[Task]) -> list[str]:
        """Submit multiple tasks at once."""
        return self.scheduler.submit_batch(tasks)

    async def get_task_result(self, task_id: str) -> TaskState | None:
        """Get the current state of a submitted task."""
        return self.scheduler.get_task_state(task_id)

    # ------------------------------------------------------------------
    # Communication shortcuts
    # ------------------------------------------------------------------

    async def send_message(self, sender_id: str, recipient_id: str, payload: dict[str, Any]) -> str:
        """Send a point-to-point message. Returns message ID."""
        msg = Message(sender_id=sender_id, recipient_id=recipient_id, payload=payload)
        await self.message_bus.send(msg)
        return msg.message_id

    async def broadcast_to_all(self, payload: dict[str, Any]) -> None:
        """Broadcast a message to all agents in the colony."""
        msg = Message(sender_id="colony", payload=payload)
        all_agents = self.list_agents()
        await self.message_bus.broadcast(msg, agent_ids=all_agents)

    # ------------------------------------------------------------------
    # Gossip protocol
    # ------------------------------------------------------------------

    async def _gossip_loop(self) -> None:
        """Periodic gossip cycle for knowledge sharing."""
        while self._running:
            try:
                await self._run_gossip_cycle()
            except Exception:
                logger.exception("Error in gossip loop")
            await asyncio.sleep(self.config.gossip_interval)

    async def _run_gossip_cycle(self) -> None:
        """Share knowledge between agents via pub/sub gossip."""
        channel = self.message_bus.get_channel("gossip")
        for agent_id in self._agents:
            summary = {
                "agent_id": agent_id,
                "load": self._agent_load.get(agent_id, 0.0),
                "task_count": self._agent_task_count.get(agent_id, 0),
                "status": self._agent_state.get(agent_id, AgentStatus.READY).name,
            }
            msg = Message(sender_id=agent_id, topic="gossip", payload=summary)
            channel.publish(msg)
        logger.debug("Gossip cycle complete (%d agents)", len(self._agents))

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    async def _health_check_loop(self) -> None:
        """Periodically check agent health and detect unresponsive agents."""
        while self._running:
            try:
                await self._run_health_checks()
            except Exception:
                logger.exception("Error in health check")
            await asyncio.sleep(self.config.health_check_interval)

    async def _run_health_checks(self) -> None:
        unresponsive = self.monitor.get_unresponsive_agents(
            timeout_seconds=self.config.agent_heartbeat_timeout
        )
        for agent_id in unresponsive:
            if agent_id in self._agents:
                self.monitor.update_status(agent_id, AgentStatus.UNRESPONSIVE)
                logger.warning("Agent %s is unresponsive", agent_id)

        # Check for degraded agents
        for agent_id in self._agents:
            error_rate = self.monitor.snapshot().error_rate
            if error_rate > 0.5 and self._agent_task_count.get(agent_id, 0) > 10:
                self.monitor.update_status(agent_id, AgentStatus.DEGRADED)

    # ------------------------------------------------------------------
    # Auto-scaling
    # ------------------------------------------------------------------

    async def _autoscale_loop(self) -> None:
        """Periodically evaluate scaling needs and adjust colony size."""
        while self._running:
            try:
                await self._evaluate_scaling()
            except Exception:
                logger.exception("Error in autoscale loop")
            await asyncio.sleep(self.config.scale_cooldown)

    async def _evaluate_scaling(self) -> None:
        """Scale up or down based on load."""
        now = _now()
        if now - self._last_scale_action < self.config.scale_cooldown:
            return

        snapshot = self.monitor.snapshot()
        queue_depth = self.scheduler.get_queue_depth()
        agent_count = len(self._agents)
        load_ratio = queue_depth / max(1, agent_count)

        if load_ratio > self.config.scale_up_threshold and agent_count < self.config.max_agents:
            await self._scale_up()
        elif (
            snapshot.idle_agents / max(1, agent_count) > (1.0 - self.config.scale_down_threshold)
            and agent_count > self.config.min_agents
        ):
            await self._scale_down()

    async def _scale_up(self) -> None:
        """Add a new agent to handle increased load."""
        spec = self._get_default_spec()
        try:
            agent_id = await self.spawn_agent(spec)
            self._last_scale_action = _now()
            self._state = ColonyState.SCALING
            self.monitor.log_audit("scale_up", details={"new_agent": agent_id})
            logger.info("Scaled up: added agent %s (total: %d)", agent_id, len(self._agents))
            self._state = ColonyState.RUNNING
        except ColonyOverCapacityError:
            logger.warning("Cannot scale up: at capacity")

    async def _scale_down(self) -> None:
        """Remove the most idle agent."""
        idle_candidates = [
            aid
            for aid, load in self._agent_load.items()
            if load == 0.0 and aid in self._agents
        ]
        if idle_candidates:
            to_retire = idle_candidates[0]
            await self.retire_agent(to_retire)
            self._last_scale_action = _now()
            self._state = ColonyState.SCALING
            self.monitor.log_audit("scale_down", details={"retired_agent": to_retire})
            logger.info("Scaled down: retired agent %s (total: %d)", to_retire, len(self._agents))
            self._state = ColonyState.RUNNING

    # ------------------------------------------------------------------
    # Health and metrics
    # ------------------------------------------------------------------

    @property
    def health(self) -> ColonyHealth:
        """Get the current colony health snapshot."""
        s = self.monitor.snapshot()
        return ColonyHealth(
            state=self._state,
            total_agents=s.total_agents,
            active_agents=s.active_agents,
            idle_agents=s.idle_agents,
            degraded_agents=s.degraded_agents,
            queue_depth=self.scheduler.get_queue_depth(),
            throughput=s.throughput_1m,
            error_rate=s.error_rate,
            health_score=s.health_score,
        )

    @property
    def stats(self) -> dict[str, Any]:
        """Return colony statistics summary."""
        h = self.health
        return {
            "state": self._state.name,
            "total_agents": h.total_agents,
            "active_agents": h.active_agents,
            "idle_agents": h.idle_agents,
            "degraded_agents": h.degraded_agents,
            "queue_depth": h.queue_depth,
            "throughput_1m": h.throughput,
            "error_rate": h.error_rate,
            "health_score": h.health_score,
            "templates": len(self._role_templates),
            "active_alerts": len(self.monitor.get_active_alerts()),
        }

    def dashboard(self) -> dict[str, Any]:
        """Return a comprehensive colony dashboard."""
        return {
            "colony": self.stats,
            "agents": {
                aid: {
                    "status": self._agent_state.get(aid, AgentStatus.READY).name,
                    "load": self._agent_load.get(aid, 0.0),
                    "tasks": self._agent_task_count.get(aid, 0),
                }
                for aid in self._agents
            },
            "scheduler": self.scheduler.snapshot(),
            "communication": self.message_bus.get_delivery_stats(),
            "monitoring": self.monitor.dashboard(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_default_spec(self) -> AgentSpec:
        """Build a default agent specification."""
        role = AgentRole(
            name="worker",
            kind=AgentRoleKind.WORKER,
            description="Default colony worker agent",
            default_priority=5,
        )
        return AgentSpec(
            role=role,
            capabilities=("general", "execute", "communicate"),
            resource_limits=ResourceLimits(),
        )

    @property
    def state(self) -> ColonyState:
        return self._state

    @property
    def agent_count(self) -> int:
        return len(self._agents)
