"""Wave-E Task 1: contract tests for the channel adapter substrate.

These tests are intentionally **transport-free** — they exercise the
:class:`Inbound` dataclass, the :class:`ChannelAdapter` protocol, and
the :class:`Gateway` against an in-memory ``FakeAdapter`` so the unit
tier never needs Slack / Discord / Matrix tokens. Every per-channel
adapter (Tasks 2–6) reuses this same protocol; if those adapters' own
contract tests pass *and* the substrate tests below pass, gateway
routing is wired correctly.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import AsyncIterator, List

import pytest

from lyra_cli.channels.base import (
    ChannelAdapter,
    Gateway,
    Inbound,
    Outbound,
)


# ---------------------------------------------------------------------------
# Fake adapter
# ---------------------------------------------------------------------------


class _FakeAdapter:
    """In-memory adapter the gateway tests drive."""

    name = "fake"

    def __init__(self, *, name: str = "fake") -> None:
        self.name = name
        self._inbound_q: asyncio.Queue[Inbound] | None = None
        self._pending: list[Inbound] = []
        self.sent: List[Outbound] = []
        self.started = False
        self.stopped = False
        self.raise_on_iter = False

    def _ensure_queue(self) -> "asyncio.Queue[Inbound]":
        if self._inbound_q is None:
            self._inbound_q = asyncio.Queue()
            for inbound in self._pending:
                self._inbound_q.put_nowait(inbound)
            self._pending.clear()
        return self._inbound_q

    async def start(self) -> None:
        self.started = True
        self._ensure_queue()

    async def stop(self) -> None:
        self.stopped = True

    async def send(self, *, thread_id: str, text: str) -> str:
        msg = Outbound(channel=self.name, thread_id=thread_id, text=text)
        self.sent.append(msg)
        return f"{self.name}:{thread_id}:{len(self.sent)}"

    async def iter_inbound(self) -> AsyncIterator[Inbound]:
        if self.raise_on_iter:
            raise RuntimeError("intentional adapter failure")
        q = self._ensure_queue()
        while True:
            inbound = await q.get()
            if inbound.text == "__STOP__":
                return
            yield inbound

    # test helpers ---------------------------------------------------
    def push(self, inbound: Inbound) -> None:
        if self._inbound_q is None:
            self._pending.append(inbound)
        else:
            self._inbound_q.put_nowait(inbound)


def _inbound(channel: str = "fake", thread: str = "T1", text: str = "hi") -> Inbound:
    return Inbound(
        channel=channel,
        thread_id=thread,
        user_id="U1",
        text=text,
        attachments=(),
        received_at=0.0,
    )


# ---------------------------------------------------------------------------
# Test 1: protocol surface
# ---------------------------------------------------------------------------


def test_channel_adapter_protocol_surface() -> None:
    adapter = _FakeAdapter()
    assert isinstance(adapter, ChannelAdapter)
    for attr in ("start", "stop", "send", "iter_inbound"):
        assert hasattr(adapter, attr), f"missing {attr}"


# ---------------------------------------------------------------------------
# Test 2: gateway routes inbound to the right session
# ---------------------------------------------------------------------------


def test_gateway_routes_inbound_to_per_thread_session() -> None:
    fake = _FakeAdapter()
    seen: list[tuple[str, str]] = []

    async def handler(inbound: Inbound) -> str:
        seen.append((inbound.thread_id, inbound.text))
        return f"echo: {inbound.text}"

    async def driver() -> None:
        gw = Gateway(adapters=[fake], handler=handler)
        await gw.start()
        fake.push(_inbound(thread="T1", text="one"))
        fake.push(_inbound(thread="T2", text="two"))
        fake.push(_inbound(thread="T1", text="three"))
        fake.push(_inbound(text="__STOP__"))
        await gw.run_until_idle()
        await gw.stop()

    asyncio.run(driver())
    assert ("T1", "one") in seen
    assert ("T2", "two") in seen
    assert ("T1", "three") in seen
    assert {msg.thread_id for msg in fake.sent} == {"T1", "T2"}


# ---------------------------------------------------------------------------
# Test 3: gateway tolerates an adapter that raises in iter_inbound
# ---------------------------------------------------------------------------


def test_gateway_swallows_adapter_iter_failure() -> None:
    bad = _FakeAdapter(name="bad")
    bad.raise_on_iter = True
    good = _FakeAdapter(name="good")

    async def handler(inbound: Inbound) -> str:
        return inbound.text

    async def driver() -> None:
        gw = Gateway(adapters=[bad, good], handler=handler)
        await gw.start()
        good.push(_inbound(channel="good", text="survived"))
        good.push(_inbound(text="__STOP__"))
        await gw.run_until_idle()
        await gw.stop()

    asyncio.run(driver())
    assert any(msg.text == "survived" for msg in good.sent)


# ---------------------------------------------------------------------------
# Test 4: gateway emits ``channel.inbound`` HIR event
# ---------------------------------------------------------------------------


def test_gateway_emits_hir_event_on_inbound() -> None:
    from lyra_core.hir.events import subscribe, unsubscribe

    captured: list[tuple[str, dict]] = []

    def sub(name: str, /, **attrs: object) -> None:
        if name == "channel.inbound":
            captured.append((name, dict(attrs)))

    fake = _FakeAdapter()

    async def handler(inbound: Inbound) -> str:
        return ""

    async def driver() -> None:
        subscribe(sub)
        try:
            gw = Gateway(adapters=[fake], handler=handler)
            await gw.start()
            fake.push(_inbound(thread="HIR", text="ping"))
            fake.push(_inbound(text="__STOP__"))
            await gw.run_until_idle()
            await gw.stop()
        finally:
            unsubscribe(sub)

    asyncio.run(driver())
    assert any(
        attrs.get("channel") == "fake" and attrs.get("thread_id") == "HIR"
        for _, attrs in captured
    )


# ---------------------------------------------------------------------------
# Test 5: send returns a stable message id
# ---------------------------------------------------------------------------


def test_adapter_send_returns_message_id() -> None:
    fake = _FakeAdapter()

    async def driver() -> str:
        return await fake.send(thread_id="T9", text="hello")

    msg_id = asyncio.run(driver())
    assert isinstance(msg_id, str) and msg_id


# ---------------------------------------------------------------------------
# Test 6: multiplex multiple adapters
# ---------------------------------------------------------------------------


def test_gateway_multiplexes_multiple_adapters() -> None:
    a = _FakeAdapter(name="a")
    b = _FakeAdapter(name="b")
    seen_channels: list[str] = []

    async def handler(inbound: Inbound) -> str:
        seen_channels.append(inbound.channel)
        return ""

    async def driver() -> None:
        gw = Gateway(adapters=[a, b], handler=handler)
        await gw.start()
        a.push(_inbound(channel="a", text="from a"))
        b.push(_inbound(channel="b", text="from b"))
        a.push(_inbound(text="__STOP__"))
        b.push(_inbound(text="__STOP__"))
        await gw.run_until_idle()
        await gw.stop()

    asyncio.run(driver())
    assert set(seen_channels) >= {"a", "b"}


# ---------------------------------------------------------------------------
# Test 7: stop drains in-flight messages
# ---------------------------------------------------------------------------


def test_stop_drains_inflight() -> None:
    fake = _FakeAdapter()
    seen: list[str] = []

    async def handler(inbound: Inbound) -> str:
        await asyncio.sleep(0)  # yield once
        seen.append(inbound.text)
        return ""

    async def driver() -> None:
        gw = Gateway(adapters=[fake], handler=handler)
        await gw.start()
        for n in range(5):
            fake.push(_inbound(thread=f"T{n}", text=f"m{n}"))
        fake.push(_inbound(text="__STOP__"))
        await gw.run_until_idle()
        await gw.stop()

    asyncio.run(driver())
    assert sorted(seen) == [f"m{n}" for n in range(5)]


# ---------------------------------------------------------------------------
# Test 8: Inbound round-trips through JSON
# ---------------------------------------------------------------------------


def test_inbound_round_trips_through_json() -> None:
    inb = Inbound(
        channel="slack",
        thread_id="C123:ts.456",
        user_id="U1",
        text="hi",
        attachments=("file:///tmp/a.png",),
        received_at=1.0,
    )
    raw = json.dumps(asdict(inb), default=list)
    decoded = json.loads(raw)
    rebuilt = Inbound(
        channel=decoded["channel"],
        thread_id=decoded["thread_id"],
        user_id=decoded["user_id"],
        text=decoded["text"],
        attachments=tuple(decoded["attachments"]),
        received_at=decoded["received_at"],
    )
    assert rebuilt == inb
