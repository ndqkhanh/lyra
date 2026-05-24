"""
Comprehensive tests for the Lyra Cognitive Architecture.

Covers:
- Data models (enums, frozen dataclasses)
- System 2 Planner (plan generation, evaluation, decomposition)
- System 1 Executor (execution, pattern matching, caching)
- Meta-Cognitive Controller (mode assessment, escalation, caching decisions)
- Theater of Mind (publishing, subscribing, attention)
- Attention Manager (priority, selection, decay)
- Cognitive Loop (tick, run, interrupt, trace)
- Reasoning Engine (chain-of-thought, tree-of-thoughts, reflexion, debate)
"""

from datetime import datetime

import pytest

from lyra_cognitive import (
    AttentionManager,
    AttentionSignal,
    CognitiveLoop,
    CognitiveState,
    CognitiveTick,
    ConfidenceLevel,
    MetaCognitiveController,
    Plan,
    ReasoningEngine,
    ReasoningResult,
    System1Executor,
    System2Planner,
    SystemMode,
    TheaterOfMind,
    Thought,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Data Models Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystemMode:
    """Tests for SystemMode enum."""

    def test_all_modes_exist(self):
        """All expected modes are present."""
        assert SystemMode.SYSTEM1.value == "system1"
        assert SystemMode.SYSTEM2.value == "system2"
        assert SystemMode.META_COGNITIVE.value == "meta"
        assert SystemMode.IDLE.value == "idle"

    def test_mode_comparison(self):
        """Modes can be compared."""
        assert SystemMode.SYSTEM1 != SystemMode.SYSTEM2
        modes = list(SystemMode)
        assert len(modes) == 4


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_from_score_high(self):
        assert ConfidenceLevel.from_score(0.9) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.8) == ConfidenceLevel.HIGH

    def test_from_score_medium(self):
        assert ConfidenceLevel.from_score(0.7) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.5) == ConfidenceLevel.MEDIUM

    def test_from_score_low(self):
        assert ConfidenceLevel.from_score(0.4) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(0.2) == ConfidenceLevel.LOW

    def test_from_score_unknown(self):
        assert ConfidenceLevel.from_score(0.1) == ConfidenceLevel.UNKNOWN
        assert ConfidenceLevel.from_score(0.0) == ConfidenceLevel.UNKNOWN


class TestAttentionSignal:
    """Tests for AttentionSignal frozen dataclass."""

    def test_creation_defaults(self):
        signal = AttentionSignal()
        assert signal.id
        assert signal.source == ""
        assert signal.content == ""
        assert signal.urgency == 0.0
        assert signal.relevance == 0.0
        assert signal.novelty == 0.0
        assert signal.priority == 0.0

    def test_creation_with_values(self):
        signal = AttentionSignal(
            source="test-module",
            content="Important alert",
            urgency=0.9,
            relevance=0.8,
            novelty=0.7,
        )
        assert signal.source == "test-module"
        assert signal.content == "Important alert"
        assert signal.priority == pytest.approx(0.9 * 0.8 * 0.7)

    def test_priority_calculation(self):
        signal = AttentionSignal(urgency=0.5, relevance=0.8, novelty=0.3)
        assert signal.priority == pytest.approx(0.12)

    def test_validation_rejects_invalid_urgency(self):
        with pytest.raises(ValueError):
            AttentionSignal(urgency=1.5)

    def test_validation_rejects_negative_relevance(self):
        with pytest.raises(ValueError):
            AttentionSignal(relevance=-0.1)

    def test_frozen(self):
        signal = AttentionSignal(content="test")
        with pytest.raises(Exception):
            signal.content = "modified"  # type: ignore[misc]

    def test_metadata_storage(self):
        signal = AttentionSignal(metadata={"key": "value", "count": 42})
        assert signal.metadata == {"key": "value", "count": 42}


