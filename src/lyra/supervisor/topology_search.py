"""
MCTS-driven topology search for optimal agent communication graphs.

Discovers the most efficient communication topology for a set of agent
roles working on a task, balancing completion quality against cost and
latency.

Pre-built templates::

    STAR  (supervisor-centric)   — one central coordinator, N workers
    MESH  (debate)               — every agent talks to every other agent
    TREE  (research)             — hierarchical decomposition
    HYBRID                       — mixed: star for management, mesh within teams

Usage::

    searcher = TopologySearcher()
    topo = searcher.search_optimal_topology(task="Write unit tests", pool=agent_pool)
    print(topo.graph)  # adjacency list
    print(topo.reward)  # estimated reward
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Topology templates
# ---------------------------------------------------------------------------

TopologyTemplate = Enum(
    "TopologyTemplate",
    [("STAR", "star"), ("MESH", "mesh"), ("TREE", "tree"), ("HYBRID", "hybrid")],
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TopologyNode:
    """A node (agent role) in a communication topology.

    Attributes:
        role: The agent's role label (e.g. "researcher", "critic").
        parent: The role of the parent node, or None for root.
        children: List of child role labels.
        communication_weight: Relative communication intensity (0.0-1.0).
            Higher means more messages flow through this edge.
    """

    role: str
    parent: str | None
    children: tuple[str, ...] = ()
    communication_weight: float = 1.0


@dataclass(frozen=True)
class Topology:
    """A complete agent communication topology.

    Attributes:
        nodes: Mapping of role -> TopologyNode.
        template: The template this topology is derived from.
        edges: Adjacency list as (from_role, to_role) tuples.
        reward: Estimated reward for this topology (higher is better).
        quality_score: Estimated task completion quality (0.0-1.0).
        cost_estimate: Estimated cumulative cost.
        latency_estimate: Estimated end-to-end latency.
    """

    nodes: dict[str, TopologyNode]
    template: TopologyTemplate
    edges: tuple[tuple[str, str], ...] = ()
    reward: float = 0.0
    quality_score: float = 0.0
    cost_estimate: float = 0.0
    latency_estimate: float = 0.0


@dataclass(frozen=True)
class AgentRole:
    """Description of an agent role available in the pool.

    Attributes:
        role: Unique role identifier.
        capabilities: List of capability tags.
        cost_per_step: Relative cost per interaction step.
        latency_factor: Relative latency factor (0.0-1.0).
        max_instances: Maximum number of agents with this role.
    """

    role: str
    capabilities: tuple[str, ...] = ()
    cost_per_step: float = 1.0
    latency_factor: float = 0.5
    max_instances: int = 1


@dataclass(frozen=True)
class MCTSConfig:
    """Configuration for the MCTS topology search.

    Attributes:
        iterations: Number of MCTS rollouts to run.
        exploration_constant: UCB1 exploration parameter (higher = more explore).
        max_depth: Maximum depth of the search tree.
        simulation_budget: Maximum nodes to simulate per rollout.
    """

    iterations: int = 100
    exploration_constant: float = 1.414
    max_depth: int = 5
    simulation_budget: int = 50


# ---------------------------------------------------------------------------
# TopologySearcher
# ---------------------------------------------------------------------------


class TopologySearcher:
    """MCTS-driven searcher for optimal agent communication topologies.

    Uses Monte Carlo Tree Search to explore the space of possible topologies,
    evaluating each candidate by the reward function::

        reward = task_completion_quality / (cost + latency)

    The search balances exploration of novel topologies against exploitation
    of known-good structures.
    """

    def __init__(
        self,
        config: MCTSConfig | None = None,
        reward_fn: Callable[[Topology], float] | None = None,
    ) -> None:
        """
        Args:
            config: MCTS configuration. Uses defaults if not provided.
            reward_fn: Custom reward function. Defaults to the built-in
                ``quality / (cost + latency)`` formula.
        """
        self._config = config or MCTSConfig()
        self._reward_fn = reward_fn or self._default_reward

        # MCTS state
        self._visit_counts: dict[str, int] = {}
        self._total_rewards: dict[str, float] = {}
        self._children_cache: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_optimal_topology(
        self,
        task: str,
        pool: list[AgentRole],
    ) -> Topology:
        """Search for the optimal communication topology for a task.

        Args:
            task: A description of the task to be performed.
            pool: Available agent roles that can be assigned.

        Returns:
            The best Topology found during the search.
        """
        # Seed with pre-built templates
        candidates = [
            self._build_template(template, pool)
            for template in TopologyTemplate
        ]

        # Evaluate seed candidates
        evaluated_candidates: list[Topology] = []
        for topo in candidates:
            ev = self._evaluate(topo, task)
            evaluated_candidates.append(ev)
            state_key = self._topology_key(ev)
            self._visit_counts[state_key] = 1
            self._total_rewards[state_key] = ev.reward

        candidates = evaluated_candidates
        best = max(candidates, key=lambda t: t.reward)
        logger.info(
            "topology_search_started",
            task=task[:80],
            pool_size=len(pool),
            seed_templates=[t.template.value for t in candidates],
            best_seed_reward=best.reward,
        )

        # MCTS iterations
        for iteration in range(self._config.iterations):
            node = self._select(best)
            reward = self._simulate(node, task, pool)
            self._backpropagate(node, reward)

            # Track best
            current_best = self._best_known(candidates)
            if current_best.reward > best.reward:
                best = current_best
                logger.debug(
                    "topology_improved",
                    iteration=iteration,
                    reward=best.reward,
                    template=best.template.value,
                )

        logger.info(
            "topology_search_complete",
            iterations=self._config.iterations,
            best_template=best.template.value,
            best_reward=round(best.reward, 4),
            best_quality=round(best.quality_score, 4),
            best_cost=round(best.cost_estimate, 4),
        )

        return best

    def build_template(
        self,
        template: TopologyTemplate,
        pool: list[AgentRole],
    ) -> Topology:
        """Build a topology from a named template without search.

        Args:
            template: The template identifier.
            pool: Available agent roles.

        Returns:
            A Topology based on the template.
        """
        topo = self._build_template(template, pool)
        # Evaluate with a generic task string for baseline scoring
        return self._evaluate(topo, "generic task")

    # ------------------------------------------------------------------
    # Template builders
    # ------------------------------------------------------------------

    def _build_template(
        self,
        template: TopologyTemplate,
        pool: list[AgentRole],
    ) -> Topology:
        """Build a topology from a template and agent pool."""
        if template == TopologyTemplate.STAR:
            return self._build_star(pool)
        if template == TopologyTemplate.MESH:
            return self._build_mesh(pool)
        if template == TopologyTemplate.TREE:
            return self._build_tree(pool)
        if template == TopologyTemplate.HYBRID:
            return self._build_hybrid(pool)
        return self._build_star(pool)

    def _build_star(self, pool: list[AgentRole]) -> Topology:
        """Build a star topology: one supervisor, N workers."""
        if not pool:
            return self._empty_topology(TopologyTemplate.STAR)

        # Pick the most capable role as supervisor
        supervisor_role = max(pool, key=lambda r: len(r.capabilities))
        supervisor = TopologyNode(
            role=supervisor_role.role,
            parent=None,
            children=tuple(r.role for r in pool if r.role != supervisor_role.role),
            communication_weight=1.0,
        )

        nodes: dict[str, TopologyNode] = {supervisor.role: supervisor}
        edges: list[tuple[str, str]] = []

        for role in pool:
            if role.role == supervisor_role.role:
                continue
            node = TopologyNode(
                role=role.role,
                parent=supervisor_role.role,
                communication_weight=0.5,
            )
            nodes[role.role] = node
            edges.append((supervisor_role.role, role.role))

        return Topology(
            nodes=nodes,
            template=TopologyTemplate.STAR,
            edges=tuple(edges),
        )

    def _build_mesh(self, pool: list[AgentRole]) -> Topology:
        """Build a mesh topology: every agent talks to every other agent."""
        if not pool:
            return self._empty_topology(TopologyTemplate.MESH)

        nodes: dict[str, TopologyNode] = {}
        edges: list[tuple[str, str]] = []

        for i, role in enumerate(pool):
            children = tuple(
                r.role for j, r in enumerate(pool)
                if j != i
            )
            node = TopologyNode(
                role=role.role,
                parent=None,  # no single parent in mesh
                children=children,
                communication_weight=1.0,
            )
            nodes[role.role] = node
            for j, r in enumerate(pool):
                if j != i:
                    edges.append((role.role, r.role))

        return Topology(
            nodes=nodes,
            template=TopologyTemplate.MESH,
            edges=tuple(edges),
        )

    def _build_tree(self, pool: list[AgentRole]) -> Topology:
        """Build a tree topology: hierarchical decomposition.

        Roles are arranged into levels based on capability breadth.
        The broadest role becomes the root; narrower roles become leaves.
        """
        if not pool:
            return self._empty_topology(TopologyTemplate.TREE)

        sorted_pool = sorted(
            pool,
            key=lambda r: len(r.capabilities),
            reverse=True,
        )

        root_role = sorted_pool[0]
        remaining = sorted_pool[1:]

        # Divide remaining into levels (binary-ish tree)
        nodes: dict[str, TopologyNode] = {}
        edges: list[tuple[str, str]] = []

        # Root
        mid = len(remaining)
        root = TopologyNode(
            role=root_role.role,
            parent=None,
            children=tuple(r.role for r in remaining[:max(1, mid // 2)]),
            communication_weight=1.0,
        )
        nodes[root_role.role] = root

        current_parents = [root_role.role]
        level_remaining = remaining[:]

        while level_remaining:
            next_parents: list[str] = []
            for parent_role in current_parents:
                if not level_remaining:
                    break
                # Assign up to 2 children per parent
                children_count = min(2, len(level_remaining))
                for _ in range(children_count):
                    child = level_remaining.pop(0)
                    node = TopologyNode(
                        role=child.role,
                        parent=parent_role,
                        communication_weight=0.7,
                    )
                    nodes[child.role] = node
                    edges.append((parent_role, child.role))
                    next_parents.append(child.role)

                # Update parent's children
                parent_node = nodes[parent_role]
                nodes[parent_role] = TopologyNode(
                    role=parent_node.role,
                    parent=parent_node.parent,
                    children=tuple(
                        c for c in parent_node.children
                        if c in nodes or c == parent_role
                    ),
                    communication_weight=parent_node.communication_weight,
                )

            current_parents = next_parents

        return Topology(
            nodes=nodes,
            template=TopologyTemplate.TREE,
            edges=tuple(edges),
        )

    def _build_hybrid(self, pool: list[AgentRole]) -> Topology:
        """Build a hybrid topology: star for management, mesh within teams.

        Splits pool into 2+ teams, each internally meshed, with a single
        root coordinator connecting them in a star pattern.
        """
        if not pool:
            return self._empty_topology(TopologyTemplate.HYBRID)
        if len(pool) < 4:
            # Fall back to star
            return self._build_star(pool)

        # Pick root coordinator (most capable)
        root_role = max(pool, key=lambda r: len(r.capabilities))
        others = [r for r in pool if r.role != root_role.role]

        # Split remaining into two teams
        mid = len(others) // 2
        team_a = others[:mid]
        team_b = others[mid:]

        nodes: dict[str, TopologyNode] = {}
        edges: list[tuple[str, str]] = []

        # Root coordinator
        root_node = TopologyNode(
            role=root_role.role,
            parent=None,
            children=tuple(r.role for r in others),
            communication_weight=1.0,
        )
        nodes[root_role.role] = root_node

        # Team A: mesh
        for role in team_a:
            children_a = tuple(
                r.role for r in team_a if r.role != role.role
            )
            node = TopologyNode(
                role=role.role,
                parent=root_role.role,
                children=children_a,
                communication_weight=0.8,
            )
            nodes[role.role] = node
            edges.append((root_role.role, role.role))
            for child in children_a:
                if (role.role, child) not in edges:
                    edges.append((role.role, child))

        # Team B: mesh
        for role in team_b:
            children_b = tuple(
                r.role for r in team_b if r.role != role.role
            )
            node = TopologyNode(
                role=role.role,
                parent=root_role.role,
                children=children_b,
                communication_weight=0.8,
            )
            nodes[role.role] = node
            edges.append((root_role.role, role.role))
            for child in children_b:
                if (role.role, child) not in edges:
                    edges.append((role.role, child))

        return Topology(
            nodes=nodes,
            template=TopologyTemplate.HYBRID,
            edges=tuple(edges),
        )

    # ------------------------------------------------------------------
    # MCTS internals
    # ------------------------------------------------------------------

    def _select(self, root: Topology) -> Topology:
        """MCTS Selection phase: traverse to the most promising child."""
        current = root
        depth = 0

        while depth < self._config.max_depth:
            children = self._get_children(current)
            if not children:
                break

            # UCB1 selection
            best_child: Topology | None = None
            best_ucb = -float("inf")

            for child in children:
                key = self._topology_key(child)
                visits = self._visit_counts.get(key, 0)
                if visits == 0:
                    # Unexplored: high UCB
                    child_ucb = float("inf")
                else:
                    parent_visits = self._visit_counts.get(
                        self._topology_key(current), 1
                    )
                    avg_reward = self._total_rewards.get(key, 0.0) / visits
                    explore = self._config.exploration_constant * math.sqrt(
                        math.log(parent_visits) / visits
                    )
                    child_ucb = avg_reward + explore

                if child_ucb > best_ucb:
                    best_ucb = child_ucb
                    best_child = child

            if best_child is None:
                break

            current = best_child
            depth += 1

        return current

    def _simulate(
        self,
        node: Topology,
        task: str,
        pool: list[AgentRole],
    ) -> float:
        """MCTS Simulation phase: estimate reward by expanding randomly."""
        # Perturb the topology to generate a new candidate
        perturbed = self._perturb_topology(node, pool)
        evaluated = self._evaluate(perturbed, task)
        return evaluated.reward

    def _backpropagate(self, leaf: Topology, reward: float) -> None:
        """MCTS Backpropagation phase: update visit counts and rewards."""
        key = self._topology_key(leaf)
        self._visit_counts[key] = self._visit_counts.get(key, 0) + 1
        self._total_rewards[key] = self._total_rewards.get(key, 0.0) + reward

    # ------------------------------------------------------------------
    # Topology manipulation
    # ------------------------------------------------------------------

    def _perturb_topology(
        self,
        topology: Topology,
        pool: list[AgentRole],
    ) -> Topology:
        """Generate a perturbed version of a topology (mutation).

        Randomly reassigns a child node to a different parent, swaps
        roles, or adjusts communication weights.
        """
        nodes = dict(topology.nodes)
        edges = list(topology.edges)

        if len(nodes) < 2:
            return topology

        mutation = random.choice(["reparent", "swap_weights", "add_edge", "remove_edge"])

        if mutation == "reparent" and len(nodes) >= 3:
            # Move a non-root node to a different parent
            non_root = [r for r, n in nodes.items() if n.parent is not None]
            if len(non_root) >= 2:
                child_role = random.choice(non_root)
                possible_parents = [
                    r for r in nodes if r != child_role and r != nodes[child_role].parent
                ]
                if possible_parents:
                    new_parent = random.choice(possible_parents)
                    old_parent = nodes[child_role].parent

                    # Update child
                    nodes[child_role] = TopologyNode(
                        role=child_role,
                        parent=new_parent,
                        communication_weight=nodes[child_role].communication_weight,
                    )

                    # Update old and new parent children lists
                    if old_parent is not None and old_parent in nodes:
                        old_children = tuple(
                            c for c in nodes[old_parent].children if c != child_role
                        )
                        nodes[old_parent] = TopologyNode(
                            role=old_parent,
                            parent=nodes[old_parent].parent,
                            children=old_children,
                            communication_weight=nodes[old_parent].communication_weight,
                        )

                    if new_parent in nodes:
                        new_children = nodes[new_parent].children + (child_role,)
                        nodes[new_parent] = TopologyNode(
                            role=new_parent,
                            parent=nodes[new_parent].parent,
                            children=new_children,
                            communication_weight=nodes[new_parent].communication_weight,
                        )

        elif mutation == "swap_weights":
            # Swap communication weights between two nodes
            roles = list(nodes.keys())
            if len(roles) >= 2:
                r1, r2 = random.sample(roles, 2)
                w1 = nodes[r1].communication_weight
                w2 = nodes[r2].communication_weight
                nodes[r1] = TopologyNode(
                    role=r1,
                    parent=nodes[r1].parent,
                    children=nodes[r1].children,
                    communication_weight=w2,
                )
                nodes[r2] = TopologyNode(
                    role=r2,
                    parent=nodes[r2].parent,
                    children=nodes[r2].children,
                    communication_weight=w1,
                )

        elif mutation == "add_edge":
            possible = [
                (r1, r2)
                for r1 in nodes for r2 in nodes
                if r1 != r2 and (r1, r2) not in edges
            ]
            if possible:
                new_edge = random.choice(possible)
                edges.append(new_edge)

        elif mutation == "remove_edge" and len(edges) > len(nodes):
            # Don't remove edges that would disconnect a node
            connected_nodes = set()
            for frm, to in edges:
                connected_nodes.add(frm)
                connected_nodes.add(to)

            safe_removals = [
                e for e in edges
                if len([(f, t) for (f, t) in edges if f == e[0] or t == e[0]]) > 1
                and len([(f, t) for (f, t) in edges if f == e[1] or t == e[1]]) > 1
            ]
            if safe_removals:
                edges.remove(random.choice(safe_removals))

        return Topology(
            nodes=nodes,
            template=topology.template,
            edges=tuple(edges),
            reward=topology.reward,
            quality_score=topology.quality_score,
            cost_estimate=topology.cost_estimate,
            latency_estimate=topology.latency_estimate,
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def _evaluate(self, topology: Topology, task: str) -> Topology:
        """Evaluate a topology, computing its reward.

        The default reward function is::

            reward = quality_score / (cost + latency)

        where:
          - quality_score is derived from node connectivity and role diversity
          - cost is the sum of all node costs
          - latency is the longest path from root to leaf
        """
        quality = self._estimate_quality(topology, task)
        cost = self._estimate_cost(topology)
        latency = self._estimate_latency(topology)

        reward = self._reward_fn(Topology(
            nodes=topology.nodes,
            template=topology.template,
            edges=topology.edges,
            quality_score=quality,
            cost_estimate=cost,
            latency_estimate=latency,
        ))

        return Topology(
            nodes=topology.nodes,
            template=topology.template,
            edges=topology.edges,
            reward=reward,
            quality_score=quality,
            cost_estimate=cost,
            latency_estimate=latency,
        )

    @staticmethod
    def _estimate_quality(topology: Topology, task: str) -> float:
        """Estimate task completion quality based on topology structure.

        Factors considered:
          - Node count (more agents -> higher potential quality, diminishing)
          - Edge count / connectivity (more edges -> better information flow)
          - Role diversity (different capabilities -> better coverage)
          - Tree depth (deeper -> more specialized processing)

        Returns a score in [0.0, 1.0].
        """
        n_nodes = len(topology.nodes)
        if n_nodes == 0:
            return 0.0

        # Base: node count (logarithmic scaling)
        node_score = math.log(n_nodes + 1) / math.log(10)

        # Connectivity: edge density
        possible_edges = n_nodes * (n_nodes - 1) / 2.0
        edge_density = len(topology.edges) / possible_edges if possible_edges > 0 else 0.0
        connectivity_score = math.sqrt(edge_density)  # sqrt to reward, not demand

        # Role diversity: unique capabilities
        roles = set(topology.nodes.keys())
        diversity_score = min(len(roles) / 10.0, 1.0)

        # Composite
        quality = (
            node_score * 0.4
            + connectivity_score * 0.35
            + diversity_score * 0.25
        )

        return min(quality, 1.0)

    @staticmethod
    def _estimate_cost(topology: Topology) -> float:
        """Estimate cumulative cost of the topology.

        Sum of communication_weight across all nodes, with a base of 1.0
        per node.
        """
        total = 0.0
        for node in topology.nodes.values():
            total += 1.0 + node.communication_weight * 0.5
        return total

    @staticmethod
    def _estimate_latency(topology: Topology) -> float:
        """Estimate latency as the longest root-to-leaf path.

        Returns the number of edges on the longest path.
        """
        if not topology.nodes:
            return 0.0

        # Find root(s)
        roots = [r for r, n in topology.nodes.items() if n.parent is None]
        if not roots:
            return float(len(topology.nodes))  # approximate

        # BFS from roots to find max depth
        max_depth = 0.0
        for root in roots:
            visited: set[str] = set()
            stack: list[tuple[str, float]] = [(root, 0.0)]

            while stack:
                role, depth = stack.pop()
                if role in visited:
                    continue
                visited.add(role)
                max_depth = max(max_depth, depth)

                node = topology.nodes.get(role)
                if node:
                    for child in node.children:
                        if child in topology.nodes:
                            stack.append((child, depth + node.communication_weight))

        return max_depth + 1.0  # +1 for the root step

    @staticmethod
    def _default_reward(topology: Topology) -> float:
        """Default reward function: quality / (cost + latency)."""
        denominator = (topology.cost_estimate + topology.latency_estimate)
        if denominator <= 0:
            return 0.0
        return topology.quality_score / denominator

    # ------------------------------------------------------------------
    # MCTS tree management
    # ------------------------------------------------------------------

    def _get_children(self, topology: Topology) -> list[Topology]:
        """Generate child topologies by applying one perturbation each."""
        key = self._topology_key(topology)
        if key in self._children_cache:
            return [self._deserialize_topology(k) for k in self._children_cache[key]]

        # Generate via perturbations
        children: list[Topology] = []
        pool_roles = [
            AgentRole(role=r)
            for r in topology.nodes.keys()
        ]

        for _ in range(min(3, len(topology.nodes))):
            child = self._perturb_topology(topology, pool_roles)
            if child != topology:
                children.append(child)

        # Cache serialized keys
        self._children_cache[key] = [self._topology_key(c) for c in children]
        return children

    def _best_known(self, seed_candidates: list[Topology]) -> Topology:
        """Return the topology with the highest reward seen so far."""
        best = seed_candidates[0] if seed_candidates else None
        if best is None:
            # Find from visited
            best_key = max(
                self._total_rewards,
                key=lambda k: self._total_rewards[k] / max(self._visit_counts[k], 1),
                default=None,
            )
            if best_key is None:
                return self._empty_topology(TopologyTemplate.STAR)
            return self._deserialize_topology(best_key)

        for key in self._total_rewards:
            avg = self._total_rewards[key] / max(self._visit_counts[key], 1)
            if avg > best.reward:
                topo = self._deserialize_topology(key)
                if topo.reward > best.reward:
                    best = topo
        return best

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _topology_key(topology: Topology) -> str:
        """Serialize topology to a hashable string key."""
        sorted_edges = sorted(
            f"{f}->{t}" for f, t in topology.edges
        )
        return f"{topology.template.value}:{','.join(sorted_edges)}"

    @staticmethod
    def _deserialize_topology(key: str) -> Topology:
        """Deserialize a topology key back to a Topology object.

        This is lossy: only edges and template are preserved. For full
        reconstruction, use the original building methods.
        """
        parts = key.split(":", 1)
        template_str = parts[0] if len(parts) >= 2 else "star"
        template = TopologyTemplate(template_str)

        edges: list[tuple[str, str]] = []
        nodes: dict[str, TopologyNode] = {}

        if len(parts) >= 2 and parts[1]:
            for edge_str in parts[1].split(","):
                if "->" in edge_str:
                    frm, to = edge_str.split("->", 1)
                    edges.append((frm, to))
                    if frm not in nodes:
                        nodes[frm] = TopologyNode(role=frm, parent=None)
                    if to not in nodes:
                        nodes[to] = TopologyNode(role=to, parent=frm)
                    # Update the 'to' node's parent
                    nodes[to] = TopologyNode(
                        role=to,
                        parent=frm,
                        communication_weight=nodes[to].communication_weight if to in nodes else 0.5,
                    )

        return Topology(
            nodes=nodes,
            template=template,
            edges=tuple(edges),
        )

    @staticmethod
    def _empty_topology(template: TopologyTemplate) -> Topology:
        """Return an empty topology for a given template."""
        return Topology(
            nodes={},
            template=template,
            edges=(),
        )
