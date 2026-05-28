"""Real-time streaming memory ingestion.

Processes conversation streams in small chunks, extracting memories
as they arrive rather than waiting for conversation completion.

Architecture:
  - Token buffer accumulates incoming text chunks
  - Sentence boundary detector triggers memory extraction
  - Batch write to EternalStore when memory count crosses threshold
  - Backpressure signal when buffer exceeds max size
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


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


@dataclass
class StreamIngestor:
    """Real-time streaming memory ingestion engine.

    Usage::

        ingestor = StreamIngestor()
        ingestor.start()

        for chunk in conversation_stream:
            memories = ingestor.ingest(chunk)
            if memories:
                for memory in memories:
                    eternal_store.put(memory)

        ingestor.flush()
    """

    config: IngestorConfig = field(default_factory=IngestorConfig)
    _buffer: str = ""
    _token_estimate: int = 0
    _memories: list[str] = field(default_factory=list)
    _status: IngestorStatus = IngestorStatus.IDLE
    _sequence: int = 0
    _last_activity: float = 0.0
    _session_id: str = ""
    _total_ingested: int = 0
    _total_memories_extracted: int = 0

    def start(self, session_id: str | None = None) -> None:
        self._session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        self._status = IngestorStatus.STREAMING
        self._last_activity = time.time()

    def ingest(self, text: str) -> list[str]:
        self._last_activity = time.time()
        self._buffer += text
        self._token_estimate += _estimate_tokens(text)
        self._sequence += 1
        self._total_ingested += len(text)

        if self._token_estimate >= self.config.max_buffer_tokens * self.config.backpressure_ratio:
            self._status = IngestorStatus.BACKPRESSURE
        else:
            self._status = IngestorStatus.STREAMING

        new_memories: list[str] = []
        while True:
            boundary_idx = self._find_boundary()
            if boundary_idx == -1:
                break

            sentence = self._buffer[:boundary_idx + 1].strip()
            self._buffer = self._buffer[boundary_idx + 1:]
            self._token_estimate = _estimate_tokens(self._buffer)

            if len(sentence) > 10:
                self._memories.append(sentence)
                new_memories.append(sentence)
                self._total_memories_extracted += 1

        return new_memories

    def _find_boundary(self) -> int:
        earliest = len(self._buffer)
        for boundary in self.config.sentence_boundaries:
            idx = self._buffer.find(boundary)
            if idx != -1 and idx < earliest:
                earliest = idx
        return earliest if earliest < len(self._buffer) else -1

    def should_flush(self) -> bool:
        if self._status != IngestorStatus.STREAMING:
            return False
        if not self._buffer.strip():
            return False
        idle_ms = (time.time() - self._last_activity) * 1000
        return idle_ms >= self.config.flush_timeout_ms

    def flush(self) -> list[str]:
        self._status = IngestorStatus.FLUSHING
        remaining: list[str] = []

        if self._buffer.strip():
            remaining.append(self._buffer.strip())
            self._memories.append(self._buffer.strip())
            self._total_memories_extracted += 1
            self._buffer = ""
            self._token_estimate = 0

        self._status = IngestorStatus.DRAINED
        return remaining

    def get_batch(self) -> list[str]:
        if len(self._memories) < self.config.batch_write_threshold:
            return []
        batch = list(self._memories)
        self._memories.clear()
        return batch

    def stop(self) -> None:
        self.flush()
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
