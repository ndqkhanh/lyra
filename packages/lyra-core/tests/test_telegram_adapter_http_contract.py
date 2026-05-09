"""Contract tests for the **real** Telegram HTTP path (v1.7.3).

The v1.7.2 :class:`TelegramAdapter` was a pure stub that only honoured
in-memory inbox/outbox via ``deliver_test_message``. v1.7.3 flips it
to an httpx-backed Bot API client when an ``http`` transport is
injected, while keeping the stub path green for existing tests.

Tested invariants:

- ``TelegramAdapter(http=fake_client, token="…")`` uses the HTTP
  path — ``poll`` hits ``getUpdates``, ``send`` hits ``sendMessage``.
- Long-polling offset tracking advances past the max ``update_id``
  returned.
- ``send`` maps :class:`OutboundMessage` onto the Bot API payload
  (``chat_id``, ``text``, optional ``reply_to_message_id``).
- HTTP failures raise :class:`GatewayError` with the underlying
  response code, never leaking raw httpx types.
- ``FeatureUnavailable`` is raised if neither an injected client nor
  the ``httpx`` package is available when ``use_http=True``.
"""
from __future__ import annotations

import pytest

from lyra_core.gateway import (
    GatewayError,
    InboundMessage,
    OutboundMessage,
)
from lyra_core.gateway.adapters import TelegramAdapter
from lyra_core.lsp_backend import FeatureUnavailable


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {"ok": True, "result": []}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._next_response: _FakeResponse = _FakeResponse()

    def preload(self, resp: _FakeResponse) -> None:
        self._next_response = resp

    def post(self, url: str, *, json: dict | None = None, timeout: float = 30.0) -> _FakeResponse:
        self.calls.append({"url": url, "json": dict(json or {}), "timeout": timeout})
        return self._next_response


def _make_inbound_update(update_id: int, text: str, chat_id: int = 42) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "chat": {"id": chat_id},
            "from": {"id": 7, "username": "alice"},
            "text": text,
        },
    }


# --- HTTP poll -------------------------------------------------------- #


def test_poll_via_http_calls_get_updates_and_returns_inbound_messages() -> None:
    fake = _FakeHttpClient()
    fake.preload(
        _FakeResponse(
            payload={
                "ok": True,
                "result": [
                    _make_inbound_update(100, "hello"),
                    _make_inbound_update(101, "world"),
                ],
            }
        )
    )
    a = TelegramAdapter(token="t-secret", http=fake)
    a.connect()

    received = list(a.poll())

    # First call uses offset=None/0.
    assert any("getUpdates" in c["url"] for c in fake.calls)
    assert [m.text for m in received] == ["hello", "world"]
    assert all(m.platform == "telegram" for m in received)
    assert received[0].channel_id == "42"
    assert received[0].author_id == "7"


def test_poll_advances_offset_past_highest_update_id() -> None:
    fake = _FakeHttpClient()
    fake.preload(
        _FakeResponse(
            payload={
                "ok": True,
                "result": [
                    _make_inbound_update(500, "a"),
                    _make_inbound_update(501, "b"),
                ],
            }
        )
    )
    a = TelegramAdapter(token="t", http=fake)
    a.connect()
    list(a.poll())

    # Second poll with an empty result should use offset=502.
    fake.preload(_FakeResponse(payload={"ok": True, "result": []}))
    list(a.poll())

    second_call = fake.calls[-1]
    assert second_call["json"].get("offset") == 502


# --- HTTP send -------------------------------------------------------- #


def test_send_posts_sendMessage_payload() -> None:
    fake = _FakeHttpClient()
    fake.preload(_FakeResponse(payload={"ok": True, "result": {"message_id": 1}}))
    a = TelegramAdapter(token="xyz", http=fake)
    a.connect()

    a.send(OutboundMessage(platform="telegram", channel_id="42", text="hi", reply_to="9"))

    assert fake.calls, "send() must issue at least one HTTP call"
    call = fake.calls[-1]
    assert "sendMessage" in call["url"]
    assert "xyz" in call["url"]  # token embedded in the Bot API URL
    assert call["json"]["chat_id"] == 42
    assert call["json"]["text"] == "hi"
    assert call["json"]["reply_to_message_id"] == 9


def test_send_http_failure_raises_gateway_error() -> None:
    fake = _FakeHttpClient()
    fake.preload(_FakeResponse(status_code=500, payload={"ok": False, "error_code": 500}))
    a = TelegramAdapter(token="t", http=fake)
    a.connect()

    with pytest.raises(GatewayError):
        a.send(OutboundMessage(platform="telegram", channel_id="1", text="boom"))


def test_poll_http_failure_raises_gateway_error() -> None:
    fake = _FakeHttpClient()
    fake.preload(_FakeResponse(status_code=502, payload={"ok": False}))
    a = TelegramAdapter(token="t", http=fake)
    a.connect()

    with pytest.raises(GatewayError):
        list(a.poll())


# --- optional dep discipline ---------------------------------------- #


def test_use_http_without_httpx_raises_feature_unavailable(monkeypatch) -> None:
    """If the caller opts into ``use_http=True`` but doesn't inject an
    ``http`` client and ``httpx`` is unavailable, we must raise
    :class:`FeatureUnavailable` rather than silently regressing to the
    stub path."""
    import sys

    saved = sys.modules.get("httpx")
    sys.modules["httpx"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(FeatureUnavailable):
            TelegramAdapter(token="t", use_http=True).connect()
    finally:
        if saved is None:
            sys.modules.pop("httpx", None)
        else:
            sys.modules["httpx"] = saved
