"""Policy optimizer exception hierarchy."""

from __future__ import annotations


class PolicyOptimizerError(Exception):
    """Base exception for all policy optimizer errors."""


class PolicySearchError(PolicyOptimizerError):
    """Raised when policy search operations fail."""


class RewardModelError(PolicyOptimizerError):
    """Raised when reward modeling or shaping fails."""


class PolicyGradientError(PolicyOptimizerError):
    """Raised when policy gradient computation fails."""


class ConstraintOptimizationError(PolicyOptimizerError):
    """Raised when constrained optimization fails."""


class PolicyEvaluationError(PolicyOptimizerError):
    """Raised when policy evaluation fails."""


class DeploymentError(PolicyOptimizerError):
    """Raised when policy deployment fails."""


class StrategyError(PolicyOptimizerError):
    """Raised when meta-strategy optimization fails."""
