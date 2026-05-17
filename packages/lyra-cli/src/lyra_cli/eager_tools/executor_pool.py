"""Eager executor pool for concurrent tool dispatch during streaming."""
import asyncio
from typing import Callable, Any
from dataclasses import dataclass

from lyra_cli.eager_tools.seal_detector import ToolBlock


@dataclass
class ToolResult:
    """Result from tool execution."""
    tool_call_id: str
    result: Any
    error: str | None = None


class EagerExecutorPool:
    """Execute tools concurrently during streaming."""

    def __init__(self, tool_registry: dict[str, Callable]):
        self.tool_registry = tool_registry
        self.pending_tasks: list[asyncio.Task] = []
        self.results: list[ToolResult] = []

    async def dispatch(self, tool: ToolBlock, idempotent: bool = False) -> None:
        """Fire tool immediately (non-blocking)."""
        if not idempotent:
            # Non-idempotent tools wait for message_stop
            return

        # Create background task for eager dispatch
        task = asyncio.create_task(self._execute_tool(tool))
        self.pending_tasks.append(task)

    async def _execute_tool(self, tool: ToolBlock) -> None:
        """Execute tool and store result."""
        try:
            tool_fn = self.tool_registry.get(tool.name)
            if not tool_fn:
                self.results.append(ToolResult(
                    tool_call_id=tool.tool_call_id,
                    result=None,
                    error=f"Tool {tool.name} not found",
                ))
                return

            # Execute tool (simplified - real implementation would parse arguments)
            result = await tool_fn(tool.arguments)
            self.results.append(ToolResult(
                tool_call_id=tool.tool_call_id,
                result=result,
                error=None,
            ))
        except Exception as e:
            self.results.append(ToolResult(
                tool_call_id=tool.tool_call_id,
                result=None,
                error=str(e),
            ))

    async def collect_results(self) -> list[ToolResult]:
        """Gather all results after stream completes."""
        if self.pending_tasks:
            await asyncio.gather(*self.pending_tasks, return_exceptions=True)
        return self.results

    def cancel_all(self) -> None:
        """Cancel all in-flight tools (called on stream abort)."""
        for task in self.pending_tasks:
            if not task.done():
                task.cancel()
