"""Phase 2.1 — Task Decomposer.

Breaks complex tasks into dependency-ordered subtasks with priority
and effort estimates. Supports four coordination strategies for
multi-agent execution.

Strategy selection rules:
  - SEQUENTIAL: ordered subtasks with hard dependencies
  - PARALLEL: independent subtasks, no shared state
  - VOTING: multiple agents solve same subtask, results merged
  - CASCADE: each subtask output feeds the next as input
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class CoordinationStrategy(Enum):
    """How subtasks should be coordinated across agents."""

    SEQUENTIAL = "sequential"   # One after another, dependency order
    PARALLEL = "parallel"       # All at once, independent
    VOTING = "voting"           # Multiple agents, consensus merge
    CASCADE = "cascade"         # Output of one feeds input of next


class TaskPriority(Enum):
    """Priority level for a subtask."""

    CRITICAL = "critical"   # Must complete first, blocks everything
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"   # Nice-to-have, can be skipped


class SubtaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Subtask:
    """A single decomposed unit of work.

    Attributes:
        subtask_id: Unique identifier
        name: Short human-readable name
        description: What this subtask accomplishes
        dependencies: IDs of subtasks that must complete first
        priority: Criticality of this subtask
        estimated_effort: Relative effort score (1–10)
        coordination: How agents should collaborate on this subtask
        agent_role: Suggested agent role for assignment
        acceptance_criteria: How to verify completion
    """

    subtask_id: str
    name: str
    description: str
    dependencies: tuple[str, ...]
    priority: TaskPriority
    estimated_effort: int            # 1–10 scale
    coordination: CoordinationStrategy
    agent_role: str
    acceptance_criteria: str

    def __post_init__(self) -> None:
        if not 1 <= self.estimated_effort <= 10:
            raise ValueError(
                f"estimated_effort must be 1–10, got {self.estimated_effort}"
            )


@dataclass(frozen=True)
class DependencyGraph:
    """The dependency structure derived from a task decomposition."""

    subtasks: tuple[Subtask, ...]
    adjacency: dict[str, tuple[str, ...]]      # subtask_id → depends_on
    reverse_adjacency: dict[str, tuple[str, ...]]  # subtask_id → depended_by
    entry_points: tuple[str, ...]              # subtasks with zero dependencies
    max_depth: int                             # longest dependency chain


@dataclass(frozen=True)
class DecompositionResult:
    """The complete output of task decomposition."""

    result_id: str
    original_task: str
    subtasks: tuple[Subtask, ...]
    default_strategy: CoordinationStrategy
    total_effort: int
    critical_path: tuple[str, ...]  # ordered IDs on the critical path
    graph: DependencyGraph
    summary: str


_STRATEGY_RULES: dict[CoordinationStrategy, str] = {
    CoordinationStrategy.SEQUENTIAL: (
        "Execute subtasks one at a time in dependency order. "
        "Each subtask must complete before the next begins."
    ),
    CoordinationStrategy.PARALLEL: (
        "All independent subtasks may run concurrently. "
        "Use when subtasks share no mutable state."
    ),
    CoordinationStrategy.VOTING: (
        "Assign the same subtask to multiple agents. "
        "Merge results via majority vote or consensus scoring."
    ),
    CoordinationStrategy.CASCADE: (
        "Chain subtasks so each output becomes the next input. "
        "Pipeline-style execution with intermediate validation."
    ),
}

_PRIORITY_WEIGHTS: dict[TaskPriority, float] = {
    TaskPriority.CRITICAL: 1.0,
    TaskPriority.HIGH: 0.8,
    TaskPriority.MEDIUM: 0.5,
    TaskPriority.LOW: 0.3,
    TaskPriority.OPTIONAL: 0.1,
}

# ── Keyword-based decomposition heuristics ────────────────────────────

_DECOMPOSITION_MARKERS: dict[str, list[str]] = {
    "implement": ["design", "implement", "test", "review", "document"],
    "refactor": ["analyze", "plan", "extract", "migrate", "verify"],
    "debug": ["reproduce", "isolate", "fix", "verify", "regression_test"],
    "review": ["read", "analyze", "report", "recommend", "approve"],
    "deploy": ["build", "stage", "validate", "deploy", "monitor"],
    "migrate": ["backup", "prepare", "execute", "validate", "cleanup"],
    "research": ["search", "evaluate", "synthesize", "report", "recommend"],
    "optimize": ["profile", "identify", "implement", "benchmark", "validate"],
}


def _detect_task_domain(task: str) -> str:
    """Heuristically classify the task domain from keywords."""
    task_lower = task.lower()
    for domain in _DECOMPOSITION_MARKERS:
        if domain in task_lower:
            return domain
    return "implement"


def _estimate_effort(description: str, priority: TaskPriority) -> int:
    """Rough effort estimate from description length and priority."""
    base = max(1, min(10, len(description.split()) // 6))
    if priority == TaskPriority.CRITICAL:
        base = max(base, 6)
    elif priority == TaskPriority.OPTIONAL:
        base = min(base, 3)
    return base


def _topological_order(graph: DependencyGraph) -> tuple[str, ...]:
    """Kahn's algorithm for topological sort. Returns execution order."""
    in_degree: dict[str, int] = {s.subtask_id: len(s.dependencies) for s in graph.subtasks}
    zero_in = [nid for nid, deg in in_degree.items() if deg == 0]
    order: list[str] = []

    while zero_in:
        node = zero_in.pop(0)
        order.append(node)
        for dependent in graph.reverse_adjacency.get(node, ()):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                zero_in.append(dependent)

    return tuple(order)


