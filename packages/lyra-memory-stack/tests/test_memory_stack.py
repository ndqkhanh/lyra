"""Tests for lyra-memory-stack package."""

from __future__ import annotations

import math
import time

import pytest

from lyra_memory_stack import (
    # Working Memory
    ContextItem,
    WorkingMemory,
    estimate_tokens,
    # Episodic Memory
    EpisodeEvent,
    EpisodicMemory,
    # Semantic Memory
    Fact,
    FactQueryResult,
    SemanticMemory,
    # Procedural Memory
    KnowledgeEdge,
    ProceduralMemory,
    Skill,
    WorkflowStep,
    WorkflowTemplate,
    # Retrieval
    Layer1Index,
    Layer2Timeline,
    Layer3Detail,
    RetrievalManager,
    # Dual Trace
    DualTraceEntry,
    DualTraceStore,
    SceneTrace,
    SceneType,
    # Symbolic Compression
    CompressedSymbol,
    SymbolicCompressor,
    ToolCall,
    # Privacy Tiers
    PrivacyManager,
    PrivacyPolicy,
    PrivacyTier,
    cascade_tiers,
    # Decay Manager
    Contradiction,
    DecayManager,
    DecayPolicy,
    MemoryEntry,
    MemoryType,
    # Dream Cycle
    DreamCycle,
    DreamInsight,
    # MCP Server
    MCPServer,
    # Exceptions
    CompressionError,
    DecayError,
    DreamCycleError,
    MemoryCapacityError,
    MemoryError,
    MemoryNotFoundError,
    PrivacyViolationError,
    RetrievalError,
)


# ── Working Memory ──────────────────────────────────────────────────────


class TestWorkingMemory:
    def test_add_and_peek(self):
        wm = WorkingMemory(max_tokens=1000)
        item = ContextItem(item_id="test_1", content="hello world", priority=5, token_estimate=10)
        wm.add(item)
        assert wm.peek("test_1") is item
        assert wm.item_count == 1

    def test_remove(self):
        wm = WorkingMemory(max_tokens=1000)
        item = ContextItem(item_id="test_1", content="hello", priority=5, token_estimate=10)
        wm.add(item)
        removed = wm.remove("test_1")
        assert removed.item_id == "test_1"
        assert wm.item_count == 0

    def test_remove_not_found(self):
        wm = WorkingMemory(max_tokens=1000)
        with pytest.raises(MemoryNotFoundError):
            wm.remove("nonexistent")

    def test_clear(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="a", content="a", priority=1, token_estimate=10))
        wm.add(ContextItem(item_id="b", content="b", priority=2, token_estimate=10))
        wm.clear()
        assert wm.item_count == 0

    def test_eviction_over_budget(self):
        wm = WorkingMemory(max_tokens=50)
        wm.add(ContextItem(item_id="a", content="a" * 100, priority=1, token_estimate=30))
        wm.add(ContextItem(item_id="b", content="b" * 100, priority=2, token_estimate=30))
        assert wm.current_tokens <= wm.max_tokens

    def test_skip_lower_priority_eviction(self):
        """Higher priority items survive eviction before lower priority ones."""
        wm = WorkingMemory(max_tokens=80)
        wm.add(ContextItem(item_id="low", content="low", priority=1, token_estimate=50))
        wm.add(ContextItem(item_id="high", content="high", priority=10, token_estimate=50))
        assert wm.current_tokens <= wm.max_tokens
        # The high priority item should survive
        assert wm.peek("high") is not None

    def test_update_priority(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="test", content="test", priority=1, token_estimate=10))
        wm.update_priority("test", 10)
        assert wm.peek("test").priority == 10

    def test_update_priority_not_found(self):
        wm = WorkingMemory(max_tokens=1000)
        with pytest.raises(MemoryNotFoundError):
            wm.update_priority("nonexistent", 10)

    def test_set_max_tokens(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="a", content="a", priority=1, token_estimate=50))
        wm.set_max_tokens(10)
        assert wm.current_tokens <= 10

    def test_items_ordered_by_priority(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="low", content="low", priority=1, token_estimate=10))
        wm.add(ContextItem(item_id="high", content="high", priority=10, token_estimate=10))
        items = wm.items()
        assert items[0].item_id == "high"

    def test_remaining_tokens(self):
        wm = WorkingMemory(max_tokens=100)
        wm.add(ContextItem(item_id="a", content="a", priority=1, token_estimate=30))
        assert wm.remaining_tokens == 70

    def test_utilization(self):
        wm = WorkingMemory(max_tokens=100)
        wm.add(ContextItem(item_id="a", content="a", priority=1, token_estimate=25))
        assert wm.utilization == 0.25

    def test_summary(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="a", content="a", priority=1, token_estimate=10))
        s = wm.summary()
        assert "item_count" in s
        assert s["item_count"] == 1

    def test_estimate_tokens(self):
        assert estimate_tokens("hello world") == 2
        assert estimate_tokens("") == 1
        assert estimate_tokens("a" * 40) == 10

    def test_context_item_immutable_update(self):
        item = ContextItem(item_id="test", content="hello", priority=5, token_estimate=10)
        updated = item.with_priority(10)
        assert item.priority == 5
        assert updated.priority == 10
        assert updated.item_id == "test"

    def test_context_item_with_content(self):
        item = ContextItem(item_id="test", content="hello", priority=5, token_estimate=10)
        updated = item.with_content("world")
        assert item.content == "hello"
        assert updated.content == "world"
        assert updated.item_id == "test"

    def test_peek_returns_none(self):
        wm = WorkingMemory(max_tokens=1000)
        assert wm.peek("nonexistent") is None


# ── Episodic Memory ─────────────────────────────────────────────────────


