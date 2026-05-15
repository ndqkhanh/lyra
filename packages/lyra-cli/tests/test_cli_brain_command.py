"""Contract tests for ``lyra brain`` (Phase J.1).

These exercise the CLI surface end-to-end:

* ``lyra brain list`` shows the four built-ins.
* ``lyra brain show <name>`` prints description + soul + policy.
* ``lyra brain install <name>`` writes files into the target repo.
* idempotency / ``--force`` behaviour.
* unknown bundle names exit with a non-zero status.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.__main__ import app
from typer.testing import CliRunner


def _runner() -> CliRunner:
    return CliRunner()


def test_brain_list_shows_builtins() -> None:
    result = _runner().invoke(app, ["brain", "list"])
    assert result.exit_code == 0, result.output
    out = result.output
    for name in ("default", "tdd-strict", "research", "ship-fast"):
        assert name in out


def test_brain_show_default_prints_soul_preview() -> None:
    result = _runner().invoke(app, ["brain", "show", "default"])
    assert result.exit_code == 0, result.output
    assert "default brain" in result.output
    assert "toolset" in result.output


def test_brain_show_unknown_exits_nonzero() -> None:
    result = _runner().invoke(app, ["brain", "show", "no-such-brain"])
    assert result.exit_code != 0
    assert "unknown brain" in result.output


def test_brain_install_default_into_tmp_repo(tmp_path: Path) -> None:
    result = _runner().invoke(
        app,
        ["brain", "install", "default", "--repo-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "SOUL.md").exists()
    assert (tmp_path / ".lyra" / "brain.txt").read_text().strip() == "default"


def test_brain_install_tdd_strict_writes_policy(tmp_path: Path) -> None:
    result = _runner().invoke(
        app,
        ["brain", "install", "tdd-strict", "--repo-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    policy = tmp_path / ".lyra" / "policy.yaml"
    assert policy.exists()
    assert "tdd_gate: on" in policy.read_text()


def test_brain_install_is_idempotent_without_force(tmp_path: Path) -> None:
    soul = tmp_path / "SOUL.md"
    soul.parent.mkdir(parents=True, exist_ok=True)
    soul.write_text("# user-written\n")
    result = _runner().invoke(
        app,
        ["brain", "install", "default", "--repo-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert soul.read_text() == "# user-written\n"
    assert "skipped" in result.output.lower()


def test_brain_install_force_overwrites(tmp_path: Path) -> None:
    soul = tmp_path / "SOUL.md"
    soul.parent.mkdir(parents=True, exist_ok=True)
    soul.write_text("# stale\n")
    result = _runner().invoke(
        app,
        [
            "brain",
            "install",
            "ship-fast",
            "--repo-root",
            str(tmp_path),
            "--force",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "ship-fast" in soul.read_text()


def test_brain_install_unknown_exits_nonzero(tmp_path: Path) -> None:
    result = _runner().invoke(
        app,
        ["brain", "install", "no-such", "--repo-root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "unknown brain" in result.output
