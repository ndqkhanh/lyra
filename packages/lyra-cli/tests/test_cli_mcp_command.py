"""Tests for the ``lyra mcp`` Typer subcommand (Phase C.2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lyra_cli.__main__ import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def lyra_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "lyra-home"
    monkeypatch.setenv("LYRA_HOME", str(home))
    return home


def test_lyra_mcp_list_when_empty(runner: CliRunner, lyra_home: Path) -> None:
    result = runner.invoke(app, ["mcp", "list"])
    assert result.exit_code == 0, result.stdout
    assert "no MCP servers" in result.stdout


def test_lyra_mcp_add_then_list(
    runner: CliRunner, lyra_home: Path, tmp_path: Path
) -> None:
    add_result = runner.invoke(
        app,
        [
            "mcp",
            "add",
            "fs",
            "--command",
            "echo",
            "--arg",
            "hi",
            "--arg",
            "bye",
            "--env",
            "FOO=bar",
            "--trust",
            "first-party",
        ],
    )
    assert add_result.exit_code == 0, add_result.stdout
    target = lyra_home / "mcp.json"
    assert target.exists()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["mcpServers"]["fs"]["command"] == "echo"
    assert payload["mcpServers"]["fs"]["args"] == ["hi", "bye"]
    assert payload["mcpServers"]["fs"]["env"] == {"FOO": "bar"}
    assert payload["mcpServers"]["fs"]["trust"] == "first-party"

    list_result = runner.invoke(app, ["mcp", "list"])
    assert list_result.exit_code == 0
    assert "fs" in list_result.stdout
    assert "echo" in list_result.stdout


def test_lyra_mcp_add_rejects_bad_env(
    runner: CliRunner, lyra_home: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "mcp",
            "add",
            "fs",
            "--command",
            "echo",
            "--env",
            "no-equals-sign",
        ],
    )
    assert result.exit_code != 0
    assert "bad --env" in result.stdout


def test_lyra_mcp_remove(runner: CliRunner, lyra_home: Path) -> None:
    runner.invoke(
        app,
        ["mcp", "add", "fs", "--command", "echo"],
    )
    rm = runner.invoke(app, ["mcp", "remove", "fs"])
    assert rm.exit_code == 0
    assert "removed" in rm.stdout
    again = runner.invoke(app, ["mcp", "remove", "fs"])
    assert again.exit_code == 0
    assert "not removed" in again.stdout


def test_lyra_mcp_doctor_empty_exit_code_zero(
    runner: CliRunner, lyra_home: Path
) -> None:
    result = runner.invoke(app, ["mcp", "doctor"])
    assert result.exit_code == 0
    assert "no MCP servers" in result.stdout


def test_lyra_mcp_doctor_reports_missing_executable(
    runner: CliRunner, lyra_home: Path
) -> None:
    runner.invoke(
        app,
        [
            "mcp",
            "add",
            "ghost",
            "--command",
            "definitely-not-on-path-zzz-9999",
        ],
    )
    result = runner.invoke(app, ["mcp", "doctor"])
    assert result.exit_code != 0
    assert "missing on PATH" in result.stdout


def test_lyra_mcp_list_json_output(runner: CliRunner, lyra_home: Path) -> None:
    runner.invoke(
        app,
        ["mcp", "add", "fs", "--command", "echo", "--arg", "hi"],
    )
    result = runner.invoke(app, ["mcp", "list", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert any(s["name"] == "fs" for s in payload["servers"])
