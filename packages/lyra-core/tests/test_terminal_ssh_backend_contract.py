"""Wave-E Task 8: contract tests for the real SSH backend.

The unit tier injects a ``_FakeParamikoClient`` so CI doesn't need a
real SSH server. Smoke tests gate on ``LYRA_RUN_SMOKE=1`` +
``LYRA_SSH_HOST``.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, List

import pytest

from lyra_core.lsp_backend import FeatureUnavailable
from lyra_core.terminal import CommandResult, TerminalBackend


# ---------------------------------------------------------------------------
# Fake paramiko-shaped client
# ---------------------------------------------------------------------------


class _FakeChannel:
    def __init__(self, exit_code: int) -> None:
        self.exit_code = exit_code
        self.timeout: float | None = None

    def recv_exit_status(self) -> int:
        return self.exit_code

    def settimeout(self, seconds: float) -> None:
        self.timeout = seconds


@dataclass
class _FakeExecResult:
    stdout: bytes = b""
    stderr: bytes = b""
    exit_code: int = 0


class _FakeParamikoClient:
    """Mimics :class:`paramiko.SSHClient` for the bits the backend uses."""

    def __init__(self) -> None:
        self.connect_kwargs: dict[str, Any] = {}
        self.exec_calls: List[dict[str, Any]] = []
        self._next: _FakeExecResult | None = None
        self.closed: bool = False
        self.raise_on_exec: Exception | None = None

    def preload(self, result: _FakeExecResult) -> None:
        self._next = result

    def connect(self, **kwargs: Any) -> None:
        self.connect_kwargs = dict(kwargs)

    def exec_command(self, cmd: str, *, timeout: float | None = None):
        if self.raise_on_exec is not None:
            raise self.raise_on_exec
        self.exec_calls.append({"cmd": cmd, "timeout": timeout})
        result = self._next or _FakeExecResult()
        self._next = None
        chan_stdout = BytesIO(result.stdout)
        chan_stderr = BytesIO(result.stderr)
        chan_stdout.channel = _FakeChannel(result.exit_code)  # type: ignore[attr-defined]
        chan_stderr.channel = chan_stdout.channel  # type: ignore[attr-defined]
        return None, chan_stdout, chan_stderr

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ssh_backend_satisfies_terminal_backend_protocol() -> None:
    from lyra_core.terminal.ssh import SSHBackend

    b = SSHBackend(host="x", client=_FakeParamikoClient())
    assert b.name == "ssh"
    assert isinstance(b, TerminalBackend)


def test_ssh_backend_raises_feature_unavailable_without_paramiko() -> None:
    from lyra_core.terminal.ssh import SSHBackend

    saved = sys.modules.get("paramiko")
    sys.modules["paramiko"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(FeatureUnavailable) as excinfo:
            SSHBackend(host="x")
        msg = str(excinfo.value).lower()
        assert "ssh" in msg or "paramiko" in msg
        assert "lyra[ssh]" in msg or "pip install" in msg
    finally:
        if saved is None:
            sys.modules.pop("paramiko", None)
        else:
            sys.modules["paramiko"] = saved


def test_run_delegates_command_to_client() -> None:
    from lyra_core.terminal.ssh import SSHBackend

    fake = _FakeParamikoClient()
    fake.preload(_FakeExecResult(stdout=b"hi\n", exit_code=0))
    b = SSHBackend(host="server", user="ubuntu", port=22, client=fake)

    result = b.run(["echo", "hi"])

    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "hi" in result.stdout
    # Connect happened lazily on first run.
    assert fake.connect_kwargs["hostname"] == "server"
    assert fake.connect_kwargs["username"] == "ubuntu"
    assert fake.connect_kwargs["port"] == 22


def test_run_quotes_argv_safely() -> None:
    from lyra_core.terminal.ssh import SSHBackend

    fake = _FakeParamikoClient()
    fake.preload(_FakeExecResult(stdout=b"", exit_code=0))
    b = SSHBackend(host="x", client=fake)

    b.run(["echo", "hello world", "$(rm -rf /)"])

    cmd = fake.exec_calls[0]["cmd"]
    # Must NOT contain the unquoted destructive substring.
    assert "$(rm -rf /)" not in cmd or "'$(rm -rf /)'" in cmd
    # Plain shellwords containment so we know quoting happened.
    assert "echo" in cmd


def test_run_surfaces_non_zero_exit_code_without_raising() -> None:
    from lyra_core.terminal.ssh import SSHBackend

    fake = _FakeParamikoClient()
    fake.preload(_FakeExecResult(stdout=b"", stderr=b"err", exit_code=7))
    b = SSHBackend(host="x", client=fake)

    result = b.run(["false"])
    assert result.exit_code == 7
    assert "err" in result.stderr


def test_argv_safety() -> None:
    from lyra_core.terminal.ssh import SSHBackend

    b = SSHBackend(host="x", client=_FakeParamikoClient())
    with pytest.raises(ValueError):
        b.run([])
    with pytest.raises(TypeError):
        b.run("echo hi")  # type: ignore[arg-type]
