"""Local subprocess backend — the one that always works."""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .backend import CommandResult, TerminalError

__all__ = ["LocalBackend"]


@dataclass
class LocalBackend:
    name: str = "local"

    def run(
        self,
        cmd: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_ms: int = 30_000,
    ) -> CommandResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=max(timeout_ms, 1) / 1000.0,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return CommandResult(
                exit_code=-1,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\n[timeout after {timeout_ms}ms]",
                duration_ms=duration_ms,
                truncated=True,
            )
        except FileNotFoundError as exc:
            raise TerminalError(f"local backend: {exc}") from exc

        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=duration_ms,
        )
