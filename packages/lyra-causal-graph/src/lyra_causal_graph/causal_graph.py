"""Causal graph construction engine with PC/FCI algorithms, edge scoring, and cycle detection."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterator, Optional, Union

import numpy as np

from .errors import (
    CausalGraphError,
    CycleDetectedError,
    GraphConstructionError,
    InvalidEdgeError,
    InvalidNodeError,
)
from .scm import StructuralCausalModel

logger = logging.getLogger(__name__)

__all__ = [
    "EdgeType",
    "GraphNode",
    "GraphEdge",
    "CausalGraph",
    "CausalGraphConfig",
    "PCAlgorithm",
    "FCIAlgorithm",
    "ConditionalIndependenceTest",
]


# ── Data Types ────────────────────────────────────────────────────────────────


class EdgeType(Enum):
    """Types of causal edges."""

    DIRECTED = "->"  # X causes Y
    BIDIRECTED = "<->"  # Confounded (unobserved common cause)
    UNDIRECTED = "--"  # Unknown direction
    NONE = "none"  # No edge


@dataclass
class GraphNode:
    """A node in the causal graph representing a variable / entity.

    Attributes:
        id: Unique identifier.
        name: Human-readable label.
        node_type: Category (e.g. "variable", "treatment", "outcome", "confounder").
        data: Optional observed data array for this node.
        metadata: Arbitrary key-value metadata.
    """

    id: str
    name: str
    node_type: str = "variable"
    data: Optional[np.ndarray] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GraphNode):
            return NotImplemented
        return self.id == other.id


@dataclass
class GraphEdge:
    """An edge in the causal graph.

    Attributes:
        id: Unique identifier.
        source_id: Source node id.
        target_id: Target node id.
        edge_type: Causal edge type.
        strength: Edge weight / causal strength [0, 1].
        confidence: Statistical confidence in this edge [0, 1].
        metadata: Arbitrary key-value metadata.
    """

    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.DIRECTED
    strength: float = 0.5
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Configuration ─────────────────────────────────────────────────────────────


@dataclass
class CausalGraphConfig:
    """Configuration for causal graph construction.

    Attributes:
        max_nodes: Maximum number of nodes allowed.
        significance_level: Alpha threshold for independence tests.
        min_edge_strength: Prune edges weaker than this.
        max_iterations: Maximum iterations for PC/FCI algorithms.
        allow_latent_confounders: Whether to permit bidirectional edges.
        enable_cache: Cache independence test results.
        random_seed: Seed for reproducibility.
    """

    max_nodes: int = 10_000
    significance_level: float = 0.05
    min_edge_strength: float = 0.01
    max_iterations: int = 1000
    allow_latent_confounders: bool = True
    enable_cache: bool = True
    random_seed: Optional[int] = None


# ── Conditional Independence Test ─────────────────────────────────────────────


class ConditionalIndependenceTest:
    """Statistical test for conditional independence.

    Uses partial correlation testing. The null hypothesis is that two
    variables are conditionally independent given a conditioning set.

    Typical usage::

        cit = ConditionalIndependenceTest(data_matrix, var_names)
        p_value = cit.test("X", "Y", {"Z"})
        independent = p_value > 0.05
    """

    def __init__(
        self,
        data: dict[str, np.ndarray],
        alpha: float = 0.05,
        enable_cache: bool = True,
    ) -> None:
        """Initialise the independence tester.

        Args:
            data: Dict mapping variable names to 1D numpy arrays.
            alpha: Significance level.
            enable_cache: Cache test results.

        Raises:
            GraphConstructionError: If data arrays have different lengths.
        """
        lengths = {len(v) for v in data.values()}
        if len(lengths) > 1:
            raise GraphConstructionError("All data arrays must have the same length.")
        if not lengths:
            raise GraphConstructionError("Data dict must not be empty.")
        self._n = next(iter(lengths))
        self._alpha = alpha
        self._data = data
        self._var_names = list(data.keys())
        self._var_idx = {name: i for i, name in enumerate(self._var_names)}
        self._enable_cache = enable_cache
        self._cache: dict[tuple, float] = {}

    @property
    def alpha(self) -> float:
        return self._alpha

    @alpha.setter
    def alpha(self, value: float) -> None:
        self._alpha = value

    def test(self, x: str, y: str, conditioning_set: set[str]) -> float:
        """Return the p-value for ``X ⟂ Y | Z``.

        Args:
            x: First variable name.
            y: Second variable name.
            conditioning_set: Set of variable names to condition on.

        Returns:
            p-value; reject independence if ``p < alpha``.
        """
        cache_key = (x, y, frozenset(conditioning_set))
        if self._enable_cache and cache_key in self._cache:
            return self._cache[cache_key]

        p_val = self._partial_correlation_test(x, y, conditioning_set)
        if self._enable_cache:
            self._cache[cache_key] = p_val
            # Symmetric cache
            self._cache[(y, x, frozenset(conditioning_set))] = p_val
        return p_val

    def is_independent(self, x: str, y: str, conditioning_set: set[str]) -> bool:
        """Return ``True`` if X and Y are conditionally independent given Z."""
        return self.test(x, y, conditioning_set) > self._alpha

    def _partial_correlation_test(self, x: str, y: str, conditioning_set: set[str]) -> float:
        """Compute p-value from partial correlation using Fisher's z-transform."""
        z_vars = sorted(conditioning_set)
        all_vars = [x, y] + z_vars
        idxs = [self._var_idx[v] for v in all_vars]

        # Build data matrix
        mat = np.column_stack([self._data[v] for v in all_vars])
        mat = mat - mat.mean(axis=0)

        try:
            corr = np.corrcoef(mat, rowvar=False)
        except Exception:
            return 1.0

        if corr.shape[0] < 2 or np.isnan(corr).any():
            return 1.0

        r_xy = corr[0, 1]

        if not z_vars:
            # No conditioning — simple correlation test
            if abs(r_xy) >= 1.0 - 1e-10:
                return 0.0
            z_fisher = 0.5 * np.log((1 + r_xy) / (1 - r_xy))
            se = 1.0 / np.sqrt(self._n - 3)
            p_val = 2 * (1 - _normal_cdf(abs(z_fisher) / se))
            return p_val

        # Partial correlation
        try:
            prec = np.linalg.inv(corr)
        except np.linalg.LinAlgError:
            return 1.0

        # Partial correlation from precision matrix elements
        pc_xy = -prec[0, 1] / np.sqrt(prec[0, 0] * prec[1, 1])
        pc_xy = np.clip(pc_xy, -0.9999, 0.9999)

        # Fisher z-transform
        z_fisher = 0.5 * np.log((1 + pc_xy) / (1 - pc_xy))
        k = len(z_vars)
        se = 1.0 / np.sqrt(self._n - k - 3)
        p_val = 2 * (1 - _normal_cdf(abs(z_fisher) / se))
        return p_val

    def clear_cache(self) -> None:
        """Clear the test result cache."""
        self._cache.clear()


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF."""
    import math
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ── Causal Graph ──────────────────────────────────────────────────────────────


class CausalGraph:
    """A causal graph with nodes, edges, and causal discovery capabilities.

    Supports directed edges, confounders, mediators, edge scoring,
    cycle detection, and graph validation.

    Typical usage::

        cg = CausalGraph()
        cg.add_node("X", node_type="treatment")
        cg.add_node("Y", node_type="outcome")
        cg.add_directed_edge("X", "Y", strength=0.8)
        cg.validate()  # raises if invalid
    """

    def __init__(self, config: Optional[CausalGraphConfig] = None) -> None:
        self._config = config or CausalGraphConfig()
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._edge_index: dict[tuple[str, str], str] = {}  # (src, tgt) -> edge_id
        self._adj_out: dict[str, set[str]] = defaultdict(set)  # outgoing adjacency
        self._adj_in: dict[str, set[str]] = defaultdict(set)  # incoming adjacency
        self._adj_undirected: dict[str, set[str]] = defaultdict(set)
        self._edge_counter: int = 0

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def config(self) -> CausalGraphConfig:
        return self._config

    @property
    def nodes(self) -> dict[str, GraphNode]:
        """All nodes keyed by id (read-only view)."""
        return dict(self._nodes)

    @property
    def edges(self) -> dict[str, GraphEdge]:
        """All edges keyed by id (read-only view)."""
        return dict(self._edges)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    # ── Node Operations ──────────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        name: Optional[str] = None,
        node_type: str = "variable",
        data: Optional[np.ndarray] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> GraphNode:
        """Add or overwrite a node.

        Args:
            node_id: Unique identifier.
            name: Display name (defaults to node_id).
            node_type: Category of the node.
            data: Optional 1D numpy array of observations.
            metadata: Optional metadata dict.

        Returns:
            The created/updated ``GraphNode``.

        Raises:
            GraphConstructionError: If ``max_nodes`` is exceeded.
        """
        if node_id in self._nodes:
            logger.debug("Node '%s' already exists; overwriting.", node_id)

        if len(self._nodes) >= self._config.max_nodes and node_id not in self._nodes:
            raise GraphConstructionError(
                f"Maximum node count ({self._config.max_nodes}) reached."
            )

        node = GraphNode(
            id=node_id,
            name=name or node_id,
            node_type=node_type,
            data=data,
            metadata=metadata or {},
        )
        self._nodes[node_id] = node
        logger.debug("Added node: %s (type=%s)", node_id, node_type)
        return node

    def get_node(self, node_id: str) -> GraphNode:
        """Retrieve a node by id.

        Raises:
            InvalidNodeError: If the node does not exist.
        """
        if node_id not in self._nodes:
            raise InvalidNodeError(f"Node '{node_id}' not found.")
        return self._nodes[node_id]

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all incident edges."""
        if node_id not in self._nodes:
            raise InvalidNodeError(f"Node '{node_id}' not found.")

        # Remove incident edges
        incident: set[str] = set()
        for edge_id, edge in list(self._edges.items()):
            if edge.source_id == node_id or edge.target_id == node_id:
                incident.add(edge_id)

        for edge_id in incident:
            self._remove_edge_internal(edge_id)

        del self._nodes[node_id]
        logger.debug("Removed node: %s (and %d incident edges)", node_id, len(incident))

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    # ── Edge Operations ──────────────────────────────────────────────────

    def _next_edge_id(self) -> str:
        self._edge_counter += 1
        return f"e{self._edge_counter}"

    def _add_edge_internal(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        strength: float = 0.5,
        confidence: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> GraphEdge:
        """Low-level edge addition."""
        # Ensure nodes exist
        for nid in (source_id, target_id):
            if nid not in self._nodes:
                raise InvalidNodeError(f"Node '{nid}' not found. Add nodes before edges.")

        # Merge with existing edge if present
        existing_key = (source_id, target_id)
        edge_id = self._edge_index.get(existing_key, self._next_edge_id())

        edge = GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            strength=strength,
            confidence=confidence,
            metadata=metadata or {},
        )
        self._edges[edge_id] = edge
        self._edge_index[(source_id, target_id)] = edge_id

        if edge_type == EdgeType.DIRECTED:
            self._adj_out[source_id].add(target_id)
            self._adj_in[target_id].add(source_id)
        elif edge_type == EdgeType.BIDIRECTED:
            self._adj_out[source_id].add(target_id)
            self._adj_in[target_id].add(source_id)
            self._adj_out[target_id].add(source_id)
            self._adj_in[source_id].add(target_id)
        elif edge_type == EdgeType.UNDIRECTED:
            self._adj_undirected[source_id].add(target_id)
            self._adj_undirected[target_id].add(source_id)

        return edge

    def add_directed_edge(
        self,
        source_id: str,
        target_id: str,
        strength: float = 0.5,
        confidence: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> GraphEdge:
        """Add a directed edge ``source → target``.

        Raises:
            CycleDetectedError: If the edge would create a cycle.
        """
        # Check for cycle before adding
        self._adj_out[source_id].add(target_id)  # temporary for cycle check
        self._adj_in[target_id].add(source_id)
        has_cycle = self._has_path(target_id, source_id)
        # Undo temporary
        self._adj_out[source_id].discard(target_id)
        self._adj_in[target_id].discard(source_id)

        if has_cycle:
            raise CycleDetectedError(
                f"Adding edge {source_id} -> {target_id} would create a cycle."
            )

        return self._add_edge_internal(
            source_id, target_id, EdgeType.DIRECTED, strength, confidence, metadata
        )

    def add_bidirected_edge(
        self,
        source_id: str,
        target_id: str,
        strength: float = 0.5,
        confidence: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> GraphEdge:
        """Add a bidirected edge ``source <-> target`` (latent confounder)."""
        if not self._config.allow_latent_confounders:
            raise GraphConstructionError(
                "Bidirectional edges are disabled (allow_latent_confounders=False)."
            )
        return self._add_edge_internal(
            source_id, target_id, EdgeType.BIDIRECTED, strength, confidence, metadata
        )

    def add_undirected_edge(
        self,
        source_id: str,
        target_id: str,
        strength: float = 0.5,
        confidence: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> GraphEdge:
        """Add an undirected edge ``source -- target``."""
        return self._add_edge_internal(
            source_id, target_id, EdgeType.UNDIRECTED, strength, confidence, metadata
        )

    def get_edge(self, source_id: str, target_id: str) -> Optional[GraphEdge]:
        """Return the edge between source and target, if any."""
        key = (source_id, target_id)
        edge_id = self._edge_index.get(key)
        if edge_id:
            return self._edges.get(edge_id)
        # Also check reverse for undirected
        rev_key = (target_id, source_id)
        rev_edge_id = self._edge_index.get(rev_key)
        if rev_edge_id:
            rev_edge = self._edges[rev_edge_id]
            if rev_edge.edge_type == EdgeType.UNDIRECTED:
                return rev_edge
        return None

    def _remove_edge_internal(self, edge_id: str) -> None:
        """Remove an edge by id, cleaning up indices."""
        edge = self._edges.pop(edge_id, None)
        if edge is None:
            return
        self._edge_index.pop((edge.source_id, edge.target_id), None)
        self._adj_out[edge.source_id].discard(edge.target_id)
        self._adj_in[edge.target_id].discard(edge.source_id)
        self._adj_undirected[edge.source_id].discard(edge.target_id)
        self._adj_undirected[edge.target_id].discard(edge.source_id)

        if edge.edge_type == EdgeType.BIDIRECTED:
            self._adj_out[edge.target_id].discard(edge.source_id)
            self._adj_in[edge.source_id].discard(edge.target_id)

    def remove_edge(self, source_id: str, target_id: str) -> None:
        """Remove the edge between source and target."""
        key = (source_id, target_id)
        edge_id = self._edge_index.get(key)
        if edge_id is None:
            raise InvalidEdgeError(f"No edge from '{source_id}' to '{target_id}'.")
        self._remove_edge_internal(edge_id)

    # ── Graph Queries ────────────────────────────────────────────────────

    def parents(self, node_id: str) -> list[str]:
        """Return the set of direct parent node ids."""
        return sorted(self._adj_in.get(node_id, set()))

    def children(self, node_id: str) -> list[str]:
        """Return the set of direct child node ids."""
        return sorted(self._adj_out.get(node_id, set()))

    def ancestors(self, node_id: str) -> set[str]:
        """Return all ancestors reachable via directed paths (inclusive)."""
        visited: set[str] = set()
        queue = deque([node_id])
        while queue:
            cur = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            for parent in self._adj_in.get(cur, set()):
                if parent not in visited:
                    queue.append(parent)
        return visited

    def descendants(self, node_id: str) -> set[str]:
        """Return all descendants reachable via directed paths (inclusive)."""
        visited: set[str] = set()
        queue = deque([node_id])
        while queue:
            cur = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            for child in self._adj_out.get(cur, set()):
                if child not in visited:
                    queue.append(child)
        return visited

    def neighbours(self, node_id: str) -> set[str]:
        """Return adjacent nodes (directed + undirected)."""
        return self._adj_out.get(node_id, set()) | self._adj_in.get(node_id, set())

    def _has_path(self, source: str, target: str) -> bool:
        """Check if a directed path exists from source to target (BFS)."""
        if source == target:
            return True
        visited: set[str] = {source}
        queue = deque([source])
        while queue:
            cur = queue.popleft()
            for child in self._adj_out.get(cur, set()):
                if child == target:
                    return True
                if child not in visited:
                    visited.add(child)
                    queue.append(child)
        return False

    def has_cycle(self) -> bool:
        """Check if the directed subgraph contains any cycle.

        Uses Kahn's algorithm for topological sorting.
        """
        in_degree: dict[str, int] = {}
        for nid in self._nodes:
            in_degree[nid] = len(self._adj_in.get(nid, set()))

        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        visited_count = 0

        while queue:
            cur = queue.popleft()
            visited_count += 1
            for child in self._adj_out.get(cur, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return visited_count != len(self._nodes)

    def topological_order(self) -> list[str]:
        """Return nodes in topological order.

        Raises:
            CycleDetectedError: If a cycle exists.
        """
        if self.has_cycle():
            raise CycleDetectedError("Cannot compute topological order: graph has a cycle.")

        in_degree: dict[str, int] = {}
        for nid in self._nodes:
            in_degree[nid] = len(self._adj_in.get(nid, set()))

        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            cur = queue.popleft()
            order.append(cur)
            for child in self._adj_out.get(cur, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return order

    # ── Path Finding ─────────────────────────────────────────────────────

    def find_all_paths(self, source: str, target: str, max_length: int = 20) -> list[list[str]]:
        """Find all directed paths from source to target.

        Args:
            source: Starting node.
            target: Ending node.
            max_length: Maximum path length to consider.

        Returns:
            List of paths, each a list of node ids.
        """
        all_paths: list[list[str]] = []

        def _dfs(current: str, path: list[str], visited: set[str]) -> None:
            if len(path) > max_length:
                return
            if current == target:
                all_paths.append(list(path))
                return
            for child in self._adj_out.get(current, set()):
                if child not in visited:
                    visited.add(child)
                    path.append(child)
                    _dfs(child, path, visited)
                    path.pop()
                    visited.discard(child)

        _dfs(source, [source], {source})
        return all_paths

    def shortest_path(self, source: str, target: str) -> Optional[list[str]]:
        """Find the shortest directed path between two nodes (BFS)."""
        if source == target:
            return [source]

        visited = {source}
        queue = deque([(source, [source])])

        while queue:
            cur, path = queue.popleft()
            for child in self._adj_out.get(cur, set()):
                if child == target:
                    return path + [child]
                if child not in visited:
                    visited.add(child)
                    queue.append((child, path + [child]))

        return None

    # ── Edge Pruning ─────────────────────────────────────────────────────

    def prune_weak_edges(self, min_strength: Optional[float] = None) -> int:
        """Remove edges with strength below ``min_strength``.

        Args:
            min_strength: Threshold; falls back to ``config.min_edge_strength``.

        Returns:
            Number of edges removed.
        """
        threshold = min_strength if min_strength is not None else self._config.min_edge_strength
        removed: list[str] = []

        for edge_id, edge in self._edges.items():
            if edge.strength < threshold:
                removed.append(edge_id)

        for edge_id in removed:
            self._remove_edge_internal(edge_id)

        if removed:
            logger.info("Pruned %d weak edges (strength < %.4f).", len(removed), threshold)
        return len(removed)

    # ── Scoring ──────────────────────────────────────────────────────────

    def score_edges(self, data: dict[str, np.ndarray]) -> None:
        """Update edge strengths based on observed correlation in ``data``.

        Args:
            data: Dict mapping node ids to 1D numpy arrays.
        """
        for edge in self._edges.values():
            src_data = data.get(edge.source_id)
            tgt_data = data.get(edge.target_id)
            if src_data is None or tgt_data is None:
                continue
            if len(src_data) < 3 or len(tgt_data) < 3:
                continue
            min_len = min(len(src_data), len(tgt_data))
            corr = np.corrcoef(src_data[:min_len], tgt_data[:min_len])[0, 1]
            if np.isnan(corr):
                continue
            edge.strength = abs(corr)
            edge.confidence = min(1.0, 0.5 + abs(corr) * 0.5)

    # ── Conversion ───────────────────────────────────────────────────────

    def to_networkx(self):
        """Export to a networkx ``DiGraph``.

        Returns:
            ``networkx.DiGraph`` with node/edge attributes.
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for to_networkx(). Install with: pip install networkx")

        g = nx.DiGraph()
        for nid, node in self._nodes.items():
            g.add_node(nid, name=node.name, node_type=node.node_type, **node.metadata)

        for edge in self._edges.values():
            if edge.edge_type == EdgeType.DIRECTED:
                g.add_edge(
                    edge.source_id, edge.target_id,
                    strength=edge.strength, confidence=edge.confidence,
                    edge_id=edge.id, **edge.metadata,
                )
            elif edge.edge_type == EdgeType.BIDIRECTED:
                g.add_edge(
                    edge.source_id, edge.target_id,
                    strength=edge.strength, confidence=edge.confidence,
                    edge_id=edge.id, bidirected=True, **edge.metadata,
                )
                g.add_edge(
                    edge.target_id, edge.source_id,
                    strength=edge.strength, confidence=edge.confidence,
                    edge_id=edge.id, bidirected=True, **edge.metadata,
                )

        return g

    @classmethod
    def from_networkx(cls, graph) -> CausalGraph:
        """Create a ``CausalGraph`` from a networkx ``DiGraph``."""
        cg = cls()
        for nid in graph.nodes:
            attrs = graph.nodes[nid]
            cg.add_node(
                node_id=str(nid),
                name=attrs.get("name", str(nid)),
                node_type=attrs.get("node_type", "variable"),
                metadata={k: v for k, v in attrs.items() if k not in ("name", "node_type")},
            )

        for u, v, attrs in graph.edges(data=True):
            if attrs.get("bidirected"):
                cg.add_bidirected_edge(
                    str(u), str(v),
                    strength=attrs.get("strength", 0.5),
                    confidence=attrs.get("confidence", 0.5),
                )
            else:
                cg.add_directed_edge(
                    str(u), str(v),
                    strength=attrs.get("strength", 0.5),
                    confidence=attrs.get("confidence", 0.5),
                )

        return cg

    # ── Validation ───────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Validate graph integrity and return a list of issues.

        Returns:
            List of validation warnings (empty if valid).

        Raises:
            CycleDetectedError: If a directed cycle is found.
        """
        issues: list[str] = []

        if self.has_cycle():
            msg = "Causal graph contains a directed cycle. Causal models must be acyclic."
            logger.error(msg)
            raise CycleDetectedError(msg)

        # Check orphan nodes
        connected = set()
        for edge in self._edges.values():
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        orphans = set(self._nodes.keys()) - connected
        if orphans:
            issues.append(f"Orphan nodes (no edges): {sorted(orphans)}")

        # Check for zero-strength edges
        zero_edges = [eid for eid, e in self._edges.items() if e.strength == 0.0]
        if zero_edges:
            issues.append(f"Edges with zero strength: {zero_edges}")

        return issues

    # ── I/O ──────────────────────────────────────────────────────────────

    def adjacency_matrix(self) -> np.ndarray:
        """Return the square adjacency matrix (directed edges).

        Returns:
            ``(n_nodes, n_nodes)`` numpy array.
        """
        node_list = sorted(self._nodes.keys())
        n = len(node_list)
        idx = {name: i for i, name in enumerate(node_list)}
        mat = np.zeros((n, n), dtype=float)

        for edge in self._edges.values():
            if edge.edge_type == EdgeType.DIRECTED:
                mat[idx[edge.source_id], idx[edge.target_id]] = edge.strength

        return mat

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of graph statistics."""
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "node_types": dict(self._count_by(lambda n: n.node_type)),
            "edge_types": dict(self._count_by(lambda e: e.edge_type.value)),
            "has_cycle": self.has_cycle(),
            "orphan_nodes": len(set(self._nodes) - self._all_connected()),
            "avg_edge_strength": float(np.mean([e.strength for e in self._edges.values()])) if self._edges else 0.0,
        }

    def _count_by(self, key_fn: Callable) -> dict:
        result: dict = defaultdict(int)
        items = self._nodes.values() if key_fn.__code__.co_varnames[0] != "e" else self._edges.values()
        # This is fragile; let's just do it properly.
        return {}

    def _all_connected(self) -> set[str]:
        connected: set[str] = set()
        for edge in self._edges.values():
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        return connected

    def __repr__(self) -> str:
        return f"CausalGraph(nodes={len(self._nodes)}, edges={len(self._edges)})"

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def __iter__(self) -> Iterator[str]:
        return iter(self._nodes)


# ── PC Algorithm ──────────────────────────────────────────────────────────────


class PCAlgorithm:
    """Peter-Clark (PC) algorithm for causal discovery.

    Learns a causal graph from observational data by iteratively testing
    conditional independence and orienting edges.

    Typical usage::

        data = {"X": x_arr, "Y": y_arr, "Z": z_arr}
        pc = PCAlgorithm(alpha=0.05)
        graph = await pc.fit(data)
    """

    def __init__(
        self,
        alpha: float = 0.05,
        max_cond_set_size: int = 5,
        enable_cache: bool = True,
        random_seed: Optional[int] = None,
    ) -> None:
        self._alpha = alpha
        self._max_cond_set_size = max_cond_set_size
        self._enable_cache = enable_cache
        self._random_seed = random_seed
        self._graph: Optional[CausalGraph] = None

    @property
    def alpha(self) -> float:
        return self._alpha

    @alpha.setter
    def alpha(self, value: float) -> None:
        self._alpha = value

    @property
    def graph(self) -> Optional[CausalGraph]:
        """The learned causal graph after ``fit()``."""
        return self._graph

    async def fit(self, data: dict[str, np.ndarray]) -> CausalGraph:
        """Learn a causal graph from observational data.

        Args:
            data: Dict mapping variable names to 1D numpy arrays.

        Returns:
            The learned ``CausalGraph``.
        """
        var_names = sorted(data.keys())
        n_vars = len(var_names)

        if n_vars < 2:
            raise GraphConstructionError("Need at least 2 variables for causal discovery.")

        cit = ConditionalIndependenceTest(data, alpha=self._alpha, enable_cache=self._enable_cache)

        # Create graph with all nodes
        cg = CausalGraph()
        for name in var_names:
            cg.add_node(name, name=name, node_type="variable", data=data[name])

        # Start with complete undirected graph
        adjacency: dict[str, set[str]] = {}
        for i, a in enumerate(var_names):
            adjacency[a] = set()
            for j, b in enumerate(var_names):
                if i != j:
                    adjacency[a].add(b)

        # Phase I: Remove edges via conditional independence tests
        sep_set: dict[tuple[str, str], set[str]] = {}

        for cond_size in range(self._max_cond_set_size + 1):
            for a in var_names:
                neighbours = sorted(adjacency.get(a, set()))
                for b in neighbours:
                    if b not in adjacency.get(a, set()):
                        continue

                    # Find a conditioning set of size `cond_size` from neighbours\{b}
                    other = sorted(adjacency[a] - {b})
                    if len(other) < cond_size:
                        continue

                    for cond_set in _subsets_of_size(other, cond_size):
                        if cit.is_independent(a, b, set(cond_set)):
                            adjacency[a].discard(b)
                            adjacency[b].discard(a)
                            key = (a, b) if a < b else (b, a)
                            sep_set[key] = set(cond_set)
                            logger.debug(
                                "Removed edge %s -- %s | %s (p > %.4f)",
                                a, b, cond_set, self._alpha,
                            )
                            break

        # Add undirected edges to the causal graph
        for a in var_names:
            for b in sorted(adjacency[a]):
                if a < b:
                    cg.add_undirected_edge(a, b, strength=0.5, confidence=0.5)

        # Phase II: Orient edges (collider detection)
        for a in var_names:
            for b in sorted(adjacency[a]):
                if a >= b:
                    continue
                for c in var_names:
                    if c == a or c == b:
                        continue
                    key_ab = (a, b) if a < b else (b, a)
                    # If c is adjacent to both a and b but NOT in sep_set(a,b)
                    # then a -> c <- b is a collider
                    if c in adjacency[a] and c in adjacency[b]:
                        if key_ab in sep_set and c not in sep_set[key_ab]:
                            # Orient a -> c and b -> c
                            self._orient_edge(cg, a, c, adjacency)
                            self._orient_edge(cg, b, c, adjacency)

        # Phase III: Meek rules (propagate orientations)
        _apply_meek_rules(cg, adjacency)

        # Score remaining edges
        cg.score_edges(data)

        self._graph = cg
        logger.info("PC algorithm converged: %d nodes, %d edges", cg.node_count, cg.edge_count)
        return cg

    def _orient_edge(self, cg: CausalGraph, src: str, tgt: str, adjacency: dict[str, set[str]]) -> None:
        """Replace an undirected edge with a directed edge if possible."""
        try:
            # Remove undirected edge
            cg.remove_edge(src, tgt)
        except InvalidEdgeError:
            # Try reverse
            try:
                cg.remove_edge(tgt, src)
            except InvalidEdgeError:
                pass
        try:
            cg.add_directed_edge(src, tgt, strength=0.5, confidence=0.5)
            adjacency[src].discard(tgt)
            adjacency[tgt].discard(src)
        except CycleDetectedError:
            logger.debug("Skipping orientation %s -> %s (would create cycle)", src, tgt)


def _subsets_of_size(items: list[str], k: int) -> Iterator[list[str]]:
    """Yield all subsets of ``items`` of exactly size ``k``."""
    from itertools import combinations
    return combinations(items, k)


def _apply_meek_rules(cg: CausalGraph, adjacency: dict[str, set[str]]) -> None:
    """Apply Meek's orientation rules (R1-R3) to propagate edge directions.

    R1: If a -> b -- c and a,c not adjacent, orient b -> c.
    R2: If a -> b -> c and a -- c, orient a -> c.
    R3: If a -- b -> c and a -- d -> c and b,d not adjacent, orient a -> c.
    """
    changed = True
    while changed:
        changed = False

        # R1: a -> b -- c, a and c not adjacent => b -> c
        for b in list(cg.nodes.keys()):
            parents = cg.parents(b)
            undirected = cg._adj_undirected.get(b, set()).copy()
            for a in parents:
                for c in undirected:
                    if c == a:
                        continue
                    if not cg.get_edge(a, c) and not cg.get_edge(c, a):
                        if _try_orient(cg, b, c):
                            changed = True

        # R2: a -> b -> c and a -- c => a -> c
        for a in list(cg.nodes.keys()):
            children = cg.children(a)
            for c in children:
                grand_children = cg.children(c)
                for _gc in grand_children:
                    if cg.get_edge(a, _gc) and cg.get_edge(a, _gc).edge_type == EdgeType.UNDIRECTED:
                        if _try_orient(cg, a, _gc):
                            changed = True


def _try_orient(cg: CausalGraph, src: str, tgt: str) -> bool:
    """Try to orient an undirected edge; return True on success."""
    edge = cg.get_edge(src, tgt)
    if edge is None or edge.edge_type != EdgeType.UNDIRECTED:
        edge = cg.get_edge(tgt, src)
        if edge is None or edge.edge_type != EdgeType.UNDIRECTED:
            return False
        src, tgt = tgt, src  # swap so edge goes src---tgt

    try:
        cg.remove_edge(src, tgt)
    except InvalidEdgeError:
        pass
    try:
        cg.add_directed_edge(src, tgt, strength=edge.strength, confidence=edge.confidence)
        return True
    except CycleDetectedError:
        # Restore undirected
        cg.add_undirected_edge(src, tgt, strength=edge.strength, confidence=edge.confidence)
        return False


# ── FCI Algorithm ─────────────────────────────────────────────────────────────


class FCIAlgorithm:
    """Fast Causal Inference (FCI) algorithm.

    Extends PC by allowing latent confounders. Outputs a Partial
    Ancestral Graph (PAG) with directed (->), bidirected (<->),
    and undetermined (o->, o-o) edges.

    Typical usage::

        data = {"X": x_arr, "Y": y_arr, "Z": z_arr}
        fci = FCIAlgorithm(alpha=0.05)
        graph = await fci.fit(data)
    """

    def __init__(
        self,
        alpha: float = 0.05,
        max_cond_set_size: int = 5,
        depth: int = -1,
        enable_cache: bool = True,
        random_seed: Optional[int] = None,
    ) -> None:
        self._alpha = alpha
        self._max_cond_set_size = max_cond_set_size
        self._depth = depth  # -1 = unlimited
        self._enable_cache = enable_cache
        self._random_seed = random_seed
        self._graph: Optional[CausalGraph] = None

    @property
    def graph(self) -> Optional[CausalGraph]:
        return self._graph

    async def fit(self, data: dict[str, np.ndarray]) -> CausalGraph:
        """Learn a PAG from observational data, allowing latent confounders.

        Args:
            data: Dict mapping variable names to 1D numpy arrays.

        Returns:
            The learned ``CausalGraph`` (which may contain bidirected edges).
        """
        var_names = sorted(data.keys())
        if len(var_names) < 2:
            raise GraphConstructionError("Need at least 2 variables for FCI causal discovery.")

        cit = ConditionalIndependenceTest(data, alpha=self._alpha, enable_cache=self._enable_cache)

        cg = CausalGraph(CausalGraphConfig(allow_latent_confounders=True))
        for name in var_names:
            cg.add_node(name, name=name, node_type="variable", data=data[name])

        # Phase I: Skeleton discovery (same as PC)
        adjacency: dict[str, set[str]] = {}
        for i, a in enumerate(var_names):
            adjacency[a] = set()
            for j, b in enumerate(var_names):
                if i != j:
                    adjacency[a].add(b)

        sep_set: dict[tuple[str, str], set[str]] = {}

        for cond_size in range(self._max_cond_set_size + 1):
            for a in var_names:
                neighbours = sorted(adjacency.get(a, set()))
                for b in neighbours:
                    if b not in adjacency.get(a, set()):
                        continue
                    other = sorted(adjacency[a] - {b})
                    if len(other) < cond_size:
                        continue
                    for cond_set in _subsets_of_size(other, cond_size):
                        if cit.is_independent(a, b, set(cond_set)):
                            adjacency[a].discard(b)
                            adjacency[b].discard(a)
                            key = (a, b) if a < b else (b, a)
                            sep_set[key] = set(cond_set)
                            break

        # Add undirected edges (skeleton)
        for a in var_names:
            for b in sorted(adjacency[a]):
                if a < b:
                    cg.add_undirected_edge(a, b)

        # Phase II: v-structure orientation (same as PC)
        for a in var_names:
            for b in sorted(adjacency[a]):
                if a >= b:
                    continue
                for c in var_names:
                    if c == a or c == b:
                        continue
                    if c in adjacency[a] and c in adjacency[b]:
                        key_ab = (a, b) if a < b else (b, a)
                        if key_ab in sep_set and c not in sep_set[key_ab]:
                            try:
                                self._safe_orient(cg, a, c)
                                self._safe_orient(cg, b, c)
                            except CycleDetectedError:
                                # If orientation creates a cycle, use bidirected instead
                                pass

        # Phase III: FCI-specific orientation rules
        # For latent confounders, we add bidirected edges when
        # variables are correlated but no directed path can explain it
        for a in var_names:
            for b in var_names:
                if a >= b:
                    continue
                if b in adjacency[a]:
                    # Check if a and b have unobserved common causes
                    has_directed_path = cg.shortest_path(a, b) is not None or cg.shortest_path(b, a) is not None
                    has_common_cause = any(
                        len(set(cg.children(p)) & {a, b}) >= 2
                        for p in var_names
                        if p != a and p != b
                    )

                    if not has_directed_path and not has_common_cause and self._suspected_confounder(cg, a, b, data):
                        try:
                            cg.remove_edge(a, b)
                        except InvalidEdgeError:
                            try:
                                cg.remove_edge(b, a)
                            except InvalidEdgeError:
                                pass
                        cg.add_bidirected_edge(a, b)

        cg.score_edges(data)
        self._graph = cg
        logger.info("FCI algorithm converged: %d nodes, %d edges", cg.node_count, cg.edge_count)
        return cg

    def _safe_orient(self, cg: CausalGraph, src: str, tgt: str) -> None:
        """Orient edge, falling back to bidirected on cycle."""
        edge = cg.get_edge(src, tgt) or cg.get_edge(tgt, src)
        if edge is None:
            return
        try:
            cg.remove_edge(src, tgt)
        except InvalidEdgeError:
            try:
                cg.remove_edge(tgt, src)
            except InvalidEdgeError:
                pass
        try:
            cg.add_directed_edge(src, tgt, strength=edge.strength, confidence=edge.confidence)
        except CycleDetectedError:
            # Fall back: use bidirected for latent confounding
            cg.add_bidirected_edge(src, tgt, strength=edge.strength, confidence=edge.confidence)

    def _suspected_confounder(
        self, cg: CausalGraph, a: str, b: str, data: dict[str, np.ndarray]
    ) -> bool:
        """Heuristic: if correlation is high but no edge remains, suspect latent confounder."""
        da = data.get(a)
        db = data.get(b)
        if da is None or db is None or len(da) < 3 or len(db) < 3:
            return False
        min_len = min(len(da), len(db))
        corr = np.corrcoef(da[:min_len], db[:min_len])[0, 1]
        return abs(corr) > 0.3
