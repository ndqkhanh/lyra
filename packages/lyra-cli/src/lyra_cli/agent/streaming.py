"""Stream event publisher for real-time output."""

from __future__ import annotations

from typing import Any

from lyra_cli.cli.messages import StreamEvent

from .loop import AgentState, RunContext


class StreamPublisher:
    """Publishes stream events during agent execution."""

    def __init__(self, stream_store: Any | None = None):
        self.stream_store = stream_store
        self._enabled = stream_store is not None

    async def publish_text_delta(
        self, ctx: RunContext, text: str
    ) -> None:
        """Publish text delta event.

        Args:
            ctx: Run context
            text: Text delta
        """
        if not self._enabled:
            return

        event = StreamEvent(
            event_type="text_delta",
            data={"text": text},
            agent=ctx.agent_name,
        )
        await self.stream_store.push_event(ctx.session_id, event)

    async def publish_tool_start(
        self, ctx: RunContext, tool_name: str, arguments: dict[str, Any]
    ) -> None:
        """Publish tool start event.

        Args:
            ctx: Run context
            tool_name: Tool name
            arguments: Tool arguments
        """
        if not self._enabled:
            return

        event = StreamEvent(
            event_type="tool_start",
            data={"name": tool_name, "arguments": arguments},
            agent=ctx.agent_name,
        )
        await self.stream_store.push_event(ctx.session_id, event)

    async def publish_tool_end(
        self, ctx: RunContext, tool_name: str, result: str, success: bool = True
    ) -> None:
        """Publish tool end event.

        Args:
            ctx: Run context
            tool_name: Tool name
            result: Tool result
            success: Whether tool succeeded
        """
        if not self._enabled:
            return

        event = StreamEvent(
            event_type="tool_end",
            data={"name": tool_name, "result": result, "success": success},
            agent=ctx.agent_name,
        )
        await self.stream_store.push_event(ctx.session_id, event)

    async def publish_thinking(
        self, ctx: RunContext, text: str
    ) -> None:
        """Publish thinking event.

        Args:
            ctx: Run context
            text: Thinking text
        """
        if not self._enabled:
            return

        event = StreamEvent(
            event_type="thinking",
            data={"text": text},
            agent=ctx.agent_name,
        )
        await self.stream_store.push_event(ctx.session_id, event)

    async def publish_status(
        self, ctx: RunContext, message: str
    ) -> None:
        """Publish status event.

        Args:
            ctx: Run context
            message: Status message
        """
        if not self._enabled:
            return

        event = StreamEvent(
            event_type="status",
            data={"message": message},
            agent=ctx.agent_name,
        )
        await self.stream_store.push_event(ctx.session_id, event)
