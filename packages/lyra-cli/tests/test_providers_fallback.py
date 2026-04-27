"""Contract tests for the fallback provider chain.

Cascade through a list of LLM providers: try the first; on transient
errors (5xx, 429, network timeouts), advance to the next; on fatal
errors (auth, bad request), short-circuit and re-raise. If the chain
exhausts, raise FallbackExhausted with the per-provider error list so
callers can see what happened.
"""
from __future__ import annotations

import pytest

from harness_core.messages import Message, StopReason
from lyra_cli.providers.fallback import (
    FallbackChain,
    FallbackExhausted,
    classify_error,
    is_retryable_error,
)
from lyra_cli.providers.openai_compatible import (
    ProviderHTTPError,
    ProviderNotConfigured,
)


class _FakeProvider:
    def __init__(self, name: str, *, raises: Exception | None = None,
                 reply: str = "ok") -> None:
        self.name = name
        self._raises = raises
        self._reply = reply
        self.call_count = 0

    def generate(self, messages, tools=None, max_tokens=2048, temperature=0.0):
        self.call_count += 1
        if self._raises is not None:
            raise self._raises
        return Message.assistant(content=self._reply, stop_reason=StopReason.END_TURN)


def test_first_provider_success_used_directly() -> None:
    p1 = _FakeProvider("p1", reply="from-p1")
    p2 = _FakeProvider("p2", reply="from-p2")
    chain = FallbackChain([p1, p2])
    out = chain.generate([Message.user("hi")])
    assert out.content == "from-p1"
    assert p1.call_count == 1
    assert p2.call_count == 0


def test_5xx_advances_to_next() -> None:
    p1 = _FakeProvider("p1", raises=ProviderHTTPError("p1 HTTP 503: down"))
    p2 = _FakeProvider("p2", reply="from-p2")
    chain = FallbackChain([p1, p2])
    out = chain.generate([Message.user("hi")])
    assert out.content == "from-p2"
    assert p1.call_count == 1
    assert p2.call_count == 1


def test_429_advances_to_next() -> None:
    p1 = _FakeProvider("p1", raises=ProviderHTTPError("p1 HTTP 429: rate limit"))
    p2 = _FakeProvider("p2", reply="from-p2")
    chain = FallbackChain([p1, p2])
    out = chain.generate([Message.user("hi")])
    assert out.content == "from-p2"


def test_timeout_advances_to_next() -> None:
    p1 = _FakeProvider("p1", raises=ProviderHTTPError(
        "p1 unreachable at https://example.com: timed out"))
    p2 = _FakeProvider("p2", reply="from-p2")
    chain = FallbackChain([p1, p2])
    out = chain.generate([Message.user("hi")])
    assert out.content == "from-p2"


def test_401_short_circuits() -> None:
    p1 = _FakeProvider("p1", raises=ProviderHTTPError("p1 HTTP 401: unauthorized"))
    p2 = _FakeProvider("p2", reply="from-p2")
    chain = FallbackChain([p1, p2])
    with pytest.raises(ProviderHTTPError):
        chain.generate([Message.user("hi")])
    assert p1.call_count == 1
    assert p2.call_count == 0


def test_400_short_circuits() -> None:
    p1 = _FakeProvider("p1", raises=ProviderHTTPError("p1 HTTP 400: bad request"))
    p2 = _FakeProvider("p2", reply="from-p2")
    chain = FallbackChain([p1, p2])
    with pytest.raises(ProviderHTTPError):
        chain.generate([Message.user("hi")])


def test_provider_not_configured_short_circuits() -> None:
    p1 = _FakeProvider("p1", raises=ProviderNotConfigured("p1: no key"))
    p2 = _FakeProvider("p2", reply="from-p2")
    chain = FallbackChain([p1, p2])
    with pytest.raises(ProviderNotConfigured):
        chain.generate([Message.user("hi")])


def test_chain_exhausted_raises_with_full_history() -> None:
    p1 = _FakeProvider("p1", raises=ProviderHTTPError("p1 HTTP 503"))
    p2 = _FakeProvider("p2", raises=ProviderHTTPError("p2 HTTP 502"))
    chain = FallbackChain([p1, p2])
    with pytest.raises(FallbackExhausted) as exc:
        chain.generate([Message.user("hi")])
    assert "p1" in str(exc.value) or "p2" in str(exc.value)
    assert len(exc.value.errors) == 2


def test_classify_error_recognises_5xx_as_retryable() -> None:
    assert classify_error(ProviderHTTPError("HTTP 503: down")) == "retryable"
    assert classify_error(ProviderHTTPError("HTTP 502")) == "retryable"
    assert classify_error(ProviderHTTPError("HTTP 500")) == "retryable"


def test_classify_error_recognises_4xx_as_fatal() -> None:
    assert classify_error(ProviderHTTPError("HTTP 401: nope")) == "fatal"
    assert classify_error(ProviderHTTPError("HTTP 403: forbidden")) == "fatal"
    assert classify_error(ProviderHTTPError("HTTP 400: bad")) == "fatal"


def test_is_retryable_helper_matches_classify() -> None:
    assert is_retryable_error(ProviderHTTPError("HTTP 503"))
    assert not is_retryable_error(ProviderHTTPError("HTTP 401"))
    assert not is_retryable_error(ProviderNotConfigured("missing key"))


def test_empty_chain_raises_immediately() -> None:
    chain = FallbackChain([])
    with pytest.raises(FallbackExhausted):
        chain.generate([Message.user("hi")])