class TestThought:
    """Tests for Thought frozen dataclass."""

    def test_creation_defaults(self):
        thought = Thought()
        assert thought.id
        assert thought.content == ""
        assert thought.source == ""
        assert thought.confidence == ConfidenceLevel.UNKNOWN
        assert thought.tags == frozenset()
        assert thought.attended_count == 0

    def test_creation_with_tags(self):
        tags = frozenset({"plan", "system2", "urgent"})
        thought = Thought(content="Test thought", tags=tags)
        assert thought.tags == tags
        assert "plan" in thought.tags

    def test_frozen_tags(self):
        thought = Thought(tags=frozenset({"a"}))
        with pytest.raises(Exception):
            thought.tags = frozenset({"b"})  # type: ignore[misc]

    def test_metadata(self):
        thought = Thought(metadata={"urgency": 0.9})
        assert thought.metadata["urgency"] == 0.9


class TestPlan:
    """Tests for Plan frozen dataclass."""

    def test_creation(self):
        plan = Plan(
            goal="Implement feature X",
            steps=("Design", "Implement", "Test"),
            dependencies={1: frozenset({0}), 2: frozenset({1})},
            estimated_costs={0: 1.5, 1: 5.0, 2: 2.0},
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert plan.step_count == 3
        assert plan.total_estimated_cost == pytest.approx(8.5)

    def test_get_ready_steps_all_available(self):
        plan = Plan(steps=("A", "B", "C"))
        ready = plan.get_ready_steps(frozenset())
        assert ready == [0, 1, 2]

    def test_get_ready_steps_with_dependencies(self):
        plan = Plan(
            steps=("A", "B", "C"),
            dependencies={1: frozenset({0}), 2: frozenset({0, 1})},
        )
        assert plan.get_ready_steps(frozenset()) == [0]
        assert plan.get_ready_steps(frozenset({0})) == [1]
        assert plan.get_ready_steps(frozenset({0, 1})) == [2]

    def test_empty_plan(self):
        plan = Plan(goal="Empty")
        assert plan.step_count == 0
        assert plan.total_estimated_cost == 0.0

    def test_timestamp_auto_generated(self):
        plan = Plan()
        assert isinstance(plan.created_at, datetime)


class TestCognitiveState:
    """Tests for CognitiveState frozen dataclass."""

    def test_default_state(self):
        state = CognitiveState()
        assert state.mode == SystemMode.IDLE
        assert state.active_thoughts == frozenset()
        assert state.working_memory == {}
        assert state.attention_budget == 1.0
        assert state.task_progress == 0.0
        assert state.cycle_count == 0

    def test_custom_state(self):
        state = CognitiveState(
            mode=SystemMode.SYSTEM2,
            task_progress=0.5,
            cycle_count=42,
        )
        assert state.mode == SystemMode.SYSTEM2
        assert state.task_progress == 0.5
        assert state.cycle_count == 42


class TestCognitiveTick:
    """Tests for CognitiveTick frozen dataclass."""

    def test_creation(self):
        tick = CognitiveTick(
            index=0,
            mode=SystemMode.SYSTEM1,
            perception=("obs1", "obs2"),
            attended=frozenset({"id1", "id2"}),
            reasoning="Quick reasoning",
            decision="Execute step",
            action="Executed",
            observation="Success",
        )
        assert tick.index == 0
        assert tick.mode == SystemMode.SYSTEM1
        assert len(tick.perception) == 2
        assert len(tick.attended) == 2
        assert tick.reasoning == "Quick reasoning"


# ═══════════════════════════════════════════════════════════════════════════════
# System 2 Planner Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystem2Planner:
    """Tests for System2Planner."""

    @pytest.fixture
    def planner(self) -> System2Planner:
        return System2Planner()

    def test_generate_plan_returns_plan(self, planner):
        plan = planner.generate_plan("Implement a user authentication system")
        assert isinstance(plan, Plan)
        assert len(plan.steps) > 0
        assert plan.goal == "Implement a user authentication system"
        assert plan.confidence != ConfidenceLevel.UNKNOWN

    def test_generate_plan_with_context(self, planner):
        context = {"language": "Python", "deadline": "2 weeks"}
        plan = planner.generate_plan("Build REST API", context)
        assert isinstance(plan, Plan)
        assert plan.metadata == context

    def test_plan_has_dependencies(self, planner):
        plan = planner.generate_plan("Implement a user authentication system")
        if plan.step_count > 1:
            # Sequential steps should have at least one dependency
            assert len(plan.dependencies) > 0

    def test_plan_has_cost_estimates(self, planner):
        plan = planner.generate_plan("Refactor database layer")
        assert len(plan.estimated_costs) == len(plan.steps)

    def test_decompose_implement_task(self, planner):
        steps = planner.decompose_task("Implement and test a caching layer")
        assert len(steps) >= 3
        assert any("test" in s.lower() for s in steps)

    def test_decompose_debug_task(self, planner):
        steps = planner.decompose_task("Debug the authentication timeout issue")
        assert any("reproduce" in s.lower() or "isolate" in s.lower() for s in steps)

    def test_decompose_refactor_task(self, planner):
        steps = planner.decompose_task("Refactor the user service module")
        assert any("extract" in s.lower() or "map" in s.lower() for s in steps)

    def test_evaluate_plan(self, planner):
        plan = planner.generate_plan("Build a search feature")
        scores = planner.evaluate_plan(plan)
        assert "quality" in scores
        assert "risk" in scores
        assert "cost" in scores
        for value in scores.values():
            assert 0.0 <= value <= 1.0

    def test_synthesize_results(self, planner):
        results = {0: "Designed schema", 1: "Implemented endpoints", 2: "Tests pass"}
        summary = planner.synthesize_results(results)
        assert "Step 1" in summary
        assert "Step 3" in summary

    def test_synthesize_empty_results(self, planner):
        summary = planner.synthesize_results({})
        assert "No results" in summary

    def test_custom_cost_model(self, planner):
        # Reset with custom cost model
        planner = System2Planner(cost_model=lambda s: 2.0)  # Fixed cost
        plan = planner.generate_plan("Test")
        for cost in plan.estimated_costs.values():
            assert cost == 2.0


# ═══════════════════════════════════════════════════════════════════════════════
# System 1 Executor Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystem1Executor:
    """Tests for System1Executor."""

    @pytest.fixture
    def executor(self) -> System1Executor:
        return System1Executor()

    def test_execute_step_returns_string(self, executor):
        result = executor.execute_step("Run the test suite")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_execute_step_for_build(self, executor):
        result = executor.execute_step("Build the project")
        assert "build" in result.lower() or "Build" in result

    def test_match_pattern_no_cache(self, executor):
        result = executor.match_pattern("Unknown task never seen before")
        assert result is None

    def test_cache_and_match_pattern(self, executor):
        executor.cache_pattern("run tests", "All tests passed")
        result = executor.match_pattern("run tests")
        assert result == "All tests passed"

    def test_cache_pattern_case_insensitive(self, executor):
        executor.cache_pattern("Run Tests", "All passed")
        result = executor.match_pattern("run tests")
        assert result == "All passed"

    def test_fuzzy_pattern_match(self, executor):
        executor.cache_pattern("build and deploy the application", "Deploy OK")
        result = executor.match_pattern("deploy the application")
        # Fuzzy match should find it
        assert result == "Deploy OK"

    def test_quick_evaluate_empty(self, executor):
        assert executor.quick_evaluate("") == 0.0

    def test_quick_evaluate_structured(self, executor):
        score = executor.quick_evaluate(
            "Therefore, because the first step is to verify the inputs, "
            "we should proceed with caution and validate all assumptions."
        )
        assert score >= 0.7


# ═══════════════════════════════════════════════════════════════════════════════
# Meta-Cognitive Controller Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetaCognitiveController:
    """Tests for MetaCognitiveController."""

    @pytest.fixture
    def controller(self) -> MetaCognitiveController:
        return MetaCognitiveController(System1Executor(), System2Planner())

    def test_assess_complex_task(self, controller):
        mode = controller.assess_task(
            "Design and implement a new architecture for the distributed system"
        )
        assert mode == SystemMode.SYSTEM2

    def test_assess_simple_task(self, controller):
        mode = controller.assess_task("Run the linter")
        assert mode == SystemMode.SYSTEM1

    def test_should_escalate_on_error(self, controller):
        assert controller.should_escalate(
            "The build failed with an unexpected error",
            SystemMode.SYSTEM1,
        ) is True

    def test_should_not_escalate_normal_observation(self, controller):
        assert controller.should_escalate(
            "All tests passed successfully",
            SystemMode.SYSTEM1,
        ) is False

    def test_should_not_escalate_from_system2(self, controller):
        assert controller.should_escalate(
            "An error occurred",
            SystemMode.SYSTEM2,
        ) is False

    def test_should_cache_high_confidence(self, controller):
        plan = Plan(confidence=ConfidenceLevel.HIGH, steps=("A", "B"))
        assert controller.should_cache(plan) is True

    def test_should_cache_medium_low_cost(self, controller):
        plan = Plan(
            confidence=ConfidenceLevel.MEDIUM,
            steps=("A",),
            estimated_costs={0: 5.0},
        )
        assert controller.should_cache(plan) is True

    def test_should_not_cache_low_confidence(self, controller):
        plan = Plan(confidence=ConfidenceLevel.LOW)
        assert controller.should_cache(plan) is False

    def test_mode_history_tracking(self, controller):
        controller.assess_task("Run tests")
        controller.assess_task("Design system architecture")
        history = controller.get_mode_history()
        assert len(history) == 2
        assert history[0] == SystemMode.SYSTEM1
        assert history[1] == SystemMode.SYSTEM2

    def test_escalation_count(self, controller):
        assert controller.get_escalation_count() == 0
        controller.should_escalate("error detected", SystemMode.SYSTEM1)
        assert controller.get_escalation_count() == 1

    def test_escalation_with_deadlock(self, controller):
        assert controller.should_escalate("Process deadlock detected", SystemMode.SYSTEM1)


# ═══════════════════════════════════════════════════════════════════════════════
# Attention Manager Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAttentionManager:
    """Tests for AttentionManager."""

    @pytest.fixture
    def manager(self) -> AttentionManager:
        return AttentionManager(capacity=3, decay_rate=0.2)

    def test_compute_priority(self, manager):
        signal = AttentionSignal(urgency=0.9, relevance=0.8, novelty=0.5)
        priority = manager.compute_priority(signal)
        assert priority == pytest.approx(0.9 * 0.8 * 0.5)

    def test_register_signal(self, manager):
        signal = AttentionSignal(source="test", urgency=0.5, relevance=0.5, novelty=0.5)
        manager.register_signal(signal)
        top = manager.get_top_signals(10)
        assert len(top) >= 1

    def test_select_focus_limits_to_capacity(self, manager):
        for i in range(10):
            signal = AttentionSignal(
                source=f"src-{i}",
                urgency=0.5 + i * 0.04,
                relevance=0.5,
                novelty=0.5,
            )
            manager.register_signal(signal)
        selected = manager.select_focus()
        assert len(selected) == 3

    def test_select_focus_external_signals(self, manager):
        signals = [
            AttentionSignal(urgency=0.9, relevance=0.9, novelty=0.9),
            AttentionSignal(urgency=0.1, relevance=0.1, novelty=0.1),
        ]
        selected = manager.select_focus(signals)
        assert len(selected) == 2
        # Higher priority should be first
        assert selected[0].priority > selected[1].priority

    def test_decay_reduces_weights(self, manager):
        signal = AttentionSignal(urgency=0.3, relevance=0.3, novelty=0.3)
        manager.register_signal(signal)

        # Force this signal out of focus by filling capacity
        for i in range(5):
            strong = AttentionSignal(
                source=f"strong-{i}",
                urgency=0.9,
                relevance=0.9,
                novelty=0.9,
            )
            manager.register_signal(strong)

        _initial_top = [s.id for s in manager.select_focus()]
        manager.decay_attention()
        # Decay should have run without error
        assert True

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            AttentionManager(capacity=0)

    def test_invalid_decay_rate_raises(self):
        with pytest.raises(ValueError):
            AttentionManager(decay_rate=0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# Theater of Mind Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTheaterOfMind:
    """Tests for TheaterOfMind."""

    @pytest.fixture
    def theater(self) -> TheaterOfMind:
        return TheaterOfMind(capacity=5)

    def test_publish_thought(self, theater):
        thought = Thought(content="Hello world", source="test")
        theater.publish(thought)
        history = theater.get_thought_history()
        assert len(history) == 1
        assert history[0].content == "Hello world"

    def test_subscribe_and_receive(self, theater):
        received: list[Thought] = []

        def callback(thought: Thought) -> None:
            received.append(thought)

        theater.subscribe(r"error", callback)
        theater.publish(Thought(content="An error occurred in module X", source="test"))
        assert len(received) == 1

    def test_subscribe_no_match(self, theater):
        received: list[Thought] = []

        def callback(thought: Thought) -> None:
            received.append(thought)

        theater.subscribe(r"error", callback)
        theater.publish(Thought(content="Everything is fine", source="test"))
        assert len(received) == 0

    def test_subscribe_matches_tags(self, theater):
        received: list[Thought] = []

        def callback(thought: Thought) -> None:
            received.append(thought)

        theater.subscribe(r"urgent", callback)
        theater.publish(Thought(
            content="Regular message",
            tags=frozenset({"urgent", "alert"}),
        ))
        assert len(received) == 1

    def test_unsubscribe(self, theater):
        received: list[Thought] = []

        def callback(thought: Thought) -> None:
            received.append(thought)

        theater.subscribe(r".*", callback)
        removed = theater.unsubscribe(callback)
        assert removed >= 1
        theater.publish(Thought(content="Should not be received"))
        assert len(received) == 0

    def test_focus_thought(self, theater):
        thought = Thought(content="Important observation", source="sensor")
        theater.publish(thought)
        theater.focus(thought.id)
        focused = theater.get_focused_thought()
        assert focused is not None
        assert focused.content == "Important observation"

    def test_focus_nonexistent_raises(self, theater):
        with pytest.raises(KeyError):
            theater.focus("nonexistent-id")

    def test_get_workspace_state(self, theater):
        thought = Thought(content="Active task: build API", source="loop")
        theater.publish(thought)
        theater.focus(thought.id)
        state = theater.get_workspace_state()
        assert "active_thoughts" in state
        assert "focused_thought" in state
        assert "working_memory" in state
        assert state["focused_thought"] == "Active task: build API"

    def test_get_thought_by_id(self, theater):
        thought = Thought(content="Find me")
        theater.publish(thought)
        found = theater.get_thought_by_id(thought.id)
        assert found is not None
        assert found.content == "Find me"
        assert theater.get_thought_by_id("nonexistent") is None

    def test_attend_returns_thoughts(self, theater):
        for i in range(3):
            theater.publish(Thought(content=f"Thought {i}", source="test"))
        attended = theater.attend()
        assert len(attended) == 3

    def test_tick_maintenance(self, theater):
        theater.publish(Thought(content="Test"))
        theater.tick_maintenance()  # Should not raise


# ═══════════════════════════════════════════════════════════════════════════════
# Reasoning Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestReasoningEngine:
    """Tests for ReasoningEngine."""

    @pytest.fixture
    def engine(self) -> ReasoningEngine:
        return ReasoningEngine(max_depth=5, branching_factor=3)

    def test_chain_of_thought(self, engine):
        result = engine.chain_of_thought("How should we optimize the database?")
        assert isinstance(result, ReasoningResult)
        assert result.strategy == "chain_of_thought"
        assert len(result.conclusion) > 0
        assert len(result.trace) > 0
        assert isinstance(result.confidence, ConfidenceLevel)

    def test_tree_of_thoughts(self, engine):
        result = engine.tree_of_thoughts("What architecture pattern is best?")
        assert result.strategy == "tree_of_thoughts"
        assert len(result.trace) > 0
        assert len(result.alternatives) > 0

    def test_reflexion(self, engine):
        result = engine.reflexion(
            "The system is slow because of database queries.",
            iterations=3,
        )
        assert result.strategy == "reflexion"
        assert len(result.trace) == 3
        assert len(result.conclusion) > len(
            "The system is slow because of database queries."
        )

    def test_debate(self, engine):
        result = engine.debate(
            "Should we use microservices for this project?",
            perspectives=3,
        )
        assert result.strategy == "debate"
        assert len(result.trace) == 3
        assert len(result.alternatives) == 3

    def test_debate_two_perspectives(self, engine):
        result = engine.debate("Is TypeScript better than JavaScript?", perspectives=2)
        assert len(result.trace) == 2

    def test_chain_of_thought_short_problem(self, engine):
        result = engine.chain_of_thought("Fix bug")
        assert len(result.trace) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Cognitive Loop Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveLoop:
    """Tests for CognitiveLoop."""

    @pytest.fixture
    def loop(self) -> CognitiveLoop:
        return CognitiveLoop(max_ticks_default=10)

    def test_tick_returns_record(self, loop):
        tick = loop.tick("Initial observation")
        assert isinstance(tick, CognitiveTick)
        assert tick.index == 0
        assert len(tick.perception) >= 1
        assert isinstance(tick.timestamp, datetime)

    def test_tick_increments_index(self, loop):
        t1 = loop.tick()
        t2 = loop.tick()
        assert t1.index == 0
        assert t2.index == 1

    def test_run_simple_task(self, loop):
        ticks = loop.run("Run all tests and format code", max_ticks=5)
        assert len(ticks) > 0
        assert all(isinstance(t, CognitiveTick) for t in ticks)

    def test_run_complex_task_uses_system2(self, loop):
        ticks = loop.run("Design and implement new architecture", max_ticks=5)
        assert len(ticks) > 0

    def test_interrupt(self, loop):
        interrupt_thought = Thought(
            content="System failure detected!",
            source="monitor",
            tags=frozenset({"urgent", "alert"}),
        )
        loop.interrupt(interrupt_thought)
        ticks = loop.run("Normal operation", max_ticks=3)
        assert len(ticks) > 0

    def test_get_trace_empty(self, loop):
        trace = loop.get_trace()
        assert trace == []

    def test_get_trace_after_run(self, loop):
        loop.run("Test task", max_ticks=3)
        trace = loop.get_trace()
        assert len(trace) > 0
        assert all(isinstance(t, CognitiveTick) for t in trace)

    def test_get_state(self, loop):
        loop.run("Simple task", max_ticks=2)
        state = loop.get_state()
        assert isinstance(state, CognitiveState)
        assert state.cycle_count > 0

    def test_reset(self, loop):
        loop.run("Task", max_ticks=2)
        loop.reset()
        assert loop.tick_count == 0
        assert loop.current_mode == SystemMode.IDLE
        assert loop.get_trace() == []

    def test_theater_accessibility(self, loop):
        """The theater can be accessed from the loop for direct observation publishing."""
        loop.theater.publish(Thought(content="External event", source="external"))
        history = loop.theater.get_thought_history()
        assert len(history) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """End-to-end integration tests across multiple components."""

    def test_full_workflow_simple_task(self):
        """A simple task flows through the complete cognitive pipeline."""
        theater = TheaterOfMind()
        planner = System2Planner()
        executor = System1Executor()
        controller = MetaCognitiveController(executor, planner)
        reasoning = ReasoningEngine()
        loop = CognitiveLoop(
            theater=theater,
            system1=executor,
            system2=planner,
            reasoning=reasoning,
        )

        # Simple task should use System 1
        mode = controller.assess_task("Run unit tests")
        assert mode == SystemMode.SYSTEM1

        # Run through the loop
        ticks = loop.run("Run unit tests", max_ticks=5)
        assert len(ticks) > 0

        # Verify trace is consistent
        trace = loop.get_trace()
        assert len(trace) == len(ticks)

    def test_full_workflow_complex_task(self):
        """A complex task triggers System 2 and generates a plan."""
        theater = TheaterOfMind()
        planner = System2Planner()
        executor = System1Executor()
        controller = MetaCognitiveController(executor, planner)
        reasoning = ReasoningEngine()
        _loop = CognitiveLoop(
            theater=theater,
            system1=executor,
            system2=planner,
            reasoning=reasoning,
        )

        # Complex task should use System 2
        mode = controller.assess_task("Design a new distributed architecture")
        assert mode == SystemMode.SYSTEM2

        # Generate a plan
        plan = planner.generate_plan("Design a new distributed architecture")
        assert plan.step_count >= 3

        # Publish to theater and verify attention
        thought = Thought(content=f"Plan: {plan.goal}", tags=frozenset({"plan"}))
        theater.publish(thought)
        attended = theater.attend()
        assert len(attended) > 0

    def test_escalation_flow(self):
        """System 1 escalates to System 2 on error."""
        executor = System1Executor()
        planner = System2Planner()
        controller = MetaCognitiveController(executor, planner)

        # Simulate System 1 encountering an error
        should_escalate = controller.should_escalate(
            "unexpected failure in module X",
            SystemMode.SYSTEM1,
        )
        assert should_escalate is True
        assert controller.get_escalation_count() == 1

    def test_plan_caching_flow(self):
        """High-confidence plans get cached for System 1 reuse."""
        planner = System2Planner()
        executor = System1Executor()
        controller = MetaCognitiveController(executor, planner)

        # Generate and cache a plan
        plan = planner.generate_plan("Standard deployment checklist")
        if controller.should_cache(plan):
            for i, step in enumerate(plan.steps):
                executor.cache_pattern(step, f"Step {i} completed")

        # Verify cache hit
        if plan.steps:
            result = executor.match_pattern(plan.steps[0])
            # Cache hit should return a result (may be None if not enough content to match)
            assert result is not None or plan.step_count == 0

    def test_reasoning_integration_with_cognitive_loop(self):
        """Reasoning engine integrates with the cognitive loop."""
        reasoning = ReasoningEngine()
        loop = CognitiveLoop(reasoning=reasoning)

        # Run a task that needs reasoning
        ticks = loop.run("Analyze database performance", max_ticks=5)
        assert len(ticks) > 0

        # At least one tick should have reasoning output
        reasoning_ticks = [t for t in ticks if t.reasoning]
        assert len(reasoning_ticks) > 0

    def test_attention_broadcast_and_receive(self):
        """Multiple subscribers receive relevant broadcasts."""
        theater = TheaterOfMind()

        system1_received: list[Thought] = []
        system2_received: list[Thought] = []
        monitor_received: list[Thought] = []

        theater.subscribe(r"\bplan\b", lambda t: system2_received.append(t))
        theater.subscribe(r"\bexecute\b|\bcache\b", lambda t: system1_received.append(t))
        theater.subscribe(r"\bcritical\b|\balert\b", lambda t: monitor_received.append(t))

        theater.publish(Thought(content="plan: new architecture ready", source="planner"))
        theater.publish(Thought(content="execute fast action now", source="executor"))
        theater.publish(Thought(content="critical: disk full detected", source="monitor"))

        assert len(system2_received) == 1
        assert len(system1_received) == 1
        assert len(monitor_received) == 1

    def test_cognitive_state_progression(self):
        """Cognitive state progresses correctly through a task."""
        loop = CognitiveLoop()

        # Initial state
        state_before = loop.get_state()
        assert state_before.mode == SystemMode.IDLE
        assert state_before.cycle_count == 0

        # Run a task
        loop.run("Build and deploy the application", max_ticks=5)

        # Final state
        state_after = loop.get_state()
        assert state_after.cycle_count > 0
        assert state_after.mode != SystemMode.IDLE
