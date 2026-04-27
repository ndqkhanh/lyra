"""``ChannelAdapter`` — the surface every gateway transport implements."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol, runtime_checkable

__all__ = [
    "ChannelAdapter",
    "GatewayError",
    "InboundMessage",
    "OutboundMessage",
]


class GatewayError(Exception):
    """Raised when an adapter fails to reach its transport."""


@dataclass(frozen=True)
class InboundMessage:
    platform: str
    channel_id: str
    author_id: str
    text: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboundMessage:
    platform: str
    channel_id: str
    text: str
    reply_to: str | None = None


@runtime_checkable
class ChannelAdapter(Protocol):
    """Each platform (telegram, slack, discord …) implements this.

    The gateway daemon calls :meth:`poll` on every tick and hands any
    replies back via :meth:`send`.
    """

    platform: str

    def connect(self) -> None: ...
    def poll(self) -> Iterable[InboundMessage]: ...
    def send(self, message: OutboundMessage) -> None: ...
    def disconnect(self) -> None: ...
