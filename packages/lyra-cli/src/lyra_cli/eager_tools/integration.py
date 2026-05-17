"""Integration layer for eager tools with Lyra agent loop."""

import asyncio
from typing import Any

from lyra_cli.eager_tools.seal_detector import SealDetector
from lyra_cli.eager_tools.executor_pool import EagerExecutorPool
from lyra_cli.eager_tools.registry import ToolRegistry
from lyra_cli.eager_tools.types import StreamChunk, ToolSeal


class EagerAgentLoop:
    """Agent loop with eager tool dispatch."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        metrics_collector: Any = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.metrics_collector = metrics_collector

    async def run_with_eager_dispatch(
        self,
        stream: Any,
        emit_event: Any = None,
    ) -> dict[str, Any]:
        """Run agent loop with eager tool dispatch.

        Args:
            stream: LLM streaming response
            emit_event: Optional event emitter for TUI

        Returns:
            Response with text and tool results
        """
        detector = SealDetector()
        executor = EagerExecutorPool(
            tool_registry={
                name: meta.fn
                for name, meta in self.tool_registry.tools.items()
            },
            metrics=self.metrics_collector,
        )

        response_text = []
        sealed_tools: list[ToolSeal] = []

        # Process stream
        async for chunk in stream:
            # Convert to StreamChunk (adapter pattern)
            stream_chunk = self._adapt_chunk(chunk)

            # Detect sealed tools
            sealed = detector.process_chunk(stream_chunk)

            for seal in sealed:
                sealed_tools.append(seal)

                # Check idempotency and dispatch
                is_idempotent = self.tool_registry.is_idempotent(seal.tool_name)

                if is_idempotent:
                    # Eager dispatch!
                    await executor.dispatch(seal, idempotent=True)

                    # Emit event for TUI
                    if emit_event:
                        emit_event(
                            {
                                "kind": "tool_sealed",
                                "tool_call_id": seal.tool_call_id,
                                "tool_name": seal.tool_name,
                                "dispatched": True,
                            }
                        )

            # Accumulate response text
            if stream_chunk.text:
                response_text.append(stream_chunk.text)

        # Stream complete - wait for all tools
        tool_results = await executor.collect_results()

        return {
            "text": "".join(response_text),
            "tool_results": tool_results,
            "sealed_tools": sealed_tools,
        }

    def _adapt_chunk(self, chunk: Any) -> StreamChunk:
        """Adapt provider-specific chunk to StreamChunk.

        Override this for different providers (Anthropic, OpenAI, etc.)
        """
        # Default implementation - assumes chunk has these attributes
        return StreamChunk(
            tool_call_id=getattr(chunk, "tool_call_id", None),
            name=getattr(chunk, "name", None),
            arguments=getattr(chunk, "arguments", None),
            text=getattr(chunk, "text", None),
        )
