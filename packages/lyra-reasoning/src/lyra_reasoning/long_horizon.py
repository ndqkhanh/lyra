"""
Long-Horizon Planning & World Model.

Hierarchical planning for 100+ step tasks. Implements decomposition,
dependency tracking, incremental execution, and a mental world model
for counterfactual simulation.

This module addresses the SGR-Bench failure mode where agents cannot
reliably plan beyond 3 steps by providing:

- **PlanTree** -- hierarchical decomposition of goals into
  dependency-tracked nodes.
- **LongHorizonPlanner** -- recursive decomposition, milestone tracking,
  blocker detection, and automatic replanning on failure.
- **WorldModel** -- mental simulation with invariant checking and
  state diffing.

Typical usage::

    planner = LongHorizonPlanner()
    tree = planner.create_plan("Build a web application", {"tech": "Django"})
    tasks = planner.get_next_tasks(tree, limit=3)

    world = WorldModel()
    state = world.define_state({"db": "disconnected"}, [], [])
    result = world.simulate_action(state, "connect to database")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════


class NodeStatus(str, Enum):
    """Status values for plan nodes."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


# ═══════════════════════════════════════════════════════════════════════════
# Core data classes
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PlanNode:
    """A single node in a hierarchical plan tree.

    Attributes:
        node_id: Unique identifier for this node.
        description: Human-readable description of the task.
        parent_id: ID of the parent node, or ``None`` for the root.
        children: Tuple of child node IDs.
        dependencies: Tuple of node IDs that must complete before this node.
        estimated_steps: Estimated number of steps to complete this node.
        status: Current status from ``NodeStatus``.
        priority: Priority level 1--10 (10 = highest).
        assigned_agent: Agent assigned to this node, or ``None``.
    """

    node_id: str
    description: str
    parent_id: Optional[str] = None
    children: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    estimated_steps: int = 1
    status: str = NodeStatus.PENDING.value
    priority: int = 5
    assigned_agent: Optional[str] = None


@dataclass(frozen=True)
class Milestone:
    """A significant checkpoint within a plan.

    Attributes:
        milestone_id: Unique identifier.
        description: Human-readable description.
        completion_criteria: Description of what constitutes completion.
        depends_on_milestones: Milestone IDs that must be completed first.
        deadline_step: Step number by which this milestone should be reached.
        verified: Whether the milestone has been verified as complete.
    """

    milestone_id: str
    description: str
    completion_criteria: str
    depends_on_milestones: Tuple[str, ...] = ()
    deadline_step: int = 0
    verified: bool = False


@dataclass(frozen=True)
class PlanTree:
    """A hierarchical plan with dependency tracking.

    Attributes:
        root: The root ``PlanNode`` representing the overall goal.
        nodes: Mapping of node ID to ``PlanNode`` for the entire tree.
        total_steps: Sum of estimated steps across all nodes.
        completed_steps: Number of steps completed so far.
        created_at: Unix timestamp of plan creation.
        milestones: Milestones associated with this plan.
    """

    root: PlanNode
    nodes: Dict[str, PlanNode]
    total_steps: int
    completed_steps: int
    created_at: float
    milestones: Tuple[Milestone, ...] = ()


@dataclass(frozen=True)
class WorldState:
    """A snapshot of the mental world model.

    Attributes:
        variables: Key-value pairs describing current world state.
        invariants: Constraints that must always hold true.
        assumptions: Working assumptions that may be revised.
    """

    variables: Tuple[Tuple[str, str], ...]
    invariants: Tuple[str, ...]
    assumptions: Tuple[str, ...]


@dataclass(frozen=True)
class SimulationResult:
    """Result of simulating an action in the world model.

    Attributes:
        projected_state: The state after the action.
        success: Whether the action succeeded.
        violated_invariants: Invariants that were violated.
        side_effects: Unintended consequences of the action.
        confidence: Confidence in the simulation (0.0--1.0).
    """

    projected_state: WorldState
    success: bool
    violated_invariants: Tuple[str, ...] = ()
    side_effects: Tuple[str, ...] = ()
    confidence: float = 0.5


