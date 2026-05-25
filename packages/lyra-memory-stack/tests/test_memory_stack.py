"""Tests for lyra_memory_stack package."""

from __future__ import annotations

import time

import numpy as np
import pytest

from lyra_memory_stack.decay_manager import DecayConfig, DecayManager
from lyra_memory_stack.dream_cycle import DreamCycle
from lyra_memory_stack.dual_trace import DualTraceEncoder
from lyra_memory_stack.episodic_memory import EpisodicMemory, EpisodicEvent
from lyra_memory_stack.exceptions import MemoryStackError
from lyra_memory_stack.mcp_server import MemoryMCPServer, MCPSearchResult
from lyra_memory_stack.privacy_tiers import PrivacyManager, PrivacyTier
from lyra_memory_stack.procedural_memory import (
    KnowledgeGraphEntry,
    ProceduralMemory,
    Procedure,
)
from lyra_memory_stack.retrieval import IndexEntry, RetrievalPipeline, TimelineEntry
from lyra_memory_stack.semantic_memory import (
    SemanticFact,
    SemanticMemory,
    SemanticSearchResult,
)
from lyra_memory_stack.symbolic_compressor import SymbolicCanvas, SymbolicCompressor
from lyra_memory_stack.working_memory import (
    WorkingMemory,
    WorkingMemoryConfig,
    WorkingMemoryEntry,
)


class TestWorkingMemory:
    @pytest.mark.asyncio
    async def test_add_and_get(self) -> None:
        wm = WorkingMemory()
        eid = await wm.add("Hello world")
        entry = await wm.get(eid)
        assert entry.content == "Hello world"
        assert entry.priority == 1.0

    @pytest.mark.asyncio
    async def test_add_empty_content_raises(self) -> None:
        wm = WorkingMemory()
        with pytest.raises(MemoryStackError, match="Content cannot be empty"):
            await wm.add("   ")

    @pytest.mark.asyncio
    async def test_get_missing_raises(self) -> None:
        wm = WorkingMemory()
        with pytest.raises(MemoryStackError, match="Entry not found"):
            await wm.get("nonexistent")

    @pytest.mark.asyncio
    async def test_get_all_sorted_by_priority(self) -> None:
        wm = WorkingMemory()
        await wm.add("low", priority=0.5)
        await wm.add("high", priority=2.0)
        await wm.add("mid", priority=1.0)
        entries = await wm.get_all()
        assert entries[0].content == "high"
        assert entries[1].content == "mid"
        assert entries[2].content == "low"

    @pytest.mark.asyncio
    async def test_update_priority(self) -> None:
        wm = WorkingMemory()
        eid = await wm.add("test", priority=1.0)
        await wm.update_priority(eid, 5.0)
        entry = await wm.get(eid)
        assert entry.priority == 5.0

    @pytest.mark.asyncio
    async def test_remove_entry(self) -> None:
        wm = WorkingMemory()
        eid = await wm.add("test")
        await wm.remove(eid)
        with pytest.raises(MemoryStackError):
            await wm.get(eid)

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        wm = WorkingMemory()
        await wm.add("a")
        await wm.add("b")
        await wm.clear()
        entries = await wm.get_all()
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_eviction_when_full(self) -> None:
        config = WorkingMemoryConfig(max_entries=3)
        wm = WorkingMemory(config)
        await wm.add("keep1", priority=10.0)
        await wm.add("keep2", priority=9.0)
        await wm.add("keep3", priority=8.0)
        await wm.add("new", priority=1.0)
        entries = await wm.get_all()
        assert len(entries) == 3
        assert entries[-1].content == "new"

    @pytest.mark.asyncio
    async def test_estimate_tokens(self) -> None:
        wm = WorkingMemory()
        await wm.add("Hello world, this is a test")
        tokens = await wm.estimate_tokens()
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_config_defaults(self) -> None:
        config = WorkingMemoryConfig()
        assert config.max_entries == 100
        assert config.max_tokens_estimate == 100_000

    @pytest.mark.asyncio
    async def test_ttl_expiry(self) -> None:
        wm = WorkingMemory(WorkingMemoryConfig(default_ttl=0.0))
        eid = await wm.add("expires", ttl=0.001)
        await wm.get(eid)
        await wm.add("another")
        entries = await wm.get_all()
        assert len(entries) >= 1


