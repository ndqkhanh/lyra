"""Wave-E Task 5b: SMS channel adapter.

Backend-agnostic: any object that implements :class:`SmsBackend`
(``login``, ``send``, ``stream_inbound``) plugs in. Two production
backends are planned (``TwilioBackend`` + ``VonageBackend``); both
get full smoke coverage in v1.9.1 once the live integration tests
are gated on ``LYRA_RUN_SMOKE=1`` + per-vendor env vars.

Threading model
---------------

The remote phone number is the thread id. Outbound replies are sent
to ``thread_id`` directly; inbound surfaces ``from`` as both
``thread_id`` and ``user_id``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from ._errors import (
    AdapterAuthError as SmsAuthError,
    FeatureUnavailable,
)


__all__ = [
    "FeatureUnavailable",
    "SmsAdapter",
    "SmsAuthError",
    "SmsBackend",
]


@runtime_checkable
class SmsBackend(Protocol):
    """Tiny surface every SMS provider backend implements."""

    name: str

    async def login(self) -> None: ...

    async def send(self, *, to: str, body: str) -> str: ...

    def stream_inbound(self) -> AsyncIterator[dict[str, Any]]: ...


@dataclass
class SmsAdapter:
    backend: SmsBackend
    sender: str
    name: str = "sms"

    def __post_init__(self) -> None:
        if not self.sender:
            raise FeatureUnavailable(
                "sms adapter requires a sender phone number; "
                "set $LYRA_SMS_SENDER or pass sender=…"
            )

    async def start(self) -> None:
        await self.backend.login()

    async def stop(self) -> None:
        # Backends that need explicit teardown override this.
        return None

    async def send(self, *, thread_id: str, text: str) -> str:
        if not thread_id:
            raise FeatureUnavailable("sms adapter: thread_id (recipient) required")
        msg_id = await self.backend.send(to=thread_id, body=text)
        return f"sms:{thread_id}:{msg_id}"

    async def iter_inbound(self) -> AsyncIterator:
        from .base import Inbound

        async for evt in self.backend.stream_inbound():
            sender = str(evt.get("from") or "")
            yield Inbound(
                channel="sms",
                thread_id=sender,
                user_id=sender,
                text=str(evt.get("body") or ""),
                attachments=(),
                received_at=float(evt.get("timestamp") or 0.0)
                if isinstance(evt.get("timestamp"), (int, float))
                else 0.0,
            )
