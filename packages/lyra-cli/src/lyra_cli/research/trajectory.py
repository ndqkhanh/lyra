"""
Research trajectory tracking.

Records action-result pairs during multi-hop exploration, maintains an
exploration tree, and computes coverage metrics. Supports replay and
analysis of past research sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ResearchAction:
    """A single research action in the exploration tree."""

    action_id: str
    action_type: str  # "search", "extract", "analyze", "synthesize"
    query: str
    strategy: str  # "breadth_first", "depth_first", "best_first"
    depth: int
    parent_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class ResearchResult:
    """The outcome produced by a research action."""

    result_id: str
    action_id: str
    findings: Tuple[str, ...] = field(default_factory=tuple)
    sources: Tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 1.0
    source_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TrajectoryNode:
    """A node in the exploration tree, linking action + result."""

    action: ResearchAction
    result: Optional[ResearchResult] = None
    children: List[TrajectoryNode] = field(default_factory=list)
    parent: Optional[TrajectoryNode] = None


class ResearchTrajectory:
    """
    Tracks the full exploration tree of a multi-hop research session.

    Each node in the tree represents an action-result pair.  The root
    node corresponds to the initial research query.

    Features:
    - Action-result pair recording
    - Tree-based exploration path tracking
    - Coverage metrics (depth, breadth, source diversity)
    - Serialisable session replay
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, TrajectoryNode] = {}
        self._root_id: Optional[str] = None

    # ---- mutation -------------------------------------------------------

    def add_action(self, action: ResearchAction) -> str:
        """Register a new action and return its ID."""
        node = TrajectoryNode(action=action)
        self._nodes[action.action_id] = node

        if action.parent_id is not None:
            parent = self._nodes.get(action.parent_id)
            if parent is not None:
                node.parent = parent
                parent.children.append(node)

        if self._root_id is None:
            self._root_id = action.action_id

        return action.action_id

    def add_result(self, result: ResearchResult) -> str:
        """Attach a result to its parent action."""
        node = self._nodes.get(result.action_id)
        if node is None:
            raise KeyError(
                f"No action found for result {result.result_id}: "
                f"action {result.action_id} does not exist"
            )
        node.result = result
        return result.result_id

    # ---- query ----------------------------------------------------------

    def get_node(self, action_id: str) -> Optional[TrajectoryNode]:
        """Retrieve a node by action ID."""
        return self._nodes.get(action_id)

    def get_root(self) -> Optional[ResearchAction]:
        """Return the root action, if any."""
        root_node = self._nodes.get(self._root_id) if self._root_id else None
        return root_node.action if root_node else None

    def get_action_count(self) -> int:
        """Return the total number of actions recorded."""
        return len(self._nodes)

    def get_path_to(self, action_id: str) -> List[ResearchAction]:
        """Return the ordered path from root to the given action."""
        node = self._nodes.get(action_id)
        if node is None:
            raise KeyError(f"Action {action_id} not found")

        path: List[ResearchAction] = []
        current: Optional[TrajectoryNode] = node
        while current is not None:
            path.append(current.action)
            current = current.parent
        path.reverse()
        return path

    def get_leaf_nodes(self) -> List[TrajectoryNode]:
        """Return all leaf nodes (actions with no children)."""
        return [
            node for node in self._nodes.values()
            if not node.children
        ]

    def get_all_findings(self) -> List[str]:
        """Collect all unique findings across every result."""
        seen: set = set()
        findings: List[str] = []
        for node in self._nodes.values():
            if node.result is not None:
                for finding in node.result.findings:
                    if finding not in seen:
                        seen.add(finding)
                        findings.append(finding)
        return findings

    # ---- metrics --------------------------------------------------------

    def get_coverage_metrics(self) -> dict:
        """Compute coverage and exploration metrics."""
        if not self._nodes:
            return {
                "total_actions": 0,
                "total_results": 0,
                "max_depth": 0,
                "average_depth": 0.0,
                "leaf_count": 0,
                "unique_sources": 0,
                "unique_findings": 0,
                "breadth_per_depth": {},
            }

        nodes = list(self._nodes.values())
        results_with_data = [n for n in nodes if n.result is not None]

        # Depth stats
        depths = [self._depth_of(n) for n in nodes]
        max_depth = max(depths) if depths else 0
        avg_depth = sum(depths) / len(depths) if depths else 0.0

        # Source diversity
        all_sources: set = set()
        for node in results_with_data:
            if node.result is not None:
                all_sources.update(node.result.sources)

        # Breadth per depth level
        breadth: Dict[int, int] = {}
        for node in nodes:
            d = self._depth_of(node)
            breadth[d] = breadth.get(d, 0) + 1

        return {
            "total_actions": len(nodes),
            "total_results": len(results_with_data),
            "max_depth": max_depth,
            "average_depth": round(avg_depth, 2),
            "leaf_count": len(self.get_leaf_nodes()),
            "unique_sources": len(all_sources),
            "unique_findings": len(self.get_all_findings()),
            "breadth_per_depth": dict(sorted(breadth.items())),
        }

    # ---- serialisation --------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the trajectory to a plain dict."""
        actions = []
        results = []
        for node in self._nodes.values():
            actions.append({
                "action_id": node.action.action_id,
                "action_type": node.action.action_type,
                "query": node.action.query,
                "strategy": node.action.strategy,
                "depth": node.action.depth,
                "parent_id": node.action.parent_id,
                "timestamp": node.action.timestamp,
            })
            if node.result is not None:
                results.append({
                    "result_id": node.result.result_id,
                    "action_id": node.result.action_id,
                    "findings": list(node.result.findings),
                    "sources": list(node.result.sources),
                    "confidence": node.result.confidence,
                    "source_count": node.result.source_count,
                    "timestamp": node.result.timestamp,
                })

        return {
            "root_id": self._root_id,
            "actions": actions,
            "results": results,
        }

    def from_dict(self, data: dict) -> None:
        """Restore trajectory state from a dict (destructive)."""
        self._nodes.clear()
        self._root_id = None

        for a in data.get("actions", []):
            self.add_action(ResearchAction(**a))

        for r in data.get("results", []):
            self.add_result(ResearchResult(**r))

        self._root_id = data.get("root_id")

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _depth_of(node: TrajectoryNode) -> int:
        """Compute the depth of a node in the tree."""
        depth = 0
        current = node.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth
