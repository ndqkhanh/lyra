"""
Deep Reasoning Research Agent - Main interface.
"""

from typing import Optional

from .engines import (
    ChainOfThoughtEngine,
    EnhancedDebateEngine,
    HypothesisEngine,
    TreeSearchEngine,
)
from .evolution import EvolutionEngine
from .memory import ReasoningMemory
from .orchestrator import ReasoningOrchestrator
from .types import (
    ReasoningConfig,
    ReasoningResult,
    ReasoningStrategy,
    ReasoningTrace,
)
from .verification import VerificationSystem


class DeepReasoningAgent:
    """
    Deep Reasoning Research Agent.

    Combines:
    - Test-time compute scaling
    - Multiple reasoning engines
    - Multi-level verification
    - Reasoning memory
    - Self-improvement

    Example:
        >>> agent = DeepReasoningAgent()
        >>> result = agent.reason(
        ...     task="Analyze transformer attention mechanisms",
        ...     strategy="auto",
        ...     depth="comprehensive"
        ... )
        >>> print(result.conclusion)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        storage_path: str = ".lyra/reasoning/",
    ):
        """
        Initialize Deep Reasoning Agent.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
            storage_path: Path for reasoning memory storage
        """
        # Initialize components
        self.orchestrator = ReasoningOrchestrator()
        self.memory = ReasoningMemory(storage_path)
        self.verification = VerificationSystem(api_key)
        self.evolution = EvolutionEngine(self.memory)

        # Initialize engines
        self.engines = {
            ReasoningStrategy.CHAIN_OF_THOUGHT: ChainOfThoughtEngine(api_key),
            ReasoningStrategy.TREE_SEARCH: TreeSearchEngine(api_key),
            ReasoningStrategy.DEBATE: EnhancedDebateEngine(api_key),
            ReasoningStrategy.HYPOTHESIS: HypothesisEngine(api_key),
        }

    def reason(
        self,
        task: str,
        strategy: str = "auto",
        depth: str = "standard",
        config: Optional[ReasoningConfig] = None,
    ) -> ReasoningResult:
        """
        Execute deep reasoning on a task.

        Args:
            task: The task to reason about
            strategy: Reasoning strategy ("auto", "cot", "tree_search", "debate", "hypothesis")
            depth: Reasoning depth ("quick", "standard", "comprehensive")
            config: Optional custom configuration

        Returns:
            Reasoning result with conclusion and trace
        """
        # Create config if not provided
        if config is None:
            config = ReasoningConfig(
                strategy=ReasoningStrategy(strategy),
                depth=depth,
            )

        # Prepare for reasoning
        selected_strategy, budget, difficulty = self.orchestrator.prepare(task, config)

        # Check memory for similar tasks
        similar_traces = self.memory.retrieve_similar(task, k=3)
        if similar_traces and config.strategy == ReasoningStrategy.AUTO:
            # Use best strategy from memory
            recommended_strategy = self.memory.get_best_strategy(task)
            selected_strategy = recommended_strategy

        # Execute reasoning with selected engine
        engine = self.engines[selected_strategy]
        trace = engine.reason(task, budget, config)

        # Verify reasoning
        verification = self.verification.verify(trace)
        trace.verification = verification

        # Store in memory
        self.memory.store(trace)

        # Record execution
        self.orchestrator.record_execution(
            selected_strategy,
            verification.passed,
            trace.token_count,
            trace.duration,
        )

        # Create result
        conclusion = trace.get_conclusion() or "No conclusion reached"

        result = ReasoningResult(
            task=task,
            conclusion=conclusion,
            reasoning_trace={
                "strategy": selected_strategy.value,
                "num_steps": len(trace.steps),
                "duration": trace.duration,
                "outcome": trace.outcome,
            },
            verification_score=verification.overall_score,
            strategy_used=selected_strategy,
            tokens_used=trace.token_count,
            duration=trace.duration,
            success=verification.passed,
            metadata={
                "difficulty": difficulty.level.value,
                "step_scores": verification.step_scores,
                "trace_score": verification.trace_score,
            },
        )

        return result

    def get_full_trace(self, task: str, **kwargs) -> ReasoningTrace:
        """
        Get full reasoning trace (for debugging/analysis).

        Args:
            task: The task to reason about
            **kwargs: Arguments passed to reason()

        Returns:
            Complete reasoning trace
        """
        config = kwargs.get("config")
        if config is None:
            config = ReasoningConfig(
                strategy=ReasoningStrategy(kwargs.get("strategy", "auto")),
                depth=kwargs.get("depth", "standard"),
            )

        selected_strategy, budget, _ = self.orchestrator.prepare(task, config)
        engine = self.engines[selected_strategy]
        trace = engine.reason(task, budget, config)

        # Verify
        verification = self.verification.verify(trace)
        trace.verification = verification

        return trace

    def evolve(self) -> dict:
        """
        Run evolution cycle to improve reasoning capabilities.

        Returns:
            Evolution report
        """
        report = self.evolution.evolve()

        return {
            "new_strategies": report.new_strategies,
            "pruned_strategies": report.pruned_strategies,
            "performance_delta": report.performance_delta,
            "insights": report.insights,
            "recommendations": self.evolution.get_recommendations(),
        }

    def get_stats(self) -> dict:
        """
        Get reasoning statistics.

        Returns:
            Statistics dictionary
        """
        strategy_performance = self.memory.get_strategy_performance()
        patterns = self.memory.get_patterns()

        return {
            "total_traces": len(self.memory.traces),
            "strategy_performance": [
                {
                    "strategy": perf.strategy.value,
                    "success_rate": perf.success_rate,
                    "total_uses": perf.total_uses,
                    "avg_tokens": perf.avg_tokens,
                    "avg_duration": perf.avg_duration,
                }
                for perf in strategy_performance
            ],
            "patterns_learned": len(patterns),
            "top_patterns": [
                {
                    "name": p.name,
                    "success_rate": p.success_rate,
                    "usage_count": p.usage_count,
                }
                for p in patterns[:5]
            ],
        }