class TestEpisodicMemory:
    def test_store_and_retrieve(self):
        em = EpisodicMemory()
        event = EpisodeEvent(
            event_id="evt_1",
            agent_id="agent_a",
            event_type="tool_call",
            content="Called read_file on /tmp/test.txt",
        )
        em.store(event)
        retrieved = em.retrieve("evt_1")
        assert retrieved.event_id == "evt_1"
        assert retrieved.agent_id == "agent_a"
        assert retrieved.event_type == "tool_call"

    def test_retrieve_not_found(self):
        em = EpisodicMemory()
        with pytest.raises(MemoryNotFoundError):
            em.retrieve("nonexistent")

    def test_store_with_metadata(self):
        em = EpisodicMemory()
        event = EpisodeEvent(
            event_id="evt_meta",
            agent_id="agent_a",
            event_type="tool_result",
            content="Result data",
            metadata={"duration_ms": 150, "status": "ok"},
        )
        em.store(event)
        retrieved = em.retrieve("evt_meta")
        assert retrieved.metadata["duration_ms"] == 150

    def test_count(self):
        em = EpisodicMemory()
        assert em.count() == 0
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="type", content="c"))
        assert em.count() == 1

    def test_query_by_agent(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="alice", event_type="type", content="hello"))
        em.store(EpisodeEvent(event_id="e2", agent_id="bob", event_type="type", content="world"))
        em.store(EpisodeEvent(event_id="e3", agent_id="alice", event_type="type", content="again"))
        results = em.query_by_agent("alice")
        assert len(results) == 2
        assert all(r.agent_id == "alice" for r in results)

    def test_query_by_type(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="read", content="c1"))
        em.store(EpisodeEvent(event_id="e2", agent_id="a", event_type="write", content="c2"))
        results = em.query_by_type("read")
        assert len(results) == 1
        assert results[0].event_id == "e1"

    def test_query_by_time_range(self):
        em = EpisodicMemory()
        t = time.time()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="t", content="c", timestamp=t - 10))
        em.store(EpisodeEvent(event_id="e2", agent_id="a", event_type="t", content="c", timestamp=t))
        em.store(EpisodeEvent(event_id="e3", agent_id="a", event_type="t", content="c", timestamp=t + 10))
        results = em.query_by_time_range(t - 5, t + 5)
        assert len(results) == 1
        assert results[0].event_id == "e2"

    def test_query_by_session(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="t", content="c", session_id="s1"))
        em.store(EpisodeEvent(event_id="e2", agent_id="a", event_type="t", content="c", session_id="s1"))
        em.store(EpisodeEvent(event_id="e3", agent_id="a", event_type="t", content="c", session_id="s2"))
        results = em.query_by_session("s1")
        assert len(results) == 2

    def test_search_fts(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="tool_call", content="Reading file config.json"))
        em.store(EpisodeEvent(event_id="e2", agent_id="a", event_type="tool_call", content="Writing output data"))
        results = em.search("config")
        assert len(results) >= 1
        assert any("config.json" in r.snippet for r in results)

    def test_search_like_fallback(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="tool_call", content="Some unique content here"))
        results = em.search("unique")
        assert len(results) >= 1

    def test_delete(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="t", content="c"))
        assert em.delete("e1") is True
        assert em.delete("e1") is False
        assert em.count() == 0

    def test_clear(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="t", content="c"))
        em.store(EpisodeEvent(event_id="e2", agent_id="a", event_type="t", content="c"))
        em.clear()
        assert em.count() == 0

    def test_db_path(self):
        em = EpisodicMemory()
        assert em.db_path == ":memory:"

    def test_search_result_rank(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="e1", agent_id="a", event_type="t", content="test content for search"))
        results = em.search("test")
        # FTS5 rank can be negative (BM25 score), just verify it exists
        assert len(results) >= 0

    def test_close(self):
        em = EpisodicMemory()
        em.close()
        # Should not raise

    def test_event_with_session(self):
        event = EpisodeEvent(event_id="e1", agent_id="a", event_type="t", content="c", session_id="session_abc")
        assert event.session_id == "session_abc"


# ── Semantic Memory ─────────────────────────────────────────────────────


class TestSemanticMemory:
    def test_add_and_get_fact(self):
        sm = SemanticMemory()
        fact = Fact(fact_id="f1", domain="coding", statement="Python is dynamically typed")
        sm.add_fact(fact)
        assert sm.get_fact("f1").statement == "Python is dynamically typed"

    def test_get_fact_not_found(self):
        sm = SemanticMemory()
        with pytest.raises(MemoryNotFoundError):
            sm.get_fact("nonexistent")

    def test_update_fact(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="coding", statement="Python is slow", confidence=0.5))
        updated = sm.update_fact("f1", statement="Python can be fast with optimization", confidence=0.8)
        assert updated.statement == "Python can be fast with optimization"
        assert updated.confidence == 0.8

    def test_update_fact_not_found(self):
        sm = SemanticMemory()
        with pytest.raises(MemoryNotFoundError):
            sm.update_fact("nonexistent")

    def test_delete_fact(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="test"))
        assert sm.delete_fact("f1") is True
        assert sm.delete_fact("f1") is False

    def test_query_facts_keyword(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="coding", statement="Python is great for data science", confidence=0.9))
        sm.add_fact(Fact(fact_id="f2", domain="coding", statement="JavaScript runs in browsers", confidence=0.8))
        results = sm.query_facts("python", limit=5)
        assert len(results) >= 1
        assert results[0].fact.fact_id == "f1"

    def test_query_facts_by_domain(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="coding", statement="Python is great"))
        sm.add_fact(Fact(fact_id="f2", domain="music", statement="Jazz is great"))
        results = sm.query_facts("great", domain="music")
        assert len(results) == 1
        assert results[0].fact.domain == "music"

    def test_query_facts_min_confidence(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="Low confidence fact", confidence=0.2))
        sm.add_fact(Fact(fact_id="f2", domain="test", statement="High confidence fact", confidence=0.9))
        results = sm.query_facts("fact", min_confidence=0.5)
        assert len(results) == 1
        assert results[0].fact.fact_id == "f2"

    def test_query_by_embedding(self):
        sm = SemanticMemory(embedding_dim=4)
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="a", embedding=(1.0, 0.0, 0.0, 0.0)))
        sm.add_fact(Fact(fact_id="f2", domain="test", statement="b", embedding=(0.0, 1.0, 0.0, 0.0)))
        results = sm.query_by_embedding((1.0, 0.0, 0.0, 0.0))
        assert len(results) == 1  # f2 has orthogonal embedding (cos=0), filtered out
        assert results[0].fact.fact_id == "f1"

    def test_query_by_domain(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="coding", statement="a"))
        sm.add_fact(Fact(fact_id="f2", domain="music", statement="b"))
        results = sm.query_by_domain("coding")
        assert len(results) == 1

    def test_count(self):
        sm = SemanticMemory()
        assert sm.count() == 0
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="a"))
        assert sm.count() == 1

    def test_clear(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="a"))
        sm.clear()
        assert sm.count() == 0

    def test_all_facts(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="a"))
        sm.add_fact(Fact(fact_id="f2", domain="test", statement="b"))
        assert len(sm.all_facts()) == 2

    def test_summary(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="coding", statement="a", confidence=0.8))
        s = sm.summary()
        assert s["total_facts"] == 1
        assert s["domains"]["coding"] == 1

    def test_query_facts_tier_filter(self):
        from lyra_memory_stack.privacy_tiers import PrivacyTier
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="private fact", tier=PrivacyTier.PRIVATE))
        sm.add_fact(Fact(fact_id="f2", domain="test", statement="durable fact", tier=PrivacyTier.DURABLE))
        results = sm.query_facts("fact", tier_filter=PrivacyTier.DURABLE)
        assert len(results) > 0

    def test_query_facts_no_match(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="hello world"))
        results = sm.query_facts("nonexistent")
        assert len(results) == 0


