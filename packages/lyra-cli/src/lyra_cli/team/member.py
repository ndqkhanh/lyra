"""Team member lifecycle management."""

from __future__ import annotations

import asyncio
from typing import Any

from .mailbox import TeamMailbox


class TeamMember:
    """Team member with mailbox-based activation."""

    def __init__(
        self,
        name: str,
        blueprint: Any,
        mailbox: TeamMailbox,
    ):
        self.name = name
        self.blueprint = blueprint
        self.mailbox = mailbox
        self.state: str = "idle"  # idle, working
        self._active_task: asyncio.Task | None = None

    async def activate(self) -> None:
        """Activate member (called by mailbox on message arrival)."""
        if self.state == "working":
            return  # Already working, will drain queue before next LLM call

        self.state = "working"
        self._active_task = asyncio.create_task(self._run_activation())

    async def _run_activation(self) -> None:
        """One-shot task: drain inbox, run agent, emit done."""
        try:
            # Drain all queued messages
            pending = []
            while not self.mailbox.inbox_empty(self.name):
                try:
                    msg = self.mailbox.receive_nowait(self.name)
                    pending.append(msg)
                except asyncio.QueueEmpty:
                    break

            if not pending:
                self.state = "idle"
                return  # Spurious wakeup

            # Process messages
            await self._handle_messages(pending)

        finally:
            self.state = "idle"

    async def _handle_messages(self, messages: list[dict[str, Any]]) -> None:
        """Handle received messages.

        Args:
            messages: List of message dicts
        """
        # TODO: Implement actual agent execution
        # For now, just log
        for msg in messages:
            print(f"[{self.name}] Received: {msg.get('content', '')}")

    async def shutdown(self) -> None:
        """Shutdown member and cancel active tasks."""
        if self._active_task and not self._active_task.done():
            self._active_task.cancel()
            try:
                await self._active_task
            except asyncio.CancelledError:
                pass

        self.state = "idle"
