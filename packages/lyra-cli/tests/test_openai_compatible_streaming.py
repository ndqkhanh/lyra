"""SSE streaming for :class:`OpenAICompatibleLLM`.

v2.2.4 added a ``stream`` peer of ``generate`` so the REPL can show
token-by-token replies instead of a long blocking pause. The wire
format is OpenAI's ``stream=True`` with ``stream_options.include_usage
=true`` — DeepSeek, Groq, Cerebras, Mistral, OpenRouter and xAI all
honour the same shape.

These tests pin the SSE parser, the request payload, and the post-
stream usage capture without touching the network. They use the
``_urlopen`` test seam already present on the class to feed a fake
response that exposes ``readline`` (matching what ``urllib`` returns
for a streaming HTTP connection).
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


def _sse_lines(*frames: dict | str) -> list[bytes]:
    """Convert a list of dict/string frames into raw SSE byte lines.

    Each frame becomes ``data: <json-or-string>\\n`` followed by an
    empty ``\\n`` separator. The fake ``readline`` implementation
    streams these one byte-line at a time, returning ``b""`` once the
    list is exhausted (urllib's EOF signal).
    """
    out: list[bytes] = []
    for f in frames:
        body = f if isinstance(f, str) else json.dumps(f)
        out.append(f"data: {body}\n".encode())
        out.append(b"\n")
    return out


class _FakeStreamResponse:
    """Stand-in for the response object ``urlopen`` returns.

    Only implements ``readline`` (line-at-a-time) and ``close`` —
    which is the contract :meth:`OpenAICompatibleLLM.stream` reads
    against. Returns ``b""`` to signal EOF.
    """

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = list(lines)
        self.closed = False

    def readline(self) -> bytes:
        if not self._lines:
            return b""
        return self._lines.pop(0)

    def close(self) -> None:
        self.closed = True


def _build_llm(urlopen) -> OpenAICompatibleLLM:
    return OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.example.com/v1",
        model="test-model",
        provider_name="example",
        _urlopen=urlopen,
    )


def test_stream_yields_text_deltas_in_order() -> None:
    """Three deltas in → three deltas out, concatenation matches."""
    frames = _sse_lines(
        {"choices": [{"delta": {"content": "Hello"}, "index": 0}]},
        {"choices": [{"delta": {"content": ", "}, "index": 0}]},
        {"choices": [{"delta": {"content": "world!"}, "index": 0}]},
        {
            "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 3,
                "total_tokens": 8,
            },
        },
        "[DONE]",
    )

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _FakeStreamResponse(frames)

    llm = _build_llm(urlopen)
    chunks = list(
        llm.stream(messages=[__build_user_message("hi")])
    )
    assert chunks == ["Hello", ", ", "world!"]
    assert "".join(chunks) == "Hello, world!"


def test_stream_captures_usage_on_final_chunk() -> None:
    """The trailing chunk's ``usage`` block lands on ``last_usage``
    so :func:`_bill_turn` can read it back the moment the stream
    iterator finishes."""
    frames = _sse_lines(
        {"choices": [{"delta": {"content": "yo"}, "index": 0}]},
        {
            "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 17,
                "completion_tokens": 23,
                "total_tokens": 40,
            },
        },
        "[DONE]",
    )

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _FakeStreamResponse(frames)

    llm = _build_llm(urlopen)
    list(llm.stream(messages=[__build_user_message("ping")]))

    assert llm.last_usage["prompt_tokens"] == 17
    assert llm.last_usage["completion_tokens"] == 23
    assert llm.last_usage["total_tokens"] == 40
    # Cumulative is bumped by the same delta.
    assert llm.cumulative_usage["total_tokens"] == 40


def test_stream_request_includes_stream_true_and_usage_opt_in() -> None:
    """Wire format: stream=true, stream_options.include_usage=true.
    These two fields are what unlock token-level streaming and final
    usage telemetry across the OpenAI-compat ecosystem."""
    captured: dict[str, Any] = {}

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeStreamResponse(_sse_lines("[DONE]"))

    llm = _build_llm(urlopen)
    list(llm.stream(messages=[__build_user_message("hi")]))

    payload = captured["payload"]
    assert payload["stream"] is True
    assert payload["stream_options"] == {"include_usage": True}
    assert payload["model"] == "test-model"


def test_stream_emits_accept_event_stream_header() -> None:
    """Some CDNs collapse SSE into a single chunk if Accept doesn't
    explicitly opt in. The header must be set."""
    captured: dict[str, Any] = {}

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        captured["headers"] = dict(req.header_items())
        return _FakeStreamResponse(_sse_lines("[DONE]"))

    llm = _build_llm(urlopen)
    list(llm.stream(messages=[__build_user_message("hi")]))

    assert captured["headers"].get("Accept") == "text/event-stream"


def test_stream_skips_sse_comment_heartbeats() -> None:
    """OpenRouter (and others) send ``: keepalive`` comment lines
    every ~10s. They must not show up as text deltas."""
    frames: list[bytes] = [
        b": keepalive\n",
        b"\n",
        b"data: " + json.dumps({"choices": [{"delta": {"content": "x"}}]}).encode() + b"\n",
        b"\n",
        b"data: [DONE]\n",
        b"\n",
    ]

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _FakeStreamResponse(frames)

    llm = _build_llm(urlopen)
    chunks = list(llm.stream(messages=[__build_user_message("hi")]))
    assert chunks == ["x"]


def test_stream_tolerates_malformed_chunk() -> None:
    """A single corrupt JSON line must not poison the rest of the
    stream — providers occasionally send truncated frames during
    rate-limit ramps."""
    frames: list[bytes] = [
        b"data: {not-json}\n",
        b"\n",
        b"data: " + json.dumps({"choices": [{"delta": {"content": "ok"}}]}).encode() + b"\n",
        b"\n",
        b"data: [DONE]\n",
        b"\n",
    ]

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return _FakeStreamResponse(frames)

    llm = _build_llm(urlopen)
    chunks = list(llm.stream(messages=[__build_user_message("hi")]))
    assert chunks == ["ok"]


def test_stream_closes_response_when_iterator_exhausted() -> None:
    """We must release the HTTP connection — leaking sockets across
    many turns will exhaust the file descriptor pool."""
    resp_holder: dict[str, _FakeStreamResponse] = {}
    frames = _sse_lines(
        {"choices": [{"delta": {"content": "ok"}}]},
        "[DONE]",
    )

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        resp_holder["resp"] = _FakeStreamResponse(frames)
        return resp_holder["resp"]

    llm = _build_llm(urlopen)
    list(llm.stream(messages=[__build_user_message("hi")]))

    assert resp_holder["resp"].closed is True


def test_stream_raises_provider_http_error_on_4xx() -> None:
    """A 401/429 must surface as ProviderHTTPError so the chat
    handler can fall back to the non-streaming retry path or render
    a friendly error renderable."""
    import urllib.error
    import io

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError(
            url="https://api.example.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"error":{"message":"bad key"}}'),
        )

    llm = _build_llm(urlopen)
    with pytest.raises(ProviderHTTPError) as exc_info:
        list(llm.stream(messages=[__build_user_message("hi")]))

    assert "401" in str(exc_info.value)


def test_stream_resets_last_usage_at_start() -> None:
    """A second stream call must not leak the usage from the first —
    each turn captures its own.

    When the provider wire ships a real ``usage`` chunk the recorded
    figures land verbatim and ``estimated`` is *not* set. When the wire
    omits ``usage`` entirely (some providers do, even though the OpenAI
    spec mandates it once you pass ``stream_options.include_usage``),
    the v2.3 backstop in :meth:`OpenAICompatibleLLM.stream` synthesises
    a char-count-based estimate and tags it with ``estimated: True`` so
    the budget meter never silently bills $0.
    """
    first_frames = _sse_lines(
        {"choices": [{"delta": {"content": "a"}}]},
        {
            "choices": [{"delta": {}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        },
        "[DONE]",
    )
    second_frames = _sse_lines(
        {"choices": [{"delta": {"content": "b"}}]},
        # No usage on the second call — the backstop must populate an
        # estimate so chat turns are never billed at zero cost.
        "[DONE]",
    )
    box = {"first": True}

    def urlopen(req, timeout):  # type: ignore[no-untyped-def]
        if box["first"]:
            box["first"] = False
            return _FakeStreamResponse(first_frames)
        return _FakeStreamResponse(second_frames)

    llm = _build_llm(urlopen)
    list(llm.stream(messages=[__build_user_message("hi")]))
    assert llm.last_usage["total_tokens"] == 15
    assert "estimated" not in llm.last_usage

    list(llm.stream(messages=[__build_user_message("hi again")]))
    # Second turn: SSE shipped no `usage`, so the backstop fills in an
    # estimated counter pair. The exact tokens are heuristic (4
    # chars/token) — what matters for the contract is the keys exist
    # and the row is flagged as estimated so dashboards can distinguish
    # real vs synthesised numbers.
    assert llm.last_usage.get("estimated") is True
    assert llm.last_usage["prompt_tokens"] >= 1
    assert llm.last_usage["completion_tokens"] >= 1
    assert llm.last_usage["total_tokens"] == (
        llm.last_usage["prompt_tokens"] + llm.last_usage["completion_tokens"]
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def __build_user_message(text: str) -> Any:
    """Construct a single-user :class:`Message` for stream() inputs.

    The provider only needs ``role`` + ``content`` to build the
    OpenAI wire payload, so a thin object suffices.
    """
    from harness_core.messages import Message

    return Message(role="user", content=text)
