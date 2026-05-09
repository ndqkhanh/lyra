"""Wave-E Task 7: contract tests for the real Modal backend.

The unit tier injects a ``_FakeModalRunner`` so CI doesn't need a
Modal account or paid compute. Smoke tests against the real Modal
service gate on ``LYRA_MODAL_TOKEN`` + ``LYRA_RUN_PAID_SMOKE=1``
(not exercised here).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, List

import pytest

from lyra_core.lsp_backend import FeatureUnavailable
from lyra_core.terminal import CommandResult, TerminalBackend


# ---------------------------------------------------------------------------
# Fake Modal runner
# ---------------------------------------------------------------------------


@dataclass
class _FakeModalSandbox:
    """Mimics the surface of ``modal.Sandbox.create``."""

    cmd: List[str]
    image: str
    cpu: float
    memory_mb: int
    env: dict[str, str] = field(default_factory=dict)
    exit_code: int = 0
    stdout_bytes: bytes = b""
    stderr_bytes: bytes = b""
    raise_on_wait: Exception | None = None
    killed: bool = False

    def wait(self, *, timeout: float | None = None) -> int:
        if self.raise_on_wait is not None:
            raise self.raise_on_wait
        return self.exit_code

    def stdout(self) -> bytes:
        return self.stdout_bytes

    def stderr(self) -> bytes:
        return self.stderr_bytes

    def terminate(self) -> None:
        self.killed = True


class _FakeModalRunner:
    """Modal-shaped runner — matches ``modal.Sandbox.create``."""

    def __init__(self) -> None:
        self.create_calls: List[dict[str, Any]] = []
        self._next: _FakeModalSandbox | None = None

    def preload(self, sandbox: _FakeModalSandbox) -> None:
        self._next = sandbox

    def create(
        self,
        *,
        image: str,
        cmd: List[str],
        cpu: float,
        memory_mb: int,
        env: dict[str, str] | None = None,
    ) -> _FakeModalSandbox:
        self.create_calls.append(
            {
                "image": image,
                "cmd": cmd,
                "cpu": cpu,
                "memory_mb": memory_mb,
                "env": dict(env or {}),
            }
        )
        sb = self._next or _FakeModalSandbox(
            cmd=cmd, image=image, cpu=cpu, memory_mb=memory_mb
        )
        self._next = None
        return sb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_modal_backend_satisfies_terminal_backend_protocol() -> None:
    from lyra_core.terminal.modal import ModalBackend

    b = ModalBackend(image="python:3.12-slim", runner=_FakeModalRunner())
    assert b.name == "modal"
    assert isinstance(b, TerminalBackend)


def test_modal_backend_raises_feature_unavailable_without_modal_dep() -> None:
    from lyra_core.terminal.modal import ModalBackend

    saved = sys.modules.get("modal")
    sys.modules["modal"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(FeatureUnavailable) as excinfo:
            ModalBackend(image="python:3.12")
        msg = str(excinfo.value).lower()
        assert "modal" in msg
        assert "lyra[modal]" in msg or "pip install" in msg
    finally:
        if saved is None:
            sys.modules.pop("modal", None)
        else:
            sys.modules["modal"] = saved


def test_run_delegates_image_cpu_memory_env_to_runner() -> None:
    from lyra_core.terminal.modal import ModalBackend

    runner = _FakeModalRunner()
    runner.preload(
        _FakeModalSandbox(
            cmd=["echo", "hi"],
            image="python:3.12",
            cpu=2.0,
            memory_mb=4096,
            stdout_bytes=b"ok\n",
        )
    )
    b = ModalBackend(image="python:3.12", cpu=2.0, memory_mb=4096, runner=runner)

    result = b.run(["echo", "hi"], env={"FOO": "bar"})

    assert len(runner.create_calls) == 1
    call = runner.create_calls[0]
    assert call["image"] == "python:3.12"
    assert call["cmd"] == ["echo", "hi"]
    assert call["cpu"] == 2.0
    assert call["memory_mb"] == 4096
    assert call["env"] == {"FOO": "bar"}

    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "ok" in result.stdout


def test_run_surfaces_non_zero_exit_code_without_raising() -> None:
    from lyra_core.terminal.modal import ModalBackend

    runner = _FakeModalRunner()
    runner.preload(
        _FakeModalSandbox(
            cmd=["false"],
            image="python:3.12",
            cpu=1.0,
            memory_mb=512,
            exit_code=42,
            stderr_bytes=b"died",
        )
    )
    b = ModalBackend(image="python:3.12", runner=runner)

    result = b.run(["false"])
    assert result.exit_code == 42
    assert "died" in result.stderr


def test_timeout_terminates_sandbox_and_returns_truncated() -> None:
    from lyra_core.terminal.modal import ModalBackend

    class _TimeoutExc(Exception):
        pass

    runner = _FakeModalRunner()
    sb = _FakeModalSandbox(
        cmd=["sleep", "99"],
        image="python:3.12",
        cpu=1.0,
        memory_mb=512,
        raise_on_wait=_TimeoutExc("read timeout"),
    )
    runner.preload(sb)
    b = ModalBackend(image="python:3.12", runner=runner, timeout_exception=_TimeoutExc)

    result = b.run(["sleep", "99"], timeout_ms=50)

    assert result.truncated is True
    assert result.exit_code == -1
    assert sb.killed is True


def test_argv_safety() -> None:
    from lyra_core.terminal.modal import ModalBackend

    b = ModalBackend(image="python:3.12", runner=_FakeModalRunner())
    with pytest.raises(ValueError):
        b.run([])
    with pytest.raises(TypeError):
        b.run("echo hi")  # type: ignore[arg-type]
