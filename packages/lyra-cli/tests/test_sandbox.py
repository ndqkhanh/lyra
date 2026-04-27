"""Tests for :mod:`lyra_cli.sandbox`."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lyra_cli.sandbox import (
    CommandResult,
    DockerSandbox,
    LocalSandbox,
    Sandbox,
    SandboxError,
    SandboxNotAvailable,
    pick_sandbox,
)


# ---------------------------------------------------------------------------
# LocalSandbox
# ---------------------------------------------------------------------------


def test_local_sandbox_implements_protocol() -> None:
    s = LocalSandbox()
    try:
        assert isinstance(s, Sandbox)
    finally:
        s.close()


def test_local_sandbox_workspace_is_isolated_dir(tmp_path: Path) -> None:
    s = LocalSandbox()
    try:
        ws = s.workspace
        assert ws.is_dir()
        assert ws.exists()
    finally:
        s.close()
    assert not ws.exists(), "workspace must be torn down on close()"


def test_local_sandbox_write_and_read_round_trip() -> None:
    with LocalSandbox() as s:
        s.write_file("hello.txt", "hi from sandbox")
        assert s.read_file("hello.txt") == "hi from sandbox"


def test_local_sandbox_creates_parent_dirs() -> None:
    with LocalSandbox() as s:
        s.write_file("nested/dir/file.py", "print('hi')\n")
        assert (s.workspace / "nested" / "dir" / "file.py").is_file()


def test_local_sandbox_rejects_path_escapes() -> None:
    with LocalSandbox() as s:
        with pytest.raises(SandboxError, match="escapes sandbox"):
            s.write_file("../escape.txt", "x")
        with pytest.raises(SandboxError, match="escapes sandbox"):
            s.read_file("/etc/passwd")


def test_local_sandbox_run_captures_output() -> None:
    with LocalSandbox() as s:
        result = s.run(["echo", "hello"])
        assert isinstance(result, CommandResult)
        assert result.ok
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.duration_ms >= 0


def test_local_sandbox_run_string_uses_bash() -> None:
    with LocalSandbox() as s:
        result = s.run("echo abc | tr a-z A-Z")
        assert result.ok
        assert "ABC" in result.stdout


def test_local_sandbox_run_respects_cwd() -> None:
    with LocalSandbox() as s:
        s.write_file("nested/file.txt", "ok")
        result = s.run(["cat", "file.txt"], cwd="nested")
        assert result.ok
        assert result.stdout.strip() == "ok"


def test_local_sandbox_run_propagates_env() -> None:
    with LocalSandbox() as s:
        result = s.run(["env"], env={"LYRA_TEST_VAR": "marker"})
        assert "LYRA_TEST_VAR=marker" in result.stdout


def test_local_sandbox_run_non_zero_exit_is_not_ok() -> None:
    with LocalSandbox() as s:
        result = s.run(["bash", "-c", "exit 7"])
        assert result.exit_code == 7
        assert result.ok is False


def test_local_sandbox_run_handles_timeout() -> None:
    with LocalSandbox() as s:
        result = s.run(["bash", "-c", "sleep 5"], timeout=0.1)
        assert result.timed_out is True
        assert result.exit_code == 124
        assert result.ok is False


def test_local_sandbox_run_after_close_errors() -> None:
    s = LocalSandbox()
    s.close()
    with pytest.raises(SandboxError, match="closed"):
        s.run(["echo", "x"])


def test_local_sandbox_close_is_idempotent() -> None:
    s = LocalSandbox()
    s.close()
    s.close()


def test_command_result_to_dict_is_json_safe() -> None:
    import json

    r = CommandResult(
        argv=["echo", "x"], exit_code=0, stdout="x\n", stderr="",
        duration_ms=1.5, timed_out=False,
    )
    json.dumps(r.to_dict())


# ---------------------------------------------------------------------------
# Picker
# ---------------------------------------------------------------------------


def test_pick_sandbox_local_always_returns_local() -> None:
    s = pick_sandbox(preference="local")
    try:
        assert isinstance(s, LocalSandbox)
    finally:
        s.close()


def test_pick_sandbox_auto_returns_local_when_docker_missing(monkeypatch) -> None:
    """Without ``docker`` on PATH the cascade must fall through to local."""
    real_which = shutil.which

    def fake_which(name, *a, **kw):
        if name == "docker":
            return None
        return real_which(name, *a, **kw)

    monkeypatch.setattr(shutil, "which", fake_which)
    s = pick_sandbox(preference="auto")
    try:
        assert isinstance(s, LocalSandbox)
    finally:
        s.close()


def test_pick_sandbox_docker_raises_when_missing(monkeypatch) -> None:
    real_which = shutil.which

    def fake_which(name, *a, **kw):
        if name == "docker":
            return None
        return real_which(name, *a, **kw)

    monkeypatch.setattr(shutil, "which", fake_which)
    with pytest.raises(SandboxNotAvailable):
        pick_sandbox(preference="docker")


# ---------------------------------------------------------------------------
# DockerSandbox (requires docker shim)
# ---------------------------------------------------------------------------


def test_docker_sandbox_raises_when_docker_missing(monkeypatch) -> None:
    real_which = shutil.which

    def fake_which(name, *a, **kw):
        if name == "docker":
            return None
        return real_which(name, *a, **kw)

    monkeypatch.setattr(shutil, "which", fake_which)
    with pytest.raises(SandboxNotAvailable):
        DockerSandbox()


def test_docker_sandbox_run_invokes_docker_with_expected_argv(tmp_path: Path) -> None:
    """Build a fake ``docker`` shim that records argv to a file."""
    shim = tmp_path / "fake-docker"
    log = tmp_path / "args.txt"
    shim.write_text(
        "#!/bin/bash\n"
        f"echo \"$@\" >> {log}\n"
        "echo from-shim\n"
        "exit 0\n"
    )
    shim.chmod(0o755)

    sandbox = DockerSandbox(
        docker_bin=str(shim),
        image="custom:tag",
        network="none",
    )
    try:
        result = sandbox.run(["python", "-c", "print(1)"])
        assert result.ok
        assert "from-shim" in result.stdout
        recorded = log.read_text()
        # Image, working dir, and inner command must all appear in the argv.
        assert "custom:tag" in recorded
        assert "/workspace" in recorded
        assert "python" in recorded
    finally:
        sandbox.close()


def test_docker_sandbox_propagates_exit_code(tmp_path: Path) -> None:
    shim = tmp_path / "fake-docker"
    shim.write_text("#!/bin/bash\nexit 5\n")
    shim.chmod(0o755)

    sandbox = DockerSandbox(docker_bin=str(shim))
    try:
        result = sandbox.run(["whatever"])
        assert result.exit_code == 5
        assert result.ok is False
    finally:
        sandbox.close()
