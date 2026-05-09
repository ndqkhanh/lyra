"""Contract tests for the gateway adapter layer."""
from __future__ import annotations

import pytest

from lyra_core.gateway import (
    ChannelAdapter,
    GatewayError,
    InboundMessage,
    OutboundMessage,
)
from lyra_core.gateway.adapters import TelegramAdapter


def test_channel_adapter_is_a_runtime_protocol() -> None:
    """Any class with the 4 required methods + a ``platform`` attr satisfies it."""
    assert isinstance(TelegramAdapter(token="t"), ChannelAdapter)


def test_telegram_requires_token() -> None:
    with pytest.raises(GatewayError, match="missing bot token"):
        TelegramAdapter(token="").connect()


def test_telegram_poll_before_connect_raises() -> None:
    a = TelegramAdapter(token="t")
    with pytest.raises(GatewayError, match="poll before connect"):
        list(a.poll())


def test_telegram_send_before_connect_raises() -> None:
    a = TelegramAdapter(token="t")
    with pytest.raises(GatewayError, match="send before connect"):
        a.send(OutboundMessage(platform="telegram", channel_id="c", text="hi"))


def test_telegram_rejects_wrong_platform_on_send() -> None:
    a = TelegramAdapter(token="t")
    a.connect()
    with pytest.raises(GatewayError, match="non-telegram"):
        a.send(OutboundMessage(platform="slack", channel_id="c", text="hi"))


def test_roundtrip_inbox_outbox_via_stub() -> None:
    a = TelegramAdapter(token="t")
    a.connect()
    a.deliver_test_message(
        InboundMessage(
            platform="telegram",
            channel_id="c1",
            author_id="u1",
            text="hello",
        )
    )
    received = list(a.poll())
    assert len(received) == 1
    assert received[0].text == "hello"

    a.send(OutboundMessage(platform="telegram", channel_id="c1", text="ack"))
    assert a._outbox[-1].text == "ack"
