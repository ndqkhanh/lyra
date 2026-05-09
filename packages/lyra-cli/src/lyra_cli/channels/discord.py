"""Wave-E Task 3: Discord channel adapter.

Same protocol shape as the Slack adapter (Task 2). The wire client
is injectable so unit tests never touch the live Discord API. The
production default lazily imports a thin wrapper around
:mod:`discord.py` (an opt-in dep via ``pip install lyra[discord]``).

Threading model
---------------

Discord identifies a thread by ``(channel_id, thread_id)`` —
collapsing them into ``"<channel>:<thread>"`` matches the Slack
convention so the gateway can key sessions on a single string.
A bare channel id (no ``:``) means a top-level channel post.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

from ._errors import (
    AdapterAuthError as DiscordAuthError,
    AdapterRateLimited as DiscordRateLimited,
    FeatureUnavailable,
)


__all__ = [
    "DiscordAdapter",
    "DiscordAuthError",
    "DiscordRateLimited",
    "FeatureUnavailable",
]


def _default_client_factory(*, token: str) -> Any:
    try:  # pragma: no cover — exercised in smoke
        import discord  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise FeatureUnavailable(
            "discord channel requires the optional dep; "
            "install with `pip install lyra[discord]`"
        ) from exc
    raise FeatureUnavailable(
        "discord adapter ships its own thin wrapper in v1.9.1; "
        "for now, inject your own via client_factory=…"
    )


@dataclass
class DiscordAdapter:
    token: str
    client_factory: Callable[..., Any] = _default_client_factory
    name: str = "discord"

    def __post_init__(self) -> None:
        if not self.token:
            raise FeatureUnavailable(
                "discord adapter requires a bot token; "
                "set $LYRA_DISCORD_TOKEN or pass token=…"
            )
        self._client: Any | None = None

    async def start(self) -> None:
        if self._client is None:
            self._client = self.client_factory(token=self.token)
        await self._client.login(self.token)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.close()

    async def send(self, *, thread_id: str, text: str) -> str:
        assert self._client is not None, "call start() first"
        channel_id = thread_id.split(":", 1)[0] if thread_id else ""
        try:
            resp = await self._client.send_message(
                channel_id=channel_id, content=text
            )
        except DiscordRateLimited as exc:
            await asyncio.sleep(max(exc.retry_after, 0))
            resp = await self._client.send_message(
                channel_id=channel_id, content=text
            )
        return f"discord:{channel_id}:{resp.get('id', '?')}"

    async def iter_inbound(self) -> AsyncIterator:
        from .base import Inbound

        assert self._client is not None, "call start() first"
        async for evt in self._client.stream_events():
            if evt.get("type") != "message":
                continue
            channel = str(evt.get("channel_id") or "")
            thread = str(evt.get("thread_id") or "")
            thread_id = f"{channel}:{thread}" if channel and thread else (channel or thread)
            attachments = tuple(
                a.get("url", "") for a in (evt.get("attachments") or []) if a
            )
            yield Inbound(
                channel="discord",
                thread_id=thread_id,
                user_id=str(evt.get("author_id") or ""),
                text=str(evt.get("content") or ""),
                attachments=tuple(a for a in attachments if a),
                received_at=float(evt.get("timestamp") or 0.0)
                if isinstance(evt.get("timestamp"), (int, float))
                else 0.0,
            )
