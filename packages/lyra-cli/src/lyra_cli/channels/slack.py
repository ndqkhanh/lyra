"""Wave-E Task 2: Slack channel adapter.

The adapter speaks the same :class:`ChannelAdapter` protocol every
other channel uses. The wire client is injectable
(``client_factory=...``) so unit tests never need ``slack-sdk`` and
the import path stays cheap (``slack-sdk`` is opt-in via
``pip install lyra[slack]``).

Design notes
------------

* **Threading.** Slack identifies a thread by ``(channel_id,
  thread_ts)``. We collapse that into the adapter-level
  ``thread_id`` as ``"<channel>:<thread_ts>"`` so the gateway can
  key sessions on a single string.
* **Rate limits.** Slack returns ``429`` with a ``Retry-After`` header.
  The adapter catches :class:`SlackRateLimited` once and retries
  after the suggested delay; a second 429 propagates to the caller.
* **Auth.** ``auth_test`` is run on :meth:`start` so failures surface
  immediately instead of on the first ``send``.
* **No live transport.** The default ``client_factory`` lazily
  imports :mod:`slack_sdk`. Missing dep → :class:`FeatureUnavailable`
  with the exact install hint, never an opaque ``ImportError``.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Optional

from ._errors import (
    AdapterAuthError as SlackAuthError,
    AdapterRateLimited as SlackRateLimited,
    FeatureUnavailable,
)


__all__ = [
    "FeatureUnavailable",
    "SlackAdapter",
    "SlackAuthError",
    "SlackRateLimited",
]


def _default_client_factory(*, token: str) -> Any:
    """Lazy-import the real :mod:`slack_sdk` client.

    Raises :class:`FeatureUnavailable` when the optional dep is
    missing — exactly the behaviour the protocol contract requires.
    """
    try:
        from slack_sdk.web.async_client import AsyncWebClient  # type: ignore
    except ImportError as exc:  # pragma: no cover — exercised in smoke
        raise FeatureUnavailable(
            "slack channel requires the optional dep; "
            "install with `pip install lyra[slack]`"
        ) from exc
    return AsyncWebClient(token=token)


@dataclass
class SlackAdapter:
    """Slack adapter wrapping ``slack-sdk``'s async client."""

    token: str
    client_factory: Callable[..., Any] = _default_client_factory
    name: str = "slack"

    def __post_init__(self) -> None:
        if not self.token:
            raise FeatureUnavailable(
                "slack adapter requires a bot token; "
                "set $LYRA_SLACK_TOKEN or pass token=…"
            )
        self._client: Any | None = None
        self._auth: dict[str, Any] | None = None

    # ---- ChannelAdapter ----------------------------------------------

    async def start(self) -> None:
        if self._client is None:
            self._client = self.client_factory(token=self.token)
        if self._auth is None:
            try:
                self._auth = await self._client.auth_test()
            except SlackAuthError:
                raise
            except Exception as exc:  # noqa: BLE001 — opaque providers
                raise SlackAuthError(
                    f"slack auth failed: {type(exc).__name__}: {exc}"
                ) from exc

    async def stop(self) -> None:
        # ``slack-sdk``'s async client owns an aiohttp session that
        # ``__aexit__`` closes; we don't manage it directly here.
        # Subclasses can override to close transports they own.
        return None

    async def send(self, *, thread_id: str, text: str) -> str:
        assert self._client is not None, "call start() first"
        channel, thread_ts = self._split_thread_id(thread_id)
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        try:
            resp = await self._client.chat_postMessage(**payload)
        except SlackRateLimited as exc:
            await asyncio.sleep(max(exc.retry_after, 0))
            resp = await self._client.chat_postMessage(**payload)
        ts = str(resp.get("ts") or resp.get("message_ts") or "")
        return f"slack:{channel}:{ts}" if ts else f"slack:{channel}:?"

    async def iter_inbound(self) -> AsyncIterator:
        assert self._client is not None, "call start() first"
        async for evt in self._client.stream_events():
            if evt.get("type") != "message":
                continue
            inb = self._event_to_inbound(evt)
            if inb is not None:
                yield inb

    # ---- helpers ------------------------------------------------------

    @staticmethod
    def _split_thread_id(thread_id: str) -> tuple[str, str]:
        """Split ``"C123:1729820000.001"`` → ``("C123", "1729820000.001")``.

        A bare channel id (no ``:``) is treated as a top-level
        channel post (no ``thread_ts``).
        """
        if ":" in thread_id:
            channel, ts = thread_id.split(":", 1)
            return channel, ts
        return thread_id, ""

    @staticmethod
    def _event_to_inbound(evt: dict[str, Any]):
        from .base import Inbound

        channel = evt.get("channel") or ""
        ts = evt.get("thread_ts") or evt.get("ts") or ""
        thread_id = f"{channel}:{ts}" if channel and ts else channel or ts
        attachments = tuple(
            f.get("url_private", "") for f in (evt.get("files") or []) if f
        )
        try:
            received_at = float(evt.get("event_ts") or evt.get("ts") or 0.0)
        except (TypeError, ValueError):
            received_at = 0.0
        return Inbound(
            channel="slack",
            thread_id=thread_id,
            user_id=str(evt.get("user") or ""),
            text=str(evt.get("text") or ""),
            attachments=tuple(a for a in attachments if a),
            received_at=received_at,
        )
