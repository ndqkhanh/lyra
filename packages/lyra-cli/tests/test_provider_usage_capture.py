"""OpenAI-compatible providers expose per-call and cumulative token usage.

DeepSeek (and every other OpenAI-compatible endpoint) returns a
``usage`` block in the response body::

    {"usage": {"prompt_tokens": 7, "completion_tokens": 4,
               "total_tokens": 11}}

Pre-2.1.3 we discarded it. The user complaint that motivated this
change: "I don't see real call to deepseek yet??" — i.e. the bare
"hello world" output looked indistinguishable from a canned mock.

Surfacing token usage in the run footer (``done · 1 step · 0 tools
· 7 in / 4 out · 1.5s``) is hard evidence the API actually answered
— mocks don't return token counts, so a non-zero ``in/out`` is
proof-of-life by construction.

This file pins the capture-side contract on
:class:`OpenAICompatibleLLM`. The footer-rendering side is in
``test_run_render.py``.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from lyra_cli.providers.openai_compatible import (
    OpenAICompatibleLLM,
    ProviderHTTPError,
)


def _fake_response(payload: dict[str, Any]) -> MagicMock:
    """Build a fake ``urlopen`` context-manager-yielding response.

    Mimics what ``urllib.request.urlopen`` returns so we can drop it
    into ``OpenAICompatibleLLM`` via the ``_urlopen`` test seam.
    """
    raw = json.dumps(payload).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = raw
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _build_llm(urlopen) -> OpenAICompatibleLLM:
    return OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.example.com/v1",
        model="test-model",
        provider_name="example",
        _urlopen=urlopen,
    )


def test_provider_records_last_usage_on_successful_call() -> None:
    """A single ``generate`` call captures the response's ``usage``
    block on ``llm.last_usage``."""
    payload = {
        "choices": [{"message": {"content": "ok", "role": "assistant"}}],
        "usage": {
            "prompt_tokens": 7,
            "completion_tokens": 4,
            "total_tokens": 11,
        },
    }

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _fake_response(payload)

    llm = _build_llm(urlopen)
    from harness_core.messages import Message

    llm.generate([Message.user("hi")])
    assert llm.last_usage == {
        "prompt_tokens": 7,
        "completion_tokens": 4,
        "total_tokens": 11,
    }


def test_provider_initialises_last_usage_empty_before_first_call() -> None:
    """``last_usage`` is an empty dict before the first ``generate``,
    so callers don't trip over ``AttributeError`` mid-cascade."""
    llm = _build_llm(lambda req, timeout: _fake_response({}))
    assert llm.last_usage == {}
    assert llm.cumulative_usage == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_provider_accumulates_usage_across_multiple_calls() -> None:
    """Multi-step agent loops sum usage on ``cumulative_usage`` so
    the run footer can show *total* tokens spent, not just the last
    step's. This matches how ``claude-code`` / ``opencode`` display
    session-wide cost."""
    responses = [
        {
            "choices": [{"message": {"content": "step1", "role": "assistant"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
        {
            "choices": [{"message": {"content": "step2", "role": "assistant"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        },
        {
            "choices": [{"message": {"content": "step3", "role": "assistant"}}],
            "usage": {"prompt_tokens": 6, "completion_tokens": 3, "total_tokens": 9},
        },
    ]
    iterator = iter(responses)

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _fake_response(next(iterator))

    llm = _build_llm(urlopen)
    from harness_core.messages import Message

    for _ in range(3):
        llm.generate([Message.user("hi")])

    assert llm.cumulative_usage == {
        "prompt_tokens": 10 + 12 + 6,
        "completion_tokens": 5 + 8 + 3,
        "total_tokens": 15 + 20 + 9,
    }


def test_provider_handles_missing_usage_gracefully() -> None:
    """Some providers (esp. local servers) omit ``usage`` from the
    response. We must not crash; ``last_usage`` stays empty and
    ``cumulative_usage`` doesn't move."""
    payload_no_usage = {
        "choices": [{"message": {"content": "ok", "role": "assistant"}}],
    }

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _fake_response(payload_no_usage)

    llm = _build_llm(urlopen)
    from harness_core.messages import Message

    llm.generate([Message.user("hi")])

    assert llm.last_usage == {}
    assert llm.cumulative_usage == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_provider_handles_partial_usage_block() -> None:
    """Some providers (e.g. older Groq builds) return ``total_tokens``
    only. We accept any subset and keep zeroes for the missing keys."""
    payload = {
        "choices": [{"message": {"content": "ok", "role": "assistant"}}],
        "usage": {"total_tokens": 11},  # no prompt/completion split
    }

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _fake_response(payload)

    llm = _build_llm(urlopen)
    from harness_core.messages import Message

    llm.generate([Message.user("hi")])

    assert llm.last_usage == {"total_tokens": 11}
    assert llm.cumulative_usage["total_tokens"] == 11
    assert llm.cumulative_usage["prompt_tokens"] == 0
    assert llm.cumulative_usage["completion_tokens"] == 0
