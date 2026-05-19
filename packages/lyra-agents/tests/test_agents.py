"""Tests for advanced agent capabilities."""

import pytest

from lyra_agents import (
    ExecutionFeedback,
    ModelRouter,
    ModelTier,
    PromptOptimizer,
    SelfImprovementLoop,
    TaskComplexity,
)


def test_model_router_simple_task():
    """Test routing simple task to Haiku."""
    router = ModelRouter()

    decision = router.route("What is 2+2?", task_type="general")

    assert decision.selected_model == ModelTier.HAIKU
    assert decision.complexity == TaskComplexity.SIMPLE
    assert decision.estimated_cost < 0.01


def test_model_router_complex_task():
    """Test routing complex task to Opus."""
    router = ModelRouter()

    prompt = "Analyze and design a distributed system architecture for handling 1M requests/second with multi-region failover"
    decision = router.route(prompt, task_type="reasoning")

    assert decision.selected_model == ModelTier.OPUS
    assert decision.complexity == TaskComplexity.COMPLEX


def test_model_router_cost_budget():
    """Test cost budget enforcement."""
    router = ModelRouter(cost_budget=0.01)

    # Large prompt that would normally use Opus
    prompt = "analyze " * 1000
    decision = router.route(prompt, require_reasoning=True)

    # Should downgrade due to cost
    assert decision.selected_model in [ModelTier.SONNET, ModelTier.HAIKU]


def test_prompt_optimizer_template():
    """Test template rendering."""
    optimizer = PromptOptimizer()

    prompt = optimizer.render(
        "code_review",
        language="python",
        code="def hello(): print('world')",
    )

    assert "python" in prompt
    assert "hello" in prompt
    assert "Security vulnerabilities" in prompt


def test_prompt_optimizer_optimization():
    """Test prompt optimization."""
    optimizer = PromptOptimizer()

    prompt = "fix    the    bug"
    optimized = optimizer.optimize(prompt)

    assert "  " not in optimized  # No double spaces
    assert len(optimized) > len(prompt)  # Added structure


def test_prompt_optimizer_compression():
    """Test prompt compression."""
    optimizer = PromptOptimizer()

    long_prompt = "a" * 2000
    compressed = optimizer.compress(long_prompt, max_length=100)

    assert len(compressed) <= 110  # Allow for ellipsis
    assert "..." in compressed


def test_self_improvement_feedback():
    """Test feedback recording."""
    loop = SelfImprovementLoop()

    feedback = ExecutionFeedback(
        task_id="task1",
        prompt="Test prompt",
        result="Success",
        success=True,
        execution_time=1.5,
        token_count=100,
    )

    loop.record_feedback(feedback)

    insights = loop.get_insights()
    assert insights["total_executions"] == 1
    assert insights["success_rate"] == 1.0


def test_self_improvement_variants():
    """Test A/B testing variants."""
    loop = SelfImprovementLoop(learning_rate=0.5)  # Higher learning rate for faster convergence

    # Register variants
    loop.register_variant("v1", "Template 1")
    loop.register_variant("v2", "Template 2")

    # Record feedback for v1 (successful)
    for i in range(10):
        loop.record_feedback(
            ExecutionFeedback(
                task_id=f"task{i}",
                prompt="Template 1: test",
                result="Success",
                success=True,
                execution_time=1.0,
                token_count=100,
            )
        )

    # Record feedback for v2 (failed)
    for i in range(10):
        loop.record_feedback(
            ExecutionFeedback(
                task_id=f"task{i+10}",
                prompt="Template 2: test",
                result="Failed",
                success=False,
                execution_time=2.0,
                token_count=100,
            )
        )

    best = loop.get_best_variant()
    assert best is not None
    assert best.variant_id == "v1"
    # v1 should have higher success rate than v2
    v1 = loop.prompt_variants["v1"]
    v2 = loop.prompt_variants["v2"]
    assert v1.success_rate > v2.success_rate


def test_self_improvement_suggestions():
    """Test improvement suggestions."""
    loop = SelfImprovementLoop()

    # Record low success rate
    for i in range(10):
        loop.record_feedback(
            ExecutionFeedback(
                task_id=f"task{i}",
                prompt="Test",
                result="Failed",
                success=False,
                execution_time=1.0,
                token_count=100,
                error="ValueError: test",
            )
        )

    suggestions = loop.suggest_improvements()
    assert len(suggestions) > 0
    assert any("success rate" in s.lower() for s in suggestions)
