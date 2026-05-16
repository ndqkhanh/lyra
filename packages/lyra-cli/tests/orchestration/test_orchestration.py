"""Tests for Phase 4 Orchestration modules."""

import pytest

from lyra_cli.orchestration.specialist_agents import (
    AgentRole,
    AgentOrchestrator,
)
from lyra_cli.orchestration.model_router import (
    ModelTier,
    ModelRouter,
)
from lyra_cli.orchestration.closed_loop import (
    ClosedLoopController,
    SimpleVerifier,
    VerificationResult,
)


# ============================================================================
# Specialist Agents Tests
# ============================================================================

@pytest.fixture
def orchestrator():
    """Create agent orchestrator."""
    return AgentOrchestrator()


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes with all agents."""
    assert len(orchestrator.agents) == 4
    assert AgentRole.PLANNER in orchestrator.agents
    assert AgentRole.EDITOR in orchestrator.agents
    assert AgentRole.DEBUGGER in orchestrator.agents
    assert AgentRole.TESTER in orchestrator.agents


def test_assign_task(orchestrator):
    """Test task assignment."""
    task_id = orchestrator.assign_task(
        role=AgentRole.PLANNER,
        description="Plan implementation of feature X",
        context={"priority": "high"},
    )

    assert task_id is not None
    assert orchestrator.stats["total_tasks"] == 1


def test_execute_task(orchestrator):
    """Test task execution."""
    task_id = orchestrator.assign_task(
        role=AgentRole.EDITOR,
        description="Write function to parse JSON",
    )

    success, result, error = orchestrator.execute_task(task_id)

    assert success is True
    assert result is not None
    assert orchestrator.stats["completed_tasks"] == 1


def test_agent_success_rate(orchestrator):
    """Test agent success rate tracking."""
    # Execute multiple tasks
    for i in range(5):
        task_id = orchestrator.assign_task(
            role=AgentRole.TESTER,
            description=f"Write test {i}",
        )
        orchestrator.execute_task(task_id)

    agent = orchestrator.agents[AgentRole.TESTER]
    assert agent.tasks_completed == 5
    assert agent.get_success_rate() == 1.0


def test_task_handoff(orchestrator):
    """Test task handoff between agents."""
    # Create initial task
    task_id = orchestrator.assign_task(
        role=AgentRole.PLANNER,
        description="Plan feature",
    )

    # Hand off to editor
    new_task_id = orchestrator.handoff_task(
        task_id=task_id,
        from_role=AgentRole.PLANNER,
        to_role=AgentRole.EDITOR,
        reason="Planning complete, ready for implementation",
    )

    assert new_task_id != task_id
    assert orchestrator.stats["agent_handoffs"] == 1


def test_agent_capabilities(orchestrator):
    """Test agent capabilities."""
    planner = orchestrator.agents[AgentRole.PLANNER]
    assert len(planner.capabilities) > 0
    assert planner.capabilities[0].name == "Task Decomposition"


def test_get_agent_stats(orchestrator):
    """Test getting agent statistics."""
    stats = orchestrator.get_agent_stats(AgentRole.PLANNER)

    assert "agent_id" in stats
    assert "role" in stats
    assert stats["role"] == "planner"


# ============================================================================
# Model Router Tests
# ============================================================================

@pytest.fixture
def router():
    """Create model router."""
    return ModelRouter()


def test_router_initialization(router):
    """Test router initializes with model costs."""
    assert ModelTier.HAIKU in router.model_costs
    assert ModelTier.SONNET in router.model_costs
    assert ModelTier.OPUS in router.model_costs


def test_assess_complexity_simple(router):
    """Test complexity assessment for simple tasks."""
    complexity = router.assess_complexity("Fix typo in README")

    assert complexity.complexity_score < 0.3
    assert complexity.reasoning_depth == "shallow"
    assert complexity.code_size == "small"


def test_assess_complexity_medium(router):
    """Test complexity assessment for medium tasks."""
    complexity = router.assess_complexity("Implement user authentication")

    assert 0.3 <= complexity.complexity_score < 0.7
    assert complexity.reasoning_depth in ["shallow", "medium"]


def test_assess_complexity_high(router):
    """Test complexity assessment for complex tasks."""
    complexity = router.assess_complexity(
        "Design and implement complex distributed caching architecture"
    )

    assert complexity.complexity_score >= 0.7
    assert complexity.reasoning_depth == "deep"


def test_route_to_haiku(router):
    """Test routing simple tasks to Haiku."""
    decision = router.route_task("Add console.log statement")

    assert decision.selected_model == ModelTier.HAIKU
    assert router.stats["haiku_routes"] == 1


def test_route_to_sonnet(router):
    """Test routing medium tasks to Sonnet."""
    decision = router.route_task("Implement REST API endpoint")

    assert decision.selected_model in [ModelTier.SONNET, ModelTier.HAIKU]
    assert router.stats["total_routes"] == 1


def test_route_to_opus(router):
    """Test routing complex tasks to Opus."""
    decision = router.route_task(
        "Design complex microservices architecture with event sourcing"
    )

    assert decision.selected_model == ModelTier.OPUS
    assert router.stats["opus_routes"] == 1


def test_cost_reduction(router):
    """Test cost reduction calculation."""
    # Route mix of tasks
    router.route_task("Fix typo")  # Haiku
    router.route_task("Add feature")  # Sonnet
    router.route_task("Design architecture")  # Opus

    cost_reduction = router.get_cost_reduction()

    # Should have some cost reduction vs always using Opus
    assert cost_reduction > 0.0


def test_routing_with_context(router):
    """Test routing with context overrides."""
    # Force Opus
    decision = router.route_task(
        "Simple task",
        context={"force_opus": True}
    )

    assert decision.selected_model == ModelTier.OPUS


def test_precision_routing(router):
    """Test routing for precision-required tasks."""
    decision = router.route_task(
        "Implement security-critical authentication",
        context={"is_critical": True}
    )

    # Should route to Sonnet or Opus for critical tasks
    assert decision.selected_model in [ModelTier.SONNET, ModelTier.OPUS]


# ============================================================================
# Closed Loop Tests
# ============================================================================

@pytest.fixture
def controller():
    """Create closed-loop controller."""
    return ClosedLoopController(max_iterations=3)


def test_controller_initialization(controller):
    """Test controller initialization."""
    assert controller.max_iterations == 3
    assert len(controller.executions) == 0


def test_simple_verification_pass(controller):
    """Test execution that passes verification on first try."""
    def execute_fn(input_data):
        return "valid output"

    def verify_fn(output):
        return VerificationResult(passed=True, score=1.0)

    def correct_fn(input_data, verification):
        return input_data

    success, output, iterations = controller.execute_with_verification(
        task_description="Test task",
        execute_fn=execute_fn,
        verify_fn=verify_fn,
        correct_fn=correct_fn,
        initial_input="input",
    )

    assert success is True
    assert len(iterations) == 1
    assert controller.stats["successful_executions"] == 1


def test_verification_with_retry(controller):
    """Test execution that requires retry."""
    attempt = [0]

    def execute_fn(input_data):
        attempt[0] += 1
        if attempt[0] == 1:
            return "invalid"
        return "valid"

    def verify_fn(output):
        if output == "valid":
            return VerificationResult(passed=True, score=1.0)
        return VerificationResult(
            passed=False,
            score=0.5,
            issues=["Output invalid"],
            suggestions=["Fix output"],
        )

    def correct_fn(input_data, verification):
        return "corrected_input"

    success, output, iterations = controller.execute_with_verification(
        task_description="Test task with retry",
        execute_fn=execute_fn,
        verify_fn=verify_fn,
        correct_fn=correct_fn,
        initial_input="input",
    )

    assert success is True
    assert len(iterations) == 2
    assert iterations[0].verification.passed is False
    assert iterations[1].verification.passed is True


def test_max_iterations_exceeded(controller):
    """Test execution that exceeds max iterations."""
    def execute_fn(input_data):
        return "always invalid"

    def verify_fn(output):
        return VerificationResult(
            passed=False,
            score=0.0,
            issues=["Always fails"],
        )

    def correct_fn(input_data, verification):
        return input_data

    success, output, iterations = controller.execute_with_verification(
        task_description="Test task that fails",
        execute_fn=execute_fn,
        verify_fn=verify_fn,
        correct_fn=correct_fn,
        initial_input="input",
    )

    assert success is False
    assert len(iterations) == 3  # max_iterations
    assert controller.stats["failed_executions"] == 1


def test_success_rate_calculation(controller):
    """Test success rate calculation."""
    def execute_fn(input_data):
        return "output"

    def verify_fn(output):
        return VerificationResult(passed=True, score=1.0)

    def correct_fn(input_data, verification):
        return input_data

    # Execute multiple tasks
    for i in range(10):
        controller.execute_with_verification(
            task_description=f"Task {i}",
            execute_fn=execute_fn,
            verify_fn=verify_fn,
            correct_fn=correct_fn,
            initial_input="input",
        )

    success_rate = controller.get_success_rate()
    assert success_rate == 1.0


def test_simple_verifier_code_syntax(controller):
    """Test simple code syntax verifier."""
    # Valid code
    result = SimpleVerifier.verify_code_syntax("def foo(): return 42")
    assert result.passed is True

    # Invalid code (unmatched parentheses)
    result = SimpleVerifier.verify_code_syntax("def foo(: return 42")
    assert result.passed is False
    assert len(result.issues) > 0


def test_simple_verifier_test_results(controller):
    """Test simple test results verifier."""
    # Passing tests
    result = SimpleVerifier.verify_test_results("10 passed in 0.5s")
    assert result.passed is True

    # Failing tests
    result = SimpleVerifier.verify_test_results("5 passed, 2 FAILED")
    assert result.passed is False


def test_improvement_rate(controller):
    """Test improvement rate calculation."""
    def execute_fn(input_data):
        return "output"

    def verify_fn(output):
        return VerificationResult(passed=True, score=1.0)

    def correct_fn(input_data, verification):
        return input_data

    # Execute tasks to build success rate
    for i in range(10):
        controller.execute_with_verification(
            task_description=f"Task {i}",
            execute_fn=execute_fn,
            verify_fn=verify_fn,
            correct_fn=correct_fn,
            initial_input="input",
        )

    improvement_rate = controller.get_improvement_rate()
    # Should show improvement over 60% baseline
    assert improvement_rate > 0.0
