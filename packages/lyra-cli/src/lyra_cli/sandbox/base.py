"""Sandbox protocol + shared dataclasses.

A :class:`Sandbox` exposes four operations:

* :meth:`Sandbox.write_file` — stage a file inside the sandbox,
  creating parent dirs as needed.
* :meth:`Sandbox.read_file` — read a file from the sandbox.
* :meth:`Sandbox.run` — execute a shell command and return a
  :class:`CommandResult`.
* :meth:`Sandbox.close` — tear down the workspace.

Sandboxes are also context managers so ``with Sandbox(...) as s:``
guarantees cleanup. :class:`SandboxNotAvailable` is the loud
failure mode (Docker missing, container failed to start);
:class:`SandboxError` covers everything else (command failed
post-launch, file out of bounds).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable


class SandboxError(Exception):
    """Generic sandbox failure (file IO, oversized stdout, etc.)."""


class SandboxNotAvailable(SandboxError):
    """Raised when the requested sandbox can't be constructed.

    Examples: Docker isn't on PATH, the image pull failed, the
    network is down. Callers can catch this and fall back to a
    different provider — that's the whole point of the picker.
    """


@dataclass(frozen=True)
class CommandResult:
    """Outcome of a single :meth:`Sandbox.run` invocation.

    Attributes:
        argv: The argv list that ran (debug aid; sandboxes that
            shell out to ``bash -c`` still record the high-level
            argv they were given).
        exit_code: Process exit status. ``0`` is success.
        stdout: Captured stdout (string).
        stderr: Captured stderr (string).
        duration_ms: Wall-clock duration in milliseconds.
        timed_out: ``True`` when the run hit ``timeout`` and was
            killed; ``exit_code`` will be a non-zero sentinel
            (``124`` on Unix-style sandboxes).
    """

    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable shape (for the HTTP layer in N.6)."""
        return {
            "argv": list(self.argv),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "ok": self.ok,
        }


@runtime_checkable
class Sandbox(Protocol):
    """The operations every sandbox provider must support.

    Methods raise :class:`SandboxError` (or :class:`SandboxNotAvailable`
    for a hard backend failure). Implementations should make all
    methods idempotent on re-entry — ``close()`` after ``close()``
    is a no-op, ``write_file()`` overwrites, etc.
    """

    @property
    def workspace(self) -> Path:  # pragma: no cover - protocol
        """Absolute path of the sandbox's root inside the host fs.

        For container-backed sandboxes this is the bind-mount path
        on the host side; the path *inside* the container is
        always ``/workspace``.
        """

    def write_file(self, relpath: str, content: str | bytes) -> Path:
        """Write *content* to ``<workspace>/<relpath>``."""
        ...  # pragma: no cover

    def read_file(self, relpath: str) -> str:
        """Read ``<workspace>/<relpath>`` as UTF-8 text."""
        ...  # pragma: no cover

    def run(
        self,
        argv: Iterable[str] | str,
        *,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        """Execute a command inside the sandbox."""
        ...  # pragma: no cover

    def close(self) -> None:
        """Tear down the workspace and release any resources."""
        ...  # pragma: no cover


__all__ = [
    "CommandResult",
    "Sandbox",
    "SandboxError",
    "SandboxNotAvailable",
]
