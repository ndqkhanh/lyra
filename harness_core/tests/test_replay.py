"""Tests for harness_core.replay — types + builder + comparator."""
from __future__ import annotations

import pytest

from harness_core.forensic import Trajectory, TrajectoryOutcome
from harness_core.orchestration import AgentDecision, SideEffectRecord
from harness_core.provenance import WitnessLattice
from harness_core.replay import (
    ReplayEvent,
    ReplayEventKind,
    Trace,
    TraceBuilder,
    TraceComparator,
    TraceDelta,
    TraceDeltaKind,
)


# --- ReplayEvent / Trace --------------------------------------------------


class TestReplayEvent:
    def test_valid(self):
        e = ReplayEvent(
            event_id="e1",
            kind=ReplayEventKind.RETRIEVAL,
            timestamp=1.0,
            issued_by="r",
        )
        assert e.event_id == "e1"

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            ReplayEvent(
                event_id="", kind=ReplayEventKind.AGENT_DECISION,
                timestamp=0.0, issued_by="x",
            )

    def test_empty_issuer_rejected(self):
        with pytest.raises(ValueError):
            ReplayEvent(
                event_id="e1", kind=ReplayEventKind.AGENT_DECISION,
                timestamp=0.0, issued_by="",
            )

    def test_negative_timestamp_rejected(self):
        with pytest.raises(ValueError):
            ReplayEvent(
                event_id="e1", kind=ReplayEventKind.AGENT_DECISION,
                timestamp=-1, issued_by="x",
            )


class TestTrace:
    def test_create_sorts_by_timestamp(self):
        events = [
            ReplayEvent(event_id="e2", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=2.0, issued_by="a"),
            ReplayEvent(event_id="e1", kind=ReplayEventKind.RETRIEVAL,
                        timestamp=1.0, issued_by="r"),
        ]
        t = Trace.create(trace_id="t1", events=events)
        assert [e.event_id for e in t.events] == ["e1", "e2"]

    def test_empty_trace_id_rejected(self):
        with pytest.raises(ValueError):
            Trace(trace_id="")

    def test_by_kind(self):
        t = Trace.create(trace_id="t", events=[
            ReplayEvent(event_id="r1", kind=ReplayEventKind.RETRIEVAL,
                        timestamp=1.0, issued_by="r"),
            ReplayEvent(event_id="d1", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=2.0, issued_by="a"),
            ReplayEvent(event_id="r2", kind=ReplayEventKind.RETRIEVAL,
                        timestamp=3.0, issued_by="r"),
        ])
        retrievals = t.by_kind(ReplayEventKind.RETRIEVAL)
        assert {e.event_id for e in retrievals} == {"r1", "r2"}

    def test_for_namespace(self):
        t = Trace.create(trace_id="t", events=[
            ReplayEvent(event_id="e1", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=1.0, issued_by="a", namespace_id="ns1"),
            ReplayEvent(event_id="e2", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=2.0, issued_by="a", namespace_id="ns2"),
        ])
        assert {e.event_id for e in t.for_namespace("ns1")} == {"e1"}

    def test_for_issuer(self):
        t = Trace.create(trace_id="t", events=[
            ReplayEvent(event_id="e1", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=1.0, issued_by="alice"),
            ReplayEvent(event_id="e2", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=2.0, issued_by="bob"),
        ])
        assert {e.event_id for e in t.for_issuer("alice")} == {"e1"}

    def test_in_window(self):
        t = Trace.create(trace_id="t", events=[
            ReplayEvent(event_id="e1", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=1.0, issued_by="a"),
            ReplayEvent(event_id="e2", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=5.0, issued_by="a"),
            ReplayEvent(event_id="e3", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=10.0, issued_by="a"),
        ])
        in_win = t.in_window(start=2.0, end=7.0)
        assert {e.event_id for e in in_win} == {"e2"}

    def test_event_kinds_and_ids(self):
        t = Trace.create(trace_id="t", events=[
            ReplayEvent(event_id="e1", kind=ReplayEventKind.RETRIEVAL,
                        timestamp=1.0, issued_by="r"),
            ReplayEvent(event_id="e2", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=2.0, issued_by="a"),
        ])
        assert t.event_kinds() == (ReplayEventKind.RETRIEVAL, ReplayEventKind.AGENT_DECISION)
        assert t.event_ids() == frozenset({"e1", "e2"})

    def test_stats(self):
        t = Trace.create(trace_id="t", events=[
            ReplayEvent(event_id="e1", kind=ReplayEventKind.RETRIEVAL,
                        timestamp=1.0, issued_by="r", namespace_id="ns1"),
            ReplayEvent(event_id="e2", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=2.0, issued_by="a", namespace_id="ns1"),
            ReplayEvent(event_id="e3", kind=ReplayEventKind.AGENT_DECISION,
                        timestamp=3.0, issued_by="a", namespace_id="ns2"),
        ])
        s = t.stats()
        assert s["total"] == 3
        assert s["retrieval"] == 1
        assert s["agent_decision"] == 2
        assert s["issuers"] == 2
        assert s["namespaces"] == 2


