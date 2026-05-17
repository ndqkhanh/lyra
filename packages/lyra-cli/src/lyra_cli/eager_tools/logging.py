"""Structured logging for eager tools."""
import logging
from typing import Any

logger = logging.getLogger("lyra.eager_tools")


def log_seal_detected(tool_id: str, tool_name: str, elapsed_ms: float) -> None:
    """Log seal detection event."""
    logger.debug(
        "Seal detected",
        extra={
            "event": "seal_detected",
            "tool_id": tool_id,
            "tool_name": tool_name,
            "elapsed_ms": elapsed_ms,
        },
    )


def log_tool_dispatched(tool_id: str, tool_name: str, idempotent: bool) -> None:
    """Log tool dispatch decision."""
    logger.debug(
        "Tool dispatched",
        extra={
            "event": "tool_dispatched",
            "tool_id": tool_id,
            "tool_name": tool_name,
            "dispatch_mode": "eager" if idempotent else "deferred",
        },
    )


def log_tool_cancelled(tool_id: str, reason: str) -> None:
    """Log tool cancellation event."""
    logger.warning(
        "Tool cancelled",
        extra={
            "event": "tool_cancelled",
            "tool_id": tool_id,
            "reason": reason,
        },
    )


def log_exception_boundary(tool_id: str, error: Exception) -> None:
    """Log exception isolation event."""
    logger.error(
        "Tool exception isolated",
        extra={
            "event": "exception_boundary",
            "tool_id": tool_id,
            "error_type": type(error).__name__,
            "error_msg": str(error),
        },
    )
