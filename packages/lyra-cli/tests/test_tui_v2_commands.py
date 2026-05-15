"""Contract tests for the v3.14 Phase 2 slash-command set.

Tests run against the harness-tui registry without mounting a real
``HarnessApp`` — each command takes ``(app, args)`` and the test
supplies a minimal stub app with the surfaces the command touches.
The stub records all chat-log writes so assertions are simple.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from harness_tui.commands.registry import REGISTRY


# Importing the package registers every Lyra command as a side effect.
from lyra_cli.tui_v2 import commands as _lyra_commands  # noqa: F401
from lyra_cli.tui_v2.commands import (
    budget as budget_mod,
    escape as escape_mod,
    skills_mcp as skills_mcp_mod,
)


# ---------------------------------------------------------------------
# Stub HarnessApp
# ---------------------------------------------------------------------


class _FakeChatLog:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def write_system(self, text: str) -> None:
        self.messages.append(text)

    @property
    def last(self) -> str:
        return self.messages[-1] if self.messages else ""


class _FakeStatusLine:
    def __init__(self) -> None:
        self.segments: dict[str, str] = {}

    def set_segment(self, key: str, value: str) -> None:
        self.segments[key] = value


class _FakeShell:
    def __init__(self) -> None:
        self.chat_log = _FakeChatLog()
        self.status_line = _FakeStatusLine()


def _build_app(
    *,
    working_dir: Path,
    model: str = "deepseek-chat",
    mode: str = "default",
    extra_payload: dict[str, Any] | None = None,
    totals: dict[str, float] | None = None,
    sessions: list | None = None,
) -> Any:
    """Construct a stub HarnessApp surface for command tests."""
    cfg = SimpleNamespace(
        name="lyra",
        model=model,
        working_dir=str(working_dir),
        transport=SimpleNamespace(name="lyra"),
        extra_payload=dict(extra_payload or {}),
    )
    app = SimpleNamespace(
        cfg=cfg,
        mode=mode,
        shell=_FakeShell(),
        size=SimpleNamespace(width=120, height=40),
        _session_id="s_test_session_123",
        session_totals=lambda: dict(
            totals or {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
        ),
        session_store=SimpleNamespace(
            list=lambda project, limit=10: list(sessions or [])[:limit]
        ),
        set_mode=lambda m: setattr(app, "mode", m) or _set_mode_side(app, m),
        notify=lambda *_a, **_kw: None,
        exit=lambda: setattr(app, "exited", True),
    )
    return app


def _set_mode_side(app, m: str) -> None:
    app.shell.status_line.set_segment("mode", m)


def _run(coro) -> None:
    asyncio.run(coro)


# ---------------------------------------------------------------------
# Registration contract
# ---------------------------------------------------------------------


def test_all_phase2_commands_registered() -> None:
    """Every command this phase ports must land in the harness-tui registry."""
    expected = {
        "status", "version", "exit", "cwd",
        "mode", "budget", "session",
        "skill", "mcp", "lyra",
    }
    missing = expected - set(REGISTRY)
    assert not missing, f"unregistered commands: {sorted(missing)}"


def test_commands_have_descriptions_and_categories() -> None:
    """Palette UX depends on description + category — guard against regressions."""
    for name in {"status", "mode", "budget", "session", "skill", "mcp", "lyra"}:
        cmd = REGISTRY[name]
        assert cmd.description, name
        assert cmd.category, name


# ---------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------


def test_status_shows_model_mode_repo(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path, model="deepseek-chat", mode="plan")
    _run(REGISTRY["status"].handler(app, ""))
    msg = app.shell.chat_log.last
    assert "deepseek-chat" in msg
    assert "plan" in msg
    assert str(tmp_path) in msg
    assert "120 x 40" in msg


# ---------------------------------------------------------------------
# /version
# ---------------------------------------------------------------------


def test_version_prints_running_version(tmp_path: Path) -> None:
    from lyra_cli import __version__

    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["version"].handler(app, ""))
    assert __version__ in app.shell.chat_log.last


# ---------------------------------------------------------------------
# /exit
# ---------------------------------------------------------------------


def test_exit_calls_app_exit(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["exit"].handler(app, ""))
    assert getattr(app, "exited", False) is True


# ---------------------------------------------------------------------
# /mode
# ---------------------------------------------------------------------


def test_mode_no_args_shows_current(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path, mode="default")
    _run(REGISTRY["mode"].handler(app, ""))
    assert "default" in app.shell.chat_log.last


def test_mode_set_valid(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path, mode="default")
    _run(REGISTRY["mode"].handler(app, "plan"))
    assert app.mode == "plan"


def test_mode_set_invalid(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path, mode="default")
    _run(REGISTRY["mode"].handler(app, "garbage"))
    assert "unknown mode" in app.shell.chat_log.last.lower()
    assert app.mode == "default"  # unchanged


# ---------------------------------------------------------------------
# /budget
# ---------------------------------------------------------------------


def test_budget_no_args_shows_state(tmp_path: Path) -> None:
    app = _build_app(
        working_dir=tmp_path,
        extra_payload={"budget": 5.0},
        totals={"cost_usd": 0.42, "tokens_in": 0, "tokens_out": 0},
    )
    _run(REGISTRY["budget"].handler(app, ""))
    msg = app.shell.chat_log.last
    assert "$5.00" in msg
    assert "$0.4200" in msg


def test_budget_no_cap_shows_no_cap(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["budget"].handler(app, ""))
    assert "no cap" in app.shell.chat_log.last.lower()


def test_budget_set_updates_cap(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["budget"].handler(app, "set 7.50"))
    assert app.cfg.extra_payload.get("budget") == pytest.approx(7.5)
    assert "$7.50" in app.shell.chat_log.last


def test_budget_set_rejects_bad_number(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["budget"].handler(app, "set notanumber"))
    assert "not a number" in app.shell.chat_log.last.lower()
    assert "budget" not in (app.cfg.extra_payload or {})


def test_budget_save_persists_to_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["budget"].handler(app, "save 12.00"))
    persisted = json.loads((fake_home / ".lyra" / "auth.json").read_text())
    assert persisted["budget_cap_usd"] == pytest.approx(12.0)


# ---------------------------------------------------------------------
# /session
# ---------------------------------------------------------------------


def test_session_info_shows_id_and_totals(tmp_path: Path) -> None:
    app = _build_app(
        working_dir=tmp_path,
        totals={"tokens_in": 100, "tokens_out": 250, "cost_usd": 0.0150},
    )
    _run(REGISTRY["session"].handler(app, "info"))
    msg = app.shell.chat_log.last
    assert "s_test_session_123" in msg
    assert "100/250" in msg
    assert "$0.0150" in msg


def test_session_list_empty(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path, sessions=[])
    _run(REGISTRY["session"].handler(app, "list"))
    assert "no recorded sessions" in app.shell.chat_log.last.lower()


def test_session_list_renders_records(tmp_path: Path) -> None:
    records = [
        SimpleNamespace(
            id=f"s_{i:08d}_abcdef", title=f"turn {i}", cost_usd=0.001 * i,
            tokens_in=i, tokens_out=i, updated_at=None,
        )
        for i in range(3)
    ]
    app = _build_app(working_dir=tmp_path, sessions=records)
    _run(REGISTRY["session"].handler(app, "list"))
    msg = app.shell.chat_log.last
    assert "recent sessions" in msg
    assert "s_00000000" in msg
    assert "turn 1" in msg


# ---------------------------------------------------------------------
# /skill — discovery helper
# ---------------------------------------------------------------------


def test_list_skills_finds_project_skill_with_description(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "make-coffee"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: make-coffee\ndescription: Brews a perfect espresso\n---\nBody.\n"
    )
    skills = skills_mcp_mod._list_skills(tmp_path)
    assert ("project", "make-coffee", "Brews a perfect espresso") in skills


def test_skill_command_empty_state(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["skill"].handler(app, "list"))
    # No SKILL.md anywhere under tmp_path
    msg = app.shell.chat_log.last
    assert "no skills" in msg.lower() or "installed skills" in msg.lower()


# ---------------------------------------------------------------------
# /mcp — discovery helper
# ---------------------------------------------------------------------


def test_list_mcp_parses_stdio_and_http(tmp_path: Path) -> None:
    cfg = tmp_path / ".lyra" / "mcp.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({
        "mcpServers": {
            "fs": {"command": "mcp-server-fs"},
            "remote": {"url": "https://example.com/mcp"},
            "broken": "not-a-dict",
        }
    }))
    servers = skills_mcp_mod._list_mcp(tmp_path)
    names = {n for n, _ in servers}
    assert {"fs", "remote", "broken"} <= names
    by_name = dict(servers)
    assert "stdio" in by_name["fs"]
    assert "http" in by_name["remote"]


def test_mcp_command_empty_state(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["mcp"].handler(app, "list"))
    assert "no MCP servers" in app.shell.chat_log.last


# ---------------------------------------------------------------------
# /lyra escape hatch
# ---------------------------------------------------------------------


def test_lyra_escape_no_args_prints_usage(tmp_path: Path) -> None:
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["lyra"].handler(app, ""))
    assert "usage" in app.shell.chat_log.last.lower()


def test_lyra_executable_locator_returns_path_or_none() -> None:
    # Just contract: returns a str path that exists, or None.
    result = escape_mod._lyra_executable()
    assert result is None or Path(result).exists()


def test_lyra_escape_runs_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the executable to a known shell command (``echo``) and verify
    stdout flows into the chat log + exit code is reported."""
    monkeypatch.setattr(escape_mod, "_lyra_executable", lambda: "/bin/echo")
    app = _build_app(working_dir=tmp_path)
    _run(REGISTRY["lyra"].handler(app, "hello phase2"))
    msgs = app.shell.chat_log.messages
    # First message: command echo "$ lyra ..."; then stdout; then exit code.
    assert any("hello phase2" in m for m in msgs)
    assert any("exit code 0" in m for m in msgs)
