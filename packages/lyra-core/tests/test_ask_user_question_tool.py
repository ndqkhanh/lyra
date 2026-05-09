"""Contract tests for ``AskUserQuestion`` tool.

Locked surface (claw-code / opencode / hermes-agent parity):

* Returned schema: ``__tool_schema__`` carries name + description +
  parameters with ``questions`` required.
* Validation: missing id / prompt → ``ValueError``; non-list
  questions → ``TypeError``; empty list → ``ValueError``.
* Successful call returns
  ``{"cancelled": False, "answers": [...]}``.
* Cancelled callback returns ``{"cancelled": True, "answers": []}``.
* Callback receives validated questions (each a dict) and the title.
"""
from __future__ import annotations

import pytest

from lyra_core.tools import make_ask_user_question_tool


def _ok_callback(*, questions, title=None):
    return {"answers": [{"id": q["id"], "answer": "yes"} for q in questions]}


def _cancel_callback(*, questions, title=None):
    return {"cancelled": True, "answers": []}


def test_ask_user_question_schema_is_locked():
    tool = make_ask_user_question_tool(ask=_ok_callback)
    schema = getattr(tool, "__tool_schema__")
    assert schema["name"] == "AskUserQuestion"
    assert "description" in schema
    params = schema["parameters"]
    assert params["type"] == "object"
    assert params["required"] == ["questions"]
    qprops = params["properties"]["questions"]["items"]["properties"]
    assert qprops["id"]["type"] == "string"
    assert qprops["prompt"]["type"] == "string"
    assert qprops["allow_multiple"]["type"] == "boolean"
    assert qprops["allow_free_text"]["type"] == "boolean"


def test_ask_user_question_returns_answers():
    tool = make_ask_user_question_tool(ask=_ok_callback)
    out = tool(
        questions=[
            {"id": "q1", "prompt": "Pick"},
            {"id": "q2", "prompt": "Pick again"},
        ]
    )
    assert out == {
        "cancelled": False,
        "answers": [
            {"id": "q1", "answer": "yes"},
            {"id": "q2", "answer": "yes"},
        ],
    }


def test_ask_user_question_propagates_title():
    seen = {}

    def capture(*, questions, title=None):
        seen["title"] = title
        seen["questions"] = list(questions)
        return {"answers": []}

    tool = make_ask_user_question_tool(ask=capture)
    tool(questions=[{"id": "q1", "prompt": "Hi"}], title="header")
    assert seen["title"] == "header"
    assert seen["questions"][0]["id"] == "q1"


def test_ask_user_question_cancellation():
    tool = make_ask_user_question_tool(ask=_cancel_callback)
    out = tool(questions=[{"id": "q", "prompt": "Hi"}])
    assert out == {"cancelled": True, "answers": []}


def test_ask_user_question_rejects_empty_list():
    tool = make_ask_user_question_tool(ask=_ok_callback)
    with pytest.raises(ValueError):
        tool(questions=[])


def test_ask_user_question_rejects_non_list():
    tool = make_ask_user_question_tool(ask=_ok_callback)
    with pytest.raises(TypeError):
        tool(questions="nope")  # type: ignore[arg-type]


def test_ask_user_question_validates_question_shape():
    tool = make_ask_user_question_tool(ask=_ok_callback)
    with pytest.raises(ValueError):
        tool(questions=[{"prompt": "no id"}])
    with pytest.raises(ValueError):
        tool(questions=[{"id": "q1"}])
    with pytest.raises(ValueError):
        tool(questions=[{"id": "q1", "prompt": "ok", "options": [{"id": "o"}]}])


def test_ask_user_question_rejects_non_callable_ask():
    with pytest.raises(TypeError):
        make_ask_user_question_tool(ask=None)  # type: ignore[arg-type]


def test_ask_user_question_propagates_options():
    seen = {}

    def capture(*, questions, title=None):
        seen["q"] = questions
        return {"answers": [{"id": "q1", "answer": ["a", "b"]}]}

    tool = make_ask_user_question_tool(ask=capture)
    out = tool(
        questions=[
            {
                "id": "q1",
                "prompt": "pick",
                "options": [
                    {"id": "a", "label": "A"},
                    {"id": "b", "label": "B"},
                ],
                "allow_multiple": True,
            }
        ],
    )
    assert seen["q"][0]["options"] == [
        {"id": "a", "label": "A"},
        {"id": "b", "label": "B"},
    ]
    assert out["answers"][0]["answer"] == ["a", "b"]
