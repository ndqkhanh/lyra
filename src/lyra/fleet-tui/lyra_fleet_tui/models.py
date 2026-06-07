"""Data models for the Lyra Fleet TUI."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class TaskState(str, enum.Enum):
    """Current state of an agent's primary task."""

    WORKING = "working"
    NEEDS_INPUT = "needs_input"
    IDLE = "idle"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ProcessLiveness(str, enum.Enum):
    """Liveness status of the agent subprocess with display symbols."""

    ACTIVE = "active"  # ◉ (circle-star)
    PAUSED = "paused"  # • (bullet)
    STOPPED = "stopped"  # ◎ (circle-dot)

    @property
    def symbol(self) -> str:
        symbols = {
            ProcessLiveness.ACTIVE: "◉",
            ProcessLiveness.PAUSED: "•",
            ProcessLiveness.STOPPED: "◎",
        }
        return symbols[self]


@dataclass(frozen=True)
class AgentState:
    """Immutable snapshot of a single fleet agent."""

    agent_id: str
    name: str
    task_state: TaskState = TaskState.IDLE
    liveness: ProcessLiveness = ProcessLiveness.STOPPED
    model: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    current_task: str = ""
    last_active: Optional[datetime] = None
    git_branch: str = ""
    pr_label: str = ""
    pane_id: str = ""

    @property
    def display_name(self) -> str:
        return (self.name or self.agent_id)[:16]


@dataclass
class FleetData:
    """Mutable container for the full fleet snapshot received from the supervisor."""

    agents: list[AgentState] = field(default_factory=list)
    totals: dict[str, int] = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        return len(self.agents)

    @property
    def active_count(self) -> int:
        return sum(
            1
            for a in self.agents
            if a.liveness is ProcessLiveness.ACTIVE
        )

    @property
    def working_count(self) -> int:
        return sum(
            1
            for a in self.agents
            if a.task_state is TaskState.WORKING
        )


@dataclass
class FleetSummary:
    """Computed summary statistics derived from FleetData."""

    total_agents: int = 0
    active: int = 0
    working: int = 0
    idle: int = 0
    needs_input: int = 0
    completed: int = 0
    failed: int = 0
    stopped: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    by_liveness: dict[str, int] = field(default_factory=dict)
    by_task_state: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_fleet_data(cls, data: FleetData) -> FleetSummary:
        by_liveness: dict[str, int] = {}
        by_task_state: dict[str, int] = {}
        total_tokens = 0
        total_cost = 0.0

        for agent in data.agents:
            by_liveness[agent.liveness.value] = (
                by_liveness.get(agent.liveness.value, 0) + 1
            )
            by_task_state[agent.task_state.value] = (
                by_task_state.get(agent.task_state.value, 0) + 1
            )
            total_tokens += agent.tokens_used
            total_cost += agent.cost_usd

        for ts in TaskState:
            by_task_state.setdefault(ts.value, 0)
        for pl in ProcessLiveness:
            by_liveness.setdefault(pl.value, 0)

        return cls(
            total_agents=len(data.agents),
            active=by_liveness.get(ProcessLiveness.ACTIVE.value, 0),
            working=by_task_state.get(TaskState.WORKING.value, 0),
            idle=by_task_state.get(TaskState.IDLE.value, 0),
            needs_input=by_task_state.get(TaskState.NEEDS_INPUT.value, 0),
            completed=by_task_state.get(TaskState.COMPLETED.value, 0),
            failed=by_task_state.get(TaskState.FAILED.value, 0),
            stopped=by_liveness.get(ProcessLiveness.STOPPED.value, 0),
            total_tokens=total_tokens,
            total_cost=round(total_cost, 4),
            by_liveness=by_liveness,
            by_task_state=by_task_state,
        )


@dataclass
class AgentFilter:
    """Filter criteria for the agent table."""

    task_state: Optional[TaskState] = None
    liveness: Optional[ProcessLiveness] = None
    search: str = ""

    def matches(self, agent: AgentState) -> bool:
        if self.task_state is not None and agent.task_state != self.task_state:
            return False
        if self.liveness is not None and agent.liveness != self.liveness:
            return False
        if self.search:
            lower = self.search.lower()
            if (
                lower not in agent.name.lower()
                and lower not in agent.agent_id.lower()
                and lower not in agent.current_task.lower()
                and lower not in agent.git_branch.lower()
                and lower not in agent.pr_label.lower()
            ):
                return False
        return True

    def clone(self) -> AgentFilter:
        return AgentFilter(
            task_state=self.task_state,
            liveness=self.liveness,
            search=self.search,
        )

    @classmethod
    def from_task_state(cls, state: TaskState) -> AgentFilter:
        return cls(task_state=state)

    @classmethod
    def from_liveness(cls, liveness: ProcessLiveness) -> AgentFilter:
        return cls(liveness=liveness)

    @classmethod
    def from_search(cls, query: str) -> AgentFilter:
        return cls(search=query)
