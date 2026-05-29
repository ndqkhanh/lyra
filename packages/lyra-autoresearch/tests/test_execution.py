"""
Tests for Self-Healing Execution System
"""

from lyra_autoresearch.execution import (
    ExecutionCheckpoint,
    ExecutionStrategy,
    FailureAnalyzer,
    FailureType,
    PivotRefineDecider,
    SelfHealingExecutor,
    execute_with_healing,
)


class TestFailureAnalyzer:
    """Test failure classification"""

    def test_syntax_error(self):
        """Classify syntax errors"""
        error = SyntaxError("invalid syntax")
        failure_type = FailureAnalyzer.classify_failure(error, {})
        assert failure_type == FailureType.SYNTAX_ERROR

    def test_import_error(self):
        """Classify import errors"""
        error = ModuleNotFoundError("No module named 'foo'")
        failure_type = FailureAnalyzer.classify_failure(error, {})
        assert failure_type == FailureType.DEPENDENCY_ERROR

    def test_timeout(self):
        """Classify timeout errors"""
        error = TimeoutError("Operation timed out")
        failure_type = FailureAnalyzer.classify_failure(error, {})
        assert failure_type == FailureType.TIMEOUT

    def test_null_result(self):
        """Classify null results"""
        error = ValueError("Empty result")
        context = {"output": None}
        failure_type = FailureAnalyzer.classify_failure(error, context)
        assert failure_type == FailureType.NULL_RESULT

    def test_assertion_error(self):
        """Classify assertion violations"""
        error = AssertionError("Invariant violated")
        failure_type = FailureAnalyzer.classify_failure(error, {})
        assert failure_type == FailureType.ASSUMPTION_VIOLATION


class TestPivotRefineDecider:
    """Test Pivot/Refine decision logic"""

    def test_syntax_error_refine(self):
        """Syntax errors should trigger REFINE"""
        decider = PivotRefineDecider()
        checkpoint = ExecutionCheckpoint(
            iteration=1,
            strategy_history=[],
            failure_history=[],
            code_versions=[],
            results=[],
        )

        strategy = decider.decide(FailureType.SYNTAX_ERROR, checkpoint)
        assert strategy == ExecutionStrategy.REFINE

    def test_null_result_pivot(self):
        """Null results should trigger PIVOT"""
        decider = PivotRefineDecider()
        checkpoint = ExecutionCheckpoint(
            iteration=1,
            strategy_history=[],
            failure_history=[],
            code_versions=[],
            results=[],
        )

        strategy = decider.decide(FailureType.NULL_RESULT, checkpoint)
        assert strategy == ExecutionStrategy.PIVOT

    def test_max_refines_reached(self):
        """Should ABORT after max refines"""
        decider = PivotRefineDecider(max_refines=3, max_pivots=2)
        checkpoint = ExecutionCheckpoint(
            iteration=6,
            strategy_history=[
                ExecutionStrategy.REFINE,
                ExecutionStrategy.REFINE,
                ExecutionStrategy.REFINE,
                ExecutionStrategy.PIVOT,
                ExecutionStrategy.PIVOT,
            ],
            failure_history=[],
            code_versions=[],
            results=[],
        )

        strategy = decider.decide(FailureType.SYNTAX_ERROR, checkpoint)
        assert strategy == ExecutionStrategy.ABORT

    def test_switch_to_pivot_after_max_refines(self):
        """Should switch to PIVOT after max refines"""
        decider = PivotRefineDecider(max_refines=3, max_pivots=2)
        checkpoint = ExecutionCheckpoint(
            iteration=4,
            strategy_history=[
                ExecutionStrategy.REFINE,
                ExecutionStrategy.REFINE,
                ExecutionStrategy.REFINE,
            ],
            failure_history=[],
            code_versions=[],
            results=[],
        )

        strategy = decider.decide(FailureType.SYNTAX_ERROR, checkpoint)
        assert strategy == ExecutionStrategy.PIVOT


class TestSelfHealingExecutor:
    """Test self-healing executor"""

    def test_success_first_try(self):
        """Task succeeds on first try"""
        def task():
            return "success"

        def refine(error, context):
            return context

        def pivot(error, context):
            return context

        executor = SelfHealingExecutor()
        result = executor.execute(task, refine, pivot)

        assert result.success is True
        assert result.output == "success"
        assert result.iterations == 1

    def test_success_after_refine(self):
        """Task succeeds after one refine"""
        attempts = [0]

        def task():
            attempts[0] += 1
            if attempts[0] == 1:
                raise ValueError("First attempt fails")
            return "success"

        def refine(error, context):
            return context

        def pivot(error, context):
            return context

        executor = SelfHealingExecutor(max_refines=3)
        result = executor.execute(task, refine, pivot)

        assert result.success is True
        assert result.output == "success"
        assert result.iterations == 2
        assert ExecutionStrategy.REFINE in result.checkpoint.strategy_history

    def test_abort_after_max_iterations(self):
        """Should abort after max iterations"""
        def task():
            raise ValueError("Always fails")

        def refine(error, context):
            return context

        def pivot(error, context):
            return context

        executor = SelfHealingExecutor(max_refines=2, max_pivots=1)
        result = executor.execute(task, refine, pivot)

        assert result.success is False
        assert result.strategy_used == ExecutionStrategy.ABORT


def test_execute_with_healing_convenience():
    """Test convenience function"""
    attempts = [0]

    def task():
        attempts[0] += 1
        if attempts[0] < 3:
            raise ValueError("Not yet")
        return "done"

    result = execute_with_healing(task, max_refines=5)

    assert result.success is True
    assert result.output == "done"
    assert result.iterations == 3
