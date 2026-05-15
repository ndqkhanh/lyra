"""Tests for v3.11 Tier-5 bundled skills.

Covers: /loop, /debug, /simplify, /batch, /claude-api. These are
small handlers that delegate to existing infrastructure (cron,
spawn, OMC) — so the tests are mostly contract checks (does the
delegation produce the expected payload?) rather than full
integration suites.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import (
    COMMAND_REGISTRY,
    InteractiveSession,
    _cmd_batch,
    _cmd_claude_api,
    _cmd_debug,
    _cmd_loop,
    _cmd_simplify,
)


def _new_session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="m", mode="agent")


# ---------------------------------------------------------------------------
# /loop — leading-token interval parser
# ---------------------------------------------------------------------------


class TestCmdLoop:
    def test_empty_args_prints_usage(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_loop(s, "")
        assert "usage" in result.output.lower()

    def test_leading_interval_token_extracted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _new_session(tmp_path)
        captured = {}

        def fake_cron(self_unused, args):
            captured["args"] = args
            from lyra_cli.interactive.session import CommandResult
            return CommandResult(output="(stub)")

        monkeypatch.setattr(
            "lyra_cli.interactive.session._cmd_cron", fake_cron
        )
        _cmd_loop(s, "5m check the deploy")
        assert captured["args"] == "add 5m check the deploy"

    def test_no_leading_interval_defaults_to_5m(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _new_session(tmp_path)
        captured = {}

        def fake_cron(self_unused, args):
            captured["args"] = args
            from lyra_cli.interactive.session import CommandResult
            return CommandResult(output="(stub)")

        monkeypatch.setattr(
            "lyra_cli.interactive.session._cmd_cron", fake_cron
        )
        _cmd_loop(s, "check the deploy every PR")
        assert captured["args"].startswith("add 5m ")
        assert "check the deploy" in captured["args"]


# ---------------------------------------------------------------------------
# /debug — pure flag toggle
# ---------------------------------------------------------------------------


class TestCmdDebug:
    def test_toggle_off_to_on(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_debug(s, "")
        assert s.debug_mode is True
        _cmd_debug(s, "")
        assert s.debug_mode is False

    def test_explicit_on(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_debug(s, "on")
        assert s.debug_mode is True

    def test_invalid_rejected(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_debug(s, "extra")
        assert "expected on|off|toggle" in result.output


# ---------------------------------------------------------------------------
# /simplify — dispatches /spawn with framing
# ---------------------------------------------------------------------------


def test_simplify_dispatches_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = _new_session(tmp_path)
    captured = {}

    def fake_dispatch(line):
        captured["line"] = line
        from lyra_cli.interactive.session import CommandResult
        return CommandResult(output="(stub)")

    monkeypatch.setattr(s, "dispatch", fake_dispatch)
    _cmd_simplify(s, "the cache module")
    assert captured["line"].startswith("/spawn")
    assert "Pass 1" in captured["line"]
    assert "Pass 2" in captured["line"]
    assert "Pass 3" in captured["line"]
    assert "the cache module" in captured["line"]


def test_simplify_default_focus_when_no_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = _new_session(tmp_path)
    captured = {}

    def fake_dispatch(line):
        captured["line"] = line
        from lyra_cli.interactive.session import CommandResult
        return CommandResult(output="(stub)")

    monkeypatch.setattr(s, "dispatch", fake_dispatch)
    _cmd_simplify(s, "")
    assert "general code-quality" in captured["line"]


# ---------------------------------------------------------------------------
# /batch — pointer to OMC
# ---------------------------------------------------------------------------


class TestCmdBatch:
    def test_no_args_prints_usage(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_batch(s, "")
        assert "usage" in result.output.lower()
        assert "omc batch" in result.output

    def test_with_args_emits_omc_command(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_batch(s, "convert callsites to async")
        assert 'omc batch "convert callsites to async"' in result.output


# ---------------------------------------------------------------------------
# /claude-api — static reference card
# ---------------------------------------------------------------------------


def test_claude_api_prints_reference(tmp_path: Path) -> None:
    s = _new_session(tmp_path)
    result = _cmd_claude_api(s, "")
    # Sanity: output mentions endpoint, auth, models, SDK install lines.
    assert "api.anthropic.com" in result.output
    assert "ANTHROPIC_API_KEY" in result.output
    assert "claude-opus" in result.output
    assert "@anthropic-ai/sdk" in result.output


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


def test_all_tier5_specs_registered() -> None:
    expected = {"loop", "debug", "simplify", "batch", "claude-api"}
    actual = {s.name for s in COMMAND_REGISTRY}
    missing = expected - actual
    assert not missing, f"missing CommandSpecs: {missing}"
