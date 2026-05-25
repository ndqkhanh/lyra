"""Sandbox exception types and shared response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time


class Language(str, Enum):
    """Supported execution languages."""

    PYTHON = "python"
    BASH = "bash"
    JAVASCRIPT = "javascript"
    RUBY = "ruby"
    SQL = "sql"
    GENERIC = "generic"


@dataclass(frozen=True)
class ResourceUsage:
    """Resource consumption snapshot."""

    cpu_time: float = 0.0
    max_memory_kb: int = 0
    io_read: int = 0
    io_write: int = 0


@dataclass(frozen=True)
class ExecutionResult:
    """Result of a single code execution."""

    output: str
    stderr: str
    return_code: int
    duration_ms: float
    timed_out: bool = False
    was_killed: bool = False
    sandbox_type_used: str = "unknown"
    resource_usage: ResourceUsage | None = None


@dataclass(frozen=True)
class CodeRequest:
    """Request to execute code in a sandbox."""

    code: str
    language: Language = Language.GENERIC
    stdin: str = ""
    args: list[str] = field(default_factory=list)
    expected_return_code: int = 0


class SandboxError(Exception):
    """Base sandbox error."""


class ContainerError(SandboxError):
    """Docker container operation error."""


class ExecutionError(SandboxError):
    """Code execution failure."""


class ResourceLimitError(SandboxError):
    """Resource constraint violation."""


class NetworkError(SandboxError):
    """Network policy violation."""


class FilesystemError(SandboxError):
    """Filesystem isolation error."""


class ImageError(SandboxError):
    """Sandbox image management error."""


class SecurityScanError(SandboxError):
    """Security scan failure."""


class TimeoutError(SandboxError):
    """Execution timeout exceeded."""
