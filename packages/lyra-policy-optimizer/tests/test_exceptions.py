"""Tests for the exceptions module."""

from __future__ import annotations

from lyra_policy_optimizer.exceptions import (
    ConstraintOptimizationError,
    DeploymentError,
    PolicyEvaluationError,
    PolicyGradientError,
    PolicyOptimizerError,
    PolicySearchError,
    RewardModelError,
    StrategyError,
)


class TestExceptions:
    """Test exception hierarchy and instantiation."""

    def test_base_exception(self) -> None:
        """PolicyOptimizerError should be the base exception."""
        error = PolicyOptimizerError("base error")
        assert str(error) == "base error"
        assert isinstance(error, Exception)

    def test_policy_search_error(self) -> None:
        """PolicySearchError should inherit from PolicyOptimizerError."""
        error = PolicySearchError("search failed")
        assert str(error) == "search failed"
        assert isinstance(error, PolicyOptimizerError)

    def test_reward_model_error(self) -> None:
        """RewardModelError should inherit from PolicyOptimizerError."""
        error = RewardModelError("reward error")
        assert str(error) == "reward error"
        assert isinstance(error, PolicyOptimizerError)

    def test_policy_gradient_error(self) -> None:
        """PolicyGradientError should inherit from PolicyOptimizerError."""
        error = PolicyGradientError("gradient error")
        assert str(error) == "gradient error"
        assert isinstance(error, PolicyOptimizerError)

    def test_constraint_optimization_error(self) -> None:
        """ConstraintOptimizationError should inherit from PolicyOptimizerError."""
        error = ConstraintOptimizationError("constraint error")
        assert str(error) == "constraint error"
        assert isinstance(error, PolicyOptimizerError)

    def test_policy_evaluation_error(self) -> None:
        """PolicyEvaluationError should inherit from PolicyOptimizerError."""
        error = PolicyEvaluationError("evaluation error")
        assert str(error) == "evaluation error"
        assert isinstance(error, PolicyOptimizerError)

    def test_deployment_error(self) -> None:
        """DeploymentError should inherit from PolicyOptimizerError."""
        error = DeploymentError("deploy error")
        assert str(error) == "deploy error"
        assert isinstance(error, PolicyOptimizerError)

    def test_strategy_error(self) -> None:
        """StrategyError should inherit from PolicyOptimizerError."""
        error = StrategyError("strategy error")
        assert str(error) == "strategy error"
        assert isinstance(error, PolicyOptimizerError)

    def test_all_subclasses_of_base(self) -> None:
        """All custom exceptions should be subclasses of PolicyOptimizerError."""
        errors = [
            PolicySearchError(""),
            RewardModelError(""),
            PolicyGradientError(""),
            ConstraintOptimizationError(""),
            PolicyEvaluationError(""),
            DeploymentError(""),
            StrategyError(""),
        ]
        for err in errors:
            assert isinstance(err, PolicyOptimizerError)

    def test_exception_without_message(self) -> None:
        """Exceptions should work without a message."""
        error = PolicyOptimizerError()
        assert isinstance(error, PolicyOptimizerError)

    def test_exception_chaining(self) -> None:
        """Exceptions should support chaining."""
        try:
            try:
                raise ValueError("inner")
            except ValueError as inner:
                raise PolicySearchError("outer") from inner
        except PolicySearchError as e:
            assert isinstance(e.__cause__, ValueError)

    def test_exception_identity(self) -> None:
        """Different exception types should be distinct."""
        search_err = PolicySearchError("err")
        deploy_err = DeploymentError("err")
        assert type(search_err) is not type(deploy_err)

    def test_empty_exception_str(self) -> None:
        """Exception with no args should produce an empty string."""
        error = PolicyOptimizerError()
        assert str(error) == ""
