"""
Tests for TreeOfThoughts, MCTSPlanner, AFlowSearch, IdleSpecPlanner.

Covers:
- PlanNode construction and tree operations
- TreeOfThoughts beam search and backtracking
- MCTSPlanner search loop and best_action
- AFlowSearch evolutionary workflow discovery
- IdleSpecPlanner speculative planning during idle time
"""

from __future__ import annotations

from lyra.agent_loop.tree_of_thoughts import (
    AFlowSearch,
    IdleSpecPlanner,
    MCTSPlanner,
    PlanNode,
    SpeculativePlan,
    TreeOfThoughts,
    Workflow,
    WorkflowStep,
)

# ======================================================================
# PlanNode
# ======================================================================


class TestPlanNode:
    """PlanNode — tree node with state, action, reward, children."""

    def test_root_node(self) -> None:
        """A root node has no parent and no action."""
        node = PlanNode(state="initial")
        assert node.state == "initial"
        assert node.action is None
        assert node.parent is None
        assert node.depth == 0
        assert node.is_leaf
        assert node.children == []

    def test_add_child(self) -> None:
        """add_child creates and returns a connected child node."""
        root = PlanNode(state="root")
        child = root.add_child(state="child_a", action="act_a", reward=1.0)
        assert child.state == "child_a"
        assert child.action == "act_a"
        assert child.reward == 1.0
        assert child.parent is root
        assert child.depth == 1
        assert child in root.children

    def test_is_leaf(self) -> None:
        """is_leaf is True for a node with no children."""
        root = PlanNode(state="root")
        assert root.is_leaf
        root.add_child(state="c", action="a")
        assert not root.is_leaf

    def test_best_path(self) -> None:
        """best_path returns the sequence from root to self."""
        root = PlanNode(state="root")
        mid = root.add_child(state="mid", action="step1")
        leaf = mid.add_child(state="leaf", action="step2")
        path = leaf.best_path()
        assert len(path) == 3
        assert path[0] is root
        assert path[1] is mid
        assert path[2] is leaf

    def test_ucb_score(self) -> None:
        """ucb_score returns a finite value for visited nodes."""
        root = PlanNode(state="root")
        child = root.add_child(state="c", action="a", reward=5.0)
        child.visits = 3
        root.visits = 10
        score = child.ucb_score(exploration_weight=1.41)
        assert score > 0

    def test_best_child(self) -> None:
        """best_child returns the child with highest UCB."""
        root = PlanNode(state="root")
        c1 = root.add_child(state="c1", action="a1", reward=1.0)
        c2 = root.add_child(state="c2", action="a2", reward=10.0)
        c1.visits = 5
        c2.visits = 5
        root.visits = 10
        best = root.best_child(exploration_weight=0)  # pure exploitation
        assert best is c2

    def test_to_dict(self) -> None:
        """to_dict serializes the subtree."""
        root = PlanNode(state="root")
        root.add_child(state="c", action="a", reward=0.5)
        d = root.to_dict()
        assert d["state"] == "root"
        assert len(d["children"]) == 1
        assert d["children"][0]["action"] == "a"


# ======================================================================
# TreeOfThoughts
# ======================================================================


