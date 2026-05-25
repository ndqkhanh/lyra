"""Custom exceptions for the model router package."""

from __future__ import annotations


class RouterError(Exception):
    """Base exception for all model router errors."""


class ModelNotFoundError(RouterError):
    """Raised when a requested model is not found in the registry."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        super().__init__(f"Model '{model_id}' not found in registry")


class BudgetExceededError(RouterError):
    """Raised when a routing budget (cost/token) has been exceeded."""

    def __init__(self, budget_type: str, limit: float, current: float, period: str = "unknown") -> None:
        self.budget_type = budget_type
        self.limit = limit
        self.current = current
        self.period = period
        super().__init__(
            f"{budget_type} budget exceeded for period '{period}': "
            f"{current:.2f}/{limit:.2f}"
        )


class VerificationError(RouterError):
    """Raised when cross-model verification fails."""

    def __init__(self, generator: str, reviewer: str, reason: str) -> None:
        self.generator = generator
        self.reviewer = reviewer
        self.reason = reason
        super().__init__(
            f"Cross-model verification failed: {reason} "
            f"(generator={generator}, reviewer={reviewer})"
        )


class CapabilityMismatchError(RouterError):
    """Raised when a task's requirements cannot be matched to any model."""

    def __init__(self, task_type: str, reason: str) -> None:
        self.task_type = task_type
        self.reason = reason
        super().__init__(
            f"Capability mismatch for task type '{task_type}': {reason}"
        )


class RoutingError(RouterError):
    """Raised when routing fails to produce a valid selection."""

    def __init__(self, task_id: str, reason: str) -> None:
        self.task_id = task_id
        self.reason = reason
        super().__init__(
            f"Routing failed for task '{task_id}': {reason}"
        )
