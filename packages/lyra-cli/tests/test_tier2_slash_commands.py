"""Tests for the v3.11 Tier-2 slash commands.

Covers: /security-review, /feedback (alias /bug), /statusline, /color,
/fast, /focus, /tui. These are pure UX-state toggles — most tests are
input/output checks rather than wiring tests, since the toggles
are read by the renderer downstream.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import (
    COMMAND_REGISTRY,
    InteractiveSession,
    _cmd_color,
    _cmd_fast,
    _cmd_feedback,
    _cmd_focus,
    _cmd_security_review,
    _cmd_statusline,
    _cmd_tui,
    command_spec,
)


def _new_session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="m", mode="agent")


# ---------------------------------------------------------------------------
# /security-review — wraps /review with security framing
# ---------------------------------------------------------------------------


def test_security_review_dispatches_review_with_security_focus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = _new_session(tmp_path)
    captured = {}

    def fake_dispatch(line):
        captured["line"] = line
        from lyra_cli.interactive.session import CommandResult
        return CommandResult(output="(stub)")

    monkeypatch.setattr(s, "dispatch", fake_dispatch)
    _cmd_security_review(s, "src/auth")
    assert captured["line"].startswith("/review src/auth")
    assert "security" in captured["line"].lower()
    assert "OWASP" in captured["line"]


def test_security_review_defaults_to_head() -> None:
    """Missing target ⇒ default to ``HEAD`` so calling bare works."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        s = InteractiveSession(repo_root=Path(td), model="m", mode="agent")
        captured = {}
        s.dispatch = lambda line: (captured.setdefault("line", line), None)[1]
        _cmd_security_review(s, "")
        assert "HEAD" in captured["line"]


# ---------------------------------------------------------------------------
# /feedback (alias /bug)
# ---------------------------------------------------------------------------


class TestCmdFeedback:
    def test_prints_issue_url(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_feedback(s, "")
        assert "github.com" in result.output
        assert "issues" in result.output

    def test_alias_bug_resolves(self) -> None:
        spec = command_spec("bug")
        assert spec is not None and spec.name == "feedback"


# ---------------------------------------------------------------------------
# /statusline
# ---------------------------------------------------------------------------


class TestCmdStatusline:
    def test_no_arg_prints_current(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_statusline(s, "")
        assert "current statusline" in result.output.lower()

    def test_set_persists_format(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_statusline(s, "<b>{repo}</b> · {model}")
        assert s.statusline_format == "<b>{repo}</b> · {model}"

    def test_default_resets(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_statusline(s, "custom")
        _cmd_statusline(s, "default")
        assert s.statusline_format is None


# ---------------------------------------------------------------------------
# /color
# ---------------------------------------------------------------------------


class TestCmdColor:
    def test_named_colour_persists(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_color(s, "purple")
        assert s.prompt_color == "purple"

    def test_default_resets(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_color(s, "purple")
        _cmd_color(s, "default")
        assert s.prompt_color is None

    def test_unknown_colour_rejected(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_color(s, "fuchsia")
        assert "unknown colour" in result.output.lower()

    def test_bare_picks_deterministically_from_session_id(
        self, tmp_path: Path
    ) -> None:
        # Same session id ⇒ same pick. Pseudo-random is fine; reproducible
        # is the contract — keeps the colour stable across resumes.
        s1 = _new_session(tmp_path)
        s2 = _new_session(tmp_path)
        s1.session_id = "test-id-stable"  # type: ignore[attr-defined]
        s2.session_id = "test-id-stable"  # type: ignore[attr-defined]
        _cmd_color(s1, "")
        _cmd_color(s2, "")
        assert s1.prompt_color == s2.prompt_color


# ---------------------------------------------------------------------------
# /fast
# ---------------------------------------------------------------------------


class TestCmdFast:
    def test_toggle_off_to_on(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_fast(s, "")
        assert s.fast_mode is True
        assert s.effort == "low"

    def test_explicit_off(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        s.fast_mode = True  # type: ignore[attr-defined]
        _cmd_fast(s, "off")
        assert s.fast_mode is False

    def test_invalid_value_rejected(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_fast(s, "yolo")
        assert "expected on|off|toggle" in result.output


# ---------------------------------------------------------------------------
# /focus
# ---------------------------------------------------------------------------


def test_focus_toggles_session_flag(tmp_path: Path) -> None:
    s = _new_session(tmp_path)
    _cmd_focus(s, "")
    assert s.focus_mode is True
    _cmd_focus(s, "off")
    assert s.focus_mode is False


# ---------------------------------------------------------------------------
# /tui
# ---------------------------------------------------------------------------


class TestCmdTui:
    def test_explicit_classic(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        _cmd_tui(s, "classic")
        assert s.tui_mode == "classic"

    def test_toggle_inverts(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        s.tui_mode = "smooth"  # type: ignore[attr-defined]
        _cmd_tui(s, "")
        assert s.tui_mode == "classic"
        _cmd_tui(s, "")
        assert s.tui_mode == "smooth"

    def test_invalid_value_rejected(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_tui(s, "wobbly")
        assert "expected one of" in result.output


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


def test_all_tier2_specs_registered() -> None:
    expected = {
        "security-review", "feedback", "statusline",
        "color", "fast", "focus", "tui",
    }
    actual = {s.name for s in COMMAND_REGISTRY}
    missing = expected - actual
    assert not missing, f"missing CommandSpecs: {missing}"
