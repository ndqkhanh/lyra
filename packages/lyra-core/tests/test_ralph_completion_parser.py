"""L312-2 — completion-signal parser tests."""
from __future__ import annotations

from lyra_core.ralph.completion import parse_completion


def test_promise_complete_canonical():
    sig = parse_completion("All done.\n<promise>COMPLETE</promise>\n")
    assert sig.found
    assert sig.variant == "promise"
    assert sig.span[1] > sig.span[0]


def test_promise_complete_whitespace_tolerated():
    sig = parse_completion("<promise> COMPLETE </promise>")
    assert sig.found
    assert sig.variant == "promise"


def test_promise_complete_case_insensitive():
    sig = parse_completion("<Promise>complete</Promise>")
    assert sig.found
    assert sig.variant == "promise"


def test_exit_signal_token_frankbria():
    sig = parse_completion("Phase wrap-up.\nEXIT_SIGNAL: true")
    assert sig.found
    assert sig.variant == "exit_signal"


def test_promise_takes_priority_over_exit_signal():
    sig = parse_completion(
        "EXIT_SIGNAL: true\n<promise>COMPLETE</promise>"
    )
    assert sig.found
    assert sig.variant == "promise"


def test_no_signal_returns_unfound():
    sig = parse_completion("Phase complete and tests pass!")
    assert not sig.found
    assert sig.variant == ""


def test_empty_text_returns_unfound():
    assert not parse_completion("").found
    assert not parse_completion(None or "").found