@dataclass(frozen=True)
class ProgressSnapshot:
    """Summary of plan progress at a point in time.

    Attributes:
        plan_id: Identifier for the plan (uses root node ID).
        completed_nodes: Number of completed nodes.
        total_nodes: Total nodes in the plan.
        current_milestone: ID of the nearest incomplete milestone, or ``None``.
        blockers: Node IDs that are currently blocked.
        elapsed_steps: Steps executed so far.
        estimated_remaining: Estimated remaining steps.
    """

    plan_id: str
    completed_nodes: int
    total_nodes: int
    current_milestone: Optional[str] = None
    blockers: Tuple[str, ...] = ()
    elapsed_steps: int = 0
    estimated_remaining: int = 0


@dataclass(frozen=True)
class LongHorizonConfig:
    """Configuration for the long-horizon planner.

    Attributes:
        max_depth: Maximum decomposition depth.
        max_breadth: Maximum children per node.
        max_total_steps: Absolute maximum steps for any plan.
        simulation_enabled: Whether world-model simulation is active.
        auto_replan_threshold: Fraction of plan progress below which
            auto-replanning is triggered.
    """

    max_depth: int = 5
    max_breadth: int = 20
    max_total_steps: int = 500
    simulation_enabled: bool = True
    auto_replan_threshold: float = 0.3


# ═══════════════════════════════════════════════════════════════════════════
# Long-Horizon Planner
# ═══════════════════════════════════════════════════════════════════════════


