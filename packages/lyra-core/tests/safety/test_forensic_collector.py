"""Tests for ForensicCollector — forensic trace collection for safety incidents."""

import pytest

from lyra_core.safety.forensic_collector import (
    ForensicCollector,
    ForensicSnapshot,
    IncidentCategory,
    SnapshotChain,
)


class TestIncidentCategory:
    def test_values(self):
        assert IncidentCategory.PROMPT_INJECTION.value == "prompt_injection"
        assert IncidentCategory.TOOL_MISUSE.value == "tool_misuse"
        assert IncidentCategory.CREDENTIAL_EXPOSURE.value == "credential_exposure"

    def test_all_categories(self):
        categories = list(IncidentCategory)
        assert len(categories) >= 9


class TestForensicSnapshot:
    def test_create_minimal(self):
        snapshot = ForensicSnapshot(
            snapshot_id="snap-001",
            incident_category=IncidentCategory.PROMPT_INJECTION,
            timestamp=1000.0,
            agent_id="agent-1",
            session_id="sess-1",
            tool_name=None,
            tool_args=None,
            model_id=None,
            model_output=None,
            permissions_state=None,
            safety_flags=None,
            stack_trace=None,
            environment_summary=None,
            previous_snapshot_hash=None,
        )
        assert snapshot.incident_category == IncidentCategory.PROMPT_INJECTION
        assert snapshot.agent_id == "agent-1"

    def test_create_full(self):
        snapshot = ForensicSnapshot(
            snapshot_id="snap-002",
            incident_category=IncidentCategory.TOOL_MISUSE,
            timestamp=2000.0,
            agent_id="agent-2",
            session_id="sess-2",
            tool_name="execute_code",
            tool_args={"code": "print('hi')"},
            model_id="claude-sonnet-4-6",
            model_output="I'll run that code",
            permissions_state={"can_execute": True},
            safety_flags=["unusual_pattern"],
            stack_trace="Traceback: ...",
            environment_summary={"os": "darwin"},
            previous_snapshot_hash="abc123",
        )
        assert snapshot.tool_name == "execute_code"
        assert snapshot.safety_flags == ["unusual_pattern"]

    def test_age_sec(self):
        import time
        snapshot = ForensicSnapshot(
            snapshot_id="s", incident_category=IncidentCategory.UNKNOWN,
            timestamp=time.time() - 50, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        assert snapshot.age_sec >= 50

    def test_immutable(self):
        snapshot = ForensicSnapshot(
            snapshot_id="s", incident_category=IncidentCategory.UNKNOWN,
            timestamp=0.0, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        with pytest.raises(Exception):
            snapshot.tool_name = "hacked"  # type: ignore[misc]


class TestSnapshotChain:
    def test_append_and_count(self):
        chain = SnapshotChain()
        s1 = ForensicSnapshot(
            snapshot_id="1", incident_category=IncidentCategory.PROMPT_INJECTION,
            timestamp=1.0, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        s2 = ForensicSnapshot(
            snapshot_id="2", incident_category=IncidentCategory.TOOL_MISUSE,
            timestamp=2.0, agent_id="b", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash="hash1",
        )
        chain.append(s1)
        chain.append(s2)
        assert chain.count == 2

    def test_get_existing(self):
        chain = SnapshotChain()
        s = ForensicSnapshot(
            snapshot_id="find-me", incident_category=IncidentCategory.UNKNOWN,
            timestamp=1.0, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        chain.append(s)
        assert chain.get("find-me") is not None

    def test_get_nonexistent(self):
        chain = SnapshotChain()
        assert chain.get("nope") is None

    def test_query_by_category(self):
        chain = SnapshotChain()
        s1 = ForensicSnapshot(
            snapshot_id="1", incident_category=IncidentCategory.PROMPT_INJECTION,
            timestamp=1.0, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        s2 = ForensicSnapshot(
            snapshot_id="2", incident_category=IncidentCategory.TOOL_MISUSE,
            timestamp=2.0, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        chain.append(s1)
        chain.append(s2)
        results = chain.query(category=IncidentCategory.PROMPT_INJECTION)
        assert len(results) == 1
        assert results[0].incident_category == IncidentCategory.PROMPT_INJECTION

    def test_query_by_agent(self):
        chain = SnapshotChain()
        s1 = ForensicSnapshot(
            snapshot_id="1", incident_category=IncidentCategory.UNKNOWN,
            timestamp=1.0, agent_id="alpha", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        s2 = ForensicSnapshot(
            snapshot_id="2", incident_category=IncidentCategory.UNKNOWN,
            timestamp=2.0, agent_id="beta", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        chain.append(s1)
        chain.append(s2)
        results = chain.query(agent_id="alpha")
        assert len(results) == 1

    def test_query_since_timestamp(self):
        chain = SnapshotChain()
        s1 = ForensicSnapshot(
            snapshot_id="1", incident_category=IncidentCategory.UNKNOWN,
            timestamp=100.0, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        s2 = ForensicSnapshot(
            snapshot_id="2", incident_category=IncidentCategory.UNKNOWN,
            timestamp=200.0, agent_id="a", session_id="s",
            tool_name=None, tool_args=None, model_id=None, model_output=None,
            permissions_state=None, safety_flags=None, stack_trace=None,
            environment_summary=None, previous_snapshot_hash=None,
        )
        chain.append(s1)
        chain.append(s2)
        results = chain.query(since=150.0)
        assert len(results) == 1
        assert results[0].snapshot_id == "2"


class TestForensicCollector:
    def test_capture_creates_snapshot(self):
        collector = ForensicCollector()
        snap = collector.capture(
            category=IncidentCategory.PROMPT_INJECTION,
            agent_id="agent-7",
            session_id="sess-42",
            tool_name="execute_code",
            safety_flags=["injection_detected"],
        )
        assert snap.incident_category == IncidentCategory.PROMPT_INJECTION
        assert snap.agent_id == "agent-7"
        assert len(snap.snapshot_id) == 24

    def test_capture_chain_linking(self):
        collector = ForensicCollector()
        s1 = collector.capture(
            category=IncidentCategory.UNKNOWN, agent_id="a", session_id="s",
        )
        s2 = collector.capture(
            category=IncidentCategory.UNKNOWN, agent_id="a", session_id="s",
        )
        assert s1.previous_snapshot_hash is None
        assert s2.previous_snapshot_hash is not None

    def test_verify_chain(self):
        collector = ForensicCollector()
        collector.capture(category=IncidentCategory.UNKNOWN, agent_id="a", session_id="s")
        collector.capture(category=IncidentCategory.UNKNOWN, agent_id="a", session_id="s")
        assert collector.verify_chain() is True

    def test_model_output_truncation(self):
        collector = ForensicCollector()
        snap = collector.capture(
            category=IncidentCategory.UNKNOWN,
            agent_id="a",
            session_id="s",
            model_output="x" * 3000,
        )
        assert snap.model_output is not None
        assert len(snap.model_output) <= 2100  # 2000 + "…"

    def test_query_by_category(self):
        collector = ForensicCollector()
        collector.capture(
            category=IncidentCategory.PROMPT_INJECTION, agent_id="a", session_id="s",
        )
        collector.capture(
            category=IncidentCategory.TOOL_MISUSE, agent_id="a", session_id="s",
        )
        results = collector.query(category=IncidentCategory.PROMPT_INJECTION)
        assert len(results) == 1

    def test_get_snapshot(self):
        collector = ForensicCollector()
        snap = collector.capture(
            category=IncidentCategory.UNKNOWN, agent_id="a", session_id="s",
        )
        assert collector.get_snapshot(snap.snapshot_id) is not None
        assert collector.get_snapshot("nonexistent") is None

    def test_stats(self):
        collector = ForensicCollector()
        collector.capture(
            category=IncidentCategory.PROMPT_INJECTION, agent_id="a", session_id="s",
        )
        collector.capture(
            category=IncidentCategory.PROMPT_INJECTION, agent_id="b", session_id="s",
        )
        stats = collector.stats()
        assert stats["total_snapshots"] == 2
        assert stats["chain_verified"] is True
        assert "by_category" in stats
