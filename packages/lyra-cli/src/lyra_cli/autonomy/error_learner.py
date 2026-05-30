"""Error Recovery Learner - Learns recovery strategies from execution traces.

Persists error patterns and successful recovery strategies across sessions,
enabling autonomous agents to improve error handling over time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from lyra_cli.autonomy.recovery.pattern_recognizer import (
    ErrorCategory,
    ErrorPattern,
    PatternRecognizer,
)
from lyra_cli.autonomy.recovery.retry_policy import RetryPolicy, RetryResult
from lyra_cli.autonomy.recovery.strategy_selector import (
    RecoveryAction,
    RecoveryStrategy,
    StrategySelector,
)


@dataclass(frozen=True)
class RecoveryTrace:
    """A complete trace of an error recovery attempt."""

    trace_id: str
    error_signature: str
    error_category: ErrorCategory
    strategies_tried: tuple[RecoveryAction, ...]
    successful_strategy: RecoveryAction | None
    attempts: int
    total_duration_ms: float
    resolved: bool
    timestamp: str


@dataclass(frozen=True)
class LearningReport:
    """Summary of what the error learner has learned."""

    total_errors: int
    total_recoveries: int
    success_rate: float
    most_common_error: str
    most_successful_strategy: str
    patterns_learned: int
    avg_recovery_time_ms: float


class ErrorRecoveryLearner:
    """Learns error recovery strategies from execution traces.

    Features:
    - Error classification and pattern recognition
    - Strategy selection with success/failure tracking
    - Retry policy with exponential backoff
    - Recovery trace recording
    - Learning report generation
    """

    def __init__(self, max_history_days: int = 30):
        self.recognizer = PatternRecognizer()
        self.selector = StrategySelector()
        self.retry = RetryPolicy()
        self._traces: list[RecoveryTrace] = []
        self._max_history_days = max_history_days

    def classify_error(
        self,
        error: Exception,
        context: dict | None = None,
    ) -> ErrorCategory:
        """Classify an error into a category.

        Args:
            error: The exception
            context: Optional execution context

        Returns:
            ErrorCategory
        """
        return self.recognizer.classify(error, context)

    def suggest_recovery(
        self,
        error: Exception,
        history: list[RecoveryTrace] | None = None,
        attempt: int = 0,
    ) -> RecoveryStrategy:
        """Suggest a recovery strategy for an error.

        Args:
            error: The exception
            history: Previous recovery traces
            attempt: Current attempt number

        Returns:
            RecoveryStrategy
        """
        # Learn this error pattern
        pattern = self.recognizer.learn_pattern(error)

        # Select strategy based on category and pattern
        return self.selector.select(error, pattern.category, pattern, attempt)

    def attempt_recovery(
        self,
        trace_id: str,
        error: Exception,
        attempt: int,
    ) -> tuple[RecoveryStrategy, RetryResult]:
        """Evaluate recovery and get retry decision.

        Args:
            trace_id: Unique trace identifier
            error: The exception
            attempt: Current attempt number

        Returns:
            Tuple of (strategy, retry_result)
        """
        category = self.classify_error(error)
        strategy = self.suggest_recovery(error, attempt=attempt)

        retry_result = self.retry.should_retry(trace_id, category.value, attempt)

        return strategy, retry_result

    def record_recovery(
        self,
        trace_id: str,
        error: Exception,
        strategies_tried: list[RecoveryAction],
        successful_strategy: RecoveryAction | None,
        attempts: int,
        duration_ms: float,
        resolved: bool,
    ) -> RecoveryTrace:
        """Record a recovery trace.

        Args:
            trace_id: Unique trace identifier
            error: The exception
            strategies_tried: List of strategies attempted
            successful_strategy: Strategy that worked (None if unresolved)
            attempts: Total attempts made
            duration_ms: Total recovery duration
            resolved: Whether the error was resolved

        Returns:
            RecoveryTrace
        """
        category = self.recognizer.classify(error)
        signature = self.recognizer.fingerprint(error)

        # Learn the pattern
        self.recognizer.learn_pattern(error)

        # Record success/failure
        if successful_strategy:
            for strategy in strategies_tried:
                is_success = strategy == successful_strategy
                if is_success:
                    self.selector.record_success(category, strategy)
                else:
                    self.selector.record_failure(category, strategy)

        trace = RecoveryTrace(
            trace_id=trace_id,
            error_signature=signature,
            error_category=category,
            strategies_tried=tuple(strategies_tried),
            successful_strategy=successful_strategy,
            attempts=attempts,
            total_duration_ms=duration_ms,
            resolved=resolved,
            timestamp=datetime.now().isoformat(),
        )
        self._traces.append(trace)

        # Prune old traces
        self._prune_old_traces()

        return trace

    def learn_pattern(
        self,
        error_sequence: list[Exception],
        successful_recovery: str | None = None,
    ) -> None:
        """Learn from an error sequence with a successful recovery.

        Args:
            error_sequence: List of exceptions in order
            successful_recovery: Recovery strategy that worked
        """
        self.recognizer.learn_sequence(error_sequence, successful_recovery)

    def get_recovery_history(
        self,
        category: ErrorCategory | None = None,
        limit: int = 20,
    ) -> list[RecoveryTrace]:
        """Get recovery history, optionally filtered by category.

        Args:
            category: Filter by error category (None for all)
            limit: Maximum number to return

        Returns:
            List of RecoveryTrace
        """
        if category:
            filtered = [t for t in self._traces if t.error_category == category]
        else:
            filtered = list(self._traces)

        return sorted(filtered, key=lambda t: t.timestamp, reverse=True)[:limit]

    def get_learning_report(self) -> LearningReport:
        """Generate a learning report.

        Returns:
            LearningReport
        """
        total = len(self._traces)
        resolved = sum(1 for t in self._traces if t.resolved)
        success_rate = resolved / total if total > 0 else 0.0

        # Most common error category
        category_counts: dict[str, int] = {}
        for t in self._traces:
            category_counts[t.error_category.value] = category_counts.get(t.error_category.value, 0) + 1

        most_common = max(category_counts, key=category_counts.get) if category_counts else "none"

        # Most successful strategy
        strategy_successes: dict[str, int] = {}
        for t in self._traces:
            if t.successful_strategy:
                key = t.successful_strategy.value
                strategy_successes[key] = strategy_successes.get(key, 0) + 1

        most_successful = max(strategy_successes, key=strategy_successes.get) if strategy_successes else "none"

        # Average recovery time
        total_ms = sum(t.total_duration_ms for t in self._traces)
        avg_ms = total_ms / total if total > 0 else 0.0

        return LearningReport(
            total_errors=total,
            total_recoveries=resolved,
            success_rate=success_rate,
            most_common_error=most_common,
            most_successful_strategy=most_successful,
            patterns_learned=sum(1 for _ in self.recognizer._patterns),
            avg_recovery_time_ms=avg_ms,
        )

    def _prune_old_traces(self) -> None:
        """Remove traces older than max_history_days."""
        if not self._traces:
            return

        cutoff = datetime.now() - timedelta(days=self._max_history_days)
        self._traces = [
            t for t in self._traces
            if datetime.fromisoformat(t.timestamp) > cutoff
        ]

    def clear(self) -> None:
        """Clear all learned data."""
        self._traces.clear()
        self.recognizer._patterns.clear()  # type: ignore[attr-defined]
        self.recognizer._sequences.clear()  # type: ignore[attr-defined]
