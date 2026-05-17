"""Executor pool for concurrent tool execution."""

import asyncio
from collections.abc import Callable
from typing import Any

from .types import ToolResult, ToolSeal


class ExecutorPool:
    """Manages concurrent tool execution with cancellation support."""

    def __init__(self, max_workers: int = 10) -> None:
        self.max_workers = max_workers
        self.workers: dict[str, asyncio.Task[Any]] = {}
        self.results: dict[str, ToolResult] = {}
        self.semaphore = asyncio.Semaphore(max_workers)

    async def dispatch(
        self, seal: ToolSeal, tool_fn: Callable[..., Any]
    ) -> None:
        """Dispatch sealed tool to background worker."""

        async def worker() -> None:
            async with self.semaphore:
                try:
                    result = await tool_fn(**seal.arguments)
                    self.results[seal.tool_call_id] = ToolResult(
                        success=True, output=result
                    )
                except Exception as e:
                    self.results[seal.tool_call_id] = ToolResult(
                        success=False, error=str(e)
                    )

        task = asyncio.create_task(worker())
        self.workers[seal.tool_call_id] = task

    async def wait_all(self) -> dict[str, ToolResult]:
        """Wait for all workers to complete."""
        if self.workers:
            await asyncio.gather(*self.workers.values(), return_exceptions=True)
        return self.results

    async def cancel_all(self) -> None:
        """Cancel all in-flight workers."""
        for task in self.workers.values():
            task.cancel()
        if self.workers:
            await asyncio.gather(*self.workers.values(), return_exceptions=True)
        self.workers.clear()
