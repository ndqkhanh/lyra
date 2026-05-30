"""Tests for error recovery and learning system."""

import pytest

from lyra_cli.autonomy.error_learner import ErrorRecoveryLearner, RecoveryTrace
from lyra_cli.autonomy.recovery.pattern_recognizer import (
    ErrorCategory,
    ErrorPattern,
    PatternRecognizer,
)
from lyra_cli.autonomy.recovery.retry_policy import (
    RetryConfig,
    RetryDecision,
    RetryPolicy,
)
from lyra_cli.autonomy.recovery.strategy_selector import (
    RecoveryAction,
    RecoveryStrategy,
    StrategySelector,
)


# ── PatternRecognizer Tests ────────────────────────────────────────


class TestPatternRecognizer:
    """Test suite for PatternRecognizer."""

    def test_classify_timeout(self):
        recognizer = PatternRecognizer()
        category = recognizer.classify(TimeoutError("connection timed out"))
        assert category == ErrorCategory.TIMEOUT

    def test_classify_permission(self):
        recognizer = PatternRecognizer()
        category = recognizer.classify(PermissionError("access denied"))
        assert category == ErrorCategory.PERMISSION

    def test_classify_validation(self):
        recognizer = PatternRecognizer()
        category = recognizer.classify(ValueError("invalid value"))
        assert category == ErrorCategory.VALIDATION

    def test_classify_dependency(self):
        recognizer = PatternRecognizer()
        category = recognizer.classify(ImportError("No module named 'foo'"))
        assert category == ErrorCategory.DEPENDENCY

    def test_classify_resource(self):
        recognizer = PatternRecognizer()
        category = recognizer.classify(MemoryError("out of memory"))
        assert category == ErrorCategory.RESOURCE

    def test_classify_logic(self):
        recognizer = PatternRecognizer()
        category = recognizer.classify(KeyError("missing key"))
        assert category == ErrorCategory.LOGIC

    def test_classify_unknown(self):
        recognizer = PatternRecognizer()
        category = recognizer.classify(Exception("something unusual"))
        assert category == ErrorCategory.UNKNOWN

    def test_fingerprint_consistency(self):
        recognizer = PatternRecognizer()
        fp1 = recognizer.fingerprint(ValueError("bad input"))
        fp2 = recognizer.fingerprint(ValueError("bad input"))
        assert fp1 == fp2

    def test_fingerprint_different_errors(self):
        recognizer = PatternRecognizer()
        fp1 = recognizer.fingerprint(ValueError("bad input"))
        fp2 = recognizer.fingerprint(TypeError("wrong type"))
        assert fp1 != fp2

    def test_learn_pattern(self):
        recognizer = PatternRecognizer()
        pattern = recognizer.learn_pattern(ValueError("invalid"))
        assert pattern.category == ErrorCategory.VALIDATION
        assert pattern.occurrence_count == 1

        # Learning same error again increments count
        pattern2 = recognizer.learn_pattern(ValueError("invalid"))
        assert pattern2.occurrence_count == 2

    def test_learn_sequence(self):
        recognizer = PatternRecognizer()
        errors = [ValueError("bad input"), ImportError("no module")]
        sequence = recognizer.learn_sequence(errors, "retry")
        assert len(sequence.categories) == 2

    def test_find_similar(self):
        recognizer = PatternRecognizer()
        recognizer.learn_pattern(TimeoutError("connection timed out"))
        recognizer.learn_pattern(TimeoutError("connection timed out"))
        recognizer.learn_pattern(TimeoutError("request timeout"))
        similar = recognizer.find_similar(TimeoutError("operation timed out"))
        assert len(similar) >= 2
        assert all(p.category == ErrorCategory.TIMEOUT for p in similar)


# ── StrategySelector Tests ─────────────────────────────────────────


class TestStrategySelector:
    """Test suite for StrategySelector."""

    def test_select_transient(self):
        selector = StrategySelector()
        strategy = selector.select(Exception("temp"), ErrorCategory.TRANSIENT)
        assert strategy.action == RecoveryAction.RETRY_WITH_BACKOFF

    def test_select_permanent(self):
        selector = StrategySelector()
        strategy = selector.select(Exception("fatal"), ErrorCategory.PERMANENT)
        assert strategy.action == RecoveryAction.ESCALATE

    def test_select_max_retries_exceeded(self):
        selector = StrategySelector()
        strategy = selector.select(
            Exception("retry"), ErrorCategory.TRANSIENT, attempt=5
        )
        assert strategy.action == RecoveryAction.ESCALATE

    def test_record_and_get_success_rate(self):
        selector = StrategySelector()
        selector.record_success(ErrorCategory.TRANSIENT, RecoveryAction.RETRY_WITH_BACKOFF)
        selector.record_success(ErrorCategory.TRANSIENT, RecoveryAction.RETRY_WITH_BACKOFF)
        selector.record_failure(ErrorCategory.TRANSIENT, RecoveryAction.RETRY_WITH_BACKOFF)

        rate = selector.get_success_rate(ErrorCategory.TRANSIENT, RecoveryAction.RETRY_WITH_BACKOFF)
        assert rate == 2.0 / 3.0

    def test_get_fallback_chain(self):
        selector = StrategySelector()
        chain = selector.get_fallback_chain(RecoveryAction.RETRY)
        assert RecoveryAction.RETRY_WITH_BACKOFF in chain
        assert RecoveryAction.FALLBACK in chain


