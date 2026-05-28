"""Tests for UI modules: vibes_dashboard, fleet_view, mode_manager, btw, stats, tmux_manager."""

from __future__ import annotations

from lyra_cli.ui.vibes_dashboard import (
    VibeDimension,
    VibeReading,
    VibesDashboard,
)
from lyra_cli.ui.fleet_view import (
    AgentStatus,
    FleetAgent,
    FleetView,
)
from lyra_cli.ui.mode_manager import (
    AgentMode,
    ModeManager,
)
from lyra_cli.commands.btw import (
    BtwPriority,
    BtwNote,
    BtwQueue,
)
from lyra_cli.commands.stats import (
    StatsCollector,
)
from lyra_cli.terminal.tmux_manager import TmuxManager


class TestVibesDashboard:
    def test_record_and_snapshot(self):
        dashboard = VibesDashboard()
        dashboard.record(VibeDimension.CONFIDENCE, 0.8)
        dashboard.record(VibeDimension.CURIOSITY, 0.6)
        snapshot = dashboard.snapshot()
        assert snapshot is not None
        assert len(snapshot.readings) >= 1
        conf_reading = next(
            (r for r in snapshot.readings if r.dimension == VibeDimension.CONFIDENCE), None
        )
        assert conf_reading is not None
        assert 0.0 <= conf_reading.score <= 1.0

    def test_dominant_dimension(self):
        dashboard = VibesDashboard()
        dashboard.record(VibeDimension.CONFIDENCE, 0.9)
        dashboard.record(VibeDimension.CURIOSITY, 0.3)
        snapshot = dashboard.snapshot()
        assert snapshot.dominant_dimension is not None

    def test_get_alerts(self):
        dashboard = VibesDashboard()
        dashboard.record(VibeDimension.CAUTION, 0.96)
        alerts = dashboard.get_alerts()
        assert isinstance(alerts, list)

    def test_vibe_reading_frozen(self):
        reading = VibeReading(
            dimension=VibeDimension.HELPFULNESS, score=0.75, trend=0.0, timestamp=1000.0
        )
        assert reading.score == 0.75
        assert reading.dimension == VibeDimension.HELPFULNESS

    def test_alerts_cleared_after_get(self):
        dashboard = VibesDashboard()
        dashboard.record(VibeDimension.CONFIDENCE, 0.99)
        alerts = dashboard.get_alerts()
        assert len(alerts) >= 1
        alerts2 = dashboard.get_alerts()
        assert len(alerts2) == 0


class TestFleetView:
    def test_register_agent(self):
        fv = FleetView()
        agent = fv.register("agent-1", "Worker Alpha")
        assert agent.agent_id == "agent-1"
        assert agent.name == "Worker Alpha"
        assert agent.status == AgentStatus.IDLE

    def test_heartbeat_updates(self):
        fv = FleetView()
        fv.register("agent-2", "Researcher Beta")
        agent = fv.heartbeat("agent-2")
        assert agent is not None
        assert agent.agent_id == "agent-2"

    def test_heartbeat_nonexistent(self):
        fv = FleetView()
        assert fv.heartbeat("nonexistent") is None

    def test_update_status(self):
        fv = FleetView()
        fv.register("agent-3", "Planner Gamma")
        agent = fv.update_status("agent-3", AgentStatus.BUSY)
        assert agent is not None
        assert agent.status == AgentStatus.BUSY

    def test_update_status_nonexistent(self):
        fv = FleetView()
        assert fv.update_status("nonexistent", AgentStatus.BUSY) is None

    def test_record_task(self):
        fv = FleetView()
        fv.register("agent-4", "Executor Delta")
        fv.record_task("agent-4", success=True, response_ms=150.0)
        agent = fv.get_agent("agent-4")
        assert agent is not None
        assert agent.task_count == 1

    def test_summary(self):
        fv = FleetView()
        fv.register("a", "Alpha")
        fv.register("b", "Beta")
        summary = fv.summary()
        assert summary.total_agents == 2

    def test_fleet_agent_is_healthy(self):
        agent = FleetAgent(
            agent_id="a1",
            name="TestAgent",
            status=AgentStatus.IDLE,
            task_count=5,
            success_rate=0.95,
            avg_response_ms=120.0,
            last_heartbeat=1000.0,
        )
        assert agent.is_healthy

    def test_fleet_agent_is_not_healthy(self):
        agent = FleetAgent(
            agent_id="a2",
            name="BadAgent",
            status=AgentStatus.OFFLINE,
            task_count=0,
            success_rate=0.0,
            avg_response_ms=0.0,
            last_heartbeat=0.0,
        )
        assert not agent.is_healthy

    def test_get_agent_nonexistent(self):
        fv = FleetView()
        assert fv.get_agent("nonexistent") is None


