"""Wave-C Task 9: ``/effort`` arrow-key slider + max-tokens mapping.

The TTY layer is exercised by hand. Tests target the *pure* picker
logic and the slash dispatcher's side-effects (env var, session
state) so the slider stays unit-testable across CI.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from lyra_cli.interactive.effort import (
    EffortPicker,
    effort_to_max_completion_tokens,
)
from lyra_cli.interactive.session import InteractiveSession


# ---- picker -----------------------------------------------------------

def test_picker_renders_with_cursor_at_initial_value() -> None:
    picker = EffortPicker(initial="medium")
    text = picker.render()
    # Cursor marker on the active option:
    assert "▸ medium" in text or "> medium" in text
    # Every option appears in the rendering:
    for level in ("low", "medium", "high", "max"):
        assert level in text


def test_picker_arrow_keys_cycle() -> None:
    picker = EffortPicker(initial="low")
    picker.down()
    assert picker.value == "medium"
    picker.down()
    assert picker.value == "high"
    picker.up()
    assert picker.value == "medium"
    # Cycles past the ends:
    picker.up()
    picker.up()
    assert picker.value == "max"  # wrapped


def test_picker_confirm_returns_value() -> None:
    picker = EffortPicker(initial="high")
    picker.down()
    assert picker.confirm() == "max"


# ---- /effort slash sets env var --------------------------------------

def test_slash_effort_sets_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HARNESS_REASONING_EFFORT", raising=False)
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("/effort high")
    assert os.environ.get("HARNESS_REASONING_EFFORT") == "high"


# ---- max-tokens mapping ----------------------------------------------

def test_effort_to_max_completion_tokens_monotonic() -> None:
    """Higher effort levels must request strictly more max tokens."""
    low = effort_to_max_completion_tokens("low")
    med = effort_to_max_completion_tokens("medium")
    high = effort_to_max_completion_tokens("high")
    mx = effort_to_max_completion_tokens("max")
    assert low < med < high < mx
