"""Custom exceptions for the SLA package."""

from __future__ import annotations


class SLAError(Exception):
    """Base exception for all SLA errors."""


class SLANotFoundError(SLAError):
    """Raised when an SLA is not found for an agent or service."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"No SLA defined for agent '{agent_id}'")


class SLAViolationError(SLAError):
    """Raised when an SLA violation occurs that requires immediate action."""

    def __init__(self, agent_id: str, metric: str, threshold: float, actual: float) -> None:
        self.agent_id = agent_id
        self.metric = metric
        self.threshold = threshold
        self.actual = actual
        super().__init__(
            f"SLA violation for '{agent_id}': {metric}={actual:.2f} "
            f"(threshold={threshold:.2f})"
        )


class BudgetExceededError(SLAError):
    """Raised when a budget (token/cost/time) is exceeded."""

    def __init__(self, budget_type: str, limit: float, current: float) -> None:
        self.budget_type = budget_type
        self.limit = limit
        self.current = current
        super().__init__(
            f"{budget_type} budget exceeded: {current:.2f}/{limit:.2f}"
        )


class InvalidMetricError(SLAError):
    """Raised when an invalid metric name is used."""

    def __init__(self, metric: str, valid_metrics: list[str]) -> None:
        self.metric = metric
        self.valid_metrics = valid_metrics
        super().__init__(
            f"Invalid metric '{metric}'. Valid: {', '.join(valid_metrics)}"
        )


class AutoScalerError(SLAError):
    """Raised when auto-scaling fails."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Auto-scaling failed: {reason}")
