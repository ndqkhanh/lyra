"""
Basic usage examples for Deep Reasoning Agent.
"""

from lyra_reasoning import DeepReasoningAgent


def example_simple_reasoning():
    """Example: Simple reasoning task."""
    print("=" * 60)
    print("Example 1: Simple Reasoning")
    print("=" * 60)

    agent = DeepReasoningAgent()

    result = agent.reason(
        task="Explain why the sky appears blue during the day",
        strategy="cot",
        depth="standard",
    )

    print(f"\nTask: {result.task}")
    print(f"\nConclusion:\n{result.conclusion}")
    print(f"\nVerification Score: {result.verification_score:.2f}")
    print(f"Tokens Used: {result.tokens_used}")
    print(f"Duration: {result.duration:.2f}s")
    print(f"Success: {result.success}")


def example_auto_strategy():
    """Example: Automatic strategy selection."""
    print("\n" + "=" * 60)
    print("Example 2: Automatic Strategy Selection")
    print("=" * 60)

    agent = DeepReasoningAgent()

    result = agent.reason(
        task="Analyze the time complexity of merge sort and explain when it's optimal",
        strategy="auto",  # Let the agent choose
        depth="comprehensive",
    )

    print(f"\nTask: {result.task}")
    print(f"\nStrategy Selected: {result.strategy_used.value}")
    print(f"\nConclusion:\n{result.conclusion}")
    print("\nMetadata:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")


def example_hypothesis_generation():
    """Example: Hypothesis generation."""
    print("\n" + "=" * 60)
    print("Example 3: Hypothesis Generation")
    print("=" * 60)

    agent = DeepReasoningAgent()

    result = agent.reason(
        task="Generate novel hypotheses for improving battery energy density",
        strategy="hypothesis",
        depth="comprehensive",
    )

    print(f"\nTask: {result.task}")
    print(f"\nGenerated Hypotheses:\n{result.conclusion}")
    print(f"\nVerification Score: {result.verification_score:.2f}")


def example_debate():
    """Example: Multi-perspective debate."""
    print("\n" + "=" * 60)
    print("Example 4: Multi-Perspective Debate")
    print("=" * 60)

    agent = DeepReasoningAgent()

    result = agent.reason(
        task="Should artificial general intelligence research be regulated?",
        strategy="debate",
        depth="comprehensive",
    )

    print(f"\nTask: {result.task}")
    print(f"\nDebate Synthesis:\n{result.conclusion}")
    print(f"\nVerification Score: {result.verification_score:.2f}")


def example_tree_search():
    """Example: Tree search for optimal solutions."""
    print("\n" + "=" * 60)
    print("Example 5: Tree Search")
    print("=" * 60)

    agent = DeepReasoningAgent()

    result = agent.reason(
        task="Find the optimal approach to implement a caching system with LRU eviction",
        strategy="tree_search",
        depth="comprehensive",
    )

    print(f"\nTask: {result.task}")
    print(f"\nOptimal Solution:\n{result.conclusion}")
    print(f"\nVerification Score: {result.verification_score:.2f}")


def example_full_trace():
    """Example: Getting full reasoning trace."""
    print("\n" + "=" * 60)
    print("Example 6: Full Reasoning Trace")
    print("=" * 60)

    agent = DeepReasoningAgent()

    trace = agent.get_full_trace(
        task="Prove that the square root of 2 is irrational",
        strategy="cot",
        depth="comprehensive",
    )

    print(f"\nTask: {trace.task}")
    print(f"Strategy: {trace.strategy.value}")
    print(f"Number of Steps: {len(trace.steps)}")
    print("\nReasoning Steps:")

    for i, step in enumerate(trace.steps, 1):
        print(f"\n  Step {i} ({step.step_type.value}):")
        print(f"    {step.content[:200]}...")
        print(f"    Verification: {step.verification_score:.2f}")

    print(f"\nOverall Verification: {trace.verification.overall_score:.2f}")


def example_memory_and_learning():
    """Example: Memory and learning capabilities."""
    print("\n" + "=" * 60)
    print("Example 7: Memory and Learning")
    print("=" * 60)

    agent = DeepReasoningAgent()

    # Do some reasoning
    print("\nPerforming reasoning tasks...")
    for i in range(5):
        agent.reason(
            task=f"Explain concept {i} in machine learning",
            strategy="auto",
            depth="standard",
        )

    # Get statistics
    stats = agent.get_stats()

    print("\nAgent Statistics:")
    print(f"  Total Traces: {stats['total_traces']}")
    print(f"  Patterns Learned: {stats['patterns_learned']}")

    print("\n  Strategy Performance:")
    for perf in stats['strategy_performance']:
        print(f"    {perf['strategy']}:")
        print(f"      Success Rate: {perf['success_rate']:.2%}")
        print(f"      Total Uses: {perf['total_uses']}")
        print(f"      Avg Tokens: {perf['avg_tokens']:.0f}")

    # Retrieve similar reasoning
    print("\n  Retrieving similar reasoning...")
    similar = agent.memory.retrieve_similar("deep learning", k=3)
    print(f"  Found {len(similar)} similar traces")


def example_evolution():
    """Example: Self-improvement through evolution."""
    print("\n" + "=" * 60)
    print("Example 8: Evolution and Self-Improvement")
    print("=" * 60)

    agent = DeepReasoningAgent()

    # Build history
    print("\nBuilding reasoning history...")
    for i in range(10):
        agent.reason(
            task=f"Solve problem {i}",
            strategy="auto",
            depth="standard",
        )

    # Run evolution
    print("\nRunning evolution cycle...")
    report = agent.evolve()

    print("\nEvolution Report:")
    print(f"  New Strategies: {report['new_strategies']}")
    print(f"  Pruned Strategies: {report['pruned_strategies']}")

    print("\n  Insights:")
    for insight in report['insights']:
        print(f"    - {insight}")

    print("\n  Recommendations:")
    for rec in report['recommendations']:
        print(f"    - {rec}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Deep Reasoning Agent - Usage Examples")
    print("=" * 60)

    examples = [
        example_simple_reasoning,
        example_auto_strategy,
        example_hypothesis_generation,
        example_debate,
        example_tree_search,
        example_full_trace,
        example_memory_and_learning,
        example_evolution,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")

    print("\n" + "=" * 60)
    print("Examples Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
