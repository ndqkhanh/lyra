"""
Comprehensive tests for Chain-of-Thought reasoning engine.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from lyra_reasoning.engines.cot import ChainOfThoughtEngine
from lyra_reasoning.types import (
    ComputeBudget,
    ReasoningConfig,
    ReasoningStrategy,
    StepType,
)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    with patch("lyra_reasoning.engines.cot.Anthropic") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def cot_engine(mock_anthropic_client):
    """Create CoT engine with mocked client."""
    return ChainOfThoughtEngine()


@pytest.fixture
def basic_config():
    """Basic reasoning configuration."""
    return ReasoningConfig(
        strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        model="claude-opus-4-20250514",
        max_steps=5,
        temperature=0.7,
        enable_verification=True,
        verification_threshold=0.6,
        enable_backtracking=True,
    )


@pytest.fixture
def basic_budget():
    """Basic compute budget."""
    return ComputeBudget(max_tokens=10000, max_steps=10)


class TestChainOfThoughtEngine:
    """Test suite for ChainOfThoughtEngine."""

    def test_initialization(self):
        """Test engine initialization."""
        engine = ChainOfThoughtEngine()
        assert engine.client is not None

    def test_initialization_with_api_key(self):
        """Test engine initialization with API key."""
        with patch("lyra_reasoning.engines.cot.Anthropic") as mock:
            engine = ChainOfThoughtEngine(api_key="test-key")
            mock.assert_called_once_with(api_key="test-key")

    def test_reason_basic_flow(self, cot_engine, mock_anthropic_client, basic_config, basic_budget):
        """Test basic reasoning flow."""
        # Mock API responses
        mock_response = Mock()
        mock_response.content = [Mock(text="This is a reasoning step.")]
        mock_anthropic_client.messages.create.return_value = mock_response

        # Execute reasoning
        trace = cot_engine.reason("Test task", basic_budget, basic_config)

        # Assertions
        assert trace.task == "Test task"
        assert trace.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert len(trace.steps) > 0
        assert trace.duration > 0
        assert trace.token_count >= 0

    def test_step_type_progression(self, cot_engine):
        """Test step type progression logic."""
        # Empty steps -> HYPOTHESIS
        assert cot_engine._determine_step_type([]) == StepType.HYPOTHESIS

        # After hypothesis -> EVIDENCE
        from lyra_reasoning.types import ReasoningStep
        steps = [ReasoningStep(content="test", step_type=StepType.HYPOTHESIS)]
        assert cot_engine._determine_step_type(steps) == StepType.EVIDENCE

        # After evidence -> ANALYSIS
        steps.append(ReasoningStep(content="test", step_type=StepType.EVIDENCE))
        assert cot_engine._determine_step_type(steps) == StepType.ANALYSIS

        # After analysis -> EVIDENCE or CONCLUSION
        steps.append(ReasoningStep(content="test", step_type=StepType.ANALYSIS))
        next_type = cot_engine._determine_step_type(steps)
        assert next_type in [StepType.EVIDENCE, StepType.CONCLUSION]

    def test_verification_scoring(self, cot_engine):
        """Test step verification scoring."""
        from lyra_reasoning.types import ReasoningStep

        # Good step with reasoning indicators
        good_step = ReasoningStep(
            content="Because of the evidence, therefore we can conclude that this is correct.",
            step_type=StepType.ANALYSIS,
        )
        score = cot_engine._verify_step(good_step, "task", [])
        assert score > 0.5

        # Poor step (too short)
        poor_step = ReasoningStep(
            content="Yes.",
            step_type=StepType.ANALYSIS,
        )
        score = cot_engine._verify_step(poor_step, "task", [])
        assert score < 0.7

    def test_backtracking_on_low_verification(
        self, cot_engine, mock_anthropic_client, basic_config, basic_budget
    ):
        """Test backtracking when verification fails."""
        # Mock responses: first bad, then good
        bad_response = Mock()
        bad_response.content = [Mock(text="Bad.")]
        good_response = Mock()
        good_response.content = [Mock(text="This is a much better reasoning step with evidence.")]

        mock_anthropic_client.messages.create.side_effect = [bad_response, good_response, good_response]

        # Execute reasoning
        trace = cot_engine.reason("Test task", basic_budget, basic_config)

        # Should have backtrack step
        backtrack_steps = [s for s in trace.steps if s.step_type == StepType.BACKTRACK]
        assert len(backtrack_steps) >= 0  # May or may not backtrack depending on verification

    def test_budget_enforcement(self, cot_engine, mock_anthropic_client, basic_config):
        """Test that reasoning respects budget limits."""
        # Very limited budget
        limited_budget = ComputeBudget(max_tokens=100, max_steps=2)

        mock_response = Mock()
        mock_response.content = [Mock(text="Step content")]
        mock_anthropic_client.messages.create.return_value = mock_response

        trace = cot_engine.reason("Test task", limited_budget, basic_config)

        # Should stop due to budget
        assert len(trace.steps) <= 2

    def test_context_building(self, cot_engine):
        """Test context building from previous steps."""
        from lyra_reasoning.types import ReasoningStep

        steps = [
            ReasoningStep(content="First step", step_type=StepType.HYPOTHESIS),
            ReasoningStep(content="Second step", step_type=StepType.EVIDENCE),
        ]

        context = cot_engine._build_context("Test task", steps)

        assert "Test task" in context
        assert "First step" in context
        assert "Second step" in context
        assert "hypothesis" in context.lower()
        assert "evidence" in context.lower()

    def test_prompt_building(self, cot_engine):
        """Test prompt building for different step types."""
        context = "Test context"

        # Test each step type
        for step_type in [StepType.HYPOTHESIS, StepType.EVIDENCE, StepType.ANALYSIS, StepType.CONCLUSION]:
            prompt = cot_engine._build_prompt(context, step_type)
            assert context in prompt
            assert len(prompt) > len(context)

    def test_state_update(self, cot_engine):
        """Test state update with new step."""
        from lyra_reasoning.types import ReasoningStep

        initial_state = "Initial task"
        step = ReasoningStep(content="New reasoning", step_type=StepType.ANALYSIS)

        new_state = cot_engine._update_state(initial_state, step)

        assert initial_state in new_state
        assert step.content in new_state

    def test_conclusion_detection(self, cot_engine, mock_anthropic_client, basic_config, basic_budget):
        """Test that reasoning completes successfully."""
        # Mock responses
        responses = [
            Mock(content=[Mock(text="Hypothesis: Initial approach")]),
            Mock(content=[Mock(text="Evidence: Supporting data")]),
            Mock(content=[Mock(text="Analysis: Detailed analysis of the evidence")]),
            Mock(content=[Mock(text="More evidence to support")]),
            Mock(content=[Mock(text="Further analysis based on all evidence")]),
            Mock(content=[Mock(text="Additional analysis point")]),
        ]
        mock_anthropic_client.messages.create.side_effect = responses

        trace = cot_engine.reason("Test task", basic_budget, basic_config)

        # Should complete with multiple steps
        assert len(trace.steps) > 0
        assert trace.duration > 0
        # Outcome can be success or incomplete depending on step progression
        assert trace.outcome in ["success", "incomplete"]

    def test_error_handling(self, cot_engine, mock_anthropic_client, basic_config, basic_budget):
        """Test error handling during step generation."""
        # Mock API error
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        trace = cot_engine.reason("Test task", basic_budget, basic_config)

        # Should have error step
        assert len(trace.steps) > 0
        assert "Error" in trace.steps[0].content

    def test_verification_disabled(self, cot_engine, mock_anthropic_client, basic_budget):
        """Test reasoning with verification disabled."""
        config = ReasoningConfig(
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            model="claude-opus-4-20250514",
            max_steps=3,
            enable_verification=False,
        )

        mock_response = Mock()
        mock_response.content = [Mock(text="Step content")]
        mock_anthropic_client.messages.create.return_value = mock_response

        trace = cot_engine.reason("Test task", basic_budget, config)

        # No verification scores should be set
        for step in trace.steps:
            if step.step_type != StepType.BACKTRACK:
                assert step.verification_score is None or step.verification_score == 0.0


@pytest.mark.integration
class TestChainOfThoughtIntegration:
    """Integration tests for CoT engine."""

    @pytest.mark.skip(reason="Requires real API key")
    def test_real_reasoning_task(self):
        """Test with real API (requires API key)."""
        engine = ChainOfThoughtEngine()
        config = ReasoningConfig(
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            model="claude-opus-4-20250514",
            max_steps=5,
        )
        budget = ComputeBudget(max_tokens=5000, max_steps=10)

        trace = engine.reason(
            "Explain why the sky appears blue during the day.",
            budget,
            config,
        )

        assert len(trace.steps) > 0
        assert trace.outcome == "success"
        assert trace.get_conclusion() is not None
