"""Terminal backend protocol."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ["CommandResult", "TerminalBackend", "TerminalError"]


class TerminalError(Exception):
    """Backend failed to start or execute a command."""


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    truncated: bool = False


@runtime_checkable
class TerminalBackend(Protocol):
    """Every transport (local, docker, modal, ssh, daytona, singularity)
    implements this tiny surface.

    The backend is responsible for:

    - honouring ``timeout_ms`` (truncated → ``exit_code`` sentinel and
      ``truncated=True``);
    - returning *decoded* stdout/stderr;
    - never raising on non-zero exit — callers decide how to react.
    """

    name: str

    def run(
        self,
        cmd: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_ms: int = 30_000,
    ) -> CommandResult: ...
