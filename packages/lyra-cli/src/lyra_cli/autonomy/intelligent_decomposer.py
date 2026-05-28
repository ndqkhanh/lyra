"""Intelligent Goal Decomposer — enhanced goal decomposition with priority and parallelism.

Extends the basic GoalDecomposer with:
  - Effort estimation (low/medium/high) per subtask
  - Priority scoring based on dependency depth and impact
  - Parallel group detection — identifies subtasks that can run concurrently
  - Execution wave scheduling (wave 0 = no deps, wave 1 = after wave 0, etc.)
  - Progress tracking with completion percentage
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EffortLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class IntelligentSubtask:
    """A subtask with effort estimation and priority scoring."""

    id: str
    description: str
    effort: EffortLevel
    priority: Priority
    depends_on: tuple[str, ...] = ()
    estimated_minutes: int = 15
    parallel_group: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionWave:
    """A group of subtasks that can be executed in parallel."""

    wave_index: int
    subtask_ids: tuple[str, ...]
    total_effort_minutes: int


@dataclass(frozen=True)
class IntelligentPlan:
    """A complete execution plan with waves and progress tracking."""

    goal_id: str
    description: str
    subtasks: tuple[IntelligentSubtask, ...]
    waves: tuple[ExecutionWave, ...]
    total_estimated_minutes: int
    critical_path_minutes: int

    @property
    def progress(self) -> float:
        """Overall completion percentage based on remaining subtasks."""
        if not self.subtasks:
            return 1.0
        completed = sum(1 for s in self.subtasks if s.metadata.get("completed", False))
        return completed / len(self.subtasks)

    @property
    def subtask_count(self) -> int:
        return len(self.subtasks)

    def subtask_by_id(self, subtask_id: str) -> IntelligentSubtask | None:
        for s in self.subtasks:
            if s.id == subtask_id:
                return s
        return None


class CyclicDependencyError(Exception):
    """Raised when the dependency graph contains a cycle."""


@dataclass
class IntelligentDecomposer:
    """Decomposes high-level goals into prioritized execution plans.

    Usage::

        decomposer = IntelligentDecomposer()
        plan = decomposer.decompose("GOAL-1", "Build user authentication system")
        for wave in plan.waves:
            print(f"Wave {wave.wave_index}: {wave.subtask_ids}")
    """

    def decompose(
        self,
        goal_id: str,
        description: str,
        *,
        constraints: dict[str, Any] | None = None,
    ) -> IntelligentPlan:
        """Break a goal into subtasks and organize into execution waves."""
        subtasks = self._generate_subtasks(goal_id, description, constraints or {})
        self._validate_acyclic(subtasks)
        waves = self._schedule_waves(subtasks)
        total = sum(s.estimated_minutes for s in subtasks)
        critical = self._critical_path_minutes(subtasks)

        return IntelligentPlan(
            goal_id=goal_id,
            description=description,
            subtasks=tuple(subtasks),
            waves=tuple(waves),
            total_estimated_minutes=total,
            critical_path_minutes=critical,
        )

    def mark_complete(self, plan: IntelligentPlan, subtask_id: str) -> IntelligentPlan:
        """Return a new plan with the given subtask marked complete."""
        new_subtasks: list[IntelligentSubtask] = []
        for s in plan.subtasks:
            if s.id == subtask_id:
                meta = dict(s.metadata)
                meta["completed"] = True
                new_subtasks.append(IntelligentSubtask(
                    id=s.id, description=s.description, effort=s.effort,
                    priority=s.priority, depends_on=s.depends_on,
                    estimated_minutes=s.estimated_minutes,
                    parallel_group=s.parallel_group, metadata=meta,
                ))
            else:
                new_subtasks.append(s)

        return IntelligentPlan(
            goal_id=plan.goal_id,
            description=plan.description,
            subtasks=tuple(new_subtasks),
            waves=plan.waves,
            total_estimated_minutes=plan.total_estimated_minutes,
            critical_path_minutes=plan.critical_path_minutes,
        )

    # ── subtask generation ───────────────────────────────────────────

    def _generate_subtasks(
        self, goal_id: str, description: str, _constraints: dict[str, Any]
    ) -> list[IntelligentSubtask]:
        """Generate domain-aware subtasks based on the goal description."""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ("auth", "login", "authentication")):
            return self._auth_subtasks(goal_id)
        if any(kw in desc_lower for kw in ("api", "endpoint", "rest", "graphql")):
            return self._api_subtasks(goal_id)
        if any(kw in desc_lower for kw in ("migrat", "database", "schema")):
            return self._migration_subtasks(goal_id)

        return self._default_subtasks(goal_id, description)

    def _auth_subtasks(self, goal_id: str) -> list[IntelligentSubtask]:
        return [
            IntelligentSubtask(f"{goal_id}_research", "Research auth protocols (OAuth2, JWT, Passkey)",
                EffortLevel.LOW, Priority.HIGH, estimated_minutes=30, parallel_group=0),
            IntelligentSubtask(f"{goal_id}_schema", "Design user & session database schema",
                EffortLevel.MEDIUM, Priority.HIGH, depends_on=(f"{goal_id}_research",),
                estimated_minutes=45, parallel_group=1),
            IntelligentSubtask(f"{goal_id}_register", "Implement registration endpoint",
                EffortLevel.MEDIUM, Priority.CRITICAL, depends_on=(f"{goal_id}_schema",),
                estimated_minutes=60, parallel_group=2),
            IntelligentSubtask(f"{goal_id}_login", "Implement login endpoint with rate limiting",
                EffortLevel.MEDIUM, Priority.CRITICAL, depends_on=(f"{goal_id}_schema",),
                estimated_minutes=60, parallel_group=2),
            IntelligentSubtask(f"{goal_id}_tokens", "Implement JWT refresh & revocation",
                EffortLevel.MEDIUM, Priority.HIGH, depends_on=(f"{goal_id}_login",),
                estimated_minutes=45, parallel_group=3),
            IntelligentSubtask(f"{goal_id}_verify", "Integration tests & security review",
                EffortLevel.HIGH, Priority.HIGH,
                depends_on=(f"{goal_id}_register", f"{goal_id}_login"),
                estimated_minutes=90, parallel_group=3),
        ]

    def _api_subtasks(self, goal_id: str) -> list[IntelligentSubtask]:
        return [
            IntelligentSubtask(f"{goal_id}_design", "Design API contract (OpenAPI/GraphQL schema)",
                EffortLevel.MEDIUM, Priority.HIGH, estimated_minutes=45, parallel_group=0),
            IntelligentSubtask(f"{goal_id}_models", "Implement data models & validation",
                EffortLevel.MEDIUM, Priority.CRITICAL, depends_on=(f"{goal_id}_design",),
                estimated_minutes=60, parallel_group=1),
            IntelligentSubtask(f"{goal_id}_handlers", "Implement route handlers",
                EffortLevel.HIGH, Priority.CRITICAL, depends_on=(f"{goal_id}_models",),
                estimated_minutes=120, parallel_group=2),
            IntelligentSubtask(f"{goal_id}_middleware", "Add auth, logging, CORS middleware",
                EffortLevel.MEDIUM, Priority.HIGH, depends_on=(f"{goal_id}_models",),
                estimated_minutes=45, parallel_group=2),
            IntelligentSubtask(f"{goal_id}_docs", "Generate API documentation",
                EffortLevel.LOW, Priority.LOW, depends_on=(f"{goal_id}_design",),
                estimated_minutes=30, parallel_group=1),
            IntelligentSubtask(f"{goal_id}_test", "Write API integration tests",
                EffortLevel.HIGH, Priority.HIGH, depends_on=(f"{goal_id}_handlers",),
                estimated_minutes=90, parallel_group=3),
        ]

    def _migration_subtasks(self, goal_id: str) -> list[IntelligentSubtask]:
        return [
            IntelligentSubtask(f"{goal_id}_audit", "Audit current schema & data",
                EffortLevel.MEDIUM, Priority.CRITICAL, estimated_minutes=60, parallel_group=0),
            IntelligentSubtask(f"{goal_id}_plan", "Design migration plan & rollback strategy",
                EffortLevel.MEDIUM, Priority.HIGH, depends_on=(f"{goal_id}_audit",),
                estimated_minutes=45, parallel_group=1),
            IntelligentSubtask(f"{goal_id}_script", "Write forward migration script",
                EffortLevel.HIGH, Priority.CRITICAL, depends_on=(f"{goal_id}_plan",),
                estimated_minutes=60, parallel_group=2),
            IntelligentSubtask(f"{goal_id}_rollback", "Write rollback script",
                EffortLevel.MEDIUM, Priority.HIGH, depends_on=(f"{goal_id}_plan",),
                estimated_minutes=30, parallel_group=2),
            IntelligentSubtask(f"{goal_id}_test_migrate", "Test migration on staging",
                EffortLevel.HIGH, Priority.CRITICAL,
                depends_on=(f"{goal_id}_script", f"{goal_id}_rollback"),
                estimated_minutes=45, parallel_group=3),
        ]

    def _default_subtasks(self, goal_id: str, description: str) -> list[IntelligentSubtask]:
        return [
            IntelligentSubtask(f"{goal_id}_research", f"Research: {description}",
                EffortLevel.LOW, Priority.HIGH, estimated_minutes=30, parallel_group=0),
            IntelligentSubtask(f"{goal_id}_design", f"Design: {description}",
                EffortLevel.MEDIUM, Priority.HIGH, depends_on=(f"{goal_id}_research",),
                estimated_minutes=45, parallel_group=1),
            IntelligentSubtask(f"{goal_id}_implement", f"Implement: {description}",
                EffortLevel.HIGH, Priority.CRITICAL, depends_on=(f"{goal_id}_design",),
                estimated_minutes=120, parallel_group=2),
            IntelligentSubtask(f"{goal_id}_test", f"Test: {description}",
                EffortLevel.HIGH, Priority.HIGH, depends_on=(f"{goal_id}_implement",),
                estimated_minutes=60, parallel_group=3),
            IntelligentSubtask(f"{goal_id}_review", f"Review: {description}",
                EffortLevel.MEDIUM, Priority.MEDIUM, depends_on=(f"{goal_id}_test",),
                estimated_minutes=30, parallel_group=4),
        ]

    # ── dependency validation ────────────────────────────────────────

    def _validate_acyclic(self, subtasks: list[IntelligentSubtask]) -> None:
        """Raise CyclicDependencyError if the graph contains a cycle."""
        ids = {s.id for s in subtasks}
        for s in subtasks:
            for dep in s.depends_on:
                if dep not in ids:
                    raise CyclicDependencyError(
                        f"Subtask '{s.id}' depends on unknown '{dep}'"
                    )

        in_degree = {s.id: len(s.depends_on) for s in subtasks}
        adj: dict[str, list[str]] = {s.id: [] for s in subtasks}
        for s in subtasks:
            for dep in s.depends_on:
                adj[dep].append(s.id)

        queue = deque(sid for sid, deg in in_degree.items() if deg == 0)
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(subtasks):
            raise CyclicDependencyError("Dependency graph contains a cycle")

    # ── wave scheduling ──────────────────────────────────────────────

    def _schedule_waves(self, subtasks: list[IntelligentSubtask]) -> list[ExecutionWave]:
        """Group subtasks into execution waves based on dependency depth."""
        depth: dict[str, int] = {}
        adj: dict[str, list[str]] = {s.id: [] for s in subtasks}
        in_degree: dict[str, int] = {}

        for s in subtasks:
            in_degree[s.id] = len(s.depends_on)
            if not s.depends_on:
                depth[s.id] = 0
            for dep in s.depends_on:
                adj[dep].append(s.id)

        queue = deque(sid for sid, deg in in_degree.items() if deg == 0)
        while queue:
            node = queue.popleft()
            for neighbor in adj[node]:
                depth[neighbor] = max(depth.get(neighbor, 0), depth.get(node, 0) + 1)
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        wave_groups: dict[int, list[str]] = {}
        for s in subtasks:
            d = depth.get(s.id, 0)
            wave_groups.setdefault(d, []).append(s.id)

        waves: list[ExecutionWave] = []
        for wave_idx in sorted(wave_groups):
            ids = wave_groups[wave_idx]
            effort = sum(
                next(st.estimated_minutes for st in subtasks if st.id == sid)
                for sid in ids
            )
            waves.append(ExecutionWave(wave_idx, tuple(ids), effort))

        return waves

    def _critical_path_minutes(self, subtasks: list[IntelligentSubtask]) -> int:
        """Compute the length of the critical path in minutes."""
        id_to_subtask = {s.id: s for s in subtasks}
        memo: dict[str, int] = {}

        def dfs(sid: str) -> int:
            if sid in memo:
                return memo[sid]
            sub = id_to_subtask[sid]
            longest_dep = max((dfs(d) for d in sub.depends_on), default=0)
            result = sub.estimated_minutes + longest_dep
            memo[sid] = result
            return result

        return max((dfs(s.id) for s in subtasks), default=0)
