"""Structured logging configuration for Lyra.

Provides JSON and console logging with TUI-compatible output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "console",
    log_file: Path | None = None,
) -> None:
    """Configure structured logging for Lyra.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Output format (console or json)
        log_file: Optional log file path for persistent logs
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr if log_file is None else open(log_file, "a"),
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class TUICompatibleHandler(logging.Handler):
    """Logging handler that doesn't disrupt TUI display.

    Writes logs to a separate file instead of stdout/stderr.
    """

    def __init__(self, log_file: Path):
        """Initialize handler.

        Args:
            log_file: Path to log file
        """
        super().__init__()
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to file.

        Args:
            record: Log record to emit
        """
        try:
            msg = self.format(record)
            with open(self.log_file, "a") as f:
                f.write(msg + "\n")
        except Exception:
            self.handleError(record)


def configure_tui_logging(log_file: Path, log_level: str = "INFO") -> None:
    """Configure logging that doesn't disrupt TUI.

    Args:
        log_file: Path to log file
        log_level: Logging level
    """
    handler = TUICompatibleHandler(log_file)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Configure structlog to use the same handler
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(file=open(log_file, "a")),
        cache_logger_on_first_use=True,
    )


__all__ = [
    "configure_logging",
    "get_logger",
    "configure_tui_logging",
    "TUICompatibleHandler",
]
