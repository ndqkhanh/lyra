"""Tests for streaming memory ingestion and buffer."""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from lyra_memory.dream_consolidator import DreamConsolidator, MemoryFragment
from lyra_memory.eternal_store import EternalStore, RetentionTier
from lyra_memory.streaming import (
    BufferState,
    IngestorConfig,
    IngestorStatus,
    MemoryEvent,
    StreamBuffer,
    StreamIngestor,
)


# ── StreamBuffer Tests ──────────────────────────────────────────────────


class TestStreamBuffer:
    """Test StreamBuffer ring buffer operations."""

    def test_buffer_initialization(self):
        """Test buffer initializes with correct defaults."""
        buffer = StreamBuffer(capacity=100)
        assert buffer.size == 0
        assert buffer.capacity == 100
        assert buffer.fill_ratio == 0.0
        assert buffer.state == BufferState.READY

    def test_buffer_push(self):
        """Test pushing events to buffer."""
        buffer = StreamBuffer(capacity=10)
        event = MemoryEvent.create("Test memory", session_id="sess-1")

        result = buffer.push(event)
        assert result is True
        assert buffer.size == 1

    def test_buffer_deduplication(self):
        """Test buffer deduplicates events by content hash."""
        buffer = StreamBuffer(capacity=10, enable_dedup=True)
        event1 = MemoryEvent.create("Same content", session_id="sess-1")
        event2 = MemoryEvent.create("Same content", session_id="sess-1")

        assert buffer.push(event1) is True
        assert buffer.push(event2) is False  # Deduplicated
        assert buffer.size == 1

    def test_buffer_overwrite_oldest(self):
        """Test buffer overwrites oldest when capacity reached."""
        buffer = StreamBuffer(capacity=3)

        for i in range(5):
            event = MemoryEvent.create(f"Memory {i}", session_id="sess-1")
            buffer.push(event)

        assert buffer.size == 3
        assert buffer.stats["total_overwrites"] == 2

    def test_buffer_pop_batch(self):
        """Test popping batch of events."""
        buffer = StreamBuffer(capacity=10)

        for i in range(5):
            event = MemoryEvent.create(f"Memory {i}", session_id="sess-1")
            buffer.push(event)

        batch = buffer.pop_batch(size=3)
        assert len(batch) == 3
        assert buffer.size == 2

    def test_buffer_backpressure(self):
        """Test backpressure signaling."""
        buffer = StreamBuffer(capacity=10, backpressure_threshold=0.8)

        # Fill to 70% - should be READY
        for i in range(7):
            event = MemoryEvent.create(f"Memory {i}", session_id="sess-1")
            buffer.push(event)

        assert buffer.state == BufferState.READY
        assert buffer.has_backpressure is False

        # Fill to 85% - should trigger BACKPRESSURE
        for i in range(2):
            event = MemoryEvent.create(f"Memory {i+7}", session_id="sess-1")
            buffer.push(event)

        assert buffer.state == BufferState.BACKPRESSURE
        assert buffer.has_backpressure is True

    def test_buffer_peek(self):
        """Test peeking at events without removing."""
        buffer = StreamBuffer(capacity=10)

        for i in range(3):
            event = MemoryEvent.create(f"Memory {i}", session_id="sess-1")
            buffer.push(event)

        peeked = buffer.peek(count=2)
        assert len(peeked) == 2
        assert buffer.size == 3  # Size unchanged

    def test_buffer_clear(self):
        """Test clearing buffer."""
        buffer = StreamBuffer(capacity=10)

        for i in range(5):
            event = MemoryEvent.create(f"Memory {i}", session_id="sess-1")
            buffer.push(event)

        cleared = buffer.clear()
        assert cleared == 5
        assert buffer.size == 0

    def test_buffer_stats(self):
        """Test buffer statistics."""
        buffer = StreamBuffer(capacity=10)

        for i in range(3):
            event = MemoryEvent.create(f"Memory {i}", session_id="sess-1")
            buffer.push(event)

        stats = buffer.stats
        assert stats["size"] == 3
        assert stats["capacity"] == 10
        assert stats["total_pushed"] == 3
        assert stats["total_popped"] == 0

    @pytest.mark.asyncio
    async def test_buffer_async_operations(self):
        """Test async buffer operations."""
        buffer = StreamBuffer(capacity=10)

        event = MemoryEvent.create("Async memory", session_id="sess-1")
        result = await buffer.push_async(event)
        assert result is True

        batch = await buffer.pop_batch_async(size=1)
        assert len(batch) == 1

        cleared = await buffer.clear_async()
        assert cleared == 0


# ── StreamIngestor Tests ────────────────────────────────────────────────


