"""Contract tests for :mod:`lyra_cli.interactive.effort_app`.

The interactive ``/effort`` picker is the only legacy interactive module
without tests (v3.14 audit). This file locks down the pure render
helper plus the ``run_effort_picker`` exit paths before the eventual
decommission of ``interactive/``.

The ``Application.run()`` event loop requires a real TTY; tests patch
it out and assert on the prompt_toolkit ``Application``'s observable
return-value contract instead.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from lyra_cli.interactive.effort import EffortPicker
from lyra_cli.interactive.effort_app import _build_fragments, run_effort_picker


# ---------------------------------------------------------------------
# _build_fragments — pure renderer
# ---------------------------------------------------------------------


def test_build_fragments_contains_header_and_hint() -> None:
    picker = EffortPicker(initial="medium")
    out = _build_fragments(picker, width=50)
    # FormattedText tuples are (style, text[, mouse_handler]) — slice
    # off any optional 3rd element so the assertion works regardless of
    # prompt_toolkit version.
    plain = "".join(fragment[1] for fragment in out)
    assert "Effort" in plain
    # Hint lives on its own row and uses the dedicated style class.
    assert any("class:hint" in fragment[0] for fragment in out)


def test_build_fragments_marks_active_level() -> None:
    picker = EffortPicker(initial="high")
    out = _build_fragments(picker, width=50)
    active_runs = [
        fragment[1] for fragment in out if "class:level.active" in fragment[0]
    ]
    assert active_runs, "active level span must be tagged class:level.active"
    assert "high" in "".join(active_runs)


def test_build_fragments_highlights_marker_on_track() -> None:
    picker = EffortPicker(initial="medium")
    out = _build_fragments(picker, width=50)
    markers = [fragment[1] for fragment in out if "class:marker" in fragment[0]]
    assert markers
    assert markers[0] == "▲"


def test_build_fragments_includes_axis_row() -> None:
    picker = EffortPicker(initial="low")
    out = _build_fragments(picker, width=40)
    axis_rows = [fragment[1] for fragment in out if "class:axis" in fragment[0]]
    assert axis_rows
    # Axis line is non-empty (some combination of arrows + tick marks).
    assert any(row.strip() for row in axis_rows)


def test_build_fragments_handles_extreme_widths() -> None:
    """Narrow widths must not crash or produce empty output."""
    picker = EffortPicker(initial="medium")
    for width in (10, 30, 200):
        out = _build_fragments(picker, width=width)
        plain = "".join(fragment[1] for fragment in out)
        assert "Effort" in plain


# ---------------------------------------------------------------------
# run_effort_picker — exit paths
# ---------------------------------------------------------------------


def test_run_effort_picker_returns_picked_value() -> None:
    """When the inner Application.run() returns a level, it propagates."""
    with patch("prompt_toolkit.application.Application.run", return_value="high"):
        assert run_effort_picker(initial="medium") == "high"


def test_run_effort_picker_returns_none_on_keyboard_interrupt() -> None:
    """Ctrl-C during the picker must bubble up as a clean None."""
    with patch(
        "prompt_toolkit.application.Application.run",
        side_effect=KeyboardInterrupt(),
    ):
        assert run_effort_picker(initial="medium") is None


def test_run_effort_picker_returns_none_on_eof_error() -> None:
    """Piped stdin closes → EOFError → graceful None, not a crash."""
    with patch(
        "prompt_toolkit.application.Application.run",
        side_effect=EOFError(),
    ):
        assert run_effort_picker(initial="medium") is None


def test_run_effort_picker_returns_none_for_non_string_result() -> None:
    """Defensive: a non-string return from Application.run normalises to None."""
    with patch("prompt_toolkit.application.Application.run", return_value=42):
        assert run_effort_picker(initial="medium") is None


@pytest.mark.parametrize("initial", ["low", "medium", "high"])
def test_run_effort_picker_propagates_each_level(initial: str) -> None:
    """Every supported level round-trips through the result handler."""
    with patch("prompt_toolkit.application.Application.run", return_value=initial):
        assert run_effort_picker(initial=initial) == initial