class TestModeManager:
    def test_transition_allowed(self):
        mm = ModeManager()
        transition = mm.transition(AgentMode.PLAN, "testing")
        assert transition.from_mode == AgentMode.CHAT
        assert transition.to_mode == AgentMode.PLAN

    def test_transition_disallowed_raises(self):
        mm = ModeManager()
        mm.transition(AgentMode.EXECUTE)
        with __import__("pytest").raises(ValueError):
            mm.transition(AgentMode.AUTOPILOT)

    def test_can_transition(self):
        mm = ModeManager()
        assert mm.can_transition(AgentMode.PLAN)

    def test_can_transition_false(self):
        mm = ModeManager()
        assert not mm.can_transition(AgentMode.AUTOPILOT)

    def test_get_allowed_transitions(self):
        mm = ModeManager()
        allowed = mm.get_allowed_transitions()
        assert len(allowed) > 0

    def test_is_write_allowed(self):
        mm = ModeManager()
        assert not mm.is_write_allowed()

    def test_is_network_allowed(self):
        mm = ModeManager()
        assert not mm.is_network_allowed()

    def test_get_history(self):
        mm = ModeManager()
        mm.transition(AgentMode.PLAN)
        history = mm.get_history()
        assert len(history) > 0

    def test_current_mode(self):
        mm = ModeManager(initial_mode=AgentMode.RESEARCH)
        assert mm.current_mode == AgentMode.RESEARCH
        assert mm.is_network_allowed()


class TestBtwQueue:
    def test_enqueue_and_deliver(self):
        q = BtwQueue()
        q.enqueue("Remember to check logs", BtwPriority.NORMAL)
        q.enqueue("Critical security patch", BtwPriority.HIGH)
        assert q.pending_count() == 2
        delivered = q.deliver()
        assert len(delivered) >= 1

    def test_get_pending(self):
        q = BtwQueue()
        n1 = q.enqueue("Note 1", BtwPriority.LOW)
        n2 = q.enqueue("Note 2", BtwPriority.HIGH)
        pending = q.get_pending()
        assert len(pending) == 2

    def test_empty_queue_deliver(self):
        q = BtwQueue()
        result = q.deliver()
        assert result == []

    def test_priority_sorting(self):
        q = BtwQueue()
        q.enqueue("low", BtwPriority.LOW)
        q.enqueue("high", BtwPriority.HIGH)
        q.enqueue("normal", BtwPriority.NORMAL)
        pending = q.get_pending()
        assert pending[0].priority == BtwPriority.HIGH

    def test_btw_note_frozen(self):
        note = BtwNote(
            note_id="btw-1",
            message="Test note",
            priority=BtwPriority.NORMAL,
            source="test",
            created_at=1000.0,
            delivered=False,
        )
        assert note.message == "Test note"


class TestStatsCollector:
    def test_start_and_end_session(self):
        sc = StatsCollector()
        sc.start_session("test-session")
        sc.record_task("test-session", True)
        session = sc.end_session("test-session")
        assert session is not None
        assert session.tasks_completed == 1

    def test_record_tokens(self):
        sc = StatsCollector()
        sc.start_session("s1")
        sc.record_tokens("s1", 100)
        session = sc.end_session("s1")
        assert session is not None
        assert session.tokens_used == 100

    def test_record_tool_call(self):
        sc = StatsCollector()
        sc.start_session("s2")
        sc.record_tool_call("s2")
        session = sc.end_session("s2")
        assert session is not None
        assert session.tools_called == 1

    def test_record_model_switch(self):
        sc = StatsCollector()
        sc.start_session("s3")
        sc.record_model_switch("s3")
        session = sc.end_session("s3")
        assert session is not None
        assert session.model_switches == 1

    def test_aggregate(self):
        sc = StatsCollector()
        sc.start_session("a")
        sc.record_task("a", True)
        sc.end_session("a")
        sc.start_session("b")
        sc.record_task("b", False)
        sc.end_session("b")
        agg = sc.aggregate()
        assert agg.total_sessions == 2

    def test_get_session_nonexistent(self):
        sc = StatsCollector()
        assert sc.get_session("nonexistent") is None

    def test_success_rate_property(self):
        sc = StatsCollector()
        sc.start_session("sr")
        sc.record_task("sr", True)
        sc.record_task("sr", True)
        sc.record_task("sr", False)
        session = sc.end_session("sr")
        assert session is not None
        assert abs(session.success_rate - 66.7) < 1.0

    def test_auto_start_session(self):
        sc = StatsCollector()
        sc.record_task("auto-session", True)
        session = sc.end_session("auto-session")
        assert session is not None
        assert session.tasks_completed == 1


class TestTmuxManager:
    def test_available_or_not(self):
        tm = TmuxManager()
        assert isinstance(tm.is_available, bool)

    def test_stats(self):
        tm = TmuxManager()
        s = tm.stats()
        assert "tmux_available" in s
