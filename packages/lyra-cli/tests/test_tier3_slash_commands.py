"""Tests for v3.11 Tier-3 + Tier-4 slash commands.

Covers: /pr-comments (gh wrapper), /schedule (alias of /cron),
/sandbox (FS strict-mode), /plugin + /reload-plugins, /release-notes,
/login (alias of /auth), /logout (creds clear).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from lyra_cli.interactive.session import (
    COMMAND_REGISTRY,
    InteractiveSession,
    _cmd_logout,
    _cmd_plugin,
    _cmd_pr_comments,
    _cmd_release_notes,
    _cmd_reload_plugins,
    _cmd_sandbox,
    _cmd_schedule,
    command_spec,
)


def _new_session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="m", mode="agent")


# ---------------------------------------------------------------------------
# /pr-comments
# ---------------------------------------------------------------------------


class TestCmdPrComments:
    def test_no_gh_cli_emits_install_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "lyra_cli.interactive.session._which", lambda c: False
        )
        s = _new_session(tmp_path)
        result = _cmd_pr_comments(s, "")
        assert "gh CLI" in result.output
        assert "install" in result.output.lower()


# ---------------------------------------------------------------------------
# /schedule — pure alias of /cron
# ---------------------------------------------------------------------------


def test_schedule_alias_delegates_to_cron(tmp_path: Path) -> None:
    s = _new_session(tmp_path)
    # Bare /cron prints status; calling /schedule should produce the same
    # output (no extra wrapping noise).
    from lyra_cli.interactive.session import _cmd_cron

    expected = _cmd_cron(s, "").output
    actual = _cmd_schedule(s, "").output
    assert expected == actual


# ---------------------------------------------------------------------------
# /sandbox
# ---------------------------------------------------------------------------


class TestCmdSandbox:
    def test_toggle_off_to_on(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_sandbox(s, "")
        assert s.sandbox_strict is True
        _cmd_sandbox(s, "")
        assert s.sandbox_strict is False

    def test_explicit_on(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_sandbox(s, "on")
        assert s.sandbox_strict is True

    def test_invalid_rejected(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_sandbox(s, "yolo")
        assert "expected on|off|toggle" in result.output


# ---------------------------------------------------------------------------
# /plugin
# ---------------------------------------------------------------------------


def test_plugin_bare_prints_omc_hint(tmp_path: Path) -> None:
    s = _new_session(tmp_path)
    result = _cmd_plugin(s, "")
    assert "omc plugin install" in result.output


def test_plugins_alias_resolves() -> None:
    spec = command_spec("plugins")
    assert spec is not None
    assert spec.name == "plugin"


# ---------------------------------------------------------------------------
# /reload-plugins
# ---------------------------------------------------------------------------


def test_reload_plugins_returns_summary(tmp_path: Path) -> None:
    s = _new_session(tmp_path)
    s._policy_hooks_cache = ("sentinel",)  # type: ignore[attr-defined]
    result = _cmd_reload_plugins(s, "")
    # Cache was dropped.
    assert getattr(s, "_policy_hooks_cache") is None
    assert "user_commands=" in result.output
    assert "policy_cache=dropped" in result.output


# ---------------------------------------------------------------------------
# /release-notes
# ---------------------------------------------------------------------------


def test_release_notes_falls_back_to_version_when_no_changelog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no CHANGELOG.md is bundled, the command shouldn't crash —
    it prints the version + a pointer to GitHub releases."""
    s = _new_session(tmp_path)
    # Force the package-root lookup to a directory we know lacks
    # CHANGELOG.md (the tmp_path).
    with patch(
        "importlib.resources.files",
        return_value=tmp_path / "fake-pkg" / "src" / "lyra_cli",
    ):
        result = _cmd_release_notes(s, "")
    # Output must include either the version line or a pointer.
    assert "lyra v" in result.output or "github" in result.output.lower()


# ---------------------------------------------------------------------------
# /login (alias of /auth) and /logout
# ---------------------------------------------------------------------------


def test_login_alias_resolves_to_auth() -> None:
    spec = command_spec("login")
    assert spec is not None
    assert spec.name == "auth"


def test_logout_revokes_each_stored_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``/logout`` walks list_providers() and revokes each entry."""
    revoked: list[str] = []

    monkeypatch.setattr(
        "lyra_core.auth.store.list_providers",
        lambda: ["openai", "anthropic"],
    )
    monkeypatch.setattr(
        "lyra_core.auth.store.revoke",
        lambda provider: revoked.append(provider),
    )
    s = _new_session(tmp_path)
    result = _cmd_logout(s, "")
    assert revoked == ["openai", "anthropic"]
    assert "cleared" in result.output.lower()
    assert "openai" in result.output and "anthropic" in result.output


def test_logout_handles_no_stored_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no providers are stored, output should explain that —
    not silently emit a misleading "cleared 0 providers" line."""
    monkeypatch.setattr(
        "lyra_core.auth.store.list_providers", lambda: []
    )
    s = _new_session(tmp_path)
    result = _cmd_logout(s, "")
    assert "no stored credentials" in result.output.lower()


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


def test_all_tier3_specs_registered() -> None:
    expected = {
        "pr-comments", "schedule", "sandbox", "plugin",
        "reload-plugins", "release-notes", "logout",
    }
    actual = {s.name for s in COMMAND_REGISTRY}
    missing = expected - actual
    assert not missing, f"missing CommandSpecs: {missing}"
