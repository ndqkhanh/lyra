"""Real ``DockerBackend`` — docker-py wrapper (v1.7.3).

Runs a command inside a fresh container on every :meth:`run` and
tears the container down afterwards. Satisfies the
:class:`lyra_core.terminal.TerminalBackend` protocol so policy wiring
(dangerous-command allow/deny, output normalization) is shared with
:class:`LocalBackend`.

Optional-dep discipline: ``import docker`` happens inside the
constructor. When the package is missing we raise
:class:`FeatureUnavailable` with an install hint pointing at the
``lyra[docker]`` extra.

Testability: a ``client`` kwarg accepts an injected docker client
(production: ``docker.from_env()``; tests: a minimal double). The
backend only touches ``client.containers.run(...)`` + the returned
container's ``wait``, ``logs``, ``kill``, ``remove`` methods, so the
double can be very small.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from ..lsp_backend.errors import FeatureUnavailable
from .backend import CommandResult


def _default_timeout_exception() -> tuple[type[BaseException], ...]:
    """Resolve the timeout sentinel types from docker-py + requests at
    construction time, if available."""
    excs: list[type[BaseException]] = []
    try:
        import requests.exceptions as rex  # type: ignore[import-not-found]

        excs.append(rex.ReadTimeout)
        excs.append(rex.ConnectionError)
    except Exception:  # pragma: no cover - optional dep
        pass
    try:
        import docker.errors as derr  # type: ignore[import-not-found]

        excs.append(derr.APIError)
    except Exception:  # pragma: no cover - optional dep
        pass
    return tuple(excs) or (TimeoutError,)


class DockerBackend:
    """Run commands inside a fresh docker container per invocation."""

    name: str = "docker"

    def __init__(
        self,
        *,
        image: str,
        client: Any | None = None,
        network: str | None = None,
        volumes: dict[str, dict] | None = None,
        timeout_exception: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> None:
        if client is None:
            try:
                import docker  # type: ignore[import-not-found]
            except Exception as exc:
                raise FeatureUnavailable(
                    "docker python client is not installed. "
                    "Install with `pip install 'lyra[docker]'` "
                    f"(underlying error: {type(exc).__name__}: {exc})"
                ) from exc
            client = docker.from_env()

        self._client = client
        self._image = image
        self._network = network
        self._volumes = dict(volumes or {})
        if timeout_exception is None:
            self._timeout_excs = _default_timeout_exception()
        elif isinstance(timeout_exception, tuple):
            self._timeout_excs = timeout_exception
        else:
            self._timeout_excs = (timeout_exception,)

    # ---- TerminalBackend surface ---------------------------------- #

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
                f"DockerBackend.run expects a list argv, got {type(cmd).__name__}"
            )
        if not cmd:
            raise ValueError("cmd must be a non-empty list")

        start = time.monotonic()
        run_kwargs: dict[str, Any] = {
            "detach": True,
            "working_dir": cwd,
            "environment": dict(env or {}),
        }
        if self._network is not None:
            run_kwargs["network"] = self._network
        if self._volumes:
            run_kwargs["volumes"] = dict(self._volumes)

        container = self._client.containers.run(
            self._image,
            list(cmd),
            **run_kwargs,
        )

        timeout_s = max(1, int(timeout_ms)) / 1000.0
        try:
            wait_result = container.wait(timeout=timeout_s)
            exit_code = int(wait_result.get("StatusCode", 0)) if isinstance(wait_result, dict) else 0
            stdout = self._decode(container.logs(stdout=True, stderr=False))
            stderr = self._decode(container.logs(stdout=False, stderr=True))
            truncated = False
        except self._timeout_excs:
            self._kill_and_remove(container)
            duration_ms = int((time.monotonic() - start) * 1000)
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"[timeout after {timeout_ms}ms]",
                duration_ms=duration_ms,
                truncated=True,
            )
        finally:
            if not getattr(container, "removed", False):
                self._safe_remove(container)

        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            truncated=truncated,
        )

    # ---- helpers --------------------------------------------------- #

    def _kill_and_remove(self, container: Any) -> None:
        try:
            container.kill()
        except Exception:  # pragma: no cover - best-effort
            pass
        self._safe_remove(container)

    def _safe_remove(self, container: Any) -> None:
        try:
            container.remove()
        except Exception:  # pragma: no cover - best-effort
            pass

    @staticmethod
    def _decode(payload: Any) -> str:
        if payload is None:
            return ""
        if isinstance(payload, bytes):
            return payload.decode("utf-8", errors="replace")
        return str(payload)


__all__ = ["DockerBackend"]
