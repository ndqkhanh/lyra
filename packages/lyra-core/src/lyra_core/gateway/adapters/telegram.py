"""Telegram adapter — stub + real HTTP path.

v1.7.2 shipped the pure in-memory stub (driven by
``deliver_test_message``). v1.7.3 adds the **real Bot API** path: when
``http`` is injected (or ``use_http=True`` is passed and ``httpx`` is
importable) the adapter calls ``getUpdates`` / ``sendMessage`` against
``https://api.telegram.org/bot<token>``.

The stub path remains the default — existing tests continue to pass —
and is used whenever neither ``http`` nor ``use_http=True`` is set.
This preserves deterministic unit tests while enabling real deployment.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from ...lsp_backend.errors import FeatureUnavailable
from ..adapter import ChannelAdapter, GatewayError, InboundMessage, OutboundMessage

__all__ = ["TelegramAdapter"]


_API_BASE = "https://api.telegram.org"


@dataclass
class TelegramAdapter(ChannelAdapter):
    token: str
    home_channel: str | None = None
    platform: str = "telegram"
    http: Any | None = None
    use_http: bool = False
    long_poll_timeout: int = 30
    _inbox: deque[InboundMessage] = field(default_factory=deque)
    _outbox: list[OutboundMessage] = field(default_factory=list)
    _connected: bool = False
    _offset: int | None = None

    # ---- lifecycle ---------------------------------------------------

    def connect(self) -> None:
        if not self.token:
            raise GatewayError("telegram: missing bot token")

        if self.http is None and self.use_http:
            try:
                import httpx  # type: ignore[import-not-found]
            except Exception as exc:
                raise FeatureUnavailable(
                    "TelegramAdapter(use_http=True) requires httpx. "
                    "Install with `pip install 'lyra[web]'` or inject "
                    "an ``http`` client."
                ) from exc
            self.http = httpx.Client(timeout=self.long_poll_timeout + 5)

        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        # Leave self.http alone — the caller owns it when injected.

    # ---- inbox / outbox ---------------------------------------------

    def poll(self) -> Iterable[InboundMessage]:
        if not self._connected:
            raise GatewayError("telegram: poll before connect")

        if self.http is not None:
            yield from self._poll_http()
            return

        while self._inbox:
            yield self._inbox.popleft()

    def send(self, message: OutboundMessage) -> None:
        if not self._connected:
            raise GatewayError("telegram: send before connect")
        if message.platform != self.platform:
            raise GatewayError(
                f"telegram: refusing to send non-telegram message "
                f"({message.platform})"
            )

        if self.http is not None:
            self._send_http(message)
        else:
            self._outbox.append(message)

    def deliver_test_message(self, msg: InboundMessage) -> None:
        """Test helper — enqueue an inbound message as if from the wire."""
        self._inbox.append(msg)

    # ---- HTTP path ---------------------------------------------------

    def _poll_http(self) -> Iterable[InboundMessage]:
        payload: dict[str, Any] = {"timeout": self.long_poll_timeout}
        if self._offset is not None:
            payload["offset"] = self._offset

        try:
            resp = self.http.post(  # type: ignore[union-attr]
                f"{_API_BASE}/bot{self.token}/getUpdates",
                json=payload,
                timeout=self.long_poll_timeout + 5,
            )
        except Exception as exc:
            raise GatewayError(f"telegram getUpdates transport error: {exc}") from exc

        status = int(getattr(resp, "status_code", 0))
        if status >= 400:
            raise GatewayError(f"telegram getUpdates http {status}")

        body = resp.json() if hasattr(resp, "json") else {}
        if not body.get("ok", False):
            raise GatewayError(
                f"telegram getUpdates not ok: {body.get('description') or body}"
            )

        updates = body.get("result") or []
        max_update_id = self._offset - 1 if self._offset is not None else -1
        for upd in updates:
            uid = int(upd.get("update_id", 0))
            max_update_id = max(max_update_id, uid)
            msg = upd.get("message") or upd.get("edited_message")
            if not msg:
                continue
            chat = msg.get("chat") or {}
            sender = msg.get("from") or {}
            yield InboundMessage(
                platform=self.platform,
                channel_id=str(chat.get("id", "")),
                author_id=str(sender.get("id", "")),
                text=str(msg.get("text", "")),
                raw={"update": upd},
            )

        if updates:
            self._offset = max_update_id + 1

    def _send_http(self, message: OutboundMessage) -> None:
        payload: dict[str, Any] = {
            "chat_id": _maybe_int(message.channel_id),
            "text": message.text,
        }
        if message.reply_to is not None:
            payload["reply_to_message_id"] = _maybe_int(message.reply_to)

        try:
            resp = self.http.post(  # type: ignore[union-attr]
                f"{_API_BASE}/bot{self.token}/sendMessage",
                json=payload,
                timeout=self.long_poll_timeout + 5,
            )
        except Exception as exc:
            raise GatewayError(f"telegram sendMessage transport error: {exc}") from exc

        status = int(getattr(resp, "status_code", 0))
        if status >= 400:
            raise GatewayError(f"telegram sendMessage http {status}")

        body = resp.json() if hasattr(resp, "json") else {}
        if not body.get("ok", False):
            raise GatewayError(
                f"telegram sendMessage not ok: {body.get('description') or body}"
            )


def _maybe_int(raw: str | int | None) -> Any:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    try:
        return int(raw)
    except (TypeError, ValueError):
        return raw