class LongHorizonPlanner:
    """Hierarchical planner for long-horizon tasks.

    Decomposes a goal into a dependency-tracked plan tree with milestone
    verification, blocker detection, and automatic replanning on failure.

    Args:
        config: Configuration for planning limits and behaviour.

    Example::

        planner = LongHorizonPlanner()
        tree = planner.create_plan("Deploy microservice", {"service": "auth"})
        ready = planner.get_next_tasks(tree, limit=3)
        tree = planner.update_node(tree, "n1", NodeStatus.COMPLETED.value)
    """

    def __init__(self, config: Optional[LongHorizonConfig] = None) -> None:
        self._config = config or LongHorizonConfig()
        self._node_counter: int = 0

    # ── Public API ──────────────────────────────────────────────────────

    def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanTree:
        """Hierarchically decompose *goal* into a complete ``PlanTree``.

        Args:
            goal: The high-level goal description.
            context: Optional supplementary context (tech stack, domain, etc.).

        Returns:
            A fully decomposed plan tree.
        """
        ctx = context or {}
        self._node_counter = 0

        root = PlanNode(
            node_id="root",
            description=goal,
            parent_id=None,
            priority=10,
            estimated_steps=self._estimate_steps(goal),
        )

        all_nodes: Dict[str, PlanNode] = {"root": root}
        self._decompose_recursive(root, 0, ctx, all_nodes)

        total = sum(n.estimated_steps for n in all_nodes.values())
        total = min(total, self._config.max_total_steps)

        return PlanTree(
            root=root,
            nodes=all_nodes,
            total_steps=total,
            completed_steps=0,
            created_at=time.time(),
        )

    def decompose(
        self,
        node: PlanNode,
        depth: int,
        config: LongHorizonConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PlanNode]:
        """Decompose *node* into sub-tasks.

        Creates child ``PlanNode`` instances based on the description,
        respecting ``max_depth`` and ``max_breadth`` limits from *config*.

        Args:
            node: The node to decompose.
            depth: Current depth (controls recursion termination).
            config: Configuration for depth/breadth limits.
            context: Optional context influencing decomposition.

        Returns:
            List of child ``PlanNode`` instances.
        """
        if depth >= config.max_depth:
            return []

        ctx = context or {}
        children: List[PlanNode] = []

        sub_tasks = self._generate_sub_tasks(node.description, ctx)
        num_children = min(len(sub_tasks), config.max_breadth)

        for i in range(num_children):
            self._node_counter += 1
            child_id = f"n{self._node_counter}"
            desc = sub_tasks[i] if i < len(sub_tasks) else f"Sub-task {i + 1}"
            dep_ids: Tuple[str, ...] = ()
            if i > 0:
                dep_ids = (child_id[:1] + str(self._node_counter - 1),)

            child = PlanNode(
                node_id=child_id,
                description=desc,
                parent_id=node.node_id,
                dependencies=dep_ids,
                estimated_steps=self._estimate_steps(desc),
                priority=max(1, node.priority - 1),
            )
            children.append(child)

        return children

    def get_next_tasks(self, plan: PlanTree, limit: int = 5) -> List[PlanNode]:
        """Return tasks that are ready to execute.

        A task is ready when all its dependencies have ``COMPLETED`` status
        and its own status is ``PENDING`` or ``BLOCKED``. Results are sorted
        by priority (highest first), then by estimated steps (shortest first).

        Args:
            plan: The plan tree to query.
            limit: Maximum number of tasks to return.

        Returns:
            Up to *limit* ready ``PlanNode`` instances.
        """
        completed_ids = {
            nid
            for nid, n in plan.nodes.items()
            if n.status == NodeStatus.COMPLETED.value
        }

        ready: List[PlanNode] = []
        for node in plan.nodes.values():
            if node.status not in (
                NodeStatus.PENDING.value,
                NodeStatus.BLOCKED.value,
            ):
                continue
            if all(dep in completed_ids for dep in node.dependencies):
                ready.append(node)

        ready.sort(key=lambda n: (-n.priority, n.estimated_steps))
        return ready[:limit]

    def update_node(
        self,
        plan: PlanTree,
        node_id: str,
        status: str,
    ) -> PlanTree:
        """Update a node's status, returning a new ``PlanTree``.

        When a node is marked ``COMPLETED``, children are re-evaluated.
        When marked ``FAILED``, dependent nodes are marked ``BLOCKED``.

        Args:
            plan: Current plan tree.
            node_id: ID of the node to update.
            status: New status (from ``NodeStatus``).

        Returns:
            New ``PlanTree`` with the updated node.
        """
        if node_id not in plan.nodes:
            logger.warning("update_node: node %s not found", node_id)
            return plan

        node = plan.nodes[node_id]
        updated_node = PlanNode(
            node_id=node.node_id,
            description=node.description,
            parent_id=node.parent_id,
            children=node.children,
            dependencies=node.dependencies,
            estimated_steps=node.estimated_steps,
            status=status,
            priority=node.priority,
            assigned_agent=node.assigned_agent,
        )

        new_nodes: Dict[str, PlanNode] = dict(plan.nodes)
        new_nodes[node_id] = updated_node

        # Propagate blocker status when a dependency fails
        if status == NodeStatus.FAILED.value:
            for nid, n in new_nodes.items():
                if node_id in n.dependencies and n.status != NodeStatus.COMPLETED.value:
                    new_nodes[nid] = PlanNode(
                        node_id=n.node_id,
                        description=n.description,
                        parent_id=n.parent_id,
                        children=n.children,
                        dependencies=n.dependencies,
                        estimated_steps=n.estimated_steps,
                        status=NodeStatus.BLOCKED.value,
                        priority=n.priority,
                        assigned_agent=n.assigned_agent,
                    )

        completed = sum(
            1 for n in new_nodes.values() if n.status == NodeStatus.COMPLETED.value
        )

        # Mark root completed if all nodes are done
        if "root" in new_nodes:
            root = new_nodes["root"]
            all_done = all(
                n.status == NodeStatus.COMPLETED.value for n in new_nodes.values()
            )
            if all_done:
                new_nodes["root"] = PlanNode(
                    node_id=root.node_id,
                    description=root.description,
                    parent_id=root.parent_id,
                    children=root.children,
                    dependencies=root.dependencies,
                    estimated_steps=root.estimated_steps,
                    status=NodeStatus.COMPLETED.value,
                    priority=root.priority,
                    assigned_agent=root.assigned_agent,
                )

        return PlanTree(
            root=new_nodes.get("root", plan.root),
            nodes=new_nodes,
            total_steps=plan.total_steps,
            completed_steps=completed,
            created_at=plan.created_at,
            milestones=plan.milestones,
        )

    def add_milestone(
        self,
        plan: PlanTree,
        milestone: Milestone,
    ) -> PlanTree:
        """Associate a milestone with the plan.

        Args:
            plan: Current plan tree.
            milestone: The milestone to add.

        Returns:
            New ``PlanTree`` containing the milestone.
        """
        new_milestones = plan.milestones + (milestone,)
        return PlanTree(
            root=plan.root,
            nodes=plan.nodes,
            total_steps=plan.total_steps,
            completed_steps=plan.completed_steps,
            created_at=plan.created_at,
            milestones=new_milestones,
        )

    def check_milestone(
        self,
        plan: PlanTree,
        milestone_id: str,
    ) -> bool:
        """Verify whether a milestone's completion criteria are met.

        Args:
            plan: Current plan tree.
            milestone_id: ID of the milestone to check.

        Returns:
            ``True`` if the milestone is complete.
        """
        milestone = next(
            (m for m in plan.milestones if m.milestone_id == milestone_id),
            None,
        )
        if milestone is None:
            logger.warning("check_milestone: milestone %s not found", milestone_id)
            return False

        dep_met = all(
            any(m2.milestone_id == dep and m2.verified for m2 in plan.milestones)
            for dep in milestone.depends_on_milestones
        )
        if not dep_met:
            return False

        criteria_lower = milestone.completion_criteria.lower()
        for node in plan.nodes.values():
            if criteria_lower in node.description.lower():
                if node.status != NodeStatus.COMPLETED.value:
                    return False
        return True

    def detect_blockers(self, plan: PlanTree) -> List[PlanNode]:
        """Find all nodes that are currently blocked.

        A node is blocked if any of its dependencies have ``FAILED`` status.

        Args:
            plan: Current plan tree.

        Returns:
            List of blocked ``PlanNode`` instances.
        """
        failed_ids = {
            nid
            for nid, n in plan.nodes.items()
            if n.status == NodeStatus.FAILED.value
        }
        blocked: List[PlanNode] = []
        for node in plan.nodes.values():
            if node.status == NodeStatus.BLOCKED.value:
                blocked.append(node)
            elif any(dep in failed_ids for dep in node.dependencies):
                blocked.append(node)
        return blocked

    def replan(
        self,
        plan: PlanTree,
        failed_node_id: str,
    ) -> PlanTree:
        """Replan the subtree rooted at *failed_node_id*.

        Removes the failed subtree, creates a replacement node, and
        re-decomposes it.

        Args:
            plan: Current plan tree.
            failed_node_id: ID of the node that failed.

        Returns:
            New ``PlanTree`` with the re-decomposed subtree.
        """
        if failed_node_id not in plan.nodes:
            logger.warning("replan: node %s not found", failed_node_id)
            return plan

        failed_node = plan.nodes[failed_node_id]
        new_nodes = dict(plan.nodes)

        # Remove failed node and all its descendants
        descendants = self._collect_descendants(plan, failed_node_id)
        to_remove = {failed_node_id} | descendants
        for nid in to_remove:
            new_nodes.pop(nid, None)

        # Create a replacement node with PENDING status
        replacement = PlanNode(
            node_id=failed_node_id,
            description=failed_node.description,
            parent_id=failed_node.parent_id,
            dependencies=failed_node.dependencies,
            estimated_steps=failed_node.estimated_steps,
            status=NodeStatus.PENDING.value,
            priority=failed_node.priority,
            assigned_agent=failed_node.assigned_agent,
        )
        new_nodes[failed_node_id] = replacement

        # Re-decompose the replacement
        depth = self._node_depth(plan, failed_node_id)
        child_context: Dict[str, Any] = {"replan": True}
        child_nodes = self.decompose(
            replacement,
            depth,
            self._config,
            child_context,
        )
        for child in child_nodes:
            new_nodes[child.node_id] = child

        # Update parent's children list
        parent_id = failed_node.parent_id
        if parent_id and parent_id in new_nodes:
            parent = new_nodes[parent_id]
            updated_parent = PlanNode(
                node_id=parent.node_id,
                description=parent.description,
                parent_id=parent.parent_id,
                children=tuple(
                    c if c != failed_node_id else failed_node_id
                    for c in parent.children
                ),
                dependencies=parent.dependencies,
                estimated_steps=parent.estimated_steps,
                status=parent.status,
                priority=parent.priority,
                assigned_agent=parent.assigned_agent,
            )
            new_nodes[parent_id] = updated_parent

        total = sum(n.estimated_steps for n in new_nodes.values())
        completed = sum(
            1 for n in new_nodes.values() if n.status == NodeStatus.COMPLETED.value
        )

        return PlanTree(
            root=new_nodes.get("root", plan.root),
            nodes=new_nodes,
            total_steps=min(total, self._config.max_total_steps),
            completed_steps=completed,
            created_at=plan.created_at,
            milestones=plan.milestones,
        )

    def get_progress(self, plan: PlanTree) -> ProgressSnapshot:
        """Compute a progress snapshot for the plan.

        Args:
            plan: Current plan tree.

        Returns:
            ``ProgressSnapshot`` summarising current status.
        """
        total_nodes = len(plan.nodes)
        completed_nodes = sum(
            1 for n in plan.nodes.values() if n.status == NodeStatus.COMPLETED.value
        )
        blockers = tuple(n.node_id for n in self.detect_blockers(plan))
        elapsed = plan.completed_steps
        remaining = plan.total_steps - elapsed

        current_milestone: Optional[str] = None
        for ms in plan.milestones:
            if not ms.verified:
                current_milestone = ms.milestone_id
                break

        return ProgressSnapshot(
            plan_id=plan.root.node_id,
            completed_nodes=completed_nodes,
            total_nodes=total_nodes,
            current_milestone=current_milestone,
            blockers=blockers,
            elapsed_steps=elapsed,
            estimated_remaining=max(0, remaining),
        )

    def get_critical_path(self, plan: PlanTree) -> List[str]:
        """Return the longest dependency chain through the plan.

        Considers both explicit dependencies (``dependencies`` field) and
        implicit parent-child edges (a child depends on its parent).

        Uses topological DP over the combined DAG.

        Args:
            plan: Current plan tree.

        Returns:
            List of node IDs forming the critical path, ordered root-to-leaf.
        """
        # Build predecessor list: every node implicitly depends on its parent
        implicit_deps: Dict[str, List[str]] = {}
        for nid, node in plan.nodes.items():
            deps: List[str] = list(node.dependencies)
            if node.parent_id is not None and node.parent_id != nid:
                deps.append(node.parent_id)
            implicit_deps[nid] = deps

        visited: set[str] = set()
        topo: List[str] = []

        def _dfs(nid: str) -> None:
            if nid in visited:
                return
            visited.add(nid)
            for dep in implicit_deps.get(nid, []):
                _dfs(dep)
            topo.append(nid)

        # Visit root first, then any unvisited nodes (orphan chains)
        _dfs(plan.root.node_id)
        for nid in plan.nodes:
            if nid not in visited:
                _dfs(nid)

        longest: Dict[str, int] = {}
        predecessor: Dict[str, Optional[str]] = {}

        for nid in topo:
            node = plan.nodes[nid]
            best_pred: Optional[str] = None
            best_len = 0
            for dep in implicit_deps.get(nid, []):
                if dep in longest and longest[dep] > best_len:
                    best_len = longest[dep]
                    best_pred = dep
            longest[nid] = best_len + node.estimated_steps
            predecessor[nid] = best_pred

        leaf = max(longest, key=lambda k: longest[k])

        path: List[str] = []
        current: Optional[str] = leaf
        while current is not None:
            path.append(current)
            current = predecessor.get(current)
        path.reverse()
        return path

    # ── Internal helpers ────────────────────────────────────────────────

    def _decompose_recursive(
        self,
        node: PlanNode,
        depth: int,
        context: Dict[str, Any],
        all_nodes: Dict[str, PlanNode],
    ) -> None:
        """Recursively decompose *node* and populate *all_nodes*."""
        # Safety cap: stop if plan already exceeds max_total_steps
        if len(all_nodes) >= self._config.max_total_steps:
            return

        children = self.decompose(node, depth, self._config, context)
        if not children:
            return

        child_ids: List[str] = []
        for child in children:
            child_ids.append(child.node_id)
            all_nodes[child.node_id] = child

        updated = PlanNode(
            node_id=node.node_id,
            description=node.description,
            parent_id=node.parent_id,
            children=tuple(child_ids),
            dependencies=node.dependencies,
            estimated_steps=node.estimated_steps,
            status=node.status,
            priority=node.priority,
            assigned_agent=node.assigned_agent,
        )
        all_nodes[node.node_id] = updated

        for child in children:
            self._decompose_recursive(child, depth + 1, context, all_nodes)

    @staticmethod
    def _generate_sub_tasks(
        description: str,
        context: Dict[str, Any],
    ) -> List[str]:
        """Generate sub-task descriptions for a node.

        Stub implementation returns 2--4 patterns based on description
        complexity.  A production system would call an LLM for
        context-aware decomposition.
        """
        _ = context
        templates = [
            f"Analyse requirements for: {description}",
            f"Design solution for: {description}",
            f"Implement core logic for: {description}",
            f"Test and validate: {description}",
        ]
        # Simpler descriptions get fewer children
        word_count = len(description.split())
        if word_count <= 5:
            return templates[:2]
        if word_count <= 12:
            return templates[:3]
        return templates

    @staticmethod
    def _estimate_steps(description: str) -> int:
        """Rough step estimate based on description length."""
        word_count = len(description.split())
        if word_count > 20:
            return 5
        if word_count > 10:
            return 3
        return 1

    def _collect_descendants(
        self,
        plan: PlanTree,
        node_id: str,
    ) -> set[str]:
        """Collect all descendant node IDs of *node_id*."""
        descendants: set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            node = plan.nodes.get(current)
            if node is None:
                continue
            for child_id in node.children:
                if child_id not in descendants:
                    descendants.add(child_id)
                    stack.append(child_id)
        descendants.discard(node_id)
        return descendants

    def _node_depth(self, plan: PlanTree, node_id: str) -> int:
        """Compute the depth of *node_id* in the plan tree."""
        depth = 0
        current = node_id
        visited: set[str] = set()
        while current in plan.nodes and current != "root":
            if current in visited:
                break
            visited.add(current)
            parent = plan.nodes[current].parent_id
            if parent is None:
                break
            depth += 1
            current = parent
        return depth


