"""Tests for the Rich-aware ``AskUserQuestion`` prompter."""
from __future__ import annotations

import io
import json

import pytest
from rich.console import Console

from lyra_cli.interactive.ask_user_prompter import _parse_picks, make_prompter
from lyra_core.tools.ask_user import AskUserPrompt, AskUserQuestionTool, _AskUserArgs


def _silent_console() -> Console:
    """Console writing to an in-memory buffer — no terminal noise during tests."""
    return Console(file=io.StringIO(), force_terminal=False, width=80)


# ---------------------------------------------------------------------------
# _parse_picks — pure parsing, no I/O
# ---------------------------------------------------------------------------


class TestParsePicks:
    def test_single_index(self) -> None:
        assert _parse_picks("2", n_options=3, multi=False) == [2]

    def test_multi_csv(self) -> None:
        assert _parse_picks("1,3", n_options=3, multi=True) == [1, 3]

    def test_whitespace_tolerated(self) -> None:
        assert _parse_picks("  1, 2 ,3 ", n_options=3, multi=True) == [1, 2, 3]

    def test_out_of_range_dropped(self) -> None:
        assert _parse_picks("1,99,2", n_options=3, multi=True) == [1, 2]

    def test_non_numeric_silently_skipped(self) -> None:
        # ``"1, , 3"`` shouldn't cancel the picker — only an empty
        # *result* counts as cancel. Bad tokens just disappear.
        assert _parse_picks("1, , 3", n_options=3, multi=True) == [1, 3]

    def test_single_select_caps_at_first(self) -> None:
        assert _parse_picks("2,3", n_options=3, multi=False) == [2]

    def test_empty_returns_empty(self) -> None:
        assert _parse_picks("", n_options=3, multi=False) == []


# ---------------------------------------------------------------------------
# make_prompter — closes over a console, reads stdin via input()
# ---------------------------------------------------------------------------


def test_make_prompter_returns_callable() -> None:
    prompter = make_prompter(_silent_console())
    assert callable(prompter)


def test_prompter_renders_question_to_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The question + options panel must hit the bound console.

    We sniff the console's underlying buffer instead of capturing
    stdout because that's where Rich actually writes.
    """
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=80)
    monkeypatch.setattr("builtins.input", lambda _prompt: "1")
    prompter = make_prompter(console)
    prompter(
        AskUserPrompt(
            question="Pick a model",
            options=("sonnet", "opus", "haiku"),
            multi_select=False,
        )
    )
    output = buf.getvalue()
    assert "Pick a model" in output
    assert "sonnet" in output
    assert "haiku" in output


def test_prompter_returns_picked_indices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    prompter = make_prompter(_silent_console())
    picks = prompter(
        AskUserPrompt(
            question="?",
            options=("a", "b", "c"),
            multi_select=False,
        )
    )
    assert list(picks) == [2]


def test_prompter_handles_eof_as_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ctrl-D mid-prompt should cancel cleanly — not crash the tool loop."""

    def raise_eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    prompter = make_prompter(_silent_console())
    picks = prompter(
        AskUserPrompt(
            question="?",
            options=("a", "b"),
            multi_select=False,
        )
    )
    assert list(picks) == []


def test_prompter_handles_ctrl_c_as_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_int(_prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", raise_int)
    prompter = make_prompter(_silent_console())
    picks = prompter(
        AskUserPrompt(
            question="?",
            options=("a", "b"),
            multi_select=False,
        )
    )
    assert list(picks) == []


# ---------------------------------------------------------------------------
# end-to-end: tool wired with the Rich prompter returns a JSON answer
# ---------------------------------------------------------------------------


def test_tool_with_rich_prompter_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    prompter = make_prompter(_silent_console())
    tool = AskUserQuestionTool(prompter=prompter)

    args = _AskUserArgs(
        question="What's your favourite editor?",
        options=["vim", "emacs", "vscode"],
        multi_select=False,
    )
    out = tool.run(args)
    parsed = json.loads(out)
    assert parsed == {"cancelled": False, "selected": ["emacs"], "index": [2]}
