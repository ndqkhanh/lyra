"""
Deliberate problem solving via tree search, MCTS, automated workflow
generation, and speculative planning during idle time.

Classes
-------
PlanNode:
    A node in the search tree with state, action, reward, and children.
TreeOfThoughts:
    Deliberate problem solving via breadth-first tree search.
MCTSPlanner:
    Monte Carlo Tree Search with a learned / heuristic world model.
AFlowSearch:
    Automated workflow generation that discovers effective action
    sequences through iterative refinement.
IdleSpecPlanner:
    Speculative planning that runs during tool-waiting idle time.
"""

from __future__ import annotations

import itertools
import logging
import math
import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PlanNode
# ---------------------------------------------------------------------------


@dataclass
class PlanNode:
    """A node in the search tree."""
    """A node in the search tree.

    Attributes
    ----------
    state:
        Current problem state (arbitrary serializable data).
    action:
        The action that led to this state (``None`` for root).
    reward:
        Accumulated reward / value estimate for this node.
    parent:
        Parent node (``None`` for root).
    children:
        Child nodes discovered during search.
    visits:
        Number of times this node has been visited during search.
    depth:
        Depth of this node from the root.
    metadata:
        Arbitrary metadata attached to the node.
    """

    state: Any
    action: str | None = None
    reward: float = 0.0
    parent: PlanNode | None = None
    children: list[PlanNode] = field(default_factory=list)
    visits: int = 0
    depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        """True if this node has no children."""
        return len(self.children) == 0

    def ucb_score(self, exploration_weight: float = 1.41) -> float:
        """Upper Confidence Bound score for MCTS selection.

        Args:
            exploration_weight: Controls exploration vs. exploitation
                (default 1.41, standard for UCB1).

        Returns:
            The UCB score.
        """
        if self.visits == 0:
            return float("inf")
        exploitation = self.reward / self.visits
        parent_visits = self.parent.visits if self.parent else 1
        exploration = exploration_weight * math.sqrt(
            math.log(parent_visits) / self.visits
        )
        return exploitation + exploration

    def best_child(self, exploration_weight: float = 1.41) -> PlanNode:
        """Select the child with the highest UCB score.

        Args:
            exploration_weight: UCB exploration parameter.

        Returns:
            The child node with maximum UCB score.
        """
        return max(self.children, key=lambda c: c.ucb_score(exploration_weight))

    def best_path(self) -> list[PlanNode]:
        """Return the sequence of nodes from root to self."""
        path: list[PlanNode] = []
        current: PlanNode | None = self
        while current is not None:
            path.append(current)
            current = current.parent
        path.reverse()
        return path

    def add_child(self, state: Any, action: str, reward: float = 0.0) -> PlanNode:
        """Create and add a child node.

        Args:
            state: Child state.
            action: Action leading to this state.
            reward: Reward for this action.

        Returns:
            The newly created child node.
        """
        child = PlanNode(
            state=state,
            action=action,
            reward=reward,
            parent=self,
            depth=self.depth + 1,
        )
        self.children.append(child)
        return child

    def to_dict(self) -> dict[str, Any]:
        """Serialize node and subtree to a dict."""
        return {
            "state": self.state,
            "action": self.action,
            "reward": self.reward,
            "depth": self.depth,
            "visits": self.visits,
            "children": [c.to_dict() for c in self.children],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# TreeOfThoughts
# ---------------------------------------------------------------------------


class TreeOfThoughts:
    """Deliberate problem solving via breadth-first tree search.

    Explores a tree of partial solutions (thoughts) by branching at each
    step into candidate next-thoughts, then selecting the most promising
    paths for further expansion.

    Usage::

        def propose(state: str) -> list[str]:
            # Generate candidate next-thoughts
            return [state + " " + w for w in ["explore", "analyze", "conclude"]]

        def evaluate(state: str) -> float:
            # Score a partial solution
            return len(state) / 100.0

        tot = TreeOfThoughts(propose_fn=propose, evaluate_fn=evaluate)
        result = tot.search(initial_state="start", max_steps=5, beam_width=3)
        print(result.state, result.reward)
    """

    def __init__(
        self,
        propose_fn: Callable[[Any], list[tuple[str, Any]]] | None = None,
        evaluate_fn: Callable[[Any], float] | None = None,
        branch_factor: int = 3,
        seed: int | None = None,
    ) -> None:
        self._propose_fn = propose_fn or self._default_propose
        self._evaluate_fn = evaluate_fn or self._default_evaluate
        self.branch_factor = branch_factor
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        initial_state: Any,
        max_steps: int = 10,
        beam_width: int = 3,
    ) -> PlanNode:
        """Run breadth-first tree-of-thought search.

        At each step, expands each node in the current frontier, evaluates
        all candidates, and keeps the top ``beam_width``.

        Args:
            initial_state: Starting problem state.
            max_steps: Maximum depth of search.
            beam_width: Number of best nodes to keep per level.

        Returns:
            The best leaf node found.
        """
        root = PlanNode(state=initial_state)
        frontier: list[PlanNode] = [root]

        for step in range(max_steps):
            candidates: list[PlanNode] = []

            for node in frontier:
                proposals = self._propose_fn(node.state)

                for action, state in proposals:
                    candidate = node.add_child(state=state, action=str(action))

                    # Evaluate the candidate thought
                    candidate.reward = self._evaluate_fn(state)
                    candidate.visits = 1
                    candidates.append(candidate)

            if not candidates:
                logger.info("ToT: no candidates at step %d — terminating early", step)
                break

            # Keep top beam_width candidates
            candidates.sort(key=lambda n: n.reward, reverse=True)
            frontier = candidates[:beam_width]

            logger.debug(
                "ToT step %d: %d candidates, best=%.4f, worst=%.4f",
                step,
                len(candidates),
                frontier[0].reward,
                frontier[-1].reward if len(frontier) > 1 else frontier[0].reward,
            )

        return max(frontier, key=lambda n: n.reward) if frontier else root

    def search_with_backtracking(
        self,
        initial_state: Any,
        max_steps: int = 10,
        beam_width: int = 3,
        backtrack_threshold: float = 0.1,
    ) -> PlanNode:
        """Search with backtracking when no candidate exceeds a threshold.

        Args:
            initial_state: Starting state.
            max_steps: Maximum depth.
            beam_width: Beam width per level.
            backtrack_threshold: If no candidate exceeds this reward,
                backtrack to the parent.

        Returns:
            Best leaf node.
        """
        root = PlanNode(state=initial_state)
        frontier: list[PlanNode] = [root]

        for step in range(max_steps):
            new_frontier: list[PlanNode] = []

            for node in frontier:
                proposals = self._propose_fn(node.state)
                for action, state in proposals:
                    candidate = node.add_child(state=state, action=str(action))
                    candidate.reward = self._evaluate_fn(state)
                    candidate.visits = 1
                    new_frontier.append(candidate)

            if not new_frontier:
                break

            # Filter: keep only candidates above threshold
            above_threshold = [
                n for n in new_frontier if n.reward >= backtrack_threshold
            ]
            if above_threshold:
                above_threshold.sort(key=lambda n: n.reward, reverse=True)
                frontier = above_threshold[:beam_width]
            else:
                # Backtrack: fall back to parent nodes
                logger.info("ToT: backtracking at step %d", step)
                parents: list[PlanNode] = []
                seen_ids: set[int] = set()
                for n in new_frontier:
                    if n.parent is not None and id(n.parent) not in seen_ids:
                        parents.append(n.parent)
                        seen_ids.add(id(n.parent))
                frontier = parents if parents else new_frontier[:beam_width]

        return max(frontier, key=lambda n: n.reward) if frontier else root

    def to_dict(self, root: PlanNode) -> dict[str, Any]:
        """Serialize the tree rooted at *root* to a dict.

        Args:
            root: Root node of the tree.

        Returns:
            Serializable dict representation.
        """
        return root.to_dict()

    # ------------------------------------------------------------------
    # Default helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_propose(state: Any) -> list[tuple[str, Any]]:
        """Default proposer: return no candidates."""
        return []

    @staticmethod
    def _default_evaluate(state: Any) -> float:
        """Default evaluator: return 0."""
        return 0.0


