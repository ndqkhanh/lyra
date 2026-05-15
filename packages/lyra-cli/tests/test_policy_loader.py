"""Tests for ``lyra_cli.policy_loader`` — layered settings → Policy / hooks."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.policy_loader import load_hooks, load_policy
from lyra_core.permissions.grammar import Verdict


def _write_settings(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _isolate_user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point LYRA_HOME at a tmpdir so user-level settings don't leak in.

    Without this, the test inherits whatever ``~/.lyra/settings.json``
    happens to exist on the dev machine — flaky in CI and brittle to
    "well it works on my laptop" failures.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("LYRA_HOME", str(home))
    return home


# ---------------------------------------------------------------------------
# load_policy
# ---------------------------------------------------------------------------


class TestLoadPolicy:
    def test_no_settings_returns_empty_policy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        policy = load_policy(tmp_path / "repo")
        assert policy.is_empty()

    def test_project_settings_loaded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path / "repo"
        _write_settings(
            repo / ".lyra" / "settings.json",
            {
                "permissions": {
                    "deny": ["Bash(rm -rf *)"],
                    "allow": ["Read"],
                }
            },
        )
        policy = load_policy(repo)
        # Deny rule wins over default ASK for Bash.
        assert (
            policy.decide("Bash", {"command": "rm -rf /tmp/x"}).verdict
            is Verdict.DENY
        )

    def test_user_and_project_compose(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path / "repo"
        _write_settings(
            home / "settings.json",
            {"permissions": {"allow": ["Bash(npm test)"]}},
        )
        _write_settings(
            repo / ".lyra" / "settings.json",
            {"permissions": {"deny": ["Bash(rm -rf *)"]}},
        )
        policy = load_policy(repo)
        # User allow rule still applies.
        assert (
            policy.decide("Bash", {"command": "npm test"}).verdict
            is Verdict.ALLOW
        )
        # Project deny rule still applies.
        assert (
            policy.decide("Bash", {"command": "rm -rf /tmp/x"}).verdict
            is Verdict.DENY
        )

    def test_project_rules_match_first_in_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Both layers declare an allow for the same tool but with
        # different specifiers — the *project* rule should be matched
        # first since it sits at the head of the list.
        home = _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path / "repo"
        _write_settings(
            home / "settings.json",
            {"permissions": {"allow": ["Bash(git *)"]}},
        )
        _write_settings(
            repo / ".lyra" / "settings.json",
            {"permissions": {"allow": ["Bash(git status)"]}},
        )
        policy = load_policy(repo)
        match = policy.decide("Bash", {"command": "git status"})
        assert match.rule.source == "Bash(git status)"


# ---------------------------------------------------------------------------
# load_hooks
# ---------------------------------------------------------------------------


class TestLoadHooks:
    def test_no_settings_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        specs, enabled = load_hooks(tmp_path / "repo")
        assert specs == []
        assert enabled is False

    def test_master_switch_from_either_layer_enables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Project file omits the flag; user file enables it. The
        # composite should be enabled — opting in once at the user
        # level shouldn't be undone by every greenfield project.
        home = _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path / "repo"
        _write_settings(
            home / "settings.json",
            {
                "enable_hooks": True,
                "hooks": {
                    "PreToolUse": [{"matcher": "*", "command": "true"}]
                },
            },
        )
        _write_settings(
            repo / ".lyra" / "settings.json",
            {
                "hooks": {
                    "PreToolUse": [{"matcher": "Bash(rm *)", "command": "false"}]
                }
            },
        )
        specs, enabled = load_hooks(repo)
        assert enabled is True
        assert len(specs) == 2
        # Project specs come first so they fire before user specs.
        assert specs[0].matcher == "Bash(rm *)"

    def test_disabled_when_no_layer_enables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _isolate_user_home(tmp_path, monkeypatch)
        repo = tmp_path / "repo"
        _write_settings(
            repo / ".lyra" / "settings.json",
            {
                "hooks": {
                    "PreToolUse": [{"matcher": "*", "command": "true"}]
                }
            },
        )
        specs, enabled = load_hooks(repo)
        # Specs still parse so /doctor can show them — runtime gating
        # via ``enabled`` is the operative check.
        assert len(specs) == 1
        assert enabled is False
