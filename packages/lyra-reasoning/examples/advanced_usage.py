"""
Advanced usage examples for Deep Reasoning Agent.
"""

from lyra_reasoning import DeepReasoningAgent, ReasoningConfig, ReasoningStrategy, ReasoningDepth


def example_custom_config():
    """Example: Using custom configuration."""
    print("=" * 60)
    print("Advanced Example 1: Custom Configuration")
    print("=" * 60)
    
    agent = DeepReasoningAgent()
    
    # Create custom config
    config = ReasoningConfig(
        strategy=ReasoningStrategy.TREE_SEARCH,
        depth=ReasoningDepth.COMPREHENSIVE,
        max_tokens=15000,
        max_steps=100,
        temperature=0.8,
        verification_threshold=0.8,
        enable_backtracking=True,
    )
    
    result = agent.reason(
        task="Design an optimal algorithm for real-time anomaly detection in streaming data",
        config=config,
    )
    
    print(f"\nTask: {result.task}")
    print(f"Strategy: {result.strategy_used.value}")
    print(f"Tokens Used: {result.tokens_used}")
    print(f"Verification: {result.verification_score:.2f}")
    print(f"\nSolution:\n{result.conclusion}")


def example_research_pipeline():
    """Example: Complete research pipeline."""
    print("\n" + "=" * 60)
    print("Advanced Example 2: Research Pipeline")
    print("=" * 60)
    
    agent = DeepReasoningAgent()
    
    research_topic = "quantum error correction codes"
    
    # Phase 1: Generate hypotheses
    print("\nPhase 1: Hypothesis Generation")
    hypotheses = agent.reason(
        task=f"Generate novel research hypotheses for {research_topic}",
        strategy="hypothesis",
        depth="comprehensive",
    )
    print(f"Generated hypotheses (score: {hypotheses.verification_score:.2f})")
    
    # Phase 2: Analyze feasibility
    print("\nPhase 2: Feasibility Analysis")
    analysis = agent.reason(
        task=f"Analyze the feasibility and potential impact of research on {research_topic}",
        strategy="cot",
        depth="comprehensive",
    )
    print(f"Analysis complete (score: {analysis.verification_score:.2f})")
    
    # Phase 3: Debate approach
    print("\nPhase 3: Approach Debate")
    debate = agent.reason(
        task=f"Debate the best research methodology for {research_topic}",
        strategy="debate",
        depth="comprehensive",
    )
    print(f"Debate synthesis (score: {debate.verification_score:.2f})")
    
    # Phase 4: Synthesize findings
    print("\nPhase 4: Synthesis")
    synthesis = agent.reason(
        task=f"Synthesize a research proposal for {research_topic} based on the analysis",
        strategy="cot",
        depth="comprehensive",
    )
    
    print(f"\nFinal Research Proposal:\n{synthesis.conclusion}")
    print(f"\nPipeline Statistics:")
    print(f"  Total tokens: {hypotheses.tokens_used + analysis.tokens_used + debate.tokens_used + synthesis.tokens_used}")
    print(f"  Average verification: {(hypotheses.verification_score + analysis.verification_score + debate.verification_score + synthesis.verification_score) / 4:.2f}")


def example_iterative_refinement():
    """Example: Iterative refinement with feedback."""
    print("\n" + "=" * 60)
    print("Advanced Example 3: Iterative Refinement")
    print("=" * 60)
    
    agent = DeepReasoningAgent()
    
    problem = "Design a distributed consensus algorithm"
    
    # Iteration 1: Initial solution
    print("\nIteration 1: Initial Solution")
    solution_v1 = agent.reason(
        task=problem,
        strategy="tree_search",
        depth="standard",
    )
    print(f"V1 Score: {solution_v1.verification_score:.2f}")
    
    # Iteration 2: Refine based on analysis
    print("\nIteration 2: Refinement")
    solution_v2 = agent.reason(
        task=f"{problem} - improve upon previous approach considering fault tolerance",
        strategy="tree_search",
        depth="comprehensive",
    )
    print(f"V2 Score: {solution_v2.verification_score:.2f}")
    
    # Iteration 3: Final optimization
    print("\nIteration 3: Optimization")
    solution_v3 = agent.reason(
        task=f"{problem} - optimize for performance and scalability",
        strategy="tree_search",
        depth="comprehensive",
    )
    print(f"V3 Score: {solution_v3.verification_score:.2f}")
    
    print(f"\nFinal Solution:\n{solution_v3.conclusion}")
    print(f"\nImprovement: {solution_v3.verification_score - solution_v1.verification_score:.2f}")


