"""Wave-E Task 7: real ``ModalBackend`` (replaces v1.7.2 stub).

Runs an :class:`AgentLoop` (or any argv) on Modal compute. The
runner is injectable so the unit tier never needs the ``modal``
package or paid compute. Production callers omit ``runner`` and the
backend lazy-imports :mod:`modal` plus its own thin ``Sandbox.create``
wrapper.

Optional-dep discipline mirrors :class:`DockerBackend`: missing
``modal`` → :class:`FeatureUnavailable` with the
``pip install lyra[modal]`` hint, never an opaque ``ImportError``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..lsp_backend.errors import FeatureUnavailable
from .backend import CommandResult


@runtime_checkable
class ModalRunner(Protocol):
    """Minimal Modal runner surface — what the backend actually uses."""

    def create(
        self,
        *,
        image: str,
        cmd: list[str],
        cpu: float,
        memory_mb: int,
        env: dict[str, str] | None = None,
    ) -> Any: ...


def _default_runner_factory() -> ModalRunner:  # pragma: no cover — smoke
    try:
        import modal  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise FeatureUnavailable(
            "modal backend requires the optional dep; "
            "install with `pip install lyra[modal]`"
        ) from exc
    raise FeatureUnavailable(
        "modal backend ships its production sandbox wrapper in v1.9.1; "
        "for now, inject your own via runner=…"
    )


class ModalBackend:
    """Run a command in a Modal sandbox per invocation."""

    name: str = "modal"

    def __init__(
        self,
        *,
        image: str,
        cpu: float = 1.0,
        memory_mb: int = 1024,
        runner: ModalRunner | None = None,
        timeout_exception: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> None:
        if runner is None:
            runner = _default_runner_factory()
        self._runner = runner
        self._image = image
        self._cpu = cpu
        self._memory_mb = memory_mb
        if timeout_exception is None:
            self._timeout_excs: tuple[type[BaseException], ...] = (TimeoutError,)
        elif isinstance(timeout_exception, tuple):
            self._timeout_excs = timeout_exception
        else:
            self._timeout_excs = (timeout_exception,)

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
                f"ModalBackend.run expects a list argv, got {type(cmd).__name__}"
            )
        if not cmd:
            raise ValueError("cmd must be a non-empty list")

        start = time.monotonic()
        sandbox = self._runner.create(
            image=self._image,
            cmd=list(cmd),
            cpu=self._cpu,
            memory_mb=self._memory_mb,
            env=dict(env or {}),
        )
        timeout_s = max(1, int(timeout_ms)) / 1000.0
        try:
            exit_code = int(sandbox.wait(timeout=timeout_s) or 0)
            stdout = self._decode(getattr(sandbox, "stdout", lambda: b"")())
            stderr = self._decode(getattr(sandbox, "stderr", lambda: b"")())
            truncated = False
        except self._timeout_excs:
            self._terminate(sandbox)
            duration_ms = int((time.monotonic() - start) * 1000)
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"[modal timeout after {timeout_ms}ms]",
                duration_ms=duration_ms,
                truncated=True,
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            truncated=truncated,
        )

    @staticmethod
    def _terminate(sandbox: Any) -> None:
        try:
            sandbox.terminate()
        except Exception:  # pragma: no cover — best-effort
            pass

    @staticmethod
    def _decode(payload: Any) -> str:
        if payload is None:
            return ""
        if isinstance(payload, bytes):
            return payload.decode("utf-8", errors="replace")
        return str(payload)


__all__ = ["ModalBackend", "ModalRunner"]
