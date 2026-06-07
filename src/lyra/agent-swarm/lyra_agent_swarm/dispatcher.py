"""Task classification and specialist routing for the agent swarm."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from heapq import heappop, heappush
from typing import Any

from lyra.agent_swarm.discipline_agents import AgentRegistry, Capability, DisciplineAgent


class TaskPriority(Enum):
    """Urgency level for a task ticket."""

    CRITICAL = auto()
    HIGH = auto()
    NORMAL = auto()
    LOW = auto()
    BACKGROUND = auto()


class DispatchStrategy(Enum):
    """Strategy used to assign agents to a task."""

    SINGLE_AGENT = auto()
    SQUAD = auto()
    COALITION = auto()
    ROUND_ROBIN = auto()
    LOAD_BALANCED = auto()


@dataclass(frozen=True)
class TaskTicket:
    """Immutable task description to be dispatched to agents."""

    task_id: str
    description: str
    required_capabilities: frozenset[Capability] = field(default_factory=frozenset)
    priority: TaskPriority = TaskPriority.NORMAL
    deadline: float | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DispatchConfig:
    """Configuration governing dispatcher behaviour."""

    max_agents_per_task: int = 3
    prefer_specialists: bool = True
    load_balance: bool = True


@dataclass(frozen=True)
class DispatchDecision:
    """Result of a dispatch operation — which agents were chosen and why."""

    task: TaskTicket
    assigned_agents: tuple[DisciplineAgent, ...]
    strategy: DispatchStrategy
    reasoning: str


class TaskQueue:
    """Priority-ordered task queue (highest priority dequeued first)."""

    _PRIORITY_ORDER: dict[TaskPriority, int] = {
        TaskPriority.CRITICAL: 0,
        TaskPriority.HIGH: 1,
        TaskPriority.NORMAL: 2,
        TaskPriority.LOW: 3,
        TaskPriority.BACKGROUND: 4,
    }

    def __init__(self) -> None:
        self._items: list[tuple[int, int, TaskTicket]] = []
        self._counter: int = 0

    def push(self, task: TaskTicket) -> None:
        order = self._PRIORITY_ORDER.get(task.priority, 99)
        heappush(self._items, (order, self._counter, task))
        self._counter += 1

    def pop(self) -> TaskTicket | None:
        if not self._items:
            return None
        return heappop(self._items)[2]

    def peek(self) -> TaskTicket | None:
        if not self._items:
            return None
        return self._items[0][2]

    @property
    def size(self) -> int:
        return len(self._items)

    @property
    def is_empty(self) -> bool:
        return len(self._items) == 0


class Dispatcher:
    """Classifies incoming tasks and routes them to the most appropriate agents."""

    def __init__(self, registry: AgentRegistry, config: DispatchConfig | None = None) -> None:
        self._registry = registry
        self._config = config or DispatchConfig()
        self._queue = TaskQueue()
        self._task_load: dict[str, int] = {}

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    @property
    def config(self) -> DispatchConfig:
        return self._config

    @property
    def queue(self) -> TaskQueue:
        return self._queue

    def classify_task(self, task: TaskTicket) -> dict[Capability, float]:
        """Score each required capability for the given task (1.0 = required)."""
        return dict.fromkeys(task.required_capabilities, 1.0)

    def dispatch(self, task: TaskTicket) -> DispatchDecision:
        """Select the best agents for a task and return a dispatch decision."""
        self.classify_task(task)

        qualified: list[DisciplineAgent] = []
        for cap in task.required_capabilities:
            qualified.extend(self._registry.get_capable(cap))

        seen: set[str] = set()
        unique_qualified: list[DisciplineAgent] = []
        for agent in qualified:
            if agent.agent_id not in seen:
                seen.add(agent.agent_id)
                unique_qualified.append(agent)

        scored_agents = [
            (
                sum(1 for c in task.required_capabilities if c in agent.capabilities),
                len(agent.capabilities),
                agent.priority,
                agent,
            )
            for agent in unique_qualified
        ]
        scored_agents.sort(key=lambda x: (-x[0], -x[1], -x[2]))

        max_agents = min(self._config.max_agents_per_task, len(scored_agents))
        selected: tuple[DisciplineAgent, ...] = tuple(
            agent for _, _, _, agent in scored_agents[:max_agents]
        )

        if not selected:
            from lyra.agent_swarm.exceptions import DispatchError

            raise DispatchError(
                f"No capable agents found for task '{task.task_id}' requiring "
                f"{[c.name for c in task.required_capabilities]}"
            )

        for agent in selected:
            self._task_load[agent.agent_id] = self._task_load.get(agent.agent_id, 0) + 1

        strategy = DispatchStrategy.SINGLE_AGENT if len(selected) == 1 else DispatchStrategy.SQUAD

        return DispatchDecision(
            task=task,
            assigned_agents=selected,
            strategy=strategy,
            reasoning=(
                f"Assigned {len(selected)} agent(s) matching "
                f"{len(task.required_capabilities)} required capabilities"
            ),
        )

    def submit(self, task: TaskTicket) -> None:
        """Enqueue a task for later dispatch."""
        self._queue.push(task)
