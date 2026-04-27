"""Contract tests for the real :class:`DockerBackend` (v1.7.3).

The v1.7.2 pass shipped a ``DockerBackend`` that raised
``TerminalError`` on every call. This pass flips it to a real
``docker-py`` wrapper; the unit tests exercise behaviour with a
``_FakeDockerClient`` so CI doesn't need a docker daemon.

Invariants tested:

- Satisfies :class:`TerminalBackend` protocol (has ``name`` + ``run``).
- ``FeatureUnavailable`` when ``docker`` package is not importable,
  with an install-hint message pointing at ``lyra[docker]``.
- ``run(cmd)`` delegates to the injected client's ``containers.run``
  with the configured image, command, working dir, and env.
- Exit-code + stdout + stderr are surfaced faithfully from the fake
  client.
- Timeout kills the running container and returns a truncated
  :class:`CommandResult` (never raises on timeout).
- ``cmd`` must be a non-empty list — argv-safe, no shell concatenation.
"""
from __future__ import annotations

import sys

import pytest

from lyra_core.lsp_backend import FeatureUnavailable
from lyra_core.terminal import CommandResult, TerminalBackend


# --- fake docker client -------------------------------------------- #


class _FakeContainer:
    def __init__(self, *, exit_code: int = 0, logs: bytes = b"", raise_on_wait: Exception | None = None):
        self._exit_code = exit_code
        self._logs = logs
        self._raise_on_wait = raise_on_wait
        self.killed = False
        self.removed = False

    def wait(self, *, timeout: float | None = None):
        if self._raise_on_wait is not None:
            raise self._raise_on_wait
        return {"StatusCode": self._exit_code}

    def logs(self, *, stdout: bool = True, stderr: bool = True) -> bytes:
        return self._logs

    def kill(self) -> None:
        self.killed = True

    def remove(self) -> None:
        self.removed = True


class _FakeContainers:
    def __init__(self) -> None:
        self.run_calls: list[dict] = []
        self._next_container: _FakeContainer | None = None

    def preload(self, container: _FakeContainer) -> None:
        self._next_container = container

    def run(self, image: str, command, **kwargs) -> _FakeContainer:
        self.run_calls.append(
            {"image": image, "command": command, **kwargs}
        )
        ctr = self._next_container or _FakeContainer()
        self._next_container = None
        return ctr


class _FakeDockerClient:
    def __init__(self) -> None:
        self.containers = _FakeContainers()


# --- import + construction ----------------------------------------- #


def test_docker_backend_satisfies_terminal_backend_protocol() -> None:
    from lyra_core.terminal.docker import DockerBackend

    b = DockerBackend(image="alpine:3.20", client=_FakeDockerClient())
    assert b.name == "docker"
    # Protocol check at runtime — duck-typed ``run`` + ``name`` present.
    assert isinstance(b, TerminalBackend)


def test_docker_backend_raises_feature_unavailable_without_docker_py() -> None:
    from lyra_core.terminal.docker import DockerBackend

    saved = sys.modules.get("docker")
    sys.modules["docker"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(FeatureUnavailable) as excinfo:
            DockerBackend(image="alpine:3.20")
        msg = str(excinfo.value).lower()
        assert "docker" in msg
        assert "lyra[docker]" in msg or "pip install" in msg
    finally:
        if saved is None:
            sys.modules.pop("docker", None)
        else:
            sys.modules["docker"] = saved


# --- run(): happy path ---------------------------------------------- #


def test_run_delegates_image_command_cwd_env_to_client() -> None:
    from lyra_core.terminal.docker import DockerBackend

    fake = _FakeDockerClient()
    fake.containers.preload(_FakeContainer(exit_code=0, logs=b"ok\n"))
    b = DockerBackend(image="alpine:3.20", client=fake)

    result = b.run(
        ["echo", "hi"],
        cwd="/work",
        env={"FOO": "bar"},
    )

    assert len(fake.containers.run_calls) == 1
    call = fake.containers.run_calls[0]
    assert call["image"] == "alpine:3.20"
    assert call["command"] == ["echo", "hi"]
    assert call["working_dir"] == "/work"
    assert call["environment"] == {"FOO": "bar"}
    # Detached so we can implement timeout + log streaming.
    assert call["detach"] is True

    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "ok" in result.stdout


def test_run_surfaces_non_zero_exit_code_without_raising() -> None:
    from lyra_core.terminal.docker import DockerBackend

    fake = _FakeDockerClient()
    fake.containers.preload(_FakeContainer(exit_code=7, logs=b"exploded"))
    b = DockerBackend(image="alpine:3.20", client=fake)

    result = b.run(["false"])

    assert result.exit_code == 7
    # Backend must not raise on non-zero; caller decides how to react
    # (parity with LocalBackend contract).


# --- timeout behaviour --------------------------------------------- #


def test_timeout_kills_container_and_returns_truncated() -> None:
    from lyra_core.terminal.docker import DockerBackend

    class _TimeoutExc(Exception):
        pass

    # ``_TimeoutExc`` stands in for whatever exception docker-py's
    # ``wait(timeout=...)`` raises on read timeout; the backend is
    # configured (via ``timeout_exception``) to treat this class as
    # the timeout sentinel so tests don't need docker-py installed.
    fake = _FakeDockerClient()
    ctr = _FakeContainer(raise_on_wait=_TimeoutExc("read timeout"))
    fake.containers.preload(ctr)
    b = DockerBackend(
        image="alpine:3.20",
        client=fake,
        timeout_exception=_TimeoutExc,  # let tests pin the sentinel
    )

    result = b.run(["sleep", "99"], timeout_ms=50)

    assert result.truncated is True
    assert result.exit_code == -1
    assert ctr.killed is True
    assert ctr.removed is True


# --- argv safety --------------------------------------------------- #


def test_empty_cmd_raises_value_error() -> None:
    from lyra_core.terminal.docker import DockerBackend

    b = DockerBackend(image="alpine:3.20", client=_FakeDockerClient())
    with pytest.raises(ValueError):
        b.run([])


def test_string_cmd_rejected_keeps_argv_safety() -> None:
    from lyra_core.terminal.docker import DockerBackend

    b = DockerBackend(image="alpine:3.20", client=_FakeDockerClient())
    with pytest.raises(TypeError):
        b.run("echo hi")  # type: ignore[arg-type]
