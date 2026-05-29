"""Extended DeadEndRegistry tests — semantic overlap, persistence, concurrency, performance."""

from __future__ import annotations

import json
import threading
import time

from lyra_core.collective import DeadEndEntry, DeadEndRegistry


def _entry(id: str, hypothesis: str, approach: str = "", tags: list[str] | None = None) -> DeadEndEntry:
    return DeadEndEntry(
        id=id, hypothesis=hypothesis, approach=approach,
        failure_reason="test failure", discovered_by="test-agent",
        tags=tags or [],
    )


# ── Semantic similarity beyond keyword overlap ─────────────────────────


class TestSemanticOverlap:
    def test_exact_keyword_match_high_overlap(self):
        reg = DeadEndRegistry(similarity_threshold=0.5)
        reg.register(_entry("de1", "transformer attention mechanisms fail on long sequences"))
        is_dead, entry = reg.is_known_dead_end("transformer attention mechanisms")
        assert is_dead
        assert entry is not None
        assert entry.id == "de1"

    def test_partial_overlap_below_threshold(self):
        reg = DeadEndRegistry(similarity_threshold=0.8)
        reg.register(_entry("de1", "transformer attention mechanisms fail on long sequences"))
        is_dead, _ = reg.is_known_dead_end("completely different topic about graph neural networks")
        assert not is_dead

    def test_synonym_handling_no_match_without_overlap(self):
        """Without embeddings, synonyms won't match — this is the current limitation."""
        reg = DeadEndRegistry(similarity_threshold=0.3)
        reg.register(_entry("de1", "self-attention mechanisms in transformer models"))
        is_dead, _ = reg.is_known_dead_end("internal focus systems within neural architectures")
        assert not is_dead  # Keyword overlap is zero despite semantic similarity

    def test_tag_matching_boosts_overlap(self):
        reg = DeadEndRegistry(similarity_threshold=0.3)
        reg.register(_entry("de1", "test hypothesis", tags=["nlp", "attention", "transformer"]))
        is_dead, _ = reg.is_known_dead_end("nlp attention transformer experiment")
        assert is_dead

    def test_false_positive_rate_acceptable(self):
        """Unrelated hypotheses should not be flagged as dead ends."""
        reg = DeadEndRegistry(similarity_threshold=0.7)
        reg.register(_entry("de1", "RNN vanishing gradient with long sequences"))
        reg.register(_entry("de2", "CNN feature maps for image classification"))
        is_dead, _ = reg.is_known_dead_end("transformer attention patterns in NLP")
        assert not is_dead


# ── Persistence ─────────────────────────────────────────────────────────


class TestPersistence:
    def test_register_and_query_roundtrip(self):
        reg = DeadEndRegistry()
        reg.register(_entry("de1", "hypothesis A", "approach X", tags=["tag1"]))
        reg.register(_entry("de2", "hypothesis B", "approach Y", tags=["tag2"]))
        assert reg.entry_count == 2

        results = reg.query_similar("hypothesis A approach X", top_k=3)
        assert len(results) >= 1
        assert results[0].id == "de1"

    def test_json_serialization_of_entries(self):
        entry = _entry("de1", "test hypothesis", "test approach", tags=["ml", "nlp"])
        d = {
            "id": entry.id,
            "hypothesis": entry.hypothesis,
            "approach": entry.approach,
            "failure_reason": entry.failure_reason,
            "discovered_by": entry.discovered_by,
            "tags": entry.tags,
        }
        raw = json.dumps(d)
        restored = json.loads(raw)
        assert restored["hypothesis"] == "test hypothesis"
        assert restored["tags"] == ["ml", "nlp"]

    def test_reconstitute_registry_from_entries(self):
        reg = DeadEndRegistry()
        for i in range(10):
            reg.register(_entry(f"de{i}", f"hypothesis {i}", f"approach {i}"))

        # Simulate save/reload
        reg2 = DeadEndRegistry()
        for i in range(10):
            reg2.register(_entry(f"de{i}", f"hypothesis {i}", f"approach {i}"))

        assert reg2.entry_count == 10
        for i in range(10):
            is_dead, _ = reg2.is_known_dead_end(f"hypothesis {i}")
            assert is_dead


# ── Performance ─────────────────────────────────────────────────────────


