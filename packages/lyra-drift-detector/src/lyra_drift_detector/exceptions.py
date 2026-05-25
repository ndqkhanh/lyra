"""Custom exceptions for the drift detector package."""

from __future__ import annotations


class DriftDetectorError(Exception):
    """Base exception for all drift detector errors."""


class MonitorNotInitializedError(DriftDetectorError):
    """Raised when a monitor is used before being initialized with baseline data."""

    def __init__(self, monitor_name: str) -> None:
        self.monitor_name = monitor_name
        super().__init__(
            f"Monitor '{monitor_name}' has not been initialized. "
            f"Call initialize() or set_baseline() first."
        )


class AlertThrottledError(DriftDetectorError):
    """Raised when an alert is suppressed due to throttling."""

    def __init__(self, alert_id: str, cooldown_remaining: float) -> None:
        self.alert_id = alert_id
        self.cooldown_remaining = cooldown_remaining
        super().__init__(
            f"Alert '{alert_id}' throttled. Cooldown remaining: {cooldown_remaining:.1f}s"
        )


class InsufficientDataError(DriftDetectorError):
    """Raised when there is not enough data to perform a drift check."""

    def __init__(self, metric: str, required: int, actual: int) -> None:
        self.metric = metric
        self.required = required
        self.actual = actual
        super().__init__(
            f"Insufficient data for '{metric}': "
            f"need at least {required} samples, got {actual}"
        )


class AdaptationError(DriftDetectorError):
    """Raised when an automatic adaptation fails."""

    def __init__(self, strategy: str, reason: str) -> None:
        self.strategy = strategy
        self.reason = reason
        super().__init__(f"Adaptation strategy '{strategy}' failed: {reason}")


class RollbackError(DriftDetectorError):
    """Raised when a rollback operation fails."""

    def __init__(self, checkpoint_id: str, reason: str) -> None:
        self.checkpoint_id = checkpoint_id
        self.reason = reason
        super().__init__(f"Rollback to checkpoint '{checkpoint_id}' failed: {reason}")


class InvalidConfigurationError(DriftDetectorError):
    """Raised when a detector or monitor is configured with invalid parameters."""

    def __init__(self, component: str, message: str) -> None:
        self.component = component
        super().__init__(f"Invalid configuration for '{component}': {message}")
