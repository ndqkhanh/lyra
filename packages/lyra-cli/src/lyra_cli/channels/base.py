"""Wave-E Task 1: channel adapter protocol + :class:`Gateway`.

The gateway owns N adapters, fans every adapter's ``iter_inbound``
asynchronously into a single in-memory queue, dispatches each message
to a per-(channel, thread_id) agent-loop session via the user-provided
``handler`` callback, and pushes the handler's return string back as
an outbound reply on the same adapter.

Why a single queue + N background tasks instead of "one task per
session" or "one task per adapter"?

* The handler is what owns session state — it's a callback the REPL /
  daemon supplies. The gateway just needs to make sure inbound
  messages reach the handler in arrival order *per thread*. A single
  consumer loop reading from a single queue gives us that ordering
  guarantee while keeping the per-adapter producers fully concurrent.
* Adapters that raise mid-iteration are demoted to "no more inbound";
  the gateway logs the failure (HIR ``channel.adapter_error``) and
  the other adapters keep running. Telemetry must never break the
  caller's cascade — same contract as :class:`LifecycleBus` (Wave-D
  Task 11).

Wire transports and credential handling stay in the per-adapter
files; this module is intentionally network-free so the unit tier
runs in <100ms with zero side effects.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    List,
    Protocol,
    Sequence,
    runtime_checkable,
)

from lyra_core.hir.events import emit


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Inbound:
    """One inbound message a gateway adapter surfaces.

    All fields are JSON-serialisable so ``/replay`` (Task 12) can
    persist the inbound stream verbatim. ``attachments`` is a tuple
    of opaque URI strings — each adapter decides whether it stores
    files locally (e.g., Email) or hands back a remote URL (Slack
    file share).
    """

    channel: str
    thread_id: str
    user_id: str
    text: str
    attachments: tuple[str, ...] = ()
    received_at: float = 0.0


@dataclass(frozen=True)
class Outbound:
    """One outbound reply a gateway pushed to an adapter.

    Adapters return a string message id from :meth:`ChannelAdapter.send`;
    the gateway records the id alongside the outbound payload for
    auditing. Mostly useful for tests that want to assert "we replied
    to thread T1 with this text".
    """

    channel: str
    thread_id: str
    text: str
    message_id: str | None = None


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ChannelAdapter(Protocol):
    """Every per-channel adapter implements this surface.

    Methods are coroutine-friendly so adapters can use any of the
    common async client libraries (``slack-sdk``'s
    ``AsyncWebClient``, ``discord.py``'s gateway client,
    ``matrix-nio``'s async API). Synchronous adapters wrap their
    internals with ``asyncio.to_thread``; the gateway never assumes a
    specific transport.
    """

    name: str

    async def start(self) -> None:
        """Open whatever connection the adapter needs."""

    async def stop(self) -> None:
        """Cleanly close the connection (must be idempotent)."""

    async def send(self, *, thread_id: str, text: str) -> str:
        """Push ``text`` to ``thread_id``; return the provider's message id."""

    def iter_inbound(self) -> AsyncIterator[Inbound]:
        """Stream :class:`Inbound` messages until the adapter shuts down."""


GatewayHandler = Callable[[Inbound], Awaitable[str]]
"""User-supplied callback the gateway invokes for every inbound message.

The handler returns the *outbound text*; the gateway sends it back on
the same adapter / thread. Returning an empty string skips the reply
(useful for fire-and-forget side-effects).
"""


# ---------------------------------------------------------------------------
# The gateway
# ---------------------------------------------------------------------------


class Gateway:
    """Multiplex N :class:`ChannelAdapter`s into one handler loop."""

    def __init__(
        self,
        *,
        adapters: Sequence[ChannelAdapter],
        handler: GatewayHandler,
        poll_interval: float = 0.005,
    ) -> None:
        self.adapters: Sequence[ChannelAdapter] = adapters
        self.handler: GatewayHandler = handler
        # Sentinel sleep between idle ticks of ``run_until_idle`` so
        # we don't busy-loop on an empty queue.
        self.poll_interval: float = poll_interval

        # asyncio primitives are loop-bound; on Python 3.9 we MUST
        # create them after the loop is running, so they're filled in
        # by ``start()`` instead of ``__init__``.
        self._queue: asyncio.Queue[Inbound] | None = None
        self._producers: List[asyncio.Task[None]] = []
        self._consumer: asyncio.Task[None] | None = None
        self._started: bool = False
        self._stopping: bool = False
        self._outbound: List[Outbound] = []

    # ---- lifecycle ----------------------------------------------------

    async def start(self) -> None:
        """Start every adapter and wire its ``iter_inbound`` to the queue."""
        if self._started:
            return
        if self._queue is None:
            self._queue = asyncio.Queue()
        for adapter in self.adapters:
            try:
                await adapter.start()
            except Exception as exc:  # noqa: BLE001 — telemetry, never crash
                emit(
                    "channel.adapter_error",
                    channel=getattr(adapter, "name", "?"),
                    where="start",
                    error=f"{type(exc).__name__}: {exc}",
                )
                continue
            self._producers.append(
                asyncio.create_task(self._produce(adapter))
            )
        self._consumer = asyncio.create_task(self._consume())
        self._started = True

    async def stop(self) -> None:
        """Stop all adapters and the consumer loop. Idempotent."""
        if not self._started or self._stopping:
            return
        self._stopping = True
        for adapter in self.adapters:
            try:
                await adapter.stop()
            except Exception as exc:  # noqa: BLE001
                emit(
                    "channel.adapter_error",
                    channel=getattr(adapter, "name", "?"),
                    where="stop",
                    error=f"{type(exc).__name__}: {exc}",
                )
        # Cancel producers first, then drain the consumer.
        for task in self._producers:
            task.cancel()
        for task in self._producers:
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._consumer is not None:
            self._consumer.cancel()
            try:
                await self._consumer
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self._started = False

    async def run_until_idle(self) -> None:
        """Wait until every queued inbound has been handled.

        Used in tests so the asserts can run after the consumer has
        actually processed the producers' messages. Production callers
        normally call :meth:`run_forever` instead.
        """
        if self._queue is None:
            return
        # First wait for every producer to finish (i.e. iter_inbound
        # raised StopAsyncIteration). Producers raise the
        # ``__STOP__`` sentinel as a graceful end signal.
        while self._producers and any(not t.done() for t in self._producers):
            await asyncio.sleep(self.poll_interval)
        # Then drain the queue (``join`` waits for ``task_done`` on
        # every put so we know the consumer has finished, not just
        # that the queue is empty).
        await self._queue.join()

    async def run_forever(self) -> None:
        """Block until ``stop()`` is called from another task."""
        if self._consumer is None:
            await self.start()
        while self._started and not self._stopping:
            await asyncio.sleep(0.05)

    # ---- read --------------------------------------------------------

    @property
    def outbound(self) -> List[Outbound]:
        """Read-only view of every outbound the consumer pushed."""
        return list(self._outbound)

    # ---- internals ---------------------------------------------------

    async def _produce(self, adapter: ChannelAdapter) -> None:
        assert self._queue is not None  # set by start()
        try:
            async for inbound in adapter.iter_inbound():
                await self._queue.put(inbound)
        except Exception as exc:  # noqa: BLE001
            emit(
                "channel.adapter_error",
                channel=getattr(adapter, "name", "?"),
                where="iter_inbound",
                error=f"{type(exc).__name__}: {exc}",
            )

    async def _consume(self) -> None:
        assert self._queue is not None  # set by start()
        while True:
            inbound = await self._queue.get()
            try:
                emit(
                    "channel.inbound",
                    channel=inbound.channel,
                    thread_id=inbound.thread_id,
                    user_id=inbound.user_id,
                    text_len=len(inbound.text),
                    attachments=len(inbound.attachments),
                )
                reply: str = ""
                try:
                    reply = await self.handler(inbound)
                except Exception as exc:  # noqa: BLE001
                    emit(
                        "channel.handler_error",
                        channel=inbound.channel,
                        thread_id=inbound.thread_id,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                if reply:
                    adapter = self._adapter_for(inbound.channel)
                    if adapter is not None:
                        try:
                            msg_id = await adapter.send(
                                thread_id=inbound.thread_id,
                                text=reply,
                            )
                            self._outbound.append(
                                Outbound(
                                    channel=inbound.channel,
                                    thread_id=inbound.thread_id,
                                    text=reply,
                                    message_id=msg_id,
                                )
                            )
                        except Exception as exc:  # noqa: BLE001
                            emit(
                                "channel.send_error",
                                channel=inbound.channel,
                                thread_id=inbound.thread_id,
                                error=f"{type(exc).__name__}: {exc}",
                            )
            finally:
                self._queue.task_done()

    def _adapter_for(self, channel: str) -> ChannelAdapter | None:
        for adapter in self.adapters:
            if getattr(adapter, "name", None) == channel:
                return adapter
        return None


__all__ = [
    "ChannelAdapter",
    "Gateway",
    "GatewayHandler",
    "Inbound",
    "Outbound",
]