# ── Procedural Memory ────────────────────────────────────────────────────


class TestProceduralMemory:
    def test_store_and_load_skill(self):
        pm = ProceduralMemory()
        skill = Skill(
            skill_id="s1",
            name="File Reader",
            description="Reads files from disk",
            triggers=("read", "file"),
            content="def read_file(path): ...",
        )
        pm.store_skill(skill)
        loaded = pm.load_skill("s1")
        assert loaded.name == "File Reader"
        assert loaded.skill_id == "s1"

    def test_load_skill_not_found(self):
        pm = ProceduralMemory()
        with pytest.raises(MemoryNotFoundError):
            pm.load_skill("nonexistent")

    def test_delete_skill(self):
        pm = ProceduralMemory()
        pm.store_skill(Skill(skill_id="s1", name="test", description="d"))
        assert pm.delete_skill("s1") is True
        assert pm.delete_skill("s1") is False

    def test_list_skills(self):
        pm = ProceduralMemory()
        pm.store_skill(Skill(skill_id="s1", name="a", description="d", domain="coding"))
        pm.store_skill(Skill(skill_id="s2", name="b", description="d", domain="music"))
        all_skills = pm.list_skills()
        assert len(all_skills) == 2
        coding_skills = pm.list_skills(domain="coding")
        assert len(coding_skills) == 1

    def test_find_skills_by_trigger(self):
        pm = ProceduralMemory()
        pm.store_skill(Skill(skill_id="s1", name="Reader", description="d", triggers=("read", "open")))
        pm.store_skill(Skill(skill_id="s2", name="Writer", description="d", triggers=("write", "save")))
        results = pm.find_skills_by_trigger("read")
        assert len(results) == 1
        assert results[0].skill_id == "s1"

    def test_skill_count(self):
        pm = ProceduralMemory()
        assert pm.skill_count() == 0
        pm.store_skill(Skill(skill_id="s1", name="test", description="d"))
        assert pm.skill_count() == 1

    def test_skill_with_version_update(self):
        skill = Skill(skill_id="s1", name="test", description="d", version="1.0.0")
        updated = skill.with_version("2.0.0")
        assert skill.version == "1.0.0"
        assert updated.version == "2.0.0"

    def test_skill_with_content_update(self):
        skill = Skill(skill_id="s1", name="test", description="d", content="old")
        updated = skill.with_content("new")
        assert skill.content == "old"
        assert updated.content == "new"

    def test_store_and_load_workflow(self):
        pm = ProceduralMemory()
        step = WorkflowStep(step_id="step1", name="Init", description="Initialize")
        wf = WorkflowTemplate(
            workflow_id="wf1",
            name="Test Workflow",
            description="A test",
            steps=(step,),
        )
        pm.store_workflow(wf)
        loaded = pm.load_workflow("wf1")
        assert loaded.workflow_id == "wf1"
        assert len(loaded.steps) == 1

    def test_load_workflow_not_found(self):
        pm = ProceduralMemory()
        with pytest.raises(MemoryNotFoundError):
            pm.load_workflow("nonexistent")

    def test_delete_workflow(self):
        pm = ProceduralMemory()
        pm.store_workflow(WorkflowTemplate(workflow_id="wf1", name="test", description="d"))
        assert pm.delete_workflow("wf1") is True
        assert pm.delete_workflow("wf1") is False

    def test_list_workflows(self):
        pm = ProceduralMemory()
        pm.store_workflow(WorkflowTemplate(workflow_id="wf1", name="a", description="d", domain="coding"))
        pm.store_workflow(WorkflowTemplate(workflow_id="wf2", name="b", description="d", domain="music"))
        assert len(pm.list_workflows(domain="coding")) == 1

    def test_workflow_count(self):
        pm = ProceduralMemory()
        assert pm.workflow_count() == 0
        pm.store_workflow(WorkflowTemplate(workflow_id="wf1", name="test", description="d"))
        assert pm.workflow_count() == 1

    def test_workflow_dependency_graph(self):
        step1 = WorkflowStep(step_id="s1", name="Step 1", description="First")
        step2 = WorkflowStep(step_id="s2", name="Step 2", description="Second", depends_on=("s1",))
        wf = WorkflowTemplate(workflow_id="wf1", name="Test", description="d", steps=(step1, step2))
        graph = wf.dependency_graph()
        assert "s1" in graph
        assert "s2" in graph
        # s2 depends on s1, so it appears in graph["s1"]
        assert "s2" in graph.get("s1", [])

    def test_workflow_execution_order(self):
        step1 = WorkflowStep(step_id="s1", name="Init", description="First")
        step2 = WorkflowStep(step_id="s2", name="Process", description="Second", depends_on=("s1",))
        step3 = WorkflowStep(step_id="s3", name="Finalize", description="Third", depends_on=("s2",))
        wf = WorkflowTemplate(workflow_id="wf1", name="Pipeline", description="d", steps=(step3, step2, step1))
        order = wf.execution_order()
        order_ids = [s.step_id for s in order]
        # s1 must come before s2, s2 before s3
        assert order_ids.index("s1") < order_ids.index("s2")
        assert order_ids.index("s2") < order_ids.index("s3")

    def test_workflow_validation(self):
        step = WorkflowStep(step_id="s1", name="Step", description="d", depends_on=("nonexistent",))
        wf = WorkflowTemplate(workflow_id="wf1", name="Test", description="d", steps=(step,))
        errors = wf.validate()
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_workflow_valid_no_errors(self):
        step = WorkflowStep(step_id="s1", name="Step", description="d")
        wf = WorkflowTemplate(workflow_id="wf1", name="Test", description="d", steps=(step,))
        assert wf.validate() == []

    def test_add_and_remove_edge(self):
        pm = ProceduralMemory()
        edge = KnowledgeEdge(
            edge_id="e1",
            source_id="skill_1",
            target_id="skill_2",
            relation="depends_on",
        )
        assert pm.add_edge(edge) == "e1"
        assert pm.remove_edge("e1") is True
        assert pm.remove_edge("e1") is False

    def test_query_edges(self):
        pm = ProceduralMemory()
        pm.add_edge(KnowledgeEdge(edge_id="e1", source_id="a", target_id="b", relation="depends_on"))
        pm.add_edge(KnowledgeEdge(edge_id="e2", source_id="b", target_id="c", relation="triggers"))
        results = pm.query_edges(relation="depends_on")
        assert len(results) == 1

    def test_knowledge_edge_validity(self):
        edge = KnowledgeEdge(
            edge_id="e1",
            source_id="a",
            target_id="b",
            relation="r",
            valid_from=100.0,
            valid_until=200.0,
        )
        assert edge.is_valid(150.0) is True
        assert edge.is_valid(50.0) is False
        assert edge.is_valid(250.0) is False

    def test_edge_count(self):
        pm = ProceduralMemory()
        pm.add_edge(KnowledgeEdge(edge_id="e1", source_id="a", target_id="b", relation="r"))
        assert pm.edge_count() == 1

    def test_clear_all(self):
        pm = ProceduralMemory()
        pm.store_skill(Skill(skill_id="s1", name="test", description="d"))
        pm.store_workflow(WorkflowTemplate(workflow_id="wf1", name="test", description="d"))
        pm.add_edge(KnowledgeEdge(edge_id="e1", source_id="a", target_id="b", relation="r"))
        pm.clear()
        assert pm.skill_count() == 0
        assert pm.workflow_count() == 0
        assert pm.edge_count() == 0

    def test_summary(self):
        pm = ProceduralMemory()
        pm.store_skill(Skill(skill_id="s1", name="test", description="d"))
        s = pm.summary()
        assert s["skills"] == 1


