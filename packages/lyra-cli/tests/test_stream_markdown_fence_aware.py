"""Phase 0 — RED for the fence-aware streaming markdown buffer.

Ported from claw-code's ``MarkdownStreamState`` at
``rust/crates/rusty-claude-cli/src/render.rs``.

Contract (plan Phase 6, cc-stream-buffer):

- ``MarkdownStreamState`` lives at ``lyra_cli.interactive.stream``.
- ``state.push(delta: str) -> Optional[str]`` appends incoming text and
  returns the portion that is safe to flush (outside any unclosed
  fenced code block, aligned on a newline). Returns ``None`` when
  nothing is safe to flush yet.
- ``state.flush() -> str`` always returns whatever is buffered,
  regardless of boundaries (used when the stream ends).
- Splitting inside an open ``` fence must NEVER happen.
"""
from __future__ import annotations

import pytest


def _import_stream():
    try:
        from lyra_cli.interactive.stream import MarkdownStreamState
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_cli.interactive.stream.MarkdownStreamState must exist ({exc})")
    return MarkdownStreamState


def test_push_plain_text_flushes_at_newline():
    MarkdownStreamState = _import_stream()
    s = MarkdownStreamState()
    assert s.push("hello") in (None, "")  # no newline yet -> hold back
    ready = s.push(" world\nnext")
    assert ready is not None
    assert "hello world" in ready
    # "next" (no newline) is still pending.


def test_push_never_splits_inside_an_open_fence():
    MarkdownStreamState = _import_stream()
    s = MarkdownStreamState()
    s.push("Here is code:\n")
    s.push("```python\n")
    mid = s.push("def hi():\n")
    # Inside an unclosed fence we MUST hold everything back.
    assert mid in (None, "")


def test_push_flushes_once_fence_closes():
    MarkdownStreamState = _import_stream()
    s = MarkdownStreamState()
    s.push("```python\n")
    s.push("x = 1\n")
    out = s.push("```\nafter")
    assert out is not None
    # The closing fence (and everything up to it) is now safe.
    assert "```" in out
    assert "x = 1" in out


def test_flush_returns_pending_text():
    MarkdownStreamState = _import_stream()
    s = MarkdownStreamState()
    s.push("no-newline tail")
    rest = s.flush()
    assert "no-newline tail" in rest


def test_flush_is_empty_after_clean_stream():
    MarkdownStreamState = _import_stream()
    s = MarkdownStreamState()
    s.push("hello\n")
    # a push ending with \n should have produced output already
    leftover = s.flush()
    assert leftover == ""


def test_multiple_consecutive_fences_roundtrip():
    MarkdownStreamState = _import_stream()
    s = MarkdownStreamState()
    parts = [
        "Before code.\n",
        "```\n", "A\n", "```\n",
        "Between.\n",
        "```python\n", "b=2\n", "```\n",
        "After.\n",
    ]
    collected = []
    for p in parts:
        out = s.push(p)
        if out:
            collected.append(out)
    collected.append(s.flush())
    combined = "".join(collected)
    assert "A" in combined
    assert "b=2" in combined
    assert "Before code." in combined
    assert "After." in combined
