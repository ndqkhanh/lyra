"""Data models for sandbox execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration for sandbox execution."""

    timeout: float = 5.0  # seconds
    max_memory_mb: int = 100
    allow_network: bool = False
    allow_file_write: bool = False
    allowed_modules: list[str] = field(
        default_factory=lambda: [
            "math",
            "random",
            "datetime",
            "time",
            "json",
            "re",
            "collections",
            "itertools",
            "functools",
        ]
    )
    blocked_modules: list[str] = field(
        default_factory=lambda: ["os", "sys", "subprocess", "socket", "urllib"]
    )


@dataclass(frozen=True)
class ExecutionResult:
    """Result of code execution in sandbox."""

    success: bool
    return_value: dict[str, Any] | None = None
    error: str | None = None
    execution_time: float = 0.0
    stdout: str = ""
    stderr: str = ""


@dataclass
class Snapshot:
    """Filesystem snapshot for rollback."""

    path: Path
    files: dict[str, str] = field(default_factory=dict)  # filename -> content
    timestamp: float = 0.0
