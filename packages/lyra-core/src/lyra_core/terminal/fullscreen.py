"""Flicker-free fullscreen TUI renderer (v3.7 L37-2).

Anthropic's Claude Code announcement explicitly calls out "flicker-free
rendering": long-text updates that previously redrew the whole screen
now ship as *diff-blocks* — only the changed rows write back to the
terminal.

This module ships the contract + a deterministic in-memory renderer
that any backend (Rich `Live`, prompt_toolkit's full_screen App, raw
ANSI) can plug into. The CLI wires the production backend; tests use
the in-memory renderer to assert *which rows changed*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass(frozen=True)
class DiffBlock:
    """One contiguous range of rows whose content changed."""

    start_row: int                 # inclusive
    end_row: int                   # exclusive
    text: tuple[str, ...]          # one entry per row in [start_row, end_row)

    def __post_init__(self) -> None:
        if self.start_row < 0 or self.end_row < self.start_row:
            raise ValueError(
                f"DiffBlock invalid range: [{self.start_row}, {self.end_row})"
            )
        if len(self.text) != (self.end_row - self.start_row):
            raise ValueError(
                f"DiffBlock text length {len(self.text)} != range "
                f"{self.end_row - self.start_row}"
            )


@dataclass
class FullscreenRenderer:
    """In-memory fullscreen buffer with diff-block emission.

    The renderer keeps the *previous* frame and emits ``DiffBlock``s
    only for the rows that actually changed. Production backends call
    ``apply(blocks)`` to write changed rows; tests inspect the blocks
    directly to assert no-flicker behaviour.
    """

    rows: int
    cols: int
    _frame: list[str] = field(default_factory=list)
    _initialised: bool = False

    def __post_init__(self) -> None:
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("rows and cols must be positive")
        self._frame = [""] * self.rows

    @property
    def frame(self) -> tuple[str, ...]:
        return tuple(self._frame)

    def render(self, lines: Iterable[str]) -> list[DiffBlock]:
        """Compute diff blocks against the prior frame; update buffer."""
        new_frame = list(lines)
        # Pad / truncate to rows.
        if len(new_frame) < self.rows:
            new_frame.extend([""] * (self.rows - len(new_frame)))
        else:
            new_frame = new_frame[: self.rows]
        # Truncate per-row to cols (caller may pass long lines).
        new_frame = [_truncate(line, self.cols) for line in new_frame]
        if not self._initialised:
            self._frame = new_frame
            self._initialised = True
            # First render: every row is "new" — emit a single block
            # so the backend writes the whole frame once.
            return [DiffBlock(0, self.rows, tuple(new_frame))]
        blocks = _diff_blocks(self._frame, new_frame)
        self._frame = new_frame
        return blocks

    def apply(self, blocks: Iterable[DiffBlock]) -> None:
        """Apply caller-supplied blocks directly.

        Backends that already know what changed (e.g. an external
        renderer) can call this instead of ``render``.
        """
        for block in blocks:
            for i, text in enumerate(block.text):
                row = block.start_row + i
                if 0 <= row < self.rows:
                    self._frame[row] = _truncate(text, self.cols)
        self._initialised = True


def _truncate(text: str, cols: int) -> str:
    if len(text) <= cols:
        return text
    return text[:cols]


def _diff_blocks(old: list[str], new: list[str]) -> list[DiffBlock]:
    """Group consecutive changed rows into DiffBlocks."""
    blocks: list[DiffBlock] = []
    n = len(new)
    i = 0
    while i < n:
        if new[i] == old[i]:
            i += 1
            continue
        start = i
        while i < n and new[i] != old[i]:
            i += 1
        blocks.append(DiffBlock(
            start_row=start, end_row=i,
            text=tuple(new[start:i]),
        ))
    return blocks


__all__ = ["DiffBlock", "FullscreenRenderer"]
