"""Contract tests for :class:`lyra_cli.tui_v2.LyraTransport`.

The transport bridges Lyra's sync ``harness_core.AgentLoop`` to
harness-tui's async event stream. The contract under test:

  * ``submit`` emits ``TurnStarted`` immediately
  * Tool calls during the run emit paired ``ToolStarted`` / ``ToolFinished``
  * The final reply is re-emitted as one or more ``TextDelta`` events
  * The turn closes with a single ``TurnFinished`` carrying usage + stop_reason
  * Events are totally ordered (``seq`` strictly increasing)

Provider + tools are injected as fakes so the test runs in <1s with no
network or filesystem dependency. Each test wraps its body in
``asyncio.run`` so the suite doesn't depend on pytest-asyncio.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from harness_tui import events as ev

from lyra_cli.tui_v2.transport import LyraTransport


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _FakeMessage:
    """Mimics ``harness_core.messages.Message`` for the provider response."""

    def __init__(
        self,
        *,
        content: str = "",
        tool_calls: list[Any] | None = None,
        stop_reason: Any = "end_turn",
    ) -> None:
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or []
        self.stop_reason = stop_reason

    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class _FakeProvider:
    """Returns scripted ``_FakeMessage`` responses; tracks usage."""

    def __init__(self, responses: list[_FakeMessage]) -> None:
        self._responses = list(responses)
        self.cumulative_usage = {
            "input_tokens": 42,
            "output_tokens": 100,
            "cost_usd": 0.0008,
        }

    def generate(self, _transcript, *, tools=None):  # noqa: ARG002
        if not self._responses:
            return _FakeMessage(content="done", stop_reason="end_turn")
        return self._responses.pop(0)


class _FakeTools:
    """Minimal ToolRegistry surface used by AgentLoop."""

    def schemas(self) -> list:
        return []

    def get(self, _name: str):
        return None

    def execute(self, _call):
        from harness_core.messages import ToolResult

        return ToolResult(call_id="", content="", is_error=False)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


async def _drain(transport: LyraTransport, count: int, timeout: float = 5.0) -> list:
    """Pull ``count`` events from the stream or raise on timeout."""
    out: list = []
    agen = transport.stream()
    try:
        for _ in range(count):
            out.append(await asyncio.wait_for(agen.__anext__(), timeout=timeout))
    finally:
        await agen.aclose()
    return out


def _run(coro):
    """Run an async test body in a fresh event loop.

    The transport captures the running loop via ``get_running_loop()``
    inside ``submit()``; each test gets a clean loop so worker-thread
    handoffs land on the loop the test is awaiting on.
    """
    asyncio.run(coro)


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_text_only_turn_emits_started_delta_finished(tmp_path: Path) -> None:
    async def body() -> None:
        provider = _FakeProvider([_FakeMessage(content="hello, world.")])
        transport = LyraTransport(
            repo_root=tmp_path, provider=provider, tools=_FakeTools()
        )

        turn_id = await transport.submit("ping")
        captured = await _drain(transport, 3)

        assert isinstance(captured[0], ev.TurnStarted)
        assert captured[0].turn_id == turn_id
        assert captured[0].user_text == "ping"

        assert isinstance(captured[1], ev.TextDelta)
        assert captured[1].text == "hello, world."

        assert isinstance(captured[2], ev.TurnFinished)
        assert captured[2].tokens_in == 42
        assert captured[2].tokens_out == 100
        assert captured[2].cost_usd == pytest.approx(0.0008)
        assert captured[2].stop_reason == "end_turn"

        seqs = [e.seq for e in captured]
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)

        await transport.close()

    _run(body())


def test_long_reply_chunks_into_multiple_text_deltas(tmp_path: Path) -> None:
    async def body() -> None:
        long_reply = "x" * 250  # 80-char chunks → 4 deltas
        provider = _FakeProvider([_FakeMessage(content=long_reply)])
        transport = LyraTransport(
            repo_root=tmp_path, provider=provider, tools=_FakeTools()
        )

        await transport.submit("noop")
        # Expected: TurnStarted + 4 TextDelta + TurnFinished
        captured = await _drain(transport, 6)

        text_deltas = [e for e in captured if isinstance(e, ev.TextDelta)]
        assert len(text_deltas) == 4
        assert "".join(d.text for d in text_deltas) == long_reply

        await transport.close()

    _run(body())


def test_provider_failure_emits_error_finish(tmp_path: Path) -> None:
    async def body() -> None:
        class _BoomProvider:
            cumulative_usage: dict = {}

            def generate(self, *_a, **_kw):
                raise RuntimeError("nope")

        transport = LyraTransport(
            repo_root=tmp_path, provider=_BoomProvider(), tools=_FakeTools()
        )

        await transport.submit("anything")
        captured = await _drain(transport, 3)

        assert isinstance(captured[0], ev.TurnStarted)
        assert isinstance(captured[1], ev.TextDelta)
        assert "agent error" in captured[1].text
        assert isinstance(captured[2], ev.TurnFinished)
        assert captured[2].stop_reason == "error"

        await transport.close()

    _run(body())


def test_submit_returns_turn_id_immediately(tmp_path: Path) -> None:
    """submit() must not block on the worker thread."""

    async def body() -> None:
        provider = _FakeProvider([_FakeMessage(content="ok")])
        transport = LyraTransport(
            repo_root=tmp_path, provider=provider, tools=_FakeTools()
        )

        turn_id = await asyncio.wait_for(transport.submit("hi"), timeout=0.5)
        assert turn_id.startswith("t_")
        await _drain(transport, 3)
        await transport.close()

    _run(body())
