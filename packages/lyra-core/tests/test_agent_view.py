"""Tests for Phase D: FleetView + FleetSupervisor."""
from __future__ import annotations

import time

import pytest

from lyra_core.transparency.agent_view import AgentViewRecord, AttentionPriority, FleetView
from lyra_core.transparency.supervisor import FleetSupervisor, SupervisorConfig


# ------------------------------------------------------------------ #
# AgentViewRecord                                                      #
# ------------------------------------------------------------------ #

class TestAgentViewRecord:
    def test_defaults(self):
        rec = AgentViewRecord(agent_id="s1")
        assert rec.row_summary == ""
        assert rec.attention_priority == AttentionPriority.P3
        assert rec.state == "running"
        assert not rec.is_attached

    def test_set_summary_updates_timestamp(self):
        rec = AgentViewRecord(agent_id="s1")
        before = rec.last_updated
        time.sleep(0.01)
        rec.set_summary("Fetching docs")
        assert rec.row_summary == "Fetching docs"
        assert rec.last_updated > before

    def test_set_priority(self):
        rec = AgentViewRecord(agent_id="s1")
        rec.set_priority(AttentionPriority.P0)
        assert rec.attention_priority == AttentionPriority.P0


# ------------------------------------------------------------------ #
# FleetView — registration                                             #
# ------------------------------------------------------------------ #

class TestFleetViewRegistration:
    def test_register_returns_record(self):
        fleet = FleetView()
        rec = fleet.register("sess-1", summary="hello")
        assert rec.agent_id == "sess-1"
        assert rec.row_summary == "hello"

    def test_peek_returns_record(self):
        fleet = FleetView()
        fleet.register("sess-1")
        assert fleet.peek("sess-1") is not None

    def test_peek_unknown_returns_none(self):
        fleet = FleetView()
        assert fleet.peek("no-such") is None

    def test_deregister_removes_agent(self):
        fleet = FleetView()
        fleet.register("sess-1")
        fleet.deregister("sess-1")
        assert fleet.peek("sess-1") is None
        assert fleet.count == 0

    def test_count(self):
        fleet = FleetView()
        fleet.register("a")
        fleet.register("b")
        assert fleet.count == 2


# ------------------------------------------------------------------ #
# FleetView — mutation                                                 #
# ------------------------------------------------------------------ #

class TestFleetViewMutation:
    def test_set_priority(self):
        fleet = FleetView()
        fleet.register("s1")
        fleet.set_priority("s1", AttentionPriority.P0)
        assert fleet.peek("s1").attention_priority == AttentionPriority.P0

    def test_set_state(self):
        fleet = FleetView()
        fleet.register("s1")
        fleet.set_state("s1", "blocked")
        assert fleet.peek("s1").state == "blocked"

    def test_set_summary(self):
        fleet = FleetView()
        fleet.register("s1")
        fleet.set_summary("s1", "writing test")
        assert fleet.peek("s1").row_summary == "writing test"

    def test_attach_detach(self):
        fleet = FleetView()
        fleet.register("s1")
        fleet.attach("s1")
        assert fleet.peek("s1").is_attached
        fleet.detach("s1")
        assert not fleet.peek("s1").is_attached

    def test_reply_and_pop(self):
        fleet = FleetView()
        fleet.register("s1")
        fleet.reply("s1", "stop and report")
        msg = fleet.pop_reply("s1")
        assert msg == "stop and report"
        assert fleet.pop_reply("s1") is None

    def test_pop_reply_on_unknown_returns_none(self):
        fleet = FleetView()
        assert fleet.pop_reply("ghost") is None

    def test_mutation_on_unknown_raises(self):
        fleet = FleetView()
        with pytest.raises(KeyError):
            fleet.set_priority("ghost", AttentionPriority.P1)

    def test_list_agents_sorted_by_priority(self):
        fleet = FleetView()
        fleet.register("low", priority=AttentionPriority.P4)
        fleet.register("high", priority=AttentionPriority.P0)
        fleet.register("mid", priority=AttentionPriority.P2)
        agents = fleet.list_agents()
        priorities = [a.attention_priority for a in agents]
        assert priorities == sorted(priorities)

    def test_list_by_priority(self):
        fleet = FleetView()
        fleet.register("a", priority=AttentionPriority.P1)
        fleet.register("b", priority=AttentionPriority.P2)
        fleet.register("c", priority=AttentionPriority.P1)
        p1_agents = fleet.list_by_priority(AttentionPriority.P1)
        assert len(p1_agents) == 2


# ------------------------------------------------------------------ #
# FleetSupervisor                                                      #
# ------------------------------------------------------------------ #

class TestFleetSupervisor:
    def test_scan_escalates_blocked_agent(self):
        fleet = FleetView()
        fleet.register("s1")
        fleet.set_state("s1", "blocked")
        cfg = SupervisorConfig(blocked_priority=AttentionPriority.P1)
        supervisor = FleetSupervisor(fleet, config=cfg)
        escalations = supervisor.scan_once()
        assert len(escalations) == 1
        agent_id, priority, reason = escalations[0]
        assert agent_id == "s1"
        assert priority == AttentionPriority.P1
        assert "blocked" in reason

    def test_scan_escalates_error_agent(self):
        fleet = FleetView()
        fleet.register("s1")
        fleet.set_state("s1", "error")
        supervisor = FleetSupervisor(fleet)
        escalations = supervisor.scan_once()
        assert any(e[0] == "s1" for e in escalations)

    def test_scan_escalates_stale_agent(self):
        fleet = FleetView()
        rec = fleet.register("s1")
        object.__setattr__(rec, "last_updated", time.time() - 200)
        cfg = SupervisorConfig(stale_after_s=60.0, stale_priority=AttentionPriority.P2)
        supervisor = FleetSupervisor(fleet, config=cfg)
        escalations = supervisor.scan_once()
        assert any(e[0] == "s1" and e[1] == AttentionPriority.P2 for e in escalations)

    def test_scan_no_escalation_for_healthy_agent(self):
        fleet = FleetView()
        fleet.register("s1")
        supervisor = FleetSupervisor(fleet)
        escalations = supervisor.scan_once()
        assert escalations == []

    def test_on_escalate_callback(self):
        captured = []
        fleet = FleetView()
        fleet.register("s1")
        fleet.set_state("s1", "blocked")
        supervisor = FleetSupervisor(fleet, on_escalate=lambda *args: captured.append(args))
        supervisor.scan_once()
        assert len(captured) == 1

    def test_done_agent_gets_p4(self):
        fleet = FleetView()
        fleet.register("s1", priority=AttentionPriority.P2)
        fleet.set_state("s1", "done")
        supervisor = FleetSupervisor(fleet)
        supervisor.scan_once()
        assert fleet.peek("s1").attention_priority == AttentionPriority.P4

    def test_start_stop(self):
        fleet = FleetView()
        cfg = SupervisorConfig(poll_interval_s=0.05)
        supervisor = FleetSupervisor(fleet, config=cfg)
        supervisor.start()
        assert supervisor.running
        supervisor.stop(timeout=1.0)
        assert not supervisor.running

    def test_double_start_idempotent(self):
        fleet = FleetView()
        cfg = SupervisorConfig(poll_interval_s=0.1)
        supervisor = FleetSupervisor(fleet, config=cfg)
        supervisor.start()
        supervisor.start()
        assert supervisor.running
        supervisor.stop(timeout=1.0)
