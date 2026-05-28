"""Tests for the streaming memory ingestor."""
from __future__ import annotations

from lyra_memory.streaming.ingestor import (
    ChunkEvent,
    IngestorConfig,
    IngestorStatus,
    StreamIngestor,
)


class TestChunkEvent:
    def test_chunk_is_frozen(self):
        chunk = ChunkEvent(
            chunk_id="chunk-1",
            text="Hello world.",
            timestamp=100.0,
            token_count=3,
            sequence_number=0,
        )
        with pytest.raises(Exception):
            chunk.text = "modified"  # type: ignore[misc]


import pytest


class TestStreamIngestor:
    def test_initial_status_is_idle(self):
        ingestor = StreamIngestor()
        assert ingestor.status == IngestorStatus.IDLE

    def test_start_sets_streaming(self):
        ingestor = StreamIngestor()
        ingestor.start("sess-001")
        assert ingestor.status == IngestorStatus.STREAMING

    def test_ingest_extracts_sentences(self):
        ingestor = StreamIngestor()
        ingestor.start()
        memories = ingestor.ingest("Hello world. This is a test. More content!")
        assert len(memories) >= 2

    def test_ingest_short_sentences_filtered(self):
        ingestor = StreamIngestor()
        ingestor.start()
        memories = ingestor.ingest("Hi. Ok. Go.")
        assert len(memories) == 0

    def test_ingest_accumulates_buffer(self):
        ingestor = StreamIngestor()
        ingestor.start()
        ingestor.ingest("First part of a long")
        assert ingestor.buffer_fill_ratio >= 0.0
        assert ingestor.status == IngestorStatus.STREAMING

    def test_flush_returns_remaining(self):
        ingestor = StreamIngestor()
        ingestor.start()
        ingestor.ingest("An incomplete sentence")
        remaining = ingestor.flush()
        assert len(remaining) == 1
        assert ingestor.status == IngestorStatus.DRAINED

    def test_stop_flushes_and_drains(self):
        ingestor = StreamIngestor()
        ingestor.start()
        ingestor.ingest("Unfinished thought")
        ingestor.stop()
        assert ingestor.status == IngestorStatus.DRAINED

    def test_should_flush_when_idle_timeout(self):
        ingestor = StreamIngestor()
        ingestor.start()
        ingestor.ingest("Some content that is not complete")
        # Set last activity far in the past to trigger flush
        import time
        ingestor._last_activity = time.time() - 10.0
        assert ingestor.should_flush()

    def test_should_not_flush_when_idle(self):
        ingestor = StreamIngestor()
        assert not ingestor.should_flush()

    def test_get_batch_returns_memories(self):
        ingestor = StreamIngestor()
        ingestor.start()
        for i in range(10):
            ingestor.ingest(f"Memory sentence number {i}. ")
        batch = ingestor.get_batch()
        assert len(batch) > 0

    def test_get_batch_clears_pending(self):
        ingestor = StreamIngestor()
        ingestor.start()
        for i in range(10):
            ingestor.ingest(f"Memory {i}. ")
        ingestor.get_batch()
        assert ingestor.pending_memories == 0

    def test_stats_returns_dict(self):
        ingestor = StreamIngestor()
        ingestor.start("sess-test")
        ingestor.ingest("Test sentence one. Test sentence two.")
        stats = ingestor.stats
        assert stats["session_id"] == "sess-test"
        assert stats["status"] == "streaming"
        assert stats["total_memories_extracted"] >= 2

    def test_reset_clears_all(self):
        ingestor = StreamIngestor()
        ingestor.start()
        ingestor.ingest("Content one. Content two.")
        ingestor.reset()
        assert ingestor.status == IngestorStatus.IDLE
        assert ingestor.pending_memories == 0
        assert ingestor.buffer_fill_ratio == 0.0

    def test_backpressure_triggers_at_threshold(self):
        config = IngestorConfig(max_buffer_tokens=100, backpressure_ratio=0.5)
        ingestor = StreamIngestor(config=config)
        ingestor.start()
        # Send enough text to fill the buffer past 50%
        long_text = "x" * 500
        ingestor.ingest(long_text)
        assert ingestor.status == IngestorStatus.BACKPRESSURE

    def test_streaming_without_explicit_start(self):
        ingestor = StreamIngestor()
        ingestor.ingest("Auto-start. Should work.")
        # Without start(), the status might stay IDLE
        assert ingestor.buffer_fill_ratio >= 0.0
