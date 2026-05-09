"""Wave-E Task 5a: Email channel adapter contract tests."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List

import pytest

from lyra_cli.channels.base import ChannelAdapter, Inbound
from lyra_cli.channels.email import (
    EmailAdapter,
    EmailAuthError,
    FeatureUnavailable,
)


@dataclass
class _FakeMailClient:
    user: str = "lyra@example.com"
    password: str = "pw"
    auth_ok: bool = True
    inbox: list[dict[str, Any]] = field(default_factory=list)
    sent: List[dict[str, Any]] = field(default_factory=list)

    async def login(self) -> None:
        if not self.auth_ok:
            raise EmailAuthError("imap login failed")

    async def logout(self) -> None:
        pass

    async def fetch_unseen(self) -> AsyncIterator[dict[str, Any]]:
        async def _gen() -> AsyncIterator[dict[str, Any]]:
            for msg in list(self.inbox):
                yield msg

        return _gen()

    async def send_mail(self, *, to: str, subject: str, body: str, in_reply_to: str | None) -> str:
        self.sent.append(
            {"to": to, "subject": subject, "body": body, "in_reply_to": in_reply_to}
        )
        return f"<msg-{len(self.sent)}@lyra>"


def test_email_adapter_satisfies_protocol() -> None:
    fake = _FakeMailClient()
    adapter = EmailAdapter(
        user="lyra@example.com",
        password="pw",
        client_factory=lambda **_: fake,
    )
    assert isinstance(adapter, ChannelAdapter)
    assert adapter.name == "email"


def test_inbound_email_becomes_inbound() -> None:
    fake = _FakeMailClient(
        inbox=[
            {
                "from": "alice@example.com",
                "to": "lyra@example.com",
                "message_id": "<msg-42@example>",
                "subject": "hello",
                "body": "first email body",
                "received_at": 1.0,
            }
        ]
    )
    adapter = EmailAdapter(
        user="lyra@example.com",
        password="pw",
        client_factory=lambda **_: fake,
    )

    async def collect() -> list[Inbound]:
        await adapter.start()
        out = [inb async for inb in adapter.iter_inbound()]
        await adapter.stop()
        return out

    inbs = asyncio.run(collect())
    assert len(inbs) == 1
    assert inbs[0].text.startswith("first email")
    assert inbs[0].thread_id == "<msg-42@example>"
    assert inbs[0].user_id == "alice@example.com"


def test_outbound_send_uses_in_reply_to() -> None:
    fake = _FakeMailClient()
    adapter = EmailAdapter(
        user="lyra@example.com",
        password="pw",
        default_recipient="alice@example.com",
        client_factory=lambda **_: fake,
    )

    async def driver() -> str:
        await adapter.start()
        return await adapter.send(
            thread_id="<msg-42@example>", text="reply body"
        )

    msg_id = asyncio.run(driver())
    assert msg_id
    sent = fake.sent[0]
    assert sent["to"] == "alice@example.com"
    assert sent["in_reply_to"] == "<msg-42@example>"
    assert sent["body"] == "reply body"


def test_missing_credentials_raises_feature_unavailable() -> None:
    with pytest.raises(FeatureUnavailable):
        EmailAdapter(user="", password="")


def test_auth_failure_propagates_on_start() -> None:
    fake = _FakeMailClient(auth_ok=False)
    adapter = EmailAdapter(
        user="lyra@example.com",
        password="bad",
        client_factory=lambda **_: fake,
    )

    async def driver() -> None:
        await adapter.start()

    with pytest.raises(EmailAuthError):
        asyncio.run(driver())
