"""Agent lifecycle manager with state machine, hooks, graceful shutdown, and versioning."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class LifecycleError(Exception):
    """Base exception for lifecycle errors."""


class InvalidTransitionError(LifecycleError):
    """Raised when an invalid state transition is attempted."""


class AgentNotReadyError(LifecycleError):
    """Raised when an agent is not in a ready state for the requested operation."""


class ShutdownTimeoutError(LifecycleError):
    """Raised when graceful shutdown times out."""


class UpgradeError(LifecycleError):
    """Raised when an agent upgrade fails."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LifecycleState(Enum):
    """Agent lifecycle states.

    INIT → READY → ACTIVE → PAUSED → RETIRED
              ↑        ↓         ↓
              └────────┴─────────┘
    """

    INIT = auto()
    READY = auto()
    ACTIVE = auto()
    PAUSED = auto()
    RETIRED = auto()
    ERROR = auto()


# Valid transitions
_VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.INIT: {LifecycleState.READY, LifecycleState.RETIRED, LifecycleState.ERROR},
    LifecycleState.READY: {LifecycleState.ACTIVE, LifecycleState.RETIRED, LifecycleState.ERROR},
    LifecycleState.ACTIVE: {LifecycleState.PAUSED, LifecycleState.READY, LifecycleState.RETIRED, LifecycleState.ERROR},
    LifecycleState.PAUSED: {LifecycleState.READY, LifecycleState.ACTIVE, LifecycleState.RETIRED, LifecycleState.ERROR},
    LifecycleState.RETIRED: set(),
    LifecycleState.ERROR: {LifecycleState.READY, LifecycleState.RETIRED},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleEvent:
    """Records a state transition event.

    Attributes:
        event_id: Unique event identifier.
        agent_id: Which agent.
        from_state: Previous state.
        to_state: New state.
        reason: Why the transition occurred.
        timestamp: When the transition happened.
        metadata: Additional event data.
    """

    event_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    from_state: LifecycleState = LifecycleState.INIT
    to_state: LifecycleState = LifecycleState.INIT
    reason: str = ""
    timestamp: float = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRecord:
    """Tracks an agent through its lifecycle.

    Attributes:
        agent_id: Unique agent identifier.
        state: Current lifecycle state.
        version: Agent version (for upgrades).
        spawned_at: When the agent was spawned.
        last_active_at: When the agent was last active.
        transition_count: Number of state transitions.
        history: State transition history.
    """

    agent_id: str
    state: LifecycleState = LifecycleState.INIT
    version: str = "1.0.0"
    spawned_at: float = field(default_factory=_now)
    last_active_at: float = field(default_factory=_now)
    transition_count: int = 0
    history: list[LifecycleEvent] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Lifecycle hook protocol
# ---------------------------------------------------------------------------


@dataclass
class LifecycleHooks:
    """Callback hooks for lifecycle events.

    All hooks are optional async callables.
    """

    on_init: Callable[[str], Awaitable[None]] | None = None
    on_ready: Callable[[str], Awaitable[None]] | None = None
    on_activate: Callable[[str], Awaitable[None]] | None = None
    on_pause: Callable[[str], Awaitable[None]] | None = None
    on_resume: Callable[[str], Awaitable[None]] | None = None
    on_retire: Callable[[str], Awaitable[None]] | None = None
    on_error: Callable[[str, Exception], Awaitable[None]] | None = None
    on_upgrade: Callable[[str, str, str], Awaitable[None]] | None = None  # agent_id, old_ver, new_ver

    async def fire_init(self, agent_id: str) -> None:
        if self.on_init:
            await self.on_init(agent_id)

    async def fire_ready(self, agent_id: str) -> None:
        if self.on_ready:
            await self.on_ready(agent_id)

    async def fire_activate(self, agent_id: str) -> None:
        if self.on_activate:
            await self.on_activate(agent_id)

    async def fire_pause(self, agent_id: str) -> None:
        if self.on_pause:
            await self.on_pause(agent_id)

    async def fire_resume(self, agent_id: str) -> None:
        if self.on_resume:
            await self.on_resume(agent_id)

    async def fire_retire(self, agent_id: str) -> None:
        if self.on_retire:
            await self.on_retire(agent_id)

    async def fire_error(self, agent_id: str, error: Exception) -> None:
        if self.on_error:
            await self.on_error(agent_id, error)

    async def fire_upgrade(self, agent_id: str, old_ver: str, new_ver: str) -> None:
        if self.on_upgrade:
            await self.on_upgrade(agent_id, old_ver, new_ver)


