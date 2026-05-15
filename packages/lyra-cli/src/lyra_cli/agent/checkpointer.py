"""Checkpointer for crash-safe persistence - 4 sync points per turn."""

from __future__ import annotations

from typing import Any

from lyra_cli.cli.messages import AssistantMessage, ToolMessage

from .loop import AgentState, RunContext


class Checkpointer:
    """Persists agent state at sync points for crash recovery."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path
        self._last_sync: dict[str, Any] = {}

    async def sync(self, ctx: RunContext, state: AgentState) -> None:
        """Persist state at sync point.

        Sync points per turn:
        1. After before_model (captures summarization changes)
        2. After after_model (captures assistant message + usage)
        3. After tool execution (captures tool results)
        4. After after_agent (final sync)

        Args:
            ctx: Run context
            state: Agent state to persist
        """
        if not ctx.session_id:
            return  # No persistence without session

        # Extract messages to persist
        messages_to_save = []
        for msg in state.messages:
            # Skip empty assistant messages (interrupted before content)
            if isinstance(msg, AssistantMessage) and not msg.content:
                continue

            messages_to_save.append(msg)

        # TODO: Implement actual database persistence
        # For now, just track in memory
        self._last_sync[ctx.session_id] = {
            "run_id": ctx.run_id,
            "agent_name": ctx.agent_name,
            "message_count": len(messages_to_save),
            "system_prompt": state.system_prompt,
            "metadata": state.metadata.copy(),
        }

    async def heal_orphaned_tool_calls(
        self, ctx: RunContext, state: AgentState
    ) -> None:
        """Recover from crash between assistant message and tool results.

        If crash occurs after sync point 2 (assistant with tool_calls) but
        before sync point 3 (tool results), insert synthetic ToolMessage
        to prevent provider errors.

        Args:
            ctx: Run context
            state: Agent state
        """
        if not state.messages:
            return

        last_msg = state.messages[-1]
        if not isinstance(last_msg, AssistantMessage):
            return

        if not last_msg.tool_calls:
            return

        # Check if tool results exist
        tool_call_ids = {tc["id"] for tc in last_msg.tool_calls}
        result_ids = {
            msg.tool_call_id
            for msg in state.messages
            if isinstance(msg, ToolMessage)
        }

        orphaned_ids = tool_call_ids - result_ids
        if orphaned_ids:
            # Insert synthetic results for orphaned tool calls
            for tc_id in orphaned_ids:
                state.messages.append(
                    ToolMessage(
                        content="Tool execution was interrupted. Please retry.",
                        tool_call_id=tc_id,
                    )
                )

    async def load_session(self, session_id: str) -> dict[str, Any] | None:
        """Load session state from checkpoint.

        Args:
            session_id: Session ID to load

        Returns:
            Session state dict or None if not found
        """
        # TODO: Implement actual database loading
        return self._last_sync.get(session_id)


class SQLiteCheckpointer(Checkpointer):
    """SQLite-based checkpointer for production use."""

    def __init__(self, db_path: str):
        super().__init__(db_path)
        # TODO: Initialize SQLite connection

    async def sync(self, ctx: RunContext, state: AgentState) -> None:
        """Persist to SQLite database."""
        # TODO: Implement SQLite persistence
        await super().sync(ctx, state)

    async def load_session(self, session_id: str) -> dict[str, Any] | None:
        """Load from SQLite database."""
        # TODO: Implement SQLite loading
        return await super().load_session(session_id)
