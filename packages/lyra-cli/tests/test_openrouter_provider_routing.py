"""Contract tests for OpenRouter ProviderRouting.

OpenRouter's `provider` field in the request body lets you sort by
price, restrict to specific upstream providers, and a few other knobs.
We expose this as a tiny dataclass so callers don't need to remember
the JSON keys.

These tests don't hit the network; the `_urlopen` test hook lets us
capture the outgoing request and assert on the marshalling.
"""
from __future__ import annotations

import io
import json
from typing import Any

import pytest

from lyra_cli.providers.openai_compatible import (
    OpenAICompatibleLLM,
    ProviderRouting,
)
from harness_core.messages import Message


class _FakeResp:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _ok_body() -> str:
    return json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "hi"},
                    "finish_reason": "stop",
                }
            ]
        }
    )


def _make_llm(routing: ProviderRouting | None = None):
    captured: dict[str, Any] = {}

    def fake_urlopen(req, timeout: float = 0):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(_ok_body())

    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://openrouter.ai/api/v1",
        model="anthropic/claude-3.5-sonnet",
        provider_name="openrouter",
        provider_routing=routing,
        _urlopen=fake_urlopen,
    )
    return llm, captured


def test_no_routing_omits_provider_field() -> None:
    llm, captured = _make_llm()
    llm.generate([Message.user("hi")], max_tokens=10)
    body = captured["body"]
    assert "extra_body" not in body or "provider" not in (body.get("extra_body") or {})


def test_sort_price_serialised() -> None:
    llm, captured = _make_llm(ProviderRouting(sort="price"))
    llm.generate([Message.user("hi")], max_tokens=10)
    assert captured["body"]["extra_body"]["provider"] == {"sort": "price"}


def test_sort_throughput_serialised() -> None:
    llm, captured = _make_llm(ProviderRouting(sort="throughput"))
    llm.generate([Message.user("hi")], max_tokens=10)
    assert captured["body"]["extra_body"]["provider"] == {"sort": "throughput"}


def test_only_list_serialised() -> None:
    llm, captured = _make_llm(ProviderRouting(only=("Anthropic", "OpenAI")))
    llm.generate([Message.user("hi")], max_tokens=10)
    assert captured["body"]["extra_body"]["provider"] == {"only": ["Anthropic", "OpenAI"]}


def test_ignore_list_serialised() -> None:
    llm, captured = _make_llm(ProviderRouting(ignore=("Cohere",)))
    llm.generate([Message.user("hi")], max_tokens=10)
    assert captured["body"]["extra_body"]["provider"] == {"ignore": ["Cohere"]}


def test_order_list_serialised() -> None:
    llm, captured = _make_llm(ProviderRouting(order=("Anthropic", "OpenAI", "Mistral")))
    llm.generate([Message.user("hi")], max_tokens=10)
    assert captured["body"]["extra_body"]["provider"] == {
        "order": ["Anthropic", "OpenAI", "Mistral"]
    }


def test_combined_serialised() -> None:
    llm, captured = _make_llm(
        ProviderRouting(
            sort="price",
            only=("Anthropic",),
            ignore=("Cohere",),
            require_parameters=True,
            data_collection="deny",
        )
    )
    llm.generate([Message.user("hi")], max_tokens=10)
    provider = captured["body"]["extra_body"]["provider"]
    assert provider == {
        "sort": "price",
        "only": ["Anthropic"],
        "ignore": ["Cohere"],
        "require_parameters": True,
        "data_collection": "deny",
    }


def test_urlopen_hook_actually_replaces_network() -> None:
    sentinel: dict[str, bool] = {"called": False}

    def fake_urlopen(req, timeout: float = 0):
        sentinel["called"] = True
        return _FakeResp(_ok_body())

    llm = OpenAICompatibleLLM(
        api_key="k",
        base_url="https://example.invalid",
        model="x",
        provider_name="t",
        _urlopen=fake_urlopen,
    )
    llm.generate([Message.user("hi")], max_tokens=10)
    assert sentinel["called"] is True


def test_routing_does_not_affect_other_payload_fields() -> None:
    llm, captured = _make_llm(ProviderRouting(sort="price"))
    llm.generate([Message.user("hi")], max_tokens=10, temperature=0.7)
    body = captured["body"]
    assert body["model"] == "anthropic/claude-3.5-sonnet"
    assert body["temperature"] == 0.7
    assert body["max_tokens"] == 10
    assert body["messages"] == [{"role": "user", "content": "hi"}]
