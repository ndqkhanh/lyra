"""Wave-E Task 4: Matrix channel adapter.

Same protocol shape as Slack / Discord. The wire client is
injectable so unit tests don't pull in :mod:`matrix-nio` (an opt-in
dep via ``pip install lyra[matrix]``).

Threading model
---------------

Matrix identifies a conversation by ``room_id``; replies inside a
thread are addressed by an ``m.relates_to`` event. We collapse both
into a single ``thread_id == room_id`` here — full thread-event
support arrives in a follow-up patch when we wire the relate-to
metadata back into the gateway dispatch.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

from ._errors import (
    AdapterAuthError as MatrixAuthError,
    AdapterRateLimited as MatrixRateLimited,
    FeatureUnavailable,
)


__all__ = [
    "FeatureUnavailable",
    "MatrixAdapter",
    "MatrixAuthError",
    "MatrixRateLimited",
]


def _default_client_factory(**_: Any) -> Any:  # pragma: no cover — smoke
    try:
        import nio  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise FeatureUnavailable(
            "matrix channel requires the optional dep; "
            "install with `pip install lyra[matrix]`"
        ) from exc
    raise FeatureUnavailable(
        "matrix adapter ships its production client wrapper in v1.9.1; "
        "for now, inject your own via client_factory=…"
    )


@dataclass
class MatrixAdapter:
    homeserver: str
    access_token: str
    client_factory: Callable[..., Any] = _default_client_factory
    name: str = "matrix"

    def __post_init__(self) -> None:
        if not self.access_token:
            raise FeatureUnavailable(
                "matrix adapter requires an access token; "
                "set $LYRA_MATRIX_TOKEN or pass access_token=…"
            )
        self._client: Any | None = None

    async def start(self) -> None:
        if self._client is None:
            self._client = self.client_factory(
                homeserver=self.homeserver, access_token=self.access_token
            )
        await self._client.login()

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.logout()

    async def send(self, *, thread_id: str, text: str) -> str:
        assert self._client is not None, "call start() first"
        content = {"msgtype": "m.text", "body": text}
        try:
            resp = await self._client.room_send(
                room_id=thread_id, content=content
            )
        except MatrixRateLimited as exc:
            await asyncio.sleep(max(exc.retry_after, 0))
            resp = await self._client.room_send(
                room_id=thread_id, content=content
            )
        return f"matrix:{thread_id}:{resp.get('event_id', '?')}"

    async def iter_inbound(self) -> AsyncIterator:
        from .base import Inbound

        assert self._client is not None, "call start() first"
        async for evt in self._client.stream_events():
            if evt.get("type") != "m.room.message":
                continue
            content = evt.get("content") or {}
            text = content.get("body", "")
            yield Inbound(
                channel="matrix",
                thread_id=str(evt.get("room_id") or ""),
                user_id=str(evt.get("sender") or ""),
                text=str(text),
                attachments=(),
                received_at=float(evt.get("origin_server_ts") or 0.0)
                if isinstance(evt.get("origin_server_ts"), (int, float))
                else 0.0,
            )