# ---------------------------------------------------------------------------
# MCTSPlanner
# ---------------------------------------------------------------------------


class MCTSPlanner:
    """Monte Carlo Tree Search with a world model.

    Uses a learned or heuristic world model to simulate the outcome of
    actions, then applies MCTS to find the optimal action sequence.

    Usage::

        def simulate(state: Any, action: str) -> tuple[Any, float]:
            # Apply action to state, return (next_state, reward)
            return (state + "_" + action, random.random())

        planner = MCTSPlanner(simulate_fn=simulate)
        best_node = planner.search(initial_state="start", iterations=100)
        print(best_node.best_path())
    """

    def __init__(
        self,
        simulate_fn: Callable[[Any, str], tuple[Any, float]] | None = None,
        is_terminal_fn: Callable[[Any], bool] | None = None,
        get_actions_fn: Callable[[Any], list[str]] | None = None,
        exploration_weight: float = 1.41,
        seed: int | None = None,
    ) -> None:
        self._simulate_fn = simulate_fn or self._default_simulate
        self._is_terminal_fn = is_terminal_fn or (lambda s: False)
        self._get_actions_fn = get_actions_fn or self._default_get_actions
        self.exploration_weight = exploration_weight
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        initial_state: Any,
        iterations: int = 100,
        max_depth: int = 20,
    ) -> PlanNode:
        """Run MCTS for a given number of iterations.

        Args:
            initial_state: Starting state for the search.
            iterations: Number of MCTS iterations (simulations).
            max_depth: Maximum depth per simulation.

        Returns:
            The root node with updated visit/reward data.  Use
            ``root.best_child(exploration_weight=0)`` to get the
            best action.
        """
        root = PlanNode(state=initial_state)

        for i in range(iterations):
            node = root
            path: list[PlanNode] = [node]

            # 1. SELECT
            while not node.is_leaf:
                node = node.best_child(self.exploration_weight)
                path.append(node)

            # 2. EXPAND
            if not self._is_terminal_fn(node.state):
                actions = self._get_actions_fn(node.state)
                for action in actions:
                    next_state, reward = self._simulate_fn(node.state, action)
                    child = node.add_child(state=next_state, action=action, reward=reward)
                    child.visits = 1

            # 3. SIMULATE (rollout from the expanded node)
            rollout_node = path[-1]
            reward = self._rollout(rollout_node.state, max_depth - rollout_node.depth)

            # 4. BACKPROPAGATE
            for n in reversed(path):
                n.visits += 1
                n.reward += reward

            if (i + 1) % max(1, iterations // 10) == 0:
                logger.debug("MCTS iteration %d/%d", i + 1, iterations)

        return root

    def best_action(self, root: PlanNode) -> str | None:
        """Get the best action from the root node.

        Args:
            root: Root node after running ``search(...)``.

        Returns:
            The action with the highest average reward, or None if the
            root has no children.
        """
        if not root.children:
            return None
        best = max(root.children, key=lambda c: c.reward / max(c.visits, 1))
        return best.action

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rollout(self, state: Any, depth: int) -> float:
        """Run a random rollout from a state."""
        total_reward = 0.0
        current = state

        for _ in range(depth):
            if self._is_terminal_fn(current):
                break
            actions = self._get_actions_fn(current)
            if not actions:
                break
            action = self._rng.choice(actions)
            current, reward = self._simulate_fn(current, action)
            total_reward += reward

        return total_reward

    @staticmethod
    def _default_simulate(state: Any, action: str) -> tuple[Any, float]:
        """Default simulator: return state unchanged with 0 reward."""
        return (state, 0.0)

    @staticmethod
    def _default_get_actions(state: Any) -> list[str]:
        """Default action generator: return empty list."""
        return []


# ---------------------------------------------------------------------------
# AFlowSearch
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowStep:
    """A single step in a discovered workflow.

    Attributes
    ----------
    action:
        The action name.
    params:
        Action parameters.
    expected_outcome:
        Expected outcome description (for verification).
    """

    action: str
    params: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""


@dataclass
class Workflow:
    """A discovered workflow (sequence of steps).

    Attributes
    ----------
    steps:
        Ordered list of workflow steps.
    score:
        Aggregate score based on effectiveness across task instances.
    task_description:
        Description of the task this workflow was generated for.
    """

    steps: list[WorkflowStep] = field(default_factory=list)
    score: float = 0.0
    task_description: str = ""

    def add_step(self, action: str, **params: Any) -> WorkflowStep:
        """Add a step to the workflow.

        Args:
            action: Action name.
            **params: Action parameters.

        Returns:
            The newly created step.
        """
        step = WorkflowStep(action=action, params=params)
        self.steps.append(step)
        return step


class AFlowSearch:
    """Automated workflow generation via iterative refinement.

    Discovers effective action sequences for a task by proposing candidate
    workflows, evaluating them, and refining the best ones.

    Usage::

        def evaluate(workflow: Workflow) -> float:
            # Simulate / run the workflow and return a score
            return random.random()

        aflow = AFlowSearch(evaluate_fn=evaluate)
        best = aflow.search("generate report")
        for step in best.steps:
            print(step.action, step.params)
    """

    def __init__(
        self,
        evaluate_fn: Callable[[Workflow], float] | None = None,
        mutate_fn: Callable[[Workflow], Workflow] | None = None,
        crossover_fn: Callable[[Workflow, Workflow], Workflow] | None = None,
        seed: int | None = None,
    ) -> None:
        self._evaluate_fn = evaluate_fn or self._default_evaluate
        self._mutate_fn = mutate_fn or self._default_mutate
        self._crossover_fn = crossover_fn or self._default_crossover
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        task_description: str,
        population_size: int = 10,
        generations: int = 20,
        initial_steps: list[WorkflowStep] | None = None,
    ) -> Workflow:
        """Discover a workflow through evolutionary search.

        Args:
            task_description: Description of the target task.
            population_size: Number of workflows to maintain per generation.
            generations: Number of evolutionary generations.
            initial_steps: Optional seed steps for the initial population.

        Returns:
            The best discovered workflow.
        """
        population = self._initialize_population(
            task_description=task_description,
            population_size=population_size,
            seed_steps=initial_steps,
        )

        best_workflow: Workflow = population[0]

        for gen in range(generations):
            # Evaluate
            scored = [(self._evaluate_fn(w), w) for w in population]
            scored.sort(key=lambda x: x[0], reverse=True)

            if scored[0][0] > best_workflow.score:
                best_workflow = scored[0][1]

            logger.debug(
                "AFlow gen %d/%d: best=%.4f, avg=%.4f",
                gen + 1,
                generations,
                scored[0][0],
                sum(s for s, _ in scored) / len(scored),
            )

            # Selection: keep top half
            keep = max(2, population_size // 2)
            survivors = [w for _, w in scored[:keep]]

            # Reproduction
            next_population = list(survivors)
            while len(next_population) < population_size:
                parent = self._rng.choice(survivors)
                if self._rng.random() < 0.3 and len(survivors) >= 2:
                    # Crossover
                    parent_b = self._rng.choice(survivors)
                    child = self._crossover_fn(parent, parent_b)
                else:
                    # Mutate
                    child = self._mutate_fn(parent)
                next_population.append(child)

            population = next_population

        return best_workflow

    def propose_variants(
        self,
        workflow: Workflow,
        n: int = 5,
    ) -> list[Workflow]:
        """Generate *n* candidate variant workflows from a seed.

        Args:
            workflow: The seed workflow.
            n: Number of variants to generate.

        Returns:
            List of variant workflows.
        """
        return [self._mutate_fn(workflow) for _ in range(n)]

    # ------------------------------------------------------------------
    # Default evolutionary operators
    # ------------------------------------------------------------------

    @staticmethod
    def _default_evaluate(workflow: Workflow) -> float:
        """Default evaluator: return 0."""
        return 0.0

    @staticmethod
    def _default_mutate(workflow: Workflow) -> Workflow:
        """Default mutator: return the workflow unchanged."""
        return workflow

    @staticmethod
    def _default_crossover(a: Workflow, b: Workflow) -> Workflow:
        """Default crossover: return first half of A + second half of B."""
        split = len(a.steps) // 2
        child = Workflow(task_description=a.task_description)
        child.steps = a.steps[:split] + b.steps[split:]
        return child

    def _initialize_population(
        self,
        task_description: str,
        population_size: int,
        seed_steps: list[WorkflowStep] | None,
    ) -> list[Workflow]:
        """Create the initial population of workflows."""
        population: list[Workflow] = []

        # Seed workflow if available
        if seed_steps:
            seed = Workflow(task_description=task_description)
            seed.steps = list(seed_steps)
            population.append(seed)

        # Fill remaining population with mutated variants
        while len(population) < population_size:
            if not population:
                population.append(Workflow(task_description=task_description))
            else:
                base = population[self._rng.randint(0, len(population) - 1)]
                population.append(self._mutate_fn(base))

        return population or [Workflow(task_description=task_description)]


# ---------------------------------------------------------------------------
# IdleSpecPlanner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpeculativePlan:
    """A plan generated during idle time.

    Attributes
    ----------
    steps:
        Ordered list of proposed actions.
    confidence:
        Confidence estimate (0-1) for the plan.
    trigger_condition:
        Condition under which this plan should be activated.
    reasoning:
        Brief explanation of why this plan was generated.
    """

    steps: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    trigger_condition: str = ""
    reasoning: str = ""


class IdleSpecPlanner:
    """Speculative planning during tool-waiting idle time.

    Uses available idle cycles to pre-compute plan branches, anticipate
    agent needs, and prepare fallback strategies.  Plans are cached and
    can be activated when their trigger conditions are met.

    Usage::

        planner = IdleSpecPlanner()
        planner.start_idle_cycle()

        # ... while waiting for a tool result ...
        plan = planner.generate_plan(
            current_state={"step": 1, "data": "..."},
            context="We are analyzing the results",
        )
        planner.cache_plan(plan)

        # Later, activate the cached plan:
        best = planner.select_best_plan(context="tool finished")
        if best:
            for step in best.steps:
                print(step)
    """

    def __init__(self, max_cached_plans: int = 20, seed: int | None = None) -> None:
        self._cached_plans: list[SpeculativePlan] = []
        self.max_cached_plans = max_cached_plans
        self._idle_counter = 0
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Idle cycle management
    # ------------------------------------------------------------------

    def start_idle_cycle(self) -> int:
        """Mark the start of an idle period.

        Returns:
            The idle cycle counter (increments each call).
        """
        self._idle_counter += 1
        logger.debug("IdleSpecPlanner: starting idle cycle %d", self._idle_counter)
        return self._idle_counter

    def end_idle_cycle(self) -> int:
        """Mark the end of an idle period.

        Returns:
            Number of plans generated during this cycle.
        """
        n = len(self._cached_plans)
        logger.debug("IdleSpecPlanner: ending idle cycle — %d plan(s) cached", n)
        return n

    # ------------------------------------------------------------------
    # Plan generation
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        current_state: dict[str, Any],
        context: str = "",
        horizon: int = 5,
    ) -> SpeculativePlan:
        """Generate a speculative plan for what to do next.

        Args:
            current_state: The current execution state.
            context: Natural language context description.
            horizon: Number of steps to plan ahead.

        Returns:
            A ``SpeculativePlan`` with proposed next steps.
        """
        steps: list[str] = []
        for i in range(horizon):
            step = self._propose_step(current_state, context, i)
            steps.append(step)

        confidence = self._estimate_confidence(current_state, context)
        trigger = self._infer_trigger(context)

        return SpeculativePlan(
            steps=tuple(steps),
            confidence=confidence,
            trigger_condition=trigger,
            reasoning=f"Speculative plan from state: {context[:80] if context else 'no context'}",
        )

    def generate_batch(
        self,
        current_state: dict[str, Any],
        context: str = "",
        n_plans: int = 3,
        horizon: int = 5,
    ) -> list[SpeculativePlan]:
        """Generate multiple speculative plans.

        Args:
            current_state: Current execution state.
            context: Context description.
            n_plans: Number of plans to generate.
            horizon: Steps per plan.

        Returns:
            List of plans.
        """
        return [
            self.generate_plan(current_state, context, horizon)
            for _ in range(n_plans)
        ]

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def cache_plan(self, plan: SpeculativePlan) -> None:
        """Add a plan to the cache.

        Args:
            plan: The plan to cache.
        """
        self._cached_plans.append(plan)
        if len(self._cached_plans) > self.max_cached_plans:
            # Remove oldest (lowest confidence)
            self._cached_plans.sort(key=lambda p: p.confidence)
            self._cached_plans = self._cached_plans[-self.max_cached_plans:]

    def select_best_plan(self, context: str = "") -> SpeculativePlan | None:
        """Select the best cached plan, optionally filtering by context.

        Args:
            context: If provided, only plans whose trigger_condition
                matches the context are considered.

        Returns:
            The best matching plan, or None.
        """
        candidates = self._cached_plans
        if context:
            candidates = [
                p
                for p in candidates
                if not p.trigger_condition
                or p.trigger_condition.lower() in context.lower()
                or context.lower() in p.trigger_condition.lower()
            ]

        if not candidates:
            return None

        return max(candidates, key=lambda p: p.confidence)

    def clear_cache(self) -> int:
        """Clear all cached plans.

        Returns:
            Number of plans cleared.
        """
        n = len(self._cached_plans)
        self._cached_plans.clear()
        return n

    def list_cached_plans(self) -> list[SpeculativePlan]:
        """Return all cached plans."""
        return list(self._cached_plans)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _propose_step(
        self,
        state: dict[str, Any],
        context: str,
        step_index: int,
    ) -> str:
        """Propose a single step name based on state and context."""
        templates = [
            "analyze_result",
            "validate_output",
            "generate_code",
            "run_test",
            "review_changes",
            "document_findings",
            "optimize_solution",
            "check_consistency",
            "prepare_report",
            "extract_insights",
            "refactor_module",
            "verify_assumptions",
        ]
        idx = (step_index + hash(str(state.get("step", "")))) % len(templates)
        return templates[idx]

    def _estimate_confidence(
        self,
        state: dict[str, Any],
        context: str,
    ) -> float:
        """Estimate confidence in a speculative plan (0-1)."""
        base = 0.5
        # Higher confidence when we have more context
        if len(context) > 20:
            base += 0.15
        if len(context) > 100:
            base += 0.1
        # Higher confidence with more state information
        if len(state) > 3:
            base += 0.15
        if len(state) > 5:
            base += 0.1
        return min(1.0, base)

    def _infer_trigger(self, context: str) -> str:
        """Infer a trigger condition from context."""
        triggers = [
            "tool_result_available",
            "analysis_complete",
            "error_occurred",
            "task_progress",
            "idle_detected",
        ]
        if "error" in context.lower() or "fail" in context.lower():
            return "error_occurred"
        if "complete" in context.lower() or "done" in context.lower():
            return "task_progress"
        if "analy" in context.lower() or "review" in context.lower():
            return "analysis_complete"
        return triggers[hash(context) % len(triggers)] if context else "idle_detected"
