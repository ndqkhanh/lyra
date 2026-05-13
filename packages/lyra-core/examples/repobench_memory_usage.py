"""
Usage examples for RepoBench-Memory evaluation harness.

This module demonstrates how to use the RepoBench-Memory evaluation system
to benchmark Lyra's T3 memory system against the RepoBench benchmark.

Examples:
1. Basic completion evaluation
2. Retrieval evaluation
3. Integration with Lyra's LLM providers
4. Batch evaluation across multiple contexts
5. Result analysis and visualization
6. Custom evaluation with T3 memory
"""

from pathlib import Path

from lyra_core.eval.repobench_memory import (
    EvalContext,
    RepoBenchMemoryEval,
)


def example_1_basic_completion():
    """Example 1: Basic completion evaluation with mock generator."""
    print("=" * 80)
    print("Example 1: Basic Completion Evaluation")
    print("=" * 80)

    # Initialize evaluator
    evaluator = RepoBenchMemoryEval()

    # Load a small sample from RepoBench
    print("\nLoading RepoBench dataset...")
    samples = evaluator.load_dataset(
        language="python",
        context=EvalContext.CROSS_FILE_FIRST,
        split="test",
        max_samples=5,  # Small sample for demo
    )
    print(f"Loaded {len(samples)} samples")

    # Define a simple mock generator
    def mock_generator(context: str, cross_file_context: list[str]) -> str:
        """Mock generator that returns a simple completion."""
        # In practice, this would call Lyra's LLM provider
        if "return" in context:
            return "return result"
        return "pass"

    # Evaluate
    print("\nEvaluating completion task...")
    result = evaluator.evaluate_completion(
        samples=samples,
        generate_fn=mock_generator,
        language="python",
        context=EvalContext.CROSS_FILE_FIRST,
    )

    # Print results
    print(f"\nResults:")
    print(f"  Exact Match: {result.metrics.exact_match:.2%}")
    print(f"  Edit Similarity: {result.metrics.edit_similarity:.2%}")
    print(f"  CodeBLEU: {result.metrics.codebleu:.2%}")
    print(f"  Samples: {result.metrics.num_samples}")

    # Save results
    output_path = Path("repobench_completion_results.json")
    evaluator.save_results(result, output_path)
    print(f"\nResults saved to: {output_path}")


def example_2_retrieval_evaluation():
    """Example 2: Retrieval evaluation with mock retriever."""
    print("\n" + "=" * 80)
    print("Example 2: Retrieval Evaluation")
    print("=" * 80)

    # Initialize evaluator
    evaluator = RepoBenchMemoryEval()

    # Load samples
    print("\nLoading RepoBench dataset...")
    samples = evaluator.load_dataset(
        language="python",
        context=EvalContext.CROSS_FILE_RANDOM,
        split="test",
        max_samples=5,
    )
    print(f"Loaded {len(samples)} samples")

    # Define a simple mock retriever
    def mock_retriever(context: str) -> list[str]:
        """Mock retriever that returns relevant snippets."""
        # In practice, this would use Lyra's retrieval system
        return [
            "import numpy as np",
            "from typing import List",
            "import pandas as pd",
        ]

    # Evaluate
    print("\nEvaluating retrieval task...")
    result = evaluator.evaluate_retrieval(
        samples=samples,
        retrieve_fn=mock_retriever,
        context=EvalContext.CROSS_FILE_RANDOM,
    )

    # Print results
    print(f"\nResults:")
    print(f"  Accuracy@1: {result.metrics.accuracy_at_1:.2%}")
    print(f"  Accuracy@3: {result.metrics.accuracy_at_3:.2%}")
    print(f"  Accuracy@5: {result.metrics.accuracy_at_5:.2%}")
    print(f"  Samples: {result.metrics.num_samples}")


def example_3_lyra_integration():
    """Example 3: Integration with Lyra's LLM providers."""
    print("\n" + "=" * 80)
    print("Example 3: Integration with Lyra's LLM Providers")
    print("=" * 80)

    # This example shows how to integrate with Lyra's actual LLM providers
    # Note: Requires Lyra's provider system to be set up

    try:
        from lyra_core.providers import get_provider

        # Initialize evaluator with T3 memory directory
        t3_memory_dir = Path.home() / ".lyra" / "memory" / "t3"
        evaluator = RepoBenchMemoryEval(t3_memory_dir=t3_memory_dir)

        # Load samples
        samples = evaluator.load_dataset(
            language="python",
            context=EvalContext.IN_FILE,
            split="test",
            max_samples=3,
        )

        # Get Lyra's LLM provider
        provider = get_provider("claude-sonnet-4")

        # Define generator using Lyra's provider
        def lyra_generator(context: str, cross_file_context: list[str]) -> str:
            """Generator using Lyra's LLM provider."""
            # Build prompt with context
            prompt = f"Complete the following code:\n\n{context}\n\nCompletion:"

            # Add cross-file context if available
            if cross_file_context:
                prompt = f"Relevant imports:\n" + "\n".join(cross_file_context) + f"\n\n{prompt}"

            # Generate completion
            response = provider.complete(prompt, max_tokens=100)
            return response.strip()

        # Evaluate
        result = evaluator.evaluate_completion(
            samples=samples,
            generate_fn=lyra_generator,
            language="python",
            context=EvalContext.IN_FILE,
        )

        print(f"\nResults with Lyra provider:")
        print(f"  Exact Match: {result.metrics.exact_match:.2%}")
        print(f"  Edit Similarity: {result.metrics.edit_similarity:.2%}")
        print(f"  CodeBLEU: {result.metrics.codebleu:.2%}")

    except ImportError:
        print("\nLyra provider system not available. Skipping this example.")


