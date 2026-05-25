"""Tests for exception classes."""

from __future__ import annotations

from lyra_eval_pipeline.exceptions import (
    BenchGuardError,
    CrossModelError,
    DomainEvalError,
    EvalPipelineError,
    LeaderboardError,
    ReportError,
    RubricError,
    SchedulerError,
)


class TestExceptions:
    def test_eval_pipeline_error_base(self) -> None:
        assert issubclass(DomainEvalError, EvalPipelineError)
        assert issubclass(RubricError, EvalPipelineError)
        assert issubclass(CrossModelError, EvalPipelineError)
        assert issubclass(BenchGuardError, EvalPipelineError)
        assert issubclass(LeaderboardError, EvalPipelineError)
        assert issubclass(SchedulerError, EvalPipelineError)
        assert issubclass(ReportError, EvalPipelineError)

    def test_eval_pipeline_error_message(self) -> None:
        err = EvalPipelineError("test message")
        assert str(err) == "test message"

    def test_domain_eval_error_message(self) -> None:
        err = DomainEvalError("domain not found")
        assert str(err) == "domain not found"

    def test_rubric_error_message(self) -> None:
        err = RubricError("invalid weights")
        assert str(err) == "invalid weights"

    def test_cross_model_error_message(self) -> None:
        err = CrossModelError("no consensus")
        assert str(err) == "no consensus"

    def test_bench_guard_error_message(self) -> None:
        err = BenchGuardError("over budget")
        assert str(err) == "over budget"

    def test_leaderboard_error_message(self) -> None:
        err = LeaderboardError("entry not found")
        assert str(err) == "entry not found"

    def test_scheduler_error_message(self) -> None:
        err = SchedulerError("job failed")
        assert str(err) == "job failed"

    def test_report_error_message(self) -> None:
        err = ReportError("export failed")
        assert str(err) == "export failed"

    def test_exception_raise_and_catch(self) -> None:
        try:
            raise DomainEvalError("custom domain error")
        except EvalPipelineError as e:
            assert str(e) == "custom domain error"

    def test_rubric_error_raise(self) -> None:
        try:
            raise RubricError("weight mismatch")
        except RubricError as e:
            assert str(e) == "weight mismatch"

    def test_bench_guard_error_raise(self) -> None:
        try:
            raise BenchGuardError("budget exceeded")
        except BenchGuardError as e:
            assert str(e) == "budget exceeded"

    def test_leaderboard_error_caught_as_base(self) -> None:
        try:
            raise LeaderboardError("not ranked")
        except EvalPipelineError as e:
            assert str(e) == "not ranked"

    def test_scheduler_error_caught_as_base(self) -> None:
        try:
            raise SchedulerError("timeout")
        except EvalPipelineError as e:
            assert str(e) == "timeout"

    def test_report_error_caught_as_base(self) -> None:
        try:
            raise ReportError("write error")
        except EvalPipelineError as e:
            assert str(e) == "write error"

    def test_cross_model_error_caught_as_base(self) -> None:
        try:
            raise CrossModelError("bias detected")
        except EvalPipelineError as e:
            assert str(e) == "bias detected"

    def test_all_exceptions_distinct(self) -> None:
        errors = [
            DomainEvalError(""),
            RubricError(""),
            CrossModelError(""),
            BenchGuardError(""),
            LeaderboardError(""),
            SchedulerError(""),
            ReportError(""),
        ]
        # All should be EvalPipelineError but have different types
        for err in errors:
            assert isinstance(err, EvalPipelineError)
        types = {type(e) for e in errors}
        assert len(types) == 7

    def test_exception_no_message(self) -> None:
        err = SchedulerError()
        assert str(err) == ""

    def test_exception_with_args(self) -> None:
        err = RubricError("dimension", "weight", "mismatch")
        assert str(err) == "('dimension', 'weight', 'mismatch')"

    def test_base_exception_chain(self) -> None:
        try:
            try:
                raise DomainEvalError("inner cause")
            except DomainEvalError as inner:
                raise EvalPipelineError("outer wrap") from inner
        except EvalPipelineError as outer:
            assert isinstance(outer.__cause__, DomainEvalError)

    def test_bench_guard_error_not_rubric(self) -> None:
        """Verify exception types are not confused."""
        assert not issubclass(BenchGuardError, RubricError)
        assert not issubclass(ReportError, CrossModelError)
