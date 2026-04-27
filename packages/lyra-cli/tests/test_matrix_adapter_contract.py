"""Wave-E Task 4: Matrix channel adapter contract tests."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List

import pytest

from lyra_cli.channels.base import ChannelAdapter, Inbound
from lyra_cli.channels.matrix import (
    FeatureUnavailable,
    MatrixAdapter,
    MatrixAuthError,
    MatrixRateLimited,
)


@dataclass
class _FakeMatrixClient:
    homeserver: str = "https://matrix.example"
    access_token: str = "tok"
    auth_ok: bool = True
    rate_limit_first: bool = False
    posted: List[dict[str, Any]] = field(default_factory=list)
    inbound_events: list[dict[str, Any]] = field(default_factory=list)

    async def login(self) -> None:
        if not self.auth_ok:
            raise MatrixAuthError("login failed")

    async def logout(self) -> None:
        pass

    async def room_send(self, *, room_id: str, content: dict[str, Any]) -> dict[str, Any]:
        if self.rate_limit_first:
            self.rate_limit_first = False
            raise MatrixRateLimited(retry_after=0)
        self.posted.append({"room_id": room_id, "content": dict(content)})
        return {"event_id": f"$ev{len(self.posted)}"}

    def stream_events(self) -> AsyncIterator[dict[str, Any]]:
        async def _gen() -> AsyncIterator[dict[str, Any]]:
            for evt in list(self.inbound_events):
                yield evt

        return _gen()


def test_matrix_adapter_satisfies_protocol() -> None:
    fake = _FakeMatrixClient()
    adapter = MatrixAdapter(
        homeserver="https://matrix.example",
        access_token="tok",
        client_factory=lambda **_: fake,
    )
    assert isinstance(adapter, ChannelAdapter)
    assert adapter.name == "matrix"


def test_inbound_room_message_becomes_inbound() -> None:
    fake = _FakeMatrixClient(
        inbound_events=[
            {
                "type": "m.room.message",
                "room_id": "!room:matrix.example",
                "sender": "@alice:matrix.example",
                "content": {"body": "hello matrix", "msgtype": "m.text"},
            }
        ]
    )
    adapter = MatrixAdapter(
        homeserver="https://matrix.example",
        access_token="tok",
        client_factory=lambda **_: fake,
    )

    async def collect() -> list[Inbound]:
        await adapter.start()
        out = [inb async for inb in adapter.iter_inbound()]
        await adapter.stop()
        return out

    inbs = asyncio.run(collect())
    assert len(inbs) == 1
    assert inbs[0].text == "hello matrix"
    assert inbs[0].thread_id == "!room:matrix.example"
    assert inbs[0].user_id == "@alice:matrix.example"


def test_outbound_uses_room_send() -> None:
    fake = _FakeMatrixClient()
    adapter = MatrixAdapter(
        homeserver="https://matrix.example",
        access_token="tok",
        client_factory=lambda **_: fake,
    )

    async def driver() -> str:
        await adapter.start()
        return await adapter.send(thread_id="!room:matrix.example", text="hi")

    msg_id = asyncio.run(driver())
    assert msg_id
    assert fake.posted[0]["room_id"] == "!room:matrix.example"
    assert fake.posted[0]["content"]["body"] == "hi"


def test_rate_limit_retries_once_and_succeeds() -> None:
    fake = _FakeMatrixClient(rate_limit_first=True)
    adapter = MatrixAdapter(
        homeserver="https://matrix.example",
        access_token="tok",
        client_factory=lambda **_: fake,
    )

    async def driver() -> str:
        await adapter.start()
        return await adapter.send(thread_id="!room:matrix.example", text="retry me")

    msg_id = asyncio.run(driver())
    assert msg_id
    assert len(fake.posted) == 1


def test_missing_token_raises_feature_unavailable() -> None:
    with pytest.raises(FeatureUnavailable):
        MatrixAdapter(homeserver="https://matrix.example", access_token="")


def test_auth_failure_propagates_on_start() -> None:
    fake = _FakeMatrixClient(auth_ok=False)
    adapter = MatrixAdapter(
        homeserver="https://matrix.example",
        access_token="tok",
        client_factory=lambda **_: fake,
    )

    async def driver() -> None:
        await adapter.start()

    with pytest.raises(MatrixAuthError):
        asyncio.run(driver())
