"""Plan 11: Goal System — autonomous goal decomposition, tracking, and completion.

Provides the goal data model with hierarchical sub-goal trees, templates
for common goal types, progress metrics, and budget enforcement.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class GoalStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class GoalPriority(Enum):
    P0 = 0  # Critical — drop everything
    P1 = 1  # High — next in queue
    P2 = 2  # Normal — standard priority
    P3 = 3  # Low — background / best-effort


class GoalAgentType(Enum):
    CODE = "code"
    RESEARCH = "research"
    DESIGN = "design"
    SRE = "sre"
    REVIEW = "review"
    AUTO = "auto"


def _new_id() -> str:
    return f"goal_{uuid4().hex[:12]}"


@dataclass(frozen=True)
class GoalCriteria:
    """Checkable acceptance criteria for a goal.

    Attributes:
        description: What must be true for this criterion to pass.
        verified: Whether this criterion has been verified as met.
    """

    description: str
    verified: bool = False


@dataclass(frozen=True)
class GoalMetrics:
    """Runtime metrics tracked during goal execution.

    Attributes:
        turns_completed: Number of execution turns.
        tokens_used: Total tokens consumed.
        cost_usd: Total cost in USD.
        files_changed: Number of files modified.
        tests_passing: Current test pass count.
        completion_pct: Estimated completion 0-100.
    """

    turns_completed: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    files_changed: int = 0
    tests_passing: int = 0
    completion_pct: float = 0.0


@dataclass(frozen=True)
class GoalEvent:
    """A recorded event in a goal's lifecycle.

    Attributes:
        timestamp: When the event occurred.
        event_type: What happened (e.g. 'created', 'paused', 'progress').
        details: Human-readable description.
        metrics_snapshot: Metrics at the time of the event.
    """

    timestamp: float
    event_type: str
    details: str
    metrics_snapshot: GoalMetrics = field(default_factory=GoalMetrics)


@dataclass(frozen=True)
class Goal:
    """Immutable goal definition with progress tracking.

    Attributes:
        id: Unique goal identifier.
        title: Short goal title.
        description: Detailed description of what to achieve.
        criteria: Tuple of acceptance criteria.
        status: Current goal status.
        priority: Priority level.
        agent_type: Type of agent best suited for this goal.
        parent_goal: Optional parent goal ID for goal trees.
        sub_goals: Child goal IDs.
        auto_approve: Whether the agent can self-approve actions.
        max_budget_usd: Maximum budget for this goal.
        max_turns: Maximum execution turns.
        check_interval_minutes: How often to check progress.
        created_at: Creation timestamp.
        deadline: Optional deadline timestamp.
        completed_at: When the goal was completed.
        metrics: Execution metrics.
        history: Ordered lifecycle events.
    """

    id: str = field(default_factory=_new_id)
    title: str = ""
    description: str = ""
    criteria: tuple[GoalCriteria, ...] = ()
    status: GoalStatus = GoalStatus.ACTIVE
    priority: GoalPriority = GoalPriority.P2
    agent_type: GoalAgentType = GoalAgentType.AUTO
    parent_goal: str | None = None
    sub_goals: tuple[str, ...] = ()
    auto_approve: bool = False
    max_budget_usd: float = 5.0
    max_turns: int = 100
    check_interval_minutes: int = 30
    created_at: float = field(default_factory=time.time)
    deadline: float | None = None
    completed_at: float | None = None
    metrics: GoalMetrics = field(default_factory=GoalMetrics)
    history: tuple[GoalEvent, ...] = ()

    @property
    def is_overdue(self) -> bool:
        if self.deadline is None:
            return False
        return time.time() > self.deadline

    @property
    def is_budget_exhausted(self) -> bool:
        return self.metrics.cost_usd >= self.max_budget_usd

    @property
    def is_turns_exhausted(self) -> bool:
        return self.metrics.turns_completed >= self.max_turns

    @property
    def criteria_met(self) -> int:
        return sum(1 for c in self.criteria if c.verified)

    @property
    def criteria_total(self) -> int:
        return len(self.criteria)


# ── Goal Templates ──────────────────────────────────────────────────────

GOAL_TEMPLATES: dict[str, dict] = {
    "migrate": {
        "agent_type": GoalAgentType.CODE,
        "auto_approve": False,
        "check_interval_minutes": 30,
        "criteria": [
            "All tests pass",
            "No breaking API changes",
            "Performance within 10% of baseline",
            "Documentation updated",
        ],
    },
    "research": {
        "agent_type": GoalAgentType.RESEARCH,
        "auto_approve": True,
        "check_interval_minutes": 120,
        "criteria": [
            "At least 10 sources reviewed",
            "Synthesis report with citations",
            "Gap analysis completed",
            "Recommendations documented",
        ],
    },
    "investigate": {
        "agent_type": GoalAgentType.CODE,
        "auto_approve": False,
        "check_interval_minutes": 15,
        "criteria": [
            "Root cause identified",
            "Reproduction steps documented",
            "Fix proposed with risk assessment",
            "Regression test added",
        ],
    },
    "refactor": {
        "agent_type": GoalAgentType.CODE,
        "auto_approve": False,
        "check_interval_minutes": 20,
        "criteria": [
            "All existing tests pass",
            "Code complexity reduced",
            "No new dependencies introduced",
            "Performance not degraded",
        ],
    },
    "implement-feature": {
        "agent_type": GoalAgentType.CODE,
        "auto_approve": False,
        "check_interval_minutes": 30,
        "criteria": [
            "Feature works as specified",
            "Unit tests >= 80% coverage",
            "Integration tests pass",
            "Code review approved",
            "Documentation added",
        ],
    },
    "security-audit": {
        "agent_type": GoalAgentType.REVIEW,
        "auto_approve": False,
        "check_interval_minutes": 60,
        "criteria": [
            "OWASP Top 10 checked",
            "Secret scanning completed",
            "Dependency vulnerabilities checked",
            "Report with severity ratings",
        ],
    },
}


# ── Goal Manager ────────────────────────────────────────────────────────


class GoalManager:
    """Manages the lifecycle of autonomous goals.

    Provides CRUD operations, template-based creation, progress tracking,
    event logging, and hierarchical goal tree management.
    """

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}

    # ── Create ──────────────────────────────────────────────────────────

    def create(
        self,
        title: str,
        description: str = "",
        criteria: tuple[str, ...] = (),
        template: str | None = None,
        priority: GoalPriority = GoalPriority.P2,
        agent_type: GoalAgentType = GoalAgentType.AUTO,
        auto_approve: bool = False,
        max_budget_usd: float = 5.0,
        max_turns: int = 100,
        parent_goal: str | None = None,
        deadline: float | None = None,
    ) -> Goal:
        """Create a new goal, optionally from a template."""
        if template and template in GOAL_TEMPLATES:
            tmpl = GOAL_TEMPLATES[template]
            agent_type = tmpl.get("agent_type", agent_type)
            auto_approve = tmpl.get("auto_approve", auto_approve)
            max_budget_usd = tmpl.get("max_budget_usd", max_budget_usd)
            if not criteria:
                criteria = tuple(tmpl.get("criteria", []))

        goal = Goal(
            title=title,
            description=description,
            criteria=tuple(GoalCriteria(description=c) for c in criteria),
            priority=priority,
            agent_type=agent_type,
            auto_approve=auto_approve,
            max_budget_usd=max_budget_usd,
            max_turns=max_turns,
            parent_goal=parent_goal,
            deadline=deadline,
            history=(GoalEvent(
                timestamp=time.time(),
                event_type="created",
                details=f"Goal created: {title}",
            ),),
        )

        self._goals[goal.id] = goal
        return goal

    def create_sub_goal(
        self, parent_id: str, title: str, description: str = "", **kwargs
    ) -> Goal | None:
        """Create a sub-goal linked to a parent."""
        parent = self._goals.get(parent_id)
        if parent is None:
            return None
        sub = self.create(title=title, description=description, parent_goal=parent_id, **kwargs)
        updated_parent = Goal(
            id=parent.id, title=parent.title, description=parent.description,
            criteria=parent.criteria, status=parent.status, priority=parent.priority,
            agent_type=parent.agent_type, parent_goal=parent.parent_goal,
            sub_goals=parent.sub_goals + (sub.id,),
            auto_approve=parent.auto_approve, max_budget_usd=parent.max_budget_usd,
            max_turns=parent.max_turns, created_at=parent.created_at,
            deadline=parent.deadline, metrics=parent.metrics, history=parent.history,
        )
        self._goals[parent_id] = updated_parent
        return sub

    # ── Read ────────────────────────────────────────────────────────────

    def get(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def list_active(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]

    def list_all(self) -> list[Goal]:
        return list(self._goals.values())

    def list_by_status(self, status: GoalStatus) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == status]

    def list_by_priority(self, priority: GoalPriority) -> list[Goal]:
        return [g for g in self._goals.values() if g.priority == priority]

    def get_goal_tree(self, goal_id: str) -> dict:
        """Return a goal and its sub-goal tree."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return {}
        return {
            "goal": goal,
            "sub_goals": [self.get_goal_tree(sid) for sid in goal.sub_goals if sid in self._goals],
        }

    # ── Update ──────────────────────────────────────────────────────────

    def update_status(self, goal_id: str, status: GoalStatus, reason: str = "") -> Goal | None:
        """Transition a goal to a new status."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return None

        event = GoalEvent(
            timestamp=time.time(),
            event_type=status.value,
            details=reason or f"Status changed to {status.value}",
            metrics_snapshot=goal.metrics,
        )

        completed_at = goal.completed_at
        if status == GoalStatus.COMPLETED:
            completed_at = time.time()

        updated = Goal(
            id=goal.id, title=goal.title, description=goal.description,
            criteria=goal.criteria, status=status, priority=goal.priority,
            agent_type=goal.agent_type, parent_goal=goal.parent_goal,
            sub_goals=goal.sub_goals, auto_approve=goal.auto_approve,
            max_budget_usd=goal.max_budget_usd, max_turns=goal.max_turns,
            created_at=goal.created_at, deadline=goal.deadline,
            completed_at=completed_at, metrics=goal.metrics,
            history=goal.history + (event,),
        )
        self._goals[goal_id] = updated
        return updated

    def update_metrics(self, goal_id: str, **kwargs) -> Goal | None:
        """Update execution metrics for a goal."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return None

        new_metrics = GoalMetrics(
            turns_completed=kwargs.get("turns_completed", goal.metrics.turns_completed),
            tokens_used=kwargs.get("tokens_used", goal.metrics.tokens_used),
            cost_usd=kwargs.get("cost_usd", goal.metrics.cost_usd),
            files_changed=kwargs.get("files_changed", goal.metrics.files_changed),
            tests_passing=kwargs.get("tests_passing", goal.metrics.tests_passing),
            completion_pct=kwargs.get("completion_pct", goal.metrics.completion_pct),
        )

        updated = Goal(
            id=goal.id, title=goal.title, description=goal.description,
            criteria=goal.criteria, status=goal.status, priority=goal.priority,
            agent_type=goal.agent_type, parent_goal=goal.parent_goal,
            sub_goals=goal.sub_goals, auto_approve=goal.auto_approve,
            max_budget_usd=goal.max_budget_usd, max_turns=goal.max_turns,
            created_at=goal.created_at, deadline=goal.deadline,
            completed_at=goal.completed_at, metrics=new_metrics,
            history=goal.history,
        )
        self._goals[goal_id] = updated
        return updated

    def verify_criterion(self, goal_id: str, criterion_index: int) -> Goal | None:
        """Mark a specific criterion as verified."""
        goal = self._goals.get(goal_id)
        if goal is None or criterion_index >= len(goal.criteria):
            return None

        new_criteria = tuple(
            GoalCriteria(description=c.description, verified=True)
            if i == criterion_index else c
            for i, c in enumerate(goal.criteria)
        )

        # Auto-complete if all criteria met
        new_status = goal.status
        if all(c.verified for c in new_criteria):
            new_status = GoalStatus.COMPLETED

        updated = Goal(
            id=goal.id, title=goal.title, description=goal.description,
            criteria=new_criteria, status=new_status, priority=goal.priority,
            agent_type=goal.agent_type, parent_goal=goal.parent_goal,
            sub_goals=goal.sub_goals, auto_approve=goal.auto_approve,
            max_budget_usd=goal.max_budget_usd, max_turns=goal.max_turns,
            created_at=goal.created_at, deadline=goal.deadline,
            completed_at=time.time() if new_status == GoalStatus.COMPLETED else goal.completed_at,
            metrics=goal.metrics, history=goal.history,
        )
        self._goals[goal_id] = updated
        return updated

    # ── Delete ──────────────────────────────────────────────────────────

    def cancel(self, goal_id: str, reason: str = "") -> Goal | None:
        return self.update_status(goal_id, GoalStatus.CANCELLED, reason)

    def remove(self, goal_id: str) -> bool:
        if goal_id in self._goals:
            del self._goals[goal_id]
            return True
        return False

    # ── Query ───────────────────────────────────────────────────────────

    def get_next_goal(self) -> Goal | None:
        """Get the highest-priority active goal."""
        active = self.list_active()
        if not active:
            return None
        active.sort(key=lambda g: (g.priority.value, g.created_at))
        return active[0]

    def get_overdue_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.is_overdue and g.status == GoalStatus.ACTIVE]

    @property
    def goal_count(self) -> int:
        return len(self._goals)

    def stats(self) -> dict:
        """Return summary statistics."""
        goals = list(self._goals.values())
        return {
            "total": len(goals),
            "active": sum(1 for g in goals if g.status == GoalStatus.ACTIVE),
            "completed": sum(1 for g in goals if g.status == GoalStatus.COMPLETED),
            "failed": sum(1 for g in goals if g.status == GoalStatus.FAILED),
            "blocked": sum(1 for g in goals if g.status == GoalStatus.BLOCKED),
            "total_cost_usd": round(sum(g.metrics.cost_usd for g in goals), 4),
            "total_tokens": sum(g.metrics.tokens_used for g in goals),
        }
