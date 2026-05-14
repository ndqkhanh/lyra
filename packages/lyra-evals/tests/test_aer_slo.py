"""Tests for Phase A: Agent Execution Record + SLO tracker."""
from __future__ import annotations

import time

from lyra_evals.aer import AERStore, new_aer
from lyra_evals.slo import DEFAULT_SLOS, SLOBreach, SLOTracker


# ------------------------------------------------------------------ #
# AER                                                                  #
# ------------------------------------------------------------------ #


class TestAgentExecutionRecord:
    def test_defaults(self):
        rec = new_aer("run-1", "sess-1", 0)
        assert rec.run_id == "run-1"
        assert rec.session_id == "sess-1"
        assert rec.turn_index == 0
        assert rec.model_tier == "fast"
        assert rec.confidence == 0.0

    def test_evidence_list_empty(self):
        rec = new_aer("r", "s", 0)
        assert rec.evidence_list() == []

    def test_evidence_list_populated(self):
        import json
        rec = new_aer("r", "s", 0)
        object.__setattr__(rec, "evidence_refs", json.dumps(["ref-a", "ref-b"]))
        assert rec.evidence_list() == ["ref-a", "ref-b"]

    def test_to_dict_roundtrip(self):
        rec = new_aer("r", "s", 3, intent="synthesise", model_tier="reasoning")
        d = rec.to_dict()
        assert d["intent"] == "synthesise"
        assert d["model_tier"] == "reasoning"

    def test_pid_port_list(self):
        import json
        rec = new_aer("r", "s", 0)
        object.__setattr__(rec, "child_pids", json.dumps([1234, 5678]))
        object.__setattr__(rec, "open_ports", json.dumps([8080]))
        assert rec.pid_list() == [1234, 5678]
        assert rec.port_list() == [8080]


class TestAERStore:
    def test_write_and_fetch_session(self):
        store = AERStore()
        rec = new_aer("run-1", "sess-A", 0, intent="test")
        store.write(rec)
        rows = store.fetch_session("sess-A")
        assert len(rows) == 1
        assert rows[0].intent == "test"

    def test_latest(self):
        store = AERStore()
        for i in range(3):
            store.write(new_aer("run-1", "sess-B", i, intent=f"turn-{i}"))
        latest = store.latest("sess-B")
        assert latest is not None
        assert latest.intent == "turn-2"

    def test_fetch_run(self):
        store = AERStore()
        for i in range(4):
            store.write(new_aer("run-X", "sess-C", i))
        rows = store.fetch_run("run-X")
        assert len(rows) == 4
        assert [r.turn_index for r in rows] == [0, 1, 2, 3]

    def test_count(self):
        store = AERStore()
        for i in range(5):
            store.write(new_aer("run-1", "sess-D", i))
        assert store.count("sess-D") == 5

    def test_prune(self):
        store = AERStore()
        old_rec = new_aer("run-1", "sess-E", 0)
        object.__setattr__(old_rec, "ts", 1.0)
        store.write(old_rec)
        store.write(new_aer("run-1", "sess-E", 1))
        deleted = store.prune_older_than(time.time() - 1)
        assert deleted == 1
        assert store.count("sess-E") == 1

    def test_no_session_returns_none(self):
        store = AERStore()
        assert store.latest("nonexistent") is None

    def test_git_dirty_roundtrip(self):
        store = AERStore()
        rec = new_aer("run-1", "sess-F", 0)
        object.__setattr__(rec, "git_dirty", True)
        store.write(rec)
        rows = store.fetch_session("sess-F")
        assert rows[0].git_dirty is True

    def test_transaction_rollback(self):
        store = AERStore()
        store.write(new_aer("run-1", "sess-G", 0))
        try:
            with store.transaction():
                store._conn.execute(
                    "INSERT INTO agent_execution_records(run_id, session_id, turn_index) VALUES (?, ?, ?)",
                    ("bad", "sess-rollback", 99),
                )
                raise ValueError("force rollback")
        except ValueError:
            pass
        # The explicit write above should still be there; bad insert should not
        rows = store.fetch_session("sess-G")
        assert len(rows) == 1


# ------------------------------------------------------------------ #
# SLO                                                                  #
# ------------------------------------------------------------------ #


class TestSLOTracker:
    def test_no_breach_clean_record(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s1", 0)
        object.__setattr__(rec, "context_window_pct", 50.0)
        object.__setattr__(rec, "tool_cost_usd", 0.01)
        breaches = tracker.check(rec)
        assert breaches == []

    def test_context_breach(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s2", 0)
        object.__setattr__(rec, "context_window_pct", 90.0)
        breaches = tracker.check(rec)
        names = {b.slo_name for b in breaches}
        assert "context_safety" in names

    def test_cost_breach(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s3", 0)
        object.__setattr__(rec, "tool_cost_usd", 0.50)
        breaches = tracker.check(rec)
        names = {b.slo_name for b in breaches}
        assert "cost_budget" in names

    def test_safety_breach(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s4", 0)
        object.__setattr__(rec, "policy_gate", "BLOCK: harmful content")
        breaches = tracker.check(rec)
        names = {b.slo_name for b in breaches}
        assert "safety" in names

    def test_quality_breach_on_fail_verdict(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s5", 0)
        object.__setattr__(rec, "verifier_verdict", "fail: citation not found")
        breaches = tracker.check(rec)
        names = {b.slo_name for b in breaches}
        assert "quality" in names

    def test_quality_passes_when_no_verdict(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s6", 0)
        breaches = tracker.check(rec)
        names = {b.slo_name for b in breaches}
        assert "quality" not in names

    def test_on_breach_callback(self):
        captured: list[SLOBreach] = []
        tracker = SLOTracker(on_breach=captured.append)
        rec = new_aer("r", "s7", 0)
        object.__setattr__(rec, "context_window_pct", 95.0)
        tracker.check(rec)
        assert len(captured) >= 1

    def test_summary_all_ok(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s8", 0)
        tracker.check(rec)
        summary = tracker.summary("s8")
        assert summary["all_ok"] is True

    def test_summary_with_breach(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s9", 0)
        object.__setattr__(rec, "context_window_pct", 99.0)
        tracker.check(rec)
        summary = tracker.summary("s9")
        assert summary["all_ok"] is False
        assert "context_safety" in summary["breached_slos"]

    def test_reset_session(self):
        tracker = SLOTracker()
        rec = new_aer("r", "s10", 0)
        object.__setattr__(rec, "context_window_pct", 99.0)
        tracker.check(rec)
        tracker.reset_session("s10")
        assert tracker.summary("s10")["total_breaches"] == 0

    def test_default_slos_complete(self):
        names = {s.name for s in DEFAULT_SLOS}
        expected = {
            "cost_budget", "context_safety", "latency",
            "quality", "safety", "resource_hygiene", "human_control",
        }
        assert names == expected