def example_multi_strategy_comparison():
    """Example: Compare multiple strategies on same task."""
    print("\n" + "=" * 60)
    print("Advanced Example 4: Multi-Strategy Comparison")
    print("=" * 60)
    
    agent = DeepReasoningAgent()
    
    task = "Explain the implications of P vs NP problem"
    
    strategies = [
        ("cot", "Chain of Thought"),
        ("tree_search", "Tree Search"),
        ("debate", "Multi-Agent Debate"),
    ]
    
    results = {}
    
    print(f"\nTask: {task}\n")
    
    for strategy_key, strategy_name in strategies:
        print(f"Running {strategy_name}...")
        result = agent.reason(
            task=task,
            strategy=strategy_key,
            depth="comprehensive",
        )
        
        results[strategy_name] = {
            "conclusion": result.conclusion,
            "verification": result.verification_score,
            "tokens": result.tokens_used,
            "duration": result.duration,
        }
    
    print("\n" + "=" * 60)
    print("Strategy Comparison Results")
    print("=" * 60)
    
    for strategy_name, metrics in results.items():
        print(f"\n{strategy_name}:")
        print(f"  Verification: {metrics['verification']:.2f}")
        print(f"  Tokens: {metrics['tokens']}")
        print(f"  Duration: {metrics['duration']:.2f}s")
        print(f"  Conclusion: {metrics['conclusion'][:200]}...")


def example_adaptive_reasoning():
    """Example: Adaptive reasoning based on difficulty."""
    print("\n" + "=" * 60)
    print("Advanced Example 5: Adaptive Reasoning")
    print("=" * 60)
    
    agent = DeepReasoningAgent()
    
    tasks = [
        ("What is 2 + 2?", "trivial"),
        ("Explain photosynthesis", "easy"),
        ("Analyze sorting algorithm complexity", "medium"),
        ("Prove the fundamental theorem of calculus", "hard"),
    ]
    
    print("\nAdaptive reasoning across difficulty levels:\n")
    
    for task, expected_difficulty in tasks:
        result = agent.reason(
            task=task,
            strategy="auto",  # Let agent adapt
            depth="standard",
        )
        
        print(f"Task: {task}")
        print(f"  Expected: {expected_difficulty}")
        print(f"  Strategy: {result.strategy_used.value}")
        print(f"  Tokens: {result.tokens_used}")
        print(f"  Verification: {result.verification_score:.2f}")
        print()


def example_knowledge_accumulation():
    """Example: Knowledge accumulation and reuse."""
    print("\n" + "=" * 60)
    print("Advanced Example 6: Knowledge Accumulation")
    print("=" * 60)
    
    agent = DeepReasoningAgent()
    
    # Build knowledge base
    print("\nBuilding knowledge base...")
    
    topics = [
        "neural networks",
        "backpropagation",
        "gradient descent",
        "convolutional neural networks",
        "recurrent neural networks",
    ]
    
    for topic in topics:
        agent.reason(
            task=f"Explain {topic}",
            strategy="cot",
            depth="standard",
        )
    
    # Now ask a related question
    print("\nAsking related question...")
    result = agent.reason(
        task="How do transformers improve upon RNNs?",
        strategy="auto",
        depth="comprehensive",
    )
    
    print(f"\nAnswer:\n{result.conclusion}")
    
    # Check memory
    similar = agent.memory.retrieve_similar("transformers", k=5)
    print(f"\nRetrieved {len(similar)} related traces from memory")
    
    # Get strategy recommendation
    recommended = agent.memory.get_best_strategy("deep learning architecture")
    print(f"Recommended strategy for similar tasks: {recommended.value}")


def example_performance_optimization():
    """Example: Performance optimization through evolution."""
    print("\n" + "=" * 60)
    print("Advanced Example 7: Performance Optimization")
    print("=" * 60)
    
    agent = DeepReasoningAgent()
    
    # Initial performance
    print("\nInitial Performance:")
    initial_stats = agent.get_stats()
    print(f"  Total traces: {initial_stats['total_traces']}")
    
    # Do extensive reasoning
    print("\nPerforming reasoning tasks...")
    for i in range(20):
        agent.reason(
            task=f"Analyze problem {i}",
            strategy="auto",
            depth="standard",
        )
    
    # Check performance
    mid_stats = agent.get_stats()
    print(f"\nMid-point Statistics:")
    print(f"  Total traces: {mid_stats['total_traces']}")
    
    # Run evolution
    print("\nRunning evolution...")
    evolution_report = agent.evolve()
    
    print(f"\nEvolution Results:")
    print(f"  Insights: {len(evolution_report['insights'])}")
    print(f"  Recommendations: {len(evolution_report['recommendations'])}")
    
    for insight in evolution_report['insights']:
        print(f"    - {insight}")
    
    # Continue reasoning with evolved strategies
    print("\nContinuing with evolved strategies...")
    for i in range(10):
        agent.reason(
            task=f"Optimize solution {i}",
            strategy="auto",
            depth="standard",
        )
    
    # Final performance
    final_stats = agent.get_stats()
    print(f"\nFinal Statistics:")
    print(f"  Total traces: {final_stats['total_traces']}")
    print(f"  Patterns learned: {final_stats['patterns_learned']}")


def main():
    """Run all advanced examples."""
    print("\n" + "=" * 60)
    print("Deep Reasoning Agent - Advanced Examples")
    print("=" * 60)
    
    examples = [
        example_custom_config,
        example_research_pipeline,
        example_iterative_refinement,
        example_multi_strategy_comparison,
        example_adaptive_reasoning,
        example_knowledge_accumulation,
        example_performance_optimization,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Advanced Examples Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
