"""Contract tests for ``render_context_grid`` (v1.7.3).

The grid is a single-pass, text-only renderer for the ``/context``
slash command. It turns a conversation transcript into a proportional
monospaced bar chart so the user can *see* where their token budget is
going (SOUL vs system vs user vs assistant vs tool-result).

Invariants:

- Empty transcript renders a legend + zero-total line (never crashes).
- Single message renders exactly one block whose width is proportional
  to that message's ``_tok_estimate``.
- The totals line sums every message's tokens and matches the shared
  ``_tok_estimate`` heuristic.
- Output respects a ``columns`` ceiling — no line exceeds it.
- Grid characters are drawn from ``{"█", "▓", "░", " "}`` and roles
  get distinct glyph tracks so the user can distinguish layers by
  eye without colour (colour is delegated to the Rich renderable in
  the CLI layer — the core grid stays ANSI-free for log-capture).
"""
from __future__ import annotations

import pytest

from lyra_core.context.grid import render_context_grid
from lyra_core.context.pipeline import _tok_estimate


def test_empty_conversation_renders_empty_grid_with_legend() -> None:
    out = render_context_grid([], columns=60)

    assert isinstance(out, str)
    # Must carry a legend so the user learns the glyph mapping.
    assert "legend" in out.lower()
    # Totals must appear and be zero.
    assert "total" in out.lower()
    assert "0 tokens" in out.lower() or "0 tok" in out.lower()
    # No line wider than the requested column width.
    for line in out.splitlines():
        assert len(line) <= 60


def test_single_message_renders_single_cell_proportional_to_tokens() -> None:
    msg = {"role": "user", "content": "hello " * 200}  # ~300 tok
    out = render_context_grid([msg], columns=60)

    lines = out.splitlines()
    # Find the row for the user message.
    user_rows = [l for l in lines if "user" in l.lower() and ("█" in l or "▓" in l)]
    assert user_rows, f"expected a user row with a bar; got:\n{out}"
    bar_chars = sum(user_rows[0].count(c) for c in ("█", "▓", "░"))
    assert bar_chars > 0


def test_totals_line_sums_all_messages() -> None:
    messages = [
        {"role": "system", "content": "SOUL " * 100},   # ~125 tok
        {"role": "user", "content": "hi " * 50},         # ~37 tok
        {"role": "assistant", "content": "ok " * 30},    # ~22 tok
    ]
    expected_total = sum(_tok_estimate(m["content"]) for m in messages)
    out = render_context_grid(messages, columns=60)

    assert str(expected_total) in out
    assert "total" in out.lower()


def test_wraps_to_columns_width() -> None:
    messages = [{"role": "user", "content": "x" * 8000} for _ in range(4)]
    out = render_context_grid(messages, columns=40)

    for line in out.splitlines():
        assert len(line) <= 40, f"line too wide ({len(line)}): {line!r}"


def test_distinct_roles_render_distinct_tracks() -> None:
    messages = [
        {"role": "system", "content": "soul " * 20},
        {"role": "user", "content": "hi " * 20},
        {"role": "assistant", "content": "ok " * 20},
        {"role": "tool", "content": "result " * 20},
    ]
    out = render_context_grid(messages, columns=60)

    lower = out.lower()
    assert "system" in lower
    assert "user" in lower
    assert "assistant" in lower
    assert "tool" in lower


def test_render_is_ansi_free() -> None:
    """The core renderer stays colour-free; colouring is the CLI's job."""
    messages = [{"role": "user", "content": "hello"}]
    out = render_context_grid(messages, columns=60)
    # ANSI CSI introducer: ESC[
    assert "\x1b[" not in out


def test_rejects_non_positive_columns() -> None:
    with pytest.raises(ValueError):
        render_context_grid([], columns=0)
    with pytest.raises(ValueError):
        render_context_grid([], columns=-5)
