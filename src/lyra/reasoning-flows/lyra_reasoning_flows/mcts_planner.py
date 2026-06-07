from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MCTSNode:
    state: str
    visits: int = 0
    value: float = 0.0
    children: tuple[MCTSNode, ...] = ()
    is_terminal: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: MCTSNode) -> MCTSNode:
        """Return a new node with *child* appended (immutable update)."""
        return MCTSNode(
            state=self.state,
            visits=self.visits,
            value=self.value,
            children=self.children + (child,),
            is_terminal=self.is_terminal,
            metadata=self.metadata,
        )

    def updated(self, visits: int | None = None, value: float | None = None) -> MCTSNode:
        return MCTSNode(
            state=self.state,
            visits=visits if visits is not None else self.visits,
            value=value if value is not None else self.value,
            children=self.children,
            is_terminal=self.is_terminal,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class MCTSConfig:
    max_iterations: int = 1000
    exploration_constant: float = math.sqrt(2)
    max_depth: int = 10
    time_limit_ms: float = 5000.0


def uct_score(node: MCTSNode, parent_visits: int, exploration_constant: float) -> float:
    if parent_visits == 0:
        return float("inf")
    if node.visits == 0:
        return float("inf")
    exploit = node.value / node.visits
    explore = exploration_constant * math.sqrt(math.log(parent_visits) / node.visits)
    return exploit + explore


def get_best_path(root: MCTSNode) -> list[MCTSNode]:
    path: list[MCTSNode] = [root]
    current = root
    while current.children:
        best = max(current.children, key=lambda c: c.visits if c.visits > 0 else -1)
        path.append(best)
        current = best
    return path


class MCTSPlanner:
    """MCTS-guided exploration implementing the SPIRAL pattern.

    Standard four-phase loop: selection (UCB1), expansion, simulation (rollout),
    backpropagation.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng_seed = seed

    def search(self, initial_state: str, config: MCTSConfig | None = None) -> MCTSNode:
        cfg = config or MCTSConfig()
        root = MCTSNode(state=initial_state)
        import time

        start = time.time()

        for _i in range(cfg.max_iterations):
            elapsed = (time.time() - start) * 1000
            if elapsed >= cfg.time_limit_ms:
                break

            # 1. SELECT: find path from root to a leaf node.
            path = self._select_path(root, cfg.exploration_constant)
            leaf = path[-1]

            # 2. EXPAND: create children on the leaf (returns new node).
            expanded_leaf = self._expand(leaf)

            # 3. SIMULATE: run a rollout from the (possibly expanded) leaf.
            result = self._simulate(expanded_leaf, depth=0, max_depth=cfg.max_depth)

            # 4. BACKPROPAGATE: rebuild the tree from leaf up to root.
            root = self._backpropagate_path(
                root, path[:-1], leaf, expanded_leaf, result
            )

        return root

    def _select_path(
        self, root: MCTSNode, exploration_constant: float
    ) -> list[MCTSNode]:
        """Return the path from *root* to a leaf node, inclusive."""
        path = [root]
        current = root
        while current.children:
            best = max(
                current.children,
                key=lambda c: uct_score(c, current.visits, exploration_constant),
                default=None,
            )
            if best is None:
                break
            path.append(best)
            current = best
        return path

    def _expand(self, node: MCTSNode) -> MCTSNode:
        """Return a new node with child states added."""
        if node.children:
            return node
        expansions = _expand_states(node.state)
        children = tuple(MCTSNode(state=s) for s in expansions)
        return MCTSNode(
            state=node.state,
            visits=node.visits,
            value=node.value,
            children=children,
            is_terminal=node.is_terminal,
            metadata=node.metadata,
        )

    def _simulate(self, node: MCTSNode, depth: int, max_depth: int) -> float:
        if depth >= max_depth or node.is_terminal:
            return 0.5
        return _rollout_value(node.state, self._rng_seed, depth)

    def _backpropagate_path(
        self,
        root: MCTSNode,
        path_to_parent: list[MCTSNode],
        old_leaf: MCTSNode,
        new_leaf: MCTSNode,
        result: float,
    ) -> MCTSNode:
        """Rebuild the tree, replacing *old_leaf* with *new_leaf* and
        backpropagating *result* as reward up to *root*."""

        def _rebuild_from(
            node: MCTSNode, target_state: str, replacement: MCTSNode, res: float
        ) -> MCTSNode:
            """If *node* has the target state among its children, replace it;
            otherwise recurse into children."""
            updated_children: list[MCTSNode] = []
            found = False
            for child in node.children:
                if child.state == target_state:
                    found = True
                    updated_children.append(
                        replacement.updated(
                            visits=replacement.visits + 1,
                            value=replacement.value + res,
                        )
                    )
                else:
                    # Recurse in case the target is deeper
                    rebuilt = _rebuild_from(child, target_state, replacement, res)
                    updated_children.append(rebuilt)
            if found:
                return MCTSNode(
                    state=node.state,
                    visits=node.visits + 1,
                    value=node.value + res,
                    children=tuple(updated_children),
                    is_terminal=node.is_terminal,
                    metadata=node.metadata,
                )
            # If this node _is_ the target, swap it.
            if node.state == target_state:
                return replacement.updated(
                    visits=replacement.visits + 1,
                    value=replacement.value + res,
                )
            # No match found in this subtree -- just update stats.
            return node.updated(
                visits=node.visits + 1,
                value=node.value + res,
            )

        if not path_to_parent:
            # Leaf is root itself.
            return new_leaf.updated(
                visits=new_leaf.visits + 1,
                value=new_leaf.value + result,
            )

        return _rebuild_from(root, old_leaf.state, new_leaf, result)

    def to_mermaid(self, root: MCTSNode) -> str:
        lines: list[str] = ["%% MCTS Tree", "graph TD"]
        node_id = 0
        stack: list[tuple[MCTSNode, int]] = [(root, 0)]
        visited: set[str] = set()

        while stack:
            node, parent_id = stack.pop()
            nid = f"N{node_id}"
            node_id += 1
            label = node.state[:40]
            val_str = f"{node.value:.2f}" if node.visits > 0 else "0.0"
            lines.append(f"    {nid}[{label}\\nV:{val_str} | N:{node.visits}]")
            if parent_id != 0 or node is root:
                lines.append(f"    N{parent_id} --> {nid}")

            if node.state in visited:
                continue
            visited.add(node.state)
            for child in node.children:
                stack.append((child, node_id - 1))

        return "\n".join(lines)

    def get_best_path(self, root: MCTSNode) -> list[MCTSNode]:
        return get_best_path(root)


def _expand_states(state: str) -> list[str]:
    """Generate child states from a state string.

    Produces a default set of successor states for the MCTS expansion phase.
    """
    # For deterministic expansion: produce 2-4 child states based on state input.
    base = state[:20] if len(state) > 20 else state
    return [
        f"{base}_step_1",
        f"{base}_step_2",
        f"{base}_step_3",
        f"{base}_step_4",
    ]


def _rollout_value(state: str, seed: int, depth: int) -> float:
    """Heuristic rollout value based on state characteristics."""
    # Deterministic heuristic using state content and depth.
    hash_val = abs(hash(f"{state}_{seed}_{depth}"))
    return 0.3 + (hash_val % 70) / 100.0  # range [0.3, 1.0]
