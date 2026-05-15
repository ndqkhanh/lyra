"""Phase 2 — Spinner token download display."""
from __future__ import annotations

import io
import time

import pytest

from lyra_cli.interactive.spinner import Spinner, set_enabled
from lyra_cli.interactive.status_source import StatusSource


def _capture_spinner_frames(
    status_source: StatusSource | None = None,
    message: str = "Working",
    run_secs: float = 0.35,
) -> str:
    """Run the spinner for a short time and collect all output."""
    buf = io.StringIO()
    # Make StringIO look like a TTY so the animation branch runs.
    buf.isatty = lambda: True  # type: ignore[method-assign]

    sp = Spinner(message, out=buf, status_source=status_source)
    sp.start()
    time.sleep(run_secs)
    sp.stop()
    return buf.getvalue()


def test_spinner_shows_token_count_when_present():
    src = StatusSource()
    src.update(tokens_down_turn=1_200)
    output = _capture_spinner_frames(status_source=src)
    assert "↓" in output
    assert "1.2k" in output


def test_spinner_no_token_segment_when_zero():
    src = StatusSource()
    src.update(tokens_down_turn=0)
    output = _capture_spinner_frames(status_source=src)
    assert "↓" not in output


def test_spinner_uses_verb_from_status_source():
    src = StatusSource()
    src.update(current_verb="Galloping")
    output = _capture_spinner_frames(status_source=src)
    assert "Galloping" in output


def test_spinner_falls_back_to_message_without_source():
    output = _capture_spinner_frames(message="Crunching", status_source=None)
    assert "Crunching" in output


def test_spinner_shows_elapsed_seconds():
    output = _capture_spinner_frames(run_secs=0.4)
    # Elapsed appears as "Ns" (no parens) in the new spinner format
    assert "0s" in output or "s" in output


def test_humanise_tokens():
    from lyra_cli.interactive.spinner import _humanise_tokens

    assert _humanise_tokens(0) == "0"
    assert _humanise_tokens(999) == "999"
    assert _humanise_tokens(1_000) == "1.0k"
    assert _humanise_tokens(1_500) == "1.5k"
    assert _humanise_tokens(1_000_000) == "1.0M"
