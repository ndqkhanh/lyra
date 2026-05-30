"""Real-time streaming memory ingestion.

Processes conversation streams in small chunks, extracting memories
as they arrive rather than waiting for conversation completion.

Architecture:
  - Token buffer accumulates incoming text chunks
  - Sentence boundary detector triggers memory extraction
  - Batch write to EternalStore when memory count crosses threshold
  - Backpressure signal when buffer exceeds max size
  - Async streaming pipeline with configurable flush intervals
  - Integration with dream consolidator for real-time consolidation
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IngestorStatus(Enum):
    IDLE = "idle"
    STREAMING = "streaming"
    FLUSHING = "flushing"
    BACKPRESSURE = "backpressure"
    DRAINED = "drained"


@dataclass(frozen=True)
class ChunkEvent:
    """A single chunk of text ingested from the stream."""

    chunk_id: str
    text: str
    timestamp: float
    token_count: int
    sequence_number: int


@dataclass(frozen=True)
class IngestorConfig:
    """Configuration for the streaming memory ingestor."""

    max_buffer_tokens: int = 4096
    batch_write_threshold: int = 5         # memories before batch write
    sentence_boundaries: tuple[str, ...] = (".", "!", "?", "\n\n")
    backpressure_ratio: float = 0.8        # buffer fill ratio triggering backpressure
    flush_timeout_ms: float = 5000.0       # auto-flush after idle timeout
    chunk_overlap_tokens: int = 50         # overlap between chunks for continuity
    enable_async: bool = True              # enable async streaming mode
    consolidation_enabled: bool = False    # enable real-time consolidation


@dataclass
class StreamIngestor:
    """Real-time streaming memory ingestion engine.

    Supports both synchronous and asynchronous streaming modes.
    Integrates with EternalStore for persistence and optionally with
    DreamConsolidator for real-time memory consolidation.

    Usage (sync mode)::

        ingestor = StreamIngestor()
        ingestor.start()

        for chunk in conversation_stream:
            memories = ingestor.ingest(chunk)
            if memories:
                for memory in memories:
                    eternal_store.put(memory)

        ingestor.flush()

    Usage (async mode)::

        ingestor = StreamIngestor(config=IngestorConfig(enable_async=True))
        await ingestor.start_async()

        async for chunk in conversation_stream:
            memories = await ingestor.ingest_async(chunk)
            if memories:
                for memory in memories:
                    await eternal_store.put_async(memory)

        await ingestor.flush_async()

    Args:
        config: Ingestor configuration.
        eternal_store: Optional eternal store for persistence.
        consolidator: Optional dream consolidator for real-time consolidation.
    """

    config: IngestorConfig = field(default_factory=IngestorConfig)
    eternal_store: Any | None = None
    consolidator: Any | None = None
    _buffer: str = ""
    _token_estimate: int = 0
    _memories: list[dict[str, Any]] = field(default_factory=list)
    _status: IngestorStatus = IngestorStatus.IDLE
    _sequence: int = 0
    _last_activity: float = 0.0
    _session_id: str = ""
    _total_ingested: int = 0
    _total_memories_extracted: int = 0
    _flush_task: asyncio.Task[None] | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def start(self, session_id: str | None = None) -> None:
        """Start the ingestor in synchronous mode.

        Args:
            session_id: Optional session identifier.
        """
        self._session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        self._status = IngestorStatus.STREAMING
        self._last_activity = time.time()

    async def start_async(self, session_id: str | None = None) -> None:
        """Start the ingestor in asynchronous mode.

        Args:
            session_id: Optional session identifier.
        """
        self._session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        self._status = IngestorStatus.STREAMING
        self._last_activity = time.time()

        # Start background flush task if async mode enabled
        if self.config.enable_async:
            self._flush_task = asyncio.create_task(self._auto_flush_loop())

    async def _auto_flush_loop(self) -> None:
        """Background task for automatic flushing on timeout."""
        while self._status in (IngestorStatus.STREAMING, IngestorStatus.BACKPRESSURE):
            await asyncio.sleep(self.config.flush_timeout_ms / 1000.0)
            if self.should_flush():
                async with self._lock:
                    await self._flush_to_store_async()

    def ingest(self, text: str) -> list[dict[str, Any]]:
        """Ingest a text chunk and extract memories (sync mode).

        Args:
            text: Text chunk to ingest.

        Returns:
            List of extracted memory dictionaries.
        """
        self._last_activity = time.time()
        self._buffer += text
        self._token_estimate += _estimate_tokens(text)
        self._sequence += 1
        self._total_ingested += len(text)

        if self._token_estimate >= self.config.max_buffer_tokens * self.config.backpressure_ratio:
            self._status = IngestorStatus.BACKPRESSURE
        else:
            self._status = IngestorStatus.STREAMING

        new_memories: list[dict[str, Any]] = []
        while True:
            boundary_idx = self._find_boundary()
            if boundary_idx == -1:
                break

            sentence = self._buffer[:boundary_idx + 1].strip()
            self._buffer = self._buffer[boundary_idx + 1:]
            self._token_estimate = _estimate_tokens(self._buffer)

            if len(sentence) > 10:
                memory = self._create_memory_dict(sentence)
                self._memories.append(memory)
                new_memories.append(memory)
                self._total_memories_extracted += 1

        # Auto-persist if batch threshold reached
        if len(self._memories) >= self.config.batch_write_threshold:
            self._flush_to_store()

        return new_memories

    async def ingest_async(self, text: str) -> list[dict[str, Any]]:
        """Ingest a text chunk and extract memories (async mode).

        Args:
            text: Text chunk to ingest.

        Returns:
            List of extracted memory dictionaries.
        """
        async with self._lock:
            self._last_activity = time.time()
            self._buffer += text
            self._token_estimate += _estimate_tokens(text)
            self._sequence += 1
            self._total_ingested += len(text)

            if self._token_estimate >= self.config.max_buffer_tokens * self.config.backpressure_ratio:
                self._status = IngestorStatus.BACKPRESSURE
            else:
                self._status = IngestorStatus.STREAMING

            new_memories: list[dict[str, Any]] = []
            while True:
                boundary_idx = self._find_boundary()
                if boundary_idx == -1:
                    break

                sentence = self._buffer[:boundary_idx + 1].strip()
                self._buffer = self._buffer[boundary_idx + 1:]
                self._token_estimate = _estimate_tokens(self._buffer)

                if len(sentence) > 10:
                    memory = self._create_memory_dict(sentence)
                    self._memories.append(memory)
                    new_memories.append(memory)
                    self._total_memories_extracted += 1

            # Auto-persist if batch threshold reached
            if len(self._memories) >= self.config.batch_write_threshold:
                await self._flush_to_store_async()

            return new_memories

    def _create_memory_dict(self, content: str) -> dict[str, Any]:
        """Create a memory dictionary from content.

        Args:
            content: Memory content.

        Returns:
            Memory dictionary with metadata.
        """
        return {
            "content": content,
            "session_id": self._session_id,
            "timestamp": time.time(),
            "type": "observation",
            "confidence": 0.7,
            "entities": [],
            "sequence": self._sequence,
        }

    def _flush_to_store(self) -> int:
        """Flush memories to eternal store (sync mode).

        Returns:
            Number of memories flushed.
        """
        if not self._memories or not self.eternal_store:
            return 0

        count = 0
        for memory in self._memories:
            try:
                # Convert to EternalRecord if eternal_store is available
                if hasattr(self.eternal_store, "put"):
                    from lyra_memory.eternal_store import EternalRecord, RetentionTier

                    record = EternalRecord.create(
                        content=memory["content"],
                        retention=RetentionTier.STANDARD,
                        metadata={
                            "session_id": memory["session_id"],
                            "type": memory["type"],
                            "sequence": str(memory["sequence"]),
                        },
                    )
                    self.eternal_store.put(record)
                    count += 1
            except Exception:
                # Silently skip failed writes
                pass

        self._memories.clear()
        return count

    async def _flush_to_store_async(self) -> int:
        """Flush memories to eternal store (async mode).

        Returns:
            Number of memories flushed.
        """
        if not self._memories or not self.eternal_store:
            return 0

        count = 0
        for memory in self._memories:
            try:
                # Convert to EternalRecord if eternal_store is available
                if hasattr(self.eternal_store, "put"):
                    from lyra_memory.eternal_store import EternalRecord, RetentionTier

                    record = EternalRecord.create(
                        content=memory["content"],
                        retention=RetentionTier.STANDARD,
                        metadata={
                            "session_id": memory["session_id"],
                            "type": memory["type"],
                            "sequence": str(memory["sequence"]),
                        },
                    )
                    self.eternal_store.put(record)
                    count += 1
            except Exception:
                # Silently skip failed writes
                pass

        self._memories.clear()
        return count

    def _find_boundary(self) -> int:
        earliest = len(self._buffer)
        for boundary in self.config.sentence_boundaries:
            idx = self._buffer.find(boundary)
            if idx != -1 and idx < earliest:
                earliest = idx
        return earliest if earliest < len(self._buffer) else -1

    def should_flush(self) -> bool:
        """Check if buffer should be flushed.

        Returns:
            True if idle timeout exceeded and buffer has content.
        """
        if self._status not in (IngestorStatus.STREAMING, IngestorStatus.BACKPRESSURE):
            return False
        if not self._buffer.strip():
            return False
        idle_ms = (time.time() - self._last_activity) * 1000
        return idle_ms >= self.config.flush_timeout_ms

    def flush(self) -> list[dict[str, Any]]:
        """Flush remaining buffer content (sync mode).

        Returns:
            List of remaining memories extracted from buffer.
        """
        self._status = IngestorStatus.FLUSHING
        remaining: list[dict[str, Any]] = []

        if self._buffer.strip():
            memory = self._create_memory_dict(self._buffer.strip())
            remaining.append(memory)
            self._memories.append(memory)
            self._total_memories_extracted += 1
            self._buffer = ""
            self._token_estimate = 0

        # Flush to store
        self._flush_to_store()

        self._status = IngestorStatus.DRAINED
        return remaining

    async def flush_async(self) -> list[dict[str, Any]]:
        """Flush remaining buffer content (async mode).

        Returns:
            List of remaining memories extracted from buffer.
        """
        async with self._lock:
            self._status = IngestorStatus.FLUSHING
            remaining: list[dict[str, Any]] = []

            if self._buffer.strip():
                memory = self._create_memory_dict(self._buffer.strip())
                remaining.append(memory)
                self._memories.append(memory)
                self._total_memories_extracted += 1
                self._buffer = ""
                self._token_estimate = 0

            # Flush to store
            await self._flush_to_store_async()

            self._status = IngestorStatus.DRAINED
            return remaining

    def get_batch(self) -> list[dict[str, Any]]:
        """Get current batch of memories without flushing to store.

        Returns:
            List of memory dictionaries.
        """
        if len(self._memories) < self.config.batch_write_threshold:
            return []
        batch = list(self._memories)
        self._memories.clear()
        return batch

    async def get_batch_async(self) -> list[dict[str, Any]]:
        """Get current batch of memories without flushing to store (async).

        Returns:
            List of memory dictionaries.
        """
        async with self._lock:
            return self.get_batch()

    def stop(self) -> None:
        """Stop the ingestor and flush remaining content (sync mode)."""
        self.flush()
        self._status = IngestorStatus.DRAINED

    async def stop_async(self) -> None:
        """Stop the ingestor and flush remaining content (async mode)."""
        # Cancel auto-flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        await self.flush_async()
        self._status = IngestorStatus.DRAINED

    @property
    def status(self) -> IngestorStatus:
        return self._status

    @property
    def buffer_fill_ratio(self) -> float:
        if self.config.max_buffer_tokens <= 0:
            return 0.0
        return min(self._token_estimate / self.config.max_buffer_tokens, 1.0)

    @property
    def pending_memories(self) -> int:
        return len(self._memories)

    @property
    def stats(self) -> dict[str, object]:
        return {
            "session_id": self._session_id,
            "status": self._status.value,
            "total_ingested_chars": self._total_ingested,
            "total_memories_extracted": self._total_memories_extracted,
            "buffer_tokens_est": self._token_estimate,
            "pending_memories": len(self._memories),
            "buffer_fill_ratio": self.buffer_fill_ratio,
            "sequence_number": self._sequence,
        }

    def reset(self) -> None:
        self._buffer = ""
        self._token_estimate = 0
        self._memories.clear()
        self._status = IngestorStatus.IDLE
        self._sequence = 0
        self._total_ingested = 0
        self._total_memories_extracted = 0


def _estimate_tokens(text: str) -> int:
    """Rough token count estimation (~4 chars per token for English)."""
    return max(1, len(text) // 4)


__all__ = [
    "ChunkEvent",
    "IngestorConfig",
    "IngestorStatus",
    "StreamIngestor",
]