def _find_critical_path(graph: DependencyGraph) -> tuple[str, ...]:
    """Find the longest path through the dependency graph (critical path)."""
    topo = _topological_order(graph)

    dist: dict[str, int] = {s.subtask_id: 1 for s in graph.subtasks}
    prev: dict[str, str | None] = {s.subtask_id: None for s in graph.subtasks}

    for node in topo:
        for successor in graph.reverse_adjacency.get(node, ()):
            succ_subtask = next(s for s in graph.subtasks if s.subtask_id == successor)
            new_dist = dist[node] + succ_subtask.estimated_effort
            if new_dist > dist.get(successor, 0):
                dist[successor] = new_dist
                prev[successor] = node

    end_node = max(dist, key=lambda k: dist[k])
    path: list[str] = []
    current: str | None = end_node
    while current is not None:
        path.append(current)
        current = prev[current]
    path.reverse()
    return tuple(path)


def _recommend_agent_role(phase: str) -> str:
    """Map a decomposition phase to a suggested agent role."""
    role_map: dict[str, str] = {
        "design": "architect",
        "plan": "architect",
        "analyze": "analyst",
        "search": "explorer",
        "evaluate": "analyst",
        "synthesize": "writer",
        "report": "writer",
        "recommend": "architect",
        "implement": "executor",
        "migrate": "executor",
        "extract": "executor",
        "fix": "debugger",
        "isolate": "debugger",
        "test": "test-engineer",
        "verify": "verifier",
        "regression_test": "test-engineer",
        "review": "code-reviewer",
        "approve": "verifier",
        "build": "executor",
        "stage": "executor",
        "deploy": "executor",
        "monitor": "executor",
        "backup": "executor",
        "prepare": "executor",
        "execute": "executor",
        "cleanup": "executor",
        "profile": "scientist",
        "identify": "analyst",
        "benchmark": "scientist",
        "validate": "verifier",
        "read": "explorer",
        "reproduce": "debugger",
        "document": "writer",
    }
    return role_map.get(phase, "executor")