# ---------------------------------------------------------------------------
# Lifecycle Manager
# ---------------------------------------------------------------------------


class AgentLifecycleManager:
    """Manages agent lifecycle: state machine, hooks, graceful shutdown, and versioning.

    State machine: INIT -> READY -> ACTIVE <-> PAUSED -> RETIRED

    Features:
    - Enforces valid state transitions
    - Fires lifecycle hooks on transitions
    - Graceful shutdown with timeout
    - Agent versioning and upgrade tracking
    - Full transition history
    """

    def __init__(
        self,
        *,
        default_shutdown_timeout: float = 30.0,
        max_history_per_agent: int = 1000,
    ) -> None:
        self._default_shutdown_timeout = default_shutdown_timeout
        self._max_history = max_history_per_agent

        self._agents: dict[str, AgentRecord] = {}
        self._hooks: dict[str, LifecycleHooks] = {}
        self._global_hooks = LifecycleHooks()

        # Shutdown tracking
        self._shutting_down: dict[str, asyncio.Task[Any]] = {}

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        *,
        hooks: LifecycleHooks | None = None,
        version: str = "1.0.0",
    ) -> AgentRecord:
        """Register a new agent in INIT state."""
        if agent_id in self._agents:
            raise LifecycleError(f"Agent {agent_id} already registered")

        record = AgentRecord(agent_id=agent_id, version=version)
        self._agents[agent_id] = record
        if hooks:
            self._hooks[agent_id] = hooks

        self._record_event(agent_id, LifecycleState.INIT, LifecycleState.INIT, "registered")
        logger.debug("Registered agent %s (v%s)", agent_id, version)
        return record

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent completely."""
        if agent_id not in self._agents:
            return
        del self._agents[agent_id]
        self._hooks.pop(agent_id, None)
        self._shutting_down.pop(agent_id, None)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    async def transition(
        self,
        agent_id: str,
        target: LifecycleState,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> LifecycleState:
        """Transition an agent to a target state.

        Raises InvalidTransitionError if the transition is not allowed.
        Fires appropriate lifecycle hooks before and after.
        """
        record = self._get_record(agent_id)
        current = record.state

        if target not in _VALID_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(
                f"Cannot transition {agent_id} from {current.name} to {target.name}"
            )

        # Fire pre-transition hooks
        await self._fire_pre_hooks(agent_id, current, target)

        # Apply transition
        record.state = target
        record.last_active_at = _now()
        record.transition_count += 1

        # Record the event
        self._record_event(agent_id, current, target, reason, metadata)

        # Fire post-transition hooks
        await self._fire_post_hooks(agent_id, current, target)

        logger.info("Agent %s: %s -> %s (%s)", agent_id, current.name, target.name, reason)
        return target

    async def activate(self, agent_id: str, reason: str = "") -> LifecycleState:
        """Move agent from READY to ACTIVE."""
        return await self.transition(agent_id, LifecycleState.ACTIVE, reason=reason)

    async def pause(self, agent_id: str, reason: str = "") -> LifecycleState:
        """Move agent from ACTIVE to PAUSED."""
        return await self.transition(agent_id, LifecycleState.PAUSED, reason=reason)

    async def resume(self, agent_id: str, reason: str = "") -> LifecycleState:
        """Move agent from PAUSED back to ACTIVE."""
        return await self.transition(agent_id, LifecycleState.ACTIVE, reason=reason)

    async def deactivate(self, agent_id: str, reason: str = "") -> LifecycleState:
        """Move agent from ACTIVE back to READY."""
        return await self.transition(agent_id, LifecycleState.READY, reason=reason)

    async def mark_ready(self, agent_id: str, reason: str = "") -> LifecycleState:
        """Move agent from INIT to READY."""
        return await self.transition(agent_id, LifecycleState.READY, reason=reason)

    async def mark_error(self, agent_id: str, error: Exception) -> LifecycleState:
        """Move agent to ERROR state."""
        result = await self.transition(
            agent_id,
            LifecycleState.ERROR,
            reason=f"Error: {error}",
            metadata={"error": str(error)},
        )
        # Fire error hook
        hooks = self._hooks.get(agent_id)
        if hooks:
            await hooks.fire_error(agent_id, error)
        await self._global_hooks.fire_error(agent_id, error)
        return result

    # ------------------------------------------------------------------
    # Graceful shutdown
    # ------------------------------------------------------------------

    async def graceful_shutdown(
        self,
        agent_id: str,
        timeout: float | None = None,
    ) -> bool:
        """Gracefully retire an agent with timeout.

        Returns True if shutdown was clean, False if forced.
        """
        timeout = timeout or self._default_shutdown_timeout

        try:
            result = await asyncio.wait_for(
                self._do_shutdown(agent_id),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout for %s (%.1fs), forcing retirement", agent_id, timeout)
            return await self.transition(agent_id, LifecycleState.RETIRED, reason="forced_shutdown")

    async def shutdown_all(
        self,
        timeout: float | None = None,
    ) -> dict[str, bool]:
        """Gracefully shut down all agents. Returns per-agent success map."""
        timeout = timeout or self._default_shutdown_timeout
        agents = list(self._agents.keys())
        tasks = [self.graceful_shutdown(aid, timeout) for aid in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outcomes: dict[str, bool] = {}
        for aid, result in zip(agents, results, strict=False):
            outcomes[aid] = result is True
        return outcomes

    async def _do_shutdown(self, agent_id: str) -> bool:
        """Internal shutdown sequence."""
        record = self._get_record(agent_id)

        # Pause first if active
        if record.state == LifecycleState.ACTIVE:
            await self.pause(agent_id, reason="shutdown")
            await asyncio.sleep(0.5)  # brief drain period

        # Retire
        await self.transition(agent_id, LifecycleState.RETIRED, reason="graceful_shutdown")
        return True

    # ------------------------------------------------------------------
    # Versioning and upgrades
    # ------------------------------------------------------------------

    def get_version(self, agent_id: str) -> str:
        """Get the current version of an agent."""
        return self._get_record(agent_id).version

    async def upgrade_agent(
        self,
        agent_id: str,
        new_version: str,
        *,
        require_ready: bool = True,
    ) -> bool:
        """Upgrade an agent to a new version.

        If require_ready is True, the agent must be paused or ready.
        """
        record = self._get_record(agent_id)

        if require_ready and record.state not in (LifecycleState.READY, LifecycleState.PAUSED):
            raise InvalidTransitionError(
                f"Agent {agent_id} must be READY or PAUSED for upgrade, currently {record.state.name}"
            )

        old_version = record.version
        record.version = new_version

        # Fire upgrade hooks
        hooks = self._hooks.get(agent_id)
        if hooks:
            await hooks.fire_upgrade(agent_id, old_version, new_version)
        await self._global_hooks.fire_upgrade(agent_id, old_version, new_version)

        logger.info("Upgraded agent %s from v%s to v%s", agent_id, old_version, new_version)
        return True

    # ------------------------------------------------------------------
    # Hook management
    # ------------------------------------------------------------------

    def set_global_hooks(self, hooks: LifecycleHooks) -> None:
        """Set hooks that fire for all agents."""
        self._global_hooks = hooks

    def set_agent_hooks(self, agent_id: str, hooks: LifecycleHooks) -> None:
        """Set per-agent hooks."""
        self._hooks[agent_id] = hooks

    async def _fire_pre_hooks(
        self,
        agent_id: str,
        current: LifecycleState,
        target: LifecycleState,
    ) -> None:
        """Fire hooks before a transition."""
        hooks = self._hooks.get(agent_id)

        if target == LifecycleState.RETIRED:
            if hooks:
                await hooks.fire_retire(agent_id)
            await self._global_hooks.fire_retire(agent_id)

    async def _fire_post_hooks(
        self,
        agent_id: str,
        previous: LifecycleState,
        current: LifecycleState,
    ) -> None:
        """Fire hooks after a transition."""
        hooks = self._hooks.get(agent_id)

        if current == LifecycleState.READY:
            if hooks:
                await hooks.fire_ready(agent_id)
            await self._global_hooks.fire_ready(agent_id)
        elif current == LifecycleState.ACTIVE:
            if hooks:
                await hooks.fire_activate(agent_id)
            await self._global_hooks.fire_activate(agent_id)
        elif current == LifecycleState.PAUSED:
            if hooks:
                await hooks.fire_pause(agent_id)
            await self._global_hooks.fire_pause(agent_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _get_record(self, agent_id: str) -> AgentRecord:
        """Get agent record or raise."""
        if agent_id not in self._agents:
            raise LifecycleError(f"Agent {agent_id} not found")
        return self._agents[agent_id]

    def _record_event(
        self,
        agent_id: str,
        from_state: LifecycleState,
        to_state: LifecycleState,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a transition event in the agent's history."""
        record = self._agents.get(agent_id)
        if not record:
            return

        event = LifecycleEvent(
            agent_id=agent_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            metadata=metadata or {},
        )
        record.history.append(event)

        # Prune history
        if len(record.history) > self._max_history:
            record.history = record.history[-self._max_history:]

    def get_state(self, agent_id: str) -> LifecycleState | None:
        """Get the current state of an agent."""
        record = self._agents.get(agent_id)
        return record.state if record else None

    def get_history(self, agent_id: str, limit: int = 50) -> list[LifecycleEvent]:
        """Get transition history for an agent."""
        record = self._get_record(agent_id)
        return record.history[-limit:]

    def get_agents_by_state(self, state: LifecycleState) -> list[str]:
        """Get all agents in a given state."""
        return [aid for aid, r in self._agents.items() if r.state == state]

    def is_state(self, agent_id: str, state: LifecycleState) -> bool:
        """Check if an agent is in a given state."""
        return self.get_state(agent_id) == state

    def can_transition(self, agent_id: str, target: LifecycleState) -> bool:
        """Check if a transition is valid."""
        record = self._agents.get(agent_id)
        if not record:
            return False
        return target in _VALID_TRANSITIONS.get(record.state, set())

    @property
    def active_agents(self) -> dict[str, AgentRecord]:
        """Return all non-retired agents."""
        return {
            aid: r
            for aid, r in self._agents.items()
            if r.state != LifecycleState.RETIRED
        }

    @property
    def stats(self) -> dict[str, Any]:
        """Return lifecycle statistics."""
        counts: dict[str, int] = defaultdict(int)
        for r in self._agents.values():
            counts[r.state.name] += 1

        return {
            "total": len(self._agents),
            "by_state": dict(counts),
            "total_transitions": sum(r.transition_count for r in self._agents.values()),
        }

    def snapshot(self) -> dict[str, Any]:
        """Return current state snapshot."""
        return {
            "stats": self.stats,
            "agents": {
                aid: {
                    "state": r.state.name,
                    "version": r.version,
                    "transitions": r.transition_count,
                }
                for aid, r in self._agents.items()
            },
        }
