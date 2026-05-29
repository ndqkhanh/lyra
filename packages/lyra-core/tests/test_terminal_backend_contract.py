"""Contract tests for the pluggable terminal backends."""

from __future__ import annotations

import sys

import pytest
from lyra_core.terminal import (
    CommandResult,
    LocalBackend,
    TerminalBackend,
    TerminalError,
)


def test_local_backend_satisfies_protocol() -> None:
    assert isinstance(LocalBackend(), TerminalBackend)


def test_local_backend_runs_echo() -> None:
    result = LocalBackend().run(
        [sys.executable, "-c", "import sys; print('hi'); print('bye', file=sys.stderr)"]
    )
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "hi" in result.stdout
    assert "bye" in result.stderr


def test_local_backend_non_zero_does_not_raise() -> None:
    result = LocalBackend().run([sys.executable, "-c", "import sys; sys.exit(17)"])
    assert result.exit_code == 17


def test_local_backend_timeout_marks_truncated() -> None:
    result = LocalBackend().run(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        timeout_ms=50,
    )
    assert result.truncated is True
    assert result.exit_code == -1


def test_local_backend_missing_binary_raises_terminal_error() -> None:
    with pytest.raises(TerminalError):
        LocalBackend().run(["definitely-not-a-real-command-lyra-42"])


def test_docker_backend_satisfies_protocol() -> None:
    """DockerBackend satisfies TerminalBackend protocol."""
    pytest.importorskip("docker", reason="docker package not available")
    from lyra_core.terminal.docker import DockerBackend

    try:
        backend = DockerBackend(image="python:3.12-slim")
    except Exception:
        pytest.skip("docker daemon not available")
    assert isinstance(backend, TerminalBackend)
    assert backend.name == "docker"


def test_modal_backend_satisfies_protocol() -> None:
    """ModalBackend satisfies TerminalBackend protocol."""
    from lyra_core.terminal.modal import ModalBackend

    try:
        backend = ModalBackend(image="python:3.12-slim")
    except Exception:
        pytest.skip("modal sandbox not available")
    assert isinstance(backend, TerminalBackend)
    assert backend.name == "modal"


def test_ssh_backend_satisfies_protocol() -> None:
    """SSHBackend satisfies TerminalBackend protocol."""
    pytest.importorskip("paramiko", reason="paramiko package not available")
    from lyra_core.terminal.ssh import SSHBackend

    backend = SSHBackend(host="testhost")
    assert isinstance(backend, TerminalBackend)
    assert backend.name == "ssh"
