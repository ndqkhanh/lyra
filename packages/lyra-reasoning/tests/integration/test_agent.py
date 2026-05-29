"""
Integration tests for Deep Reasoning Agent.
"""

import os

import pytest

from lyra_reasoning import DeepReasoningAgent, ReasoningStrategy

# Skip tests if no API key is available
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)


class TestDeepReasoningAgent:
    """Integration tests for DeepReasoningAgent."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = DeepReasoningAgent()

        assert agent.orchestrator is not None
        assert agent.memory is not None
        assert agent.verification is not None
        assert agent.evolution is not None
        assert len(agent.engines) > 0

    def test_simple_reasoning(self):
        """Test simple reasoning task."""
        agent = DeepReasoningAgent()

        result = agent.reason(
            task="What is 2 + 2?",
            strategy="cot",
            depth="quick",
        )

        assert result is not None
        assert result.conclusion is not None
        assert result.success is not None
        assert 0.0 <= result.verification_score <= 1.0

    def test_chain_of_thought(self):
        """Test chain-of-thought reasoning."""
        agent = DeepReasoningAgent()

        result = agent.reason(
            task="Explain why the sky appears blue",
            strategy="cot",
            depth="standard",
        )

        assert result is not None
        assert len(result.conclusion) > 0
        assert result.strategy_used == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert result.tokens_used > 0

    def test_tree_search(self):
        """Test tree search reasoning."""
        agent = DeepReasoningAgent()

        result = agent.reason(
            task="Find the optimal path through a decision tree",
            strategy="tree_search",
            depth="standard",
        )

        assert result is not None
        assert result.strategy_used == ReasoningStrategy.TREE_SEARCH

    def test_debate(self):
        """Test debate reasoning."""
        agent = DeepReasoningAgent()

        result = agent.reason(
            task="Should AI systems be regulated?",
            strategy="debate",
            depth="standard",
        )

        assert result is not None
        assert result.strategy_used == ReasoningStrategy.DEBATE

    def test_hypothesis(self):
        """Test hypothesis generation."""
        agent = DeepReasoningAgent()

        result = agent.reason(
            task="Generate hypotheses for improving battery technology",
            strategy="hypothesis",
            depth="standard",
        )

        assert result is not None
        assert result.strategy_used == ReasoningStrategy.HYPOTHESIS

    def test_auto_strategy(self):
        """Test automatic strategy selection."""
        agent = DeepReasoningAgent()

        result = agent.reason(
            task="Analyze the complexity of quicksort algorithm",
            strategy="auto",
            depth="standard",
        )

        assert result is not None
        assert result.strategy_used != ReasoningStrategy.AUTO

    def test_depth_scaling(self):
        """Test that depth affects reasoning."""
        agent = DeepReasoningAgent()

        task = "Explain quantum entanglement"

        quick_result = agent.reason(task, strategy="cot", depth="quick")
        standard_result = agent.reason(task, strategy="cot", depth="standard")
        comprehensive_result = agent.reason(task, strategy="cot", depth="comprehensive")

        # More depth should use more tokens
        assert quick_result.tokens_used < standard_result.tokens_used
        assert standard_result.tokens_used < comprehensive_result.tokens_used

    def test_get_full_trace(self):
        """Test getting full reasoning trace."""
        agent = DeepReasoningAgent()

        trace = agent.get_full_trace(
            task="Simple test task",
            strategy="cot",
            depth="quick",
        )

        assert trace is not None
        assert len(trace.steps) > 0
        assert trace.verification is not None

    def test_memory_storage(self):
        """Test that reasoning is stored in memory."""
        agent = DeepReasoningAgent()

        initial_count = len(agent.memory.traces)

        agent.reason(
            task="Test memory storage",
            strategy="cot",
            depth="quick",
        )

        final_count = len(agent.memory.traces)

        assert final_count > initial_count

    def test_memory_retrieval(self):
        """Test retrieving similar reasoning from memory."""
        agent = DeepReasoningAgent()

        # Store some reasoning
        agent.reason(
            task="Explain machine learning",
            strategy="cot",
            depth="quick",
        )

        # Retrieve similar
        similar = agent.memory.retrieve_similar("Explain deep learning", k=5)

        assert isinstance(similar, list)

    def test_get_stats(self):
        """Test getting agent statistics."""
        agent = DeepReasoningAgent()

        # Do some reasoning
        agent.reason(task="Test 1", strategy="cot", depth="quick")
        agent.reason(task="Test 2", strategy="tree_search", depth="quick")

        stats = agent.get_stats()

        assert "total_traces" in stats
        assert "strategy_performance" in stats
        assert "patterns_learned" in stats
        assert stats["total_traces"] >= 2

    def test_evolution(self):
        """Test evolution cycle."""
        agent = DeepReasoningAgent()

        # Do some reasoning to build history
        for i in range(5):
            agent.reason(
                task=f"Test task {i}",
                strategy="cot",
                depth="quick",
            )

        # Run evolution
        report = agent.evolve()

        assert "new_strategies" in report
        assert "pruned_strategies" in report
        assert "insights" in report
        assert "recommendations" in report

    def test_verification_integration(self):
        """Test that verification is integrated properly."""
        agent = DeepReasoningAgent()

        result = agent.reason(
            task="Prove that 1 + 1 = 2",
            strategy="cot",
            depth="standard",
        )

        assert result.verification_score is not None
        assert 0.0 <= result.verification_score <= 1.0
        assert "step_scores" in result.metadata
        assert "trace_score" in result.metadata


class TestEndToEndScenarios:
    """End-to-end scenario tests."""

    def test_research_workflow(self):
        """Test a complete research workflow."""
        agent = DeepReasoningAgent()

        # Step 1: Generate hypotheses
        hypotheses = agent.reason(
            task="Generate hypotheses for improving neural network training",
            strategy="hypothesis",
            depth="standard",
        )

        assert hypotheses.success

        # Step 2: Analyze one hypothesis
        analysis = agent.reason(
            task="Analyze the feasibility of adaptive learning rates",
            strategy="cot",
            depth="comprehensive",
        )

        assert analysis.success

        # Step 3: Debate the approach
        debate = agent.reason(
            task="Should we use adaptive learning rates in production?",
            strategy="debate",
            depth="standard",
        )

        assert debate.success

        # Check that memory has all traces
        assert len(agent.memory.traces) >= 3

    def test_problem_solving_workflow(self):
        """Test a problem-solving workflow."""
        agent = DeepReasoningAgent()

        # Step 1: Understand the problem
        understanding = agent.reason(
            task="Explain the traveling salesman problem",
            strategy="cot",
            depth="standard",
        )

        assert understanding.success

        # Step 2: Explore solutions
        exploration = agent.reason(
            task="Find optimal solution approaches for TSP",
            strategy="tree_search",
            depth="comprehensive",
        )

        assert exploration.success

        # Step 3: Verify solution
        stats = agent.get_stats()
        assert stats["total_traces"] >= 2

    def test_iterative_improvement(self):
        """Test iterative improvement through evolution."""
        agent = DeepReasoningAgent()

        # Do initial reasoning
        for i in range(10):
            agent.reason(
                task=f"Solve problem {i}",
                strategy="auto",
                depth="standard",
            )

        # Get initial stats
        agent.get_stats()

        # Run evolution
        evolution_report = agent.evolve()

        # Check that evolution provides insights
        assert len(evolution_report["insights"]) > 0
        assert len(evolution_report["recommendations"]) > 0