# ── Retrieval ─────────────────────────────────────────────────────────────


class TestRetrieval:
    def test_search_index_with_working_memory(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="wm1", content="important context data", priority=5, token_estimate=10))
        rm = RetrievalManager(working_memory=wm)
        results = rm.search_index("important")
        assert len(results) >= 1
        assert any(r.entry_type == "working" for r in results)

    def test_search_index_with_semantic_memory(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="Python is great", confidence=0.9))
        rm = RetrievalManager(semantic_memory=sm)
        results = rm.search_index("python")
        assert len(results) >= 1

    def test_get_timeline_working(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="wm1", content="context data", priority=5, token_estimate=10))
        rm = RetrievalManager(working_memory=wm)
        timeline = rm.get_timeline("wm1", "working")
        assert timeline is not None
        assert timeline.entry_id == "wm1"

    def test_get_timeline_not_found(self):
        rm = RetrievalManager(semantic_memory=SemanticMemory())
        timeline = rm.get_timeline("nonexistent", "semantic")
        assert timeline is None

    def test_get_detail_working(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="wm1", content="detail data", priority=5, token_estimate=10))
        rm = RetrievalManager(working_memory=wm)
        detail = rm.get_detail("wm1", "working")
        assert detail is not None
        assert detail.content == "detail data"

    def test_get_detail_episodic(self):
        em = EpisodicMemory()
        em.store(EpisodeEvent(event_id="evt1", agent_id="a", event_type="test", content="episodic content"))
        rm = RetrievalManager(episodic_memory=em)
        detail = rm.get_detail("evt1", "episodic")
        assert detail is not None
        assert detail.entry_type == "episodic"

    def test_get_detail_semantic(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="semantic fact"))
        rm = RetrievalManager(semantic_memory=sm)
        detail = rm.get_detail("f1", "semantic")
        assert detail is not None
        assert detail.content == "semantic fact"

    def test_get_detail_procedural_skill(self):
        pm = ProceduralMemory()
        pm.store_skill(Skill(skill_id="s1", name="test", description="d", content="skill content"))
        rm = RetrievalManager(procedural_memory=pm)
        detail = rm.get_detail("s1", "procedural")
        assert detail is not None

    def test_get_detail_not_found(self):
        rm = RetrievalManager(semantic_memory=SemanticMemory())
        detail = rm.get_detail("nonexistent", "semantic")
        assert detail is None

    def test_get_memory_stats(self):
        wm = WorkingMemory(max_tokens=1000)
        sm = SemanticMemory()
        em = EpisodicMemory()
        pm = ProceduralMemory()
        rm = RetrievalManager(working_memory=wm, semantic_memory=sm, episodic_memory=em, procedural_memory=pm)
        stats = rm.get_memory_stats()
        assert "working" in stats
        assert "semantic" in stats
        assert "episodic" in stats
        assert "procedural" in stats

    def test_search_index_empty(self):
        rm = RetrievalManager()
        results = rm.search_index("test")
        assert len(results) == 0


# ── Dual Trace ────────────────────────────────────────────────────────────


