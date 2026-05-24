"""Plan-on-Graph (PoG) — adaptive backtracking on graph walks.

Chen et al. 2024 (NeurIPS, arXiv:2410.23875). Three mechanisms:

    Guidance — decompose the query into sub-objectives that drive each step.
    Memory — track the visited subgraph + per-node status (pending / explored /
             pruned) + the path-of-paths.
    Reflection — when a path looks wrong, backtrack, prune, restart with an
                 alternative sub-objective.

Per [docs/200-graph-grounded-multi-hop-retrieval.md](../../../../../../research/harness-engineering/docs/200-graph-grounded-multi-hop-retrieval.md)
§"Plan-on-Graph", PoG fixes the fragility of fixed-breadth KG search by
letting the walker choose adaptive breadth and *backtrack* when wrong. This
implementation uses a Protocol-typed ``PathScorer`` so production wires an LLM
judge while tests use deterministic stubs.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol

from .types import Graph, Node


class NodeStatus(str, enum.Enum):
    PENDING = "pending"
    EXPLORED = "explored"
    PRUNED = "pruned"


@dataclass
class PathScore:
    """The judge's verdict on whether a partial path is on-track."""

    score: float  # 0.0 (clearly wrong) .. 1.0 (clearly right)
    reason: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")


class PathScorer(Protocol):
    """Protocol: judges a partial path against the query.

    Production wires an LLM-as-judge; tests use deterministic stubs.
    """

    name: str

    def score(self, *, query: str, path: tuple[str, ...], graph: Graph) -> PathScore: ...


@dataclass
class _NodeRecord:
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    last_score: Optional[float] = None
    visit_count: int = 0


@dataclass(frozen=True)
class WalkPath:
    """A single completed (or terminated) path through the graph."""

    nodes: tuple[str, ...]
    final_score: float
    completed: bool  # True if the walk reached a high-confidence terminal
    reason: str = ""


@dataclass
class WalkResult:
    """The full PoG walk trace + the best path found."""

    query: str
    paths: tuple[WalkPath, ...]
    best_path: Optional[WalkPath]
    visited: dict[str, _NodeRecord] = field(default_factory=dict)
    n_score_calls: int = 0
    n_backtracks: int = 0


@dataclass
class PlanOnGraphWalker:
    """PoG walker with backtracking + pruning.

    Maintains a frontier of candidate next steps; at each step, the
    :class:`PathScorer` rates the extension; below ``backtrack_threshold``
    the candidate is pruned and the walker tries an alternative.
    """

    graph: Graph
    scorer: PathScorer
    max_depth: int = 4
    branching: int = 3  # max neighbours to try per node
    accept_threshold: float = 0.8  # walk completes once a path scores >= this
    backtrack_threshold: float = 0.3  # below this, prune the path
    max_score_calls: int = 64  # global budget cap

    def walk(self, *, query: str, seeds: Iterable[str]) -> WalkResult:
        seed_list = [s for s in seeds if s in self.graph]
        if not seed_list:
            return WalkResult(query=query, paths=(), best_path=None)

        # Build adjacency once (symmetric, like HippoRAG).
        adj: dict[str, list[str]] = {n.id: [] for n in self.graph.all_nodes()}
        for edge in self.graph.all_edges():
            if edge.src in adj and edge.dst in adj:
                adj[edge.src].append(edge.dst)
                adj[edge.dst].append(edge.src)

        visited: dict[str, _NodeRecord] = {}
        paths: list[WalkPath] = []
        best_path: Optional[WalkPath] = None
        n_score_calls = 0
        n_backtracks = 0

        # Stack of (path, depth). DFS with prune-driven backtracking.
        stack: list[tuple[tuple[str, ...], int]] = [((seed,), 0) for seed in seed_list]

        while stack and n_score_calls < self.max_score_calls:
            path, depth = stack.pop()
            current = path[-1]

            rec = visited.setdefault(current, _NodeRecord(node_id=current))
            rec.visit_count += 1

            if n_score_calls >= self.max_score_calls:
                break

            scored = self.scorer.score(query=query, path=path, graph=self.graph)
            n_score_calls += 1
            rec.last_score = scored.score

            if scored.score < self.backtrack_threshold:
                rec.status = NodeStatus.PRUNED
                paths.append(
                    WalkPath(
                        nodes=path,
                        final_score=scored.score,
                        completed=False,
                        reason=f"pruned: {scored.reason}",
                    )
                )
                n_backtracks += 1
                continue

            if scored.score >= self.accept_threshold or depth >= self.max_depth:
                rec.status = NodeStatus.EXPLORED
                completed_flag = scored.score >= self.accept_threshold
                walk_path = WalkPath(
                    nodes=path,
                    final_score=scored.score,
                    completed=completed_flag,
                    reason=scored.reason,
                )
                paths.append(walk_path)
                if best_path is None or walk_path.final_score > best_path.final_score:
                    best_path = walk_path
                if completed_flag:
                    # Don't stop — continue to find better, but cap by score budget.
                    pass
                continue

            # Expand neighbours; deterministic order for replay.
            rec.status = NodeStatus.EXPLORED
            neighbours = sorted(set(adj.get(current, [])))
            on_path = set(path)
            extensions = [n for n in neighbours if n not in on_path][: self.branching]
            # Push extensions onto the stack.
            for nb in extensions:
                stack.append((path + (nb,), depth + 1))

        return WalkResult(
            query=query,
            paths=tuple(paths),
            best_path=best_path,
            visited=visited,
            n_score_calls=n_score_calls,
            n_backtracks=n_backtracks,
        )


# --- Deterministic stub scorer for tests ----------------------------------


@dataclass
class TargetNodeScorer:
    """Stub scorer that rewards paths reaching ``target_node_id``.

    Score is 1.0 when the last node matches the target, decaying linearly
    with distance otherwise. Used for tests + as a baseline against which
    LLM scorers are compared.
    """

    target_node_id: str
    name: str = "target-node-scorer"

    def score(self, *, query: str, path: tuple[str, ...], graph: Graph) -> PathScore:
        if not path:
            return PathScore(score=0.0, reason="empty path")
        last = path[-1]
        if last == self.target_node_id:
            return PathScore(score=1.0, reason=f"reached target {self.target_node_id}")
        # Reward proximity by path length (longer = closer-to-target if not yet there).
        decay = max(0.0, 1.0 - 0.2 * (len(path) - 1))
        # If target on path-to-here, give partial credit.
        if self.target_node_id in path:
            return PathScore(score=0.85, reason="target on path")
        return PathScore(score=decay * 0.5, reason=f"distance heuristic {decay}")


__all__ = [
    "NodeStatus",
    "PathScore",
    "PathScorer",
    "PlanOnGraphWalker",
    "TargetNodeScorer",
    "WalkPath",
    "WalkResult",
]