# ── RetryPolicy Tests ──────────────────────────────────────────────


class TestRetryPolicy:
    """Test suite for RetryPolicy."""

    def test_should_retry_transient(self):
        policy = RetryPolicy()
        result = policy.should_retry("err1", "transient", 0)
        assert result.decision == RetryDecision.RETRY
        assert result.delay_ms > 0

    def test_should_not_retry_permanent(self):
        policy = RetryPolicy()
        result = policy.should_retry("err2", "permanent", 0)
        assert result.decision == RetryDecision.ABORT

    def test_max_retries_exceeded(self):
        policy = RetryPolicy(RetryConfig(max_retries=3))
        result = policy.should_retry("err3", "transient", 3)
        assert result.decision == RetryDecision.ESCALATE

    def test_exponential_backoff_increases(self):
        policy = RetryPolicy(RetryConfig(base_delay_ms=100, backoff_factor=2.0))
        result1 = policy.should_retry("err4", "transient", 0)
        result2 = policy.should_retry("err4", "transient", 1)
        # Second delay should be roughly 2x the first
        assert result2.delay_ms >= result1.delay_ms * 1.5  # Allow for jitter

    def test_reset_state(self):
        policy = RetryPolicy()
        policy.should_retry("err5", "transient", 0)
        policy.should_retry("err5", "transient", 1)
        policy.reset("err5")

        # After reset, should allow retry again
        result = policy.should_retry("err5", "transient", 0)
        assert result.decision == RetryDecision.RETRY

    def test_total_retries(self):
        policy = RetryPolicy()
        policy.should_retry("a", "transient", 0)
        policy.should_retry("b", "timeout", 0)
        assert policy.get_total_retries() == 2


# ── ErrorRecoveryLearner Tests ─────────────────────────────────────


class TestErrorRecoveryLearner:
    """Test suite for ErrorRecoveryLearner."""

    def test_classify_error(self):
        learner = ErrorRecoveryLearner()
        category = learner.classify_error(ValueError("invalid input"))
        assert category == ErrorCategory.VALIDATION

    def test_suggest_recovery(self):
        learner = ErrorRecoveryLearner()
        strategy = learner.suggest_recovery(TimeoutError("timed out"))
        assert strategy.action in (RecoveryAction.RETRY_WITH_BACKOFF, RecoveryAction.RETRY)

    def test_attempt_recovery(self):
        learner = ErrorRecoveryLearner()
        strategy, retry_result = learner.attempt_recovery(
            "trace1", TimeoutError("timed out"), 0
        )
        assert retry_result.decision == RetryDecision.RETRY
        assert strategy.action is not None

    def test_record_recovery_success(self):
        learner = ErrorRecoveryLearner()
        trace = learner.record_recovery(
            trace_id="trace2",
            error=ValueError("invalid"),
            strategies_tried=[RecoveryAction.FALLBACK],
            successful_strategy=RecoveryAction.FALLBACK,
            attempts=1,
            duration_ms=150.0,
            resolved=True,
        )
        assert trace.resolved is True
        assert trace.successful_strategy == RecoveryAction.FALLBACK

    def test_record_recovery_failure(self):
        learner = ErrorRecoveryLearner()
        trace = learner.record_recovery(
            trace_id="trace3",
            error=ImportError("no module x"),
            strategies_tried=[RecoveryAction.FALLBACK, RecoveryAction.REPLAN, RecoveryAction.ESCALATE],
            successful_strategy=None,
            attempts=3,
            duration_ms=500.0,
            resolved=False,
        )
        assert trace.resolved is False
        assert trace.attempts == 3

    def test_learn_pattern(self):
        learner = ErrorRecoveryLearner()
        errors = [ValueError("bad"), TypeError("wrong")]
        learner.learn_pattern(errors, "retry")
        # Should not raise

    def test_get_recovery_history(self):
        learner = ErrorRecoveryLearner()
        learner.record_recovery(
            "t1", ValueError("bad"), [RecoveryAction.FALLBACK],
            RecoveryAction.FALLBACK, 1, 100.0, True,
        )
        learner.record_recovery(
            "t2", TimeoutError("timeout"), [RecoveryAction.RETRY_WITH_BACKOFF],
            RecoveryAction.RETRY_WITH_BACKOFF, 1, 200.0, True,
        )

        history = learner.get_recovery_history()
        assert len(history) == 2

        filtered = learner.get_recovery_history(category=ErrorCategory.TIMEOUT)
        assert len(filtered) == 1

    def test_learning_report(self):
        learner = ErrorRecoveryLearner()
        learner.record_recovery(
            "t1", ValueError("invalid"), [RecoveryAction.FALLBACK],
            RecoveryAction.FALLBACK, 1, 100.0, True,
        )
        learner.record_recovery(
            "t2", ImportError("missing"), [RecoveryAction.ESCALATE],
            None, 1, 50.0, False,
        )

        report = learner.get_learning_report()
        assert report.total_errors == 2
        assert report.total_recoveries == 1
        assert report.success_rate == 0.5

    def test_clear_state(self):
        learner = ErrorRecoveryLearner()
        learner.record_recovery(
            "t1", ValueError("bad"), [RecoveryAction.FALLBACK],
            RecoveryAction.FALLBACK, 1, 100.0, True,
        )
        learner.clear()
        report = learner.get_learning_report()
        assert report.total_errors == 0