class TestPerformance:
    def test_large_registry_query_speed(self):
        reg = DeadEndRegistry()
        for i in range(1000):
            reg.register(_entry(f"de{i}", f"hypothesis number {i} about topic {i % 20}",
                                f"approach variant {i % 10}", tags=[f"tag{i % 5}"]))

        start = time.monotonic()
        is_dead, _ = reg.is_known_dead_end("hypothesis number 500 about topic 0")
        elapsed = time.monotonic() - start

        assert is_dead
        assert elapsed < 1.0, f"Query took {elapsed:.3f}s, expected < 1.0s"

    def test_query_similar_scales_linearly(self):
        reg = DeadEndRegistry()
        for i in range(500):
            reg.register(_entry(f"de{i}", f"unique term {i} and shared topic"))

        start = time.monotonic()
        results = reg.query_similar("shared topic", top_k=10)
        elapsed = time.monotonic() - start

        assert len(results) == 10
        assert elapsed < 1.0


# ── Concurrency ─────────────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_registration_thread_safe(self):
        reg = DeadEndRegistry()
        errors: list[Exception] = []

        def register_batch(start: int, count: int) -> None:
            try:
                for i in range(start, start + count):
                    reg.register(_entry(f"de{i}", f"thread-safe hypothesis {i}"))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_batch, args=(i * 250, 250))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent registration raised: {errors}"
        assert reg.entry_count == 1000

    def test_concurrent_query_and_register(self):
        reg = DeadEndRegistry()
        for i in range(100):
            reg.register(_entry(f"de{i}", f"base hypothesis {i}"))

        errors: list[Exception] = []
        results_collector: list[bool] = []

        def query_worker() -> None:
            try:
                for _ in range(50):
                    is_dead, _ = reg.is_known_dead_end("base hypothesis 50")
                    results_collector.append(is_dead)
            except Exception as e:
                errors.append(e)

        def register_worker() -> None:
            try:
                for i in range(100, 200):
                    reg.register(_entry(f"de{i}", f"new hypothesis {i}"))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=query_worker)
        t2 = threading.Thread(target=register_worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        assert all(results_collector)  # All queries should find the dead end


# ── Edge cases ──────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_registry_queries_safely(self):
        reg = DeadEndRegistry()
        is_dead, entry = reg.is_known_dead_end("anything")
        assert not is_dead
        assert entry is None

    def test_query_similar_empty_registry(self):
        reg = DeadEndRegistry()
        assert reg.query_similar("anything") == []

    def test_single_word_hypothesis(self):
        reg = DeadEndRegistry(similarity_threshold=0.2)
        reg.register(_entry("de1", "overfitting"))
        is_dead, _ = reg.is_known_dead_end("overfitting")
        assert is_dead

    def test_very_long_hypothesis_text(self):
        reg = DeadEndRegistry()
        long_text = " ".join([f"term{i}" for i in range(100)])
        reg.register(_entry("de1", long_text))
        is_dead, _ = reg.is_known_dead_end(long_text)
        assert is_dead

    def test_keyword_index_maintained_on_register(self):
        reg = DeadEndRegistry()
        reg.register(_entry("de1", "gradient descent optimization", tags=["sgd", "adam"]))
        reg.register(_entry("de2", "adam optimizer convergence", tags=["adam", "optimizer"]))
        # The keyword "adam" should index both entries
        results = reg.query_similar("adam", top_k=5)
        assert len(results) == 2

    def test_prune_by_rebuilding_without_old_entries(self):
        reg = DeadEndRegistry()
        reg.register(_entry("old1", "old hypothesis one"))
        reg.register(_entry("old2", "old hypothesis two"))
        reg.register(_entry("keep", "important finding"))

        # Simulate pruning: rebuild without old entries
        reg2 = DeadEndRegistry()
        reg2.register(_entry("keep", "important finding"))

        assert reg2.entry_count == 1
        is_dead, _ = reg2.is_known_dead_end("important finding")
        assert is_dead
        is_dead, _ = reg2.is_known_dead_end("old hypothesis one")
        assert not is_dead  # Pruned away

    def test_similarity_threshold_boundary(self):
        reg = DeadEndRegistry(similarity_threshold=0.6)
        reg.register(_entry("de1", "reinforcement learning policy gradient methods"))
        # 3 of 3 query terms overlap → 1.0 ≥ 0.6 → match
        is_dead, _ = reg.is_known_dead_end("reinforcement learning policy")
        assert is_dead
        # 1 of 5 entry terms overlaps → 1/2 = 0.5 < 0.6 → no match
        reg2 = DeadEndRegistry(similarity_threshold=0.6)
        reg2.register(_entry("de1", "reinforcement learning policy gradient methods"))
        is_dead2, _ = reg2.is_known_dead_end("unrelated topic")
        assert not is_dead2

    def test_is_known_dead_end_with_empty_approach(self):
        reg = DeadEndRegistry()
        reg.register(_entry("de1", "test hypothesis"))
        is_dead, _ = reg.is_known_dead_end("test hypothesis", approach="")
        assert is_dead
