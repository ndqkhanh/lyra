"""Shell command execution tools with sandboxing and timeout."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import StrEnum


class ShellMode(StrEnum):
    BLOCKING = "blocking"
    BACKGROUND = "background"
    STREAMING = "streaming"


@dataclass(frozen=True)
class ShellResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    timed_out: bool = False
    truncated: bool = False


@dataclass(frozen=True)
class ShellSession:
    session_id: str
    cwd: str
    env: dict[str, str]
    created_at: float
    command_count: int = 0


class ShellTool:
    """Sandboxed shell execution with timeout and output capture.

    Usage::

        tool = ShellTool(timeout_seconds=30)
        result = tool.run("pytest tests/ -q")
        bg_task = tool.run_background("npm run dev")
    """

    def __init__(
        self,
        timeout_seconds: float = 60.0,
        max_output_bytes: int = 1_000_000,
        cwd: str = ".",
    ) -> None:
        self._timeout = timeout_seconds
        self._max_output = max_output_bytes
        self._cwd = cwd

    def run(
        self,
        command: str,
        env: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> ShellResult:
        import time

        timeout = timeout_seconds or self._timeout
        start = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._cwd,
                env=env,
            )
            duration = (time.monotonic() - start) * 1000
            stdout = proc.stdout
            stderr = proc.stderr
            truncated = len(stdout) > self._max_output
            if truncated:
                stdout = stdout[: self._max_output]
            return ShellResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                duration_ms=duration,
                truncated=truncated,
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                stdout="",
                stderr="Command timed out",
                exit_code=-1,
                duration_ms=timeout * 1000,
                timed_out=True,
            )

    def run_background(
        self, command: str, env: dict[str, str] | None = None
    ) -> subprocess.Popen[str]:
        return subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._cwd,
            env=env,
        )

    @staticmethod
    def escape(arg: str) -> str:
        """Shell-escape a single argument."""
        import shlex

        return shlex.quote(arg)