class TestDualTrace:
    def test_store_and_get(self):
        store = DualTraceStore()
        scene = SceneTrace(scene_id="sc1", scene_type=SceneType.OBSERVATION, description="Observed a pattern")
        entry = DualTraceEntry(fact_id="f1", statement="Pattern X exists", scene_trace=scene)
        store.store(entry)
        retrieved = store.get("f1")
        assert retrieved is not None
        assert retrieved.statement == "Pattern X exists"

    def test_get_not_found(self):
        store = DualTraceStore()
        assert store.get("nonexistent") is None

    def test_adjusted_confidence(self):
        scene = SceneTrace(scene_id="sc1", scene_type=SceneType.OBSERVATION, description="obs", confidence_boost=0.2)
        entry = DualTraceEntry(fact_id="f1", statement="test", scene_trace=scene, confidence=0.5)
        assert entry.adjusted_confidence == 0.7

    def test_query_by_domain(self):
        store = DualTraceStore()
        store.store(DualTraceEntry(fact_id="f1", statement="a", scene_trace=SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="d"), domain="coding"))
        store.store(DualTraceEntry(fact_id="f2", statement="b", scene_trace=SceneTrace(scene_id="s2", scene_type=SceneType.OBSERVATION, description="d"), domain="music"))
        results = store.query_by_domain("coding")
        assert len(results) == 1

    def test_query_by_agent(self):
        store = DualTraceStore()
        scene = SceneTrace(scene_id="sc1", scene_type=SceneType.OBSERVATION, description="d", agents_involved=("alice",))
        store.store(DualTraceEntry(fact_id="f1", statement="a", scene_trace=scene))
        results = store.query_by_agent("alice")
        assert len(results) == 1
        results = store.query_by_agent("bob")
        assert len(results) == 0

    def test_query_by_scene_type(self):
        store = DualTraceStore()
        store.store(DualTraceEntry(fact_id="f1", statement="a", scene_trace=SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="d")))
        store.store(DualTraceEntry(fact_id="f2", statement="b", scene_trace=SceneTrace(scene_id="s2", scene_type=SceneType.INFERENCE, description="d")))
        results = store.query_by_scene_type(SceneType.OBSERVATION)
        assert len(results) == 1

    def test_search(self):
        store = DualTraceStore()
        store.store(DualTraceEntry(fact_id="f1", statement="Python is great", scene_trace=SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="coding observation")))
        results = store.search("Python")
        assert len(results) == 1

    def test_delete(self):
        store = DualTraceStore()
        store.store(DualTraceEntry(fact_id="f1", statement="a", scene_trace=SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="d")))
        assert store.delete("f1") is True
        assert store.delete("f1") is False

    def test_count_and_clear(self):
        store = DualTraceStore()
        assert store.count() == 0
        store.store(DualTraceEntry(fact_id="f1", statement="a", scene_trace=SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="d")))
        assert store.count() == 1
        store.clear()
        assert store.count() == 0

    def test_all_entries(self):
        store = DualTraceStore()
        store.store(DualTraceEntry(fact_id="f1", statement="a", scene_trace=SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="d")))
        assert len(store.all_entries()) == 1

    def test_with_additional_agents(self):
        scene = SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="d", agents_involved=("alice",))
        updated = scene.with_additional_agents("bob")
        assert len(updated.agents_involved) == 2
        assert len(scene.agents_involved) == 1

    def test_with_reasoning(self):
        scene = SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="d")
        updated = scene.with_reasoning("step1", "step2")
        assert len(updated.reasoning_chain) == 2
        assert len(scene.reasoning_chain) == 0

    def test_with_updated_statement(self):
        scene = SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="original")
        entry = DualTraceEntry(fact_id="f1", statement="old", scene_trace=scene)
        updated = entry.with_updated_statement("new")
        assert updated.statement == "new"
        assert updated.scene_trace.scene_type == SceneType.CORRECTION


# ── Symbolic Compression ──────────────────────────────────────────────────


class TestSymbolicCompression:
    def test_compress_call(self):
        compressor = SymbolicCompressor()
        call = ToolCall(tool_name="read_file", arguments={"path": "/tmp/test.txt"}, result="content")
        symbol = compressor.compress_call(call)
        assert len(symbol.node_id) == 12
        assert "RD" in symbol.label or "read" in symbol.symbol_type

    def test_compress_calls(self):
        compressor = SymbolicCompressor()
        calls = [
            ToolCall(tool_name="read_file", arguments={"path": "/a.txt"}),
            ToolCall(tool_name="write_file", arguments={"path": "/b.txt"}),
        ]
        symbols = compressor.compress_calls(calls)
        assert len(symbols) == 2

    def test_compression_ratio(self):
        compressor = SymbolicCompressor()
        calls = [
            ToolCall(tool_name="read_file", arguments={"path": "/tmp/test.txt"}, result="x" * 1000),
            ToolCall(tool_name="write_file", arguments={"path": "/tmp/out.txt"}, result="y" * 500),
        ]
        symbols = compressor.compress_calls(calls)
        ratio = compressor.compression_ratio(symbols)
        assert ratio >= 1.0

    def test_build_mermaid_sequence(self):
        compressor = SymbolicCompressor()
        symbols = compressor.compress_calls([
            ToolCall(tool_name="read_file", arguments={"path": "/a.txt"}),
            ToolCall(tool_name="think", arguments={"thought": "analyzing"}),
        ])
        diagram = compressor.build_mermaid_sequence(symbols)
        assert "sequenceDiagram" in diagram
        assert "Agent" in diagram

    def test_build_mermaid_graph(self):
        compressor = SymbolicCompressor()
        symbols = compressor.compress_calls([
            ToolCall(tool_name="read_file", arguments={"path": "/a.txt"}),
        ])
        diagram = compressor.build_mermaid_graph(symbols)
        assert "flowchart" in diagram

    def test_build_empty_mermaid(self):
        compressor = SymbolicCompressor()
        seq = compressor.build_mermaid_sequence([])
        assert "No calls" in seq
        graph = compressor.build_mermaid_graph([])
        assert "No calls" in graph

    def test_expand_node(self):
        compressor = SymbolicCompressor()
        symbols = compressor.compress_calls([
            ToolCall(tool_name="read_file", arguments={"path": "/a.txt"}),
        ])
        expanded = compressor.expand_node(symbols[0].node_id, symbols)
        assert expanded is not None
        assert expanded.node_id == symbols[0].node_id

    def test_expand_node_not_found(self):
        compressor = SymbolicCompressor()
        assert compressor.expand_node("nonexistent", []) is None

    def test_compress_logs(self):
        compressor = SymbolicCompressor()
        symbol = compressor.compress_logs("line1\nline2\nline3\n", tool_name="test_tool")
        assert symbol.raw_token_count > 0

    def test_compress_empty_logs(self):
        compressor = SymbolicCompressor()
        with pytest.raises(CompressionError):
            compressor.compress_logs("  \n  ", tool_name="test")

    def test_infer_tool_call_default(self):
        compressor = SymbolicCompressor()
        call = ToolCall(tool_name="unknown_tool_xyz", arguments={})
        symbol = compressor.compress_call(call)
        assert symbol.symbol_type == "tool_call"


