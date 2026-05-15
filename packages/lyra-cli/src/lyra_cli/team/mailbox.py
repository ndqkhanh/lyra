"""Mailbox system for asyncio-based message passing."""

from __future__ import annotations

import asyncio
from typing import Any, Callable


class TeamMailbox:
    """Asyncio-based message passing with on-message activation."""

    def __init__(self):
        self._inboxes: dict[str, asyncio.Queue] = {}
        self._callbacks: dict[str, Callable] = {}

    def register(self, agent_name: str, on_message: Callable) -> None:
        """Register agent with activation callback.

        Args:
            agent_name: Agent name/handle
            on_message: Callback to invoke when message arrives
        """
        self._inboxes[agent_name] = asyncio.Queue()
        self._callbacks[agent_name] = on_message

    def unregister(self, agent_name: str) -> None:
        """Unregister agent.

        Args:
            agent_name: Agent name/handle
        """
        if agent_name in self._inboxes:
            del self._inboxes[agent_name]
        if agent_name in self._callbacks:
            del self._callbacks[agent_name]

    async def send(self, to: str, message: dict[str, Any]) -> None:
        """Send message and trigger activation.

        Args:
            to: Target agent name
            message: Message dict

        Raises:
            ValueError: If agent not registered
        """
        if to not in self._inboxes:
            raise ValueError(f"Agent {to} not registered")

        await self._inboxes[to].put(message)

        # Trigger activation callback
        if to in self._callbacks:
            asyncio.create_task(self._callbacks[to]())

    async def broadcast(
        self, message: dict[str, Any], exclude: str | None = None
    ) -> None:
        """Broadcast message to all agents.

        Args:
            message: Message dict
            exclude: Optional agent name to exclude
        """
        for agent_name in self._inboxes:
            if agent_name != exclude:
                await self.send(agent_name, message)

    def inbox_empty(self, agent_name: str) -> bool:
        """Check if inbox is empty.

        Args:
            agent_name: Agent name

        Returns:
            True if inbox is empty
        """
        if agent_name not in self._inboxes:
            return True
        return self._inboxes[agent_name].empty()

    def receive_nowait(self, agent_name: str) -> dict[str, Any]:
        """Receive message without waiting.

        Args:
            agent_name: Agent name

        Returns:
            Message dict

        Raises:
            asyncio.QueueEmpty: If inbox is empty
        """
        if agent_name not in self._inboxes:
            raise ValueError(f"Agent {agent_name} not registered")

        return self._inboxes[agent_name].get_nowait()

    async def receive(self, agent_name: str) -> dict[str, Any]:
        """Receive message (blocking).

        Args:
            agent_name: Agent name

        Returns:
            Message dict
        """
        if agent_name not in self._inboxes:
            raise ValueError(f"Agent {agent_name} not registered")

        return await self._inboxes[agent_name].get()
