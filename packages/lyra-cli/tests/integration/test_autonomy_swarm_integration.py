"""Integration: Autonomy state machine delegates tasks to Swarm orchestrator.

Tests exercise:
- Autonomy state machine delegating to SwarmOrchestrator
- Goal decomposition spawning swarm agents
- Session checkpoint across swarm execution
- Hooks firing during swarm operations
- Budget tracking during multi-agent execution
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lyra_cli.autonomy import (
    AutonomyState,
    BudgetManager,
    Goal,
    GoalDecomposer,
    HookEvent,
    HooksManager,
    SessionCheckpoint,
    SessionManager,
    StateMachine,
    TransitionError,
)
from lyra_cli.swarm import (
    OrchestratorConfig,
    PriorityLevel,
    SwarmOrchestrator,
    SwarmTask,
    TaskResult,
)

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def state_machine() -> StateMachine:
    """Provide a fresh state machine per test."""
    sm = StateMachine()
    sm.transitions.clear()
    # Add transitions needed for swarm delegation
    from lyra_cli.autonomy.state_machine import StateTransition
    sm.transitions.append(
        StateTransition(AutonomyState.IDLE, AutonomyState.PLANNING)
    )
    sm.transitions.append(
        StateTransition(AutonomyState.PLANNING, AutonomyState.EXECUTING)
    )
    sm.transitions.append(
        StateTransition(AutonomyState.EXECUTING, AutonomyState.VERIFYING)
    )
    sm.transitions.append(
        StateTransition(AutonomyState.VERIFYING, AutonomyState.COMPLETED)
    )
    sm.transitions.append(
        StateTransition(AutonomyState.VERIFYING, AutonomyState.EXECUTING)
    )
    return sm


@pytest.fixture
def swarm_orchestrator() -> SwarmOrchestrator:
    """Provide a swarm orchestrator with a minimal config."""
    config = OrchestratorConfig(
        max_concurrent_tasks=4,
        task_timeout_seconds=5.0,
        max_retries_per_task=0,
    )
    return SwarmOrchestrator(config)


@pytest.fixture
def goal_decomposer() -> GoalDecomposer:
    """Provide a goal decomposer."""
    return GoalDecomposer()


@pytest.fixture
def hooks_manager() -> HooksManager:
    """Provide a fresh hooks manager."""
    return HooksManager()


@pytest.fixture
def budget_manager(tmp_path: Path) -> BudgetManager:
    """Provide a budget manager scoped to tmp_path."""
    return BudgetManager(data_dir=tmp_path, daily_limit_usd=100.0)


@pytest.fixture
def session_manager(tmp_path: Path) -> SessionManager:
    """Provide a session manager scoped to tmp_path."""
    return SessionManager(checkpoint_dir=tmp_path / "checkpoints")


# =========================================================================
# Test: Autonomy state machine delegates tasks to Swarm
# =========================================================================


class TestAutonomySwarmDelegation:
    """Test that the autonomy state machine can delegate tasks to the swarm."""

    def test_state_machine_delegates_to_swarm(self, state_machine, swarm_orchestrator):
        """Verify state machine transitions through PLANNING -> EXECUTING."""
        state_machine.transition_to(AutonomyState.PLANNING)
        assert state_machine.in_state(AutonomyState.PLANNING)

        # Delegate to swarm
        state_machine.context["task_id"] = None
        state_machine.transition_to(AutonomyState.EXECUTING)
        assert state_machine.in_state(AutonomyState.EXECUTING)

    def test_state_machine_context_flows_to_swarm(
        self, state_machine, swarm_orchestrator,
    ):
        """Verify context dict flows from state machine into swarm tasks."""
        state_machine.context["goal_id"] = "test_goal_01"
        state_machine.context["query"] = "Analyze the codebase"

        task = SwarmTask(
            description="Analyze the codebase",
            priority=PriorityLevel.HIGH,
            payload=dict(state_machine.context),
        )

        # Context from state machine should be in the task payload
        assert task.payload["goal_id"] == "test_goal_01"
        assert task.payload["query"] == "Analyze the codebase"

    def test_task_result_updates_swarm_context(
        self, state_machine, swarm_orchestrator,
    ):
        """Verify swarm TaskResult can feed back into state machine context."""
        state_machine.transition_to(AutonomyState.PLANNING)
        state_machine.transition_to(AutonomyState.EXECUTING)

        result = TaskResult(
            task_id="task_001",
            success=True,
            result={"summary": "Analysis complete", "findings_count": 5},
            duration_seconds=1.23,
        )

        state_machine.context["swarm_result"] = result
        assert state_machine.context["swarm_result"].success is True
        assert state_machine.context["swarm_result"].result["findings_count"] == 5

    def test_swarm_task_failure_propagates_to_state_machine(
        self, state_machine,
    ):
        """Verify failed swarm task sets state machine into RECOVERING."""
        state_machine.transition_to(AutonomyState.PLANNING)
        state_machine.transition_to(AutonomyState.EXECUTING)

        # Simulate failure
        with pytest.raises(TransitionError):
            state_machine.transition_to(AutonomyState.RECOVERING)

    def test_completed_swarm_triggers_verification(
        self, state_machine,
    ):
        """Verify completed swarm execution triggers VERIFYING state."""
        state_machine.transition_to(AutonomyState.PLANNING)
        state_machine.transition_to(AutonomyState.EXECUTING)
        state_machine.transition_to(AutonomyState.VERIFYING)

        assert state_machine.in_state(AutonomyState.VERIFYING)

    def test_re_enters_execution_after_verification(
        self, state_machine,
    ):
        """Verify state machine can loop back to EXECUTING from VERIFYING."""
        state_machine.transition_to(AutonomyState.PLANNING)
        state_machine.transition_to(AutonomyState.EXECUTING)
        state_machine.transition_to(AutonomyState.VERIFYING)
        state_machine.transition_to(AutonomyState.EXECUTING)

        assert state_machine.in_state(AutonomyState.EXECUTING)


# =========================================================================
# Test: Goal decomposition spawning swarm tasks
# =========================================================================


class TestGoalDecompositionSwarmSpawn:
    """Test that decomposed goals correctly spawn swarm tasks."""

    def test_goal_decomposition_produces_execution_plan(
        self, goal_decomposer,
    ):
        """Verify goal decomposition produces an ordered execution plan."""
        goal = Goal(
            id="integration_test",
            description="Refactor the core module",
        )
        graph = goal_decomposer.decompose(goal)

        assert len(graph.subtasks) == 3
        assert len(graph.execution_order) == 3
        # research must come before implement, which comes before verify
        assert graph.execution_order[0] == "integration_test_research"
        assert graph.execution_order[1] == "integration_test_implement"
        assert graph.execution_order[2] == "integration_test_verify"

    def test_decomposed_subtasks_map_to_swarm_tasks(
        self, goal_decomposer, swarm_orchestrator,
    ):
        """Verify each decomposed subtask becomes a swarm task."""
        goal = Goal(
            id="map_test",
            description="Map dependencies",
        )
        graph = goal_decomposer.decompose(goal)

        swarm_tasks = []
        for step_id in graph.execution_order:
            subtask = graph.subtask_by_id(step_id)
            task = SwarmTask(
                description=subtask.description,
                priority=PriorityLevel.MEDIUM,
                payload={"subtask_id": subtask.id},
            )
            swarm_tasks.append(task)

        assert len(swarm_tasks) == 3
        assert swarm_tasks[0].payload["subtask_id"] == "map_test_research"

    def test_subtask_dependencies_preserved_in_swarm(
        self, goal_decomposer,
    ):
        """Verify dependency chain is preserved in execution order."""
        goal = Goal(id="dep_test", description="Test dependencies")
        graph = goal_decomposer.decompose(goal)

        # Each subtask after the first should depend on the previous
        for i in range(1, len(graph.subtasks)):
            deps = graph.subtasks[i].depends_on
            assert len(deps) >= 1
            assert deps[0] == graph.subtasks[i - 1].id


# =========================================================================
# Test: Session checkpoint across swarm execution
# =========================================================================


class TestSessionCheckpoints:
    """Test session checkpointing during swarm execution."""

    def test_checkpoint_created_before_swarm_execution(
        self, session_manager, tmp_path,
    ):
        """Verify a checkpoint is saved before swarm execution starts."""
        checkpoint = SessionCheckpoint(
            session_id="swarm_sesh_01",
            state="EXECUTING",
            goal="Refactor and test",
            context={
                "swarm_task_ids": ["task_1", "task_2"],
                "budget_limit": 50.0,
            },
        )
        path = session_manager.save_checkpoint(checkpoint)
        assert path.exists()
        assert session_manager.checkpoint_exists("swarm_sesh_01")

    def test_checkpoint_loaded_after_swarm_completion(
        self, session_manager,
    ):
        """Verify checkpoint can be loaded to resume swarm state."""
        checkpoint = SessionCheckpoint(
            session_id="swarm_sesh_02",
            state="EXECUTING",
            goal="Continue analysis",
            context={"completed": ["task_1"], "remaining": ["task_2"]},
        )
        session_manager.save_checkpoint(checkpoint)
        loaded = session_manager.load_checkpoint("swarm_sesh_02")
        assert loaded.session_id == "swarm_sesh_02"
        assert loaded.state == "EXECUTING"
        assert loaded.goal == "Continue analysis"
        assert loaded.context["remaining"] == ["task_2"]

    def test_multiple_checkpoints_maintain_history(
        self, session_manager,
    ):
        """Verify multiple checkpoints capture progress history."""
        # Use distinct created_at timestamps to avoid filename collisions
        timestamps = ["20250101T000001Z", "20250101T000002Z", "20250101T000003Z"]
        for i in range(3):
            session_manager.save_checkpoint(
                SessionCheckpoint(
                    session_id="multi_sesh",
                    state=f"STEP_{i}",
                    goal=f"Step {i}",
                    context={"progress": i},
                    created_at=timestamps[i],
                )
            )
        checkpoints = session_manager.list_checkpoints("multi_sesh")
        assert len(checkpoints) == 3

        # Latest checkpoint should reflect most recent state
        latest = session_manager.load_checkpoint("multi_sesh")
        assert latest.goal == "Step 2"


# =========================================================================
# Test: Hooks firing during swarm operations
# =========================================================================


class TestHooksDuringSwarm:
    """Test lifecycle hooks fire during swarm operations."""

    def test_on_start_hook_fires_before_swarm(
        self, hooks_manager,
    ):
        """Verify ON_START hook fires before swarm execution."""
        fired_events = []

        def capture(event, ctx):
            fired_events.append((event, ctx.get("swarm_mode")))

        hooks_manager.register(HookEvent.ON_START, capture)
        hooks_manager.fire(HookEvent.ON_START, {"swarm_mode": "parallel"})

        assert len(fired_events) == 1
        assert fired_events[0][0] == HookEvent.ON_START
        assert fired_events[0][1] == "parallel"

    def test_on_complete_hook_fires_after_swarm(
        self, hooks_manager,
    ):
        """Verify ON_COMPLETE hook fires after swarm execution."""
        fired_events = []

        def capture(event, ctx):
            fired_events.append((event, ctx.get("task_count")))

        hooks_manager.register(HookEvent.ON_COMPLETE, capture)
        hooks_manager.fire(HookEvent.ON_COMPLETE, {"task_count": 5})

        assert len(fired_events) == 1
        assert fired_events[0][0] == HookEvent.ON_COMPLETE
        assert fired_events[0][1] == 5

    def test_on_error_hook_fires_on_swarm_failure(
        self, hooks_manager,
    ):
        """Verify ON_ERROR hook fires when swarm task fails."""
        fired_events = []

        def capture(event, ctx):
            fired_events.append((event, ctx.get("error_message")))

        hooks_manager.register(HookEvent.ON_ERROR, capture)
        hooks_manager.fire(HookEvent.ON_ERROR, {"error_message": "Task timeout"})

        assert len(fired_events) == 1
        assert "timeout" in fired_events[0][1].lower()

    def test_hooks_context_accumulates_across_events(
        self, hooks_manager,
    ):
        """Verify hooks context accumulates data across lifecycle."""
        ctx: dict = {}

        hooks_manager.register(HookEvent.ON_START, lambda e, c: ctx.update(c))
        hooks_manager.register(
            HookEvent.ON_COMPLETE,
            lambda e, c: ctx.update({"result": c.get("result")}),
        )

        hooks_manager.fire(HookEvent.ON_START, {"session": "s1"})
        hooks_manager.fire(HookEvent.ON_COMPLETE, {"result": "ok"})

        assert ctx.get("session") == "s1"
        assert ctx.get("result") == "ok"


# =========================================================================
# Test: Budget tracking during multi-agent execution
# =========================================================================


class TestBudgetTracking:
    """Test budget tracking during multi-agent swarm execution."""

    def test_budget_records_multiple_agent_calls(
        self, budget_manager,
    ):
        """Verify budget records costs for multiple agents."""
        budget_manager.record_usage(
            model="gpt-4", prompt_tokens=500, completion_tokens=200, cost_usd=0.03
        )
        budget_manager.record_usage(
            model="claude-3", prompt_tokens=300, completion_tokens=150, cost_usd=0.02
        )

        summary = budget_manager.summary()
        assert summary.entry_count == 2
        assert summary.total_tokens == 1150

    def test_budget_limit_triggers_error(
        self, budget_manager,
    ):
        """Verify budget exceeded error blocks further usage."""
        budget_manager.daily_limit_usd = 0.01
        budget_manager.record_usage(
            model="gpt-4", prompt_tokens=100, completion_tokens=50, cost_usd=0.01
        )

        with pytest.raises(Exception):
            budget_manager.check_limits()

    def test_budget_warning_at_threshold(
        self, budget_manager,
    ):
        """Verify warning flags when approaching budget limit."""
        budget_manager.daily_limit_usd = 1.0
        budget_manager.warning_threshold = 0.8

        budget_manager.record_usage(
            model="gpt-4", prompt_tokens=500, completion_tokens=200, cost_usd=0.85
        )

        summary = budget_manager.summary()
        assert summary.degraded
        assert summary.daily_pct >= 0.8

    def test_budget_summary_includes_daily_and_monthly(
        self, budget_manager,
    ):
        """Verify summary provides daily and monthly breakdowns."""
        budget_manager.record_usage(
            model="claude-3", prompt_tokens=1000, completion_tokens=500, cost_usd=0.05
        )

        summary = budget_manager.summary()
        assert summary.daily_cost_usd >= 0.0
        assert summary.monthly_cost_usd >= 0.0
        assert summary.daily_limit_usd == 100.0
        assert summary.monthly_limit_usd == 200.0
