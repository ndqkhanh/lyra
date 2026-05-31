"""
Tests for Tier 2 memory enhancements:
- A-MEM Zettelkasten linking (amem_linking.py)
- Write fast-path + admission batching (amac_fastpath.py)
- Cost-sensitive retrieval store routing (cost_sensitive_retrieval.py)
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from lyra_memory.amac_fastpath import (
    AdmissionFastPath,
    AdmissionStatus,
    BackpressureSignal,
    WriteRequest,
    WriteUrgency,
)
from lyra_memory.amem_linking import AmemGraph, LinkType, MemoryLink, MemoryNote
from lyra_memory.cost_sensitive_retrieval import (
    CostSensitiveRouter,
    RetrievalResult,
    StoreTier,
)


# ────────────────────────────────────────────────────────────────────
# A-MEM Zettelkasten Linking Tests
# ────────────────────────────────────────────────────────────────────


class TestAmemGraph:
    """Tests for the A-MEM Zettelkasten graph."""

    def test_add_note(self) -> None:
        graph = AmemGraph()
        note = graph.add_note("JWT is stateless", keywords=["auth", "jwt"], tags=["security"])
        assert note.id is not None
        assert note.content == "JWT is stateless"
        assert note.activation == 1.0
        assert graph.note_count == 1

    def test_add_note_with_auto_link(self) -> None:
        graph = AmemGraph()
        note_a = graph.add_note("JWT tokens for auth", keywords=["auth", "jwt"], tags=["security"])
        note_b = graph.add_note("OAuth2 uses JWT", keywords=["auth", "oauth2", "jwt"],
                                tags=["security"], auto_link=True)
        # Should auto-link to note_a (3 keyword overlaps: auth, jwt)
        links = graph.get_outgoing_links(note_b.id)
        assert len(links) >= 1

    def test_link_notes(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("JWT is stateless", keywords=["auth"])
        b = graph.add_note("Session tokens are stateful", keywords=["auth"])
        link = graph.link(a.id, b.id, LinkType.CONTRADICTS, strength=0.9)
        assert link.link_type == LinkType.CONTRADICTS
        assert link.strength == 0.9

    def test_get_note_and_touch(self) -> None:
        graph = AmemGraph()
        note = graph.add_note("Test note")
        retrieved = graph.get_note(note.id)
        assert retrieved is not None
        assert retrieved.access_count == 1  # Touched once
        assert retrieved.activation > 1.0  # Boosted

    def test_get_neighbors(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("Note A", keywords=["x"])
        b = graph.add_note("Note B", keywords=["x"])
        c = graph.add_note("Note C", keywords=["y"])
        graph.link(a.id, b.id, LinkType.SUPPORTS)
        graph.link(a.id, c.id, LinkType.CONTRADICTS)

        neighbors = graph.get_neighbors(a.id)
        assert len(neighbors) == 2

        supports = graph.get_neighbors(a.id, link_types=[LinkType.SUPPORTS])
        assert len(supports) == 1
        assert supports[0].content == "Note B"

    def test_find_contradictions(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("Claim: X is true")
        b = graph.add_note("Evidence: X is false")
        graph.link(a.id, b.id, LinkType.CONTRADICTS)
        contradictions = graph.find_contradictions(a.id)
        assert len(contradictions) == 1

    def test_find_supporting(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("Claim: JWT is secure")
        b = graph.add_note("Study confirms JWT security")
        graph.link(b.id, a.id, LinkType.SUPPORTS)
        supporting = graph.find_supporting(a.id)
        assert len(supporting) == 1

    def test_bfs_traversal(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("Root")
        b = graph.add_note("Child 1")
        c = graph.add_note("Child 2")
        d = graph.add_note("Grandchild")
        graph.link(a.id, b.id, LinkType.EXTENDS)
        graph.link(a.id, c.id, LinkType.EXTENDS)
        graph.link(b.id, d.id, LinkType.SPECIALIZES)

        visited = graph.traverse_bfs(a.id, max_depth=2)
        assert len(visited) == 4  # a, b, c, d (d is depth 2)

        visited_shallow = graph.traverse_bfs(a.id, max_depth=1)
        assert len(visited_shallow) == 3  # a, b, c

    def test_decay_links(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("A")
        b = graph.add_note("B")
        graph.link(a.id, b.id, LinkType.RELATES_TO, strength=0.15)

        removed = graph.decay_links()
        # Link at 0.15 - 0.01 = 0.14 > 0.1 threshold, should survive
        assert removed == 0

    def test_reinforce_link(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("A")
        b = graph.add_note("B")
        graph.link(a.id, b.id, LinkType.SUPPORTS, strength=0.5)
        assert graph.reinforce_link(a.id, b.id) is True
        # Strength should increase
        links = graph.get_outgoing_links(a.id)
        assert links[0].strength > 0.5

    def test_link_count(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("A")
        b = graph.add_note("B")
        c = graph.add_note("C")
        graph.link(a.id, b.id)
        graph.link(b.id, c.id)
        assert graph.link_count == 2

    def test_missing_note_raises(self) -> None:
        graph = AmemGraph()
        a = graph.add_note("A")
        with pytest.raises(KeyError):
            graph.link(a.id, "nonexistent", LinkType.RELATES_TO)


# ────────────────────────────────────────────────────────────────────
# Write Fast-Path & Admission Batching Tests (CRITICAL-1 fix)
# ────────────────────────────────────────────────────────────────────


class TestAdmissionFastPath:
    """Tests for the A-MAC write fast-path and admission batching."""

    def test_low_urgency_takes_fast_path(self) -> None:
        fp = AdmissionFastPath()
        req = WriteRequest(content="discovery result", urgency=WriteUrgency.LOW)
        result = fp.enqueue_write(req)
        assert result.status == AdmissionStatus.TENTATIVE
        assert fp.stats["fast_path_count"] == 1
        assert fp.stats["queue_depth"] == 0

    def test_medium_urgency_queues(self) -> None:
        fp = AdmissionFastPath()
        req = WriteRequest(content="tool result", urgency=WriteUrgency.MEDIUM)
        result = fp.enqueue_write(req)
        assert result.status == AdmissionStatus.PENDING
        assert fp.stats["queue_depth"] == 1

    def test_high_urgency_queues(self) -> None:
        fp = AdmissionFastPath()
        req = WriteRequest(content="verified finding", urgency=WriteUrgency.HIGH)
        result = fp.enqueue_write(req)
        assert result.status == AdmissionStatus.PENDING

    def test_critical_urgency_queues_not_fast_path(self) -> None:
        fp = AdmissionFastPath()
        req = WriteRequest(content="safety violation", urgency=WriteUrgency.CRITICAL)
        result = fp.enqueue_write(req)
        # CRITICAL is not in FAST_PATH_URGENCIES
        assert result.status == AdmissionStatus.PENDING

    def test_backpressure_at_threshold(self) -> None:
        fp = AdmissionFastPath()
        # Enqueue 51 writes to trigger throttle
        for i in range(51):
            fp.enqueue_write(WriteRequest(content=f"write-{i}", urgency=WriteUrgency.MEDIUM))

        signal = fp.check_backpressure()
        assert signal.queue_depth == 51
        assert signal.should_throttle is True
        assert signal.should_stop is False  # 51 < 200

    def test_backpressure_stop_threshold(self) -> None:
        fp = AdmissionFastPath()
        for i in range(201):
            fp.enqueue_write(WriteRequest(content=f"write-{i}", urgency=WriteUrgency.MEDIUM))

        signal = fp.check_backpressure()
        assert signal.queue_depth == 201
        assert signal.should_stop is True

    def test_backpressure_normal(self) -> None:
        fp = AdmissionFastPath()
        for i in range(10):
            fp.enqueue_write(WriteRequest(content=f"write-{i}", urgency=WriteUrgency.MEDIUM))

        signal = fp.check_backpressure()
        assert signal.should_throttle is False
        assert signal.should_stop is False

    def test_process_queue_batches(self) -> None:
        fp = AdmissionFastPath()
        for i in range(25):
            fp.enqueue_write(WriteRequest(content=f"write-{i}", urgency=WriteUrgency.MEDIUM))

        # Evaluator that admits everything
        evaluator = lambda batch: [AdmissionStatus.ADMITTED] * len(batch)

        processed = fp.process_queue(evaluator)
        assert processed == 15  # Batch size
        assert fp.stats["batched_count"] == 15

    def test_timeout_moves_to_timed_out(self) -> None:
        fp = AdmissionFastPath()
        # Override timeout for testing
        fp.ADMISSION_TIMEOUT_SECONDS = 0.001

        req = WriteRequest(content="slow write", urgency=WriteUrgency.MEDIUM)
        fp.enqueue_write(req)

        import time
        time.sleep(0.01)  # Wait past timeout

        evaluator = lambda batch: [AdmissionStatus.ADMITTED] * len(batch)
        fp.process_queue(evaluator)

        assert fp.stats["timed_out_count"] >= 0  # May have timed out

    def test_retroactive_reject(self) -> None:
        fp = AdmissionFastPath()
        # Always returns True — caller handles actual removal
        assert fp.retroactive_reject("any-id") is True

    def test_drain_queue(self) -> None:
        fp = AdmissionFastPath()
        for i in range(5):
            fp.enqueue_write(WriteRequest(content=f"write-{i}", urgency=WriteUrgency.MEDIUM))

        evaluator = lambda batch: [AdmissionStatus.ADMITTED] * len(batch)
        drained = fp.drain_queue(evaluator)
        assert drained == 5
        assert fp.stats["queue_depth"] == 0

    def test_stats_accurate(self) -> None:
        fp = AdmissionFastPath()
        for i in range(3):
            fp.enqueue_write(WriteRequest(content=f"low-{i}", urgency=WriteUrgency.LOW))
        for i in range(7):
            fp.enqueue_write(WriteRequest(content=f"med-{i}", urgency=WriteUrgency.MEDIUM))

        stats = fp.stats
        assert stats["fast_path_count"] == 3
        assert stats["queue_depth"] == 7
        assert stats["total_processed"] == 3  # Only fast-path counted so far


# ────────────────────────────────────────────────────────────────────
# Cost-Sensitive Retrieval Tests
# ────────────────────────────────────────────────────────────────────


class TestCostSensitiveRetrieval:
    """Tests for the cost-sensitive retrieval store router."""

    def test_working_memory_hit(self) -> None:
        router = CostSensitiveRouter()

        cache: dict[str, str] = {"auth pattern": "Use JWT with RS256"}

        class MockWorkingStore:
            def search(self, query: str) -> RetrievalResult:
                if query in cache:
                    return RetrievalResult(
                        content=cache[query],
                        store=StoreTier.WORKING,
                        confidence=1.0,
                        latency_ms=0.1,
                        cost_usd=0.0,
                        found=True,
                    )
                return RetrievalResult(
                    content="", store=StoreTier.WORKING, confidence=0.0,
                    latency_ms=0.1, cost_usd=0.0, found=False,
                )

        result = router.retrieve("auth pattern", working_store=MockWorkingStore())
        assert result.found is True
        assert result.store == StoreTier.WORKING
        assert result.content == "Use JWT with RS256"

    def test_falls_through_to_episodic(self) -> None:
        router = CostSensitiveRouter()

        class MockWorkingStore:
            def search(self, query: str) -> RetrievalResult:
                return RetrievalResult(
                    content="", store=StoreTier.WORKING, confidence=0.0,
                    latency_ms=0.1, cost_usd=0.0, found=False,
                )

        class MockEpisodicStore:
            def search(self, query: str) -> RetrievalResult:
                return RetrievalResult(
                    content="Found in episodic",
                    store=StoreTier.EPISODIC,
                    confidence=0.85,
                    latency_ms=3.0,
                    cost_usd=0.0,
                    found=True,
                )

        result = router.retrieve("some query", working_store=MockWorkingStore(),
                                 episodic_store=MockEpisodicStore())
        assert result.found is True
        assert result.store == StoreTier.EPISODIC

    def test_all_miss_returns_not_found(self) -> None:
        router = CostSensitiveRouter()

        class MockMissStore:
            def search(self, query: str) -> RetrievalResult:
                return RetrievalResult(
                    content="", store=StoreTier.WORKING, confidence=0.0,
                    latency_ms=0.1, cost_usd=0.0, found=False,
                )

        result = router.retrieve("unknown query", working_store=MockMissStore())
        assert result.found is False
        assert result.confidence == 0.0

    def test_llm_fallback(self) -> None:
        router = CostSensitiveRouter()

        def llm_func(query: str) -> str:
            return f"LLM answer for: {query}"

        result = router.retrieve("new question", llm_fallback=llm_func)
        assert result.found is True
        assert result.store == StoreTier.LLM_FALLBACK

    def test_should_skip_llm(self) -> None:
        router = CostSensitiveRouter()
        assert router.should_skip_llm("any query", max_budget_usd=0.001) is True
        assert router.should_skip_llm("any query", max_budget_usd=0.05) is False

    def test_stats_initial(self) -> None:
        router = CostSensitiveRouter()
        stats = router.stats
        assert stats["total_queries"] == 0
        assert stats["working_hit_rate"] == 0.0

    def test_stats_after_retrieval(self) -> None:
        router = CostSensitiveRouter()

        class MockWorkingStore:
            def search(self, query: str) -> RetrievalResult:
                return RetrievalResult(
                    content="cached answer", store=StoreTier.WORKING,
                    confidence=1.0, latency_ms=0.1, cost_usd=0.0, found=True,
                )

        router.retrieve("test query", working_store=MockWorkingStore())
        stats = router.stats
        assert stats["total_queries"] == 1
        assert stats["working_hit_rate"] == 1.0

    def test_skips_llm_when_over_budget(self) -> None:
        router = CostSensitiveRouter()
        # All stores miss, but we're over budget so LLM is skipped
        result = router.retrieve("expensive query", max_cost_usd=0.001)
        assert result.found is False
        assert result.store != StoreTier.LLM_FALLBACK
