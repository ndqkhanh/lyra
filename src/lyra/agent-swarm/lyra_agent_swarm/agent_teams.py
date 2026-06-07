"""Agent Teams — team formation, shared task queues, role assignment, and quality gates."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum, auto

from lyra.agent_swarm.exceptions import SwarmError
from lyra.agent_swarm.team_messaging import TeamMessaging

logger = logging.getLogger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────────


class TeamError(SwarmError):
    """Raised when a team operation fails."""


# ── Enums ────────────────────────────────────────────────────────────────────


class TeamRole(Enum):
    """Role an agent can hold within a team.

    Attributes
    ----------
    COORDINATOR
        Leads the team and owns task orchestration.
    EXECUTOR
        Performs assigned work items.
    REVIEWER
        Validates completed work against quality gates.
    OBSERVER
        Monitors team activity without direct participation.
    """

    COORDINATOR = auto()
    EXECUTOR = auto()
    REVIEWER = auto()
    OBSERVER = auto()


class TaskStatus(Enum):
    """Current state of a task in the team workflow.

    Attributes
    ----------
    PENDING
        Task created but not yet started.
    IN_PROGRESS
        Task is actively being worked on.
    BLOCKED
        Task cannot proceed until dependencies are resolved.
    COMPLETED
        Task has been finished successfully.
    FAILED
        Task finished with an error or unmet quality gate.
    """

    PENDING = auto()
    IN_PROGRESS = auto()
    BLOCKED = auto()
    COMPLETED = auto()
    FAILED = auto()


# ── Data Models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TaskDependency:
    """Links a task to its prerequisite tasks.

    Attributes
    ----------
    task_id : str
        Identifier of the dependent task.
    depends_on : tuple[str, ...]
        Identifiers of tasks that must complete first.
    """

    task_id: str
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class TeamTask:
    """An immutable task assigned within a team.

    Attributes
    ----------
    task_id : str
        Unique identifier for this task.
    description : str
        Human-readable description of the work to be done.
    assigned_to : str | None
        Agent ID of the assignee, or None if unassigned.
    status : TaskStatus
        Current lifecycle state of the task.
    priority : int
        Numeric priority where higher values indicate greater urgency.
    dependencies : tuple[str, ...]
        Task IDs that must complete before this task can proceed.
    quality_gate : str
        Name of the quality gate to pass before completion, or empty string.
    created_at : float
        Unix timestamp when the task was created.
    completed_at : float | None
        Unix timestamp when the task was completed, or None.
    """

    task_id: str
    description: str
    assigned_to: str | None
    status: TaskStatus
    priority: int
    dependencies: tuple[str, ...]
    quality_gate: str
    created_at: float
    completed_at: float | None


@dataclass(frozen=True)
class Team:
    """Immutable definition of an agent team.

    Attributes
    ----------
    team_id : str
        Unique identifier for the team.
    name : str
        Human-readable team name.
    members : tuple[str, ...]
        Agent IDs belonging to the team.
    tasks : tuple[TeamTask, ...]
        Snapshot of the team's current task list.
    goal : str
        High-level objective this team is working toward.
    """

    team_id: str
    name: str
    members: tuple[str, ...]
    tasks: tuple[TeamTask, ...]
    goal: str


@dataclass(frozen=True)
class QualityGate:
    """Validation gate that a task must pass before being marked complete.

    Attributes
    ----------
    name : str
        Unique name for this quality gate.
    check_fn : Callable[[TeamTask], bool]
        Function that receives the task and returns True if it passes.
    description : str
        Human-readable explanation of what this gate validates.
    required_approvals : int
        Minimum number of approvals (e.g., reviewer sign-offs) required.
    """

    name: str
    check_fn: Callable[[TeamTask], bool]
    description: str
    required_approvals: int


@dataclass(frozen=True)
class LifecycleHook:
    """Hook triggered at specific stages of the task lifecycle.

    Attributes
    ----------
    event : str
        Lifecycle event that fires this hook. One of ``"pre_task"``,
        ``"post_task"``, or ``"on_blocked"``.
    action : Callable[[TeamTask], None]
        Callback invoked when the event occurs.
    description : str
        Human-readable description of what this hook does.
    """

    event: str
    action: Callable[[TeamTask], None]
    description: str


@dataclass(frozen=True)
class TeamMetrics:
    """Aggregated performance data for a team.

    Attributes
    ----------
    total_tasks : int
        Total number of tasks created for the team.
    completed : int
        Number of tasks that reached COMPLETED status.
    blocked : int
        Number of tasks currently in BLOCKED status.
    failed : int
        Number of tasks in FAILED status.
    avg_completion_time_ms : float
        Mean time from creation to completion in milliseconds.
    """

    total_tasks: int
    completed: int
    blocked: int
    failed: int
    avg_completion_time_ms: float


# ── Internal Helpers ─────────────────────────────────────────────────────────


def _next_task_id(team_id: str, counter: int) -> str:
    """Generate a unique task identifier within a team."""
    return f"task-{team_id}-{counter}"


def _compute_completion_time(
    completed_tasks: list[TeamTask],
) -> float:
    """Calculate mean completion time in milliseconds for a list of completed tasks."""
    if not completed_tasks:
        return 0.0
    total_ms = 0.0
    for t in completed_tasks:
        if t.completed_at is not None and t.created_at > 0:
            total_ms += (t.completed_at - t.created_at) * 1000.0
    return total_ms / len(completed_tasks)


# ── Agent Teams ──────────────────────────────────────────────────────────────


class AgentTeams:
    """Manages agent teams, shared task queues, role assignment, and quality gates.

    Provides thread-safe operations on teams and their task lists, with support
    for dependency tracking, lifecycle hooks, quality gate validation, and
    optional integration with :class:`TeamMessaging` for inter-agent notifications.

    The internal task store is protected by a ``threading.Lock`` for in-process
    race prevention. For cross-process coordination, pass *lock_file* to create
    an advisory file lock (extension point).

    Parameters
    ----------
    lock_file : str | None
        Path to an advisory lock file for cross-process safety (optional).
    messaging : TeamMessaging | None
        Optional messaging system for inter-agent notifications.
    """

    def __init__(
        self,
        lock_file: str | None = None,
        messaging: TeamMessaging | None = None,
    ) -> None:
        self._lock_path = lock_file
        self._messaging = messaging
        self._lock = threading.Lock()
        self._teams: dict[str, Team] = {}
        self._tasks: dict[str, dict[str, TeamTask]] = {}
        self._gates: dict[str, list[QualityGate]] = defaultdict(list)
        self._hooks: dict[str, list[LifecycleHook]] = defaultdict(list)
        self._team_counter: int = 0
        self._task_counter: dict[str, int] = defaultdict(int)

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def teams(self) -> dict[str, Team]:
        """Read-only snapshot of all registered teams."""
        return dict(self._teams)

    @property
    def lock_path(self) -> str | None:
        """Path to the advisory lock file, if configured."""
        return self._lock_path

    # ── Team Lifecycle ────────────────────────────────────────────────────

    def create_team(self, name: str, goal: str, members: list[str]) -> Team:
        """Create a new team with the given name, goal, and member list.

        Parameters
        ----------
        name : str
            Human-readable team name.
        goal : str
            High-level objective for the team.
        members : list[str]
            Agent IDs that belong to this team.

        Returns
        -------
        Team
            The newly created team definition.
        """
        if not members:
            raise TeamError("A team must have at least one member")
        with self._lock:
            self._team_counter += 1
            team_id = f"team-{self._team_counter}"
            team = Team(
                team_id=team_id,
                name=name,
                members=tuple(members),
                tasks=(),
                goal=goal,
            )
            self._teams[team_id] = team
            self._tasks[team_id] = {}
            logger.info(
                "Created team '%s' (%s) with %d members",
                team_id,
                name,
                len(members),
            )
            return team

    def get_team(self, team_id: str) -> Team | None:
        """Retrieve a team by its identifier.

        Parameters
        ----------
        team_id : str
            Unique team identifier.

        Returns
        -------
        Team | None
            The team if found, or None.
        """
        return self._teams.get(team_id)

    def remove_team(self, team_id: str) -> None:
        """Remove a team and all of its tasks.

        Parameters
        ----------
        team_id : str
            Unique team identifier.

        Raises
        ------
        TeamError
            If the team does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        with self._lock:
            del self._teams[team_id]
            self._tasks.pop(team_id, None)
            self._gates.pop(team_id, None)
            self._hooks.pop(team_id, None)
            self._task_counter.pop(team_id, None)
            logger.info("Removed team '%s'", team_id)

    # ── Task Management ───────────────────────────────────────────────────

    def add_task(
        self,
        team_id: str,
        description: str,
        priority: int = 0,
        dependencies: tuple[str, ...] = (),
        quality_gate: str | None = None,
    ) -> TeamTask:
        """Add a new task to a team's task list.

        If the task has dependencies that are not yet completed, it is created
        in the BLOCKED state. Otherwise it starts as PENDING.

        Parameters
        ----------
        team_id : str
            Team to add the task to.
        description : str
            Description of the work to be done.
        priority : int
            Numeric priority (higher = more urgent).
        dependencies : tuple[str, ...]
            Task IDs that must complete first.
        quality_gate : str | None
            Name of the quality gate to enforce, or None.

        Returns
        -------
        TeamTask
            The newly created task.

        Raises
        ------
        TeamError
            If the team does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        with self._lock:
            self._task_counter[team_id] += 1
            task_id = _next_task_id(team_id, self._task_counter[team_id])
            now = time.time()

            # Determine initial status based on dependency completeness
            status = TaskStatus.PENDING
            if dependencies:
                team_tasks = self._tasks.get(team_id, {})
                for dep_id in dependencies:
                    dep_task = team_tasks.get(dep_id)
                    if dep_task is None or dep_task.status != TaskStatus.COMPLETED:
                        status = TaskStatus.BLOCKED
                        break

            task = TeamTask(
                task_id=task_id,
                description=description,
                assigned_to=None,
                status=status,
                priority=priority,
                dependencies=dependencies,
                quality_gate=quality_gate or "",
                created_at=now,
                completed_at=None,
            )
            self._tasks[team_id][task_id] = task
            self._sync_team_tasks(team_id)

            if status is TaskStatus.BLOCKED:
                self._fire_hooks(team_id, "on_blocked", task)

            if self._messaging is not None:
                self._notify_team(team_id, f"New task added: {description}")

            logger.info(
                "Added task '%s' to team '%s' (status=%s)",
                task_id,
                team_id,
                status.name,
            )
            return task

    def assign_task(self, team_id: str, task_id: str, agent_id: str) -> TeamTask:
        """Assign a task to a specific agent.

        Parameters
        ----------
        team_id : str
            Team containing the task.
        task_id : str
            Task to assign.
        agent_id : str
            Agent to assign the task to.

        Returns
        -------
        TeamTask
            The updated task with the new assignee.

        Raises
        ------
        TeamError
            If the team or task does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        with self._lock:
            task = self._get_task(team_id, task_id)
            updated = replace(task, assigned_to=agent_id)
            self._tasks[team_id][task_id] = updated
            self._sync_team_tasks(team_id)

            if self._messaging is not None:
                self._messaging.send(
                    sender="system",
                    recipient=agent_id,
                    subject=f"Task assigned: {task.description}",
                    body=(
                        f"You have been assigned task '{task.description}' "
                        f"in team '{team_id}'."
                    ),
                )

            logger.info(
                "Assigned task '%s' to agent '%s'", task_id, agent_id,
            )
            return updated

    def update_task_status(
        self,
        team_id: str,
        task_id: str,
        status: TaskStatus,
    ) -> TeamTask:
        """Update the status of a task.

        When a task transitions to COMPLETED, any dependent BLOCKED tasks in the
        same team are automatically re-evaluated. Completed tasks are validated
        against their configured quality gate; failures set status to FAILED.

        Parameters
        ----------
        team_id : str
            Team containing the task.
        task_id : str
            Task to update.
        status : TaskStatus
            New status for the task.

        Returns
        -------
        TeamTask
            The updated task (potentially with a different status if gate validation
            or dependency re-evaluation occurred).

        Raises
        ------
        TeamError
            If the team or task does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        with self._lock:
            task = self._get_task(team_id, task_id)
            now = time.time()

            # Run quality gate validation before marking COMPLETED
            effective_status = status
            completed_at: float | None = None
            if status is TaskStatus.COMPLETED:
                if not self._validate_task_internal(team_id, task):
                    effective_status = TaskStatus.FAILED
                    logger.warning(
                        "Task '%s' failed quality gate validation", task_id,
                    )
                else:
                    completed_at = now

            updated = replace(
                task,
                status=effective_status,
                completed_at=completed_at,
            )
            self._tasks[team_id][task_id] = updated
            self._sync_team_tasks(team_id)

            # Fire lifecycle hooks
            if effective_status is TaskStatus.BLOCKED:
                self._fire_hooks(team_id, "on_blocked", updated)
            self._fire_hooks(team_id, "post_task", updated)

            # Re-evaluate dependencies for dependent tasks
            if effective_status is TaskStatus.COMPLETED:
                self._unblock_dependents(team_id, task_id)

            if self._messaging is not None and task.assigned_to is not None:
                self._messaging.send(
                    sender="system",
                    recipient=task.assigned_to,
                    subject=f"Task status updated: {task.description}",
                    body=(
                        f"Task '{task.description}' changed from "
                        f"{task.status.name} to {effective_status.name}."
                    ),
                )

            logger.info(
                "Task '%s' status changed: %s -> %s",
                task_id,
                task.status.name,
                effective_status.name,
            )
            return updated

    def get_task(self, team_id: str, task_id: str) -> TeamTask | None:
        """Retrieve a single task by its identifier.

        Parameters
        ----------
        team_id : str
            Team containing the task.
        task_id : str
            Task identifier.

        Returns
        -------
        TeamTask | None
            The task if found, or None.
        """
        tasks = self._tasks.get(team_id, {})
        return tasks.get(task_id)

    def get_team_tasks(self, team_id: str) -> tuple[TeamTask, ...]:
        """Retrieve all tasks for a team.

        Parameters
        ----------
        team_id : str
            Team identifier.

        Returns
        -------
        tuple[TeamTask, ...]
            All tasks associated with the team.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        return tuple(self._tasks.get(team_id, {}).values())

    # ── Dependency Analysis ───────────────────────────────────────────────

    def get_blocked_tasks(self, team_id: str) -> list[TeamTask]:
        """Return all tasks currently in the BLOCKED state for a team.

        Parameters
        ----------
        team_id : str
            Team identifier.

        Returns
        -------
        list[TeamTask]
            Blocked tasks sorted by creation time (oldest first).

        Raises
        ------
        TeamError
            If the team does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        tasks = self._tasks.get(team_id, {}).values()
        blocked = [t for t in tasks if t.status is TaskStatus.BLOCKED]
        blocked.sort(key=lambda t: t.created_at)
        return blocked

    def get_ready_tasks(self, team_id: str) -> list[TeamTask]:
        """Return tasks whose dependencies are all completed and are ready to work.

        A task is considered ready if it is in PENDING or BLOCKED status and
        every task listed in its ``dependencies`` field has COMPLETED status.
        Results are sorted by descending priority, then ascending creation time.

        Parameters
        ----------
        team_id : str
            Team identifier.

        Returns
        -------
        list[TeamTask]
            Tasks ready for assignment or execution.

        Raises
        ------
        TeamError
            If the team does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        team_tasks = self._tasks.get(team_id, {})
        ready: list[TeamTask] = []

        for task in team_tasks.values():
            if task.status not in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                continue
            all_done = True
            for dep_id in task.dependencies:
                dep = team_tasks.get(dep_id)
                if dep is None or dep.status is not TaskStatus.COMPLETED:
                    all_done = False
                    break
            if all_done:
                ready.append(task)

        ready.sort(key=lambda t: (-t.priority, t.created_at))
        return ready

    # ── Quality Gates ─────────────────────────────────────────────────────

    def register_quality_gate(self, team_id: str, gate: QualityGate) -> None:
        """Register a quality gate for a team.

        Parameters
        ----------
        team_id : str
            Team to register the gate for.
        gate : QualityGate
            The quality gate definition.

        Raises
        ------
        TeamError
            If the team does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        self._gates[team_id].append(gate)
        logger.info(
            "Registered quality gate '%s' for team '%s'",
            gate.name,
            team_id,
        )

    def validate_task(self, team_id: str, task_id: str) -> bool:
        """Run quality gate validation on a task.

        Parameters
        ----------
        team_id : str
            Team containing the task.
        task_id : str
            Task to validate.

        Returns
        -------
        bool
            True if the task passes all applicable quality gates, or if no
            gate is configured for the task. False if any gate rejects it.

        Raises
        ------
        TeamError
            If the team or task does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        task = self._get_task(team_id, task_id)
        return self._validate_task_internal(team_id, task)

    # ── Lifecycle Hooks ───────────────────────────────────────────────────

    def register_lifecycle_hook(self, team_id: str, hook: LifecycleHook) -> None:
        """Register a lifecycle hook for a team.

        Parameters
        ----------
        team_id : str
            Team to register the hook for.
        hook : LifecycleHook
            The hook definition with event, action, and description.

        Raises
        ------
        TeamError
            If the team does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        if hook.event not in ("pre_task", "post_task", "on_blocked"):
            raise TeamError(
                f"Invalid lifecycle event '{hook.event}'. "
                "Must be one of: pre_task, post_task, on_blocked",
            )
        self._hooks[team_id].append(hook)
        logger.info(
            "Registered lifecycle hook '%s' (event=%s) for team '%s'",
            hook.description,
            hook.event,
            team_id,
        )

    # ── Metrics ───────────────────────────────────────────────────────────

    def get_team_metrics(self, team_id: str) -> TeamMetrics:
        """Compute aggregate performance metrics for a team.

        Parameters
        ----------
        team_id : str
            Team identifier.

        Returns
        -------
        TeamMetrics
            Aggregated metrics computed from the team's current task set.

        Raises
        ------
        TeamError
            If the team does not exist.
        """
        if team_id not in self._teams:
            raise TeamError(f"Team '{team_id}' not found")
        tasks = list(self._tasks.get(team_id, {}).values())

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status is TaskStatus.COMPLETED)
        blocked = sum(1 for t in tasks if t.status is TaskStatus.BLOCKED)
        failed = sum(1 for t in tasks if t.status is TaskStatus.FAILED)
        completed_tasks = [t for t in tasks if t.status is TaskStatus.COMPLETED]
        avg_ms = _compute_completion_time(completed_tasks)

        return TeamMetrics(
            total_tasks=total,
            completed=completed,
            blocked=blocked,
            failed=failed,
            avg_completion_time_ms=avg_ms,
        )

    def get_agent_workload(self, agent_id: str) -> dict[str, list[TeamTask]]:
        """Retrieve the workload for a given agent across all teams.

        Parameters
        ----------
        agent_id : str
            Agent identifier.

        Returns
        -------
        dict[str, list[TeamTask]]
            Mapping of status names (e.g. ``"IN_PROGRESS"``, ``"PENDING"``) to the
            list of tasks the agent holds in that state across all teams.
        """
        result: dict[str, list[TeamTask]] = defaultdict(list)
        for team_tasks in self._tasks.values():
            for task in team_tasks.values():
                if task.assigned_to == agent_id:
                    result[task.status.name].append(task)
        return dict(result)

    # ── Messaging Integration ─────────────────────────────────────────────

    def set_messaging(self, messaging: TeamMessaging) -> None:
        """Attach a messaging system for inter-agent notifications.

        Parameters
        ----------
        messaging : TeamMessaging
            The messaging instance to use.
        """
        self._messaging = messaging

    # ── Internal Helpers ──────────────────────────────────────────────────

    def _get_task(self, team_id: str, task_id: str) -> TeamTask:
        """Look up a task by ID within a team, raising if not found."""
        tasks = self._tasks.get(team_id, {})
        task = tasks.get(task_id)
        if task is None:
            raise TeamError(f"Task '{task_id}' not found in team '{team_id}'")
        return task

    def _sync_team_tasks(self, team_id: str) -> None:
        """Refresh the Team's task snapshot from the canonical task store."""
        team = self._teams.get(team_id)
        if team is None:
            return
        all_tasks = tuple(self._tasks.get(team_id, {}).values())
        self._teams[team_id] = replace(team, tasks=all_tasks)

    def _validate_task_internal(self, team_id: str, task: TeamTask) -> bool:
        """Run quality gate checks for a task without external lookups."""
        if not task.quality_gate:
            return True
        for gate in self._gates.get(team_id, []):
            if gate.name == task.quality_gate:
                return gate.check_fn(task)
        return True

    def _unblock_dependents(self, team_id: str, completed_task_id: str) -> None:
        """Re-evaluate BLOCKED tasks that depend on the given completed task."""
        team_tasks = self._tasks.get(team_id, {})
        for task_id, task in team_tasks.items():
            if task.status is not TaskStatus.BLOCKED:
                continue
            if completed_task_id not in task.dependencies:
                continue
            # Check if all dependencies are now completed
            all_done = True
            for dep_id in task.dependencies:
                dep = team_tasks.get(dep_id)
                if dep is None or dep.status is not TaskStatus.COMPLETED:
                    all_done = False
                    break
            if all_done:
                updated = replace(task, status=TaskStatus.PENDING)
                self._tasks[team_id][task_id] = updated
                self._sync_team_tasks(team_id)
                logger.info(
                    "Task '%s' unblocked by completion of '%s'",
                    task_id,
                    completed_task_id,
                )

    def _fire_hooks(self, team_id: str, event: str, task: TeamTask) -> None:
        """Invoke all lifecycle hooks matching the given event."""
        for hook in self._hooks.get(team_id, []):
            if hook.event == event:
                try:
                    hook.action(task)
                except Exception:
                    logger.exception(
                        "Lifecycle hook '%s' failed for team '%s' task '%s'",
                        hook.description,
                        team_id,
                        task.task_id,
                    )

    def _notify_team(self, team_id: str, message: str) -> None:
        """Broadcast a notification to all team members."""
        if self._messaging is None:
            return
        team = self._teams.get(team_id)
        if team is None:
            return
        recipients = [team_id]  # Use team as a pseudo-recipient group
        self._messaging.broadcast(
            sender="system",
            recipients=recipients,
            subject=f"Team notification: {team.name}",
            body=message,
        )


# ── Public API ───────────────────────────────────────────────────────────────

__all__ = [
    "TeamError",
    "TeamRole",
    "TaskStatus",
    "TaskDependency",
    "TeamTask",
    "Team",
    "QualityGate",
    "LifecycleHook",
    "TeamMetrics",
    "AgentTeams",
]
