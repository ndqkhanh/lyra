"""Think-Build-Review-Test-Ship-Reflect sprint workflow model (gstack pattern)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto

from lyra_agent_swarm.exceptions import SprintError


class SprintPhase(Enum):
    """Phases of a sprint workflow in execution order."""

    THINK = auto()
    PLAN = auto()
    BUILD = auto()
    REVIEW = auto()
    TEST = auto()
    SHIP = auto()
    REFLECT = auto()


class SprintStatus(Enum):
    """Current status of a sprint."""

    PLANNING = auto()
    IN_PROGRESS = auto()
    REVIEWING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class SprintTask:
    """A single task within a sprint assigned to a specific phase and agent."""

    task_id: str
    phase: SprintPhase
    assigned_agent: str | None
    status: SprintStatus = SprintStatus.PLANNING
    artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Sprint:
    """Immutable representation of a sprint lifecycle."""

    sprint_id: str
    goal: str
    phases: tuple[SprintPhase, ...]
    agents: tuple[str, ...]
    start_time: float | None = None
    status: SprintStatus = SprintStatus.PLANNING
    current_phase_index: int = 0


@dataclass(frozen=True)
class SprintResult:
    """Outcome of a completed sprint."""

    sprint: Sprint
    completed_tasks: tuple[SprintTask, ...] = ()
    artifacts: tuple[str, ...] = ()
    review_notes: str = ""


@dataclass(frozen=True)
class SprintConfig:
    """Configuration that governs sprint behaviour and gating."""

    phase_timeouts: tuple[float, ...] = (300.0, 300.0, 600.0, 180.0, 300.0, 120.0, 180.0)
    auto_advance: bool = True
    require_review_gate: bool = True


_DEFAULT_PHASES: tuple[SprintPhase, ...] = (
    SprintPhase.THINK,
    SprintPhase.PLAN,
    SprintPhase.BUILD,
    SprintPhase.REVIEW,
    SprintPhase.TEST,
    SprintPhase.SHIP,
    SprintPhase.REFLECT,
)


class SprintModel:
    """Manages sprint lifecycle — creation, phase advancement, and finalization."""

    def __init__(self, config: SprintConfig | None = None) -> None:
        self._config = config or SprintConfig()
        self._sprints: dict[str, Sprint] = {}
        self._tasks: dict[str, list[SprintTask]] = {}

    @property
    def config(self) -> SprintConfig:
        return self._config

    def create_sprint(self, goal: str, agents: list[str], sprint_id: str | None = None) -> Sprint:
        sid = sprint_id or f"sprint-{int(time.time())}"
        sprint = Sprint(
            sprint_id=sid,
            goal=goal,
            phases=_DEFAULT_PHASES,
            agents=tuple(agents),
            start_time=time.time(),
            status=SprintStatus.IN_PROGRESS,
            current_phase_index=0,
        )
        self._sprints[sid] = sprint
        self._tasks[sid] = []
        return sprint

    def advance_phase(self, sprint: Sprint) -> Sprint:
        if sprint.status in (SprintStatus.COMPLETED, SprintStatus.FAILED):
            raise SprintError(f"Sprint '{sprint.sprint_id}' has already finished")

        next_index = sprint.current_phase_index + 1
        if next_index >= len(sprint.phases):
            finished = Sprint(
                sprint_id=sprint.sprint_id,
                goal=sprint.goal,
                phases=sprint.phases,
                agents=sprint.agents,
                start_time=sprint.start_time,
                status=SprintStatus.COMPLETED,
                current_phase_index=sprint.current_phase_index,
            )
            self._sprints[sprint.sprint_id] = finished
            return finished

        advanced = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phases=sprint.phases,
            agents=sprint.agents,
            start_time=sprint.start_time,
            status=SprintStatus.IN_PROGRESS,
            current_phase_index=next_index,
        )
        self._sprints[sprint.sprint_id] = advanced
        return advanced

    def get_sprint(self, sprint_id: str) -> Sprint | None:
        return self._sprints.get(sprint_id)

    def add_task(self, sprint_id: str, task: SprintTask) -> None:
        if sprint_id not in self._tasks:
            raise SprintError(f"Unknown sprint '{sprint_id}'")
        self._tasks[sprint_id].append(task)

    def get_tasks(self, sprint_id: str) -> tuple[SprintTask, ...]:
        return tuple(self._tasks.get(sprint_id, []))

    def fail_sprint(self, sprint: Sprint) -> Sprint:
        failed = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phases=sprint.phases,
            agents=sprint.agents,
            start_time=sprint.start_time,
            status=SprintStatus.FAILED,
            current_phase_index=sprint.current_phase_index,
        )
        self._sprints[sprint.sprint_id] = failed
        return failed

    def complete_sprint(self, sprint: Sprint, tasks: list[SprintTask] | None = None) -> SprintResult:
        done = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phases=sprint.phases,
            agents=sprint.agents,
            start_time=sprint.start_time,
            status=SprintStatus.COMPLETED,
            current_phase_index=len(sprint.phases) - 1,
        )
        self._sprints[sprint.sprint_id] = done
        all_artifacts: list[str] = []
        for t in (tasks or []):
            all_artifacts.extend(t.artifacts)
        return SprintResult(
            sprint=done,
            completed_tasks=tuple(tasks or []),
            artifacts=tuple(all_artifacts),
        )
