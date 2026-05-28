"""Tests for AgentCommunication."""

from __future__ import annotations

import pytest

from lyra_cli.swarm.communication import (
    AgentCommunication,
    Message,
    MessageType,
    SharedStateEntry,
)


@pytest.mark.asyncio
async def test_register_and_send_message() -> None:
    """Registering an agent and sending a message should deliver it."""
    comm = AgentCommunication()
    await comm.register_agent("agent_a")
    await comm.register_agent("agent_b")

    msg = Message(sender_id="agent_a", recipient_id="agent_b", payload={"cmd": "ping"})
    sent = await comm.send_message(msg)
    assert sent is True

    inbox = await comm.read_messages("agent_b")
    assert len(inbox) == 1
    assert inbox[0].payload["cmd"] == "ping"


@pytest.mark.asyncio
async def test_send_to_unregistered_agent_fails() -> None:
    """Sending to an unregistered agent should return False."""
    comm = AgentCommunication()
    await comm.register_agent("sender")
    msg = Message(sender_id="sender", recipient_id="ghost")
    sent = await comm.send_message(msg)
    assert sent is False


@pytest.mark.asyncio
async def test_publish_subscribe() -> None:
    """Publishing to a topic should deliver to all subscribers."""
    comm = AgentCommunication()
    await comm.register_agent("agent_a")
    await comm.register_agent("agent_b")
    await comm.register_agent("agent_c")

    await comm.subscribe("agent_a", "alerts")
    await comm.subscribe("agent_b", "alerts")

    msg = Message(sender_id="agent_c", payload={"alert": "fire"})
    delivered = await comm.publish("alerts", msg)
    assert delivered == 2

    inbox_a = await comm.read_messages("agent_a")
    inbox_b = await comm.read_messages("agent_b")
    inbox_c = await comm.read_messages("agent_c")

    assert len(inbox_a) == 1
    assert len(inbox_b) == 1


@pytest.mark.asyncio
async def test_shared_state_optimistic_locking() -> None:
    """set_state with wrong expected_version should fail."""
    comm = AgentCommunication()

    set_ok = await comm.set_state("config", "v1", "agent_a")
    assert set_ok is True

    entry = await comm.get_state("config")
    assert entry is not None
    assert entry.value == "v1"

    set_fail = await comm.set_state("config", "v2", "agent_b", expected_version=99)
    assert set_fail is False

    set_ok2 = await comm.set_state("config", "v2", "agent_b", expected_version=1)
    assert set_ok2 is True


@pytest.mark.asyncio
async def test_unsubscribe_removes_subscriber() -> None:
    """Unsubscribing should prevent further message delivery."""
    comm = AgentCommunication()
    await comm.register_agent("agent_a")
    await comm.subscribe("agent_a", "topic_x")
    await comm.unsubscribe("agent_a", "topic_x")

    msg = Message(sender_id="someone", payload={"msg": "test"})
    delivered = await comm.publish("topic_x", msg)
    assert delivered == 0


@pytest.mark.asyncio
async def test_unregister_agent_cleans_up() -> None:
    """Unregistering an agent should remove its mailbox and subscriptions."""
    comm = AgentCommunication()
    await comm.register_agent("agent_a")
    await comm.subscribe("agent_a", "news")
    assert comm.registered_agent_count == 1

    await comm.unregister_agent("agent_a")
    assert comm.registered_agent_count == 0
