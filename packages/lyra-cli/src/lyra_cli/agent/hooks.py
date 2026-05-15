"""Hook system for agent execution - OpenAgentd inspired.

Provides lifecycle hooks for extending agent behavior without
modifying the core loop.
"""

from __future__ import annotations

from typing import Any

from lyra_cli.cli.messages import AssistantMessage, Message

from .loop import AgentState, ModelRequest, RunContext


class BaseAgentHook:
    """Base class for agent lifecycle hooks."""

    async def before_agent(self, ctx: RunContext, state: AgentState) -> None:
        """Called once before agent loop starts.

        Args:
            ctx: Run context
            state: Agent state (mutable)
        """
        pass

    async def before_model(
        self,
        ctx: RunContext,
        state: AgentState,
        request: ModelRequest,
    ) -> ModelRequest | None:
        """Called before each LLM call. Can modify request.

        Args:
            ctx: Run context
            state: Agent state
            request: Model request (immutable)

        Returns:
            Modified request or None to keep original
        """
        return None

    async def on_model_delta(
        self,
        ctx: RunContext,
        state: AgentState,
        chunk: dict[str, Any],
    ) -> None:
        """Called for each streaming delta.

        Args:
            ctx: Run context
            state: Agent state
            chunk: Stream chunk data
        """
        pass

    async def after_model(
        self,
        ctx: RunContext,
        state: AgentState,
        assistant_msg: AssistantMessage,
    ) -> None:
        """Called after LLM response assembled.

        Args:
            ctx: Run context
            state: Agent state
            assistant_msg: Assistant message
        """
        pass

    async def wrap_tool_call(
        self,
        ctx: RunContext,
        state: AgentState,
        tool_call: dict[str, Any],
        next_handler: Any,
        config: dict[str, Any],
    ) -> str:
        """Wrap tool execution (middleware pattern).

        Args:
            ctx: Run context
            state: Agent state
            tool_call: Tool call dict
            next_handler: Next handler in chain
            config: Configuration

        Returns:
            Tool result string
        """
        return await next_handler(ctx, state, tool_call, config)

    async def after_agent(
        self,
        ctx: RunContext,
        state: AgentState,
        last_msg: Message,
    ) -> None:
        """Called once after agent loop completes.

        Args:
            ctx: Run context
            state: Agent state
            last_msg: Last message in conversation
        """
        pass


class StreamPublisherHook(BaseAgentHook):
    """Publishes stream events to SSE store."""

    def __init__(self, stream_store: Any):
        self.stream_store = stream_store

    async def on_model_delta(
        self,
        ctx: RunContext,
        state: AgentState,
        chunk: dict[str, Any],
    ) -> None:
        """Publish text delta to stream store."""
        from lyra_cli.cli.messages import StreamEvent

        if "text" in chunk:
            event = StreamEvent(
                event_type="text_delta",
                data={"text": chunk["text"]},
                agent=ctx.agent_name,
            )
            await self.stream_store.push_event(ctx.session_id, event)

    async def wrap_tool_call(
        self,
        ctx: RunContext,
        state: AgentState,
        tool_call: dict[str, Any],
        next_handler: Any,
        config: dict[str, Any],
    ) -> str:
        """Publish tool start/end events."""
        from lyra_cli.cli.messages import StreamEvent

        # Tool start event
        event = StreamEvent(
            event_type="tool_start",
            data={
                "name": tool_call.get("name"),
                "arguments": tool_call.get("arguments"),
            },
            agent=ctx.agent_name,
        )
        await self.stream_store.push_event(ctx.session_id, event)

        # Execute tool
        try:
            result = await next_handler(ctx, state, tool_call, config)
            success = True
        except Exception as exc:
            result = str(exc)
            success = False

        # Tool end event
        event = StreamEvent(
            event_type="tool_end",
            data={
                "name": tool_call.get("name"),
                "result": result,
                "success": success,
            },
            agent=ctx.agent_name,
        )
        await self.stream_store.push_event(ctx.session_id, event)

        if not success:
            raise Exception(result)

        return result


class ResearchHook(BaseAgentHook):
    """Injects research context and extracts citations."""

    async def before_model(
        self,
        ctx: RunContext,
        state: AgentState,
        request: ModelRequest,
    ) -> ModelRequest | None:
        """Inject research context before LLM call."""
        if state.metadata.get("research_phase") == "synthesis":
            # Inject all findings into system prompt
            findings = state.metadata.get("findings", [])
            if findings:
                enhanced_prompt = (
                    f"{request.system_prompt}\n\n"
                    f"Research Findings:\n{chr(10).join(findings)}"
                )
                return ModelRequest(
                    messages=request.messages,
                    system_prompt=enhanced_prompt,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
        return None

    async def after_model(
        self,
        ctx: RunContext,
        state: AgentState,
        assistant_msg: AssistantMessage,
    ) -> None:
        """Extract citations from assistant response."""
        # TODO: Implement citation extraction
        citations = _extract_citations(assistant_msg.content)
        if "citations" not in state.metadata:
            state.metadata["citations"] = []
        state.metadata["citations"].extend(citations)


def _extract_citations(text: str) -> list[dict[str, str]]:
    """Extract citations from text.

    Args:
        text: Text to extract citations from

    Returns:
        List of citation dicts
    """
    # TODO: Implement proper citation extraction
    # For now, return empty list
    _ = text
    return []
