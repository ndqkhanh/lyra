"""Structured Logger — leveled logging with context and JSON export.

Provides a StructuredLogger class that emits LogEntry objects with
level filtering and JSON serialization support.
"""

from __future__ import annotations

import enum
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


class LogLevel(enum.Enum):
    """Log severity levels with numeric ordering for filtering."""

    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40


@dataclass(frozen=True)
class LogEntry:
    """A single structured log entry.

    Attributes:
        level: Severity level.
        message: Human-readable log message.
        context: Structured key-value context attached to the entry.
        timestamp: Unix timestamp when the entry was created.
    """

    level: LogLevel
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class StructuredLogger:
    """A leveled, structured logger with JSON export.

    Default log level is INFO. Entries below the current level are
    silently dropped.
    """

    def __init__(self, level: LogLevel = LogLevel.INFO) -> None:
        self._level = level
        self._entries: list[LogEntry] = []

    @property
    def level(self) -> LogLevel:
        return self._level

    def set_level(self, level: LogLevel) -> None:
        """Set the minimum log level. Entries below this level are dropped.

        Args:
            level: The new minimum log level.
        """
        self._level = level

    def _log(self, level: LogLevel, msg: str, **context: Any) -> None:
        """Internal log method. Only records if level meets the threshold."""
        if level.value >= self._level.value:
            self._entries.append(LogEntry(level=level, message=msg, context=context))

    def debug(self, msg: str, **context: Any) -> None:
        """Log a DEBUG-level message."""
        self._log(LogLevel.DEBUG, msg, **context)

    def info(self, msg: str, **context: Any) -> None:
        """Log an INFO-level message."""
        self._log(LogLevel.INFO, msg, **context)

    def warn(self, msg: str, **context: Any) -> None:
        """Log a WARN-level message."""
        self._log(LogLevel.WARN, msg, **context)

    def error(self, msg: str, **context: Any) -> None:
        """Log an ERROR-level message."""
        self._log(LogLevel.ERROR, msg, **context)

    def get_recent(self, limit: int = 100) -> list[LogEntry]:
        """Return the most recent log entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of LogEntry objects, newest first.
        """
        return list(reversed(self._entries))[:limit]

    def to_json(self) -> str:
        """Export all log entries as a JSON string.

        Returns:
            Pretty-printed JSON array of log entry dicts.
        """
        serialized: list[dict[str, Any]] = []
        for entry in self._entries:
            serialized.append(
                {
                    "level": entry.level.name,
                    "message": entry.message,
                    "context": (
                        dict(entry.context.items())
                        if isinstance(entry.context, Mapping)
                        else entry.context
                    ),
                    "timestamp": entry.timestamp,
                }
            )
        return json.dumps(serialized, indent=2)
