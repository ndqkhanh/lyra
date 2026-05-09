"""Local-tempdir sandbox (always available).

Backs the :class:`Sandbox` protocol with ``tempfile.mkdtemp`` plus
:func:`subprocess.run`. No isolation beyond a fresh directory and a
``timeout=`` kwarg, but it's the right fallback when the host
doesn't have Docker and the user just wants a scratch space the
agent can throw away.

Path safety is the only real protection: every relpath is resolved
inside :attr:`workspace`, and an attempt to escape via ``..`` or an
absolute path raises :class:`SandboxError` instead of touching the
real filesystem.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Iterable, Mapping

from .base import CommandResult, SandboxError


class LocalSandbox:
    """Tempdir-backed :class:`Sandbox` implementation."""

    def __init__(self, *, prefix: str = "lyra-sandbox-") -> None:
        self._workspace = Path(tempfile.mkdtemp(prefix=prefix))
        self._closed = False

    # ---- protocol ---------------------------------------------------

    @property
    def workspace(self) -> Path:
        return self._workspace

    def write_file(self, relpath: str, content: str | bytes) -> Path:
        target = self._safe_path(relpath)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_bytes(content)
        return target

    def read_file(self, relpath: str) -> str:
        target = self._safe_path(relpath)
        if not target.is_file():
            raise SandboxError(f"no such file in sandbox: {relpath!r}")
        return target.read_text(encoding="utf-8")

    def run(
        self,
        argv: Iterable[str] | str,
        *,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        if self._closed:
            raise SandboxError("sandbox already closed")

        # We accept either a list (preferred — no shell quoting) or a
        # raw string (sugar for ``bash -c``). Stash the original argv
        # in the result so observers see what the caller asked for,
        # not the post-rewrite shell command.
        if isinstance(argv, str):
            display_argv = [argv]
            cmd: list[str] = ["bash", "-c", argv]
            shell = False
        else:
            display_argv = list(argv)
            cmd = display_argv
            shell = False

        run_env = {**os.environ, **(env or {})}
        run_cwd = self._safe_path(cwd) if cwd else self._workspace

        start = time.time()
        timed_out = False
        try:
            proc = subprocess.run(  # noqa: S603 — explicit argv
                cmd,
                cwd=str(run_cwd),
                env=run_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell,
                check=False,
            )
            stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as e:
            timed_out = True
            exit_code = 124
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
            stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode("utf-8", "replace")
        duration_ms = (time.time() - start) * 1000.0

        return CommandResult(
            argv=display_argv,
            exit_code=exit_code,
            stdout=stdout or "",
            stderr=stderr or "",
            duration_ms=duration_ms,
            timed_out=timed_out,
        )

    def close(self) -> None:
        if self._closed:
            return
        # ``ignore_errors`` because a half-written file is still
        # ours — there's nothing useful for the caller to do
        # about a stray permission error during teardown.
        shutil.rmtree(self._workspace, ignore_errors=True)
        self._closed = True

    def __enter__(self) -> "LocalSandbox":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---- internals --------------------------------------------------

    def _safe_path(self, relpath: str) -> Path:
        """Resolve *relpath* inside :attr:`workspace`; reject escapes.

        We accept absolute paths only when they already point inside
        the workspace (e.g. callers passing back a path returned by
        :meth:`write_file`). Anything else — ``..``, ``/etc``,
        symlink-style escapes — gets rejected before any IO happens.
        """
        if not relpath:
            raise SandboxError("relpath must be a non-empty string")
        candidate = Path(relpath)
        if candidate.is_absolute():
            try:
                candidate.resolve().relative_to(self._workspace.resolve())
            except ValueError as e:
                raise SandboxError(
                    f"absolute path {relpath!r} escapes sandbox"
                ) from e
            return candidate
        merged = (self._workspace / candidate).resolve()
        try:
            merged.relative_to(self._workspace.resolve())
        except ValueError as e:
            raise SandboxError(
                f"relative path {relpath!r} escapes sandbox"
            ) from e
        return merged


__all__ = ["LocalSandbox"]