class TestTreeOfThoughts:
    """TreeOfThoughts — breadth-first tree search."""

    def test_search_returns_best_leaf(self) -> None:
        """search returns the highest-reward leaf node."""
        tot = TreeOfThoughts(
            propose_fn=lambda s: [(f"step_{i}", f"{s}/{i}") for i in range(3)],
            evaluate_fn=lambda s: float(len(str(s))),
            branch_factor=3,
        )
        result = tot.search("start", max_steps=2, beam_width=2)
        assert isinstance(result, PlanNode)
        assert result.state is not None

    def test_search_with_no_proposals(self) -> None:
        """search terminates early when there are no proposals."""
        tot = TreeOfThoughts(
            propose_fn=lambda s: [],
            evaluate_fn=lambda s: 0.0,
        )
        result = tot.search("start", max_steps=5, beam_width=3)
        assert result.state == "start"

    def test_search_with_backtracking(self) -> None:
        """search_with_backtracking backtracks when below threshold."""
        tot = TreeOfThoughts(
            propose_fn=lambda s: [(f"step_{i}", f"{s}/{i}") for i in range(2)],
            evaluate_fn=lambda s: 0.05,  # below 0.1 threshold
        )
        result = tot.search_with_backtracking(
            "start", max_steps=3, beam_width=2, backtrack_threshold=0.1,
        )
        assert isinstance(result, PlanNode)
        assert isinstance(result.state, str)

    def test_to_dict(self) -> None:
        """to_dict serializes the search tree."""
        tot = TreeOfThoughts()
        root = PlanNode(state="root")
        root.add_child(state="c", action="a")
        d = tot.to_dict(root)
        assert d["state"] == "root"


# ======================================================================
# MCTSPlanner
# ======================================================================


class TestMCTSPlanner:
    """MCTSPlanner — Monte Carlo Tree Search."""

    def test_search_returns_root(self) -> None:
        """search returns the root node with updated statistics."""
        planner = MCTSPlanner(
            simulate_fn=lambda s, a: (f"{s}_{a}", 1.0),
            get_actions_fn=lambda s: ["left", "right"],
            is_terminal_fn=lambda s: "terminal" in s,
            seed=42,
        )
        root = planner.search("start", iterations=20, max_depth=5)
        assert root.state == "start"
        assert root.visits == 20
        assert len(root.children) == 2

    def test_best_action(self) -> None:
        """best_action returns the action with highest reward."""
        planner = MCTSPlanner(
            simulate_fn=lambda s, a: (f"{s}_{a}", 1.0 if a == "right" else 0.0),
            get_actions_fn=lambda s: ["left", "right"],
            seed=42,
        )
        root = planner.search("start", iterations=10, max_depth=3)
        action = planner.best_action(root)
        assert action == "right"

    def test_best_action_no_children(self) -> None:
        """best_action returns None when root has no children."""
        planner = MCTSPlanner()
        root = PlanNode(state="alone")
        action = planner.best_action(root)
        assert action is None

    def test_terminal_stops_rollout(self) -> None:
        """Rollout stops at terminal states."""
        planner = MCTSPlanner(
            simulate_fn=lambda s, a: (f"terminal_{a}", 1.0),
            get_actions_fn=lambda s: ["do_stuff"],
            is_terminal_fn=lambda s: True,
            seed=42,
        )
        root = planner.search("state", iterations=5, max_depth=10)
        assert root.visits == 5


# ======================================================================
# AFlowSearch
# ======================================================================


class TestAFlowSearch:
    """AFlowSearch — automated workflow generation."""

    def test_search_returns_workflow(self) -> None:
        """search returns a Workflow with best score."""
        def evaluate(w: Workflow) -> float:
            return len(w.steps) * 0.5

        def mutate(w: Workflow) -> Workflow:
            child = Workflow(task_description=w.task_description)
            child.steps = list(w.steps)
            child.steps.append(WorkflowStep(action="mutated_step"))
            return child

        aflow = AFlowSearch(
            evaluate_fn=evaluate,
            mutate_fn=mutate,
            seed=42,
        )
        best = aflow.search("test task", population_size=6, generations=5)
        assert isinstance(best, Workflow)
        assert best.task_description == "test task"

    def test_propose_variants(self) -> None:
        """propose_variants returns variant workflows."""
        aflow = AFlowSearch()
        w = Workflow(task_description="test")
        w.add_step("read")
        variants = aflow.propose_variants(w, n=3)
        assert len(variants) == 3

    def test_workflow_add_step(self) -> None:
        """add_step appends to workflow steps."""
        wf = Workflow(task_description="build")
        step = wf.add_step("compile", lang="python")
        assert len(wf.steps) == 1
        assert step.action == "compile"
        assert step.params["lang"] == "python"

    def test_default_crossover(self) -> None:
        """Default crossover combines two workflows."""
        a = Workflow(task_description="test")
        a.steps = [WorkflowStep(action="a1"), WorkflowStep(action="a2")]
        b = Workflow(task_description="test")
        b.steps = [WorkflowStep(action="b1"), WorkflowStep(action="b2")]
        child = AFlowSearch._default_crossover(a, b)
        assert len(child.steps) == 2
        assert child.steps[0].action == "a1"
        assert child.steps[1].action == "b2"


