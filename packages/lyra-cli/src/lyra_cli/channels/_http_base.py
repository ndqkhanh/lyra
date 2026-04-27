"""Wave-E Task 6: shared HTTP-shaped adapter base.

Eleven of Lyra's long-tail channels (Feishu/Lark, WeCom,
Mattermost, BlueBubbles, WhatsApp, Signal-cli, OpenWebUI,
HomeAssistant, QQBot, DingTalk, Generic Webhook) all expose the
same shape:

* a JSON-over-HTTP ``send`` endpoint (URL + auth header);
* a polled or webhook-driven ``stream_inbound``;
* a thread / room id baked into the destination URL or payload.

Rather than copy-paste a near-identical adapter per provider, we
ship one :class:`HttpChannelAdapter` plus a per-provider config and
let each adapter file pick its name + endpoint. Tests live as one
contract per adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

from ._errors import (
    AdapterAuthError as HttpAuthError,
    AdapterRateLimited as HttpRateLimited,
    FeatureUnavailable,
)


HttpClient = Callable[..., Awaitable[Any]]


@dataclass
class HttpChannelAdapter:
    """Base for every JSON-over-HTTP channel adapter.

    The ``http_client`` callable is what tests inject — production
    callers wire it through a vendor-specific helper that maps
    Lyra's payload to the provider's wire format.
    """

    name: str
    endpoint: str
    auth_header: str = ""
    http_client: HttpClient | None = None
    inbound_source: Callable[[], AsyncIterator[dict[str, Any]]] | None = None
    sender: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.endpoint:
            raise FeatureUnavailable(
                f"{self.name} channel requires an endpoint URL"
            )
        if self.http_client is None:
            raise FeatureUnavailable(
                f"{self.name} channel requires an http_client; "
                "inject one (production wires the vendor SDK)"
            )

    async def start(self) -> None:
        # HTTP adapters don't keep a long-lived connection.
        return None

    async def stop(self) -> None:
        return None

    async def send(self, *, thread_id: str, text: str) -> str:
        payload = {"thread_id": thread_id, "text": text, "from": self.sender}
        try:
            resp = await self.http_client(
                method="POST",
                url=self.endpoint,
                headers=self._headers(),
                json=payload,
            )
        except HttpRateLimited:
            raise
        except HttpAuthError:
            raise
        msg_id = ""
        if isinstance(resp, dict):
            msg_id = str(resp.get("message_id") or resp.get("id") or "")
        return f"{self.name}:{thread_id}:{msg_id or '?'}"

    async def iter_inbound(self) -> AsyncIterator:
        from .base import Inbound

        if self.inbound_source is None:
            return
        async for evt in self.inbound_source():
            sender = str(evt.get("from") or evt.get("user") or "")
            yield Inbound(
                channel=self.name,
                thread_id=str(evt.get("thread_id") or sender),
                user_id=sender,
                text=str(evt.get("text") or evt.get("body") or ""),
                attachments=tuple(evt.get("attachments") or ()),
                received_at=float(evt.get("timestamp") or 0.0)
                if isinstance(evt.get("timestamp"), (int, float))
                else 0.0,
            )

    def _headers(self) -> dict[str, str]:
        if not self.auth_header:
            return {}
        if ":" in self.auth_header:
            k, v = self.auth_header.split(":", 1)
            return {k.strip(): v.strip()}
        return {"Authorization": self.auth_header}


__all__ = [
    "HttpAuthError",
    "HttpChannelAdapter",
    "HttpRateLimited",
]