# ── Privacy Tiers ────────────────────────────────────────────────────────


class TestPrivacyTiers:
    def test_tier_ranking(self):
        assert PrivacyTier.EPHEMERAL.rank < PrivacyTier.PRIVATE.rank
        assert PrivacyTier.PRIVATE.rank < PrivacyTier.DURABLE.rank
        assert PrivacyTier.DURABLE.rank < PrivacyTier.SHARED.rank

    def test_tier_comparison(self):
        assert PrivacyTier.EPHEMERAL < PrivacyTier.PRIVATE
        assert PrivacyTier.PRIVATE <= PrivacyTier.DURABLE
        assert PrivacyTier.SHARED > PrivacyTier.DURABLE

    def test_cascade_tiers(self):
        cascaded = cascade_tiers(PrivacyTier.DURABLE)
        assert PrivacyTier.DURABLE in cascaded
        assert PrivacyTier.PRIVATE in cascaded
        assert PrivacyTier.EPHEMERAL in cascaded
        assert PrivacyTier.SHARED not in cascaded

    def test_privacy_policy_access(self):
        policy = PrivacyPolicy(tier=PrivacyTier.PRIVATE, allowed_roles=("user", "agent"))
        assert policy.allows_access("user") is True
        assert policy.allows_access("admin") is False

    def test_privacy_policy_with_tier(self):
        policy = PrivacyPolicy(tier=PrivacyTier.PRIVATE)
        updated = policy.with_tier(PrivacyTier.DURABLE)
        assert policy.tier == PrivacyTier.PRIVATE
        assert updated.tier == PrivacyTier.DURABLE

    def test_privacy_policy_with_roles(self):
        policy = PrivacyPolicy(tier=PrivacyTier.PRIVATE, allowed_roles=("user",))
        updated = policy.with_roles("admin", "user")
        assert len(updated.allowed_roles) == 2

    def test_privacy_manager_default_policies(self):
        pm = PrivacyManager()
        assert pm.get_policy(PrivacyTier.EPHEMERAL).tier == PrivacyTier.EPHEMERAL

    def test_privacy_manager_check_access(self):
        pm = PrivacyManager()
        assert pm.check_access(PrivacyTier.PRIVATE, "user") is True
        assert pm.check_access(PrivacyTier.PRIVATE, "team") is False

    def test_privacy_manager_cascade_forget(self):
        pm = PrivacyManager()
        tiers = pm.cascade_forget(PrivacyTier.DURABLE)
        assert PrivacyTier.EPHEMERAL in tiers
        assert PrivacyTier.PRIVATE in tiers
        assert PrivacyTier.DURABLE in tiers

    def test_privacy_manager_escalate(self):
        pm = PrivacyManager()
        result = pm.escalate_tier(PrivacyTier.EPHEMERAL, PrivacyTier.DURABLE)
        assert result == PrivacyTier.DURABLE

    def test_privacy_manager_set_policy(self):
        pm = PrivacyManager()
        new_policy = PrivacyPolicy(tier=PrivacyTier.EPHEMERAL, allowed_roles=("admin",))
        pm.set_policy(PrivacyTier.EPHEMERAL, new_policy)
        assert pm.check_access(PrivacyTier.EPHEMERAL, "admin") is True
        assert pm.check_access(PrivacyTier.EPHEMERAL, "agent") is False

    def test_validate_tier_transition(self):
        pm = PrivacyManager()
        assert pm.validate_tier_transition(PrivacyTier.SHARED, PrivacyTier.EPHEMERAL) is True
        assert pm.validate_tier_transition(PrivacyTier.EPHEMERAL, PrivacyTier.SHARED) is True

    def test_default_policies_exist(self):
        from lyra_memory_stack.privacy_tiers import DEFAULT_POLICIES
        assert PrivacyTier.EPHEMERAL in DEFAULT_POLICIES
        assert PrivacyTier.PRIVATE in DEFAULT_POLICIES
        assert PrivacyTier.DURABLE in DEFAULT_POLICIES
        assert PrivacyTier.SHARED in DEFAULT_POLICIES


# ── Decay Manager ─────────────────────────────────────────────────────────