class TestStreamIngestor:
    """Test StreamIngestor for real-time memory extraction."""

    def test_ingestor_initialization(self):
        """Test ingestor initializes correctly."""
        ingestor = StreamIngestor()
        assert ingestor.status == IngestorStatus.IDLE
        assert ingestor.pending_memories == 0

    def test_ingestor_start(self):
        """Test starting ingestor."""
        ingestor = StreamIngestor()
        ingestor.start(session_id="test-session")

        assert ingestor.status == IngestorStatus.STREAMING
        assert ingestor.stats["session_id"] == "test-session"

    def test_ingestor_ingest_single_sentence(self):
        """Test ingesting a single sentence."""
        ingestor = StreamIngestor()
        ingestor.start()

        memories = ingestor.ingest("This is a test sentence.")
        assert len(memories) == 1
        assert memories[0]["content"] == "This is a test sentence."

    def test_ingestor_ingest_multiple_sentences(self):
        """Test ingesting multiple sentences."""
        ingestor = StreamIngestor()
        ingestor.start()

        text = "First sentence. Second sentence! Third sentence?"
        memories = ingestor.ingest(text)

        assert len(memories) == 3

    def test_ingestor_buffer_accumulation(self):
        """Test buffer accumulates incomplete sentences."""
        ingestor = StreamIngestor()
        ingestor.start()

        # Incomplete sentence
        memories = ingestor.ingest("This is incomplete")
        assert len(memories) == 0
        assert ingestor.buffer_fill_ratio > 0

        # Complete it
        memories = ingestor.ingest(" and now complete.")
        assert len(memories) == 1

    def test_ingestor_backpressure(self):
        """Test backpressure signaling."""
        config = IngestorConfig(max_buffer_tokens=100, backpressure_ratio=0.8)
        ingestor = StreamIngestor(config=config)
        ingestor.start()

        # Fill buffer to trigger backpressure
        large_text = "word " * 100  # ~400 tokens
        ingestor.ingest(large_text)

        assert ingestor.status == IngestorStatus.BACKPRESSURE

    def test_ingestor_flush(self):
        """Test flushing remaining buffer."""
        ingestor = StreamIngestor()
        ingestor.start()

        ingestor.ingest("Incomplete sentence")
        remaining = ingestor.flush()

        assert len(remaining) == 1
        assert ingestor.status == IngestorStatus.DRAINED

    def test_ingestor_get_batch(self):
        """Test getting batch of memories without auto-flush."""
        # Use high threshold to prevent auto-flush
        config = IngestorConfig(batch_write_threshold=10)
        ingestor = StreamIngestor(config=config)
        ingestor.start()

        # Ingest with proper spacing after periods
        ingestor.ingest("First sentence. ")
        ingestor.ingest("Second sentence. ")
        ingestor.ingest("Third sentence. ")

        # Memories extracted but not flushed yet (below threshold)
        assert ingestor.pending_memories == 3

        # get_batch returns empty because below threshold
        batch = ingestor.get_batch()
        assert len(batch) == 0

        # Verify stats show extraction happened
        assert ingestor.stats["total_memories_extracted"] == 3

    def test_ingestor_with_eternal_store(self):
        """Test ingestor integration with eternal store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(base_path=Path(tmpdir))
            config = IngestorConfig(batch_write_threshold=2)
            ingestor = StreamIngestor(config=config, eternal_store=store)
            ingestor.start()

            # Ingest enough to trigger batch write
            ingestor.ingest("First sentence. Second sentence.")

            # Check store has records
            assert store.size >= 2

    def test_ingestor_stats(self):
        """Test ingestor statistics."""
        ingestor = StreamIngestor()
        ingestor.start()

        ingestor.ingest("Test sentence.")

        stats = ingestor.stats
        assert stats["total_ingested_chars"] > 0
        assert stats["total_memories_extracted"] == 1
        assert stats["status"] == IngestorStatus.STREAMING.value

    @pytest.mark.asyncio
    async def test_ingestor_async_mode(self):
        """Test async ingestor operations."""
        config = IngestorConfig(enable_async=True)
        ingestor = StreamIngestor(config=config)

        await ingestor.start_async(session_id="async-session")
        assert ingestor.status == IngestorStatus.STREAMING

        memories = await ingestor.ingest_async("Async sentence.")
        assert len(memories) == 1

        await ingestor.stop_async()
        assert ingestor.status == IngestorStatus.DRAINED

    @pytest.mark.asyncio
    async def test_ingestor_concurrent_writes(self):
        """Test concurrent writes to ingestor."""
        config = IngestorConfig(enable_async=True)
        ingestor = StreamIngestor(config=config)
        await ingestor.start_async()

        async def write_sentences(prefix: str, count: int):
            for i in range(count):
                await ingestor.ingest_async(f"{prefix} sentence {i}.")

        # Concurrent writes
        await asyncio.gather(
            write_sentences("First", 5),
            write_sentences("Second", 5),
            write_sentences("Third", 5),
        )

        await ingestor.stop_async()
        assert ingestor.stats["total_memories_extracted"] == 15


# ── DreamConsolidator Streaming Tests ───────────────────────────────────


class MockMemoryStore:
    """Mock memory store for testing."""

    def __init__(self):
        self.memories: list[MemoryFragment] = []

    def search(self, query: str, limit: int = 10) -> list[MemoryFragment]:
        return []

    def save(self, fragment: MemoryFragment) -> None:
        self.memories.append(fragment)


class TestDreamConsolidatorStreaming:
    """Test DreamConsolidator streaming mode."""

    def test_streaming_mode_initialization(self):
        """Test consolidator initializes in streaming mode."""
        store = MockMemoryStore()
        consolidator = DreamConsolidator(memory_store=store, streaming_mode=True)

        assert consolidator.streaming_buffer_size == 0

    def test_streaming_ingest_single_trace(self):
        """Test ingesting single trace in streaming mode."""
        store = MockMemoryStore()
        consolidator = DreamConsolidator(memory_store=store, streaming_mode=True)
        consolidator.set_streaming_batch_size(2)

        trace = {
            "content": "Test memory",
            "session_id": "sess-1",
            "timestamp": time.time(),
            "entities": [],
            "type": "observation",
        }

        fragments = consolidator.ingest_streaming(trace)
        assert len(fragments) == 0  # Batch not ready
        assert consolidator.streaming_buffer_size == 1

    def test_streaming_batch_consolidation(self):
        """Test batch consolidation in streaming mode."""
        store = MockMemoryStore()
        consolidator = DreamConsolidator(memory_store=store, streaming_mode=True)
        consolidator.set_streaming_batch_size(2)

        traces = [
            {
                "content": f"Memory {i}",
                "session_id": "sess-1",
                "timestamp": time.time(),
                "entities": [],
                "type": "observation",
            }
            for i in range(2)
        ]

        # First trace - no consolidation
        fragments = consolidator.ingest_streaming(traces[0])
        assert len(fragments) == 0

        # Second trace - triggers consolidation
        fragments = consolidator.ingest_streaming(traces[1])
        assert len(fragments) >= 1
        assert consolidator.streaming_buffer_size == 0

    def test_streaming_flush(self):
        """Test flushing streaming buffer."""
        store = MockMemoryStore()
        consolidator = DreamConsolidator(memory_store=store, streaming_mode=True)
        consolidator.set_streaming_batch_size(10)

        trace = {
            "content": "Unflushed memory",
            "session_id": "sess-1",
            "timestamp": time.time(),
            "entities": [],
            "type": "observation",
        }

        consolidator.ingest_streaming(trace)
        assert consolidator.streaming_buffer_size == 1

        fragments = consolidator.flush_streaming()
        assert len(fragments) >= 1
        assert consolidator.streaming_buffer_size == 0

    def test_streaming_mode_not_enabled_error(self):
        """Test error when streaming methods called without streaming mode."""
        store = MockMemoryStore()
        consolidator = DreamConsolidator(memory_store=store, streaming_mode=False)

        trace = {
            "content": "Test",
            "session_id": "sess-1",
            "timestamp": time.time(),
            "entities": [],
            "type": "observation",
        }

        with pytest.raises(RuntimeError, match="Streaming mode not enabled"):
            consolidator.ingest_streaming(trace)


# ── Integration Tests ───────────────────────────────────────────────────


class TestStreamingIntegration:
    """Integration tests for streaming pipeline."""

    def test_full_streaming_pipeline(self):
        """Test complete streaming pipeline: ingestor -> consolidator -> store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            eternal_store = EternalStore(base_path=Path(tmpdir))
            consolidator = DreamConsolidator(
                memory_store=eternal_store,
                streaming_mode=True,
            )
            consolidator.set_streaming_batch_size(3)

            config = IngestorConfig(batch_write_threshold=3)
            ingestor = StreamIngestor(config=config, eternal_store=eternal_store)
            ingestor.start(session_id="integration-test")

            # Ingest conversation
            conversation = """
            First important fact about Python.
            Second key insight about testing.
            Third observation about memory systems.
            """

            memories = ingestor.ingest(conversation)

            # Consolidate memories
            for memory in memories:
                trace = {
                    "content": memory["content"],
                    "session_id": memory["session_id"],
                    "timestamp": memory["timestamp"],
                    "entities": memory["entities"],
                    "type": memory["type"],
                }
                consolidator.ingest_streaming(trace)

            # Flush remaining
            ingestor.flush()
            consolidator.flush_streaming()

            # Verify persistence
            assert eternal_store.size >= 3

    @pytest.mark.asyncio
    async def test_async_streaming_pipeline(self):
        """Test async streaming pipeline with concurrent processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            eternal_store = EternalStore(base_path=Path(tmpdir))
            config = IngestorConfig(enable_async=True, batch_write_threshold=5)
            ingestor = StreamIngestor(config=config, eternal_store=eternal_store)

            await ingestor.start_async(session_id="async-integration")

            # Simulate streaming conversation
            chunks = [
                "First chunk of conversation. ",
                "Second chunk with more content. ",
                "Third chunk continues. ",
                "Fourth chunk adds detail. ",
                "Fifth chunk completes thought.",
            ]

            for chunk in chunks:
                await ingestor.ingest_async(chunk)
                await asyncio.sleep(0.01)  # Simulate streaming delay

            await ingestor.stop_async()

            # Verify memories extracted
            assert ingestor.stats["total_memories_extracted"] >= 5
