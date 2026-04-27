"""Wave-E Task 6: contract tests for the 11 long-tail channel adapters.

Each adapter is verified to:
  (a) implement :class:`ChannelAdapter`,
  (b) name itself correctly,
  (c) round-trip a happy-path send through the injected http_client.

Per-vendor wire quirks (auth header shape, endpoint URL, payload
fields) are exercised in smoke tier with live tokens.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, List

import pytest

from lyra_cli.channels.base import ChannelAdapter, Inbound
from lyra_cli.channels.bluebubbles import BlueBubblesAdapter
from lyra_cli.channels.dingtalk import DingTalkAdapter
from lyra_cli.channels.feishu import FeishuAdapter
from lyra_cli.channels.homeassistant import HomeAssistantAdapter
from lyra_cli.channels.mattermost import MattermostAdapter
from lyra_cli.channels.openwebui import OpenWebUIAdapter
from lyra_cli.channels.qqbot import QQBotAdapter
from lyra_cli.channels.signal import SignalAdapter
from lyra_cli.channels.webhook import WebhookAdapter
from lyra_cli.channels.wecom import WeComAdapter
from lyra_cli.channels.whatsapp import WhatsAppAdapter


def _stub_http_factory():
    posted: list[dict[str, Any]] = []

    async def http(*, method: str, url: str, headers: dict[str, str], json: dict[str, Any]) -> dict[str, Any]:
        posted.append({"url": url, "json": dict(json)})
        return {"id": f"id-{len(posted)}"}

    return http, posted


@pytest.mark.parametrize(
    "factory,name",
    [
        (FeishuAdapter, "feishu"),
        (WeComAdapter, "wecom"),
        (MattermostAdapter, "mattermost"),
        (BlueBubblesAdapter, "bluebubbles"),
        (WhatsAppAdapter, "whatsapp"),
        (SignalAdapter, "signal"),
        (OpenWebUIAdapter, "openwebui"),
        (HomeAssistantAdapter, "homeassistant"),
        (QQBotAdapter, "qqbot"),
        (DingTalkAdapter, "dingtalk"),
        (WebhookAdapter, "webhook"),
    ],
)
def test_long_tail_adapter_satisfies_protocol_and_sends(factory, name) -> None:
    http, posted = _stub_http_factory()
    adapter = factory(
        endpoint="https://example.test/" + name,
        auth_header="Authorization: Bearer x",
        http_client=http,
        sender="lyra-bot",
    )
    assert isinstance(adapter, ChannelAdapter), f"{name} is not a ChannelAdapter"
    assert adapter.name == name

    async def driver() -> str:
        await adapter.start()
        msg_id = await adapter.send(thread_id="THREAD", text="hello " + name)
        await adapter.stop()
        return msg_id

    msg_id = asyncio.run(driver())
    assert msg_id.startswith(f"{name}:THREAD:")
    assert posted[0]["url"].endswith("/" + name)
    assert posted[0]["json"]["text"] == "hello " + name
    assert posted[0]["json"]["thread_id"] == "THREAD"