# --- TraceBuilder -------------------------------------------------------


class TestTraceBuilder:
    def test_add_witnesses_from_lattice(self):
        lattice = WitnessLattice()
        retrieval = lattice.record_retrieval(
            retriever_name="hipporag", query="X", doc_ids=["d1"],
        )
        inference = lattice.record_inference(
            agent_id="agent", claim="X is true",
            supporting=[retrieval.witness_id],
        )

        builder = TraceBuilder(trace_id="incident-1")
        n = builder.add_witnesses_from(lattice.ledger)
        assert n == 2

        trace = builder.build()
        kinds = {e.kind for e in trace.events}
        assert ReplayEventKind.RETRIEVAL in kinds
        assert ReplayEventKind.INFERENCE in kinds

    def test_add_trajectory(self):
        decisions = (
            AgentDecision(action="search", fingerprint="fp1"),
            AgentDecision(action="answer", fingerprint="fp2"),
        )
        side_effects = (
            SideEffectRecord(
                call_id="c1", tool_name="search_tool",
                args={"q": "x"}, result="ok",
                timestamp=10.0,
            ),
        )
        traj = Trajectory(
            trajectory_id="t1",
            task_signature="research",
            decisions=decisions,
            side_effects=side_effects,
            outcome=TrajectoryOutcome.SUCCESS,
        )

        builder = TraceBuilder(trace_id="incident-2")
        n = builder.add_trajectory(traj, base_timestamp=1.0)
        assert n == 3  # 2 decisions + 1 side effect

        trace = builder.build()
        decisions_in_trace = trace.by_kind(ReplayEventKind.AGENT_DECISION)
        assert len(decisions_in_trace) == 2
        tool_calls = trace.by_kind(ReplayEventKind.TOOL_CALL)
        assert len(tool_calls) == 1
        assert tool_calls[0].payload["tool_name"] == "search_tool"

    def test_add_custom_event(self):
        builder = TraceBuilder(trace_id="incident-3")
        event = builder.add_event(
            kind=ReplayEventKind.PAGE_EDIT,
            issued_by="user:alice",
            timestamp=42.0,
            payload={"page_id": "p1", "diff": "+5 -3"},
            namespace_id="proj-A",
        )
        assert event.kind == ReplayEventKind.PAGE_EDIT
        trace = builder.build()
        assert event in trace.events

    def test_add_custom_with_explicit_id(self):
        builder = TraceBuilder(trace_id="t")
        event = builder.add_event(
            kind=ReplayEventKind.HUMAN_APPROVAL,
            issued_by="user:bob", timestamp=1.0,
            event_id="approval-1",
        )
        assert event.event_id == "approval-1"

    def test_build_sorts_by_timestamp(self):
        builder = TraceBuilder(trace_id="t")
        builder.add_event(
            kind=ReplayEventKind.AGENT_DECISION,
            issued_by="a", timestamp=3.0, event_id="late",
        )
        builder.add_event(
            kind=ReplayEventKind.AGENT_DECISION,
            issued_by="a", timestamp=1.0, event_id="early",
        )
        builder.add_event(
            kind=ReplayEventKind.AGENT_DECISION,
            issued_by="a", timestamp=2.0, event_id="mid",
        )
        trace = builder.build()
        assert [e.event_id for e in trace.events] == ["early", "mid", "late"]

    def test_combined_sources(self):
        # Build a trace from witnesses + trajectory + custom events.
        lattice = WitnessLattice()
        lattice.record_retrieval(retriever_name="r", query="q", doc_ids=["d1"])

        traj = Trajectory(
            trajectory_id="traj-1",
            task_signature="task",
            decisions=(AgentDecision(action="a", fingerprint="fp"),),
        )

        builder = TraceBuilder(trace_id="combined")
        builder.add_witnesses_from(lattice.ledger)
        builder.add_trajectory(traj, base_timestamp=100.0)
        builder.add_event(
            kind=ReplayEventKind.HUMAN_APPROVAL,
            issued_by="user:alice", timestamp=200.0,
            payload={"approved": True},
        )
        trace = builder.build()
        # Should have 3 events from 3 sources.
        assert len(trace.events) == 3
        kinds = {e.kind for e in trace.events}
        assert ReplayEventKind.RETRIEVAL in kinds
        assert ReplayEventKind.AGENT_DECISION in kinds
        assert ReplayEventKind.HUMAN_APPROVAL in kinds


