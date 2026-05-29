"""
Benchmark tests for Deep Reasoning Agent.

These tests measure performance characteristics and can be used
to track improvements over time.
"""

import os
import time

import pytest

from lyra_reasoning import DeepReasoningAgent, ReasoningStrategy

# Skip benchmarks if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_simple_task_latency(self):
        """Benchmark latency for simple tasks."""
        agent = DeepReasoningAgent()

        start = time.time()
        result = agent.reason(
            task="What is 5 + 7?",
            strategy="cot",
            depth="quick",
        )
        duration = time.time() - start

        assert result.success
        assert duration < 30.0  # Should complete quickly
        print(f"\nSimple task latency: {duration:.2f}s")

    def test_medium_task_latency(self):
        """Benchmark latency for medium tasks."""
        agent = DeepReasoningAgent()

        start = time.time()
        result = agent.reason(
            task="Explain the difference between supervised and unsupervised learning",
            strategy="cot",
            depth="standard",
        )
        duration = time.time() - start

        assert result.success
        assert duration < 60.0  # Should complete in reasonable time
        print(f"\nMedium task latency: {duration:.2f}s")

    def test_complex_task_latency(self):
        """Benchmark latency for complex tasks."""
        agent = DeepReasoningAgent()

        start = time.time()
        result = agent.reason(
            task="Analyze the computational complexity of various sorting algorithms "
                 "and explain when each should be used",
            strategy="cot",
            depth="comprehensive",
        )
        duration = time.time() - start

        assert result.success
        assert duration < 120.0  # Complex tasks take longer
        print(f"\nComplex task latency: {duration:.2f}s")

    def test_token_efficiency(self):
        """Benchmark token efficiency."""
        agent = DeepReasoningAgent()

        task = "Explain photosynthesis"

        # Quick depth
        quick = agent.reason(task, strategy="cot", depth="quick")

        # Standard depth
        standard = agent.reason(task, strategy="cot", depth="standard")

        # Comprehensive depth
        comprehensive = agent.reason(task, strategy="cot", depth="comprehensive")

        print("\nToken usage:")
        print(f"  Quick: {quick.tokens_used}")
        print(f"  Standard: {standard.tokens_used}")
        print(f"  Comprehensive: {comprehensive.tokens_used}")

        # Verify scaling
        assert quick.tokens_used < standard.tokens_used
        assert standard.tokens_used < comprehensive.tokens_used

    def test_strategy_comparison(self):
        """Compare performance across strategies."""
        agent = DeepReasoningAgent()

        task = "Should we invest in renewable energy?"

        strategies = [
            ("cot", ReasoningStrategy.CHAIN_OF_THOUGHT),
            ("tree_search", ReasoningStrategy.TREE_SEARCH),
            ("debate", ReasoningStrategy.DEBATE),
        ]

        results = {}

        for strategy_name, _strategy_enum in strategies:
            start = time.time()
            result = agent.reason(task, strategy=strategy_name, depth="standard")
            duration = time.time() - start

            results[strategy_name] = {
                "duration": duration,
                "tokens": result.tokens_used,
                "verification": result.verification_score,
                "success": result.success,
            }

        print("\nStrategy comparison:")
        for strategy, metrics in results.items():
            print(f"  {strategy}:")
            print(f"    Duration: {metrics['duration']:.2f}s")
            print(f"    Tokens: {metrics['tokens']}")
            print(f"    Verification: {metrics['verification']:.2f}")
            print(f"    Success: {metrics['success']}")


