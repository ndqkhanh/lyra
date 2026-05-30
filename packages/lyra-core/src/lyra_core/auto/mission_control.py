"""Mission Control - Autonomous mission orchestrator.

Coordinates goal decomposition, budget enforcement, verification-driven
progress tracking, and error recovery for fully autonomous missions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from lyra_core.auto.budget_enforcer import BudgetEnforcer, BudgetLimits, BudgetState
from lyra_core.auto.goal_decomposer import Goal, GoalDecomposer
from lyra_core.auto.verifier_driven_progress import (
    ProgressReport,
    VerificationGate,
    VerificationResult,
    VerificationStatus,
    VerifierDrivenProgress,
)


class MissionStatus(StrEnum):
    """Lifecycle status of a mission."""

    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionPriority(StrEnum):
    """Mission priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class MissionConfig:
    """Configuration for an autonomous mission."""

    mission_id: str
    name: str
    description: str = ""
    priority: MissionPriority = MissionPriority.MEDIUM
    goals: tuple[Goal, ...] = ()
    gates: tuple[VerificationGate, ...] = (
        VerificationGate.TEST_COVERAGE,
        VerificationGate.LINT_CHECK,
        VerificationGate.TYPE_CHECK,
    )
    budget_limits: BudgetLimits | None = None
    max_retries_per_task: int = 3
    require_verification: bool = True
    auto_resume: bool = False
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskState:
    """State of an individual task within a mission."""

    task_id: str
    goal_id: str
    description: str
    status: str  # pending, running, completed, failed, blocked
    attempt: int = 0
    assigned_agent: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    verification: VerificationResult | None = None


@dataclass(frozen=True)
class MissionState:
    """Current state of a mission."""

    mission_id: str
    status: MissionStatus
    tasks: tuple[TaskState, ...]
    budget: BudgetState
    progress: ProgressReport | None
    started_at: str | None
    updated_at: str
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class MissionResult:
    """Final result of a completed mission."""

    mission_id: str
    status: MissionStatus
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    blocked_tasks: int
    completion_pct: float
    budget_consumed: BudgetState
    verification: VerificationResult | None
    duration_seconds: float
    errors: tuple[str, ...]
    report: ProgressReport | None