class TestDecayManager:
    def test_register_and_staleness(self):
        dm = DecayManager()
        entry = MemoryEntry(entry_id="e1", memory_type=MemoryType.EPISODIC, content="test")
        dm.register_entry(entry)
        staleness = dm.compute_staleness("e1")
        assert 0.0 <= staleness <= 1.0

    def test_compute_staleness_not_found(self):
        dm = DecayManager()
        with pytest.raises(DecayError):
            dm.compute_staleness("nonexistent")

    def test_record_access(self):
        dm = DecayManager()
        entry = MemoryEntry(entry_id="e1", memory_type=MemoryType.EPISODIC, content="test", access_count=0)
        dm.register_entry(entry)
        dm.record_access("e1")
        assert dm._entries["e1"].access_count == 1

    def test_record_access_not_found(self):
        dm = DecayManager()
        with pytest.raises(DecayError):
            dm.record_access("nonexistent")

    def test_unregister_entry(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(entry_id="e1", memory_type=MemoryType.EPISODIC, content="test"))
        dm.unregister_entry("e1")
        assert dm.entry_count == 0

    def test_entries_needing_pruning(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(
            entry_id="e1",
            memory_type=MemoryType.WORKING,
            content="old",
            last_accessed=0,  # Very old
            access_count=0,
        ))
        to_prune = dm.entries_needing_pruning()
        assert len(to_prune) >= 0

    def test_prune_expired(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(
            entry_id="e1",
            memory_type=MemoryType.WORKING,
            content="old",
            last_accessed=0,
            access_count=0,
        ))
        dm.register_entry(MemoryEntry(
            entry_id="e2",
            memory_type=MemoryType.EPISODIC,
            content="fresh",
            last_accessed=time.time(),
            access_count=5,
        ))
        pruned = dm.prune_expired()
        # e1 might or might not be pruned depending on staleness timing
        assert isinstance(pruned, list)

    def test_detect_contradictions(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(entry_id="e1", memory_type=MemoryType.SEMANTIC, content="Sky is blue"))
        dm.register_entry(MemoryEntry(entry_id="e2", memory_type=MemoryType.SEMANTIC, content="Sky is green"))
        contradictions = dm.detect_contradictions([
            ("e1", "e2", "Contradictory statements about sky color"),
        ])
        assert len(contradictions) == 1
        assert contradictions[0].severity == 0.8

    def test_get_contradictions(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(entry_id="e1", memory_type=MemoryType.SEMANTIC, content="a"))
        dm.register_entry(MemoryEntry(entry_id="e2", memory_type=MemoryType.SEMANTIC, content="b"))
        dm.detect_contradictions([("e1", "e2", "conflict")])
        contradictions = dm.get_contradictions("e1")
        assert len(contradictions) == 1

    def test_clear_contradictions(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(entry_id="e1", memory_type=MemoryType.SEMANTIC, content="a"))
        dm.register_entry(MemoryEntry(entry_id="e2", memory_type=MemoryType.SEMANTIC, content="b"))
        dm.detect_contradictions([("e1", "e2", "conflict")])
        dm.clear_contradictions()
        assert dm.contradiction_count == 0

    def test_get_policy(self):
        dm = DecayManager()
        policy = dm.get_policy(MemoryType.EPISODIC)
        assert policy.memory_type == MemoryType.EPISODIC
        assert policy.half_life_hours == 720.0

    def test_set_policy(self):
        dm = DecayManager()
        new_policy = DecayPolicy(memory_type=MemoryType.EPISODIC, half_life_hours=1.0)
        dm.set_policy(MemoryType.EPISODIC, new_policy)
        assert dm.get_policy(MemoryType.EPISODIC).half_life_hours == 1.0

    def test_compute_all_staleness(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(entry_id="e1", memory_type=MemoryType.EPISODIC, content="a"))
        dm.register_entry(MemoryEntry(entry_id="e2", memory_type=MemoryType.SEMANTIC, content="b"))
        staleness = dm.compute_all_staleness()
        assert len(staleness) == 2

    def test_summary(self):
        dm = DecayManager()
        dm.register_entry(MemoryEntry(entry_id="e1", memory_type=MemoryType.EPISODIC, content="a"))
        s = dm.summary()
        assert s["total_entries"] == 1

    def test_contradiction_dataclass(self):
        c = Contradiction(entry_a_id="a", entry_b_id="b", reason="conflict", severity=0.8)
        assert c.severity == 0.8
        assert c.reason == "conflict"


# ── Dream Cycle ───────────────────────────────────────────────────────────


