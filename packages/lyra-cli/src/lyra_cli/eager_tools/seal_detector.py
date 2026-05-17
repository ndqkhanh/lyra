"""Seal detection for eager tool dispatch during streaming."""
from dataclasses import dataclass
from typing import Optional

from lyra_cli.eager_tools.logging import log_seal_detected
from lyra_cli.eager_tools.metrics import MetricsCollector


@dataclass
class ToolBlock:
    """Completed tool block ready for dispatch."""
    tool_call_id: str
    name: str
    arguments: str


class SealDetector:
    """Detect tool block completion during LLM streaming."""

    def __init__(self, metrics: Optional[MetricsCollector] = None):
        self.current_id: Optional[str] = None
        self.buffer: dict[str, dict] = {}
        self.metrics = metrics

    def process_chunk(self, chunk: dict) -> list[ToolBlock]:
        """Process stream chunk and return sealed (complete) tool blocks."""
        sealed_blocks = []

        # Extract tool_call_id from chunk (Anthropic format)
        tool_call_id = chunk.get("tool_call_id")
        if not tool_call_id:
            return sealed_blocks

        # Detect seal: new ID means previous block is complete
        if self.current_id and tool_call_id != self.current_id:
            if self.current_id in self.buffer:
                sealed_blocks.append(self._seal_block(self.current_id))

        # Update current ID and buffer
        self.current_id = tool_call_id
        if tool_call_id not in self.buffer:
            self.buffer[tool_call_id] = {
                "name": chunk.get("name", ""),
                "arguments": "",
            }

        # Accumulate arguments
        if "arguments" in chunk:
            self.buffer[tool_call_id]["arguments"] += chunk["arguments"]

        return sealed_blocks

    def flush(self) -> list[ToolBlock]:
        """Flush remaining buffered blocks (called at message_stop)."""
        sealed_blocks = []
        if self.current_id and self.current_id in self.buffer:
            sealed_blocks.append(self._seal_block(self.current_id))
        self.buffer.clear()
        self.current_id = None
        return sealed_blocks

    def _seal_block(self, tool_call_id: str) -> ToolBlock:
        """Convert buffered data to sealed ToolBlock."""
        data = self.buffer.pop(tool_call_id)
        block = ToolBlock(
            tool_call_id=tool_call_id,
            name=data["name"],
            arguments=data["arguments"],
        )

        # Log and record metrics
        if self.metrics:
            self.metrics.on_seal_detected(tool_call_id)
        log_seal_detected(tool_call_id, block.name, 0.0)

        return block
