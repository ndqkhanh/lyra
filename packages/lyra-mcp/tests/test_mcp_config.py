"""Tests for ``lyra_mcp.client.config`` (Phase C.2).

We exercise:

* Discovery precedence (project beats user when both define the same
  server name).
* Tolerance for missing files / malformed JSON / bad entry shapes.
* ``add_user_mcp_server`` / ``remove_user_mcp_server`` round-trips,
  including idempotency.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_mcp.client.config import (
    MCPLoadResult,
    MCPServerConfig,
    add_user_mcp_server,
    default_config_paths,
    load_mcp_config,
    load_mcp_config_from,
    remove_user_mcp_server,
)


def _write_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_returns_empty_when_no_files_present(tmp_path: Path) -> None:
    result = load_mcp_config_from([tmp_path / "missing.json"])
    assert isinstance(result, MCPLoadResult)
    assert result.servers == []
    assert result.issues == []


def test_load_parses_basic_user_entry(tmp_path: Path) -> None:
    user_cfg = tmp_path / "user.json"
    _write_config(
        user_cfg,
        {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        "/tmp",
                    ],
                    "env": {"DEBUG": "1"},
                    "trust": "third-party",
                }
            }
        },
    )
    result = load_mcp_config_from([user_cfg])
    assert len(result.servers) == 1
    fs = result.servers[0]
    assert isinstance(fs, MCPServerConfig)
    assert fs.name == "filesystem"
    assert fs.command == (
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/tmp",
    )
    assert fs.env == {"DEBUG": "1"}
    assert fs.trust == "third-party"
    assert fs.source == user_cfg
    assert fs.is_runnable() is True


def test_project_overrides_user_for_same_name(tmp_path: Path) -> None:
    user_cfg = tmp_path / "user.json"
    proj_cfg = tmp_path / "project.json"
    _write_config(
        user_cfg,
        {"mcpServers": {"git": {"command": "uvx", "args": ["mcp-server-git"]}}},
    )
    _write_config(
        proj_cfg,
        {
            "mcpServers": {
                "git": {
                    "command": "uvx",
                    "args": ["mcp-server-git", "--repository", "/repo"],
                    "trust": "first-party",
                }
            }
        },
    )
    # Project comes second → wins.
    result = load_mcp_config_from([user_cfg, proj_cfg])
    assert len(result.servers) == 1
    git = result.servers[0]
    assert git.command == ("uvx", "mcp-server-git", "--repository", "/repo")
    assert git.trust == "first-party"
    assert git.source == proj_cfg


def test_invalid_json_recorded_as_issue(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    result = load_mcp_config_from([bad])
    assert result.servers == []
    assert len(result.issues) == 1
    assert result.issues[0].source == bad
    assert "invalid JSON" in result.issues[0].message


def test_top_level_non_object_recorded_as_issue(tmp_path: Path) -> None:
    weird = tmp_path / "weird.json"
    weird.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    result = load_mcp_config_from([weird])
    assert result.servers == []
    assert any("must be an object" in i.message for i in result.issues)


def test_entry_missing_command_skipped_with_issue(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    _write_config(
        cfg,
        {
            "mcpServers": {
                "broken": {"args": ["x"]},
                "ok": {"command": "echo", "args": ["hi"]},
            }
        },
    )
    result = load_mcp_config_from([cfg])
    names = [s.name for s in result.servers]
    assert names == ["ok"]
    assert any(i.name == "broken" for i in result.issues)


def test_args_must_be_list_of_strings(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    _write_config(
        cfg,
        {"mcpServers": {"x": {"command": "x", "args": ["a", 1, "b"]}}},
    )
    result = load_mcp_config_from([cfg])
    assert result.servers == []
    assert any("args" in i.message for i in result.issues)


def test_default_config_paths_under_lyra_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    paths = default_config_paths(tmp_path / "repo")
    assert paths[0] == tmp_path / ".lyra" / "mcp.json"
    assert paths[1] == tmp_path / "repo" / ".lyra" / "mcp.json"


def test_add_and_remove_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra-home"))
    written = add_user_mcp_server(
        name="git",
        command="uvx",
        args=["mcp-server-git"],
        env={"FOO": "bar"},
        cwd="/tmp",
        trust="first-party",
    )
    assert written.exists()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["mcpServers"]["git"]["command"] == "uvx"
    assert payload["mcpServers"]["git"]["env"] == {"FOO": "bar"}
    assert payload["mcpServers"]["git"]["cwd"] == "/tmp"
    assert payload["mcpServers"]["git"]["trust"] == "first-party"

    removed = remove_user_mcp_server("git")
    assert removed is True
    payload2 = json.loads(written.read_text(encoding="utf-8"))
    assert "git" not in payload2["mcpServers"]

    # Idempotent.
    assert remove_user_mcp_server("git") is False


def test_add_overwrites_existing_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra-home"))
    add_user_mcp_server(name="x", command="echo", args=["a"])
    add_user_mcp_server(name="x", command="echo", args=["b", "c"])
    written = tmp_path / "lyra-home" / "mcp.json"
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["mcpServers"]["x"]["args"] == ["b", "c"]


def test_remove_when_file_missing_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "nope"))
    assert remove_user_mcp_server("anything") is False
