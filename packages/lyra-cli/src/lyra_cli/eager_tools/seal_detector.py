"""Seal detector for identifying completed tool calls in streams."""

import time
from typing import Any

from .types import StreamChunk, ToolSeal


class SealDetector:
    """Detects when tool calls are sealed (complete) in streaming responses."""

    def __init__(self) -> None:
        self.current_id: str | None = None
        self.current_buffer: dict[str, Any] = {}

    def process_chunk(self, chunk: StreamChunk) -> list[ToolSeal]:
        """Process chunk and return any sealed tools.

        A tool is sealed when a new tool_call_id appears, meaning the
        previous tool's JSON is complete.

        Performance target: <5ms per chunk
        """
        if chunk.tool_call_id is None:
            return []

        # Seal detection: ID transition means previous tool is complete
        sealed = []
        if self.current_id is not None and chunk.tool_call_id != self.current_id:
            args = self.current_buffer.get("arguments", {})
            sealed.append(
                ToolSeal(
                    tool_call_id=self.current_id,
                    tool_name=str(self.current_buffer.get("name", "")),
                    arguments=args if isinstance(args, dict) else {},
                    sealed_at=time.time(),
                )
            )
            self.current_buffer = {}

        # Accumulate current tool
        self.current_id = chunk.tool_call_id
        if chunk.name:
            self.current_buffer["name"] = chunk.name
        if chunk.arguments:
            args = self.current_buffer.setdefault("arguments", {})
            if isinstance(args, dict):
                args.update(chunk.arguments)

        return sealed

    def reset(self) -> None:
        """Reset detector state for new stream."""
        self.current_id = None
        self.current_buffer = {}
