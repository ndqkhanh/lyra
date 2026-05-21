"""Message bus for asynchronous agent-to-agent communication.

Provides abstract interface and in-memory implementation for message
passing between agents. Production implementation will use Redis Streams.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from lyra_core.orchestration.protocol import Message, MessageType


class MessageBus(ABC):
    """Abstract base class for message bus implementations.

    The message bus handles asynchronous communication between agents,
    supporting publish-subscribe, request-response, and broadcast patterns.
    """

    @abstractmethod
    async def publish(self, message: Message) -> None:
        """Publish a message to the bus.

        Args:
            message: Message to publish
        """
        pass

    @abstractmethod
    async def subscribe(self, agent_id: str, callback: Any) -> None:
        """Subscribe an agent to receive messages.

        Args:
            agent_id: Agent ID to subscribe
            callback: Async callback function to handle messages
        """
        pass

    @abstractmethod
    async def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe an agent from receiving messages.

        Args:
            agent_id: Agent ID to unsubscribe
        """
        pass

    @abstractmethod
    async def request(
        self,
        sender: str,
        receiver: str,
        payload: dict[str, Any],
        timeout: float = 30.0,
    ) -> Message:
        """Send a request and wait for response.

        Args:
            sender: Agent ID of sender
            receiver: Agent ID of receiver
            payload: Request payload
            timeout: Timeout in seconds

        Returns:
            Response message

        Raises:
            TimeoutError: If no response received within timeout
        """
        pass

    @abstractmethod
    async def respond(self, request: Message, payload: dict[str, Any]) -> None:
        """Send a response to a request.

        Args:
            request: Original request message
            payload: Response payload
        """
        pass


class InMemoryMessageBus(MessageBus):
    """In-memory implementation of message bus for testing.

    Uses asyncio queues for message delivery. Not suitable for production
    (no persistence, no distribution), but useful for testing and development.
    """

    def __init__(self) -> None:
        """Initialize in-memory message bus."""
        self._subscribers: dict[str, asyncio.Queue[Message]] = {}
        self._pending_responses: dict[str, asyncio.Future[Message]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, message: Message) -> None:
        """Publish a message to the bus.

        Delivers message to the receiver's queue if subscribed.
        Handles broadcast messages by delivering to all subscribers.

        Args:
            message: Message to publish
        """
        async with self._lock:
            # Handle response messages
            if message.type == MessageType.RESPONSE and message.reply_to:
                if message.reply_to in self._pending_responses:
                    future = self._pending_responses.pop(message.reply_to)
                    if not future.done():
                        future.set_result(message)
                    return

            # Handle broadcast messages
            if message.receiver == "broadcast":
                for agent_id, queue in self._subscribers.items():
                    if agent_id != message.sender:
                        await queue.put(message)
                return

            # Handle direct messages
            if message.receiver in self._subscribers:
                await self._subscribers[message.receiver].put(message)

    async def subscribe(self, agent_id: str, callback: Any) -> None:
        """Subscribe an agent to receive messages.

        Creates a queue for the agent and starts a background task
        to process messages using the provided callback.

        Args:
            agent_id: Agent ID to subscribe
            callback: Async callback function to handle messages
        """
        async with self._lock:
            if agent_id not in self._subscribers:
                queue: asyncio.Queue[Message] = asyncio.Queue()
                self._subscribers[agent_id] = queue

                # Start background task to process messages
                asyncio.create_task(self._process_messages(agent_id, queue, callback))

    async def _process_messages(
        self,
        agent_id: str,
        queue: asyncio.Queue[Message],
        callback: Any,
    ) -> None:
        """Background task to process messages for an agent.

        Args:
            agent_id: Agent ID
            queue: Message queue
            callback: Callback function to handle messages
        """
        while True:
            try:
                message = await queue.get()
                await callback(message)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue processing
                pass

    async def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe an agent from receiving messages.

        Args:
            agent_id: Agent ID to unsubscribe
        """
        async with self._lock:
            if agent_id in self._subscribers:
                del self._subscribers[agent_id]

    async def request(
        self,
        sender: str,
        receiver: str,
        payload: dict[str, Any],
        timeout: float = 30.0,
    ) -> Message:
        """Send a request and wait for response.

        Args:
            sender: Agent ID of sender
            receiver: Agent ID of receiver
            payload: Request payload
            timeout: Timeout in seconds

        Returns:
            Response message

        Raises:
            TimeoutError: If no response received within timeout
        """
        # Create request message
        request = Message.create(
            type=MessageType.REQUEST,
            sender=sender,
            receiver=receiver,
            payload=payload,
        )

        # Create future for response
        future: asyncio.Future[Message] = asyncio.Future()
        async with self._lock:
            self._pending_responses[request.id] = future

        # Publish request
        await self.publish(request)

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            async with self._lock:
                self._pending_responses.pop(request.id, None)
            raise TimeoutError(
                f"No response from {receiver} within {timeout} seconds"
            )

    async def respond(self, request: Message, payload: dict[str, Any]) -> None:
        """Send a response to a request.

        Args:
            request: Original request message
            payload: Response payload
        """
        response = Message.create(
            type=MessageType.RESPONSE,
            sender=request.receiver,
            receiver=request.sender,
            payload=payload,
            trace_id=request.trace_id,
            reply_to=request.id,
        )
        await self.publish(response)

    async def get_subscriber_count(self) -> int:
        """Get the number of active subscribers.

        Returns:
            Number of subscribers
        """
        async with self._lock:
            return len(self._subscribers)

    async def clear(self) -> None:
        """Clear all subscribers and pending responses.

        Useful for testing cleanup.
        """
        async with self._lock:
            self._subscribers.clear()
            self._pending_responses.clear()


__all__ = ["MessageBus", "InMemoryMessageBus"]
