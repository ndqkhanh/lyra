"""LLM-callable ``AskUserQuestion`` tool — claw-code / opencode / hermes parity.

This tool lets the agent pause and ask the user a structured question
with multiple-choice or free-form answers. All three reference repos
ship a variant of this — Claude Code's ``AskUserQuestionTool``,
opencode's ``QuestionTool``, and hermes-agent's ``clarify_tool`` — and
v3.0.0 closes the gap.

Schema:

.. code-block:: json

    {
      "name": "AskUserQuestion",
      "parameters": {
        "type": "object",
        "properties": {
          "questions": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "id": {"type": "string"},
                "prompt": {"type": "string"},
                "options": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "id": {"type": "string"},
                      "label": {"type": "string"}
                    },
                    "required": ["id", "label"]
                  }
                },
                "allow_multiple": {"type": "boolean", "default": false},
                "allow_free_text": {"type": "boolean", "default": false}
              },
              "required": ["id", "prompt"]
            }
          },
          "title": {"type": "string"}
        },
        "required": ["questions"]
      }
    }

Behaviour:

* The tool is *callback-driven* — the agent loop must inject a
  callable ``ask`` that knows how to surface the prompt to the user
  (REPL → prompt_toolkit, channel adapters → message bubble, headless
  → pre-canned answer fixture).
* The callback receives the validated ``questions`` payload and
  returns a list of ``{"id": str, "answer": str | list[str]}``
  records. If the user cancels (e.g. Ctrl+C), the tool returns
  ``{"cancelled": True, "answers": []}``.
* Free-text answers are returned as plain strings; multi-choice
  answers as a list of selected option ids.
* ``title`` is an optional header rendered above the questions in
  the UI.
"""
from __future__ import annotations

from typing import Any, Callable, Sequence

AskCallback = Callable[..., dict[str, Any]]
"""Signature: ``ask(*, questions, title=None) -> dict``.

Implementations should return either:

* ``{"answers": [{"id": str, "answer": str | list[str]}, ...]}`` on success
* ``{"cancelled": True, "answers": []}`` if the user backed out
"""


def _validate_question(q: dict) -> dict:
    if not isinstance(q, dict):
        raise TypeError(f"question must be a dict, got {type(q).__name__}")
    if "id" not in q or not q["id"]:
        raise ValueError(f"question missing 'id': {q!r}")
    if "prompt" not in q or not q["prompt"]:
        raise ValueError(f"question missing 'prompt': {q!r}")
    options = q.get("options")
    if options is not None:
        if not isinstance(options, Sequence):
            raise TypeError(
                f"question {q['id']!r} has non-sequence options: "
                f"{type(options).__name__}"
            )
        for opt in options:
            if not isinstance(opt, dict):
                raise TypeError(f"option must be a dict, got {type(opt).__name__}")
            if "id" not in opt or "label" not in opt:
                raise ValueError(f"option missing id/label: {opt!r}")
    return dict(q)


def make_ask_user_question_tool(*, ask: AskCallback) -> Callable[..., dict]:
    """Build the LLM-callable ``AskUserQuestion`` tool.

    Parameters
    ----------
    ask:
        A callback that knows how to surface a question to the user
        and collect answers. Tests pass a deterministic fixture; the
        REPL passes a prompt_toolkit-backed implementation; channel
        adapters pass a per-channel implementation.
    """
    if not callable(ask):
        raise TypeError("ask must be callable")

    def ask_user_question(
        *,
        questions: list[dict],
        title: str | None = None,
    ) -> dict:
        if not isinstance(questions, list):
            raise TypeError(
                f"questions must be a list, got {type(questions).__name__}"
            )
        if not questions:
            raise ValueError("at least one question is required")
        validated = [_validate_question(dict(q)) for q in questions]
        result = ask(questions=validated, title=title)
        if not isinstance(result, dict):
            raise TypeError(
                f"ask callback must return a dict, got {type(result).__name__}"
            )
        if result.get("cancelled"):
            return {"cancelled": True, "answers": []}
        answers = result.get("answers", [])
        if not isinstance(answers, list):
            raise TypeError(
                f"answers must be a list, got {type(answers).__name__}"
            )
        return {"cancelled": False, "answers": answers}

    ask_user_question.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "AskUserQuestion",
        "description": (
            "Ask the user one or more structured questions and wait for "
            "their answer. Use when you need clarifying information that "
            "you cannot deduce from the conversation, the repo state, or "
            "tool output. Each question can be multiple-choice or "
            "free-text. Pause the rest of your turn until the answer "
            "comes back."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "prompt": {"type": "string"},
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "label": {"type": "string"},
                                    },
                                    "required": ["id", "label"],
                                },
                            },
                            "allow_multiple": {"type": "boolean", "default": False},
                            "allow_free_text": {"type": "boolean", "default": False},
                        },
                        "required": ["id", "prompt"],
                    },
                },
                "title": {"type": "string"},
            },
            "required": ["questions"],
        },
    }
    return ask_user_question


__all__ = ["make_ask_user_question_tool", "AskCallback"]
