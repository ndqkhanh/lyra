"""Wave-E Task 8: real ``SSHBackend`` (replaces v1.7.2 stub).

Runs a command on a remote host over SSH using
:mod:`paramiko`-shaped client (injectable for tests). Output is
captured fully so the contract matches every other backend.

Optional-dep discipline: missing :mod:`paramiko` →
:class:`FeatureUnavailable` with ``pip install lyra[ssh]`` hint.

Argv safety: the backend joins argv with :func:`shlex.join`, so
shell metacharacters in user-supplied arguments are properly quoted
and never inherit shell-injection risk.
"""
from __future__ import annotations

import shlex
import time
from typing import Any, Protocol, runtime_checkable

from ..lsp_backend.errors import FeatureUnavailable
from .backend import CommandResult


@runtime_checkable
class SSHClientProto(Protocol):
    """Minimal paramiko-shaped surface."""

    def connect(self, **kwargs: Any) -> None: ...
    def exec_command(self, cmd: str, *, timeout: float | None = None): ...
    def close(self) -> None: ...


def _default_client_factory() -> SSHClientProto:  # pragma: no cover — smoke
    try:
        import paramiko  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise FeatureUnavailable(
            "ssh backend requires the optional dep; "
            "install with `pip install lyra[ssh]` (paramiko)"
        ) from exc
    return paramiko.SSHClient()  # pragma: no cover


class SSHBackend:
    """Run commands over SSH against a remote host."""

    name: str = "ssh"

    def __init__(
        self,
        *,
        host: str,
        user: str = "",
        port: int = 22,
        key_filename: str | None = None,
        password: str | None = None,
        client: SSHClientProto | None = None,
        timeout_exception: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> None:
        if client is None:
            client = _default_client_factory()
        self._client = client
        self._host = host
        self._user = user
        self._port = port
        self._key_filename = key_filename
        self._password = password
        self._connected = False
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
                f"SSHBackend.run expects a list argv, got {type(cmd).__name__}"
            )
        if not cmd:
            raise ValueError("cmd must be a non-empty list")

        self._ensure_connected()
        start = time.monotonic()
        joined = shlex.join(cmd)
        if env:
            prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
            joined = f"{prefix} {joined}"
        if cwd:
            joined = f"cd {shlex.quote(cwd)} && {joined}"

        timeout_s = max(1, int(timeout_ms)) / 1000.0
        try:
            _stdin, stdout, stderr = self._client.exec_command(
                joined, timeout=timeout_s
            )
            out = self._decode(stdout.read())
            err = self._decode(stderr.read())
            channel = getattr(stdout, "channel", None)
            exit_code = (
                int(channel.recv_exit_status()) if channel is not None else 0
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            return CommandResult(
                exit_code=exit_code,
                stdout=out,
                stderr=err,
                duration_ms=duration_ms,
            )
        except self._timeout_excs:
            duration_ms = int((time.monotonic() - start) * 1000)
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"[ssh timeout after {timeout_ms}ms]",
                duration_ms=duration_ms,
                truncated=True,
            )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # pragma: no cover — best-effort
            pass
        self._connected = False

    def _ensure_connected(self) -> None:
        if self._connected:
            return
        kwargs: dict[str, Any] = {"hostname": self._host, "port": self._port}
        if self._user:
            kwargs["username"] = self._user
        if self._key_filename:
            kwargs["key_filename"] = self._key_filename
        if self._password:
            kwargs["password"] = self._password
        self._client.connect(**kwargs)
        self._connected = True

    @staticmethod
    def _decode(payload: Any) -> str:
        if payload is None:
            return ""
        if isinstance(payload, bytes):
            return payload.decode("utf-8", errors="replace")
        return str(payload)


__all__ = ["SSHBackend", "SSHClientProto"]
