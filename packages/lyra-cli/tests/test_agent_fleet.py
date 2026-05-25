"""Tests for the unified agent fleet manager."""
from lyra_cli.tui_gateway.agent_fleet import (
    FleetStatus,
    FleetTask,
    SquadInfo,
    UnifiedAgentFleet,
)


class TestAgentFleet:
    def test_initial_state(self):
        fleet = UnifiedAgentFleet()
        assert not fleet.initialized
        fleet.initialize()
        assert fleet.initialized

    def test_double_init_idempotent(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        fleet.initialize()
        assert fleet.initialized

    def test_default_agents_created(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        agents = fleet.list_agents()
        assert len(agents) >= 8
        roles = {a["role"] for a in agents}
        assert "explorer" in roles
        assert "coder" in roles
        assert "reviewer" in roles

    def test_agent_roles(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        roles = fleet.agent_roles()
        assert "explorer" in roles
        assert "security" in roles
        assert roles["coder"]["description"] == "Code writing and editing"

    def test_submit_task(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        tid = fleet.submit_task("find auth bugs", category="search")
        assert len(tid) == 12
        task = fleet.get_task(tid)
        assert task is not None
        assert task.description == "find auth bugs"
        assert task.category == "search"

    def test_task_dispatch_assigns_agent(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        tid = fleet.submit_task("write login endpoint", category="code")
        task = fleet.get_task(tid)
        assert task is not None
        assert task.status in ("dispatched", "pending")
        assert task.assigned_agent != ""

    def test_complete_task(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        tid = fleet.submit_task("test task", category="general")
        fleet.complete_task(tid, result="done")
        task = fleet.get_task(tid)
        assert task.status == "completed"
        assert task.result == "done"

    def test_fail_task(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        tid = fleet.submit_task("bad task", category="general")
        fleet.complete_task(tid, error="something broke")
        task = fleet.get_task(tid)
        assert task.status == "failed"
        assert task.error == "something broke"

    def test_create_squad(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        squad = fleet.create_squad("dev-squad", ["explorer", "coder", "reviewer", "tester"])
        assert squad.leader == "explorer"
        assert len(squad.members) == 3
        assert squad.name == "dev-squad"

    def test_create_squad_fallback(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        squad = fleet.create_squad("custom", ["nonexistent1", "nonexistent2"])
        assert len(squad.members) >= 1  # falls back to available agents

    def test_list_squads(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        fleet.create_squad("alpha", ["explorer", "coder"])
        fleet.create_squad("beta", ["reviewer", "tester"])
        squads = fleet.list_squads()
        assert len(squads) == 2

    def test_fan_out(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        ids = fleet.fan_out([
            {"description": "task one", "category": "search"},
            {"description": "task two", "category": "code"},
            {"description": "task three", "category": "test"},
        ])
        assert len(ids) == 3
        assert len(set(ids)) == 3

    def test_status(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        status = fleet.status()
        assert status.total_agents >= 8
        assert status.idle_agents >= 0
        assert isinstance(status.throughput, float)

    def test_snapshot(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        fleet.submit_task("task a", category="search")
        snap = fleet.snapshot()
        assert "fleet" in snap
        assert "agents" in snap
        assert "squads" in snap
        assert snap["fleet"].total_agents >= 8

    def test_complete_task_frees_agent(self):
        fleet = UnifiedAgentFleet()
        fleet.initialize()
        initial = fleet.status()
        tid = fleet.submit_task("use an agent", category="code")
        _mid = fleet.status()
        fleet.complete_task(tid, result="ok")
        final = fleet.status()
        assert final.idle_agents == initial.idle_agents

    def test_fleet_task_dataclass(self):
        t = FleetTask(
            description="test",
            category="code",
            priority=2.0,
        )
        assert t.description == "test"
        assert t.status == "pending"
        assert t.priority == 2.0

    def test_fleet_status_dataclass(self):
        s = FleetStatus(
            active_agents=3,
            idle_agents=5,
            total_agents=8,
            pending_tasks=2,
            completed_tasks=10,
            failed_tasks=1,
            state="running",
        )
        assert s.total_agents == 8
        assert s.state == "running"

    def test_squad_info_dataclass(self):
        s = SquadInfo(
            id="sq1",
            name="test-squad",
            leader="explorer",
            members=["coder", "tester"],
        )
        assert s.name == "test-squad"
        assert s.leader == "explorer"
