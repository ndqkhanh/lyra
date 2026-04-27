"""Phase 0 — RED for the threaded Braille spinner.

claw-code defines a beautiful Braille spinner but its REPL only calls
``tick()`` *once* before blocking on the LLM call — so in practice the
animation never advances during the wait. We fix that by making the
spinner self-animate in a thread.

Contract (plan Phase 6, cc-spinner-threaded):

- ``ThreadedSpinner`` lives at ``lyra_cli.interactive.spinner``.
- ``spinner.start(label)`` launches a daemon thread that writes
  progressive frames to a provided stream.
- ``spinner.stop()`` stops the thread, clears the line, and (unless
  ``stop(final=...)`` is set) leaves no visible residue.
- Frames cycle through 10 Braille characters: ``⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏``.
- Running for ~250ms must produce at least 3 distinct frames in the
  stream (cap refresh around 10-12Hz so it's visible but cheap).
"""
from __future__ import annotations

import io
import re
import time

import pytest


def _import_spinner():
    try:
        from lyra_cli.interactive.spinner import ThreadedSpinner
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_cli.interactive.spinner.ThreadedSpinner must exist ({exc})")
    return ThreadedSpinner


_BRAILLE = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def test_frames_advance_over_time():
    ThreadedSpinner = _import_spinner()
    buf = io.StringIO()
    sp = ThreadedSpinner(stream=buf)
    sp.start("thinking")
    time.sleep(0.35)
    sp.stop()

    text = buf.getvalue()
    distinct = {ch for ch in text if ch in _BRAILLE}
    assert len(distinct) >= 3, (
        f"threaded spinner must advance through multiple Braille frames; saw {distinct!r}"
    )


def test_stop_clears_line():
    ThreadedSpinner = _import_spinner()
    buf = io.StringIO()
    sp = ThreadedSpinner(stream=buf)
    sp.start("thinking")
    time.sleep(0.1)
    sp.stop()
    # After stop() the last visible state should NOT contain a stale frame.
    final = buf.getvalue()
    # We emit \r then spaces to clear; accept an ANSI clear-line escape too.
    assert ("\r" in final) or ("\x1b[2K" in final), (
        "stop() must rewind the line; no \\r or ANSI clear detected"
    )


def test_stop_with_final_leaves_completion_glyph():
    ThreadedSpinner = _import_spinner()
    buf = io.StringIO()
    sp = ThreadedSpinner(stream=buf)
    sp.start("thinking")
    time.sleep(0.05)
    sp.stop(final="✔ done")
    text = buf.getvalue()
    assert "✔ done" in text


def test_spinner_tolerates_double_stop():
    ThreadedSpinner = _import_spinner()
    sp = ThreadedSpinner(stream=io.StringIO())
    sp.start("thinking")
    sp.stop()
    sp.stop()  # must be safe


def test_label_visible_in_stream():
    ThreadedSpinner = _import_spinner()
    buf = io.StringIO()
    sp = ThreadedSpinner(stream=buf)
    sp.start("compiling plans")
    time.sleep(0.12)
    sp.stop()
    # Strip ANSI for the assertion.
    stripped = re.sub(r"\x1b\[[0-9;]*m", "", buf.getvalue())
    assert "compiling plans" in stripped