class MissionControl:
    """Orchestrates autonomous missions end-to-end.

    Integrates goal decomposition, budget enforcement, and
    verification-driven progress for fully autonomous execution.

    Features:
    - Mission lifecycle management (draft → pending → running → completed/failed)
    - Automatic goal decomposition into executable tasks
    - Budget-aware execution with hard limits
    - Multi-gate verification pipeline
    - Retry with configurable max attempts
    - Pause/resume/cancel support
    - Comprehensive mission reporting
    """

    def __init__(
        self,
        budget_limits: BudgetLimits | None = None,
        strict_verification: bool = False,
    ):
        self._decomposer = GoalDecomposer()
        self._budget = BudgetEnforcer(limits=budget_limits)
        self._verifier = VerifierDrivenProgress(strict_mode=strict_verification)
        self._missions: dict[str, MissionConfig] = {}
        self._states: dict[str, MissionState] = {}
        self._results: dict[str, MissionResult] = {}
        self._tasks: dict[str, list[TaskState]] = {}  # {mission_id: [tasks]}

    # ── Mission Lifecycle ──────────────────────────────────────────

    def create_mission(self, config: MissionConfig) -> MissionState:
        """Create a new mission from configuration.

        Args:
            config: Mission configuration

        Returns:
            Initial MissionState
        """
        self._missions[config.mission_id] = config

        tasks = self._decompose_goals(config.mission_id, config.goals)

        state = MissionState(
            mission_id=config.mission_id,
            status=MissionStatus.DRAFT,
            tasks=tuple(tasks),
            budget=self._budget.check(),
            progress=None,
            started_at=None,
            updated_at=datetime.now().isoformat(),
        )
        self._states[config.mission_id] = state
        return state

    def start_mission(self, mission_id: str) -> MissionState:
        """Start a created mission.

        Args:
            mission_id: Mission identifier

        Returns:
            Updated MissionState
        """
        state = self._states[mission_id]

        state = MissionState(
            mission_id=mission_id,
            status=MissionStatus.RUNNING,
            tasks=state.tasks,
            budget=self._budget.check(),
            progress=state.progress,
            started_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        self._states[mission_id] = state
        return state

    def pause_mission(self, mission_id: str) -> MissionState:
        """Pause a running mission.

        Args:
            mission_id: Mission identifier

        Returns:
            Updated MissionState
        """
        state = self._states[mission_id]
        state = MissionState(
            mission_id=mission_id,
            status=MissionStatus.PAUSED,
            tasks=state.tasks,
            budget=self._budget.check(),
            progress=state.progress,
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            elapsed_seconds=self._elapsed(state),
        )
        self._states[mission_id] = state
        return state

    def resume_mission(self, mission_id: str) -> MissionState:
        """Resume a paused mission.

        Args:
            mission_id: Mission identifier

        Returns:
            Updated MissionState
        """
        return self.start_mission(mission_id)

    def cancel_mission(self, mission_id: str) -> MissionState:
        """Cancel a mission.

        Args:
            mission_id: Mission identifier

        Returns:
            Updated MissionState
        """
        state = self._states[mission_id]
        state = MissionState(
            mission_id=mission_id,
            status=MissionStatus.CANCELLED,
            tasks=state.tasks,
            budget=self._budget.check(),
            progress=state.progress,
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            elapsed_seconds=self._elapsed(state),
        )
        self._states[mission_id] = state
        return state

    # ── Task Execution ─────────────────────────────────────────────

    def execute_task(
        self,
        mission_id: str,
        task_id: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> TaskState:
        """Record execution of a single task.

        Args:
            mission_id: Mission identifier
            task_id: Task identifier
            result: Optional result data from task execution
            error: Optional error message if task failed

        Returns:
            Updated TaskState
        """
        tasks = list(self._states[mission_id].tasks)
        config = self._missions[mission_id]

        for i, task in enumerate(tasks):
            if task.task_id != task_id:
                continue

            attempt = task.attempt + 1
            now = datetime.now().isoformat()

            if error:
                if attempt >= config.max_retries_per_task:
                    new_status = "failed"
                else:
                    new_status = "pending"
            else:
                new_status = "completed"

            updated = TaskState(
                task_id=task_id,
                goal_id=task.goal_id,
                description=task.description,
                status=new_status,
                attempt=attempt,
                assigned_agent=task.assigned_agent,
                started_at=task.started_at or now,
                completed_at=now if new_status in ("completed", "failed") else None,
                error_message=error,
            )

            if new_status == "completed" and config.require_verification:
                vresult = self._verifier.verify_task(task_id)
                updated = TaskState(
                    task_id=updated.task_id,
                    goal_id=updated.goal_id,
                    description=updated.description,
                    status="completed" if vresult.status == VerificationStatus.PASSED else "failed",
                    attempt=updated.attempt,
                    assigned_agent=updated.assigned_agent,
                    started_at=updated.started_at,
                    completed_at=updated.completed_at,
                    error_message=updated.error_message,
                    verification=vresult,
                )

            tasks[i] = updated

            # Track budget
            self._budget.complete_operation()
            self._budget.consume_tokens(1000)  # Per-task estimate
            break

        state = MissionState(
            mission_id=mission_id,
            status=self._states[mission_id].status,
            tasks=tuple(tasks),
            budget=self._budget.check(),
            progress=self._build_progress(mission_id, tasks),
            started_at=self._states[mission_id].started_at,
            updated_at=datetime.now().isoformat(),
            elapsed_seconds=self._elapsed(self._states[mission_id]),
        )
        self._states[mission_id] = state

        # Check if mission is complete
        self._check_completion(mission_id)

        return tasks[next(i for i, t in enumerate(tasks) if t.task_id == task_id)]

    def get_next_task(self, mission_id: str) -> TaskState | None:
        """Get the next pending task for execution.

        Args:
            mission_id: Mission identifier

        Returns:
            Next TaskState or None if all tasks are done
        """
        state = self._states.get(mission_id)
        if not state:
            return None

        if state.status not in (MissionStatus.RUNNING, MissionStatus.PENDING):
            return None

        for task in state.tasks:
            if task.status == "pending":
                return task

        return None

    def mark_task_blocked(self, mission_id: str, task_id: str, reason: str) -> TaskState:
        """Mark a task as blocked.

        Args:
            mission_id: Mission identifier
            task_id: Task identifier
            reason: Why the task is blocked

        Returns:
            Updated TaskState
        """
        tasks = list(self._states[mission_id].tasks)
        for i, task in enumerate(tasks):
            if task.task_id == task_id:
                tasks[i] = TaskState(
                    task_id=task_id,
                    goal_id=task.goal_id,
                    description=task.description,
                    status="blocked",
                    attempt=task.attempt,
                    assigned_agent=task.assigned_agent,
                    started_at=task.started_at,
                    completed_at=None,
                    error_message=reason,
                )
                break

        state = MissionState(
            mission_id=mission_id,
            status=self._states[mission_id].status,
            tasks=tuple(tasks),
            budget=self._budget.check(),
            progress=self._build_progress(mission_id, tasks),
            started_at=self._states[mission_id].started_at,
            updated_at=datetime.now().isoformat(),
            elapsed_seconds=self._elapsed(self._states[mission_id]),
        )
        self._states[mission_id] = state
        return tasks[next(i for i, t in enumerate(tasks) if t.task_id == task_id)]

    # ── Budget Management ──────────────────────────────────────────

    def check_budget(self, mission_id: str) -> BudgetState:
        """Check current budget state for a mission.

        Args:
            mission_id: Mission identifier

        Returns:
            Current BudgetState
        """
        return self._budget.check()

    def can_proceed(
        self, mission_id: str, estimated_tokens: int = 0, estimated_cost_cents: int = 0
    ) -> tuple[bool, str]:
        """Check if mission can proceed within budget.

        Args:
            mission_id: Mission identifier
            estimated_tokens: Estimated tokens for next operation
            estimated_cost_cents: Estimated cost in cents

        Returns:
            Tuple of (can_proceed, reason)
        """
        return self._budget.can_proceed(estimated_tokens, estimated_cost_cents)

    # ── Reporting ──────────────────────────────────────────────────

    def get_state(self, mission_id: str) -> MissionState | None:
        """Get current mission state.

        Args:
            mission_id: Mission identifier

        Returns:
            MissionState or None if not found
        """
        return self._states.get(mission_id)

    def get_result(self, mission_id: str) -> MissionResult | None:
        """Get final mission result.

        Args:
            mission_id: Mission identifier

        Returns:
            MissionResult or None if mission not complete
        """
        return self._results.get(mission_id)

    def get_progress(self, mission_id: str) -> ProgressReport | None:
        """Get current progress report for a mission.

        Args:
            mission_id: Mission identifier

        Returns:
            ProgressReport or None
        """
        state = self._states.get(mission_id)
        if not state:
            return None
        return self._build_progress(mission_id, list(state.tasks))

    def get_all_missions(
        self, status: MissionStatus | None = None
    ) -> list[MissionState]:
        """Get all missions, optionally filtered by status.

        Args:
            status: Filter by mission status

        Returns:
            List of MissionState
        """
        states = list(self._states.values())
        if status:
            states = [s for s in states if s.status == status]
        return sorted(states, key=lambda s: s.updated_at, reverse=True)

    # ── Internal Helpers ───────────────────────────────────────────

    def _decompose_goals(
        self, mission_id: str, goals: tuple[Goal, ...]
    ) -> list[TaskState]:
        """Decompose goals into executable tasks."""
        tasks: list[TaskState] = []
        for goal in goals:
            decomposed = self._decomposer.decompose(
                description=goal.description,
                goal_type=goal.goal_type,
                tags=goal.tags,
            )
            for i, milestone in enumerate(decomposed.milestones):
                task_id = f"{mission_id}:{goal.goal_id}:task{i + 1}"
                tasks.append(
                    TaskState(
                        task_id=task_id,
                        goal_id=goal.goal_id,
                        description=milestone.description,
                        status="pending",
                    )
                )
        return tasks

    def _build_progress(
        self, mission_id: str, tasks: list[TaskState]
    ) -> ProgressReport:
        """Build a progress report from task states."""
        task_dicts = [
            {"id": t.task_id, "status": t.status, "goal_id": t.goal_id}
            for t in tasks
        ]
        return self._verifier.generate_report(mission_id, task_dicts)

    def _check_completion(self, mission_id: str) -> None:
        """Check if mission is complete and finalize if so."""
        state = self._states[mission_id]
        tasks = list(state.tasks)

        completed = sum(1 for t in tasks if t.status == "completed")
        failed = sum(1 for t in tasks if t.status == "failed")
        blocked = sum(1 for t in tasks if t.status == "blocked")
        total = len(tasks)

        progress = self._build_progress(mission_id, tasks)

        if failed > 0 and completed + failed + blocked >= total:
            self._finalize_mission(mission_id, MissionStatus.FAILED, tasks, progress)
        elif completed >= total:
            if self._verifier.is_mission_complete(progress):
                self._finalize_mission(mission_id, MissionStatus.COMPLETED, tasks, progress)
        elif blocked == total - completed and completed < total:
            self._finalize_mission(mission_id, MissionStatus.FAILED, tasks, progress)

    def _finalize_mission(
        self,
        mission_id: str,
        status: MissionStatus,
        tasks: list[TaskState],
        progress: ProgressReport,
    ) -> None:
        """Finalize a mission and store the result."""
        state = self._states[mission_id]
        budget = self._budget.check()

        errors = tuple(
            t.error_message for t in tasks if t.error_message is not None
        )

        result = MissionResult(
            mission_id=mission_id,
            status=status,
            total_tasks=len(tasks),
            completed_tasks=sum(1 for t in tasks if t.status == "completed"),
            failed_tasks=sum(1 for t in tasks if t.status == "failed"),
            blocked_tasks=sum(1 for t in tasks if t.status == "blocked"),
            completion_pct=progress.completion_pct,
            budget_consumed=budget,
            verification=VerificationResult(
                gate=VerificationGate.MANUAL_REVIEW,
                status=progress.overall_status,
                message="Mission finalized",
            ),
            duration_seconds=self._elapsed(state),
            errors=errors,
            report=progress,
        )
        self._results[mission_id] = result

        final_state = MissionState(
            mission_id=mission_id,
            status=status,
            tasks=tuple(tasks),
            budget=budget,
            progress=progress,
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            elapsed_seconds=self._elapsed(state),
        )
        self._states[mission_id] = final_state

    def _elapsed(self, state: MissionState) -> float:
        """Calculate elapsed seconds since mission started."""
        if not state.started_at:
            return 0.0
        start = datetime.fromisoformat(state.started_at)
        return (datetime.now() - start).total_seconds()

    def reset(self) -> None:
        """Reset all mission state."""
        self._missions.clear()
        self._states.clear()
        self._results.clear()
        self._tasks.clear()
        self._budget.reset()
        self._verifier.clear()
