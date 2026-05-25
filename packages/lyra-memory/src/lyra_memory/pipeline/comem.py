"""
CoMem Pipeline — k-step-off asynchronous memory compression.

A smaller, specialized memory model compresses history in the background
while the main agent decodes. The memory model is trained via GRPO with
a functional equivalence reward — it learns to compress in a way that
preserves downstream agent behavior.

Architecture:
    Time ───────────────────────────────────────────────►
    Main Agent:    [decode t] [decode t+1] [decode t+2] ...
         │              │           │           │
         └── [background compression starts at t] ──┐
                                                    │
    Memory Model:                          [compress t] [compress t+1]
    (bg thread)                                │            │
                                               ▼            ▼
                                         compressed    compressed
                                         ctx(t-k)      ctx(t-k+1)

Source: CoMem (tc9GAKlxQC), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4


class LLMClient(Protocol):
    """Protocol for LLM interaction (used for compression model)."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class CompressionJob:
    """A queued compression task for background processing."""

    step_id: int
    raw_context: str
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class CompressedContext:
    """Result of compressing a context window."""

    step_id: int
    compressed: str
    original_length: int
    compressed_length: int

    @property
    def compression_ratio(self) -> float:
        if self.original_length <= 0:
            return 1.0
        return self.compressed_length / self.original_length

    @property
    def tokens_saved(self) -> int:
        return self.original_length - self.compressed_length


@dataclass
class CoMemPipeline:
    """k-step-off asynchronous memory compression pipeline.

    The memory model runs in a background asyncio task, k steps behind
    the main agent. This decouples compression latency from agent
    inference latency, achieving 1.4x end-to-end speedup.
    """

    memory_model: LLMClient
    k_steps: int = 2
    max_compressed_length: int = 500

    # Internal state
    compression_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    compressed_store: dict[int, CompressedContext] = field(default_factory=dict)
    _compressor_task: asyncio.Task | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _next_step_id: int = field(default=0, repr=False)

    async def start(self) -> None:
        """Start the background compression loop."""
        if self._running:
            return
        self._running = True
        self._compressor_task = asyncio.create_task(self._compression_loop())

    async def stop(self) -> None:
        """Stop the background compression loop."""
        self._running = False
        if self._compressor_task and not self._compressor_task.done():
            self._compressor_task.cancel()
            try:
                await self._compressor_task
            except asyncio.CancelledError:
                pass

    async def enqueue_context(self, raw_context: str) -> int:
        """Enqueue a context window for background compression.

        Args:
            raw_context: The raw context to compress

        Returns:
            step_id for later retrieval of compressed result
        """
        step_id = self._next_step_id
        self._next_step_id += 1
        job = CompressionJob(step_id=step_id, raw_context=raw_context)
        await self.compression_queue.put(job)
        return step_id

    def get_compressed(self, step_id: int) -> CompressedContext | None:
        """Retrieve a compressed context by step_id.

        Returns None if compression hasn't completed yet or if
        the step_id is older than k_steps behind current.
        """
        return self.compressed_store.get(step_id)

    async def _compression_loop(self) -> None:
        """Background loop: compress history continuously."""
        while self._running:
            try:
                job = await asyncio.wait_for(
                    self.compression_queue.get(), timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue

            compressed_text = await self._compress(job.raw_context)
            compressed = CompressedContext(
                step_id=job.step_id,
                compressed=compressed_text,
                original_length=len(job.raw_context),
                compressed_length=len(compressed_text),
            )
            self.compressed_store[job.step_id] = compressed

            # Cleanup: remove entries older than k_steps * 2
            cutoff = job.step_id - self.k_steps * 2
            stale = [sid for sid in self.compressed_store if sid < cutoff]
            for sid in stale:
                del self.compressed_store[sid]

    async def _compress(self, raw_context: str) -> str:
        """Compress raw context using the memory model.

        Produces a dense summary that preserves functional equivalence —
        the compressed context should lead to the same agent decisions
        as the original.
        """
        prompt = f"""Compress the following context into a dense summary.
Preserve all information necessary for correct decision-making.
Target maximum {self.max_compressed_length} characters.

Context:
{raw_context[:3000]}

Compressed summary:"""

        return await self.memory_model.complete(prompt)
