"""Tests for cross-component messaging system.

Phase 4, Week 1: System Integration - Cross-Component Communication
Following TDD approach: RED → GREEN → REFACTOR
"""
import pytest
from typing import Any
from dataclasses import dataclass

from lyra_core.messaging import (
    EventBus,
    Message,
    MessageHandler,
    MessageRouter,
    MessageType,
)


@dataclass(frozen=True)
class SampleMessage(Message):
    """Sample message for unit tests."""
    content: str


class TestEventBusBasics:
    """Test EventBus basic functionality."""

    def test_eventbus_creates(self) -> None:
        """EventBus should initialize."""
        bus = EventBus()
        assert bus is not None

    def test_eventbus_publishes_message(self) -> None:
        """EventBus should publish messages."""
        bus = EventBus()
        message = SampleMessage(
            type=MessageType.AGENT_STARTED,
            content="test"
        )
        bus.publish(message)
        # Should not raise

    def test_eventbus_subscribes_handler(self) -> None:
        """EventBus should allow handler subscription."""
        bus = EventBus()
        received_messages: list[Message] = []

        def handler(msg: Message) -> None:
            received_messages.append(msg)

        bus.subscribe(MessageType.AGENT_STARTED, handler)
        message = SampleMessage(
            type=MessageType.AGENT_STARTED,
            content="test"
        )
        bus.publish(message)

        assert len(received_messages) == 1
        assert received_messages[0] == message


class TestEventBusMultipleHandlers:
    """Test EventBus with multiple handlers."""

    def test_eventbus_multiple_handlers_same_type(self) -> None:
        """Multiple handlers can subscribe to same message type."""
        bus = EventBus()
        received_1: list[Message] = []
        received_2: list[Message] = []

        bus.subscribe(MessageType.AGENT_STARTED, lambda m: received_1.append(m))
        bus.subscribe(MessageType.AGENT_STARTED, lambda m: received_2.append(m))

        message = SampleMessage(type=MessageType.AGENT_STARTED, content="test")
        bus.publish(message)

        assert len(received_1) == 1
        assert len(received_2) == 1

    def test_eventbus_unsubscribe_handler(self) -> None:
        """EventBus should allow unsubscribing handlers."""
        bus = EventBus()
        received: list[Message] = []

        def handler(msg: Message) -> None:
            received.append(msg)

        bus.subscribe(MessageType.AGENT_STARTED, handler)
        bus.unsubscribe(MessageType.AGENT_STARTED, handler)

        message = SampleMessage(type=MessageType.AGENT_STARTED, content="test")
        bus.publish(message)

        assert len(received) == 0


class TestMessageTypes:
    """Test message type enumeration."""

    def test_message_types_exist(self) -> None:
        """Core message types should be defined."""
        assert MessageType.AGENT_STARTED is not None
        assert MessageType.AGENT_COMPLETED is not None
        assert MessageType.TOOL_EXECUTED is not None
        assert MessageType.ERROR_OCCURRED is not None

    def test_message_has_type(self) -> None:
        """Message should have type attribute."""
        message = SampleMessage(
            type=MessageType.AGENT_STARTED,
            content="test"
        )
        assert message.type == MessageType.AGENT_STARTED


class TestMessageRouter:
    """Test message routing functionality."""

    def test_router_creates(self) -> None:
        """MessageRouter should initialize."""
        router = MessageRouter()
        assert router is not None

    def test_router_routes_by_pattern(self) -> None:
        """Router should route messages by pattern."""
        router = MessageRouter()
        received: list[Message] = []

        def handler(msg: Message) -> None:
            received.append(msg)

        router.add_route(pattern="agent.*", handler=handler)

        message = SampleMessage(
            type=MessageType.AGENT_STARTED,
            content="test"
        )
        router.route(message)

        assert len(received) == 1

    def test_router_ignores_non_matching_patterns(self) -> None:
        """Router should ignore non-matching patterns."""
        router = MessageRouter()
        received: list[Message] = []

        def handler(msg: Message) -> None:
            received.append(msg)

        router.add_route(pattern="tool.*", handler=handler)

        message = SampleMessage(
            type=MessageType.AGENT_STARTED,
            content="test"
        )
        router.route(message)

        assert len(received) == 0


class TestMessageHandler:
    """Test message handler protocol."""

    def test_handler_protocol(self) -> None:
        """Handler should follow protocol."""
        received: list[Message] = []

        class TestHandler(MessageHandler):
            def handle(self, message: Message) -> None:
                received.append(message)

        handler = TestHandler()
        message = SampleMessage(
            type=MessageType.AGENT_STARTED,
            content="test"
        )
        handler.handle(message)

        assert len(received) == 1


class TestEventBusErrorHandling:
    """Test EventBus error handling."""

    def test_eventbus_handles_handler_errors(self) -> None:
        """EventBus should handle handler errors gracefully."""
        bus = EventBus()
        received: list[Message] = []

        def failing_handler(msg: Message) -> None:
            raise ValueError("Handler error")

        def working_handler(msg: Message) -> None:
            received.append(msg)

        bus.subscribe(MessageType.AGENT_STARTED, failing_handler)
        bus.subscribe(MessageType.AGENT_STARTED, working_handler)

        message = SampleMessage(type=MessageType.AGENT_STARTED, content="test")
        bus.publish(message)

        # Working handler should still receive message
        assert len(received) == 1

    def test_eventbus_logs_handler_errors(self) -> None:
        """EventBus should log handler errors."""
        bus = EventBus()
        errors: list[Exception] = []

        def error_logger(error: Exception) -> None:
            errors.append(error)

        bus.set_error_handler(error_logger)

        def failing_handler(msg: Message) -> None:
            raise ValueError("Handler error")

        bus.subscribe(MessageType.AGENT_STARTED, failing_handler)

        message = SampleMessage(type=MessageType.AGENT_STARTED, content="test")
        bus.publish(message)

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)


class TestEventBusAsync:
    """Test EventBus async operations."""

    @pytest.mark.asyncio
    async def test_eventbus_async_publish(self) -> None:
        """EventBus should support async publishing."""
        bus = EventBus()
        received: list[Message] = []

        async def async_handler(msg: Message) -> None:
            received.append(msg)

        bus.subscribe_async(MessageType.AGENT_STARTED, async_handler)

        message = SampleMessage(type=MessageType.AGENT_STARTED, content="test")
        await bus.publish_async(message)

        assert len(received) == 1