# ═══════════════════════════════════════════════════════════════════════════
# World Model
# ═══════════════════════════════════════════════════════════════════════════


class WorldModel:
    """Mental world model for counterfactual simulation.

    Maintains a ``WorldState`` and provides methods to simulate actions,
    check invariants, diff states, and apply updates immutably.

    Example::

        world = WorldModel()
        state = world.define_state(
            {"connection": "active", "data": "none"},
            invariants=["connection must not be lost"],
            assumptions=["network is reliable"],
        )
        result = world.simulate_action(state, "fetch data")
        print(result.projected_state)
    """

    def __init__(self) -> None:
        self._simulation_history: List[Tuple[WorldState, SimulationResult]] = []

    def define_state(
        self,
        variables: Dict[str, str],
        invariants: Optional[List[str]] = None,
        assumptions: Optional[List[str]] = None,
    ) -> WorldState:
        """Create a new ``WorldState`` from dictionaries.

        Args:
            variables: Key-value pairs to convert to tuple form.
            invariants: Constraint descriptions.
            assumptions: Working assumption descriptions.

        Returns:
            A new ``WorldState`` instance.
        """
        var_tuples = tuple(sorted((k, v) for k, v in variables.items()))
        return WorldState(
            variables=var_tuples,
            invariants=tuple(invariants or []),
            assumptions=tuple(assumptions or []),
        )

    def simulate_action(
        self,
        state: WorldState,
        action: str,
    ) -> SimulationResult:
        """Predict the outcome of *action* given *state*.

        Stub implementation using keyword-based state projection.
        A production version would call an LLM or learned dynamics model.

        Args:
            state: Current world state.
            action: Description of the action to simulate.

        Returns:
            ``SimulationResult`` with projected state and confidence.
        """
        var_dict = dict(state.variables)
        side_effects: List[str] = []
        action_lower = action.lower()

        action_words = set(action_lower.split())
        if action_words & {"connect", "establish", "open"}:
            var_dict["connection"] = "active"
            side_effects.append("Resource allocation increased")
        elif action_words & {"disconnect", "close", "terminate"}:
            var_dict["connection"] = "disconnected"
            side_effects.append("Resources freed")
        elif action_words & {"fetch", "load", "read", "query"}:
            if var_dict.get("connection") == "active":
                var_dict["data"] = "loaded"
                side_effects.append("Cache populated")
            else:
                side_effects.append("Action skipped: no active connection")
        elif action_words & {"write", "save", "store", "update"}:
            var_dict["data"] = "persisted"
            side_effects.append("Storage consumed")
        elif action_words & {"delete", "remove", "clear"}:
            var_dict["data"] = "none"
            side_effects.append("Data erased")

        new_variables = tuple(sorted(var_dict.items()))
        projected = WorldState(
            variables=new_variables,
            invariants=state.invariants,
            assumptions=state.assumptions,
        )

        invariants_ok, violated = self.check_invariants(projected)

        result = SimulationResult(
            projected_state=projected,
            success=invariants_ok,
            violated_invariants=violated,
            side_effects=tuple(side_effects),
            confidence=0.7 if invariants_ok else 0.3,
        )

        self._simulation_history.append((state, result))
        return result

    def check_invariants(
        self,
        state: WorldState,
    ) -> Tuple[bool, Tuple[str, ...]]:
        """Verify that all invariants hold in *state*.

        Stub implementation using keyword-based violation detection.

        Args:
            state: The world state to check.

        Returns:
            ``(all_ok, violated_invariant_descriptions)``.
        """
        var_dict = dict(state.variables)
        violated: List[str] = []

        for inv in state.invariants:
            inv_lower = inv.lower()
            if "connection" in inv_lower and "lost" in inv_lower:
                if var_dict.get("connection") == "disconnected":
                    violated.append(inv)
            elif "data" in inv_lower and ("must" in inv_lower or "always" in inv_lower):
                if var_dict.get("data") == "none":
                    violated.append(inv)

        return (len(violated) == 0, tuple(violated))

    def compare_states(
        self,
        before: WorldState,
        after: WorldState,
    ) -> List[str]:
        """Diff two world states, returning human-readable changes.

        Args:
            before: The earlier state.
            after: The later state.

        Returns:
            Human-readable change descriptions.
        """
        changes: List[str] = []
        before_vars = dict(before.variables)
        after_vars = dict(after.variables)

        all_keys = set(before_vars) | set(after_vars)
        for key in sorted(all_keys):
            b_val = before_vars.get(key)
            a_val = after_vars.get(key)
            if b_val != a_val:
                if b_val is None:
                    changes.append(f"Variable '{key}' added: {a_val}")
                elif a_val is None:
                    changes.append(f"Variable '{key}' removed (was: {b_val})")
                else:
                    changes.append(
                        f"Variable '{key}' changed: {b_val} -> {a_val}"
                    )

        return changes

    def update_state(
        self,
        state: WorldState,
        updates: Dict[str, str],
    ) -> WorldState:
        """Apply updates to *state* immutably.

        Args:
            state: Current world state.
            updates: Key-value pairs to update.

        Returns:
            New ``WorldState`` with updates applied.
        """
        var_dict = dict(state.variables)
        var_dict.update(updates)
        new_variables = tuple(sorted(var_dict.items()))

        return WorldState(
            variables=new_variables,
            invariants=state.invariants,
            assumptions=state.assumptions,
        )

    @property
    def simulation_history(
        self,
    ) -> Tuple[Tuple[WorldState, SimulationResult], ...]:
        """Read-only history of all simulations performed."""
        return tuple(self._simulation_history)

    def reset_history(self) -> None:
        """Clear simulation history."""
        self._simulation_history.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Public API exports
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "NodeStatus",
    # Data classes
    "PlanNode",
    "PlanTree",
    "WorldState",
    "SimulationResult",
    "Milestone",
    "ProgressSnapshot",
    "LongHorizonConfig",
    # Planner
    "LongHorizonPlanner",
    # World model
    "WorldModel",
]
