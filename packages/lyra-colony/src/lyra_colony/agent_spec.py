"""Agent specification system for colony runtime.

Defines agent roles, capabilities, resource limits, and lifecycle hooks
that govern how agents are spawned, monitored, and retired within a colony.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class InvalidSpecError(Exception):
    """Raised when an agent specification is invalid."""


class CapabilityConflictError(InvalidSpecError):
    """Raised when required capabilities conflict with excluded capabilities."""


class ResourceLimitExceededError(Exception):
    """Raised when an agent would exceed configured resource limits."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentRoleKind(Enum):
    """Kinds of agent roles in the colony."""

    WORKER = auto()
    COORDINATOR = auto()
    OBSERVER = auto()
    SPECIALIST = auto()
    SCAVENGER = auto()
    SENTINEL = auto()


class SkillLevel(Enum):
    """Proficiency level for a skill."""

    NOVICE = 1
    APPRENTICE = 2
    COMPETENT = 3
    EXPERT = 4
    MASTER = 5


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillRequirement:
    """A single skill requirement with proficiency level.

    Attributes:
        name: Unique skill name.
        level: Minimum proficiency level required.
        mandatory: Whether this skill is mandatory for the role.
    """

    name: str
    level: SkillLevel = SkillLevel.COMPETENT
    mandatory: bool = True


@dataclass(frozen=True)
class ResourceLimits:
    """Resource constraints for an agent.

    Attributes:
        max_cpu_cores: Maximum CPU cores the agent may use.
        max_memory_mb: Maximum memory (MB) the agent may allocate.
        max_tokens_per_task: Token budget per task.
        max_concurrent_tasks: How many tasks the agent may handle at once.
        max_idle_seconds: Maximum idle time before retirement consideration.
    """

    max_cpu_cores: float = 1.0
    max_memory_mb: float = 512.0
    max_tokens_per_task: int = 100_000
    max_concurrent_tasks: int = 5
    max_idle_seconds: float = 3_600.0

    def __post_init__(self) -> None:
        if self.max_cpu_cores <= 0:
            raise InvalidSpecError("max_cpu_cores must be positive")
        if self.max_memory_mb <= 0:
            raise InvalidSpecError("max_memory_mb must be positive")
        if self.max_tokens_per_task <= 0:
            raise InvalidSpecError("max_tokens_per_task must be positive")


@dataclass(frozen=True)
class AgentRole:
    """Defines what role an agent plays in the colony.

    Attributes:
        role_id: Unique role identifier.
        name: Human-readable role name.
        kind: The kind of role (worker, coordinator, etc.).
        description: Longer description of responsibilities.
        default_priority: Base priority for tasks assigned to this role.
    """

    role_id: str = field(default_factory=_new_id)
    name: str = "worker"
    kind: AgentRoleKind = AgentRoleKind.WORKER
    description: str = ""
    default_priority: int = 5


@dataclass(frozen=True)
class AgentSpec:
    """Complete specification for spawning an agent in the colony.

    Attributes:
        spec_id: Unique specification identifier.
        role: The agent's role definition.
        capabilities: List of capability tags the agent possesses.
        skills: Required skills with proficiency levels.
        resource_limits: CPU, memory, token constraints.
        labels: Arbitrary key-value labels for discovery / affinity.
        metadata: Additional unstructured metadata.
        hooks: Lifecycle hook callbacks.
    """

    spec_id: str = field(default_factory=_new_id)
    role: AgentRole = field(default_factory=AgentRole)
    capabilities: tuple[str, ...] = ()
    skills: tuple[SkillRequirement, ...] = ()
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.capabilities:
            raise InvalidSpecError("AgentSpec must declare at least one capability")

    def has_capability(self, capability: str) -> bool:
        """Check whether the spec includes a given capability."""
        return capability in self.capabilities

    def meets_skill_requirements(self, required: tuple[SkillRequirement, ...]) -> bool:
        """Check whether the spec satisfies a set of skill requirements."""
        skill_map: dict[str, SkillLevel] = {s.name: s.level for s in self.skills}
        for req in required:
            current = skill_map.get(req.name, SkillLevel.NOVICE)
            if current.value < req.level.value:
                return False
        return True

    @property
    def total_skill_score(self) -> float:
        """Sum of skill levels as a rough capability score."""
        return sum(s.level.value for s in self.skills)


# ---------------------------------------------------------------------------
# Lifecycle hooks (registry of async callbacks)
# ---------------------------------------------------------------------------


@dataclass
class LifecycleHooks:
    """Container for agent lifecycle hook callbacks.

    All hooks are optional async callables. Hooks that are not set
    are silently skipped.
    """

    on_spawn: Callable[[str, AgentSpec], Awaitable[None]] | None = None
    on_task_start: Callable[[str, str], Awaitable[None]] | None = None
    on_task_complete: Callable[[str, str, Any], Awaitable[None]] | None = None
    on_task_error: Callable[[str, str, Exception], Awaitable[None]] | None = None
    on_idle: Callable[[str], Awaitable[None]] | None = None
    on_retire: Callable[[str, AgentSpec], Awaitable[None]] | None = None
    on_evolve: Callable[[str, AgentSpec, AgentSpec], Awaitable[None]] | None = None

    async def fire_spawn(self, agent_id: str, spec: AgentSpec) -> None:
        if self.on_spawn:
            await self.on_spawn(agent_id, spec)

    async def fire_task_start(self, agent_id: str, task_id: str) -> None:
        if self.on_task_start:
            await self.on_task_start(agent_id, task_id)

    async def fire_task_complete(self, agent_id: str, task_id: str, result: Any) -> None:
        if self.on_task_complete:
            await self.on_task_complete(agent_id, task_id, result)

    async def fire_task_error(self, agent_id: str, task_id: str, error: Exception) -> None:
        if self.on_task_error:
            await self.on_task_error(agent_id, task_id, error)

    async def fire_idle(self, agent_id: str) -> None:
        if self.on_idle:
            await self.on_idle(agent_id)

    async def fire_retire(self, agent_id: str, spec: AgentSpec) -> None:
        if self.on_retire:
            await self.on_retire(agent_id, spec)

    async def fire_evolve(self, agent_id: str, old_spec: AgentSpec, new_spec: AgentSpec) -> None:
        if self.on_evolve:
            await self.on_evolve(agent_id, old_spec, new_spec)
