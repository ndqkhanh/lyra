"""Agent sprint pipeline for Lyra team orchestration.

Implements a sprint-based execution model for agent teams with phased
workflows, task decomposition, dependency tracking, and retrospectives.
Integrates with the Dispatcher for task assignment and CoalitionFormer
for dynamic team formation.

Architecture:
    - SprintPhase: 5-phase sprint lifecycle
    - SprintTask: individual task with dependency tracking
    - SprintPipeline: orchestration engine for team sprints
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SprintPhase(StrEnum):
    """Phases of a team sprint."""

    PLANNING = "planning"
    DECOMPOSITION = "decomposition"
    EXECUTION = "execution"
    REVIEW = "review"
    RETROSPECTIVE = "retrospective"


class TaskStatus(StrEnum):
    """Status of a sprint task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class SprintTask:
    """A single task within a sprint.

    Attributes:
        task_id: unique identifier
        title: short description
        description: detailed task description
        assigned_agent: which agent/discipline is assigned
        priority: task priority level
        estimated_effort_min: estimated effort in minutes
        status: current task status
        depends_on: task IDs this task depends on
        output: task output upon completion
        started_at: when work began
        completed_at: when work finished
    """

    task_id: str
    title: str
    description: str
    assigned_agent: str
    priority: TaskPriority
    estimated_effort_min: float
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = field(default_factory=list)
    output: str | None = None
    started_at: float | None = None
    completed_at: float | None = None

    @property
    def is_blocked(self) -> bool:
        return self.status == TaskStatus.BLOCKED

    @property
    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED


@dataclass(frozen=True)
class Sprint:
    """A team sprint with tasks and phases.

    Attributes:
        sprint_id: unique identifier
        goal: the sprint goal / objective
        phase: current sprint phase
        tasks: tasks in this sprint
        team_agents: agents participating in this sprint
        created_at: sprint creation timestamp
        started_at: when execution began
        completed_at: when sprint completed
        retrospective_notes: learnings from retrospective
    """

    sprint_id: str
    goal: str
    phase: SprintPhase
    tasks: list[SprintTask]
    team_agents: list[str]
    created_at: float
    started_at: float | None = None
    completed_at: float | None = None
    retrospective_notes: str | None = None

    @property
    def is_active(self) -> bool:
        return self.started_at is not None and self.completed_at is None

    @property
    def progress_pct(self) -> float:
        if not self.tasks:
            return 100.0
        completed = sum(1 for t in self.tasks if t.is_completed)
        return (completed / len(self.tasks)) * 100

    @property
    def blocked_tasks(self) -> list[SprintTask]:
        return [t for t in self.tasks if t.is_blocked]


