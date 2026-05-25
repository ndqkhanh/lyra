"""L3 Procedural Memory — skills, workflows, knowledge graph entries.

Stores learned procedures as structured skill entries with versioning
and dependency tracking. Serves as the skill registry for the agent.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Procedure:
    """A learned procedure or skill.

    Attributes:
        proc_id: Unique identifier.
        name: Human-readable procedure name.
        description: What the procedure does.
        steps: Ordered tuple of step descriptions.
        triggers: Keywords/contexts that activate this procedure.
        dependencies: Tuple of proc_ids this procedure depends on.
        success_count: Number of successful applications.
        failure_count: Number of failed applications.
        version: Monotonically increasing version number.
        created_at: Unix timestamp of creation.
        updated_at: Unix timestamp of last update.
    """

    proc_id: str
    name: str
    description: str
    steps: tuple[str, ...]
    triggers: tuple[str, ...]
    dependencies: tuple[str, ...]
    success_count: int
    failure_count: int
    version: int
    created_at: float
    updated_at: float


@dataclass(frozen=True)
class KnowledgeGraphEntry:
    """A node in the procedural knowledge graph.

    Attributes:
        node_id: Unique node identifier.
        label: Display label.
        node_type: Category (e.g., "concept", "tool", "pattern").
        properties: Key-value metadata.
        edges: Tuple of (target_node_id, relation_type) pairs.
    """

    node_id: str
    label: str
    node_type: str
    properties: dict[str, str]
    edges: tuple[tuple[str, str], ...]


class ProceduralMemory:
    """L3 procedural memory — skills and knowledge graph.

    Manages learned procedures with success/failure tracking and
    knowledge graph entries for relational reasoning.
    """

    def __init__(self) -> None:
        self._procedures: dict[str, Procedure] = {}
        self._kg_entries: dict[str, KnowledgeGraphEntry] = {}
        self._counter = 0
        self._node_counter = 0

    async def register_procedure(
        self,
        name: str,
        description: str,
        steps: tuple[str, ...],
        triggers: tuple[str, ...] = (),
        dependencies: tuple[str, ...] = (),
    ) -> str:
        """Register a new procedure.

        Args:
            name: Human-readable name.
            description: What the procedure does.
            steps: Ordered steps.
            triggers: Activation keywords.
            dependencies: Required procedure IDs.

        Returns:
            The proc_id.
        """
        self._counter += 1
        proc_id = f"proc-{self._counter}"
        now = time.time()
        procedure = Procedure(
            proc_id=proc_id,
            name=name,
            description=description,
            steps=steps,
            triggers=triggers,
            dependencies=dependencies,
            success_count=0,
            failure_count=0,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._procedures[proc_id] = procedure
        return proc_id

    async def find_by_trigger(self, trigger: str) -> tuple[Procedure, ...]:
        """Find procedures matching a trigger keyword.

        Args:
            trigger: The keyword to match.

        Returns:
            Matching procedures sorted by success rate.
        """
        trigger_lower = trigger.lower()
        matches = [
            p
            for p in self._procedures.values()
            if any(trigger_lower in t.lower() for t in p.triggers)
        ]
        matches.sort(
            key=lambda p: (
                p.success_count / max(p.success_count + p.failure_count, 1)
            ),
            reverse=True,
        )
        return tuple(matches)

    async def record_success(self, proc_id: str) -> None:
        """Record a successful application of a procedure."""
        if proc_id not in self._procedures:
            raise KeyError(f"Procedure not found: {proc_id}")
        p = self._procedures[proc_id]
        self._procedures[proc_id] = Procedure(
            proc_id=p.proc_id,
            name=p.name,
            description=p.description,
            steps=p.steps,
            triggers=p.triggers,
            dependencies=p.dependencies,
            success_count=p.success_count + 1,
            failure_count=p.failure_count,
            version=p.version,
            created_at=p.created_at,
            updated_at=time.time(),
        )

    async def record_failure(self, proc_id: str) -> None:
        """Record a failed application of a procedure."""
        if proc_id not in self._procedures:
            raise KeyError(f"Procedure not found: {proc_id}")
        p = self._procedures[proc_id]
        self._procedures[proc_id] = Procedure(
            proc_id=p.proc_id,
            name=p.name,
            description=p.description,
            steps=p.steps,
            triggers=p.triggers,
            dependencies=p.dependencies,
            success_count=p.success_count,
            failure_count=p.failure_count + 1,
            version=p.version,
            created_at=p.created_at,
            updated_at=time.time(),
        )

    async def get_reliable_procedures(
        self, min_success_rate: float = 0.7
    ) -> tuple[Procedure, ...]:
        """Get procedures with success rate above the threshold."""
        result = []
        for p in self._procedures.values():
            total = p.success_count + p.failure_count
            if total == 0:
                continue
            rate = p.success_count / total
            if rate >= min_success_rate:
                result.append(p)
        result.sort(key=lambda p: p.success_count, reverse=True)
        return tuple(result)

    async def add_kg_entry(
        self,
        label: str,
        node_type: str,
        properties: dict[str, str] | None = None,
        edges: tuple[tuple[str, str], ...] = (),
    ) -> str:
        """Add a knowledge graph entry.

        Args:
            label: Display label.
            node_type: Category of the node.
            properties: Optional metadata.
            edges: Outgoing edges as (target_node_id, relation) pairs.

        Returns:
            The node_id.
        """
        self._node_counter += 1
        node_id = f"node-{self._node_counter}"
        entry = KnowledgeGraphEntry(
            node_id=node_id,
            label=label,
            node_type=node_type,
            properties=properties or {},
            edges=edges,
        )
        self._kg_entries[node_id] = entry
        return node_id

    async def traverse_kg(
        self, start_node_id: str, relation: str | None = None
    ) -> tuple[KnowledgeGraphEntry, ...]:
        """Traverse the knowledge graph from a starting node.

        Args:
            start_node_id: Where to start traversal.
            relation: Optional relation type filter.

        Returns:
            Connected KnowledgeGraphEntry nodes.
        """
        if start_node_id not in self._kg_entries:
            raise KeyError(f"Node not found: {start_node_id}")

        visited: set[str] = set()
        result: list[KnowledgeGraphEntry] = []
        queue = [start_node_id]

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)

            if node_id in self._kg_entries:
                entry = self._kg_entries[node_id]
                result.append(entry)
                for target, rel in entry.edges:
                    if target not in visited:
                        if relation is None or rel == relation:
                            queue.append(target)

        return tuple(result)

    @property
    def procedure_count(self) -> int:
        return len(self._procedures)

    @property
    def kg_node_count(self) -> int:
        return len(self._kg_entries)