class TestQualityBenchmarks:
    """Quality benchmark tests."""

    def test_verification_accuracy(self):
        """Test verification system accuracy."""
        agent = DeepReasoningAgent()

        # Good reasoning should score high
        good_result = agent.reason(
            task="Prove that the sum of angles in a triangle is 180 degrees",
            strategy="cot",
            depth="comprehensive",
        )

        # Simple task should also score well
        simple_result = agent.reason(
            task="What is 10 + 5?",
            strategy="cot",
            depth="quick",
        )

        print("\nVerification scores:")
        print(f"  Complex proof: {good_result.verification_score:.2f}")
        print(f"  Simple arithmetic: {simple_result.verification_score:.2f}")

        # Both should pass verification
        assert good_result.verification_score >= 0.6
        assert simple_result.verification_score >= 0.6

    def test_consistency(self):
        """Test reasoning consistency."""
        agent = DeepReasoningAgent()

        task = "Explain why water boils at 100°C at sea level"

        # Run same task multiple times
        results = []
        for _ in range(3):
            result = agent.reason(task, strategy="cot", depth="standard")
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)

        # Verification scores should be similar
        scores = [r.verification_score for r in results]
        avg_score = sum(scores) / len(scores)

        print("\nConsistency test:")
        print(f"  Scores: {scores}")
        print(f"  Average: {avg_score:.2f}")
        print(f"  Std dev: {(sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5:.2f}")


class TestScalabilityBenchmarks:
    """Scalability benchmark tests."""

    def test_memory_scaling(self):
        """Test memory system scaling."""
        agent = DeepReasoningAgent()

        # Add many traces
        num_traces = 20

        start = time.time()
        for i in range(num_traces):
            agent.reason(
                task=f"Test task {i}",
                strategy="cot",
                depth="quick",
            )
        duration = time.time() - start

        print("\nMemory scaling:")
        print(f"  {num_traces} traces in {duration:.2f}s")
        print(f"  Average: {duration / num_traces:.2f}s per trace")

        # Verify memory contains traces
        assert len(agent.memory.traces) >= num_traces

    def test_retrieval_performance(self):
        """Test memory retrieval performance."""
        agent = DeepReasoningAgent()

        # Add traces
        for i in range(50):
            agent.reason(
                task=f"Machine learning topic {i}",
                strategy="cot",
                depth="quick",
            )

        # Test retrieval speed
        start = time.time()
        similar = agent.memory.retrieve_similar("Deep learning", k=10)
        duration = time.time() - start

        print("\nRetrieval performance:")
        print(f"  Retrieved {len(similar)} traces in {duration:.4f}s")

        assert duration < 1.0  # Should be fast

    def test_evolution_performance(self):
        """Test evolution cycle performance."""
        agent = DeepReasoningAgent()

        # Build history
        for i in range(20):
            agent.reason(
                task=f"Task {i}",
                strategy="auto",
                depth="quick",
            )

        # Run evolution
        start = time.time()
        report = agent.evolve()
        duration = time.time() - start

        print("\nEvolution performance:")
        print(f"  Evolution cycle: {duration:.2f}s")
        print(f"  Insights generated: {len(report['insights'])}")

        assert duration < 5.0  # Should be reasonably fast


class TestRegressionBenchmarks:
    """Regression tests to catch performance degradation."""

    def test_baseline_performance(self):
        """Establish baseline performance metrics."""
        agent = DeepReasoningAgent()

        # Standard test case
        task = "Explain the concept of recursion in programming"

        start = time.time()
        result = agent.reason(task, strategy="cot", depth="standard")
        duration = time.time() - start

        metrics = {
            "duration": duration,
            "tokens": result.tokens_used,
            "verification": result.verification_score,
            "success": result.success,
        }

        print("\nBaseline metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Assert reasonable bounds
        assert duration < 60.0
        assert result.tokens_used < 20000
        assert result.verification_score >= 0.5
        assert result.success is True

    def test_quality_regression(self):
        """Test for quality regression."""
        agent = DeepReasoningAgent()

        # Test cases with expected high quality
        test_cases = [
            "What is 2 + 2?",
            "Explain gravity",
            "Why is the sky blue?",
        ]

        results = []
        for task in test_cases:
            result = agent.reason(task, strategy="cot", depth="standard")
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)

        # Average verification should be reasonable
        avg_verification = sum(r.verification_score for r in results) / len(results)

        print("\nQuality regression test:")
        print(f"  Average verification: {avg_verification:.2f}")

        assert avg_verification >= 0.6


if __name__ == "__main__":
    # Run benchmarks with verbose output
    pytest.main([__file__, "-v", "-s"])