@dataclass
class TaskDecomposer:
    """Breaks complex tasks into dependency-ordered subtask graphs.

    Usage::

        decomposer = TaskDecomposer()
        result = decomposer.decompose(
            "Implement user authentication with OAuth2 and JWT tokens"
        )
        for subtask in result.subtasks:
            print(f"[{subtask.priority.value}] {subtask.name}")

    The decomposer uses keyword heuristics to identify task domains
    and produces a structured breakdown with dependency ordering.
    Custom phase generators can be registered for domain-specific logic.
    """

    _phase_generators: dict[str, Callable[[str, str], list[Subtask]]] = field(
        default_factory=dict
    )

    def decompose(
        self,
        task: str,
        *,
        strategy: CoordinationStrategy | None = None,
        max_subtasks: int = 12,
    ) -> DecompositionResult:
        """Decompose a task description into dependency-ordered subtasks.

        Args:
            task: Natural-language description of the task.
            strategy: Override the auto-detected coordination strategy.
            max_subtasks: Upper bound on subtask count.

        Returns:
            DecompositionResult with subtask graph and execution plan.
        """
        domain = _detect_task_domain(task)
        phases = _DECOMPOSITION_MARKERS.get(domain, _DECOMPOSITION_MARKERS["implement"])
        phases = phases[:max_subtasks]

        subtasks: list[Subtask] = []
        prev_id: str | None = None

        for i, phase in enumerate(phases):
            priority = (
                TaskPriority.CRITICAL if i == 0
                else TaskPriority.OPTIONAL if i >= len(phases) - 1
                else TaskPriority.HIGH if i <= 1
                else TaskPriority.MEDIUM
            )

            desc = f"{phase.capitalize()} phase for: {task[:120]}"
            deps = (prev_id,) if prev_id else ()
            role = _recommend_agent_role(phase)

            subtask = Subtask(
                subtask_id=f"sub-{uuid.uuid4().hex[:8]}",
                name=f"[{domain}] {phase}",
                description=desc,
                dependencies=deps,
                priority=priority,
                estimated_effort=_estimate_effort(desc, priority),
                coordination=(
                    CoordinationStrategy.PARALLEL if phase in ("test", "review")
                    else CoordinationStrategy.SEQUENTIAL
                ),
                agent_role=role,
                acceptance_criteria=f"Phase '{phase}' completed with passing validation.",
            )
            subtasks.append(subtask)
            prev_id = subtask.subtask_id

        if strategy is None:
            strategy = (
                CoordinationStrategy.PARALLEL
                if len(subtasks) > 5 and domain in ("test", "review")
                else CoordinationStrategy.SEQUENTIAL
            )

        total = sum(s.estimated_effort for s in subtasks)
        graph = self._build_graph(subtasks)
        critical = _find_critical_path(graph)

        summary = (
            f"Decomposed '{task[:80]}' into {len(subtasks)} subtasks "
            f"({domain} domain, {strategy.value} strategy, "
            f"total effort={total}, critical path={len(critical)} steps)."
        )

        return DecompositionResult(
            result_id=f"dr-{uuid.uuid4().hex[:12]}",
            original_task=task,
            subtasks=tuple(subtasks),
            default_strategy=strategy,
            total_effort=total,
            critical_path=critical,
            graph=graph,
            summary=summary,
        )

    def register_phase_generator(
        self,
        domain: str,
        generator: Callable[[str, str], list[Subtask]],
    ) -> None:
        """Register a custom phase generator for a task domain."""
        self._phase_generators[domain] = generator

    @staticmethod
    def _build_graph(subtasks: list[Subtask]) -> DependencyGraph:
        """Build adjacency structures from a subtask list."""
        adjacency: dict[str, tuple[str, ...]] = {}
        reverse: dict[str, list[str]] = {}
        entry_points: list[str] = []

        for s in subtasks:
            adjacency[s.subtask_id] = s.dependencies
            if not s.dependencies:
                entry_points.append(s.subtask_id)
            for dep in s.dependencies:
                reverse.setdefault(dep, []).append(s.subtask_id)

        reverse_adj = {k: tuple(v) for k, v in reverse.items()}
        for s in subtasks:
            reverse_adj.setdefault(s.subtask_id, ())

        max_depth = 0
        for s in subtasks:
            depth = TaskDecomposer._compute_depth(s.subtask_id, adjacency)
            max_depth = max(max_depth, depth)

        return DependencyGraph(
            subtasks=tuple(subtasks),
            adjacency=adjacency,
            reverse_adjacency=reverse_adj,
            entry_points=tuple(entry_points),
            max_depth=max_depth,
        )

    @staticmethod
    def _compute_depth(
        node_id: str,
        adjacency: dict[str, tuple[str, ...]],
        memo: dict[str, int] | None = None,
    ) -> int:
        """Recursive depth computation with memoization."""
        if memo is None:
            memo = {}
        if node_id in memo:
            return memo[node_id]
        deps = adjacency.get(node_id, ())
        if not deps:
            memo[node_id] = 1
            return 1
        depth = 1 + max(
            TaskDecomposer._compute_depth(d, adjacency, memo) for d in deps
        )
        memo[node_id] = depth
        return depth

    def get_execution_order(self, result: DecompositionResult) -> tuple[Subtask, ...]:
        """Return subtasks in topological execution order."""
        order_ids = _topological_order(result.graph)
        subtask_map = {s.subtask_id: s for s in result.subtasks}
        return tuple(subtask_map[nid] for nid in order_ids if nid in subtask_map)

    def get_next_available(
        self,
        result: DecompositionResult,
        completed: set[str],
    ) -> tuple[Subtask, ...]:
        """Return subtasks whose dependencies are all satisfied."""
        available: list[Subtask] = []
        for s in result.subtasks:
            if s.subtask_id in completed:
                continue
            if all(d in completed for d in s.dependencies):
                available.append(s)
        return tuple(available)


__all__ = [
    "CoordinationStrategy",
    "DecompositionResult",
    "DependencyGraph",
    "Subtask",
    "SubtaskStatus",
    "TaskDecomposer",
    "TaskPriority",
]
