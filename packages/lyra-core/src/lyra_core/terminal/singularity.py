"""Wave-E Task 9b: real ``SingularityBackend`` (a.k.a. Apptainer).

Wraps the local ``singularity`` (or ``apptainer``) CLI via
:mod:`subprocess`. No optional Python deps required — but the CLI
itself must be on ``$PATH``; missing CLI → :class:`FeatureUnavailable`.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from typing import Any

from ..lsp_backend.errors import FeatureUnavailable
from .backend import CommandResult


class SingularityBackend:
    name: str = "singularity"

    def __init__(
        self,
        *,
        image: str,
        cli: str = "singularity",
        runner: Any | None = None,
    ) -> None:
        self._image = image
        self._cli = cli
        self._runner = runner

    def run(
        self,
        cmd: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_ms: int = 30_000,
    ) -> CommandResult:
        if not isinstance(cmd, list):
            raise TypeError(
                f"SingularityBackend.run expects a list argv, got {type(cmd).__name__}"
            )
        if not cmd:
            raise ValueError("cmd must be a non-empty list")
        if self._runner is None and shutil.which(self._cli) is None:
            raise FeatureUnavailable(
                f"singularity backend: CLI {self._cli!r} not found on PATH; "
                "install Singularity / Apptainer to use this backend"
            )

        start = time.monotonic()
        argv = [self._cli, "exec", self._image, *cmd]
        timeout_s = max(1, int(timeout_ms)) / 1000.0
        try:
            if self._runner is not None:
                resp = self._runner(argv=argv, env=env or {}, timeout_s=timeout_s)
                return CommandResult(
                    exit_code=int(resp.get("exit_code", 0)),
                    stdout=str(resp.get("stdout", "")),
                    stderr=str(resp.get("stderr", "")),
                    duration_ms=int((time.monotonic() - start) * 1000),
                    truncated=bool(resp.get("truncated", False)),
                )
            proc = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return CommandResult(
                exit_code=-1,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\n[singularity timeout after {timeout_ms}ms]",
                duration_ms=duration_ms,
                truncated=True,
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=duration_ms,
        )


__all__ = ["SingularityBackend"]
