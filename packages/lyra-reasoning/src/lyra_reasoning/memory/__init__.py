"""
Reasoning Memory - Store and learn from reasoning traces.
"""

import json
from collections import defaultdict
from pathlib import Path

from ..types import (
    ReasoningPattern,
    ReasoningStrategy,
    ReasoningTrace,
    StepType,  # noqa: F401
    StrategyPerformance,
)


class ReasoningMemory:
    """
    Stores and learns from reasoning traces.

    Features:
    - Store successful and failed traces
    - Pattern recognition
    - Strategy performance tracking
    - Cross-session learning
    """

    def __init__(self, storage_path: str = ".lyra/reasoning/"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.traces: list[ReasoningTrace] = []
        self.patterns: dict[str, ReasoningPattern] = {}
        self.strategy_stats: dict[ReasoningStrategy, StrategyPerformance] = {}

        # Load existing data
        self._load()

    def store(self, trace: ReasoningTrace) -> None:
        """
        Store a reasoning trace.

        Args:
            trace: Reasoning trace to store
        """
        self.traces.append(trace)

        # Extract patterns
        patterns = self._extract_patterns(trace)
        for pattern in patterns:
            if pattern.name not in self.patterns:
                self.patterns[pattern.name] = pattern
            else:
                # Update existing pattern
                existing = self.patterns[pattern.name]
                existing.usage_count += 1
                existing.avg_tokens = (existing.avg_tokens + pattern.avg_tokens) / 2
                existing.avg_duration = (existing.avg_duration + pattern.avg_duration) / 2

        # Update strategy stats
        self._update_strategy_stats(trace)

        # Persist to disk
        self._save()

    def retrieve_similar(self, task: str, k: int = 5) -> list[ReasoningTrace]:
        """
        Find similar past reasoning traces.

        Args:
            task: Task to find similar traces for
            k: Number of traces to return

        Returns:
            List of similar traces
        """
        if not self.traces:
            return []

        # Simple similarity based on keyword overlap
        task_words = set(task.lower().split())

        scored_traces = []
        for trace in self.traces:
            trace_words = set(trace.task.lower().split())
            overlap = len(task_words & trace_words)
            similarity = overlap / max(len(task_words), len(trace_words))
            scored_traces.append((similarity, trace))

        # Sort by similarity and return top k
        scored_traces.sort(key=lambda x: x[0], reverse=True)
        return [trace for _, trace in scored_traces[:k]]

    def get_best_strategy(self, task: str) -> ReasoningStrategy:
        """
        Recommend best strategy for a task.

        Args:
            task: Task to recommend strategy for

        Returns:
            Recommended strategy
        """
        # Find similar traces
        similar = self.retrieve_similar(task, k=10)

        if not similar:
            return ReasoningStrategy.CHAIN_OF_THOUGHT  # Default

        # Count strategy usage and success
        strategy_scores = defaultdict(lambda: {"uses": 0, "successes": 0})

        for trace in similar:
            strategy_scores[trace.strategy]["uses"] += 1
            if trace.outcome == "success":
                strategy_scores[trace.strategy]["successes"] += 1

        # Calculate success rates
        best_strategy = ReasoningStrategy.CHAIN_OF_THOUGHT
        best_rate = 0.0

        for strategy, stats in strategy_scores.items():
            if stats["uses"] > 0:
                rate = stats["successes"] / stats["uses"]
                if rate > best_rate:
                    best_rate = rate
                    best_strategy = strategy

        return best_strategy

    def get_patterns(self, pattern_type: str | None = None) -> list[ReasoningPattern]:
        """
        Get learned reasoning patterns.

        Args:
            pattern_type: Filter by pattern type

        Returns:
            List of patterns
        """
        patterns = list(self.patterns.values())

        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        return sorted(patterns, key=lambda p: p.success_rate, reverse=True)

    def get_strategy_performance(self) -> list[StrategyPerformance]:
        """
        Get performance metrics for all strategies.

        Returns:
            List of strategy performance metrics
        """
        return sorted(
            self.strategy_stats.values(),
            key=lambda s: s.success_rate,
            reverse=True,
        )

    def _extract_patterns(self, trace: ReasoningTrace) -> list[ReasoningPattern]:
        """Extract reasoning patterns from a trace."""
        patterns = []

        # Extract step sequence pattern
        step_sequence = [step.step_type for step in trace.steps]

        if len(step_sequence) >= 3:
            pattern_name = f"sequence_{'_'.join(s.value for s in step_sequence[:3])}"

            pattern = ReasoningPattern(
                name=pattern_name,
                description=f"Reasoning pattern: {' → '.join(s.value for s in step_sequence[:3])}",
                pattern_type="sequence",
                success_rate=1.0 if trace.outcome == "success" else 0.0,
                usage_count=1,
                avg_tokens=trace.token_count,
                avg_duration=trace.duration,
                applicable_tasks=[trace.task],
                steps_template=step_sequence,
            )

            patterns.append(pattern)

        return patterns

    def _update_strategy_stats(self, trace: ReasoningTrace) -> None:
        """Update strategy performance statistics."""
        strategy = trace.strategy

        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = StrategyPerformance(
                strategy=strategy,
                total_uses=0,
                success_count=0,
                failure_count=0,
                avg_tokens=0.0,
                avg_duration=0.0,
                avg_verification_score=0.0,
            )

        stats = self.strategy_stats[strategy]

        # Update counts
        stats.total_uses += 1
        if trace.outcome == "success":
            stats.success_count += 1
        else:
            stats.failure_count += 1

        # Update averages
        n = stats.total_uses
        stats.avg_tokens = ((n - 1) * stats.avg_tokens + trace.token_count) / n
        stats.avg_duration = ((n - 1) * stats.avg_duration + trace.duration) / n

        if trace.verification:
            stats.avg_verification_score = (
                (n - 1) * stats.avg_verification_score + trace.verification.overall_score
            ) / n

    def _save(self) -> None:
        """Persist memory to disk."""
        # Save traces
        traces_file = self.storage_path / "traces.jsonl"
        with open(traces_file, "w") as f:
            for trace in self.traces[-100:]:  # Keep last 100 traces
                # Convert to dict for JSON serialization
                trace_dict = {
                    "task": trace.task,
                    "strategy": trace.strategy.value,
                    "outcome": trace.outcome,
                    "duration": trace.duration,
                    "token_count": trace.token_count,
                    "timestamp": trace.timestamp.isoformat(),
                    "num_steps": len(trace.steps),
                }
                f.write(json.dumps(trace_dict) + "\n")

        # Save strategy stats
        stats_file = self.storage_path / "strategy_stats.json"
        stats_dict = {
            strategy.value: {
                "total_uses": stats.total_uses,
                "success_count": stats.success_count,
                "failure_count": stats.failure_count,
                "avg_tokens": stats.avg_tokens,
                "avg_duration": stats.avg_duration,
                "avg_verification_score": stats.avg_verification_score,
            }
            for strategy, stats in self.strategy_stats.items()
        }
        with open(stats_file, "w") as f:
            json.dump(stats_dict, f, indent=2)

    def _load(self) -> None:
        """Load memory from disk."""
        # Load strategy stats
        stats_file = self.storage_path / "strategy_stats.json"
        if stats_file.exists():
            with open(stats_file) as f:
                stats_dict = json.load(f)

                for strategy_str, stats_data in stats_dict.items():
                    strategy = ReasoningStrategy(strategy_str)
                    self.strategy_stats[strategy] = StrategyPerformance(
                        strategy=strategy,
                        total_uses=stats_data["total_uses"],
                        success_count=stats_data["success_count"],
                        failure_count=stats_data["failure_count"],
                        avg_tokens=stats_data["avg_tokens"],
                        avg_duration=stats_data["avg_duration"],
                        avg_verification_score=stats_data["avg_verification_score"],
                    )
