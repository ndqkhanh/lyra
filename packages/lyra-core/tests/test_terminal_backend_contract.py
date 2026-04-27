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
from lyra_core.terminal.stubs import (
    DaytonaBackend,
    DockerBackend,
    ModalBackend,
    SSHBackend,
    SingularityBackend,
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


@pytest.mark.parametrize(
    "backend,name",
    [
        (DockerBackend(), "docker"),
        (ModalBackend(), "modal"),
        (SSHBackend(host="x"), "ssh"),
        (DaytonaBackend(), "daytona"),
        (SingularityBackend(), "singularity"),
    ],
)
def test_remote_stubs_raise_scaffold_error(backend, name) -> None:
    with pytest.raises(TerminalError, match="scaffold"):
        backend.run(["echo", "hi"])
    assert backend.name == name
