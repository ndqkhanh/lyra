"""Skill Dependency Resolution — graph-based dependency resolution with circular detection (Tarjan's algorithm)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lyra_skill_loader.exceptions import DependencyError

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class SkillNode:
    """Represents a skill and its dependency/conflict relationships."""

    skill_id: str
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    provides_capability: str = ""


@dataclass(frozen=True)
class ResolutionResult:
    """Result of dependency resolution."""

    load_order: tuple[str, ...]
    conflicts: tuple[str, ...]
    missing_deps: tuple[str, ...]
    circular_deps: tuple[tuple[str, ...], ...]

    @property
    def is_ok(self) -> bool:
        """True if the resolution found no conflicts, missing deps, or circular deps."""
        return not self.conflicts and not self.missing_deps and not self.circular_deps


class DependencyGraph:
    """Internal directed graph of skill dependencies."""

    def __init__(self) -> None:
        self._nodes: dict[str, SkillNode] = {}

    def add_skill(self, node: SkillNode) -> None:
        """Add a skill node to the graph."""
        self._nodes[node.skill_id] = node

    def remove_skill(self, skill_id: str) -> None:
        """Remove a skill node from the graph."""
        self._nodes.pop(skill_id, None)

    def get_node(self, skill_id: str) -> SkillNode | None:
        """Look up a skill node by id."""
        return self._nodes.get(skill_id)

    def has_node(self, skill_id: str) -> bool:
        """Check if a node exists in the graph."""
        return skill_id in self._nodes

    def all_skill_ids(self) -> tuple[str, ...]:
        """Return all skill ids in the graph."""
        return tuple(self._nodes.keys())

    def neighbours(self, skill_id: str) -> list[str]:
        """Return list of skill ids that depend on *skill_id*."""
        result: list[str] = []
        for sid, node in self._nodes.items():
            if skill_id in node.dependencies:
                result.append(sid)
        return result


class DependencyResolver:
    """Resolves skill dependency graphs, detects cycles, and computes optimal load order.

    Uses Tarjan's algorithm for strongly connected component (cycle) detection
    and Kahn's algorithm for topological sorting.
    """

    def __init__(self) -> None:
        self._graph = DependencyGraph()

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    # ------------------------------------------------------------------
    # Graph management
    # ------------------------------------------------------------------

    def add_skill(self, node: SkillNode) -> None:
        """Add a skill to the dependency graph."""
        self._graph.add_skill(node)

    def remove_skill(self, skill_id: str) -> None:
        """Remove a skill from the dependency graph."""
        self._graph.remove_skill(skill_id)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, skill_ids: Sequence[str]) -> ResolutionResult:
        """Fully resolve a set of skill ids.

        Detects circular dependencies, checks for missing dependencies,
        resolves conflicts, and computes optimal load order.

        Args:
            skill_ids: Skill ids to resolve.

        Returns:
            A :class:`ResolutionResult` describing the resolution.
        """
        ids = list(skill_ids)
        conflicts = self.resolve_conflicts(ids)
        circular = self.detect_circular(ids)
        missing = self._find_missing(ids)
        load_order = self.optimal_load_order(ids)

        return ResolutionResult(
            load_order=tuple(load_order),
            conflicts=tuple(conflicts),
            missing_deps=tuple(missing),
            circular_deps=tuple(tuple(c) for c in circular),
        )

    # ------------------------------------------------------------------
    # Cycle detection — Tarjan's algorithm
    # ------------------------------------------------------------------

    def detect_circular(self, skill_ids: Sequence[str]) -> list[list[str]]:
        """Detect circular dependencies using Tarjan's strongly connected components algorithm.

        Returns:
            List of cycles, where each cycle is a list of skill ids.
            Only returns SCCs with more than one node (true cycles).
        """
        nodes = {sid: self._graph.get_node(sid) for sid in skill_ids}
        nodes = {k: v for k, v in nodes.items() if v is not None}

        if not nodes:
            return []

        index_counter = [0]
        indices: dict[str, int] = {}
        lowlink: dict[str, int] = {}
        on_stack: set[str] = set()
        stack: list[str] = []
        sccs: list[list[str]] = []

        def _strongconnect(v: str) -> None:
            indices[v] = index_counter[0]
            lowlink[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack.add(v)

            node = nodes[v]
            for dep in node.dependencies:
                if dep not in nodes:
                    continue
                if dep not in indices:
                    _strongconnect(dep)
                    lowlink[v] = min(lowlink[v], lowlink[dep])
                elif dep in on_stack:
                    lowlink[v] = min(lowlink[v], indices[dep])

            if lowlink[v] == indices[v]:
                scc: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == v:
                        break
                if len(scc) > 1:
                    sccs.append(scc)

        for sid in nodes:
            if sid not in indices:
                _strongconnect(sid)

        return sccs

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def resolve_conflicts(self, skill_ids: Sequence[str]) -> list[str]:
        """Identify conflicting skill pairs and resolve by keeping the higher-priority one.

        Two skills conflict if one declares the other in its ``conflicts`` list.

        Returns:
            List of skill ids that should be excluded due to conflicts.
        """
        excluded: set[str] = set()
        ids_set = set(skill_ids)

        for sid in skill_ids:
            if sid in excluded:
                continue
            node = self._graph.get_node(sid)
            if node is None:
                continue
            for conflict_id in node.conflicts:
                if conflict_id in ids_set and conflict_id not in excluded:
                    # Keep the one that was requested first (in original order)
                    excluded.add(conflict_id)

        return [e for e in skill_ids if e in excluded]

    # ------------------------------------------------------------------
    # Missing dependency detection
    # ------------------------------------------------------------------

    def _find_missing(self, skill_ids: Sequence[str]) -> list[str]:
        """Find dependencies not present in the graph."""
        ids_set = set(skill_ids)
        missing: list[str] = []

        for sid in skill_ids:
            node = self._graph.get_node(sid)
            if node is None:
                continue
            for dep in node.dependencies:
                if dep not in ids_set and not self._graph.has_node(dep):
                    missing.append(dep)

        return list(set(missing))

    # ------------------------------------------------------------------
    # Optimal load order — Kahn's algorithm
    # ------------------------------------------------------------------

    def optimal_load_order(self, skill_ids: Sequence[str]) -> list[str]:
        """Compute optimal load order using topological sort (Kahn's algorithm).

        Dependencies are loaded before the skills that depend on them.

        Args:
            skill_ids: Skill ids to order.

        Returns:
            List of skill ids in optimal load order.
        """
        relevant_nodes: dict[str, SkillNode] = {}
        for sid in skill_ids:
            node = self._graph.get_node(sid)
            if node is not None:
                relevant_nodes[sid] = node

        # Also include transitive dependencies that are in the graph
        all_consider: set[str] = set(relevant_nodes.keys())
        queue = list(all_consider)
        while queue:
            sid = queue.pop(0)
            node = self._graph.get_node(sid)
            if node is None:
                continue
            for dep in node.dependencies:
                if dep not in all_consider and self._graph.has_node(dep):
                    all_consider.add(dep)
                    queue.append(dep)

        # Build adjacency and in-degree for all involved nodes
        in_degree: dict[str, int] = {sid: 0 for sid in all_consider}
        adjacency: dict[str, list[str]] = {sid: [] for sid in all_consider}

        for sid in all_consider:
            node = self._graph.get_node(sid)
            if node is None:
                continue
            for dep in node.dependencies:
                if dep in all_consider:
                    adjacency.setdefault(dep, []).append(sid)
                    in_degree[sid] = in_degree.get(sid, 0) + 1

        # Kahn's algorithm
        result: list[str] = []
        no_incoming = [sid for sid in all_consider if in_degree.get(sid, 0) == 0]

        while no_incoming:
            no_incoming.sort(key=lambda s: skill_ids.index(s) if s in skill_ids else len(skill_ids))
            current = no_incoming.pop(0)
            result.append(current)
            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    no_incoming.append(neighbor)

        # If there are remaining nodes (cycle), append them
        remaining = [sid for sid in all_consider if sid not in result]
        result.extend(remaining)

        return result