# --- TraceComparator ---------------------------------------------------


def _trace(events_data: list[tuple[str, ReplayEventKind, float, dict]]) -> Trace:
    """Helper: build a trace from (event_id, kind, timestamp, payload) tuples."""
    events = [
        ReplayEvent(event_id=eid, kind=kind, timestamp=ts, issued_by="x", payload=p)
        for eid, kind, ts, p in events_data
    ]
    return Trace.create(trace_id="t", events=events)


class TestTraceComparator:
    def test_identical_traces_no_deltas(self):
        ref = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 1.0, {}),
            ("e2", ReplayEventKind.AGENT_DECISION, 2.0, {}),
        ])
        tgt = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 1.0, {}),
            ("e2", ReplayEventKind.AGENT_DECISION, 2.0, {}),
        ])
        assert TraceComparator().compare(reference=ref, target=tgt) == []
        assert TraceComparator().is_equivalent(reference=ref, target=tgt) is True

    def test_event_added(self):
        ref = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {})])
        tgt = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 1.0, {}),
            ("e2", ReplayEventKind.TOOL_CALL, 2.0, {}),
        ])
        deltas = TraceComparator().compare(reference=ref, target=tgt)
        assert len(deltas) == 1
        assert deltas[0].kind == TraceDeltaKind.EVENT_ADDED
        assert deltas[0].event_id == "e2"

    def test_event_removed(self):
        ref = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 1.0, {}),
            ("e2", ReplayEventKind.TOOL_CALL, 2.0, {}),
        ])
        tgt = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {})])
        deltas = TraceComparator().compare(reference=ref, target=tgt)
        assert len(deltas) == 1
        assert deltas[0].kind == TraceDeltaKind.EVENT_REMOVED
        assert deltas[0].event_id == "e2"

    def test_event_kind_diverged(self):
        ref = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {})])
        tgt = _trace([("e1", ReplayEventKind.AGENT_DECISION, 1.0, {})])
        deltas = TraceComparator().compare(reference=ref, target=tgt)
        assert len(deltas) == 1
        assert deltas[0].kind == TraceDeltaKind.EVENT_KIND_DIVERGED

    def test_payload_diverged(self):
        ref = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {"q": "X"})])
        tgt = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {"q": "Y"})])
        deltas = TraceComparator(check_payloads=True).compare(reference=ref, target=tgt)
        assert any(d.kind == TraceDeltaKind.PAYLOAD_DIVERGED for d in deltas)

    def test_payload_check_off(self):
        ref = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {"q": "X"})])
        tgt = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {"q": "Y"})])
        deltas = TraceComparator(check_payloads=False).compare(
            reference=ref, target=tgt,
        )
        assert deltas == []

    def test_order_diverged(self):
        # Same event_ids but different timestamps → different sort order.
        ref = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 1.0, {}),
            ("e2", ReplayEventKind.AGENT_DECISION, 2.0, {}),
        ])
        tgt = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 3.0, {}),  # later
            ("e2", ReplayEventKind.AGENT_DECISION, 0.5, {}),  # earlier
        ])
        deltas = TraceComparator(check_payloads=False).compare(
            reference=ref, target=tgt,
        )
        # e2 now before e1 in target → order diverged.
        order_deltas = [d for d in deltas if d.kind == TraceDeltaKind.ORDER_DIVERGED]
        assert len(order_deltas) == 1

    def test_check_timestamps(self):
        ref = _trace([("e1", ReplayEventKind.RETRIEVAL, 1.0, {})])
        tgt = _trace([("e1", ReplayEventKind.RETRIEVAL, 5.0, {})])
        deltas = TraceComparator(check_timestamps=True).compare(
            reference=ref, target=tgt,
        )
        assert any("timestamp" in d.note for d in deltas)

    def test_summarize(self):
        ref = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 1.0, {}),
            ("e2", ReplayEventKind.AGENT_DECISION, 2.0, {}),
        ])
        tgt = _trace([
            ("e1", ReplayEventKind.RETRIEVAL, 1.0, {}),
            ("e3", ReplayEventKind.TOOL_CALL, 3.0, {}),
        ])
        s = TraceComparator().summarize(reference=ref, target=tgt)
        assert s["event_added"] == 1
        assert s["event_removed"] == 1
        assert s["total"] == 2