def example_4_batch_evaluation():
    """Example 4: Batch evaluation across multiple contexts."""
    print("\n" + "=" * 80)
    print("Example 4: Batch Evaluation Across Contexts")
    print("=" * 80)

    evaluator = RepoBenchMemoryEval()

    # Define mock generator
    def mock_generator(context: str, cross_file_context: list[str]) -> str:
        return "return result"

    # Evaluate across all three contexts
    contexts = [
        EvalContext.CROSS_FILE_FIRST,
        EvalContext.CROSS_FILE_RANDOM,
        EvalContext.IN_FILE,
    ]

    results = {}
    for ctx in contexts:
        print(f"\nEvaluating context: {ctx.value}")
        samples = evaluator.load_dataset(
            language="python",
            context=ctx,
            split="test",
            max_samples=5,
        )

        result = evaluator.evaluate_completion(
            samples=samples,
            generate_fn=mock_generator,
            language="python",
            context=ctx,
        )

        results[ctx.value] = result
        print(f"  EM: {result.metrics.exact_match:.2%}, "
              f"ES: {result.metrics.edit_similarity:.2%}, "
              f"CB: {result.metrics.codebleu:.2%}")

    # Compare results
    print("\n" + "-" * 80)
    print("Summary across contexts:")
    print("-" * 80)
    for ctx_name, result in results.items():
        print(f"{ctx_name:20s} | EM: {result.metrics.exact_match:.2%} | "
              f"ES: {result.metrics.edit_similarity:.2%} | "
              f"CB: {result.metrics.codebleu:.2%}")


def example_5_result_analysis():
    """Example 5: Detailed result analysis."""
    print("\n" + "=" * 80)
    print("Example 5: Detailed Result Analysis")
    print("=" * 80)

    evaluator = RepoBenchMemoryEval()

    # Load samples
    samples = evaluator.load_dataset(
        language="python",
        context=EvalContext.CROSS_FILE_FIRST,
        split="test",
        max_samples=3,
    )

    # Mock generator
    def mock_generator(context: str, cross_file_context: list[str]) -> str:
        return "return result"

    # Evaluate
    result = evaluator.evaluate_completion(
        samples=samples,
        generate_fn=mock_generator,
        language="python",
        context=EvalContext.CROSS_FILE_FIRST,
    )

    # Analyze per-sample results
    print("\nPer-sample analysis:")
    print("-" * 80)
    for i, sample_result in enumerate(result.per_sample_results, 1):
        print(f"\nSample {i}:")
        print(f"  Repo: {sample_result['repo_name']}")
        print(f"  File: {sample_result['file_path']}")
        print(f"  Prediction: {sample_result['prediction'][:50]}...")
        print(f"  Target: {sample_result['target'][:50]}...")
        print(f"  EM: {sample_result['exact_match']:.2f}")
        print(f"  ES: {sample_result['edit_similarity']:.2f}")
        print(f"  CB: {sample_result['codebleu']:.2f}")


def example_6_custom_t3_memory():
    """Example 6: Custom evaluation with T3 memory context."""
    print("\n" + "=" * 80)
    print("Example 6: Custom Evaluation with T3 Memory")
    print("=" * 80)

    # Create temporary T3 memory directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        t3_dir = Path(tmpdir)

        # Create sample T3 memory files
        user_md = t3_dir / "user.md"
        user_md.write_text("""
# User Memory

## Coding Preferences
- Prefer type hints in Python
- Use descriptive variable names
- Follow PEP 8 style guide
""")

        team_md = t3_dir / "team.md"
        team_md.write_text("""
# Team Memory

## Code Standards
- All functions must have docstrings
- Use pytest for testing
- Maximum line length: 100 characters
""")

        # Initialize evaluator with T3 memory
        evaluator = RepoBenchMemoryEval(t3_memory_dir=t3_dir)

        print(f"\nT3 memory directory: {t3_dir}")
        print(f"User memory: {user_md.exists()}")
        print(f"Team memory: {team_md.exists()}")

        # In a real implementation, the generator would load and use T3 memory
        def t3_aware_generator(context: str, cross_file_context: list[str]) -> str:
            """Generator that uses T3 memory for context."""
            # Load T3 memory (simplified)
            user_prefs = user_md.read_text()
            team_rules = team_md.read_text()

            # In practice, this would incorporate T3 memory into the prompt
            # and generate completions that follow user/team preferences
            return "return result  # Following team standards"

        # Evaluate
        samples = evaluator.load_dataset(
            language="python",
            context=EvalContext.IN_FILE,
            split="test",
            max_samples=2,
        )

        result = evaluator.evaluate_completion(
            samples=samples,
            generate_fn=t3_aware_generator,
            language="python",
            context=EvalContext.IN_FILE,
        )

        print(f"\nResults with T3 memory context:")
        print(f"  Exact Match: {result.metrics.exact_match:.2%}")
        print(f"  Edit Similarity: {result.metrics.edit_similarity:.2%}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("RepoBench-Memory Evaluation Harness - Usage Examples")
    print("=" * 80)

    try:
        example_1_basic_completion()
        example_2_retrieval_evaluation()
        example_3_lyra_integration()
        example_4_batch_evaluation()
        example_5_result_analysis()
        example_6_custom_t3_memory()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
