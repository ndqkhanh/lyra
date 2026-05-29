"""Unified Agent Protocol — every agent in Lyra implements this interface.

Replaces the 5 duplicate agent hierarchies (src/agents/, lyra-core/agent/,
lyra-agent-swarm/, lyra-pentest/, lyra-orchestration/) with a single Protocol.

Inspired by: tmux pane model, cmux agent hooks, AutoScientists agent heartbeat.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

# ── Identity ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentIdentity:
    """Immutable agent identity. Never changes after creation."""

    agent_id: str
    project_id: str
    agent_type: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    metadata: frozenset[tuple[str, str]] = field(default_factory=frozenset)


# ── Lifecycle × Health State ────────────────────────────────────────────────


class AgentLifecycle(str, Enum):
    """What phase the agent is in."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    IDLE = "idle"
    NEEDS_INPUT = "needs_input"
    HIBERNATING = "hibernating"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    TERMINATED = "terminated"


class AgentHealth(str, Enum):
    """Health status independent of lifecycle."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class AgentState:
    """Combined lifecycle and health snapshot. Immutable."""

    lifecycle: AgentLifecycle
    health: AgentHealth
    since: float  # time.time() when this state was entered
    message: str = ""


# ── Task & Result ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Task:
    """Immutable task descriptor."""

    task_id: str
    instruction: str
    context: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    parent_task_id: str | None = None


@dataclass(frozen=True)
class TaskResult:
    """Immutable task result."""

    task_id: str
    agent_id: str
    success: bool
    output: Any = None
    error: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: tuple[str, ...] = ()  # file paths to produced artifacts


# ── Agent Mode ──────────────────────────────────────────────────────────────


class AgentMode(Protocol):
    """Pluggable interaction mode (tmux window_mode vtable pattern).

    Modes stack on top of each other. The topmost mode intercepts input/output.
    """

    @property
    def name(self) -> str: ...

    async def on_enter(self, agent: AgentProtocol) -> None: ...
    async def on_exit(self, agent: AgentProtocol) -> None: ...
    async def handle_input(self, agent: AgentProtocol, text: str) -> str | None: ...
    async def transform_output(self, agent: AgentProtocol, chunk: str) -> str: ...


# ── Agent Protocol ──────────────────────────────────────────────────────────


@runtime_checkable
class AgentProtocol(Protocol):
    """Every agent in Lyra MUST implement this protocol.

    This replaces:
      - src/agents/base.py Agent ABC
      - lyra-core/agent/loop.py AgentLoop (loop is now an implementation detail)
      - lyra-agent-swarm/ discipline agents (wrap via adapter)
      - lyra-pentest/agents/ BaseAgent (wrap via adapter)
      - lyra-orchestration/ AgentCoordinator (wrap via adapter)
    """

    # ── Identity ──

    @property
    def identity(self) -> AgentIdentity:
        """Immutable identity. Never changes after creation."""
        ...

    # ── State ──

    @property
    def state(self) -> AgentState:
        """Current lifecycle × health snapshot."""
        ...

    # ── Lifecycle ──

    async def initialize(self) -> None:
        """Called once after construction. Setup resources, load config."""
        ...

    async def run(self, task: Task) -> AsyncIterator[str]:
        """Execute a task, yielding streaming output chunks.

        This is the primary execution interface. Agents yield output
        incrementally so callers can stream results to clients.
        """
        ...

    async def shutdown(self) -> None:
        """Graceful shutdown. Flush buffers, release resources, persist state."""
        ...

    # ── Mode Stack ──

    @property
    def mode_stack(self) -> tuple[AgentMode, ...]:
        """Immutable snapshot of the current mode stack."""
        ...

    def push_mode(self, mode: AgentMode) -> None:
        """Push a new interaction mode onto the stack."""
        ...

    def pop_mode(self) -> AgentMode:
        """Pop and return the topmost mode."""
        ...

    # ── Capability Check ──

    def supports(self, capability: str) -> bool:
        """Check if this agent advertises a capability keyword."""
        return capability in self.identity.capabilities

    # ── Observation ──

    async def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of agent state for debugging."""
        ...


# ── Agent Factory Protocol ──────────────────────────────────────────────────


@runtime_checkable
class AgentFactory(Protocol):
    """Creates agents from configuration. Used by AgentSpawner."""

    @property
    def agent_type(self) -> str:
        """The type string this factory produces."""
        ...

    async def build(self, identity: AgentIdentity, config: dict[str, Any]) -> AgentProtocol:
        """Construct and initialize an agent."""
        ...

    async def warm_up(self, agent: AgentProtocol) -> None:
        """Optional warm-up: prime caches, pre-load models."""
        ...

    async def health_check(self, agent: AgentProtocol) -> AgentHealth:
        """Check if an already-built agent is healthy."""
        ...


# ── Workstream Items ────────────────────────────────────────────────────────


class ItemKind(str, Enum):
    """What kind of workstream item this is."""

    TOOL_CALL = "tool_call"
    PERMISSION = "permission"
    QUESTION = "question"
    EXIT_PLAN = "exit_plan"
    NOTIFICATION = "notification"
    TELEMETRY = "telemetry"
    PROPOSAL = "proposal"  # AutoScientists-style: experiment proposal
    REVIEW = "review"  # AutoScientists-style: peer review comment


class ItemStatus(str, Enum):
    """Workstream item lifecycle."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RESOLVED = "resolved"
    WAITING = "waiting"  # tmux CMD_RETURN_WAIT pattern


@dataclass
class WorkstreamItem:
    """A single action/event in the agent workstream.

    Inspired by cmux WorkstreamSystem. Items flow through the event bus
    and can be consumed by UIs, webhooks, and audit logs.
    """

    id: str
    kind: ItemKind
    status: ItemStatus = ItemStatus.PENDING
    source_agent_id: str = ""
    source_project_id: str = ""
    ppid: int = 0  # auto-expire on process death
    title: str = ""
    body: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    resolved_at: float | None = None
    resolved_by: str | None = None
    correlation_id: str | None = None  # for request/response chains

    @property
    def is_terminal(self) -> bool:
        return self.status in (ItemStatus.APPROVED, ItemStatus.REJECTED,
                               ItemStatus.EXPIRED, ItemStatus.RESOLVED)

    def get_age_seconds(self, now: float | None = None) -> float:
        """Return the age of this item in seconds."""
        import time
        return (now or time.time()) - self.created_at
