"""Phase 4.2a — Goal Decomposition Engine.

Explicitly decomposes high-level goals into measurable milestones
with progress tracking. Supports 10+ goal types:

  - Feature implementation, refactoring, debugging, performance
  - Infrastructure, documentation, research, learning, deployment
  - Automation, data migration, integration, optimization
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class GoalType(Enum):
    FEATURE = "feature"
    REFACTOR = "refactor"
    DEBUG = "debug"
    PERF = "performance"
    INFRA = "infrastructure"
    DOCS = "documentation"
    RESEARCH = "research"
    DEPLOY = "deployment"
    AUTOMATION = "automation"
    MIGRATION = "migration"
    INTEGRATION = "integration"
    OPTIMIZATION = "optimization"


class MilestoneStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Milestone:
    """A measurable sub-goal within a larger goal."""

    milestone_id: str
    name: str
    description: str
    status: MilestoneStatus
    progress_pct: float           # 0.0–100.0
    estimated_effort_hours: float
    actual_effort_hours: float
    dependencies: tuple[str, ...]  # milestone_ids
    acceptance_criteria: str
    started_at: float | None
    completed_at: float | None


@dataclass(frozen=True)
class Goal:
    """A decomposable high-level goal."""

    goal_id: str
    name: str
    description: str
    goal_type: GoalType
    milestones: tuple[Milestone, ...]
    overall_progress: float
    created_at: float
    target_completion: float | None  # Unix timestamp
    tags: tuple[str, ...]


@dataclass(frozen=True)
class GoalProgressReport:
    """Summary of progress across all goals."""

    report_id: str
    goals: tuple[Goal, ...]
    overall_progress: float           # Weighted average
    completed_milestones: int
    total_milestones: int
    blocked_count: int
    summary: str
    timestamp: float


_GOAL_PHASES: dict[GoalType, tuple[str, ...]] = {
    GoalType.FEATURE: (
        "Requirements gathering", "Design", "Implementation",
        "Testing", "Code review", "Documentation", "Release",
    ),
    GoalType.REFACTOR: (
        "Code analysis", "Extract interfaces", "Migrate callers",
        "Remove old code", "Verify tests", "Performance check",
    ),
    GoalType.DEBUG: (
        "Reproduce bug", "Root cause analysis", "Implement fix",
        "Regression test", "Code review", "Deploy fix",
    ),
    GoalType.PERF: (
        "Profile baseline", "Identify bottleneck", "Implement optimization",
        "Benchmark", "Validate correctness", "Document",
    ),
    GoalType.INFRA: (
        "Assess requirements", "Provision resources", "Configuration",
        "Testing/Staging", "Production rollout", "Monitoring setup",
    ),
    GoalType.DOCS: (
        "Audit existing docs", "Outline structure", "Write content",
        "Add examples", "Review", "Publish",
    ),
    GoalType.RESEARCH: (
        "Define questions", "Literature review", "Experiment design",
        "Run experiments", "Analyze results", "Write report",
    ),
    GoalType.DEPLOY: (
        "Pre-deploy checklist", "Stage deployment", "Smoke tests",
        "Production deploy", "Monitor", "Post-deploy review",
    ),
    GoalType.AUTOMATION: (
        "Identify manual steps", "Design automation", "Implement scripts",
        "Integration tests", "Rollout", "Monitor & iterate",
    ),
    GoalType.MIGRATION: (
        "Inventory & assess", "Backup data", "Migration script",
        "Test migration", "Execute", "Verify & cleanup",
    ),
    GoalType.INTEGRATION: (
        "API review", "Auth setup", "Implement adapter",
        "Integration tests", "End-to-end validation", "Document",
    ),
    GoalType.OPTIMIZATION: (
        "Measure baseline", "Identify targets", "Implement changes",
        "A/B test", "Validate no regression", "Ship & monitor",
    ),
}


def _detect_goal_type(description: str) -> GoalType:
    """Heuristically classify a goal from its description."""
    desc_lower = description.lower()
    for gt in GoalType:
        if gt.value in desc_lower:
            return gt
    if any(kw in desc_lower for kw in ("fix", "bug", "crash", "error")):
        return GoalType.DEBUG
    if any(kw in desc_lower for kw in ("optimize", "speed", "fast", "slow")):
        return GoalType.PERF
    if any(kw in desc_lower for kw in ("deploy", "release", "ship", "rollout")):
        return GoalType.DEPLOY
    if any(kw in desc_lower for kw in ("automate", "schedule", "cron", "trigger")):
        return GoalType.AUTOMATION
    if any(kw in desc_lower for kw in ("feature", "add", "new", "implement")):
        return GoalType.FEATURE
    return GoalType.FEATURE


@dataclass
class GoalDecomposer:
    """Decomposes high-level goals into trackable milestones.

    Usage::

        decomposer = GoalDecomposer()
        goal = decomposer.decompose(
            "Implement user authentication with OAuth2",
            tags=("auth", "security"),
        )
        for m in goal.milestones:
            print(f"[{m.progress_pct:.0f}%] {m.name}")
    """

    _goals: dict[str, Goal] = field(default_factory=dict)

    def decompose(
        self,
        description: str,
        *,
        goal_type: GoalType | None = None,
        estimated_hours: float = 8.0,
        tags: tuple[str, ...] = (),
        target_completion: float | None = None,
    ) -> Goal:
        """Decompose a goal description into milestones.

        Args:
            description: Natural-language goal description.
            goal_type: Override auto-detected goal type.
            estimated_hours: Total estimated effort.
            tags: Optional tags for categorization.
            target_completion: Unix timestamp for deadline.

        Returns:
            Goal with dependency-ordered milestones.
        """
        gt = goal_type or _detect_goal_type(description)
        phases = _GOAL_PHASES.get(gt, _GOAL_PHASES[GoalType.FEATURE])
        hours_per_phase = estimated_hours / len(phases)

        milestones: list[Milestone] = []
        prev_id: str | None = None

        for phase in phases:
            mid = f"ms-{uuid.uuid4().hex[:8]}"
            deps = (prev_id,) if prev_id else ()

            m = Milestone(
                milestone_id=mid,
                name=f"[{gt.value}] {phase}",
                description=f"{phase}: {description[:120]}",
                status=MilestoneStatus.PENDING,
                progress_pct=0.0,
                estimated_effort_hours=round(hours_per_phase, 1),
                actual_effort_hours=0.0,
                dependencies=deps,
                acceptance_criteria=f"Phase '{phase}' complete with verification.",
                started_at=None,
                completed_at=None,
            )
            milestones.append(m)
            prev_id = mid

        goal = Goal(
            goal_id=f"go-{uuid.uuid4().hex[:12]}",
            name=description[:80],
            description=description,
            goal_type=gt,
            milestones=tuple(milestones),
            overall_progress=0.0,
            created_at=time.time(),
            target_completion=target_completion,
            tags=tags,
        )
        self._goals[goal.goal_id] = goal
        return goal

    def update_milestone(
        self,
        goal_id: str,
        milestone_id: str,
        *,
        status: MilestoneStatus | None = None,
        progress_pct: float | None = None,
        actual_hours: float | None = None,
    ) -> Goal | None:
        """Update a milestone's progress and recalculate goal progress."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return None

        updated_milestones: list[Milestone] = []
        now = time.time()

        for m in goal.milestones:
            if m.milestone_id == milestone_id:
                new_status = status or m.status
                new_progress = progress_pct if progress_pct is not None else m.progress_pct
                new_hours = actual_hours if actual_hours is not None else m.actual_effort_hours

                started_at = m.started_at
                if new_status == MilestoneStatus.IN_PROGRESS and m.started_at is None:
                    started_at = now

                completed_at = m.completed_at
                if new_status == MilestoneStatus.COMPLETED and m.completed_at is None:
                    completed_at = now

                updated = Milestone(
                    milestone_id=m.milestone_id,
                    name=m.name,
                    description=m.description,
                    status=new_status,
                    progress_pct=new_progress,
                    estimated_effort_hours=m.estimated_effort_hours,
                    actual_effort_hours=new_hours,
                    dependencies=m.dependencies,
                    acceptance_criteria=m.acceptance_criteria,
                    started_at=started_at,
                    completed_at=completed_at,
                )
                updated_milestones.append(updated)
            else:
                updated_milestones.append(m)

        progress = sum(m.progress_pct for m in updated_milestones) / max(1, len(updated_milestones))
        updated_goal = Goal(
            goal_id=goal.goal_id,
            name=goal.name,
            description=goal.description,
            goal_type=goal.goal_type,
            milestones=tuple(updated_milestones),
            overall_progress=round(progress, 1),
            created_at=goal.created_at,
            target_completion=goal.target_completion,
            tags=goal.tags,
        )
        self._goals[goal_id] = updated_goal
        return updated_goal

    def get_progress_report(self) -> GoalProgressReport:
        """Generate a summary report across all goals."""
        all_milestones: list[Milestone] = []
        for goal in self._goals.values():
            all_milestones.extend(goal.milestones)

        completed = sum(1 for m in all_milestones if m.status == MilestoneStatus.COMPLETED)
        blocked = sum(1 for m in all_milestones if m.status == MilestoneStatus.BLOCKED)
        total = len(all_milestones)

        if total > 0:
            overall = sum(
                g.overall_progress for g in self._goals.values()
            ) / len(self._goals)
        else:
            overall = 0.0

        return GoalProgressReport(
            report_id=f"gpr-{uuid.uuid4().hex[:12]}",
            goals=tuple(self._goals.values()),
            overall_progress=round(overall, 1),
            completed_milestones=completed,
            total_milestones=total,
            blocked_count=blocked,
            summary=(
                f"{completed}/{total} milestones completed, "
                f"{blocked} blocked ({overall:.1f}% overall)"
            ),
            timestamp=time.time(),
        )

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    @property
    def goal_count(self) -> int:
        return len(self._goals)


__all__ = [
    "Goal",
    "GoalDecomposer",
    "GoalProgressReport",
    "GoalType",
    "Milestone",
    "MilestoneStatus",
]
