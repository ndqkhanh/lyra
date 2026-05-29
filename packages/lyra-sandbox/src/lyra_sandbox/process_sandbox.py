"""Lightweight subprocess-level sandbox with resource limits."""

from __future__ import annotations

import os
import platform
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass

from .exceptions import ResourceUsage
from .resource_limiter import ResourceLimiter, ResourceQuota


@dataclass(frozen=True)
class ProcessConfig:
    """Configuration for a sandboxed subprocess."""

    command: tuple[str, ...]
    work_dir: str = ""
    env_vars: tuple[tuple[str, str], ...] = ()
    timeout: int = 30
    resource_limits: ResourceQuota | None = None


@dataclass(frozen=True)
class ProcessResult:
    """Outcome of a sandboxed subprocess execution."""

    stdout: str
    stderr: str
    exit_code: int
    duration: float
    was_killed: bool = False
    resource_usage: ResourceUsage | None = None


class ProcessSandbox:
    """Lightweight sandbox that runs code in an isolated subprocess.

    No Docker required. Isolation is achieved via subprocess execution
    with resource limits and workspace containment.
    """

    _system = platform.system()

    @classmethod
    def execute(cls, config: ProcessConfig) -> ProcessResult:
        """Run a command with the given configuration."""
        env = _build_env(config.env_vars)
        work_dir = config.work_dir or tempfile.mkdtemp(prefix="lyra-sandbox-")

        start = time.monotonic()
        try:
            proc = subprocess.Popen(
                config.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                env=env,
                preexec_fn=os.setsid if cls._system != "Windows" else None,
            )
        except FileNotFoundError:
            return ProcessResult(
                stdout="",
                stderr=f"Command not found: {' '.join(config.command)}",
                exit_code=127,
                duration=time.monotonic() - start,
            )

        try:
            stdout, stderr = proc.communicate(timeout=config.timeout)
            duration = time.monotonic() - start
            was_killed = False
        except subprocess.TimeoutExpired:
            cls._kill_process_group(proc)
            stdout, stderr = proc.communicate()
            duration = time.monotonic() - start
            was_killed = True

        return ProcessResult(
            stdout=stdout.decode("utf-8", errors="replace") if stdout else "",
            stderr=stderr.decode("utf-8", errors="replace") if stderr else "",
            exit_code=proc.returncode if proc.returncode is not None else -1,
            duration=duration,
            was_killed=was_killed,
        )

    @classmethod
    def execute_with_limits(cls, config: ProcessConfig) -> ProcessResult:
        """Execute with resource limits applied."""
        if config.resource_limits is None:
            return cls.execute(config)

        quota = config.resource_limits
        env = _build_env(config.env_vars)
        work_dir = config.work_dir or tempfile.mkdtemp(prefix="lyra-sandbox-")
        start = time.monotonic()

        try:
            proc = subprocess.Popen(
                config.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                env=env,
                preexec_fn=lambda: cls._apply_process_limits(os.getpid(), quota),
            )
        except FileNotFoundError:
            return ProcessResult(
                stdout="",
                stderr=f"Command not found: {' '.join(config.command)}",
                exit_code=127,
                duration=time.monotonic() - start,
            )

        try:
            stdout, stderr = proc.communicate(timeout=config.timeout)
            duration = time.monotonic() - start
            was_killed = False
        except subprocess.TimeoutExpired:
            cls._kill_process_group(proc)
            stdout, stderr = proc.communicate()
            duration = time.monotonic() - start
            was_killed = True

        return ProcessResult(
            stdout=stdout.decode("utf-8", errors="replace") if stdout else "",
            stderr=stderr.decode("utf-8", errors="replace") if stderr else "",
            exit_code=proc.returncode if proc.returncode is not None else -1,
            duration=duration,
            was_killed=was_killed,
        )

    @staticmethod
    def _kill_process_group(proc: subprocess.Popen) -> None:
        """Kill the process and its group."""
        try:
            if proc.pid is not None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            proc.kill()

    @staticmethod
    def _apply_process_limits(pid: int, quota: ResourceQuota) -> None:
        """Apply resource limits to a process."""
        ResourceLimiter.apply_limits(pid, quota)


def _build_env(env_vars: tuple[tuple[str, str], ...]) -> dict[str, str]:
    """Build environment dict from key-value tuples."""
    env: dict[str, str] = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
    }
    for key, value in env_vars:
        env[key] = value
    return env
