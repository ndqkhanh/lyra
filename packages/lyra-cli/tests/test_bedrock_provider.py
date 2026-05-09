"""Contract tests for the AnthropicBedrockLLM provider.

boto3 is an optional dependency (lyra[bedrock]); the tests build a
fake client and inject it so the suite runs even when boto3 isn't
installed.
"""
from __future__ import annotations

import pytest

from harness_core.messages import Message, StopReason
from lyra_cli.providers.bedrock import (
    AnthropicBedrockLLM,
    BedrockUnavailable,
    bedrock_available,
)


class _FakeBedrockClient:
    """Minimal stand-in for boto3's bedrock-runtime client."""

    def __init__(self, response: dict) -> None:
        self._response = response
        self.last_kwargs: dict | None = None

    def converse(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


def test_bedrock_unavailable_when_no_client() -> None:
    with pytest.raises(BedrockUnavailable):
        AnthropicBedrockLLM(model="anthropic.claude-opus-4-5-v2:0")


def test_generate_uses_converse_api() -> None:
    fake = _FakeBedrockClient({
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "hi from bedrock"}],
            }
        },
        "stopReason": "end_turn",
    })
    llm = AnthropicBedrockLLM(
        model="anthropic.claude-opus-4-5-v2:0",
        client=fake,
    )
    out = llm.generate([Message.user("hello")], max_tokens=200)
    assert out.content == "hi from bedrock"
    assert out.stop_reason == StopReason.END_TURN
    assert fake.last_kwargs is not None
    assert fake.last_kwargs["modelId"] == "anthropic.claude-opus-4-5-v2:0"
    assert fake.last_kwargs["messages"][0]["role"] == "user"


def test_tool_call_roundtrip() -> None:
    fake = _FakeBedrockClient({
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "calling read_file"},
                    {
                        "toolUse": {
                            "toolUseId": "tu_1",
                            "name": "read_file",
                            "input": {"path": "main.py"},
                        }
                    },
                ],
            }
        },
        "stopReason": "tool_use",
    })
    llm = AnthropicBedrockLLM(
        model="anthropic.claude-opus-4-5-v2:0",
        client=fake,
    )
    out = llm.generate(
        [Message.user("read main.py")],
        tools=[{"name": "read_file", "input_schema": {"type": "object"}}],
        max_tokens=200,
    )
    assert out.stop_reason == StopReason.TOOL_USE
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].name == "read_file"
    assert out.tool_calls[0].args == {"path": "main.py"}


def test_bedrock_available_returns_bool() -> None:
    # Just verify the helper returns a bool (don't assert True/False
    # because we can't guarantee whether boto3 is installed in the
    # test env).
    assert isinstance(bedrock_available(), bool)
