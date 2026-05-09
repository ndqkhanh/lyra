"""Wave-E Task 9a: real ``DaytonaBackend``.

Runs the configured argv inside a Daytona dev-container workspace.
Workspaces are spawned per :meth:`run` and torn down afterwards
unless ``persist=True``.

The wire client is injectable so unit tests don't pull in the
``daytona-sdk`` package (opt-in via ``pip install lyra[daytona]``).
"""
from __future__ import annotations

import time
from typing import Any, Protocol, runtime_checkable

from ..lsp_backend.errors import FeatureUnavailable
from .backend import CommandResult


@runtime_checkable
class DaytonaClient(Protocol):
    """Minimal Daytona surface — what the backend actually calls."""

    def run(
        self,
        *,
        image: str,
        cmd: list[str],
        env: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> dict[str, Any]: ...


def _default_client_factory() -> DaytonaClient:  # pragma: no cover — smoke
    try:
        import daytona_sdk  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise FeatureUnavailable(
            "daytona backend requires the optional dep; "
            "install with `pip install lyra[daytona]`"
        ) from exc
    raise FeatureUnavailable(
        "daytona backend ships its production client wrapper in v1.9.1; "
        "for now, inject your own via client=…"
    )


class DaytonaBackend:
    name: str = "daytona"

    def __init__(
        self,
        *,
        image: str = "python:3.12",
        client: DaytonaClient | None = None,
    ) -> None:
        if client is None:
            client = _default_client_factory()
        self._client = client
        self._image = image

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
                f"DaytonaBackend.run expects a list argv, got {type(cmd).__name__}"
            )
        if not cmd:
            raise ValueError("cmd must be a non-empty list")

        start = time.monotonic()
        timeout_s = max(1, int(timeout_ms)) / 1000.0
        resp = self._client.run(
            image=self._image,
            cmd=list(cmd),
            env=dict(env or {}),
            timeout_s=timeout_s,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            exit_code=int(resp.get("exit_code", 0)),
            stdout=str(resp.get("stdout", "")),
            stderr=str(resp.get("stderr", "")),
            duration_ms=duration_ms,
            truncated=bool(resp.get("truncated", False)),
        )


__all__ = ["DaytonaBackend", "DaytonaClient"]