# ======================================================================
# IdleSpecPlanner
# ======================================================================


class TestIdleSpecPlanner:
    """IdleSpecPlanner — speculative planning during idle time."""

    def test_generate_plan(self) -> None:
        """generate_plan returns a SpeculativePlan with steps."""
        planner = IdleSpecPlanner()
        plan = planner.generate_plan(
            current_state={"step": 1},
            context="analyzing results",
            horizon=3,
        )
        assert isinstance(plan, SpeculativePlan)
        assert len(plan.steps) == 3
        assert 0.0 <= plan.confidence <= 1.0

    def test_generate_batch(self) -> None:
        """generate_batch returns multiple plans."""
        planner = IdleSpecPlanner()
        plans = planner.generate_batch(
            current_state={"step": 1},
            context="testing",
            n_plans=3,
            horizon=2,
        )
        assert len(plans) == 3

    def test_cache_and_select_best_plan(self) -> None:
        """Cached plans can be retrieved by select_best_plan."""
        planner = IdleSpecPlanner()
        p1 = SpeculativePlan(
            steps=("step_a",),
            confidence=0.3,
            trigger_condition="",
            reasoning="low confidence",
        )
        p2 = SpeculativePlan(
            steps=("step_b",),
            confidence=0.9,
            trigger_condition="",
            reasoning="high confidence",
        )
        planner.cache_plan(p1)
        planner.cache_plan(p2)

        best = planner.select_best_plan()
        assert best is not None
        assert best.confidence == 0.9
        assert best.steps == ("step_b",)

    def test_select_best_plan_with_context_filter(self) -> None:
        """select_best_plan filters by trigger condition."""
        planner = IdleSpecPlanner()
        planner.cache_plan(SpeculativePlan(
            steps=("x",),
            confidence=0.8,
            trigger_condition="error_occurred",
            reasoning="recovery",
        ))
        planner.cache_plan(SpeculativePlan(
            steps=("y",),
            confidence=0.9,
            trigger_condition="analysis_complete",
            reasoning="next steps",
        ))

        best = planner.select_best_plan(context="error")
        assert best is not None
        assert best.trigger_condition == "error_occurred"

    def test_select_best_plan_empty(self) -> None:
        """select_best_plan returns None when no plans match."""
        planner = IdleSpecPlanner()
        assert planner.select_best_plan("anything") is None

    def test_clear_cache(self) -> None:
        """clear_cache empties the plan cache."""
        planner = IdleSpecPlanner()
        planner.cache_plan(SpeculativePlan(
            steps=("x",), confidence=0.5, trigger_condition="", reasoning="",
        ))
        assert planner.clear_cache() == 1
        assert planner.select_best_plan() is None

    def test_start_and_end_idle_cycle(self) -> None:
        """start and end idle cycle management."""
        planner = IdleSpecPlanner()
        cycle = planner.start_idle_cycle()
        assert cycle == 1
        count = planner.end_idle_cycle()
        assert count >= 0

    def test_capacity_limit(self) -> None:
        """Cache does not exceed max_cached_plans."""
        planner = IdleSpecPlanner(max_cached_plans=3)
        for i in range(5):
            planner.cache_plan(SpeculativePlan(
                steps=(f"s{i}",),
                confidence=float(i) / 5.0,
                trigger_condition="",
                reasoning="",
            ))
        assert len(planner.list_cached_plans()) <= 3
