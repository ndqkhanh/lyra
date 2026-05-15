"""Tests for interactive/live_progress.py — nyan bar and TurnProgressHeader."""
from __future__ import annotations

import pytest

from lyra_cli.interactive.live_progress import (
    TurnProgressHeader,
    make_turn_phases,
    nyan_bar,
)


# ---------------------------------------------------------------------------
# nyan_bar
# ---------------------------------------------------------------------------


def test_nyan_bar_width():
    bar = nyan_bar(width=4, tick=0)
    # Each character is one span in the Rich Text
    assert len(bar._spans) == 4


def test_nyan_bar_content():
    bar = nyan_bar(width=3, tick=0)
    assert bar.plain == "━━━"


def test_nyan_bar_tick_rotates_colours():
    bar0 = nyan_bar(width=1, tick=0)
    bar1 = nyan_bar(width=1, tick=1)
    # Same character, different colour → different span styles
    style0 = bar0._spans[0].style
    style1 = bar1._spans[0].style
    assert style0 != style1


def test_nyan_bar_wraps_palette():
    from lyra_cli.interactive.live_progress import _NYAN_PALETTE
    n = len(_NYAN_PALETTE)
    bar_a = nyan_bar(width=1, tick=0)
    bar_b = nyan_bar(width=1, tick=n)
    # After a full palette cycle the colour should repeat
    assert bar_a._spans[0].style == bar_b._spans[0].style


def test_nyan_bar_zero_width():
    bar = nyan_bar(width=0, tick=0)
    assert bar.plain == ""


# ---------------------------------------------------------------------------
# make_turn_phases
# ---------------------------------------------------------------------------


def test_make_turn_phases_empty():
    assert make_turn_phases() == []


def test_make_turn_phases_skills_only():
    phases = make_turn_phases(skills=True)
    assert len(phases) == 1
    label, state = phases[0]
    assert "skill" in label.lower()
    assert state == "done"


def test_make_turn_phases_memory_only():
    phases = make_turn_phases(memory=True)
    assert len(phases) == 1
    label, state = phases[0]
    assert "memory" in label.lower()
    assert state == "done"


def test_make_turn_phases_both():
    phases = make_turn_phases(skills=True, memory=True)
    assert len(phases) == 2
    states = [s for _, s in phases]
    assert all(s == "done" for s in states)


def test_make_turn_phases_extra():
    phases = make_turn_phases(extra=[("Custom step", "running")])
    assert len(phases) == 1
    assert phases[0] == ("Custom step", "running")


def test_make_turn_phases_combined():
    phases = make_turn_phases(skills=True, extra=[("Tool call", "error")])
    assert len(phases) == 2


# ---------------------------------------------------------------------------
# TurnProgressHeader
# ---------------------------------------------------------------------------


def test_header_renders_verb():
    header = TurnProgressHeader([], tick=0, elapsed=5.0, verb="Planning")
    text = header.render()
    assert "Planning" in text.plain


def test_header_renders_elapsed():
    header = TurnProgressHeader([], tick=0, elapsed=7.0)
    text = header.render()
    assert "7s" in text.plain


def test_header_renders_nyan_bar():
    header = TurnProgressHeader([], tick=0, elapsed=0.0, nyan_width=3)
    text = header.render()
    assert "━━━" in text.plain


def test_header_renders_done_phase():
    phases = [("Skills loaded", "done")]
    header = TurnProgressHeader(phases, tick=0, elapsed=0.0, streaming=False)
    text = header.render()
    assert "✓" in text.plain
    assert "Skills loaded" in text.plain


def test_header_renders_running_phase():
    phases = [("Custom", "running")]
    header = TurnProgressHeader(phases, tick=0, elapsed=0.0, streaming=False)
    text = header.render()
    assert "◼" in text.plain


def test_header_renders_error_phase():
    phases = [("Broken", "error")]
    header = TurnProgressHeader(phases, tick=0, elapsed=0.0, streaming=False)
    text = header.render()
    assert "✗" in text.plain


def test_header_streaming_adds_streaming_phase():
    header = TurnProgressHeader([], tick=0, elapsed=0.0, streaming=True)
    text = header.render()
    assert "Streaming reply" in text.plain
    assert "◼" in text.plain  # running glyph


def test_header_no_streaming_no_streaming_phase():
    header = TurnProgressHeader([], tick=0, elapsed=0.0, streaming=False)
    text = header.render()
    assert "Streaming" not in text.plain


def test_header_first_phase_uses_first_indent():
    from lyra_cli.interactive.live_progress import _INDENT_FIRST
    phases = [("Phase one", "done"), ("Phase two", "done")]
    header = TurnProgressHeader(phases, tick=0, elapsed=0.0, streaming=False)
    text = header.render().plain
    # The first-phase indent should appear once
    assert _INDENT_FIRST in text


def test_header_rich_protocol():
    """TurnProgressHeader implements __rich__ so Rich can render it directly."""
    header = TurnProgressHeader([], tick=0, elapsed=1.0)
    assert hasattr(header, "__rich__")
    result = header.__rich__()
    assert result is not None


def test_header_tick_increments_nyan():
    h0 = TurnProgressHeader([], tick=0, elapsed=0.0, nyan_width=1)
    h1 = TurnProgressHeader([], tick=1, elapsed=0.0, nyan_width=1)
    t0 = h0.render()
    t1 = h1.render()
    # Same character, different span colour
    assert t0._spans[0].style != t1._spans[0].style


def test_header_multiple_phases_order():
    phases = [("A", "done"), ("B", "running"), ("C", "pending")]
    header = TurnProgressHeader(phases, tick=0, elapsed=0.0, streaming=False)
    text = header.render().plain
    assert text.index("A") < text.index("B") < text.index("C")