# --- End-to-end: incident replay scenario -----------------------------


class TestIncidentReplayScenario:
    """Realistic Aegis-Ops post-mortem: build a trace from witnesses + a
    trajectory + a human-approval event; compare against the reference."""

    def _build_reference_incident(self) -> Trace:
        lattice = WitnessLattice()
        retrieval = lattice.record_retrieval(
            retriever_name="runbook-lookup",
            query="alert-1234", doc_ids=["runbook-restart-service"],
        )
        verdict = lattice.record_verdict(
            verifier_name="composer",
            passed=True, severity="info",
            axes={"dry_run": True, "policy": True},
            parent_witnesses=[retrieval.witness_id],
        )
        builder = TraceBuilder(trace_id="incident-ref")
        builder.add_witnesses_from(lattice.ledger)
        builder.add_event(
            kind=ReplayEventKind.HUMAN_APPROVAL,
            issued_by="user:on-call", timestamp=verdict.issued_at + 0.001,
            payload={"approved": True}, event_id="approval-ref",
        )
        return builder.build()

    def test_replayed_trace_equivalent(self):
        """A trace replayed from the same source ledger should be identical.

        Production replay re-reads from the persistent ledger; in-process we
        build the trace twice from the *same* lattice + same fixed-id event.
        """
        from harness_core.provenance import WitnessLattice
        # Single shared lattice — witness IDs are content-addressed by SHA256
        # over (kind, issuer, timestamp, content, parents), so reading the
        # same lattice twice produces identical witnesses.
        lattice = WitnessLattice()
        retrieval = lattice.record_retrieval(
            retriever_name="runbook-lookup", query="alert-1234",
            doc_ids=["runbook-restart-service"],
        )
        verdict = lattice.record_verdict(
            verifier_name="composer", passed=True, severity="info",
            axes={"dry_run": True, "policy": True},
            parent_witnesses=[retrieval.witness_id],
        )
        approval_ts = verdict.issued_at + 0.001

        def build_from_same_source() -> Trace:
            b = TraceBuilder(trace_id="incident")
            b.add_witnesses_from(lattice.ledger)
            b.add_event(
                kind=ReplayEventKind.HUMAN_APPROVAL,
                issued_by="user:on-call", timestamp=approval_ts,
                payload={"approved": True}, event_id="approval-1",
            )
            return b.build()

        ref = build_from_same_source()
        replay = build_from_same_source()
        deltas = TraceComparator(check_payloads=True).compare(
            reference=ref, target=replay,
        )
        assert deltas == []

    def test_sabotage_detected_via_extra_action(self):
        ref = self._build_reference_incident()
        # The "sabotage" target adds an unauthorized rm_rf action.
        bad_builder = TraceBuilder(trace_id="incident-bad")
        for e in ref.events:
            bad_builder._events.append(e)  # carry over reference events
        bad_builder.add_event(
            kind=ReplayEventKind.TOOL_CALL,
            issued_by="user:on-call", timestamp=999.0,
            payload={"tool_name": "rm_rf", "path": "/etc/passwd"},
            event_id="malicious-action",
        )
        bad_trace = bad_builder.build()
        deltas = TraceComparator().compare(reference=ref, target=bad_trace)
        # Exactly one EVENT_ADDED for the unauthorized action.
        added = [d for d in deltas if d.kind == TraceDeltaKind.EVENT_ADDED]
        assert len(added) == 1
        assert added[0].event_id == "malicious-action"
