"""Specialized agent role definitions following the Oh-My-OpenAgent discipline pattern."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class AgentRole(Enum):
    """Discipline agent roles in the swarm hierarchy."""

    SISYPHUS = auto()  # executor — continuous iteration
    HEPHAESTUS = auto()  # builder — code generation
    PROMETHEUS = auto()  # foresight — risk assessment, architecture
    ORACLE = auto()  # deep reasoning — research synthesis
    LIBRARIAN = auto()  # knowledge — retrieval, skill lookup
    SENTINEL = auto()  # safety — policy enforcement, monitoring
    HERMES = auto()  # messaging — inter-agent coordination


class Capability(Enum):
    """Discrete skills a discipline agent can possess."""

    CODE_GEN = auto()
    CODE_REVIEW = auto()
    ARCHITECTURE = auto()
    RESEARCH = auto()
    SECURITY = auto()
    TESTING = auto()
    PLANNING = auto()
    DEBUGGING = auto()
    DOCS = auto()
    DEPLOYMENT = auto()


@dataclass(frozen=True)
class DisciplineAgent:
    """Immutable definition of a discipline agent with role, model tier, and capabilities."""

    agent_id: str
    name: str
    role: AgentRole
    model_tier: str
    capabilities: frozenset[Capability]
    priority: int
    is_blocking: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.capabilities, frozenset):
            object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        if self.priority < 0:
            raise ValueError("priority must be non-negative")


# ---------------------------------------------------------------------------
# Pre-built discipline agents with recommended model tiers
# ---------------------------------------------------------------------------

SISYPHUS = DisciplineAgent(
    agent_id="sisyphus-001",
    name="Sisyphus",
    role=AgentRole.SISYPHUS,
    model_tier="sonnet",
    capabilities=frozenset({Capability.CODE_GEN, Capability.DEBUGGING}),
    priority=10,
)

HEPHAESTUS = DisciplineAgent(
    agent_id="hephaestus-001",
    name="Hephaestus",
    role=AgentRole.HEPHAESTUS,
    model_tier="sonnet",
    capabilities=frozenset({Capability.CODE_GEN, Capability.ARCHITECTURE, Capability.CODE_REVIEW}),
    priority=9,
)

PROMETHEUS = DisciplineAgent(
    agent_id="prometheus-001",
    name="Prometheus",
    role=AgentRole.PROMETHEUS,
    model_tier="opus",
    capabilities=frozenset({Capability.ARCHITECTURE, Capability.PLANNING, Capability.CODE_REVIEW}),
    priority=8,
)

ORACLE = DisciplineAgent(
    agent_id="oracle-001",
    name="Oracle",
    role=AgentRole.ORACLE,
    model_tier="opus",
    capabilities=frozenset({Capability.RESEARCH, Capability.ARCHITECTURE}),
    priority=7,
)

LIBRARIAN = DisciplineAgent(
    agent_id="librarian-001",
    name="Librarian",
    role=AgentRole.LIBRARIAN,
    model_tier="haiku",
    capabilities=frozenset({Capability.RESEARCH, Capability.DOCS}),
    priority=5,
    is_blocking=False,
)

SENTINEL = DisciplineAgent(
    agent_id="sentinel-001",
    name="Sentinel",
    role=AgentRole.SENTINEL,
    model_tier="haiku",
    capabilities=frozenset({Capability.SECURITY, Capability.CODE_REVIEW}),
    priority=6,
    is_blocking=True,
)

HERMES = DisciplineAgent(
    agent_id="hermes-001",
    name="Hermes",
    role=AgentRole.HERMES,
    model_tier="haiku",
    capabilities=frozenset({Capability.DOCS, Capability.DEPLOYMENT}),
    priority=4,
)

_PREBUILT: tuple[DisciplineAgent, ...] = (
    SISYPHUS,
    HEPHAESTUS,
    PROMETHEUS,
    ORACLE,
    LIBRARIAN,
    SENTINEL,
    HERMES,
)


class AgentRegistry:
    """Manages registration and lookup of discipline agents."""

    def __init__(self, prebuilt: bool = True) -> None:
        self._agents: dict[str, DisciplineAgent] = {}
        if prebuilt:
            for agent in _PREBUILT:
                self._agents[agent.agent_id] = agent

    @property
    def agents(self) -> dict[str, DisciplineAgent]:
        return dict(self._agents)

    def register(self, agent: DisciplineAgent) -> None:
        if agent.agent_id in self._agents:
            raise ValueError(f"Agent '{agent.agent_id}' is already registered")
        self._agents[agent.agent_id] = agent

    def get_by_role(self, role: AgentRole) -> list[DisciplineAgent]:
        return [a for a in self._agents.values() if a.role == role]

    def get_capable(self, capability: Capability) -> list[DisciplineAgent]:
        return [a for a in self._agents.values() if capability in a.capabilities]
