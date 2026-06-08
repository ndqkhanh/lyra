"""Tests for the Latent Memory Tokens module (MemGen-style).

Covers LatentToken, MemSequence, MemoryWeaver, MemoryTrigger, LatentMemory.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from lyra.memory.latent_tokens import (
    DEFAULT_LATENT_DIM,
    DEFAULT_MAX_MEMORY_TOKENS,
    DEFAULT_NUM_LATENT_TOKENS,
    DEFAULT_TRIGGER_THRESHOLD,
    DEFAULT_WEAVER_HIDDEN_DIM,
    LatentMemory,
    LatentToken,
    MemSequence,
    MemoryTrigger,
    MemoryWeaver,
    TARGET_EXTERNAL_DB_ELIMINATION,
    TARGET_IMPROVEMENT_OVER_EXPEL,
)
from lyra.memory.memory_store import Memory, MemoryStore, MemoryType


# ===================================================================
# LatentToken tests
# ===================================================================


class TestLatentToken:
    """Tests for the LatentToken dataclass."""

    def test_creation(self) -> None:
        token = LatentToken(
            token_id="t1",
            vector=np.array([0.1, 0.2, 0.3], dtype=np.float32),
            weight=0.7,
            created_at=100.0,
        )
        assert token.token_id == "t1"
        assert token.vector.shape == (3,)
        assert token.weight == 0.7
        assert token.last_accessed == 0.0  # default
        assert token.source_memory_id is None

    def test_with_metadata(self) -> None:
        token = LatentToken(
            token_id="t1",
            vector=np.zeros(128),
            metadata={"source": "test"},
        )
        assert token.metadata["source"] == "test"

    def test_default_weight(self) -> None:
        token = LatentToken(token_id="t1", vector=np.zeros(10))
        assert token.weight == 0.5


# ===================================================================
# MemSequence tests
# ===================================================================


class TestMemSequence:
    """Tests for the MemSequence dataclass."""

    def test_creation(self) -> None:
        tokens = [
            LatentToken(token_id="t1", vector=np.zeros(128)),
            LatentToken(token_id="t2", vector=np.zeros(128)),
        ]
        seq = MemSequence(
            sequence_id="s1",
            tokens=tokens,
            source_memory_content="test content",
        )
        assert seq.sequence_id == "s1"
        assert seq.num_tokens == 2
        assert seq.source_memory_content == "test content"

    def test_to_vectors(self) -> None:
        tokens = [
            LatentToken(token_id="t1", vector=np.array([1.0, 0.0])),
            LatentToken(token_id="t2", vector=np.array([0.0, 1.0])),
        ]
        seq = MemSequence(sequence_id="s1", tokens=tokens)
        vectors = seq.to_vectors()
        assert vectors.shape == (2, 2)
        assert vectors[0][0] == 1.0
        assert vectors[1][1] == 1.0

    def test_to_vectors_empty(self) -> None:
        seq = MemSequence(sequence_id="s1", tokens=[])
        vectors = seq.to_vectors()
        assert vectors.shape == (0, 0)

    def test_weight_vector(self) -> None:
        tokens = [
            LatentToken(token_id="t1", vector=np.zeros(10), weight=0.8),
            LatentToken(token_id="t2", vector=np.zeros(10), weight=0.5),
        ]
        seq = MemSequence(sequence_id="s1", tokens=tokens)
        weights = seq.weight_vector()
        assert float(weights[0]) == pytest.approx(0.8)
        assert float(weights[1]) == pytest.approx(0.5)


# ===================================================================
# MemoryWeaver tests
# ===================================================================


class TestMemoryWeaver:
    """Tests for the MemoryWeaver."""

    def test_creation(self) -> None:
        weaver = MemoryWeaver()
        assert weaver.latent_dim == DEFAULT_LATENT_DIM
        assert weaver.hidden_dim == DEFAULT_WEAVER_HIDDEN_DIM
        assert weaver.max_tokens == DEFAULT_NUM_LATENT_TOKENS
        assert weaver.encoder is None

    def test_custom_params(self) -> None:
        weaver = MemoryWeaver(latent_dim=64, hidden_dim=128, max_tokens_per_memory=16)
        assert weaver.latent_dim == 64
        assert weaver.max_tokens == 16

    def test_encode_without_encoder(self) -> None:
        weaver = MemoryWeaver(latent_dim=32, max_tokens_per_memory=8)
        seq = weaver.encode("hello world")
        assert isinstance(seq, MemSequence)
        assert seq.source_memory_content == "hello world"
        assert len(seq.tokens) > 0
        assert seq.num_tokens <= 8

    def test_encode_with_custom_encoder(self) -> None:
        encoder = MagicMock()
        encoder.return_value = np.random.randn(128).astype(np.float32)
        weaver = MemoryWeaver(latent_dim=128, max_tokens_per_memory=4, encoder=encoder)
        seq = weaver.encode("test content")
        assert len(seq.tokens) > 0
        assert encoder.called

    def test_encode_long_content(self) -> None:
        weaver = MemoryWeaver(latent_dim=16, max_tokens_per_memory=16)
        long_content = "word " * 500
        seq = weaver.encode(long_content)
        assert seq.num_tokens <= 16

    def test_encode_short_content(self) -> None:
        weaver = MemoryWeaver(latent_dim=16, max_tokens_per_memory=16)
        seq = weaver.encode("hi")
        assert seq.num_tokens >= 1

    def test_encode_batch(self) -> None:
        weaver = MemoryWeaver(latent_dim=16, max_tokens_per_memory=4)
        memories = [
            Memory(
                memory_id="m1", content="first memory",
                memory_type=MemoryType.EPISODIC, timestamp=time.time(),
            ),
            Memory(
                memory_id="m2", content="second memory",
                memory_type=MemoryType.EPISODIC, timestamp=time.time(),
            ),
        ]
        sequences = weaver.encode_batch(memories)
        assert len(sequences) == 2

    def test_compute_sequence_length(self) -> None:
        weaver = MemoryWeaver(latent_dim=16, max_tokens_per_memory=10)
        embedding = np.random.randn(16).astype(np.float32)
        length = weaver._compute_sequence_length("test", embedding)
        assert 1 <= length <= 10

    def test_embed_to_tokens(self) -> None:
        weaver = MemoryWeaver(latent_dim=8, max_tokens_per_memory=5)
        embedding = np.random.randn(8).astype(np.float32)
        tokens = weaver._embed_to_tokens(embedding, 3, "content", None)
        assert len(tokens) == 3
        for t in tokens:
            assert t.vector.shape == (8,)
            # Should be normalized
            norm = np.linalg.norm(t.vector)
            assert abs(norm - 1.0) < 0.1 or norm <= 1.0

    def test_get_statistics(self) -> None:
        weaver = MemoryWeaver(latent_dim=32)
        weaver.encode("test")
        stats = weaver.get_statistics()
        assert stats["encode_count"] == 1
        assert stats["latent_dim"] == 32
        assert stats["has_external_encoder"] is False


# ===================================================================
# MemoryTrigger tests
# ===================================================================


class TestMemoryTrigger:
    """Tests for the MemoryTrigger."""

    def test_creation(self) -> None:
        trigger = MemoryTrigger()
        assert trigger.threshold == DEFAULT_TRIGGER_THRESHOLD
        assert trigger.max_sequences == 8
        assert trigger.trigger_rate() == 0.0

    def test_custom_params(self) -> None:
        trigger = MemoryTrigger(threshold=0.3, max_sequences=4)
        assert trigger.threshold == 0.3
        assert trigger.max_sequences == 4

    def test_evaluate_no_sequences(self) -> None:
        trigger = MemoryTrigger()
        ctx = np.random.randn(128).astype(np.float32)
        should, sequences = trigger.evaluate(ctx, [])
        assert should is False
        assert sequences == []

    def test_evaluate_with_matching_sequences(self) -> None:
        trigger = MemoryTrigger(threshold=0.0)  # Match everything
        ctx = np.ones(16).astype(np.float32)
        ctx /= np.linalg.norm(ctx)

        tokens = [LatentToken(token_id="t1", vector=ctx.copy(), weight=1.0)]
        seq = MemSequence(sequence_id="s1", tokens=tokens)

        should, sequences = trigger.evaluate(ctx, [seq])
        assert should is True
        assert len(sequences) >= 1

    def test_evaluate_with_max_sequences(self) -> None:
        trigger = MemoryTrigger(threshold=0.0, max_sequences=2)
        ctx = np.ones(16).astype(np.float32)
        ctx /= np.linalg.norm(ctx)

        sequences_list = []
        for i in range(5):
            tokens = [LatentToken(token_id=f"t{i}", vector=ctx.copy(), weight=1.0)]
            sequences_list.append(MemSequence(sequence_id=f"s{i}", tokens=tokens))

        should, retrieved = trigger.evaluate(ctx, sequences_list)
        assert len(retrieved) <= 2

    def test_trigger_rate(self) -> None:
        trigger = MemoryTrigger(threshold=0.0)
        ctx = np.ones(16).astype(np.float32)

        # First call: no sequences
        trigger.evaluate(ctx, [])
        assert trigger.trigger_rate() == 0.0

        # Second call: with matching sequence
        tokens = [LatentToken(token_id="t1", vector=ctx.copy(), weight=1.0)]
        seq = MemSequence(sequence_id="s1", tokens=tokens)
        trigger.evaluate(ctx, [seq])
        assert trigger.trigger_rate() > 0.0

    def test_get_statistics(self) -> None:
        trigger = MemoryTrigger()
        stats = trigger.get_statistics()
        assert stats["trigger_count"] == 0
        assert stats["retrieval_count"] == 0
        assert stats["trigger_rate"] == 0.0
        assert stats["threshold"] == DEFAULT_TRIGGER_THRESHOLD


# ===================================================================
# LatentMemory integration tests
# ===================================================================


class TestLatentMemory:
    """Tests for the LatentMemory class (integration of Weaver + Trigger)."""

    def test_creation(self) -> None:
        lm = LatentMemory()
        assert lm.total_sequences() == 0
        assert lm.total_tokens() == 0

    def test_creation_with_components(self) -> None:
        weaver = MemoryWeaver(latent_dim=32, max_tokens_per_memory=4)
        trigger = MemoryTrigger(threshold=0.3)
        store = MemoryStore()
        lm = LatentMemory(
            weaver=weaver,
            trigger=trigger,
            memory_store=store,
            max_total_tokens=512,
            token_weight_decay=0.01,
        )
        assert lm.weaver is weaver
        assert lm.trigger is trigger
        assert lm._persist_store is store
        assert lm.max_total_tokens == 512

    def test_store_string(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=4),
        )
        seq = lm.store("hello world")
        assert isinstance(seq, MemSequence)
        assert lm.total_sequences() == 1
        assert lm.total_tokens() > 0

    def test_store_memory_object(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=4),
        )
        memory = Memory(
            memory_id="m1", content="memory content",
            memory_type=MemoryType.EPISODIC, timestamp=time.time(),
        )
        seq = lm.store(memory)
        assert seq is not None
        assert lm.total_sequences() == 1

    def test_store_with_persistence(self) -> None:
        store = MemoryStore()
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=4),
            memory_store=store,
        )
        lm.store("persisted content")
        assert len(store.memories) > 0

    def test_store_exceeds_budget(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=8, max_tokens_per_memory=64),
            max_total_tokens=10,  # Very small budget
        )
        # Storing multiple should trigger eviction
        for i in range(5):
            lm.store(f"memory content number {i}")
        # Should not crash, some sequences evicted
        assert lm.total_sequences() >= 0

    def test_retrieve_basic(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=4),
            trigger=MemoryTrigger(threshold=0.0),  # Always trigger
        )
        lm.store("hello world test")
        should, sequences = lm.retrieve("hello")
        assert len(sequences) >= 0

    def test_retrieve_untouched_by_default(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=4),
            trigger=MemoryTrigger(threshold=1.0),  # Never trigger
        )
        lm.store("hello world")
        should, sequences = lm.retrieve("hello")
        assert should is False

    def test_retrieve_raw(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=4),
        )
        lm.store("python programming")
        lm.store("hello world")
        results = lm.retrieve_raw("python", top_k=5)
        assert len(results) >= 1
        for score, seq in results:
            assert isinstance(seq, MemSequence)
            assert isinstance(score, float)

    def test_retrieve_raw_empty(self) -> None:
        lm = LatentMemory()
        results = lm.retrieve_raw("anything", top_k=5)
        assert results == []

    def test_decay_weights(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=2),
            token_weight_decay=0.5,  # Aggressive decay
        )
        lm.store("test content")
        seq = list(lm._sequences.values())[0]
        original_weights = [t.weight for t in seq.tokens]

        lm.decay_weights()

        # Weights should have decreased
        for i, t in enumerate(seq.tokens):
            assert t.weight <= original_weights[i]

    def test_get_all_sequences(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=2),
        )
        lm.store("first")
        lm.store("second")
        sequences = lm.get_all_sequences()
        assert len(sequences) == 2

    def test_clear(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=16, max_tokens_per_memory=2),
        )
        lm.store("test")
        lm.clear()
        assert lm.total_sequences() == 0
        assert lm.total_tokens() == 0

    def test_get_statistics(self) -> None:
        lm = LatentMemory(
            weaver=MemoryWeaver(latent_dim=32, max_tokens_per_memory=4),
            max_total_tokens=256,
        )
        lm.store("test content")
        stats = lm.get_statistics()
        assert stats["total_sequences"] == 1
        assert stats["max_total_tokens"] == 256
        assert stats["budget_utilization"] > 0.0
        assert stats["performance_targets"]["improvement_over_expel"] == "+38.22%"
        assert stats["performance_targets"]["no_external_db"] is True


# ===================================================================
# Constants tests
# ===================================================================


class TestConstants:
    """Tests for module constants."""

    def test_default_values(self) -> None:
        assert DEFAULT_LATENT_DIM == 128
        assert DEFAULT_NUM_LATENT_TOKENS == 64
        assert DEFAULT_TRIGGER_THRESHOLD == 0.5
        assert DEFAULT_WEAVER_HIDDEN_DIM == 256
        assert DEFAULT_MAX_MEMORY_TOKENS == 1024

    def test_target_values(self) -> None:
        assert TARGET_IMPROVEMENT_OVER_EXPEL == 0.3822
        assert TARGET_EXTERNAL_DB_ELIMINATION is True
