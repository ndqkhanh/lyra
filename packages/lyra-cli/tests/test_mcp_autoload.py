"""Phase C.2 tests — MCP autoload + /mcp slash semantics.

Covers:

* ``autoload_mcp_servers`` happy-path when ``~/.lyra/mcp.json`` is set.
* Tolerance for missing files / disabled flag.
* ``find_mcp_server`` lookup.
* ``ensure_mcp_client_started`` caching behaviour with a fake transport.
* ``shutdown_all_mcp_clients`` calls ``close()`` on each transport.
* ``/mcp list``, ``/mcp connect``, ``/mcp disconnect``, ``/mcp tools``,
  ``/mcp reload`` slash command outputs.

We never spawn a real subprocess — the stdio transport is monkey-patched
to a tiny fake so the slash and autoload code paths can be exercised
without any process management overhead.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lyra_cli.interactive import mcp_autoload as autoload
from lyra_cli.interactive.session import InteractiveSession


def _write_user_config(home: Path, body: dict) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    target = home / "mcp.json"
    target.write_text(json.dumps(body), encoding="utf-8")
    return target


@pytest.fixture
def session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="mock", mode="agent")


@pytest.fixture
def lyra_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "lyra-home"
    monkeypatch.setenv("LYRA_HOME", str(home))
    monkeypatch.delenv("LYRA_DISABLE_MCP_AUTOLOAD", raising=False)
    return home


def test_autoload_with_no_config_leaves_session_empty(
    session: InteractiveSession, lyra_home: Path
) -> None:
    autoload.autoload_mcp_servers(session)
    assert session.mcp_servers == []
    assert session._mcp_load_issues == []


def test_autoload_populates_from_user_config(
    session: InteractiveSession, lyra_home: Path
) -> None:
    _write_user_config(
        lyra_home,
        {
            "mcpServers": {
                "filesystem": {
                    "command": "echo",
                    "args": ["hi"],
                    "trust": "third-party",
                }
            }
        },
    )
    autoload.autoload_mcp_servers(session)
    assert len(session.mcp_servers) == 1
    assert session.mcp_servers[0].name == "filesystem"


def test_autoload_disabled_via_env(
    session: InteractiveSession,
    lyra_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_user_config(
        lyra_home,
        {"mcpServers": {"x": {"command": "echo"}}},
    )
    monkeypatch.setenv("LYRA_DISABLE_MCP_AUTOLOAD", "1")
    autoload.autoload_mcp_servers(session)
    assert session.mcp_servers == []


def test_autoload_records_issues_for_bad_config(
    session: InteractiveSession, lyra_home: Path
) -> None:
    lyra_home.mkdir(parents=True, exist_ok=True)
    (lyra_home / "mcp.json").write_text("{not valid", encoding="utf-8")
    autoload.autoload_mcp_servers(session)
    assert session.mcp_servers == []
    assert len(session._mcp_load_issues) == 1


def test_find_mcp_server_returns_match(
    session: InteractiveSession, lyra_home: Path
) -> None:
    _write_user_config(lyra_home, {"mcpServers": {"a": {"command": "x"}}})
    autoload.autoload_mcp_servers(session)
    assert autoload.find_mcp_server(session, "a") is not None
    assert autoload.find_mcp_server(session, "missing") is None


class _FakeTransport:
    """Stand-in for :class:`StdioMCPTransport` used in autoload tests."""

    def __init__(self, name: str = "fake") -> None:
        self.server_name = name
        self.closed = False
        self.calls: list[Any] = []
        self.tools_response: list[dict] = [
            {"name": "ping", "inputSchema": {"type": "object"}}
        ]

    def list_tools(self) -> list[dict]:
        return list(self.tools_response)

    def call_tool(self, name: str, args, *, timeout=None):
        self.calls.append((name, dict(args), timeout))
        return {"content": [{"type": "text", "text": "ok"}]}

    def close(self) -> None:
        self.closed = True


def _patch_stdio(monkeypatch: pytest.MonkeyPatch, factory) -> None:
    """Replace ``StdioMCPTransport.start`` with a factory."""
    from lyra_mcp.client import stdio as stdio_module

    class _FakeStdio:
        @classmethod
        def start(cls, **kwargs):
            return factory(**kwargs)

    monkeypatch.setattr(stdio_module, "StdioMCPTransport", _FakeStdio)


def test_ensure_mcp_client_started_caches(
    session: InteractiveSession,
    lyra_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_user_config(lyra_home, {"mcpServers": {"fs": {"command": "echo"}}})
    autoload.autoload_mcp_servers(session)

    ts = _FakeTransport(name="fs")
    spawned: list[int] = []

    def factory(**_kw):
        spawned.append(1)
        return ts

    _patch_stdio(monkeypatch, factory)
    first = autoload.ensure_mcp_client_started(session, "fs")
    second = autoload.ensure_mcp_client_started(session, "fs")
    assert first is second is ts
    assert len(spawned) == 1


def test_ensure_mcp_client_started_returns_none_for_unknown(
    session: InteractiveSession, lyra_home: Path
) -> None:
    autoload.autoload_mcp_servers(session)
    assert autoload.ensure_mcp_client_started(session, "missing") is None


def test_ensure_mcp_client_started_swallows_spawn_errors(
    session: InteractiveSession,
    lyra_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_user_config(lyra_home, {"mcpServers": {"x": {"command": "echo"}}})
    autoload.autoload_mcp_servers(session)

    def factory(**_kw):
        raise RuntimeError("kaboom")

    _patch_stdio(monkeypatch, factory)
    assert autoload.ensure_mcp_client_started(session, "x") is None
    assert "x" not in session._mcp_clients


def test_shutdown_closes_every_client(
    session: InteractiveSession, lyra_home: Path
) -> None:
    a = _FakeTransport("a")
    b = _FakeTransport("b")
    session._mcp_clients = {"a": a, "b": b}
    autoload.shutdown_all_mcp_clients(session)
    assert a.closed and b.closed
    assert session._mcp_clients == {}


def test_shutdown_swallows_per_client_errors(
    session: InteractiveSession, lyra_home: Path
) -> None:
    class Boom:
        def close(self):
            raise RuntimeError("nope")

    session._mcp_clients = {"x": Boom()}
    autoload.shutdown_all_mcp_clients(session)
    assert session._mcp_clients == {}


# -------------------------- /mcp slash semantics --------------------------


def test_slash_mcp_list_shows_no_servers(session: InteractiveSession) -> None:
    result = session.dispatch("/mcp list")
    assert result.output is not None
    assert "no MCP servers" in result.output


def test_slash_mcp_list_shows_autoload_entries(
    session: InteractiveSession, lyra_home: Path
) -> None:
    _write_user_config(
        lyra_home,
        {"mcpServers": {"fs": {"command": "echo", "args": ["hi"]}}},
    )
    autoload.autoload_mcp_servers(session)
    out = session.dispatch("/mcp list").output or ""
    assert "MCP (stdio, autoloaded)" in out
    assert "fs" in out
    assert "[idle]" in out


def test_slash_mcp_connect_then_list_marks_connected(
    session: InteractiveSession,
    lyra_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_user_config(lyra_home, {"mcpServers": {"fs": {"command": "echo"}}})
    autoload.autoload_mcp_servers(session)
    _patch_stdio(monkeypatch, lambda **_kw: _FakeTransport("fs"))
    out = session.dispatch("/mcp connect fs").output or ""
    assert "connected" in out
    assert "ping" in out
    listed = session.dispatch("/mcp list").output or ""
    assert "[connected]" in listed


def test_slash_mcp_connect_unknown_name(
    session: InteractiveSession, lyra_home: Path
) -> None:
    autoload.autoload_mcp_servers(session)
    out = session.dispatch("/mcp connect ghost").output or ""
    assert "no MCP server" in out


def test_slash_mcp_tools_lists_advertised(
    session: InteractiveSession,
    lyra_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_user_config(lyra_home, {"mcpServers": {"fs": {"command": "echo"}}})
    autoload.autoload_mcp_servers(session)
    ts = _FakeTransport("fs")
    ts.tools_response = [
        {"name": "alpha", "description": "Alpha tool"},
        {"name": "beta"},
    ]
    _patch_stdio(monkeypatch, lambda **_kw: ts)
    out = session.dispatch("/mcp tools fs").output or ""
    assert "alpha" in out
    assert "beta" in out


def test_slash_mcp_disconnect_clears_session(
    session: InteractiveSession,
    lyra_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_user_config(lyra_home, {"mcpServers": {"fs": {"command": "echo"}}})
    autoload.autoload_mcp_servers(session)
    _patch_stdio(monkeypatch, lambda **_kw: _FakeTransport("fs"))
    session.dispatch("/mcp connect fs")
    assert "fs" in session._mcp_clients
    session.dispatch("/mcp disconnect fs")
    assert "fs" not in session._mcp_clients


def test_slash_mcp_reload_repicks_up_changes(
    session: InteractiveSession, lyra_home: Path
) -> None:
    autoload.autoload_mcp_servers(session)
    assert session.mcp_servers == []
    _write_user_config(lyra_home, {"mcpServers": {"fs": {"command": "echo"}}})
    out = session.dispatch("/mcp reload").output or ""
    assert "1 stdio server" in out
    assert any(s.name == "fs" for s in session.mcp_servers)


def test_slash_mcp_unknown_subcommand(session: InteractiveSession) -> None:
    out = session.dispatch("/mcp wat").output or ""
    assert "unknown subcommand" in out
    assert "list" in out
