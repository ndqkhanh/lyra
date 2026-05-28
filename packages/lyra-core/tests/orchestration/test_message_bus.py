"""Tests for message bus module."""

import asyncio

import pytest
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.protocol import Message, MessageType


@pytest.fixture
def message_bus() -> InMemoryMessageBus:
    """Create a message bus for testing."""
    return InMemoryMessageBus()


class TestInMemoryMessageBus:
    """Tests for InMemoryMessageBus."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, message_bus: InMemoryMessageBus) -> None:
        """Test basic publish-subscribe pattern."""
        received_messages: list[Message] = []

        async def callback(message: Message) -> None:
            received_messages.append(message)

        # Subscribe agent
        await message_bus.subscribe("agent-1", callback)

        # Publish message
        message = Message.create(
            type=MessageType.EVENT,
            sender="agent-2",
            receiver="agent-1",
            payload={"event": "test"},
        )
        await message_bus.publish(message)

        # Wait for message processing
        await asyncio.sleep(0.1)

        assert len(received_messages) == 1
        assert received_messages[0].id == message.id

    @pytest.mark.asyncio
    async def test_broadcast_message(self, message_bus: InMemoryMessageBus) -> None:
        """Test broadcasting message to all subscribers."""
        received_1: list[Message] = []
        received_2: list[Message] = []

        async def callback_1(message: Message) -> None:
            received_1.append(message)

        async def callback_2(message: Message) -> None:
            received_2.append(message)

        # Subscribe multiple agents
        await message_bus.subscribe("agent-1", callback_1)
        await message_bus.subscribe("agent-2", callback_2)

        # Broadcast message
        message = Message.create(
            type=MessageType.EVENT,
            sender="orchestrator",
            receiver="broadcast",
            payload={"event": "team_started"},
        )
        await message_bus.publish(message)

        # Wait for message processing
        await asyncio.sleep(0.1)

        # Both agents should receive the message
        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0].id == message.id
        assert received_2[0].id == message.id

    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(
        self, message_bus: InMemoryMessageBus
    ) -> None:
        """Test that broadcast doesn't send to sender."""
        received_1: list[Message] = []
        received_2: list[Message] = []

        async def callback_1(message: Message) -> None:
            received_1.append(message)

        async def callback_2(message: Message) -> None:
            received_2.append(message)

        await message_bus.subscribe("agent-1", callback_1)
        await message_bus.subscribe("agent-2", callback_2)

        # Agent-1 broadcasts
        message = Message.create(
            type=MessageType.EVENT,
            sender="agent-1",
            receiver="broadcast",
            payload={},
        )
        await message_bus.publish(message)

        await asyncio.sleep(0.1)

        # Agent-1 should not receive its own broadcast
        assert len(received_1) == 0
        assert len(received_2) == 1

    @pytest.mark.asyncio
    async def test_request_response(self, message_bus: InMemoryMessageBus) -> None:
        """Test request-response pattern."""

        async def responder_callback(message: Message) -> None:
            if message.type == MessageType.REQUEST:
                await message_bus.respond(
                    message,
                    {"result": "success", "data": "response_data"},
                )

        # Subscribe responder
        await message_bus.subscribe("agent-2", responder_callback)

        # Send request
        response = await message_bus.request(
            sender="agent-1",
            receiver="agent-2",
            payload={"action": "process"},
            timeout=5.0,
        )

        assert response.type == MessageType.RESPONSE
        assert response.sender == "agent-2"
        assert response.receiver == "agent-1"
        assert response.payload["result"] == "success"
        assert response.reply_to is not None

    @pytest.mark.asyncio
    async def test_request_timeout(self, message_bus: InMemoryMessageBus) -> None:
        """Test request timeout when no response."""
        # No subscriber, so no response
        with pytest.raises(TimeoutError, match="No response from agent-2"):
            await message_bus.request(
                sender="agent-1",
                receiver="agent-2",
                payload={},
                timeout=0.5,
            )

    @pytest.mark.asyncio
    async def test_unsubscribe(self, message_bus: InMemoryMessageBus) -> None:
        """Test unsubscribing from message bus."""
        received_messages: list[Message] = []

        async def callback(message: Message) -> None:
            received_messages.append(message)

        # Subscribe and then unsubscribe
        await message_bus.subscribe("agent-1", callback)
        await message_bus.unsubscribe("agent-1")

        # Publish message
        message = Message.create(
            type=MessageType.EVENT,
            sender="agent-2",
            receiver="agent-1",
            payload={},
        )
        await message_bus.publish(message)

        await asyncio.sleep(0.1)

        # Should not receive message after unsubscribe
        assert len(received_messages) == 0

    @pytest.mark.asyncio
    async def test_multiple_messages(self, message_bus: InMemoryMessageBus) -> None:
        """Test handling multiple messages in sequence."""
        received_messages: list[Message] = []

        async def callback(message: Message) -> None:
            received_messages.append(message)

        await message_bus.subscribe("agent-1", callback)

        # Send multiple messages
        for i in range(5):
            message = Message.create(
                type=MessageType.EVENT,
                sender="agent-2",
                receiver="agent-1",
                payload={"index": i},
            )
            await message_bus.publish(message)

        await asyncio.sleep(0.2)

        assert len(received_messages) == 5
        for i, msg in enumerate(received_messages):
            assert msg.payload["index"] == i

    @pytest.mark.asyncio
    async def test_get_subscriber_count(
        self, message_bus: InMemoryMessageBus
    ) -> None:
        """Test getting subscriber count."""
        assert await message_bus.get_subscriber_count() == 0

        await message_bus.subscribe("agent-1", lambda m: None)
        assert await message_bus.get_subscriber_count() == 1

        await message_bus.subscribe("agent-2", lambda m: None)
        assert await message_bus.get_subscriber_count() == 2

        await message_bus.unsubscribe("agent-1")
        assert await message_bus.get_subscriber_count() == 1

    @pytest.mark.asyncio
    async def test_clear(self, message_bus: InMemoryMessageBus) -> None:
        """Test clearing all subscribers and pending responses."""
        await message_bus.subscribe("agent-1", lambda m: None)
        await message_bus.subscribe("agent-2", lambda m: None)

        assert await message_bus.get_subscriber_count() == 2

        await message_bus.clear()

        assert await message_bus.get_subscriber_count() == 0

    @pytest.mark.asyncio
    async def test_message_to_nonexistent_receiver(
        self, message_bus: InMemoryMessageBus
    ) -> None:
        """Test sending message to non-subscribed receiver."""
        # Should not raise error, just silently drop
        message = Message.create(
            type=MessageType.EVENT,
            sender="agent-1",
            receiver="nonexistent",
            payload={},
        )
        await message_bus.publish(message)  # Should not raise

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, message_bus: InMemoryMessageBus) -> None:
        """Test handling multiple concurrent requests."""

        async def responder_callback(message: Message) -> None:
            if message.type == MessageType.REQUEST:
                await asyncio.sleep(0.1)  # Simulate processing
                await message_bus.respond(
                    message,
                    {"request_id": message.id},
                )

        await message_bus.subscribe("responder", responder_callback)

        # Send multiple concurrent requests
        tasks = [
            message_bus.request(
                sender=f"agent-{i}",
                receiver="responder",
                payload={"index": i},
                timeout=5.0,
            )
            for i in range(5)
        ]

        responses = await asyncio.gather(*tasks)

        assert len(responses) == 5
        for response in responses:
            assert response.type == MessageType.RESPONSE
