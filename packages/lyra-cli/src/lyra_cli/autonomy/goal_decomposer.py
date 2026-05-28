"""Goal decomposition engine for Lyra autonomy.

Breaks high-level goals into subtasks with dependency graphs and
produces a topological execution order.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Subtask:
    """A single executable subtask produced by decomposition."""

    id: str
    description: str
    depends_on: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Goal:
    """A high-level goal to be decomposed."""

    id: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DependencyGraph:
    """A directed acyclic graph of subtasks ready for execution."""

    goal: Goal
    subtasks: tuple[Subtask, ...] = ()
    execution_order: tuple[str, ...] = ()

    def subtask_by_id(self, subtask_id: str) -> Subtask | None:
        """Look up a subtask by its id."""
        for s in self.subtasks:
            if s.id == subtask_id:
                return s
        return None


class CyclicDependencyError(Exception):
    """Raised when the dependency graph contains a cycle."""


# ---------------------------------------------------------------------------
# Decomposer
# ---------------------------------------------------------------------------


@dataclass
class GoalDecomposer:
    """Decomposes a high-level :class:`Goal` into a :class:`DependencyGraph`.

    Usage::

        decomposer = GoalDecomposer()
        graph = decomposer.decompose(goal)
        for step_id in graph.execution_order:
            subtask = graph.subtask_by_id(step_id)
            ...
    """

    def decompose(self, goal: Goal) -> DependencyGraph:
        """Break *goal* into subtasks and compute execution order.

        The default implementation creates a three-phase decomposition:
        research, implement, verify.  Subclasses or custom instances
        can override :meth:`_generate_subtasks` to provide domain-
        specific decomposition logic.

        Raises:
            CyclicDependencyError: if dependencies form a cycle.
        """
        subtasks = self._generate_subtasks(goal)
        execution_order = self._topological_sort(subtasks)
        return DependencyGraph(
            goal=goal,
            subtasks=tuple(subtasks),
            execution_order=tuple(execution_order),
        )

    # ------------------------------------------------------------------
    # Extensibility point
    # ------------------------------------------------------------------

    def _generate_subtasks(self, goal: Goal) -> list[Subtask]:
        """Generate subtasks for *goal*. Override for custom logic."""
        return [
            Subtask(
                id=f"{goal.id}_research",
                description=f"Research requirements for: {goal.description}",
            ),
            Subtask(
                id=f"{goal.id}_implement",
                description=f"Implement: {goal.description}",
                depends_on=(f"{goal.id}_research",),
            ),
            Subtask(
                id=f"{goal.id}_verify",
                description=f"Verify: {goal.description}",
                depends_on=(f"{goal.id}_implement",),
            ),
        ]

    # ------------------------------------------------------------------
    # Topological sort (Kahn's algorithm)
    # ------------------------------------------------------------------

    @staticmethod
    def _topological_sort(subtasks: list[Subtask]) -> list[str]:
        """Return subtask IDs in dependency order using Kahn's algorithm.

        Raises:
            CyclicDependencyError: if a cycle is detected.
        """
        in_degree: dict[str, int] = {s.id: 0 for s in subtasks}
        adjacency: dict[str, list[str]] = {s.id: [] for s in subtasks}

        for sub in subtasks:
            for dep in sub.depends_on:
                if dep not in adjacency:
                    raise CyclicDependencyError(
                        f"Subtask {sub.id!r} depends on unknown subtask {dep!r}"
                    )
                adjacency[dep].append(sub.id)
                in_degree[sub.id] = in_degree.get(sub.id, 0) + 1

        queue: deque[str] = deque(
            sid for sid, deg in in_degree.items() if deg == 0
        )
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbour in adjacency.get(current, []):
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        if len(order) != len(subtasks):
            raise CyclicDependencyError(
                "Dependency graph contains a cycle; topological sort cannot complete."
            )

        return order
