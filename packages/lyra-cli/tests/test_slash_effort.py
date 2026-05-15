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
    # Every Claude-Code-parity level appears in the rendering:
    for level in ("low", "medium", "high", "xhigh", "max"):
        assert level in text


def test_picker_arrow_keys_cycle() -> None:
    """Five-level taxonomy: low → medium → high → xhigh → max → low."""
    picker = EffortPicker(initial="low")
    picker.down()
    assert picker.value == "medium"
    picker.down()
    assert picker.value == "high"
    picker.down()
    assert picker.value == "xhigh"
    picker.down()
    assert picker.value == "max"
    # Wrap forward from max:
    picker.down()
    assert picker.value == "low"
    # Wrap backward from low:
    picker.up()
    assert picker.value == "max"


def test_picker_horizontal_aliases_match_vertical() -> None:
    """``left``/``right`` are aliases for ``up``/``down`` so the
    horizontal slider and any legacy vertical bindings stay coherent."""
    a = EffortPicker(initial="medium")
    b = EffortPicker(initial="medium")
    a.down(); a.down()
    b.right(); b.right()
    assert a.value == b.value == "xhigh"
    a.up()
    b.left()
    assert a.value == b.value == "high"


def test_picker_confirm_returns_value() -> None:
    picker = EffortPicker(initial="high")
    picker.down()
    assert picker.confirm() == "xhigh"


def test_picker_render_slider_lines_marks_cursor() -> None:
    """``render_slider_lines`` returns the four-line Claude-Code layout
    with the ▲ marker on the cursor's column."""
    picker = EffortPicker(initial="xhigh")
    axis, track, levels, hint = picker.render_slider_lines(width=50)
    assert "Speed" in axis and "Intelligence" in axis
    assert "▲" in track
    # Marker column should sit above the active level name.
    marker_col = track.index("▲")
    # The active level name spans this column (centred):
    assert "xhigh" in levels
    xhigh_start = levels.index("xhigh")
    xhigh_end = xhigh_start + len("xhigh")
    assert xhigh_start <= marker_col < xhigh_end + 1, (
        f"marker col {marker_col} not aligned with xhigh span "
        f"[{xhigh_start},{xhigh_end}); levels={levels!r}"
    )
    assert "←/→" in hint and "Enter" in hint and "Esc" in hint


# ---- /effort slash sets env var --------------------------------------

def test_slash_effort_sets_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HARNESS_REASONING_EFFORT", raising=False)
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("/effort high")
    assert os.environ.get("HARNESS_REASONING_EFFORT") == "high"


# ---- max-tokens mapping ----------------------------------------------

def test_effort_to_max_completion_tokens_monotonic() -> None:
    """Higher effort levels must request strictly more max tokens
    across the full five-level Claude-Code-parity taxonomy."""
    low = effort_to_max_completion_tokens("low")
    med = effort_to_max_completion_tokens("medium")
    high = effort_to_max_completion_tokens("high")
    xhigh = effort_to_max_completion_tokens("xhigh")
    mx = effort_to_max_completion_tokens("max")
    assert low < med < high < xhigh < mx
