"""Tests for the v3.11 Tier-1 slash commands.

Covers: /hooks, /permissions, /plan, /branch (alias), /recap, /add-dir.
These are the user-facing dashboards on top of the v3.10
permissions+hooks+recap infrastructure.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.interactive.session import (
    COMMAND_REGISTRY,
    SLASH_COMMANDS,
    InteractiveSession,
    _cmd_add_dir,
    _cmd_hooks,
    _cmd_permissions,
    _cmd_plan,
    _cmd_recap,
    command_spec,
)


def _new_session(repo_root: Path, mode: str = "agent") -> InteractiveSession:
    return InteractiveSession(repo_root=repo_root, model="m", mode=mode)


def _isolate_user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("LYRA_HOME", str(home))
    return home


# ---------------------------------------------------------------------------
# /hooks
# ---------------------------------------------------------------------------


class TestCmdHooks:
    def test_no_hooks_configured_emits_helpful_template(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        s = _new_session(tmp_path)
        result = _cmd_hooks(s, "")
        assert "no user hooks configured" in result.output.lower()
        assert "settings.json" in result.output

    def test_lists_configured_hooks_with_master_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path
        settings = repo / ".lyra" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "enable_hooks": True,
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "Bash(rm *)", "command": "echo blocked"}
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        s = _new_session(repo)
        result = _cmd_hooks(s, "")
        assert "master: on" in result.output
        assert "Bash(rm *)" in result.output
        assert "echo blocked" in result.output

    def test_disabled_master_is_called_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path
        settings = repo / ".lyra" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "*", "command": "true"}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        s = _new_session(repo)
        result = _cmd_hooks(s, "")
        assert "master: OFF" in result.output


# ---------------------------------------------------------------------------
# /permissions
# ---------------------------------------------------------------------------


class TestCmdPermissions:
    def test_empty_policy_explains_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        s = _new_session(tmp_path)
        result = _cmd_permissions(s, "")
        assert "default policy" in result.output.lower()

    def test_renders_buckets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path
        settings = repo / ".lyra" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "permissions": {
                        "deny":  ["Bash(rm -rf *)"],
                        "ask":   ["Edit(./src/**)"],
                        "allow": ["Read", "Bash(git status)"],
                    }
                }
            ),
            encoding="utf-8",
        )
        s = _new_session(repo)
        result = _cmd_permissions(s, "")
        # Bucket order is deny → ask → allow (matches decision precedence).
        deny_idx = result.output.index("DENY")
        ask_idx = result.output.index("ASK")
        allow_idx = result.output.index("ALLOW")
        assert deny_idx < ask_idx < allow_idx

    def test_reload_drops_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        s = _new_session(tmp_path)
        s._policy_hooks_cache = ("sentinel",)  # type: ignore[attr-defined]
        result = _cmd_permissions(s, "reload")
        assert getattr(s, "_policy_hooks_cache") is None
        assert "cache dropped" in result.output


# ---------------------------------------------------------------------------
# /plan
# ---------------------------------------------------------------------------


class TestCmdPlan:
    def test_enters_plan_mode_from_agent(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path, mode="agent")
        result = _cmd_plan(s, "")
        assert s.mode == "plan_mode"
        assert result.new_mode == "plan_mode"

    def test_idempotent_when_already_in_plan(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path, mode="plan_mode")
        result = _cmd_plan(s, "")
        assert s.mode == "plan_mode"
        assert "already in plan" in result.output.lower()


# ---------------------------------------------------------------------------
# /branch (alias of /fork)
# ---------------------------------------------------------------------------


def test_branch_resolves_to_fork() -> None:
    spec = command_spec("branch")
    assert spec is not None
    assert spec.name == "fork", (
        f"/branch should alias /fork, got /{spec.name}"
    )
    assert "branch" in SLASH_COMMANDS


# ---------------------------------------------------------------------------
# /recap
# ---------------------------------------------------------------------------


class TestCmdRecap:
    def test_empty_session_returns_empty_message(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_recap(s, "")
        assert "empty" in result.output.lower()

    def test_summarises_recent_turns(self, tmp_path: Path) -> None:
        from lyra_cli.interactive.session import _TurnSnapshot

        s = _new_session(tmp_path)
        for i in range(3):
            s._turns_log.append(
                _TurnSnapshot(
                    line=f"prompt {i}",
                    mode="agent",
                    turn=i,
                    pending_task=None,
                    cost_usd=0.0,
                    tokens_used=0,
                    model="m",
                    ts=0.0,
                )
            )
        result = _cmd_recap(s, "")
        for i in range(3):
            assert f"prompt {i}" in result.output


# ---------------------------------------------------------------------------
# /add-dir
# ---------------------------------------------------------------------------


class TestCmdAddDir:
    def test_no_arg_lists_aux_dirs(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        # No aux dirs configured yet — should print usage / empty state.
        result = _cmd_add_dir(s, "")
        assert "no auxiliary directories" in result.output.lower()

    def test_adds_directory(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        target = tmp_path / "extra-repo"
        target.mkdir()
        result = _cmd_add_dir(s, str(target))
        assert target.resolve() in (s.aux_repo_roots or [])
        assert "added" in result.output.lower()

    def test_rejects_non_directory(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_add_dir(s, str(tmp_path / "does-not-exist"))
        assert "not a directory" in result.output.lower()

    def test_dedupes_repeated_add(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        target = tmp_path / "extra-repo"
        target.mkdir()
        _cmd_add_dir(s, str(target))
        result = _cmd_add_dir(s, str(target))
        assert "already registered" in result.output.lower()


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


def test_all_tier1_specs_registered() -> None:
    expected = {"hooks", "permissions", "plan", "recap", "add-dir"}
    actual = {s.name for s in COMMAND_REGISTRY}
    missing = expected - actual
    assert not missing, f"missing CommandSpecs: {missing}"