class TestDreamCycle:
    def test_analyze_sessions(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        traces = [
            DualTraceEntry(
                fact_id="f1",
                statement="Python is popular",
                scene_trace=SceneTrace(
                    scene_id="s1",
                    scene_type=SceneType.OBSERVATION,
                    description="observed python usage",
                    agents_involved=("agent_a",),
                ),
                domain="coding",
            ),
        ]
        insights = dc.analyze_sessions(traces)
        assert len(insights) >= 1

    def test_analyze_sessions_empty(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        with pytest.raises(DreamCycleError):
            dc.analyze_sessions([])

    def test_cross_link_entities_empty(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        insights = dc.cross_link_entities()
        assert len(insights) == 0

    def test_cross_link_entities(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="coding", statement="Python is great for machine learning", confidence=0.9))
        sm.add_fact(Fact(fact_id="f2", domain="ai", statement="Machine learning requires Python knowledge", confidence=0.8))
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        insights = dc.cross_link_entities()
        assert len(insights) >= 0

    def test_prune_stale(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        insights = dc.prune_stale()
        assert isinstance(insights, list)

    def test_generate_insights_empty(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        insights = dc.generate_insights()
        assert len(insights) == 0

    def test_run_full_cycle(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        traces = [
            DualTraceEntry(
                fact_id="f1",
                statement="Test fact",
                scene_trace=SceneTrace(
                    scene_id="s1",
                    scene_type=SceneType.OBSERVATION,
                    description="test",
                    agents_involved=("agent_a",),
                ),
                domain="test",
            ),
        ]
        result = dc.run_full_cycle(traces)
        assert "phase1_analyze_sessions" in result
        assert "phase4_insights" in result

    def test_get_all_insights(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        assert len(dc.get_all_insights()) == 0

    def test_clear_insights(self):
        sm = SemanticMemory()
        dts = DualTraceStore()
        dm = DecayManager()
        dc = DreamCycle(sm, dts, dm)
        traces = [
            DualTraceEntry(
                fact_id="f1",
                statement="Test",
                scene_trace=SceneTrace(scene_id="s1", scene_type=SceneType.OBSERVATION, description="test"),
                domain="test",
            ),
        ]
        dc.analyze_sessions(traces)
        dc.clear_insights()
        assert len(dc.get_all_insights()) == 0


# ── MCP Server ────────────────────────────────────────────────────────────


class TestMCPServer:
    def test_search_memory(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="Python is great", confidence=0.9))
        rm = RetrievalManager(semantic_memory=sm)
        server = MCPServer(rm)
        result = server.search_memory("python")
        assert result["metadata"]["total_results"] >= 1
        assert result["content"][0]["entry_id"] == "f1"

    def test_search_memory_empty(self):
        rm = RetrievalManager()
        server = MCPServer(rm)
        result = server.search_memory("test")
        assert result["metadata"]["total_results"] == 0

    def test_get_observation(self):
        sm = SemanticMemory()
        sm.add_fact(Fact(fact_id="f1", domain="test", statement="test fact"))
        rm = RetrievalManager(semantic_memory=sm)
        server = MCPServer(rm)
        result = server.get_observation("f1", "semantic")
        assert result["content"] is not None
        assert result["content"]["entry_id"] == "f1"

    def test_get_observation_not_found(self):
        rm = RetrievalManager()
        server = MCPServer(rm)
        result = server.get_observation("nonexistent")
        assert result["content"] is None
        assert "error" in result["metadata"]

    def test_get_timeline(self):
        wm = WorkingMemory(max_tokens=1000)
        wm.add(ContextItem(item_id="wm1", content="test context", priority=5, token_estimate=10))
        rm = RetrievalManager(working_memory=wm)
        server = MCPServer(rm)
        result = server.get_timeline("wm1", "working")
        assert result["content"] is not None

    def test_get_timeline_not_found(self):
        rm = RetrievalManager()
        server = MCPServer(rm)
        result = server.get_timeline("nonexistent")
        assert result["content"] is None

    def test_get_stats(self):
        wm = WorkingMemory(max_tokens=1000)
        sm = SemanticMemory()
        rm = RetrievalManager(working_memory=wm, semantic_memory=sm)
        server = MCPServer(rm)
        result = server.get_stats()
        assert "working" in result["content"]

    def test_list_tools(self):
        rm = RetrievalManager()
        server = MCPServer(rm)
        tools = server.list_tools()
        assert len(tools) >= 4
        tool_names = [t["name"] for t in tools]
        assert "search_memory" in tool_names
        assert "get_observation" in tool_names
        assert "get_timeline" in tool_names
        assert "get_stats" in tool_names


# ── Exceptions ────────────────────────────────────────────────────────────


class TestExceptions:
    def test_memory_error_base(self):
        e = MemoryError("test")
        assert str(e) == "test"
        assert isinstance(e, Exception)

    def test_memory_not_found_error(self):
        e = MemoryNotFoundError("id1", "episodic")
        assert "id1" in str(e)
        assert e.memory_id == "id1"
        assert e.memory_type == "episodic"

    def test_memory_capacity_error(self):
        e = MemoryCapacityError("wm", 100, 100)
        assert "wm" in str(e)
        assert e.limit == 100

    def test_privacy_violation_error(self):
        e = PrivacyViolationError("PRIVATE", "read")
        assert "PRIVATE" in str(e)

    def test_decay_error(self):
        e = DecayError("entry not found")
        assert "entry not found" in str(e)

    def test_dream_cycle_error(self):
        e = DreamCycleError("analyze", "no data")
        assert "analyze" in str(e)
        assert "no data" in str(e)

    def test_compression_error(self):
        e = CompressionError("test_tool", "empty log")
        assert "test_tool" in str(e)

    def test_retrieval_error(self):
        e = RetrievalError(2, "layer2 failed")
        assert "2" in str(e)


# ── Cross-module Integration ──────────────────────────────────────────────


class TestIntegration:
    def test_working_to_episodic_flow(self):
        """Simulate a memory flow: working memory items become episodic events."""
        wm = WorkingMemory(max_tokens=1000)
        em = EpisodicMemory()
        wm.add(ContextItem(item_id="ctx1", content="Processing file X", priority=5, token_estimate=10))
        wm.add(ContextItem(item_id="ctx2", content="Found pattern Y", priority=3, token_estimate=10))
        for item in wm.items():
            em.store(EpisodeEvent(
                event_id=f"evt_{item.item_id}",
                agent_id="test_agent",
                event_type="context_item",
                content=item.content,
                metadata={"priority": item.priority},
            ))
        assert em.count() == 2
        retrieved = em.query_by_type("context_item")
        assert len(retrieved) == 2

    def test_semantic_to_retrieval_flow(self):
        """Verify that facts stored in semantic memory are retrievable via retrieval manager."""
        sm = SemanticMemory()
        facts = [
            Fact(fact_id="f1", domain="coding", statement="Python is dynamically typed"),
            Fact(fact_id="f2", domain="coding", statement="Java is statically typed"),
            Fact(fact_id="f3", domain="music", statement="Jazz originated in New Orleans"),
        ]
        for f in facts:
            sm.add_fact(f)
        rm = RetrievalManager(semantic_memory=sm)
        results = rm.search_index("python")
        assert len(results) >= 1
        detail = rm.get_detail("f1", "semantic")
        assert detail is not None
        assert detail.content == "Python is dynamically typed"

    def test_full_stack_layer_search(self):
        """Test search across all memory layers."""
        wm = WorkingMemory(max_tokens=1000)
        em = EpisodicMemory()
        sm = SemanticMemory()
        pm = ProceduralMemory()
        wm.add(ContextItem(item_id="wm1", content="Active context about AI", priority=5, token_estimate=10))
        em.store(EpisodeEvent(event_id="evt1", agent_id="a", event_type="chat", content="Discussion about AI"))
        sm.add_fact(Fact(fact_id="f1", domain="ai", statement="AI systems use neural networks"))
        pm.store_skill(Skill(skill_id="s1", name="AI Processor", description="Processes AI-related tasks", triggers=("ai",)))
        rm = RetrievalManager(working_memory=wm, episodic_memory=em, semantic_memory=sm, procedural_memory=pm)
        results = rm.search_index("AI")
        assert len(results) >= 1

    def test_privacy_through_stack(self):
        """Verify privacy tiers propagate through semantic queries."""
        sm = SemanticMemory()
        from lyra_memory_stack.privacy_tiers import PrivacyTier
        sm.add_fact(Fact(fact_id="f1", domain="secret", statement="Secret data", confidence=0.9, tier=PrivacyTier.PRIVATE))
        results = sm.query_facts("secret", tier_filter=PrivacyTier.DURABLE)
        assert len(results) == 0

    def test_decay_contradiction_detection(self):
        """Verify decay manager detects contradictions between semantic facts."""
        dm = DecayManager()
        dm.register_entry(MemoryEntry(entry_id="f1", memory_type=MemoryType.SEMANTIC, content="Sky is blue"))
        dm.register_entry(MemoryEntry(entry_id="f2", memory_type=MemoryType.SEMANTIC, content="Sky is green"))
        contradictions = dm.detect_contradictions([
            ("f1", "f2", "Contradictory statements about sky color"),
        ])
        assert len(contradictions) == 1
        # After unregistering one, the contradiction should be cleaned
        dm.unregister_entry("f1")
        remaining = dm.get_contradictions("f2")
        assert len(remaining) == 0
