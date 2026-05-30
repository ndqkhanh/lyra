"""Hierarchical Swarm Topology — captain-worker squads with mesh cross-communication.

Implements a hybrid hierarchical-mesh topology for agent swarms:
  - Multi-level nesting: Colony → Squad → Worker (3 levels)
  - Captain-led squads with configurable role templates
  - Cross-squad mesh for peer-to-peer communication
  - Role-based task routing within squads
  - Topology node lookup, traversal, and manipulation
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class TopologyLevel(StrEnum):
    """Nesting level in the topology hierarchy."""

    COLONY = "colony"
    SQUAD = "squad"
    WORKER = "worker"


class SquadRole(StrEnum):
    """Roles within a squad."""

    CAPTAIN = "captain"
    WORKER = "worker"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"


@dataclass(frozen=True)
class TopologyNode:
    """A node in the topology tree — colony, squad, or worker."""

    node_id: str
    level: TopologyLevel
    parent_id: str | None = None
    children: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"TopologyNode(id={self.node_id}, level={self.level.value}, parent={self.parent_id})"


@dataclass(frozen=True)
class SquadTemplate:
    """Template for creating a squad with role requirements and constraints."""

    name: str
    domain: str
    min_workers: int = 2
    max_workers: int = 10
    required_roles: tuple[SquadRole, ...] = (
        SquadRole.CAPTAIN,
        SquadRole.WORKER,
    )
    stagnation_threshold_ms: float = 10_000.0
    health_check_interval_ms: float = 1_000.0
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class HierarchicalTopology:
    """Manages the full hierarchical swarm topology.

    Colonies contain squads, which contain workers. Cross-squad mesh
    communication is supported via peer lookup at each level.

    Usage::

        topo = HierarchicalTopology()
        topo.add_colony("research-colony")
        topo.add_squad("research-colony", "sq-1", SquadTemplate(...))
        topo.add_worker("sq-1", "agent-7", SquadRole.WORKER)
        captain = topo.route_task(target_role=SquadRole.CAPTAIN, squad_id="sq-1")
    """

    def __init__(self) -> None:
        self._nodes: dict[str, TopologyNode] = {}
        self._templates: dict[str, SquadTemplate] = {}
        self._role_map: dict[str, dict[SquadRole, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

    # ── Properties ───────────────────────────────────────────────

    @property
    def colony_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.level == TopologyLevel.COLONY)

    @property
    def squad_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.level == TopologyLevel.SQUAD)

    @property
    def worker_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.level == TopologyLevel.WORKER)

    # ── Node Management ──────────────────────────────────────────

    def add_colony(self, colony_id: str, metadata: dict | None = None) -> TopologyNode:
        """Create a top-level colony node."""
        if colony_id in self._nodes:
            raise ValueError(f"Colony '{colony_id}' already exists")
        node = TopologyNode(
            node_id=colony_id,
            level=TopologyLevel.COLONY,
            metadata=metadata or {},
        )
        self._nodes[colony_id] = node
        return node

    def add_squad(
        self,
        colony_id: str,
        squad_id: str,
        template: SquadTemplate,
        metadata: dict | None = None,
    ) -> TopologyNode:
        """Create a squad node under a colony."""
        if squad_id in self._nodes:
            raise ValueError(f"Node '{squad_id}' already exists")
        colony = self._nodes.get(colony_id)
        if colony is None or colony.level != TopologyLevel.COLONY:
            raise ValueError(f"Parent colony '{colony_id}' not found")

        node = TopologyNode(
            node_id=squad_id,
            level=TopologyLevel.SQUAD,
            parent_id=colony_id,
            metadata=metadata or {},
        )
        self._nodes[squad_id] = node
        self._templates[squad_id] = template
        self._nodes[colony_id] = TopologyNode(
            node_id=colony.node_id,
            level=colony.level,
            parent_id=colony.parent_id,
            children=colony.children + (squad_id,),
            metadata=colony.metadata,
        )
        return node

    def add_worker(
        self,
        squad_id: str,
        worker_id: str,
        role: SquadRole,
        metadata: dict | None = None,
    ) -> TopologyNode:
        """Create a worker node under a squad."""
        if worker_id in self._nodes:
            raise ValueError(f"Node '{worker_id}' already exists")
        squad = self._nodes.get(squad_id)
        if squad is None or squad.level != TopologyLevel.SQUAD:
            raise ValueError(f"Parent squad '{squad_id}' not found")

        template = self._templates.get(squad_id)
        if template is not None:
            current_count = len(squad.children)
            if current_count >= template.max_workers:
                raise ValueError(
                    f"Adding worker '{worker_id}' exceeds max workers "
                    f"({current_count} >= {template.max_workers}) for squad '{squad_id}'"
                )

        node = TopologyNode(
            node_id=worker_id,
            level=TopologyLevel.WORKER,
            parent_id=squad_id,
            metadata=metadata or {},
        )
        self._nodes[worker_id] = node
        self._role_map[squad_id][role].append(worker_id)
        self._nodes[squad_id] = TopologyNode(
            node_id=squad.node_id,
            level=squad.level,
            parent_id=squad.parent_id,
            children=squad.children + (worker_id,),
            metadata=squad.metadata,
        )
        return node

    def remove_worker(self, worker_id: str) -> None:
        """Remove a worker node."""
        worker = self._get_node_or_raise(worker_id)
        if worker.level != TopologyLevel.WORKER:
            raise ValueError(f"Node '{worker_id}' is not a worker")
        self._remove_from_parent(worker)
        self._nodes.pop(worker_id, None)
        for role_map in self._role_map.values():
            for role_list in role_map.values():
                if worker_id in role_list:
                    role_list.remove(worker_id)

    def remove_squad(self, squad_id: str) -> None:
        """Remove a squad and all its workers."""
        squad = self._get_node_or_raise(squad_id)
        if squad.level != TopologyLevel.SQUAD:
            raise ValueError(f"Node '{squad_id}' is not a squad")
        for child_id in list(squad.children):
            self._nodes.pop(child_id, None)
        self._role_map.pop(squad_id, None)
        if squad.parent_id:
            self._remove_child_from_node(squad.parent_id, squad_id)
        self._nodes.pop(squad_id, None)
        self._templates.pop(squad_id, None)

    def remove_colony(self, colony_id: str) -> None:
        """Remove a colony and all its squads and workers."""
        colony = self._get_node_or_raise(colony_id)
        if colony.level != TopologyLevel.COLONY:
            raise ValueError(f"Node '{colony_id}' is not a colony")
        for squad_id in list(colony.children):
            self.remove_squad(squad_id)
        self._nodes.pop(colony_id, None)

    # ── Queries ───────────────────────────────────────────────────

    def get_node(self, node_id: str) -> TopologyNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> list[TopologyNode]:
        """Get all direct children of a node."""
        node = self._nodes.get(node_id)
        if node is None:
            return []
        return [self._nodes[c] for c in node.children if c in self._nodes]

    def get_parent(self, node_id: str) -> TopologyNode | None:
        """Get the parent node."""
        node = self._nodes.get(node_id)
        if node is None or node.parent_id is None:
            return None
        return self._nodes.get(node.parent_id)

    def get_peers(self, node_id: str) -> list[TopologyNode]:
        """Get sibling nodes at the same level with the same parent."""
        node = self._nodes.get(node_id)
        if node is None or node.parent_id is None:
            return []
        parent = self._nodes.get(node.parent_id)
        if parent is None:
            return []
        peers: list[TopologyNode] = []
        for child_id in parent.children:
            if child_id != node_id and child_id in self._nodes:
                peers.append(self._nodes[child_id])
        return peers

    def get_squad_workers(self, squad_id: str) -> list[TopologyNode]:
        """Get all workers in a squad."""
        return self.get_children(squad_id)

    def list_by_level(self, level: TopologyLevel) -> list[TopologyNode]:
        """List all nodes at a given level."""
        return [n for n in self._nodes.values() if n.level == level]

    def get_summary(self) -> dict:
        """Return a summary of the topology."""
        return {
            "colonies": self.colony_count,
            "squads": self.squad_count,
            "workers": self.worker_count,
            "total_nodes": len(self._nodes),
        }

    # ── Task Routing ──────────────────────────────────────────────

    def route_task(
        self,
        target_role: SquadRole,
        squad_id: str | None = None,
        exclude_ids: set[str] | None = None,
    ) -> TopologyNode | None:
        """Route a task to a worker with the given role.

        If squad_id is specified, search only within that squad.
        Otherwise, search across all squads.
        """
        exclude = exclude_ids or set()

        if squad_id:
            candidates = self._role_map.get(squad_id, {}).get(target_role, [])
            for candidate_id in candidates:
                if candidate_id not in exclude and candidate_id in self._nodes:
                    return self._nodes[candidate_id]
            return None

        for _sid, role_map in self._role_map.items():
            candidates = role_map.get(target_role, [])
            for candidate_id in candidates:
                if candidate_id not in exclude and candidate_id in self._nodes:
                    return self._nodes[candidate_id]
        return None

    def get_role(self, worker_id: str, squad_id: str) -> SquadRole | None:
        """Get the role of a worker within a squad."""
        role_map = self._role_map.get(squad_id, {})
        for role, ids in role_map.items():
            if worker_id in ids:
                return role
        return None

    def reset(self) -> None:
        """Reset the entire topology."""
        self._nodes.clear()
        self._templates.clear()
        self._role_map.clear()

    # ── Private ───────────────────────────────────────────────────

    def _get_node_or_raise(self, node_id: str) -> TopologyNode:
        node = self._nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found")
        return node

    def _remove_from_parent(self, node: TopologyNode) -> None:
        if node.parent_id is None:
            return
        parent = self._nodes.get(node.parent_id)
        if parent is None:
            return
        new_children = tuple(c for c in parent.children if c != node.node_id)
        self._nodes[node.parent_id] = TopologyNode(
            node_id=parent.node_id,
            level=parent.level,
            parent_id=parent.parent_id,
            children=new_children,
            metadata=parent.metadata,
        )

    def _remove_child_from_node(self, node_id: str, child_id: str) -> None:
        node = self._nodes.get(node_id)
        if node is None:
            return
        new_children = tuple(c for c in node.children if c != child_id)
        self._nodes[node_id] = TopologyNode(
            node_id=node.node_id,
            level=node.level,
            parent_id=node.parent_id,
            children=new_children,
            metadata=node.metadata,
        )
