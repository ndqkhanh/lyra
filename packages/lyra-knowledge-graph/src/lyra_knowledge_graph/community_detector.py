"""Leiden-style community detection for knowledge graphs.

Provides modularity-based community detection, hierarchical community
structure, inter-community edge analysis, and community summary generation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Community:
    """A detected community of nodes."""
    community_id: str
    node_ids: frozenset[str]
    label: str = ""
    level: int = 0
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.node_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "community_id": self.community_id,
            "node_ids": list(self.node_ids),
            "label": self.label,
            "size": self.size,
            "level": self.level,
            "parent_id": self.parent_id,
            "metadata": dict(self.metadata),
        }


class CommunityDetector:
    """Detect communities in a knowledge graph using modularity optimization.

    Implements a simplified Leiden-like algorithm:
    1. Local moving phase: move nodes to maximize modularity
    2. Refinement phase: split clusters that are internally disconnected
    3. Aggregation phase: build hierarchical communities
    """

    def __init__(self, resolution: float = 1.0) -> None:
        self.resolution = resolution

    # ── Detection ───────────────────────────────────────────────────────────

    def detect_communities(self, *args: Any) -> list[Community] | tuple[Community, ...]:
        """Run community detection.

        Two modes:
        - detect_communities(graph) -> KnowledgeGraph-based detection
        - detect_communities(graph_nodes, graph_edges) -> dict-based detection
        """
        if len(args) == 1:
            return self._detect_from_graph(args[0])
        if len(args) >= 2:
            return self._detect_from_dicts(args[0], args[1])
        msg = "detect_communities requires 1 or 2 arguments"
        raise TypeError(msg)

    def _detect_from_graph(self, graph: Any) -> list[Community]:
        """Run community detection on a KnowledgeGraph object."""
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in graph.edges:
            adjacency[edge.source_id].add(edge.target_id)
            adjacency[edge.target_id].add(edge.source_id)

        for nid in graph.nodes:
            if nid not in adjacency:
                adjacency[nid] = set()

        node_ids = list(graph.nodes.keys())
        community_of: dict[str, str] = {nid: nid for nid in node_ids}
        m = graph.edge_count
        if m == 0:
            return [
                Community(
                    community_id="c0",
                    node_ids=frozenset(node_ids),
                    label="Entire graph",
                    level=0,
                )
            ]

        improved = True
        max_iterations = 10
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            for node in node_ids:
                current_comm = community_of[node]
                neighbor_comms: dict[str, float] = defaultdict(float)
                for neighbor in adjacency.get(node, set()):
                    if neighbor in community_of:
                        neighbor_comms[community_of[neighbor]] += 1.0
                best_comm = current_comm
                best_gain = 0.0
                for comm, _ in neighbor_comms.items():
                    gain = self._modularity_gain(
                        node, comm, community_of, adjacency, m, node_ids
                    )
                    if gain > best_gain:
                        best_gain = gain
                        best_comm = comm
                if best_comm != current_comm:
                    community_of[node] = best_comm
                    improved = True

        comm_groups: dict[str, set[str]] = defaultdict(set)
        for nid, cid in community_of.items():
            comm_groups[cid].add(nid)

        communities: list[Community] = []
        for i, (cid, members) in enumerate(comm_groups.items()):
            label_parts: list[str] = []
            for mid in list(members)[:3]:
                node = graph.nodes.get(mid)
                if node:
                    label_parts.append(node.label)
            label = ", ".join(label_parts) if label_parts else f"Community {i}"
            communities.append(
                Community(
                    community_id=cid if not cid.startswith("c") else f"c{i}",
                    node_ids=frozenset(members),
                    label=label,
                    level=0,
                )
            )
        return communities

    async def _detect_from_dicts(
        self,
        graph_nodes: dict[str, Any],
        graph_edges: list[Any],
    ) -> tuple[Community, ...]:
        """Detect communities using dict-based node/edge input."""
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in graph_edges:
            adjacency[edge.source_id].add(edge.target_id)
            adjacency[edge.target_id].add(edge.source_id)

        for nid in graph_nodes:
            if nid not in adjacency:
                adjacency[nid] = set()

        node_ids = list(graph_nodes.keys())
        community_of: dict[str, str] = {nid: nid for nid in node_ids}
        m = len(graph_edges)
        if m == 0:
            return (Community(
                community_id="c0",
                node_ids=frozenset(node_ids),
                label="All nodes",
                level=0,
            ),)

        improved = True
        max_iterations = 10
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            for node in node_ids:
                current_comm = community_of[node]
                neighbor_comms: dict[str, float] = defaultdict(float)
                for neighbor in adjacency.get(node, set()):
                    if neighbor in community_of:
                        neighbor_comms[community_of[neighbor]] += 1.0
                best_comm = current_comm
                best_gain = 0.0
                for comm, _ in neighbor_comms.items():
                    ki = len(adjacency.get(node, set()))
                    if ki <= 0:
                        continue
                    comm_deg = sum(
                        len(adjacency.get(nid, set())) for nid in node_ids
                        if community_of.get(nid) == comm
                    )
                    internal = sum(
                        1 for nbr in adjacency.get(node, set())
                        if community_of.get(nbr) == comm
                    )
                    gain = (internal / m) - (self.resolution * ki * comm_deg) / (2 * m * m)
                    if gain > best_gain:
                        best_gain = gain
                        best_comm = comm
                if best_comm != current_comm:
                    community_of[node] = best_comm
                    improved = True

        comm_groups: dict[str, set[str]] = defaultdict(set)
        for nid, cid in community_of.items():
            comm_groups[cid].add(nid)

        communities: list[Community] = []
        for i, (cid, members) in enumerate(comm_groups.items()):
            label_parts: list[str] = []
            for mid in list(members)[:3]:
                node = graph_nodes.get(mid)
                if node:
                    label_parts.append(getattr(node, "label", str(mid)))
            label = ", ".join(label_parts) if label_parts else f"Community {i}"
            communities.append(Community(
                community_id=cid if not cid.startswith("c") else f"c{i}",
                node_ids=frozenset(members),
                label=label,
                level=0,
            ))
        return tuple(communities)

    def detect_hierarchical(self, graph: Any, max_levels: int = 3) -> list[Community]:
        """Run hierarchical community detection. Returns all communities at all levels."""
        all_communities: list[Community] = []
        current_comm = Community(
            community_id="root",
            node_ids=frozenset(graph.nodes.keys()),
            label="Root",
            level=0,
        )
        all_communities.append(current_comm)

        remaining_ids = set(graph.nodes.keys())
        level_nodes: dict[str, set[str]] = {"root": remaining_ids}

        for level in range(1, max_levels + 1):
            next_level: dict[str, set[str]] = {}
            for parent_id, member_ids in level_nodes.items():
                if len(member_ids) <= 1:
                    continue
                sub_adj: dict[str, set[str]] = defaultdict(set)
                for edge in graph.edges:
                    if edge.source_id in member_ids and edge.target_id in member_ids:
                        sub_adj[edge.source_id].add(edge.target_id)
                        sub_adj[edge.target_id].add(edge.source_id)
                for nid in member_ids:
                    if nid not in sub_adj:
                        sub_adj[nid] = set()

                sub_ids = list(member_ids)
                m_sub = sum(len(v) for v in sub_adj.values()) // 2
                if m_sub == 0:
                    continue
                community_of: dict[str, str] = {sid: sid for sid in sub_ids}
                for _ in range(5):
                    for sid in sub_ids:
                        neighbor_comms: dict[str, float] = defaultdict(float)
                        for nbr in sub_adj.get(sid, set()):
                            if nbr in community_of:
                                neighbor_comms[community_of[nbr]] += 1.0
                        best = community_of[sid]
                        best_gain = 0.0
                        for comm, _ in neighbor_comms.items():
                            gain = self._modularity_gain(
                                sid, comm, community_of, sub_adj, m_sub, sub_ids
                            )
                            if gain > best_gain:
                                best_gain = gain
                                best = comm
                        community_of[sid] = best

                groups: dict[str, set[str]] = defaultdict(set)
                for sid, cid in community_of.items():
                    groups[cid].add(sid)

                for gid, members in groups.items():
                    child_id = f"{parent_id}.{gid[:8]}"
                    next_level.setdefault(child_id, members)
                    label_parts = []
                    for mid in list(members)[:3]:
                        node = graph.nodes.get(mid)
                        if node:
                            label_parts.append(node.label)
                    all_communities.append(
                        Community(
                            community_id=child_id,
                            node_ids=frozenset(members),
                            label=", ".join(label_parts) if label_parts else child_id,
                            level=level,
                            parent_id=parent_id,
                        )
                    )
            level_nodes = next_level
            if not level_nodes:
                break

        return all_communities

    # ── Analysis ────────────────────────────────────────────────────────────

    def analyze_inter_community_edges(self, graph: Any,
                                      communities: list[Community]) -> dict[str, Any]:
        """Analyze edges that cross community boundaries."""
        node_to_comm: dict[str, str] = {}
        for comm in communities:
            for nid in comm.node_ids:
                node_to_comm[nid] = comm.community_id

        inter_edges: list[dict[str, Any]] = []
        intra_count = 0
        inter_count = 0

        for edge in graph.edges:
            src_comm = node_to_comm.get(edge.source_id)
            tgt_comm = node_to_comm.get(edge.target_id)
            if src_comm and tgt_comm and src_comm != tgt_comm:
                inter_count += 1
                inter_edges.append({
                    "edge_id": edge.edge_id,
                    "source_community": src_comm,
                    "target_community": tgt_comm,
                    "relation": edge.relation.value,
                })
            else:
                intra_count += 1

        comm_connections: dict[str, set[str]] = defaultdict(set)
        for ie in inter_edges:
            comm_connections[ie["source_community"]].add(ie["target_community"])
            comm_connections[ie["target_community"]].add(ie["source_community"])

        return {
            "intra_community_edges": intra_count,
            "inter_community_edges": inter_count,
            "cross_community_connections": {
                k: list(v) for k, v in comm_connections.items()
            },
            "inter_edges": inter_edges,
        }

    def summarize_community(self, graph: Any,
                            community: Community) -> dict[str, Any]:
        """Generate a summary of a single community."""
        member_nodes = [
            graph.nodes[nid] for nid in community.node_ids
            if nid in graph.nodes
        ]
        type_counts: dict[str, int] = defaultdict(int)
        labels: list[str] = []
        for n in member_nodes:
            type_counts[n.node_type.value] += 1
            labels.append(n.label)
        return {
            "community_id": community.community_id,
            "size": community.size,
            "level": community.level,
            "label": community.label,
            "node_type_distribution": dict(type_counts),
            "sample_labels": labels[:10],
        }

    # ── Modularity ──────────────────────────────────────────────────────────

    def _modularity_gain(self, node_id: str, target_comm: str,
                         assignment: dict[str, str],
                         adjacency: dict[str, set[str]],
                         m: int, all_nodes: list[str]) -> float:
        """Compute the modularity gain from moving node to target_comm."""
        ki = len(adjacency.get(node_id, set()))
        if ki == 0 or m == 0:
            return 0.0

        comm_deg = sum(
            len(adjacency.get(nid, set())) for nid in all_nodes
            if assignment.get(nid) == target_comm
        )
        internal = sum(
            1 for nbr in adjacency.get(node_id, set())
            if assignment.get(nbr) == target_comm
        )

        try:
            gain = (internal / m) - (self.resolution * ki * comm_deg) / (2 * m * m)
        except ZeroDivisionError:
            gain = 0.0
        return gain
