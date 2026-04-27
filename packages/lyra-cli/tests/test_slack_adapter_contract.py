"""Wave-E Task 2: contract tests for the Slack channel adapter.

The unit tier never touches the live Slack API: we inject a fake
client (``client_factory=...``) that records every outbound call and
emits inbound events from a list. Smoke tests against a real
Slack workspace gate on ``LYRA_SLACK_TOKEN`` + ``LYRA_RUN_SMOKE=1``
(not exercised here).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List

import pytest

from lyra_cli.channels.base import ChannelAdapter, Inbound
from lyra_cli.channels.slack import (
    FeatureUnavailable,
    SlackAdapter,
    SlackAuthError,
)


# ---------------------------------------------------------------------------
# Fake Slack client
# ---------------------------------------------------------------------------


@dataclass
class _FakeSlackClient:
    token: str = "xoxb-test"
    auth_ok: bool = True
    rate_limit_first: bool = False
    posted: List[dict[str, Any]] = field(default_factory=list)
    inbound_events: list[dict[str, Any]] = field(default_factory=list)

    async def auth_test(self) -> dict[str, Any]:
        if not self.auth_ok:
            raise SlackAuthError("invalid token")
        return {"ok": True, "user_id": "U_BOT", "team_id": "T_TEAM"}

    async def chat_postMessage(self, **payload: Any) -> dict[str, Any]:
        if self.rate_limit_first:
            self.rate_limit_first = False
            from lyra_cli.channels.slack import SlackRateLimited

            raise SlackRateLimited(retry_after=0)
        self.posted.append(dict(payload))
        return {"ok": True, "ts": f"ts.{len(self.posted)}"}

    def stream_events(self) -> "AsyncIterator[dict[str, Any]]":
        async def _gen() -> "AsyncIterator[dict[str, Any]]":
            for evt in list(self.inbound_events):
                yield evt

        return _gen()


# ---------------------------------------------------------------------------
# Test 1: implements ChannelAdapter
# ---------------------------------------------------------------------------


def test_slack_adapter_satisfies_protocol() -> None:
    fake = _FakeSlackClient()
    adapter = SlackAdapter(token="xoxb-test", client_factory=lambda **_: fake)
    assert isinstance(adapter, ChannelAdapter)
    assert adapter.name == "slack"


# ---------------------------------------------------------------------------
# Test 2: inbound events become Inbound dataclasses
# ---------------------------------------------------------------------------


def test_inbound_formatting() -> None:
    fake = _FakeSlackClient(
        inbound_events=[
            {
                "type": "message",
                "channel": "C123",
                "thread_ts": "1729820000.001",
                "user": "U_USER",
                "text": "hello world",
                "ts": "1729820000.001",
            }
        ]
    )
    adapter = SlackAdapter(token="xoxb-test", client_factory=lambda **_: fake)

    async def collect() -> list[Inbound]:
        await adapter.start()
        out: list[Inbound] = []
        async for inbound in adapter.iter_inbound():
            out.append(inbound)
        await adapter.stop()
        return out

    inbounds = asyncio.run(collect())
    assert len(inbounds) == 1
    inb = inbounds[0]
    assert inb.channel == "slack"
    assert inb.thread_id == "C123:1729820000.001"
    assert inb.user_id == "U_USER"
    assert inb.text == "hello world"


# ---------------------------------------------------------------------------
# Test 3: outbound respects threading
# ---------------------------------------------------------------------------


def test_outbound_uses_thread_ts() -> None:
    fake = _FakeSlackClient()
    adapter = SlackAdapter(token="xoxb-test", client_factory=lambda **_: fake)

    async def driver() -> str:
        await adapter.start()
        msg_id = await adapter.send(thread_id="C9:111.222", text="hi")
        await adapter.stop()
        return msg_id

    msg_id = asyncio.run(driver())
    assert msg_id  # non-empty
    posted = fake.posted[0]
    assert posted["channel"] == "C9"
    assert posted["thread_ts"] == "111.222"
    assert posted["text"] == "hi"


# ---------------------------------------------------------------------------
# Test 4: attachment passthrough
# ---------------------------------------------------------------------------


def test_attachment_urls_passthrough() -> None:
    fake = _FakeSlackClient(
        inbound_events=[
            {
                "type": "message",
                "channel": "C1",
                "thread_ts": "ts.1",
                "user": "U1",
                "text": "see file",
                "ts": "ts.1",
                "files": [
                    {"url_private": "https://files.slack.com/abc"},
                    {"url_private": "https://files.slack.com/def"},
                ],
            }
        ]
    )
    adapter = SlackAdapter(token="xoxb-test", client_factory=lambda **_: fake)

    async def collect() -> list[Inbound]:
        await adapter.start()
        out = [inb async for inb in adapter.iter_inbound()]
        await adapter.stop()
        return out

    inbs = asyncio.run(collect())
    assert inbs[0].attachments == (
        "https://files.slack.com/abc",
        "https://files.slack.com/def",
    )


# ---------------------------------------------------------------------------
# Test 5: graceful 429 with retry
# ---------------------------------------------------------------------------


def test_rate_limit_retries_once_and_succeeds() -> None:
    fake = _FakeSlackClient(rate_limit_first=True)
    adapter = SlackAdapter(token="xoxb-test", client_factory=lambda **_: fake)

    async def driver() -> str:
        await adapter.start()
        msg_id = await adapter.send(thread_id="C1:ts.1", text="retry me")
        await adapter.stop()
        return msg_id

    msg_id = asyncio.run(driver())
    assert msg_id
    assert len(fake.posted) == 1


# ---------------------------------------------------------------------------
# Test 6: missing token raises FeatureUnavailable on construction
# ---------------------------------------------------------------------------


def test_missing_token_raises_feature_unavailable() -> None:
    with pytest.raises(FeatureUnavailable):
        SlackAdapter(token="")
