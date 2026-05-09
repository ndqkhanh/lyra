"""Wave-E Task 3: Discord channel adapter contract tests."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List

import pytest

from lyra_cli.channels.base import ChannelAdapter, Inbound
from lyra_cli.channels.discord import (
    DiscordAdapter,
    DiscordAuthError,
    DiscordRateLimited,
    FeatureUnavailable,
)


@dataclass
class _FakeDiscordClient:
    token: str = "fake-token"
    auth_ok: bool = True
    rate_limit_first: bool = False
    posted: List[dict[str, Any]] = field(default_factory=list)
    inbound_events: list[dict[str, Any]] = field(default_factory=list)

    async def login(self, token: str) -> None:
        if not self.auth_ok:
            raise DiscordAuthError("login failed")

    async def close(self) -> None:
        pass

    async def send_message(self, *, channel_id: str, content: str) -> dict[str, Any]:
        if self.rate_limit_first:
            self.rate_limit_first = False
            raise DiscordRateLimited(retry_after=0)
        self.posted.append({"channel_id": channel_id, "content": content})
        return {"id": f"msg-{len(self.posted)}"}

    def stream_events(self) -> AsyncIterator[dict[str, Any]]:
        async def _gen() -> AsyncIterator[dict[str, Any]]:
            for evt in list(self.inbound_events):
                yield evt

        return _gen()


def test_discord_adapter_satisfies_protocol() -> None:
    fake = _FakeDiscordClient()
    adapter = DiscordAdapter(token="fake", client_factory=lambda **_: fake)
    assert isinstance(adapter, ChannelAdapter)
    assert adapter.name == "discord"


def test_inbound_events_become_inbound() -> None:
    fake = _FakeDiscordClient(
        inbound_events=[
            {
                "type": "message",
                "channel_id": "C1",
                "thread_id": "TH1",
                "author_id": "U1",
                "content": "hi from discord",
                "attachments": [{"url": "https://cdn.discord/img.png"}],
            }
        ]
    )
    adapter = DiscordAdapter(token="x", client_factory=lambda **_: fake)

    async def collect() -> list[Inbound]:
        await adapter.start()
        out = [inb async for inb in adapter.iter_inbound()]
        await adapter.stop()
        return out

    inbs = asyncio.run(collect())
    assert len(inbs) == 1
    assert inbs[0].text == "hi from discord"
    assert inbs[0].thread_id == "C1:TH1"
    assert inbs[0].attachments == ("https://cdn.discord/img.png",)


def test_outbound_uses_channel_id() -> None:
    fake = _FakeDiscordClient()
    adapter = DiscordAdapter(token="x", client_factory=lambda **_: fake)

    async def driver() -> str:
        await adapter.start()
        msg_id = await adapter.send(thread_id="C1:TH1", text="hello")
        await adapter.stop()
        return msg_id

    msg_id = asyncio.run(driver())
    assert msg_id
    assert fake.posted[0]["channel_id"] == "C1"
    assert fake.posted[0]["content"] == "hello"


def test_rate_limit_retries_once_and_succeeds() -> None:
    fake = _FakeDiscordClient(rate_limit_first=True)
    adapter = DiscordAdapter(token="x", client_factory=lambda **_: fake)

    async def driver() -> str:
        await adapter.start()
        return await adapter.send(thread_id="C1", text="hi")

    msg_id = asyncio.run(driver())
    assert msg_id
    assert len(fake.posted) == 1


def test_missing_token_raises_feature_unavailable() -> None:
    with pytest.raises(FeatureUnavailable):
        DiscordAdapter(token="")


def test_auth_failure_propagates_on_start() -> None:
    fake = _FakeDiscordClient(auth_ok=False)
    adapter = DiscordAdapter(token="bad", client_factory=lambda **_: fake)

    async def driver() -> None:
        await adapter.start()

    with pytest.raises(DiscordAuthError):
        asyncio.run(driver())
