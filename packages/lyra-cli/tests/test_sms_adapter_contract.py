"""Wave-E Task 5b: SMS channel adapter contract tests."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List

import pytest

from lyra_cli.channels.base import ChannelAdapter, Inbound
from lyra_cli.channels.sms import (
    FeatureUnavailable,
    SmsAdapter,
    SmsAuthError,
    SmsBackend,
)


@dataclass
class _FakeTwilio:
    name: str = "twilio"
    auth_ok: bool = True
    sent: List[dict[str, Any]] = field(default_factory=list)
    inbound: list[dict[str, Any]] = field(default_factory=list)

    async def login(self) -> None:
        if not self.auth_ok:
            raise SmsAuthError("twilio auth failed")

    async def send(self, *, to: str, body: str) -> str:
        self.sent.append({"to": to, "body": body})
        return f"twilio-msg-{len(self.sent)}"

    def stream_inbound(self) -> AsyncIterator[dict[str, Any]]:
        async def _gen() -> AsyncIterator[dict[str, Any]]:
            for evt in list(self.inbound):
                yield evt

        return _gen()


def test_sms_adapter_satisfies_protocol() -> None:
    fake = _FakeTwilio()
    adapter = SmsAdapter(backend=fake, sender="+15555550123")
    assert isinstance(adapter, ChannelAdapter)
    assert adapter.name == "sms"


def test_inbound_sms_becomes_inbound() -> None:
    fake = _FakeTwilio(
        inbound=[
            {
                "from": "+15555550199",
                "to": "+15555550123",
                "body": "hi sms",
                "message_id": "tw-1",
                "timestamp": 1.0,
            }
        ]
    )
    adapter = SmsAdapter(backend=fake, sender="+15555550123")

    async def collect() -> list[Inbound]:
        await adapter.start()
        out = [inb async for inb in adapter.iter_inbound()]
        await adapter.stop()
        return out

    inbs = asyncio.run(collect())
    assert len(inbs) == 1
    assert inbs[0].text == "hi sms"
    assert inbs[0].thread_id == "+15555550199"
    assert inbs[0].user_id == "+15555550199"


def test_outbound_sms_uses_thread_id_as_recipient() -> None:
    fake = _FakeTwilio()
    adapter = SmsAdapter(backend=fake, sender="+15555550123")

    async def driver() -> str:
        await adapter.start()
        return await adapter.send(thread_id="+15555550199", text="hi back")

    msg_id = asyncio.run(driver())
    assert msg_id
    assert fake.sent[0]["to"] == "+15555550199"
    assert fake.sent[0]["body"] == "hi back"


def test_sms_backend_protocol() -> None:
    fake = _FakeTwilio()
    assert isinstance(fake, SmsBackend)


def test_missing_sender_raises_feature_unavailable() -> None:
    fake = _FakeTwilio()
    with pytest.raises(FeatureUnavailable):
        SmsAdapter(backend=fake, sender="")
