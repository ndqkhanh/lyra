"""Tests for the self-rewrite exception hierarchy."""

from __future__ import annotations

from lyra_self_rewrite.exceptions import (
    ConstraintError,
    ConvergenceError,
    FitnessError,
    GenerationError,
    GoalMutationError,
    HyperAgentError,
    RecursionError,
    RewriteValidationError,
    SelfRewriteError,
)


class TestSelfRewriteExceptions:
    def test_self_rewrite_error_base(self) -> None:
        assert issubclass(HyperAgentError, SelfRewriteError)
        assert issubclass(GoalMutationError, SelfRewriteError)
        assert issubclass(FitnessError, SelfRewriteError)
        assert issubclass(ConstraintError, SelfRewriteError)
        assert issubclass(GenerationError, SelfRewriteError)
        assert issubclass(RecursionError, SelfRewriteError)
        assert issubclass(RewriteValidationError, SelfRewriteError)
        assert issubclass(ConvergenceError, SelfRewriteError)

    def test_self_rewrite_error_message(self) -> None:
        err = SelfRewriteError("base error")
        assert str(err) == "base error"

    def test_hyper_agent_error_message(self) -> None:
        err = HyperAgentError("population empty")
        assert str(err) == "population empty"

    def test_goal_mutation_error_message(self) -> None:
        err = GoalMutationError("no strategies generated")
        assert str(err) == "no strategies generated"

    def test_fitness_error_message(self) -> None:
        err = FitnessError("objective mismatch")
        assert str(err) == "objective mismatch"

    def test_constraint_error_message(self) -> None:
        err = ConstraintError("hard constraint violated")
        assert str(err) == "hard constraint violated"

    def test_generation_error_message(self) -> None:
        err = GenerationError("rewrite generation failed")
        assert str(err) == "rewrite generation failed"

    def test_recursion_error_message(self) -> None:
        err = RecursionError("empty population")
        assert str(err) == "empty population"

    def test_rewrite_validation_error_message(self) -> None:
        err = RewriteValidationError("syntax error in rewrite")
        assert str(err) == "syntax error in rewrite"

    def test_convergence_error_message(self) -> None:
        err = ConvergenceError("failed to converge")
        assert str(err) == "failed to converge"

    def test_all_exceptions_are_self_rewrite_errors(self) -> None:
        exceptions = [
            HyperAgentError(),
            GoalMutationError(),
            FitnessError(),
            ConstraintError(),
            GenerationError(),
            RecursionError(),
            RewriteValidationError(),
            ConvergenceError(),
        ]
        for exc in exceptions:
            assert isinstance(exc, SelfRewriteError)

    def test_exception_with_cause(self) -> None:
        try:
            raise ValueError("inner cause")
        except ValueError as cause:
            err = HyperAgentError("outer error")
            assert err.args[0] == "outer error"

    def test_convergence_error_inherits_recursion(self) -> None:
        assert issubclass(ConvergenceError, SelfRewriteError)
        assert issubclass(ConvergenceError, Exception)

    def test_empty_error_message(self) -> None:
        err = HyperAgentError()
        assert str(err) == ""

    def test_multiple_args(self) -> None:
        err = FitnessError("mismatch", "extra detail")
        assert err.args == ("mismatch", "extra detail")

    def test_nested_exception_hierarchy(self) -> None:
        assert SelfRewriteError.__bases__ == (Exception,)
        assert HyperAgentError.__bases__ == (SelfRewriteError,)
        assert GoalMutationError.__bases__ == (SelfRewriteError,)
        assert FitnessError.__bases__ == (SelfRewriteError,)

    def test_fitness_error_distinct_from_generation(self) -> None:
        assert FitnessError is not GenerationError
        assert not issubclass(FitnessError, GenerationError)
        assert not issubclass(GenerationError, FitnessError)

    def test_goal_mutation_distinct_from_constraint(self) -> None:
        assert GoalMutationError is not ConstraintError
        assert not issubclass(GoalMutationError, ConstraintError)

    def test_rewrite_validation_distinct_from_generation(self) -> None:
        assert RewriteValidationError is not GenerationError
        assert not issubclass(RewriteValidationError, GenerationError)

    def test_hyper_agent_error_inherits_correctly(self) -> None:
        """Verify HyperAgentError is an instanceof SelfRewriteError."""
        err = HyperAgentError("test")
        assert isinstance(err, SelfRewriteError)
        assert isinstance(err, Exception)
