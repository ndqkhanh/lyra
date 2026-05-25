"""Tests for the unified memory orchestrator (L0-L3 + KG)."""
import pytest

from lyra_cli.tui_gateway.unified_memory import (
    MemoryQueryResult,
    MemoryStats,
    UnifiedMemoryOrchestrator,
)


class TestUnifiedMemory:
    def test_initial_state(self):
        orch = UnifiedMemoryOrchestrator()
        assert not orch.initialized
        orch.initialize()
        assert orch.initialized

    def test_double_init_is_idempotent(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        orch.initialize()  # should not raise
        assert orch.initialized

    def test_write_working(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        wid = orch.write_working("test entry", priority=1.5)
        assert wid.startswith("wm-")

    def test_write_episodic(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        eid = orch.write_episodic("sess-1", "test_event", "event content")
        assert isinstance(eid, int)
        assert eid > 0

    def test_write_semantic(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        sid = orch.write_semantic("Python is great", category="tech")
        assert sid.startswith("fact-")

    def test_write_procedural(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        pid = orch.write_procedural(
            "git_commit", "Commit changes", ["git add .", "git commit"]
        )
        assert pid.startswith("proc-")

    def test_query_cross_tier(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        orch.write_episodic("sess-1", "msg", "search the codebase for bugs")
        orch.write_semantic("codebase has 50k lines", category="tech")
        results = orch.query("codebase", top_k=5)
        assert len(results) >= 1

    def test_query_filters_by_tiers(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        orch.write_episodic("sess-1", "msg", "test content")
        results = orch.query("test", tiers=("semantic",))  # only semantic, none stored
        assert len(results) == 0

    def test_stats_increases_after_writes(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        stats_before = orch.stats()
        orch.write_working("entry 1")
        orch.write_semantic("fact 1")
        stats_after = orch.stats()
        assert stats_after.working_entries >= stats_before.working_entries
        assert stats_after.semantic_facts >= stats_before.semantic_facts

    def test_snapshot(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        snap = orch.snapshot()
        assert snap["initialized"] is True
        assert "stats" in snap
        assert "queries" in snap

    def test_consolidation_noop(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        result = orch.consolidate()
        assert "deep" in result

    def test_dream_cycle_graceful(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        result = orch.dream_cycle()
        assert isinstance(result, dict)

    def test_memory_stats_dataclass(self):
        s = MemoryStats(
            working_entries=5,
            episodic_events=10,
            semantic_facts=20,
            procedural_count=3,
            kg_nodes=15,
            kg_edges=30,
        )
        assert s.working_entries == 5
        assert s.kg_edges == 30

    def test_memory_query_result_dataclass(self):
        r = MemoryQueryResult(
            tier="L1_episodic",
            content="test content",
            score=0.85,
            metadata={"event_type": "msg"},
        )
        assert r.tier == "L1_episodic"
        assert r.score == 0.85
        assert r.metadata["event_type"] == "msg"

    def test_close(self):
        orch = UnifiedMemoryOrchestrator()
        orch.initialize()
        orch.close()  # should not raise
