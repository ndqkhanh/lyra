"""Fullscreen renderer + mouse/voice event tests (v3.7 L37-2)."""
from __future__ import annotations

import pytest

from lyra_core.terminal.events import (
    MouseButton,
    MouseEvent,
    MouseKind,
    VoiceEvent,
    VoiceKind,
)
from lyra_core.terminal.fullscreen import DiffBlock, FullscreenRenderer


# --- DiffBlock validation --------------------------------------------------


def test_diff_block_valid() -> None:
    block = DiffBlock(start_row=2, end_row=4, text=("a", "b"))
    assert block.start_row == 2
    assert block.end_row == 4


def test_diff_block_rejects_negative_start() -> None:
    with pytest.raises(ValueError):
        DiffBlock(start_row=-1, end_row=2, text=("a", "b", "c"))


def test_diff_block_rejects_text_length_mismatch() -> None:
    with pytest.raises(ValueError):
        DiffBlock(start_row=0, end_row=3, text=("a",))


# --- FullscreenRenderer ----------------------------------------------------


def test_first_render_emits_single_full_frame_block() -> None:
    r = FullscreenRenderer(rows=4, cols=20)
    blocks = r.render(["a", "b", "c", "d"])
    assert len(blocks) == 1
    assert blocks[0].start_row == 0
    assert blocks[0].end_row == 4


def test_second_render_no_change_returns_empty() -> None:
    r = FullscreenRenderer(rows=3, cols=20)
    r.render(["x", "y", "z"])
    blocks = r.render(["x", "y", "z"])
    assert blocks == []


def test_second_render_one_changed_row_emits_one_block() -> None:
    r = FullscreenRenderer(rows=4, cols=20)
    r.render(["a", "b", "c", "d"])
    blocks = r.render(["a", "B!", "c", "d"])
    assert len(blocks) == 1
    assert blocks[0].start_row == 1
    assert blocks[0].end_row == 2
    assert blocks[0].text == ("B!",)


def test_non_contiguous_changes_emit_multiple_blocks() -> None:
    r = FullscreenRenderer(rows=5, cols=20)
    r.render(["a", "b", "c", "d", "e"])
    blocks = r.render(["A!", "b", "C!", "d", "e"])
    assert len(blocks) == 2
    assert blocks[0].start_row == 0
    assert blocks[1].start_row == 2


def test_truncates_long_lines_to_cols() -> None:
    r = FullscreenRenderer(rows=2, cols=5)
    r.render(["x" * 10, "y"])
    assert r.frame[0] == "xxxxx"
    assert r.frame[1] == "y"


def test_pads_short_frame_to_rows() -> None:
    r = FullscreenRenderer(rows=4, cols=20)
    r.render(["only one line"])
    assert r.frame == ("only one line", "", "", "")


def test_apply_writes_blocks_directly() -> None:
    r = FullscreenRenderer(rows=4, cols=20)
    r.render(["a", "b", "c", "d"])
    r.apply([DiffBlock(start_row=1, end_row=3, text=("B!", "C!"))])
    assert r.frame == ("a", "B!", "C!", "d")


# --- Mouse / voice events --------------------------------------------------


def test_mouse_event_click() -> None:
    ev = MouseEvent(kind=MouseKind.CLICK, row=10, col=20)
    assert ev.button is MouseButton.LEFT
    assert ev.delta == 0


def test_mouse_event_scroll() -> None:
    ev = MouseEvent(kind=MouseKind.SCROLL, row=0, col=0,
                    button=MouseButton.NONE, delta=3)
    assert ev.kind is MouseKind.SCROLL
    assert ev.delta == 3


def test_voice_event_transcript_partial_then_final() -> None:
    partial = VoiceEvent(kind=VoiceKind.TRANSCRIPT, text="hello", final=False)
    final = VoiceEvent(kind=VoiceKind.TRANSCRIPT, text="hello world", final=True)
    assert not partial.final
    assert final.final