class TestEpisodicMemory:
    @pytest.mark.asyncio
    async def test_record_and_search(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "decision", "Chose approach A", tags=("important",))
        results = await em.search("approach", limit=10)
        assert len(results) >= 1
        assert results[0].event_type == "decision"

    @pytest.mark.asyncio
    async def test_search_with_session_filter(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "tool_call", "Ran test suite")
        await em.record_event("sess-2", "tool_call", "Deployed app")
        results = await em.search("tool_call", session_id="sess-1")
        assert all(r.session_id == "sess-1" for r in results)

    @pytest.mark.asyncio
    async def test_get_by_session(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-A", "note", "First")
        await em.record_event("sess-A", "note", "Second")
        await em.record_event("sess-B", "note", "Other")
        events = await em.get_by_session("sess-A")
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_get_recent(self) -> None:
        em = EpisodicMemory()
        for i in range(5):
            await em.record_event("sess-1", "event", f"Event {i}")
        recent = await em.get_recent(limit=3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        em = EpisodicMemory()
        assert await em.count() == 0
        await em.record_event("sess-1", "event", "test")
        assert await em.count() == 1


class TestSemanticMemory:
    @pytest.mark.asyncio
    async def test_store_and_search(self) -> None:
        sm = SemanticMemory()
        emb = np.array([1.0, 0.0, 0.0])
        await sm.store("Python is a programming language", emb, category="knowledge")
        results = await sm.search(emb, query_text="Python", top_k=5)
        assert len(results) == 1
        assert results[0].score > 0

    @pytest.mark.asyncio
    async def test_search_empty(self) -> None:
        sm = SemanticMemory()
        results = await sm.search(np.array([1.0, 0.0, 0.0]))
        assert results == ()

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self) -> None:
        sm = SemanticMemory()
        emb1 = np.array([1.0, 0.0])
        emb2 = np.array([0.0, 1.0])
        await sm.store("Fact A", emb1, category="preference")
        await sm.store("Fact B", emb2, category="knowledge")
        results = await sm.search(emb1, category="preference")
        assert len(results) == 1
        assert results[0].fact.category == "preference"

    @pytest.mark.asyncio
    async def test_update_confidence(self) -> None:
        sm = SemanticMemory()
        emb = np.array([1.0, 0.0])
        fid = await sm.store("Test fact", emb, confidence=0.5)
        await sm.update_confidence(fid, 0.9)
        fact = await sm.get_fact(fid)
        assert fact.confidence == 0.9

    @pytest.mark.asyncio
    async def test_forget(self) -> None:
        sm = SemanticMemory()
        emb = np.array([1.0, 0.0])
        fid = await sm.store("Test", emb)
        await sm.forget(fid)
        with pytest.raises(KeyError):
            await sm.get_fact(fid)

    @pytest.mark.asyncio
    async def test_get_all_by_category(self) -> None:
        sm = SemanticMemory()
        emb = np.array([1.0, 0.0])
        await sm.store("A", emb, category="preference")
        await sm.store("B", emb, category="knowledge")
        prefs = await sm.get_all_by_category("preference")
        assert len(prefs) == 1


class TestProceduralMemory:
    @pytest.mark.asyncio
    async def test_register_and_find(self) -> None:
        pm = ProceduralMemory()
        pid = await pm.register_procedure(
            "Test Proc",
            "A test procedure",
            ("Step 1", "Step 2"),
            triggers=("test", "debug"),
        )
        results = await pm.find_by_trigger("test")
        assert len(results) == 1
        assert results[0].name == "Test Proc"

    @pytest.mark.asyncio
    async def test_success_and_failure_tracking(self) -> None:
        pm = ProceduralMemory()
        pid = await pm.register_procedure("Proc", "Desc", ("Step",))
        await pm.record_success(pid)
        await pm.record_success(pid)
        await pm.record_failure(pid)
        reliable = await pm.get_reliable_procedures(min_success_rate=0.5)
        assert len(reliable) == 1
        assert reliable[0].success_count == 2
        assert reliable[0].failure_count == 1

    @pytest.mark.asyncio
    async def test_kg_add_and_traverse(self) -> None:
        pm = ProceduralMemory()
        n1 = await pm.add_kg_entry("Node 1", "concept")
        n2 = await pm.add_kg_entry(
            "Node 2", "tool", edges=((n1, "uses"),)
        )
        traversal = await pm.traverse_kg(n2)
        assert len(traversal) == 2

    @pytest.mark.asyncio
    async def test_traverse_missing_node(self) -> None:
        pm = ProceduralMemory()
        with pytest.raises(KeyError):
            await pm.traverse_kg("nonexistent")

    @pytest.mark.asyncio
    async def test_record_success_missing(self) -> None:
        pm = ProceduralMemory()
        with pytest.raises(KeyError):
            await pm.record_success("nonexistent")


class TestRetrievalPipeline:
    @pytest.mark.asyncio
    async def test_search_index(self) -> None:
        em = EpisodicMemory()
        pipeline = RetrievalPipeline(episodic=em)
        await em.record_event("sess-1", "note", "Test query content for search")
        results = await pipeline.search_index("query", limit=5)
        assert len(results) >= 1
        assert isinstance(results[0], IndexEntry)

    @pytest.mark.asyncio
    async def test_get_timeline(self) -> None:
        em = EpisodicMemory()
        pipeline = RetrievalPipeline(episodic=em)
        await em.record_event("sess-1", "note", "Event 1")
        await em.record_event("sess-1", "note", "Event 2")
        results = await pipeline.get_timeline("ep-1", depth_before=1, depth_after=1)
        assert len(results) >= 1
        assert isinstance(results[0], TimelineEntry)

    @pytest.mark.asyncio
    async def test_get_details(self) -> None:
        em = EpisodicMemory()
        pipeline = RetrievalPipeline(episodic=em)
        await em.record_event("sess-1", "note", "Full event content")
        details = await pipeline.get_details(("ep-1",))
        assert len(details) == 1
        assert "Full event content" in details[0]

    @pytest.mark.asyncio
    async def test_estimate_token_cost(self) -> None:
        pipeline = RetrievalPipeline()
        costs = await pipeline.estimate_token_cost(10, 5, 2)
        assert costs["total"] > 0
        assert costs["index_tokens"] == 750
        assert costs["timeline_tokens"] == 1500
        assert costs["detail_tokens"] == 1500


class TestSymbolicCompressor:
    @pytest.mark.asyncio
    async def test_compress(self) -> None:
        sc = SymbolicCompressor()
        raw = "Line 1\nLine 2\nError: something failed\nWarning: deprecated\n/src/main.py"
        canvas = await sc.compress("bash", raw)
        assert canvas.summary != ""
        assert canvas.symbols
        assert canvas.stats["line_count"] == 5

    @pytest.mark.asyncio
    async def test_get_raw(self) -> None:
        sc = SymbolicCompressor()
        canvas = await sc.compress("test", "raw data")
        raw = await sc.get_raw(canvas.raw_ref)
        assert raw == "raw data"

    @pytest.mark.asyncio
    async def test_compress_multi(self) -> None:
        sc = SymbolicCompressor()
        inputs = (("tool_a", "output a"), ("tool_b", "output b"))
        canvases = await sc.compress_multi(inputs)
        assert len(canvases) == 2

    @pytest.mark.asyncio
    async def test_compression_ratio(self) -> None:
        sc = SymbolicCompressor()
        raw = "x" * 10000
        canvas = await sc.compress("tool", raw)
        assert canvas.stats["compression_ratio"] < 1.0


class TestDualTraceEncoder:
    @pytest.mark.asyncio
    async def test_encode_and_search_fact(self) -> None:
        dte = DualTraceEncoder()
        tid = await dte.encode("Agent", "executed", "task", environment="session-1")
        facts = await dte.search_by_fact(subject="Agent")
        assert len(facts) == 1
        assert facts[0].predicate == "executed"

    @pytest.mark.asyncio
    async def test_search_by_scene(self) -> None:
        dte = DualTraceEncoder()
        await dte.encode("A", "did", "B", environment="prod", importance=0.9)
        await dte.encode("C", "did", "D", environment="dev", importance=0.3)
        scenes = await dte.search_by_scene(environment="prod", min_importance=0.5)
        assert len(scenes) == 1

    @pytest.mark.asyncio
    async def test_get_full_trace(self) -> None:
        dte = DualTraceEncoder()
        tid = await dte.encode("S", "P", "O")
        fact, scene = await dte.get_full_trace(tid)
        assert fact.subject == "S"
        assert scene.environment == "default"

    @pytest.mark.asyncio
    async def test_invalid_valence_clamped(self) -> None:
        dte = DualTraceEncoder()
        tid = await dte.encode("S", "P", "O", emotional_valence=5.0)
        _, scene = await dte.get_full_trace(tid)
        assert scene.emotional_valence == 1.0


class TestPrivacyManager:
    @pytest.mark.asyncio
    async def test_classify_and_check_access(self) -> None:
        pm = PrivacyManager()
        await pm.classify("ref-1", PrivacyTier.PRIVATE, "agent-A")
        assert await pm.check_access("ref-1", "agent-A")
        assert not await pm.check_access("ref-1", "agent-B")

    @pytest.mark.asyncio
    async def test_shared_access(self) -> None:
        pm = PrivacyManager()
        await pm.classify("ref-2", PrivacyTier.SHARED, "agent-A")
        assert await pm.check_access("ref-2", "agent-B")

    @pytest.mark.asyncio
    async def test_allowed_recipients(self) -> None:
        pm = PrivacyManager()
        await pm.classify(
            "ref-3", PrivacyTier.PRIVATE, "agent-A",
            allowed_recipients=("agent-C",),
        )
        assert await pm.check_access("ref-3", "agent-C")
        assert not await pm.check_access("ref-3", "agent-D")

    @pytest.mark.asyncio
    async def test_purge_ephemeral(self) -> None:
        pm = PrivacyManager()
        await pm.classify("ep-1", PrivacyTier.EPHEMERAL, "agent-A")
        await pm.classify("dur-1", PrivacyTier.DURABLE, "agent-A")
        count = await pm.purge_ephemeral()
        assert count == 1

    @pytest.mark.asyncio
    async def test_purge_expired(self) -> None:
        pm = PrivacyManager()
        await pm.classify("exp-1", PrivacyTier.DURABLE, "agent-A", ttl=0.001)
        time.sleep(0.01)
        count = await pm.purge_expired()
        assert count == 1

    @pytest.mark.asyncio
    async def test_default_tier(self) -> None:
        pm = PrivacyManager()
        tier = await pm.get_tier("unclassified")
        assert tier == PrivacyTier.DURABLE


class TestDecayManager:
    @pytest.mark.asyncio
    async def test_priority_decay(self) -> None:
        dm = DecayManager(DecayConfig(half_life=1.0))
        await dm.register("e1", 1.0, "content")
        priority = await dm.get_priority("e1")
        assert 0.0 <= priority <= 1.0

    @pytest.mark.asyncio
    async def test_contradiction_detection(self) -> None:
        dm = DecayManager()
        emb_pos = np.array([1.0, 0.0, 0.0])
        emb_neg = np.array([-1.0, 0.0, 0.0])
        await dm.register("e1", 1.0, "positive", embedding=emb_pos)
        contradictions = await dm.find_contradictions(emb_neg, threshold=0.0)
        assert len(contradictions) >= 1

    @pytest.mark.asyncio
    async def test_evict_decayed(self) -> None:
        dm = DecayManager(DecayConfig(half_life=0.001, min_priority=0.9))
        await dm.register("e1", 0.5, "content")
        evicted = await dm.evict_decayed()
        assert "e1" in evicted

    @pytest.mark.asyncio
    async def test_boost_priority(self) -> None:
        dm = DecayManager(DecayConfig(half_life=86400.0))
        await dm.register("e1", 1.0, "content")
        await dm.boost_priority("e1", factor=2.0)
        priority = await dm.get_priority("e1")
        assert priority > 1.0


class TestDreamCycle:
    @pytest.mark.asyncio
    async def test_dream_produces_result(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "note", "Dream test event")
        dc = DreamCycle(episodic=em)
        result = await dc.dream(max_events=10)
        assert result.events_consolidated >= 1
        assert result.duration_ms >= 0.0

    @pytest.mark.asyncio
    async def test_should_dream_initial(self) -> None:
        dc = DreamCycle()
        assert await dc.should_dream()

    @pytest.mark.asyncio
    async def test_should_dream_after_recent(self) -> None:
        dc = DreamCycle()
        await dc.dream(max_events=1)
        assert not await dc.should_dream(idle_seconds=99999.0)

    @pytest.mark.asyncio
    async def test_dream_count_increments(self) -> None:
        dc = DreamCycle()
        assert dc.dream_count == 0
        await dc.dream(max_events=1)
        assert dc.dream_count == 1


class TestMemoryMCPServer:
    @pytest.mark.asyncio
    async def test_search(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "note", "MCP search test content")
        server = MemoryMCPServer(episodic=em)
        results = await server.search("search test")
        assert len(results) >= 1
        assert isinstance(results[0], MCPSearchResult)
        assert results[0].token_cost == 750

    @pytest.mark.asyncio
    async def test_timeline(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "note", "Event A")
        await em.record_event("sess-1", "note", "Event B")
        server = MemoryMCPServer(episodic=em)
        timeline = await server.timeline("ep-1", depth_before=1, depth_after=1)
        assert len(timeline) >= 1

    @pytest.mark.asyncio
    async def test_get_observations(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "note", "Full observation content")
        server = MemoryMCPServer(episodic=em)
        observations = await server.get_observations(("ep-1",))
        assert len(observations) == 1
        assert "Full observation content" in observations[0]["content"]

    @pytest.mark.asyncio
    async def test_search_events(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "tool_call", "Ran tests", tags=("ci",))
        server = MemoryMCPServer(episodic=em)
        events = await server.search_events("tests")
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_count_all(self) -> None:
        em = EpisodicMemory()
        await em.record_event("sess-1", "note", "test")
        server = MemoryMCPServer(episodic=em)
        counts = await server.count_all()
        assert counts["episodic_events"] >= 1
        assert "semantic_facts" in counts


class TestDataclassFrozen:
    def test_working_memory_entry_frozen(self) -> None:
        entry = WorkingMemoryEntry("id", "content", 1.0, 0.0, 0.0)
        with pytest.raises(AttributeError):
            entry.content = "changed"  # type: ignore[misc]

    def test_episodic_event_frozen(self) -> None:
        event = EpisodicEvent(1, "s", "t", "c", (), 0.0)
        with pytest.raises(AttributeError):
            event.content = "x"  # type: ignore[misc]

    def test_semantic_fact_frozen(self) -> None:
        fact = SemanticFact("id", "c", "cat", np.array([1.0]), 1.0, 0.0, "s")
        with pytest.raises(AttributeError):
            fact.confidence = 0.5  # type: ignore[misc]

    def test_retrieval_index_entry_frozen(self) -> None:
        entry = IndexEntry("id", "summary", "cat", 0.5)
        with pytest.raises(AttributeError):
            entry.summary = "x"  # type: ignore[misc]

    def test_procedure_frozen(self) -> None:
        proc = Procedure("id", "n", "d", (), (), (), 0, 0, 1, 0.0, 0.0)
        with pytest.raises(AttributeError):
            proc.name = "x"  # type: ignore[misc]

    def test_search_result_frozen(self) -> None:
        fact = SemanticFact("id", "c", "cat", np.array([1.0]), 1.0, 0.0, "s")
        result = SemanticSearchResult(fact=fact, score=0.9)
        with pytest.raises(AttributeError):
            result.score = 0.5  # type: ignore[misc]

    def test_symbolic_canvas_frozen(self) -> None:
        canvas = SymbolicCanvas("id", "s", (), {}, "ref")
        with pytest.raises(AttributeError):
            canvas.summary = "x"  # type: ignore[misc]

    def test_decay_config_defaults(self) -> None:
        config = DecayConfig()
        assert config.half_life == 86400.0
        assert config.min_priority == 0.1
        assert config.scan_interval == 3600.0