class SprintPipeline:
    """Orchestration engine for agent team sprints.

    Manages the full sprint lifecycle: planning → decomposition →
    execution → review → retrospective. Integrates with the agent
    swarm Dispatcher for task assignment.

    Usage::

        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(
            goal="Implement user authentication flow",
            team_agents=["sentinel", "hephaestus", "hermes"],
        )
        pipeline.decompose_goal(sprint.sprint_id, task_descriptions=[
            ("Design auth schema", "sentinel", TaskPriority.HIGH, 30.0),
            ("Implement login endpoint", "hephaestus", TaskPriority.CRITICAL, 60.0),
        ])
        pipeline.start(sprint.sprint_id)
    """

    def __init__(self) -> None:
        self._sprints: dict[str, Sprint] = {}
        self._history: list[Sprint] = []

    def create_sprint(
        self,
        goal: str,
        team_agents: list[str],
    ) -> Sprint:
        """Create a new sprint with the given goal and team."""
        sprint_id = hashlib.sha256(
            f"{goal}|{time.time()}|{uuid.uuid4()}".encode()
        ).hexdigest()[:16]

        sprint = Sprint(
            sprint_id=sprint_id,
            goal=goal,
            phase=SprintPhase.PLANNING,
            tasks=[],
            team_agents=list(team_agents),
            created_at=time.time(),
        )
        self._sprints[sprint_id] = sprint
        return sprint

    def decompose_goal(
        self,
        sprint_id: str,
        task_descriptions: list[tuple[str, str, TaskPriority, float]],
    ) -> list[SprintTask]:
        """Decompose the sprint goal into concrete tasks."""
        sprint = self._sprints.get(sprint_id)
        if sprint is None:
            raise KeyError(f"Sprint {sprint_id} not found")

        tasks: list[SprintTask] = []
        for title, agent, priority, effort in task_descriptions:
            task_id = hashlib.sha256(
                f"{sprint_id}|{title}|{agent}".encode()
            ).hexdigest()[:12]
            task = SprintTask(
                task_id=task_id,
                title=title,
                description=title,
                assigned_agent=agent,
                priority=priority,
                estimated_effort_min=effort,
            )
            tasks.append(task)

        updated = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phase=SprintPhase.DECOMPOSITION,
            tasks=sprint.tasks + tasks,
            team_agents=sprint.team_agents,
            created_at=sprint.created_at,
            started_at=sprint.started_at,
            completed_at=sprint.completed_at,
            retrospective_notes=sprint.retrospective_notes,
        )
        self._sprints[sprint_id] = updated
        return tasks

    def add_dependency(self, sprint_id: str, task_id: str, depends_on_id: str) -> bool:
        """Add a dependency between two tasks in a sprint."""
        sprint = self._sprints.get(sprint_id)
        if sprint is None:
            return False

        new_tasks: list[SprintTask] = []
        found = False
        for t in sprint.tasks:
            if t.task_id == task_id:
                new_deps = list(t.depends_on)
                if depends_on_id not in new_deps:
                    new_deps.append(depends_on_id)
                new_tasks.append(SprintTask(
                    task_id=t.task_id,
                    title=t.title,
                    description=t.description,
                    assigned_agent=t.assigned_agent,
                    priority=t.priority,
                    estimated_effort_min=t.estimated_effort_min,
                    status=t.status,
                    depends_on=new_deps,
                    output=t.output,
                    started_at=t.started_at,
                    completed_at=t.completed_at,
                ))
                found = True
            else:
                new_tasks.append(t)

        if found:
            self._sprints[sprint_id] = Sprint(
                sprint_id=sprint.sprint_id,
                goal=sprint.goal,
                phase=sprint.phase,
                tasks=new_tasks,
                team_agents=sprint.team_agents,
                created_at=sprint.created_at,
                started_at=sprint.started_at,
                completed_at=sprint.completed_at,
                retrospective_notes=sprint.retrospective_notes,
            )
        return found

    def start(self, sprint_id: str) -> Sprint | None:
        """Start sprint execution."""
        sprint = self._sprints.get(sprint_id)
        if sprint is None:
            return None

        updated = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phase=SprintPhase.EXECUTION,
            tasks=sprint.tasks,
            team_agents=sprint.team_agents,
            created_at=sprint.created_at,
            started_at=time.time(),
            completed_at=None,
            retrospective_notes=sprint.retrospective_notes,
        )
        self._sprints[sprint_id] = updated
        return updated

    def update_task_status(
        self, sprint_id: str, task_id: str, status: TaskStatus, output: str | None = None
    ) -> SprintTask | None:
        """Update a task's status and optionally its output."""
        sprint = self._sprints.get(sprint_id)
        if sprint is None:
            return None

        updated_task: SprintTask | None = None
        new_tasks: list[SprintTask] = []
        for t in sprint.tasks:
            if t.task_id == task_id:
                updated_task = SprintTask(
                    task_id=t.task_id,
                    title=t.title,
                    description=t.description,
                    assigned_agent=t.assigned_agent,
                    priority=t.priority,
                    estimated_effort_min=t.estimated_effort_min,
                    status=status,
                    depends_on=t.depends_on,
                    output=output,
                    started_at=t.started_at if status != TaskStatus.IN_PROGRESS else (t.started_at or time.time()),
                    completed_at=time.time() if status == TaskStatus.COMPLETED else t.completed_at,
                )
                new_tasks.append(updated_task)
            else:
                new_tasks.append(t)

        self._sprints[sprint_id] = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phase=sprint.phase,
            tasks=new_tasks,
            team_agents=sprint.team_agents,
            created_at=sprint.created_at,
            started_at=sprint.started_at,
            completed_at=sprint.completed_at,
            retrospective_notes=sprint.retrospective_notes,
        )

        # Check if all tasks complete → auto-advance to review phase
        if all(t.is_completed or t.status == TaskStatus.SKIPPED for t in new_tasks):
            self._advance_phase(sprint_id, SprintPhase.REVIEW)

        return updated_task

    def complete_sprint(self, sprint_id: str, retrospective_notes: str = "") -> Sprint | None:
        """Complete a sprint with retrospective notes."""
        sprint = self._sprints.get(sprint_id)
        if sprint is None:
            return None

        updated = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phase=SprintPhase.RETROSPECTIVE,
            tasks=sprint.tasks,
            team_agents=sprint.team_agents,
            created_at=sprint.created_at,
            started_at=sprint.started_at,
            completed_at=time.time(),
            retrospective_notes=retrospective_notes,
        )
        self._sprints[sprint_id] = updated
        self._history.append(updated)
        return updated

    def _advance_phase(self, sprint_id: str, phase: SprintPhase) -> None:
        sprint = self._sprints.get(sprint_id)
        if sprint is None:
            return
        self._sprints[sprint_id] = Sprint(
            sprint_id=sprint.sprint_id,
            goal=sprint.goal,
            phase=phase,
            tasks=sprint.tasks,
            team_agents=sprint.team_agents,
            created_at=sprint.created_at,
            started_at=sprint.started_at,
            completed_at=sprint.completed_at,
            retrospective_notes=sprint.retrospective_notes,
        )

    def get_sprint(self, sprint_id: str) -> Sprint | None:
        return self._sprints.get(sprint_id)

    def get_active_sprints(self) -> list[Sprint]:
        return [s for s in self._sprints.values() if s.is_active]

    def get_next_available_tasks(self, sprint_id: str) -> list[SprintTask]:
        """Get tasks ready to be worked on (all deps satisfied)."""
        sprint = self._sprints.get(sprint_id)
        if sprint is None:
            return []

        completed_ids = {t.task_id for t in sprint.tasks if t.is_completed}
        return [
            t for t in sprint.tasks
            if t.status == TaskStatus.PENDING
            and all(dep in completed_ids for dep in t.depends_on)
        ]

    def stats(self) -> dict[str, Any]:
        active = self.get_active_sprints()
        return {
            "total_sprints": len(self._sprints),
            "active_sprints": len(active),
            "completed_sprints": len(self._history),
            "active_goals": [s.goal for s in active],
        }
