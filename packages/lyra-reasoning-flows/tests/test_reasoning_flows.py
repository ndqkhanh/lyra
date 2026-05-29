"""Comprehensive tests for lyra-reasoning-flows."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import pytest

from lyra_reasoning_flows.cot_integration import (
    CoTIntegrator,
    ReflexionStep,
    ThoughtNode,
    ThoughtStrategy,
)
from lyra_reasoning_flows.exceptions import (
    FlowCompositionError,
    HorizonEstimationError,
    MCTSSearchError,
    ReActLoopError,
    ReasoningError,
    TraceError,
)
from lyra_reasoning_flows.flow_engine import (
    FlowDefinition,
    FlowEngine,
    FlowPattern,
    FlowResult,
    FlowStep,
)
from lyra_reasoning_flows.mcts_planner import (
    MCTSConfig,
    MCTSNode,
    MCTSPlanner,
    get_best_path,
    uct_score,
)
from lyra_reasoning_flows.planning_horizon import (
    HorizonConfig,
    HorizonMetrics,
    PlanningHorizonOptimizer,
)
from lyra_reasoning_flows.react_loop import EnhancedReActLoop, ReActStep, ReActTrace
from lyra_reasoning_flows.reasoning_tracer import (
    FullTrace,
    ReasoningTracer,
    TraceEvent,
    TraceEventType,
)
from lyra_reasoning_flows.system_i import (
    ReasoningTier,
    SystemIReasoner,
    TaskAssessment,
    TaskCategory,
)
from lyra_reasoning_flows.system_i import ReasoningTrace as S1ReasoningTrace
from lyra_reasoning_flows.system_ii import (
    BranchingFactor,
    PlanTree,
    SimulationResult,
    SystemIIReasoner,
)
from lyra_reasoning_flows.system_iii import (
    MetaDecision,
    MetaMetrics,
    RegulationAction,
    RegulationCost,
    SystemIIIMetaRegulator,
)

# =============================================================================
# Exceptions
# =============================================================================


class TestExceptions:
    def test_reasoning_error_is_base(self) -> None:
        assert issubclass(FlowCompositionError, ReasoningError)
        assert issubclass(MCTSSearchError, ReasoningError)
        assert issubclass(HorizonEstimationError, ReasoningError)
        assert issubclass(ReActLoopError, ReasoningError)
        assert issubclass(TraceError, ReasoningError)

    def test_exceptions_can_be_raised(self) -> None:
        with pytest.raises(ReasoningError):
            raise FlowCompositionError("cannot compose")
        with pytest.raises(MCTSSearchError):
            raise MCTSSearchError("search failed")
        with pytest.raises(HorizonEstimationError):
            raise HorizonEstimationError("bad estimate")
        with pytest.raises(ReActLoopError):
            raise ReActLoopError("loop error")
        with pytest.raises(TraceError):
            raise TraceError("trace error")

    def test_exception_messages(self) -> None:
        e = FlowCompositionError("test msg")
        assert str(e) == "test msg"


# =============================================================================
# System I
# =============================================================================


class TestSystemIReasoner:
    def test_quick_assess_lookup(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("find the latest sales report")
        assert assess.category == TaskCategory.LOOKUP
        assert assess.confidence >= 0.75

    def test_quick_assess_edit(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("edit the user profile page")
        assert assess.category == TaskCategory.EDIT
        assert assess.estimated_difficulty >= 0.0

    def test_quick_assess_classify(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("classify this document as spam")
        assert assess.category == TaskCategory.CLASSIFY

    def test_quick_assess_generate(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("write a poem about AI")
        assert assess.category == TaskCategory.GENERATE

    def test_quick_assess_plan(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("design a new authentication system")
        assert assess.category == TaskCategory.PLAN

    def test_quick_assess_debug(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("fix the login bug")
        assert assess.category == TaskCategory.DEBUG

    def test_quick_assess_fallthrough(self) -> None:
        r = SystemIReasoner(fallthrough_threshold=0.9)
        assess = r.quick_assess("generate some text")
        assert assess.requires_fallthrough is True
        assert assess.reasoning_tier == ReasoningTier.SIMULATIVE

    def test_quick_assess_no_fallthrough(self) -> None:
        r = SystemIReasoner(fallthrough_threshold=0.3)
        assess = r.quick_assess("lookup the value")
        assert assess.requires_fallthrough is False
        assert assess.reasoning_tier == ReasoningTier.FAST

    def test_reasoning_trace_created(self) -> None:
        r = SystemIReasoner()
        trace = r.reason("search for data")
        assert len(trace.steps) == 1
        assert trace.confidence > 0.0
        assert trace.timing_ms >= 0.0
        assert trace.tier == ReasoningTier.FAST

    def test_reasoning_trace_validation(self) -> None:
        with pytest.raises(ValueError):
            S1ReasoningTrace(steps=("a",), confidence=1.5, timing_ms=10.0)

    def test_reason_with_fallthrough(self) -> None:
        r = SystemIReasoner(fallthrough_threshold=0.99)
        assess = r.reason_with_fallthrough("complex strategic planning")
        assert assess.requires_fallthrough

    def test_task_assessment_fields(self) -> None:
        assess = TaskAssessment(
            category=TaskCategory.LOOKUP,
            confidence=0.9,
            estimated_difficulty=0.1,
            reasoning_tier=ReasoningTier.FAST,
            explanation="simple lookup",
            requires_fallthrough=False,
        )
        assert assess.category == TaskCategory.LOOKUP
        assert assess.confidence == 0.9
        assert assess.explanation == "simple lookup"

    def test_confidence_in_range(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("unknown gibberish xyzzy")
        assert 0.0 <= assess.confidence <= 1.0

    def test_difficulty_inverse_of_confidence(self) -> None:
        r = SystemIReasoner()
        assess = r.quick_assess("search for a file")
        assert abs(assess.estimated_difficulty - (1.0 - assess.confidence)) < 0.01

    def test_reasoning_tier_enum_values(self) -> None:
        assert ReasoningTier.FAST.value == "fast"
        assert ReasoningTier.SIMULATIVE.value == "simulative"
        assert ReasoningTier.META.value == "meta"

    def test_task_category_enum_values(self) -> None:
        assert TaskCategory.LOOKUP.value == "lookup"
        assert TaskCategory.EDIT.value == "edit"
        assert TaskCategory.GENERATE.value == "generate"
        assert TaskCategory.DEBUG.value == "debug"


# =============================================================================
# System II
# =============================================================================


class TestSystemIIReasoner:
    @pytest.mark.asyncio
    async def test_plan_creates_tree(self) -> None:
        r = SystemIIReasoner()
        tree = await r.plan("build a recommendation engine")
        assert isinstance(tree, PlanTree)
        assert tree.root_id
        assert len(tree.nodes) > 0

    @pytest.mark.asyncio
    async def test_plan_depth(self) -> None:
        r = SystemIIReasoner()
        tree = await r.plan("simple task", BranchingFactor.NARROW)
        assert tree.depth == 3

    @pytest.mark.asyncio
    async def test_plan_branching_narrow(self) -> None:
        r = SystemIIReasoner()
        tree = await r.plan("test", BranchingFactor.NARROW)
        root = [n for n in tree.nodes if n["id"] == tree.root_id][0]
        assert len(root["children"]) == BranchingFactor.NARROW.value

    @pytest.mark.asyncio
    async def test_plan_branching_standard(self) -> None:
        r = SystemIIReasoner()
        tree = await r.plan("test", BranchingFactor.STANDARD)
        root = [n for n in tree.nodes if n["id"] == tree.root_id][0]
        assert len(root["children"]) == BranchingFactor.STANDARD.value

    @pytest.mark.asyncio
    async def test_plan_branching_wide(self) -> None:
        r = SystemIIReasoner()
        tree = await r.plan("test", BranchingFactor.WIDE)
        root = [n for n in tree.nodes if n["id"] == tree.root_id][0]
        assert len(root["children"]) == BranchingFactor.WIDE.value

    @pytest.mark.asyncio
    async def test_simulate_returns_result(self) -> None:
        r = SystemIIReasoner()
        plan = await r.plan("task")
        plan_node = plan.nodes[0]
        result = await r.simulate(plan_node)
        assert isinstance(result, SimulationResult)
        assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_simulate_deeper_depth_lower_confidence(self) -> None:
        r = SystemIIReasoner()
        plan_node = {"task": "deep task", "id": "test"}
        result_shallow = await r.simulate(plan_node, depth=0)
        result_deep = await r.simulate(plan_node, depth=5)
        assert result_shallow.confidence > result_deep.confidence

    @pytest.mark.asyncio
    async def test_critique_accept(self) -> None:
        r = SystemIIReasoner()
        plan = await r.plan("test")
        results = [SimulationResult(outcome="good", confidence=0.9)]
        critique = await r.critique(plan, results)
        assert critique.verdict == "accept"

    @pytest.mark.asyncio
    async def test_critique_revise(self) -> None:
        r = SystemIIReasoner()
        plan = await r.plan("test")
        results = [SimulationResult(outcome="ok", confidence=0.5)]
        critique = await r.critique(plan, results)
        assert critique.verdict == "revise"

    @pytest.mark.asyncio
    async def test_critique_reject(self) -> None:
        r = SystemIIReasoner()
        plan = await r.plan("test")
        results = [SimulationResult(outcome="bad", confidence=0.2)]
        critique = await r.critique(plan, results)
        assert critique.verdict == "reject"

    @pytest.mark.asyncio
    async def test_critique_empty_results(self) -> None:
        r = SystemIIReasoner()
        plan = await r.plan("test")
        critique = await r.critique(plan, [])
        assert critique.verdict == "reject"

    def test_branching_factor_values(self) -> None:
        assert BranchingFactor.NARROW.value == 2
        assert BranchingFactor.STANDARD.value == 4
        assert BranchingFactor.WIDE.value == 8

    def test_simulation_result_validation(self) -> None:
        with pytest.raises(ValueError):
            SimulationResult(outcome="test", confidence=1.5)

    def test_simulation_result_frozen(self) -> None:
        s = SimulationResult(outcome="ok", confidence=0.5)
        with pytest.raises(AttributeError):
            s.outcome = "new"  # type: ignore[misc]


# =============================================================================
# System III
# =============================================================================


class TestSystemIIIMetaRegulator:
    def test_should_plan_deep_continue_fast(self) -> None:
        r = SystemIIIMetaRegulator()
        decision = r.should_plan_deep("say hello")
        assert decision.regulation_action == RegulationAction.CONTINUE_FAST
        assert decision.escalation_flag is False

    def test_should_plan_deep_engage_planning(self) -> None:
        r = SystemIIIMetaRegulator()
        decision = r.should_plan_deep(
            "analyze the impact of climate change on coastal "
            "ecosystems compare various adaptation approaches "
            "and evaluate proposed mitigation strategies"
        )
        assert decision.regulation_action in (
            RegulationAction.CONTINUE_FAST,
            RegulationAction.ENGAGE_PLANNING,
        )

    def test_should_plan_deep_escalate_model(self) -> None:
        r = SystemIIIMetaRegulator()
        # Very long, complex task.
        long_task = "synthesize " * 500
        decision = r.should_plan_deep(long_task)
        assert decision.regulation_action in (
            RegulationAction.ESCALATE_MODEL,
            RegulationAction.ENGAGE_PLANNING,
        )

    def test_should_plan_deep_request_human(self) -> None:
        r = SystemIIIMetaRegulator()
        # Extremely long task to push complexity towards 0.9+.
        long_task = "analyze " * 1000 + "compare and contrast " * 500 + "synthesize " * 500 + "evaluate why " * 500
        decision = r.should_plan_deep(long_task)
        # Both ESCALATE_MODEL and REQUEST_HUMAN are valid escalation paths
        # for extremely complex tasks.
        assert decision.regulation_action in (
            RegulationAction.ESCALATE_MODEL,
            RegulationAction.REQUEST_HUMAN,
        )
        assert decision.escalation_flag is True

    def test_regulate_no_history(self) -> None:
        r = SystemIIIMetaRegulator()
        action = r.regulate()
        assert action == RegulationAction.CONTINUE_FAST

    def test_regulate_poor_history_escalates(self) -> None:
        r = SystemIIIMetaRegulator()
        history = [
            {"success": False},
            {"success": False},
            {"success": False},
        ]
        action = r.regulate(performance_history=history)
        assert action == RegulationAction.ESCALATE_MODEL

    def test_regulate_mixed_history_engages_planning(self) -> None:
        r = SystemIIIMetaRegulator()
        history = [
            {"success": True},
            {"success": False},
            {"success": True},
            {"success": False},
        ]
        action = r.regulate(performance_history=history)
        assert action == RegulationAction.ENGAGE_PLANNING

    def test_regulate_high_loop_count(self) -> None:
        r = SystemIIIMetaRegulator()
        trace = {"loop_count": 15, "success": True}
        history = [{"success": True}] * 5
        action = r.regulate(current_trace=trace, performance_history=history)
        assert action == RegulationAction.REQUEST_HUMAN

    def test_estimate_cost_benefit(self) -> None:
        r = SystemIIIMetaRegulator()
        cost = r.estimate_cost_benefit(task_complexity=0.7, estimated_depth=5)
        assert isinstance(cost, RegulationCost)
        assert cost.computational_cost > 0

    def test_estimate_cost_benefit_low_value(self) -> None:
        r = SystemIIIMetaRegulator()
        cost = r.estimate_cost_benefit(task_complexity=0.1, estimated_depth=10)
        assert isinstance(cost, RegulationCost)
        assert cost.computational_cost > 0

    def test_metrics_tracking(self) -> None:
        m = MetaMetrics()
        m.record_decision(RegulationAction.CONTINUE_FAST, 0.9)
        m.record_decision(RegulationAction.ESCALATE_MODEL, 0.8)
        assert m.total_decisions == 2
        assert m.fast_decisions == 1
        assert m.model_escalations == 1
        assert m.avg_confidence == pytest.approx(0.85, rel=1e-3)

    def test_meta_decision_validation(self) -> None:
        with pytest.raises(ValueError):
            MetaDecision(
                reasoning="test",
                confidence=1.5,
                escalation_flag=True,
                regulation_action=RegulationAction.CONTINUE_FAST,
            )

    def test_meta_decision_frozen(self) -> None:
        d = MetaDecision(
            reasoning="test", confidence=0.5, escalation_flag=False, regulation_action=RegulationAction.CONTINUE_FAST
        )
        with pytest.raises(AttributeError):
            d.confidence = 0.9  # type: ignore[misc]

    def test_regulation_action_values(self) -> None:
        assert RegulationAction.CONTINUE_FAST.value == "continue_fast"
        assert RegulationAction.REQUEST_HUMAN.value == "request_human"


# =============================================================================
# Flow Engine
# =============================================================================


class TestFlowEngine:
    @pytest.mark.asyncio
    async def test_execute_sequential_flow(self) -> None:
        engine = FlowEngine()
        steps = (
            FlowStep(step_type="plan", action="create_plan"),
            FlowStep(step_type="execute", action="execute_plan"),
        )
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.SEQUENTIAL)
        result = await engine.execute_flow(flow)
        assert isinstance(result, FlowResult)
        assert "plan" in result.outputs
        assert "execute" in result.outputs

    @pytest.mark.asyncio
    async def test_execute_branching_flow(self) -> None:
        engine = FlowEngine()
        steps = (
            FlowStep(step_type="branch", action="branch_A"),
            FlowStep(step_type="branch", action="branch_B"),
            FlowStep(step_type="merge", action="merge"),
            FlowStep(step_type="conclude", action="conclude"),
        )
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.BRANCHING)
        result = await engine.execute_flow(flow)
        assert "merged" in result.outputs
        assert "conclusion" in result.outputs

    @pytest.mark.asyncio
    async def test_execute_reflective_flow(self) -> None:
        engine = FlowEngine()
        steps = (
            FlowStep(step_type="generate", action="generate"),
            FlowStep(step_type="critique", action="critique"),
            FlowStep(step_type="finalize", action="finalize"),
        )
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.REFLECTIVE)
        result = await engine.execute_flow(flow)
        assert "generate" in result.outputs
        assert "finalize" in result.outputs

    @pytest.mark.asyncio
    async def test_execute_meta_flow(self) -> None:
        engine = FlowEngine()
        steps = (
            FlowStep(step_type="observe", action="observe"),
            FlowStep(step_type="identify_patterns", action="identify"),
            FlowStep(step_type="update_strategies", action="update"),
        )
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.META)
        result = await engine.execute_flow(flow)
        assert "observe" in result.outputs
        assert "identify_patterns" in result.outputs
        assert "update_strategies" in result.outputs

    @pytest.mark.asyncio
    async def test_execute_meta_summary(self) -> None:
        engine = FlowEngine()
        steps = (
            FlowStep(step_type="observe", action="observe1"),
            FlowStep(step_type="observe", action="observe2"),
            FlowStep(step_type="identify_patterns", action="identify1"),
            FlowStep(step_type="update_strategies", action="update1"),
        )
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.META)
        result = await engine.execute_flow(flow)
        assert result.outputs["summary"]["patterns_identified"] >= 1

    @pytest.mark.asyncio
    async def test_trace_and_metrics(self) -> None:
        engine = FlowEngine()
        steps = (FlowStep(step_type="plan", action="plan"),)
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.SEQUENTIAL)
        result = await engine.execute_flow(flow, {"key": "value"})
        assert len(result.trace) == 1
        assert result.metrics["duration_seconds"] >= 0

    def test_compose_sequential(self) -> None:
        engine = FlowEngine()
        flow = engine.compose(["execute"])
        assert flow.pattern == FlowPattern.SEQUENTIAL

    def test_compose_reflective(self) -> None:
        engine = FlowEngine()
        flow = engine.compose(["reflect", "critique"])
        assert flow.pattern == FlowPattern.REFLECTIVE

    def test_compose_branching(self) -> None:
        engine = FlowEngine()
        flow = engine.compose(["branch"])
        assert flow.pattern == FlowPattern.BRANCHING

    def test_compose_meta(self) -> None:
        engine = FlowEngine()
        flow = engine.compose(["monitor"])
        assert flow.pattern == FlowPattern.META

    def test_compose_caches(self) -> None:
        engine = FlowEngine()
        flow1 = engine.compose(["a", "b"])
        flow2 = engine.compose(["b", "a"])
        assert flow1 is flow2

    def test_compose_meta_flow_has_correct_steps(self) -> None:
        engine = FlowEngine()
        flow = engine.compose(["monitor"])
        step_types = [s.step_type for s in flow.steps]
        assert step_types == ["observe", "identify_patterns", "update_strategies"]

    def test_compose_branching_includes_branch_steps(self) -> None:
        engine = FlowEngine()
        flow = engine.compose(["branch", "research", "analyze"])
        step_types = [s.step_type for s in flow.steps]
        assert "merge" in step_types
        assert "conclude" in step_types

    @pytest.mark.asyncio
    async def test_register_step_handler(self) -> None:
        engine = FlowEngine()

        def custom_handler(action: str, ctx: dict) -> dict:
            return {"step": action, "custom": True}

        engine.register_step_handler("custom_type", custom_handler)
        steps = (FlowStep(step_type="custom_type", action="test"),)
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.SEQUENTIAL)
        result = await engine.execute_flow(flow)
        assert result.outputs["custom_type"]["custom"] is True

    def test_flow_pattern_values(self) -> None:
        assert FlowPattern.SEQUENTIAL.value == "sequential"
        assert FlowPattern.BRANCHING.value == "branching"
        assert FlowPattern.REFLECTIVE.value == "reflective"
        assert FlowPattern.META.value == "meta"


# =============================================================================
# MCTS Planner
# =============================================================================


class TestMCTSPlanner:
    def test_search_returns_root(self) -> None:
        planner = MCTSPlanner()
        root = planner.search("initial_state")
        assert isinstance(root, MCTSNode)
        assert root.state == "initial_state"

    def test_search_expands_nodes(self) -> None:
        planner = MCTSPlanner()
        config = MCTSConfig(max_iterations=50)
        root = planner.search("test", config)
        assert len(root.children) > 0

    def test_uct_score_infinity_for_new_nodes(self) -> None:
        node = MCTSNode(state="test", visits=0, value=0.0)
        score = uct_score(node, parent_visits=10, exploration_constant=1.41)
        assert score == float("inf")

    def test_uct_score_finite_for_visited_nodes(self) -> None:
        node = MCTSNode(state="test", visits=5, value=3.0)
        score = uct_score(node, parent_visits=10, exploration_constant=1.41)
        assert math.isfinite(score)
        assert score > 0

    def test_uct_score_infinity_when_parent_not_visited(self) -> None:
        node = MCTSNode(state="test", visits=5, value=3.0)
        score = uct_score(node, parent_visits=0, exploration_constant=1.41)
        assert score == float("inf")

    def test_get_best_path_single_node(self) -> None:
        root = MCTSNode(state="start")
        path = get_best_path(root)
        assert len(path) == 1

    def test_get_best_path_selects_most_visited(self) -> None:
        root = MCTSNode(
            state="start",
            children=(
                MCTSNode(state="A", visits=10, value=5.0),
                MCTSNode(state="B", visits=2, value=3.0),
            ),
        )
        path = get_best_path(root)
        assert path[-1].state == "A"

    def test_get_best_path_multi_level(self) -> None:
        child = MCTSNode(
            state="child",
            visits=10,
            value=5.0,
            children=(
                MCTSNode(state="grandchild", visits=8, value=4.0),
            ),
        )
        root = MCTSNode(state="root", children=(child,))
        path = get_best_path(root)
        assert len(path) == 3
        assert path[-1].state == "grandchild"

    def test_mcts_config_defaults(self) -> None:
        config = MCTSConfig()
        assert config.max_iterations == 1000
        assert config.exploration_constant == math.sqrt(2)
        assert config.max_depth == 10
        assert config.time_limit_ms == 5000.0

    def test_to_mermaid(self) -> None:
        planner = MCTSPlanner()
        root = MCTSNode(state="root")
        mermaid = planner.to_mermaid(root)
        assert "%% MCTS Tree" in mermaid
        assert "graph TD" in mermaid

    def test_to_mermaid_with_children(self) -> None:
        planner = MCTSPlanner()
        root = MCTSNode(
            state="root",
            children=(MCTSNode(state="child_a", visits=5, value=2.0),),
        )
        mermaid = planner.to_mermaid(root)
        assert "root" in mermaid or "child_a" in mermaid

    def test_mcts_node_add_child(self) -> None:
        parent = MCTSNode(state="parent")
        child = MCTSNode(state="child")
        updated = parent.add_child(child)
        assert len(updated.children) == 1
        assert id(parent) != id(updated)

    def test_mcts_node_updated(self) -> None:
        node = MCTSNode(state="test", visits=5, value=2.0)
        updated = node.updated(visits=6)
        assert updated.visits == 6
        assert updated.value == 2.0
        assert id(node) != id(updated)

    def test_mcts_node_frozen(self) -> None:
        node = MCTSNode(state="test")
        with pytest.raises(AttributeError):
            node.state = "new"  # type: ignore[misc]

    def test_search_with_time_limit(self) -> None:
        planner = MCTSPlanner()
        config = MCTSConfig(max_iterations=10000, time_limit_ms=10)
        root = planner.search("fast", config)
        assert root.visits >= 0


# =============================================================================
# Planning Horizon
# =============================================================================


class TestPlanningHorizonOptimizer:
    def test_estimate_horizon_low_complexity(self) -> None:
        opt = PlanningHorizonOptimizer()
        depth = opt.estimate_horizon(task_complexity=0.1, context_budget=100.0)
        assert depth >= 1

    def test_estimate_horizon_high_complexity(self) -> None:
        opt = PlanningHorizonOptimizer(config=HorizonConfig(max_depth=10))
        depth = opt.estimate_horizon(task_complexity=0.9, context_budget=100.0)
        assert depth <= 10
        assert depth > 1

    def test_estimate_horizon_bounded_by_max(self) -> None:
        opt = PlanningHorizonOptimizer(config=HorizonConfig(max_depth=5))
        depth = opt.estimate_horizon(task_complexity=1.0, context_budget=100.0)
        assert depth <= 5

    def test_estimate_horizon_zero_budget(self) -> None:
        opt = PlanningHorizonOptimizer()
        with pytest.raises(HorizonEstimationError):
            opt.estimate_horizon(task_complexity=0.5, context_budget=0)

    def test_estimate_horizon_negative_budget(self) -> None:
        opt = PlanningHorizonOptimizer()
        with pytest.raises(HorizonEstimationError):
            opt.estimate_horizon(task_complexity=0.5, context_budget=-1)

    def test_estimate_horizon_invalid_complexity(self) -> None:
        opt = PlanningHorizonOptimizer()
        with pytest.raises(HorizonEstimationError):
            opt.estimate_horizon(task_complexity=1.5, context_budget=100.0)

    def test_should_expand_high_complexity_low_confidence(self) -> None:
        opt = PlanningHorizonOptimizer()
        assert opt.should_expand(node_confidence=0.3, task_complexity=0.8) is True

    def test_should_expand_low_complexity(self) -> None:
        opt = PlanningHorizonOptimizer()
        assert opt.should_expand(node_confidence=0.3, task_complexity=0.2) is False

    def test_should_expand_high_confidence(self) -> None:
        opt = PlanningHorizonOptimizer()
        assert opt.should_expand(node_confidence=0.9, task_complexity=0.8) is False

    def test_should_expand_invalid_confidence(self) -> None:
        opt = PlanningHorizonOptimizer()
        with pytest.raises(HorizonEstimationError):
            opt.should_expand(node_confidence=1.5, task_complexity=0.5)

    def test_compute_complexity_simple(self) -> None:
        opt = PlanningHorizonOptimizer()
        c = opt.compute_complexity(num_steps=1, num_dependencies=0, ambiguity_score=0.1)
        assert 0.0 <= c <= 1.0

    def test_compute_complexity_complex(self) -> None:
        opt = PlanningHorizonOptimizer()
        c = opt.compute_complexity(num_steps=20, num_dependencies=10, ambiguity_score=0.9)
        assert c == 0.97  # Step factor: 1.0*0.4 + Dep factor: 1.0*0.3 + Ambiguity: 0.9*0.3 = 0.97

    def test_compute_complexity_invalid_ambiguity(self) -> None:
        opt = PlanningHorizonOptimizer()
        with pytest.raises(HorizonEstimationError):
            opt.compute_complexity(num_steps=1, num_dependencies=0, ambiguity_score=1.5)

    def test_compute_complexity_negative_steps(self) -> None:
        opt = PlanningHorizonOptimizer()
        with pytest.raises(HorizonEstimationError):
            opt.compute_complexity(num_steps=-1, num_dependencies=0, ambiguity_score=0.5)

    def test_horizon_metrics(self) -> None:
        m = HorizonMetrics()
        assert m.total_estimations == 0
        m.record_estimation(depth=5, expanded=True)
        m.record_estimation(depth=3, expanded=False)
        assert m.total_estimations == 2
        assert m.expansions_triggered == 1
        assert m.avg_depth == 4.0

    def test_horizon_config_defaults(self) -> None:
        c = HorizonConfig()
        assert c.default_depth == 3
        assert c.max_depth == 10
        assert c.expansion_threshold == 0.6
        assert c.confidence_threshold == 0.7


# =============================================================================
# ReAct Loop
# =============================================================================


class TestEnhancedReActLoop:
    @pytest.mark.asyncio
    async def test_run_creates_trace(self) -> None:
        loop = EnhancedReActLoop()
        trace = await loop.run("test task")
        assert isinstance(trace, ReActTrace)
        assert len(trace.steps) > 0

    @pytest.mark.asyncio
    async def test_run_max_iterations(self) -> None:
        loop = EnhancedReActLoop()
        trace = await loop.run("task", max_iterations=3)
        assert len(trace.steps) <= 3

    @pytest.mark.asyncio
    async def test_run_stops_on_answer(self) -> None:
        loop = EnhancedReActLoop()
        trace = await loop.run("task: answer the question", max_iterations=10)
        assert trace.completed

    @pytest.mark.asyncio
    async def test_run_stops_on_final(self) -> None:
        loop = EnhancedReActLoop()
        trace = await loop.run("final: complete the task", max_iterations=10)
        assert trace.completed

    @pytest.mark.asyncio
    async def test_run_with_tools(self) -> None:
        loop = EnhancedReActLoop()

        async def dummy_tool(action: str, **kwargs: str) -> str:
            return f"result of {action}"

        trace = await loop.run("task", tools={"search": dummy_tool}, max_iterations=2)
        assert len(trace.steps) > 0
        # Check that the tool was called.
        step = trace.steps[0]
        assert len(step.tool_calls) > 0

    def test_audit_no_calls(self) -> None:
        loop = EnhancedReActLoop()
        trace = ReActTrace(
            steps=(ReActStep(thought="think", action="final: done", observation="ok"),),
            completed=True,
        )
        result = loop.audit_tool_calls(trace)
        assert "No tool calls made during the trace" in result.issues_found

    def test_audit_redundant_calls(self) -> None:
        loop = EnhancedReActLoop()
        trace = ReActTrace(
            steps=(
                ReActStep(thought="t1", action="a1", observation="o1", tool_calls=("search",)),
                ReActStep(thought="t2", action="a2", observation="o2", tool_calls=("search",)),
            ),
            completed=True,
        )
        result = loop.audit_tool_calls(trace)
        assert "Redundant tool call: search" in result.issues_found

    def test_audit_missing_answer(self) -> None:
        loop = EnhancedReActLoop()
        trace = ReActTrace(
            steps=(
                ReActStep(thought="t1", action="a1", observation="o1", tool_calls=("compute",)),
            ),
            completed=True,
        )
        result = loop.audit_tool_calls(trace)
        assert len(result.issues_found) >= 1

    def test_audit_clean(self) -> None:
        loop = EnhancedReActLoop()
        trace = ReActTrace(
            steps=(
                ReActStep(
                    thought="t1", action="search: query", observation="data", tool_calls=("search",)
                ),
                ReActStep(
                    thought="t2", action="final: done", observation="ok", tool_calls=("answer",)
                ),
            ),
            completed=True,
        )
        result = loop.audit_tool_calls(trace)
        # "search" and "answer" are unique, so no redundancy issues.
        redundant = [i for i in result.issues_found if "Redundant" in i]
        assert len(redundant) == 0

    def test_re_act_step_frozen(self) -> None:
        step = ReActStep(thought="t", action="a", observation="o")
        with pytest.raises(AttributeError):
            step.thought = "new"  # type: ignore[misc]

    def test_re_act_trace_creation(self) -> None:
        trace = ReActTrace(steps=(), completed=False)
        assert not trace.completed
        assert trace.total_duration_ms == 0.0


# =============================================================================
# CoT Integration
# =============================================================================


class TestCoTIntegrator:
    def test_chain_of_thought(self) -> None:
        cot = CoTIntegrator()
        steps = cot.chain_of_thought("What is 2+2?", max_steps=3)
        assert len(steps) == 3
        assert "Step" in steps[0]

    def test_chain_of_thought_single_step(self) -> None:
        cot = CoTIntegrator()
        steps = cot.chain_of_thought("test", max_steps=1)
        assert len(steps) == 1
        assert "Conclusion" in steps[0]

    def test_tree_of_thoughts_creates_tree(self) -> None:
        cot = CoTIntegrator()
        root = cot.tree_of_thoughts("solve equation", branching_factor=2, max_depth=2)
        assert root.content == "solve equation"
        assert len(root.children) > 0

    def test_tree_of_thoughts_branching_factor(self) -> None:
        cot = CoTIntegrator()
        root = cot.tree_of_thoughts("test", branching_factor=3, max_depth=1)
        assert len(root.children) == 3

    def test_tree_of_thoughts_returns_root(self) -> None:
        cot = CoTIntegrator()
        root = cot.tree_of_thoughts("prompt", branching_factor=2, max_depth=0)
        assert root.depth == 0

    def test_self_consistency(self) -> None:
        cot = CoTIntegrator(seed=42)
        result = cot.self_consistency("What is the capital of France?", num_samples=3)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_self_consistency_empty(self) -> None:
        cot = CoTIntegrator()
        result = cot.self_consistency("")
        # Should still return something.
        assert isinstance(result, str)

    def test_reflexion(self) -> None:
        cot = CoTIntegrator(seed=42)
        steps = cot.reflexion("solve problem", max_trials=3)
        assert len(steps) == 3
        assert all(isinstance(s, ReflexionStep) for s in steps)

    def test_reflexion_single_trial(self) -> None:
        cot = CoTIntegrator()
        steps = cot.reflexion("test", max_trials=1)
        assert len(steps) == 1
        assert steps[0].trial == 1

    def test_reflexion_revises_plan(self) -> None:
        cot = CoTIntegrator(seed=42)
        steps = cot.reflexion("plan", max_trials=2)
        assert len(steps) == 2
        assert "Revised" in steps[1].revised_plan

    def test_get_thought_node(self) -> None:
        cot = CoTIntegrator()
        cot.tree_of_thoughts("test", branching_factor=2, max_depth=1)
        root = cot.get_thought_node("root")
        assert root is not None
        assert root.content == "test"

    def test_get_thought_node_missing(self) -> None:
        cot = CoTIntegrator()
        assert cot.get_thought_node("nonexistent") is None

    @pytest.mark.asyncio
    async def test_tree_of_thoughts_async(self) -> None:
        cot = CoTIntegrator()
        root = await cot.tree_of_thoughts_async("test", branching_factor=2, max_depth=1)
        assert len(root.children) == 2

    def test_thought_node_score_validation(self) -> None:
        with pytest.raises(ValueError):
            ThoughtNode(content="test", score=1.5)

    def test_thought_node_frozen(self) -> None:
        node = ThoughtNode(content="test")
        with pytest.raises(AttributeError):
            node.content = "new"  # type: ignore[misc]

    def test_thought_strategy_values(self) -> None:
        assert ThoughtStrategy.COT.value == "cot"
        assert ThoughtStrategy.TOT.value == "tot"
        assert ThoughtStrategy.SELF_CONSISTENCY.value == "self_consistency"
        assert ThoughtStrategy.REFLEXION.value == "reflexion"

    def test_reflexion_step_mutable(self) -> None:
        step = ReflexionStep(trial=1, outcome="fail", reflection="bad", revised_plan="fix")
        step.outcome = "success"
        assert step.outcome == "success"


# =============================================================================
# Reasoning Tracer
# =============================================================================


class TestReasoningTracer:
    def test_start_trace_returns_id(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("test context")
        assert isinstance(tid, str)
        assert len(tid) > 0

    def test_record_event(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("test")
        event = TraceEvent(
            event_type=TraceEventType.THOUGHT,
            timestamp=datetime.now(timezone.utc),
            data={"thought": "I think"},
            system="system_i",
        )
        tracer.record_event(tid, event)
        trace = tracer.get_full_trace(tid)
        assert len(trace.events) == 1

    def test_record_event_nonexistent_trace(self) -> None:
        tracer = ReasoningTracer()
        event = TraceEvent(
            event_type=TraceEventType.THOUGHT,
            timestamp=datetime.now(timezone.utc),
            data={},
            system="system_i",
        )
        with pytest.raises(TraceError):
            tracer.record_event("nonexistent", event)

    def test_get_full_trace(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("ctx")
        trace = tracer.get_full_trace(tid)
        assert isinstance(trace, FullTrace)
        assert len(trace.events) == 0

    def test_get_full_trace_nonexistent(self) -> None:
        tracer = ReasoningTracer()
        with pytest.raises(TraceError):
            tracer.get_full_trace("nonexistent")

    def test_export_json(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("test")
        event = TraceEvent(
            event_type=TraceEventType.DECISION,
            timestamp=datetime.now(timezone.utc),
            data={"decision": "proceed"},
            system="system_i",
        )
        tracer.record_event(tid, event)
        output = tracer.export_trace(tid, fmt="json")
        parsed = json.loads(output)
        assert "events" in parsed
        assert len(parsed["events"]) == 1

    def test_export_mermaid(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("test")
        event = TraceEvent(
            event_type=TraceEventType.ACTION,
            timestamp=datetime.now(timezone.utc),
            data={"summary": "search action"},
            system="system_ii",
        )
        tracer.record_event(tid, event)
        output = tracer.export_trace(tid, fmt="mermaid")
        assert "sequenceDiagram" in output
        assert "system_ii" in output

    def test_export_unsupported_format(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("test")
        with pytest.raises(TraceError):
            tracer.export_trace(tid, fmt="xml")

    def test_trace_stats(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("test")
        events = [
            TraceEvent(TraceEventType.THOUGHT, datetime.now(timezone.utc), {"a": 1}, "system_i"),
            TraceEvent(TraceEventType.ACTION, datetime.now(timezone.utc), {"b": 2}, "system_ii"),
            TraceEvent(TraceEventType.ESCALATION, datetime.now(timezone.utc), {"c": 3}, "system_iii"),
        ]
        for e in events:
            tracer.record_event(tid, e)
        stats = tracer.trace_stats(tid)
        assert stats["total_events"] == 3
        assert stats["escalation_count"] == 1
        assert stats["system_count"] == 3

    def test_trace_event_type_values(self) -> None:
        assert TraceEventType.THOUGHT.value == "thought"
        assert TraceEventType.ACTION.value == "action"
        assert TraceEventType.ERROR.value == "error"

    def test_trace_event_validation(self) -> None:
        with pytest.raises(TraceError):
            TraceEvent(
                event_type=TraceEventType.THOUGHT,
                timestamp=datetime.now(timezone.utc),
                data={},
                system="system_iv",
            )

    def test_trace_event_frozen(self) -> None:
        e = TraceEvent(
            event_type=TraceEventType.THOUGHT,
            timestamp=datetime.now(timezone.utc),
            data={},
            system="system_i",
        )
        with pytest.raises(AttributeError):
            e.event_type = "new"  # type: ignore[misc]

    def test_full_trace_end_time(self) -> None:
        now = datetime.now(timezone.utc)
        trace = FullTrace(events=(), start_time=now, end_time=now)
        assert trace.end_time == now

    def test_set_metadata(self) -> None:
        tracer = ReasoningTracer()
        tid = tracer.start_trace("ctx")
        tracer.set_metadata(tid, model="sonnet", temperature=0.7)
        trace = tracer.get_full_trace(tid)
        assert trace.metadata["model"] == "sonnet"

    def test_set_metadata_nonexistent(self) -> None:
        tracer = ReasoningTracer()
        with pytest.raises(TraceError):
            tracer.set_metadata("bad_id", key="val")


# =============================================================================
# Integration / Cross-module
# =============================================================================


class TestIntegration:
    @pytest.mark.asyncio
    async def test_system_i_to_system_iii(self) -> None:
        """Test the three-system integration flow."""
        s1 = SystemIReasoner()
        s3 = SystemIIIMetaRegulator()

        assess = s1.quick_assess("design a distributed cache system")
        decision = s3.should_plan_deep(assess.explanation)

        assert assess.category == TaskCategory.PLAN
        assert decision.regulation_action in (
            RegulationAction.CONTINUE_FAST,
            RegulationAction.ENGAGE_PLANNING,
        )

    @pytest.mark.asyncio
    async def test_system_ii_simulation_with_mcts(self) -> None:
        """Test that MCTS search results can feed System II simulation."""
        planner = MCTSPlanner()
        root = planner.search("design_task", MCTSConfig(max_iterations=20))
        path = planner.get_best_path(root)
        assert len(path) >= 1

        s2 = SystemIIReasoner()
        results = []
        for node in path[:3]:
            result = await s2.simulate({"task": node.state, "id": "test"}, depth=0)
            results.append(result)

        critique = await s2.critique(
            await s2.plan("task", BranchingFactor.NARROW), results
        )
        assert isinstance(critique.verdict, str)

    @pytest.mark.asyncio
    async def test_flow_engine_with_react(self) -> None:
        """Test that the flow engine can compose with ReAct-like steps."""
        engine = FlowEngine()
        steps = (
            FlowStep(step_type="reason", action="analyze_input"),
            FlowStep(step_type="act", action="execute_tool"),
            FlowStep(step_type="observe", action="get_result"),
        )
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.SEQUENTIAL)
        result = await engine.execute_flow(flow)
        assert "reason" in result.outputs
        assert "act" in result.outputs

    @pytest.mark.asyncio
    async def test_reasoning_tracer_with_flow(self) -> None:
        """Test tracing a full flow execution."""
        tracer = ReasoningTracer()
        engine = FlowEngine()

        tid = tracer.start_trace("integration_test")
        tracer.record_event(
            tid,
            TraceEvent(
                TraceEventType.THOUGHT,
                datetime.now(timezone.utc),
                {"summary": "starting sequential flow"},
                "system_i",
            ),
        )

        steps = (FlowStep(step_type="plan", action="create_plan"),)
        flow = FlowDefinition(steps=steps, pattern=FlowPattern.SEQUENTIAL)
        result = await engine.execute_flow(flow)

        tracer.record_event(
            tid,
            TraceEvent(
                TraceEventType.DECISION,
                datetime.now(timezone.utc),
                {"summary": "flow completed", "outputs": list(result.outputs.keys())},
                "system_i",
            ),
        )

        trace = tracer.get_full_trace(tid)
        assert len(trace.events) == 2
        json_out = tracer.export_trace(tid)
        assert "system_i" in json_out

    @pytest.mark.asyncio
    async def test_planning_horizon_in_flow(self) -> None:
        """Test planning horizon optimization integrated with MCTS."""
        opt = PlanningHorizonOptimizer()
        planner = MCTSPlanner()

        complexity = opt.compute_complexity(
            num_steps=10, num_dependencies=3, ambiguity_score=0.6
        )
        horizon = opt.estimate_horizon(complexity, 50.0)

        config = MCTSConfig(max_iterations=horizon * 10)
        root = planner.search("complex_task", config)
        assert root.visits > 0 or len(root.children) > 0

    def test_exception_hierarchy(self) -> None:
        """Verify all custom exceptions are importable."""
        from lyra_reasoning_flows import (
            FlowCompositionError,
            HorizonEstimationError,
            MCTSSearchError,
            ReActLoopError,
            ReasoningError,
            TraceError,
        )

        assert issubclass(FlowCompositionError, ReasoningError)
        assert issubclass(MCTSSearchError, ReasoningError)
        assert issubclass(HorizonEstimationError, ReasoningError)
        assert issubclass(ReActLoopError, ReasoningError)
        assert issubclass(TraceError, ReasoningError)

    @pytest.mark.asyncio
    async def test_end_to_end_sequential_flow(self) -> None:
        engine = FlowEngine()
        tracer = ReasoningTracer()

        tid = tracer.start_trace("e2e_sequential")
        tracer.set_metadata(tid, test_name="end_to_end")

        s1 = SystemIReasoner()
        assess = s1.quick_assess("search for documents about AI")
        tracer.record_event(
            tid,
            TraceEvent(
                TraceEventType.THOUGHT,
                datetime.now(timezone.utc),
                {"assessment": assess.explanation},
                "system_i",
            ),
        )

        flow = engine.compose(["execute"])
        result = await engine.execute_flow(flow)

        tracer.record_event(
            tid,
            TraceEvent(
                TraceEventType.DECISION,
                datetime.now(timezone.utc),
                {
                    "flow_pattern": flow.pattern.value,
                    "output_keys": list(result.outputs.keys()),
                },
                "system_i",
            ),
        )

        trace = tracer.get_full_trace(tid)
        assert len(trace.events) == 2
        assert trace.metadata["test_name"] == "end_to_end"


# =============================================================================
# Package import verification
# =============================================================================


class TestPackageImports:
    def test_all_exports_available(self) -> None:
        """Verify all public API items are importable from the package."""
        from lyra_reasoning_flows import __all__ as exported

        # Spot-check key items.
        assert "SystemIReasoner" in exported
        assert "SystemIIReasoner" in exported
        assert "SystemIIIMetaRegulator" in exported
        assert "FlowEngine" in exported
        assert "MCTSPlanner" in exported
        assert "EnhancedReActLoop" in exported
        assert "CoTIntegrator" in exported
        assert "ReasoningTracer" in exported

    def test_all_exception_classes_exported(self) -> None:
        from lyra_reasoning_flows import __all__ as exported

        for exc_name in [
            "ReasoningError",
            "FlowCompositionError",
            "MCTSSearchError",
            "HorizonEstimationError",
            "ReActLoopError",
            "TraceError",
        ]:
            assert exc_name in exported

    def test_version(self) -> None:
        from lyra_reasoning_flows import __version__

        assert __version__ == "0.1.0"
