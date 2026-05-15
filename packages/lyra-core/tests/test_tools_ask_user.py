"""Tests for ``lyra_core.tools.ask_user`` — AskUserQuestion tool."""
from __future__ import annotations

import json

import pytest

from lyra_core.tools.ask_user import (
    AskUserPrompt,
    AskUserQuestionTool,
    _AskUserArgs,
)
from harness_core.tools import ToolError


def _build_tool(picks):
    """Build a tool with a fake prompter that returns ``picks``."""
    return AskUserQuestionTool(prompter=lambda _prompt: picks)


def _make_args(**overrides):
    base = {
        "question": "Pick a model",
        "options": ["sonnet", "opus", "haiku"],
        "multi_select": False,
    }
    base.update(overrides)
    return _AskUserArgs(**base)


# ---------------------------------------------------------------------------
# happy-path single-select
# ---------------------------------------------------------------------------


def test_single_select_returns_chosen_option() -> None:
    tool = _build_tool([2])
    out = tool.run(_make_args())
    parsed = json.loads(out)
    assert parsed == {"cancelled": False, "selected": ["opus"], "index": [2]}


def test_multi_select_returns_all_picks() -> None:
    tool = _build_tool([1, 3])
    out = tool.run(_make_args(multi_select=True))
    parsed = json.loads(out)
    assert parsed == {
        "cancelled": False,
        "selected": ["sonnet", "haiku"],
        "index": [1, 3],
    }


# ---------------------------------------------------------------------------
# cancellation paths
# ---------------------------------------------------------------------------


def test_empty_pick_marks_cancelled() -> None:
    tool = _build_tool([])
    out = tool.run(_make_args())
    parsed = json.loads(out)
    assert parsed == {"cancelled": True, "selected": [], "index": []}


def test_out_of_range_index_treated_as_cancel() -> None:
    # Asking for index 99 against a 3-option list should not crash —
    # it should sanitize and report cancellation.
    tool = _build_tool([99])
    out = tool.run(_make_args())
    parsed = json.loads(out)
    assert parsed["cancelled"] is True


# ---------------------------------------------------------------------------
# sanitization / safety
# ---------------------------------------------------------------------------


def test_duplicate_options_raise() -> None:
    tool = _build_tool([1])
    args = _AskUserArgs(
        question="?", options=["a", "a", "b"], multi_select=False
    )
    with pytest.raises(ToolError):
        tool.run(args)


def test_single_select_takes_first_when_multiple_provided() -> None:
    # multi_select=False but the prompter handed back two indices —
    # we should silently keep the first to match the contract.
    tool = _build_tool([2, 3])
    out = tool.run(_make_args(multi_select=False))
    parsed = json.loads(out)
    assert parsed == {"cancelled": False, "selected": ["opus"], "index": [2]}


def test_duplicate_indices_deduped() -> None:
    tool = _build_tool([1, 1, 2])
    out = tool.run(_make_args(multi_select=True))
    parsed = json.loads(out)
    assert parsed["index"] == [1, 2]


# ---------------------------------------------------------------------------
# tool surface
# ---------------------------------------------------------------------------


def test_tool_metadata() -> None:
    tool = AskUserQuestionTool()
    assert tool.name == "AskUserQuestion"
    assert tool.risk == "medium"
    assert tool.writes is False


def test_set_prompter_swaps_at_runtime() -> None:
    tool = AskUserQuestionTool()
    tool.set_prompter(lambda _p: [1])
    out = tool.run(_make_args())
    parsed = json.loads(out)
    assert parsed["index"] == [1]


def test_args_validation_rejects_too_few_options() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _AskUserArgs(
            question="?", options=["only one"], multi_select=False
        )


def test_args_validation_rejects_too_many_options() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _AskUserArgs(
            question="?",
            options=[f"opt{i}" for i in range(11)],
            multi_select=False,
        )


def test_prompter_receives_structured_object() -> None:
    """The prompter callback gets an :class:`AskUserPrompt` — not a dict."""
    captured = {}

    def fake(prompt: AskUserPrompt):
        captured["prompt"] = prompt
        return [1]

    tool = AskUserQuestionTool(prompter=fake)
    tool.run(_make_args(multi_select=True))

    p: AskUserPrompt = captured["prompt"]
    assert p.question == "Pick a model"
    assert p.options == ("sonnet", "opus", "haiku")
    assert p.multi_select is True
