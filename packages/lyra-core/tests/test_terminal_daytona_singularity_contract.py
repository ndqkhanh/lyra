"""Wave-E Task 9: contract tests for Daytona + Singularity backends."""
from __future__ import annotations

import sys
from typing import Any, List

import pytest

from lyra_core.lsp_backend import FeatureUnavailable
from lyra_core.terminal import CommandResult, TerminalBackend


# ---------------------------------------------------------------------------
# Daytona — fake client + tests
# ---------------------------------------------------------------------------


class _FakeDaytonaClient:
    def __init__(self, *, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.calls: List[dict[str, Any]] = []
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr

    def run(
        self,
        *,
        image: str,
        cmd: list[str],
        env: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "image": image,
                "cmd": list(cmd),
                "env": dict(env or {}),
                "timeout_s": timeout_s,
            }
        )
        return {
            "exit_code": self._exit_code,
            "stdout": self._stdout,
            "stderr": self._stderr,
        }


def test_daytona_backend_satisfies_terminal_backend_protocol() -> None:
    from lyra_core.terminal.daytona import DaytonaBackend

    b = DaytonaBackend(image="python:3.12", client=_FakeDaytonaClient())
    assert b.name == "daytona"
    assert isinstance(b, TerminalBackend)


def test_daytona_backend_raises_feature_unavailable_without_dep() -> None:
    from lyra_core.terminal.daytona import DaytonaBackend

    saved = sys.modules.get("daytona_sdk")
    sys.modules["daytona_sdk"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(FeatureUnavailable) as excinfo:
            DaytonaBackend(image="python:3.12")
        msg = str(excinfo.value).lower()
        assert "daytona" in msg
        assert "lyra[daytona]" in msg or "pip install" in msg
    finally:
        if saved is None:
            sys.modules.pop("daytona_sdk", None)
        else:
            sys.modules["daytona_sdk"] = saved


def test_daytona_run_delegates_image_cmd_env() -> None:
    from lyra_core.terminal.daytona import DaytonaBackend

    fake = _FakeDaytonaClient(exit_code=0, stdout="ok\n")
    b = DaytonaBackend(image="python:3.12", client=fake)

    result = b.run(["echo", "hi"], env={"FOO": "bar"})

    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "ok" in result.stdout
    call = fake.calls[0]
    assert call["image"] == "python:3.12"
    assert call["cmd"] == ["echo", "hi"]
    assert call["env"] == {"FOO": "bar"}


def test_daytona_argv_safety() -> None:
    from lyra_core.terminal.daytona import DaytonaBackend

    b = DaytonaBackend(image="python:3.12", client=_FakeDaytonaClient())
    with pytest.raises(ValueError):
        b.run([])
    with pytest.raises(TypeError):
        b.run("echo hi")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Singularity — fake runner + tests
# ---------------------------------------------------------------------------


class _FakeSingularityRunner:
    def __init__(self, *, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.calls: List[dict[str, Any]] = []
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr

    def __call__(self, *, argv: list[str], env: dict[str, str], timeout_s: float) -> dict[str, Any]:
        self.calls.append({"argv": list(argv), "env": dict(env), "timeout_s": timeout_s})
        return {
            "exit_code": self._exit_code,
            "stdout": self._stdout,
            "stderr": self._stderr,
        }


def test_singularity_backend_satisfies_terminal_backend_protocol() -> None:
    from lyra_core.terminal.singularity import SingularityBackend

    b = SingularityBackend(image="x.sif", runner=_FakeSingularityRunner())
    assert b.name == "singularity"
    assert isinstance(b, TerminalBackend)


def test_singularity_run_invokes_cli_with_image_and_cmd() -> None:
    from lyra_core.terminal.singularity import SingularityBackend

    runner = _FakeSingularityRunner(exit_code=0, stdout="ok")
    b = SingularityBackend(image="image.sif", runner=runner)

    result = b.run(["echo", "hi"])

    assert result.exit_code == 0
    assert "ok" in result.stdout
    argv = runner.calls[0]["argv"]
    assert argv[0] == "singularity"
    assert "image.sif" in argv
    assert argv[-2:] == ["echo", "hi"]


def test_singularity_argv_safety() -> None:
    from lyra_core.terminal.singularity import SingularityBackend

    b = SingularityBackend(image="image.sif", runner=_FakeSingularityRunner())
    with pytest.raises(ValueError):
        b.run([])
    with pytest.raises(TypeError):
        b.run("echo hi")  # type: ignore[arg-type]


def test_singularity_missing_cli_raises_feature_unavailable() -> None:
    from lyra_core.terminal.singularity import SingularityBackend

    # No runner injected → the backend probes ``shutil.which`` and the
    # CLI name we supply is intentionally missing.
    b = SingularityBackend(image="image.sif", cli="absolutely-not-a-real-bin-7842")
    with pytest.raises(FeatureUnavailable) as excinfo:
        b.run(["echo", "hi"])
    msg = str(excinfo.value).lower()
    assert "singularity" in msg
    assert "path" in msg
