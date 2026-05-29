"""Graph Memory Tier — Knowledge graph, MMR reranking, ACT-R decay, auto-dreamer, federation."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeGraphNode:
    id: str
    label: str
    node_type: str  # entity, concept, action, outcome
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: np.ndarray | None = None


@dataclass
class KnowledgeGraphEdge:
    source_id: str
    target_id: str
    relation: str  # causes, uses, depends_on, similar_to, part_of
    weight: float = 1.0


class KnowledgeGraph:
    """Entity-relation graph connecting memories."""

    def __init__(self):
        self.nodes: dict[str, KnowledgeGraphNode] = {}
        self.edges: dict[str, list[KnowledgeGraphEdge]] = defaultdict(list)
        self.reverse_edges: dict[str, list[KnowledgeGraphEdge]] = defaultdict(list)

    def add_node(self, node: KnowledgeGraphNode) -> str:
        self.nodes[node.id] = node
        return node.id

    def add_edge(self, edge: KnowledgeGraphEdge) -> None:
        self.edges[edge.source_id].append(edge)
        self.reverse_edges[edge.target_id].append(edge)

    def get_neighbors(
        self, node_id: str, relation: str | None = None
    ) -> list[tuple[str, str, float]]:
        neighbors = []
        for edge in self.edges.get(node_id, []):
            if relation is None or edge.relation == relation:
                neighbors.append((edge.target_id, edge.relation, edge.weight))
        for edge in self.reverse_edges.get(node_id, []):
            if relation is None or edge.relation == relation:
                neighbors.append((edge.source_id, f"reverse_{edge.relation}", edge.weight))
        return neighbors

    def query(self, query_type: str, min_weight: float = 0.5) -> list[KnowledgeGraphNode]:
        results = []
        for node in self.nodes.values():
            if node.node_type == query_type:
                total_weight = sum(e.weight for e in self.edges.get(node.id, [])) + sum(
                    e.weight for e in self.reverse_edges.get(node.id, [])
                )
                if total_weight >= min_weight:
                    results.append(node)
        return results

    @property
    def stats(self) -> dict[str, int]:
        return {"nodes": len(self.nodes), "edges": sum(len(e) for e in self.edges.values())}


class MMRReranker:
    """Maximum Marginal Relevance diversity reranking to prevent redundant retrievals."""

    def __init__(self, lambda_param: float = 0.5):
        self.lambda_param = lambda_param
        self._served: list[str] = []

    def reset(self):
        self._served = []

    def rerank(
        self, items: list[tuple[str, float, np.ndarray]], top_k: int = 5
    ) -> list[tuple[str, float]]:
        selected = []
        candidates = list(range(len(items)))
        while len(selected) < min(top_k, len(items)):
            best = -1
            best_score = -float("inf")
            for i in candidates:
                relevance = items[i][1]
                if self._served:
                    max_sim = (
                        max(
                            np.dot(items[i][2], items[j][2])
                            / max(np.linalg.norm(items[i][2]) * np.linalg.norm(items[j][2]), 1e-10)
                            for j in selected
                            if len(items[j]) > 2
                            and items[j][2] is not None
                            and items[i][2] is not None
                        )
                        if len(items[i]) > 2 and items[i][2] is not None
                        else 0.0
                    )
                else:
                    max_sim = 0.0
                mmr = self.lambda_param * relevance - (1.0 - self.lambda_param) * max_sim
                if mmr > best_score:
                    best_score = mmr
                    best = i
            if best >= 0:
                selected.append(best)
                self._served.append(items[best][0])
                candidates.remove(best)
            else:
                break
        return [(items[i][0], items[i][1]) for i in selected]


class ACTRMemoryModel:
    """ACT-R cognitive architecture activation/decay model — memories fade unless reinforced."""

    def __init__(self, decay_rate: float = 0.5, retrieval_threshold: float = 0.1):
        self.decay_rate = decay_rate
        self.retrieval_threshold = retrieval_threshold
        self.memories: dict[str, float] = {}  # memory_id -> base_activation

    def encode(self, memory_id: str, initial_activation: float = 1.0) -> None:
        self.memories[memory_id] = initial_activation

    def retrieve(self, memory_id: str) -> float | None:
        activation = self.memories.get(memory_id)
        if activation is None:
            return None
        if activation < self.retrieval_threshold:
            return None  # memory too weak to retrieve
        return activation

    def reinforce(self, memory_id: str, boost: float = 0.3) -> None:
        if memory_id in self.memories:
            self.memories[memory_id] += boost

    def decay_all(self, time_delta_hours: float = 1.0) -> dict[str, float]:
        decayed = {}
        for mem_id, activation in self.memories.items():
            new_activation = activation - self.decay_rate * time_delta_hours
            self.memories[mem_id] = max(0.0, new_activation)
            if self.memories[mem_id] < activation:
                decayed[mem_id] = activation - self.memories[mem_id]
        return decayed


class AutoDreamer:
    """Offline memory consolidation — reorganizes memories during idle cycles."""

    def __init__(self):
        self.consolidation_cycles: int = 0

    async def consolidate(self, graph: KnowledgeGraph, actr: ACTRMemoryModel) -> dict[str, Any]:
        self.consolidation_cycles += 1
        consolidated = 0
        for node_id in list(graph.nodes.keys()):
            actr.reinforce(node_id, boost=0.1)
            consolidated += 1
        return {
            "cycle": self.consolidation_cycles,
            "memories_consolidated": consolidated,
        }


class FederatedRetriever:
    """Queries peer agent memories via gossip protocol."""

    def __init__(self):
        self.peers: dict[str, list[str]] = defaultdict(list)  # peer_id -> memory_ids

    def register_peer(self, peer_id: str, memory_ids: list[str]) -> None:
        self.peers[peer_id] = memory_ids

    async def query_peer(self, peer_id: str, query: str, top_k: int = 3) -> list[str]:
        memories = self.peers.get(peer_id, [])
        scored = [(mem, 0.5) for mem in memories[:top_k]]
        return [mem for mem, _ in scored]


class GraphMemoryStore:
    """Combined graph-backed memory tier with ACT-R, MMR, and federation."""

    def __init__(self):
        self.graph = KnowledgeGraph()
        self.mmr = MMRReranker()
        self.actr = ACTRMemoryModel()
        self.dreamer = AutoDreamer()
        self.federation = FederatedRetriever()

    async def store(
        self, node: KnowledgeGraphNode, edges: list[KnowledgeGraphEdge] | None = None
    ) -> str:
        nid = self.graph.add_node(node)
        self.actr.encode(nid)
        if edges:
            for edge in edges:
                self.graph.add_edge(edge)
        return nid

    async def retrieve(self, query_type: str, top_k: int = 5) -> list[KnowledgeGraphNode]:
        nodes = self.graph.query(query_type)
        scored = []
        for n in nodes:
            activation = self.actr.retrieve(n.id) or 0.0
            scored.append((n.id, activation, n))
            self.actr.reinforce(n.id)

        scored.sort(key=lambda x: x[1], reverse=True)
        return [n for _, _, n in scored[:top_k]]
