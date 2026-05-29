"""Tests for Plan 12: Fleet Orchestrator — fan-out, map-reduce, fleet metrics."""

from __future__ import annotations

import pytest
from lyra_agent_swarm.fleet_orchestrator import (
    ExecutionPattern,
    FanOutBatch,
    Fleet,
    FleetMetrics,
    FleetOrchestrator,
    FleetStatus,
    MapReduceResult,
    TaskItem,
    TaskItemStatus,
    chunk_items,
    estimate_fleet_cost,
)


class TestTaskItem:
    def test_create(self):
        t = TaskItem(input="src/a.py", status=TaskItemStatus.QUEUED)
        assert t.input == "src/a.py"
        assert t.status == TaskItemStatus.QUEUED
        assert t.result == ""

    def test_completed(self):
        t = TaskItem(
            input="src/b.py",
            status=TaskItemStatus.COMPLETED,
            result="Analysis complete",
            assigned_agent="agent-1",
        )
        assert t.status == TaskItemStatus.COMPLETED
        assert t.assigned_agent == "agent-1"

    def test_is_frozen(self):
        t = TaskItem(input="file.py")
        with pytest.raises(Exception):
            t.status = TaskItemStatus.COMPLETED


class TestFanOutBatch:
    def test_create(self):
        tasks = (TaskItem(input="a"), TaskItem(input="b"))
        b = FanOutBatch(tasks=tasks, pattern=ExecutionPattern.FAN_OUT, agent_count=2)
        assert len(b.tasks) == 2
        assert b.agent_count == 2

    def test_is_frozen(self):
        b = FanOutBatch()
        with pytest.raises(Exception):
            b.agent_count = 5


class TestMapReduceResult:
    def test_create(self):
        r = MapReduceResult(
            map_results=("r1", "r2"),
            synthesis="Combined",
            map_agent_count=2,
            reduce_agent="lead",
            total_tokens=500,
        )
        assert len(r.map_results) == 2
        assert r.synthesis == "Combined"
        assert r.total_tokens == 500

    def test_is_frozen(self):
        r = MapReduceResult()
        with pytest.raises(Exception):
            r.synthesis = "new"


class TestFleetMetrics:
    def test_default(self):
        m = FleetMetrics()
        assert m.total_tasks == 0
        assert m.completed_tasks == 0

    def test_custom(self):
        m = FleetMetrics(
            total_tasks=10,
            completed_tasks=7,
            failed_tasks=1,
            total_agents=4,
            active_agents=2,
            idle_agents=2,
            throughput_tasks_per_min=3.5,
        )
        assert m.total_tasks == 10
        assert m.completed_tasks == 7
        assert m.throughput_tasks_per_min == 3.5

    def test_is_frozen(self):
        m = FleetMetrics()
        with pytest.raises(Exception):
            m.total_tasks = 100


class TestFleet:
    def test_create(self):
        f = Fleet(name="test-fleet", agent_ids=("a1", "a2", "a3"))
        assert f.id.startswith("fleet_")
        assert f.name == "test-fleet"
        assert f.agent_count == 3
        assert f.task_count == 0

    def test_with_squads(self):
        f = Fleet(name="squad-fleet", squad_ids=("s1", "s2"))
        assert f.squad_count == 2

    def test_is_frozen(self):
        f = Fleet(name="test")
        with pytest.raises(Exception):
            f.name = "changed"


class TestFleetOrchestratorCreate:
    def test_create_fleet(self):
        o = FleetOrchestrator()
        f = o.create_fleet("test", agent_ids=("a1", "a2"))
        assert f.name == "test"
        assert f.agent_count == 2
        assert f.status == FleetStatus.FORMING

    def test_get_fleet(self):
        o = FleetOrchestrator()
        f = o.create_fleet("test")
        fetched = o.get_fleet(f.id)
        assert fetched is not None
        assert fetched.name == "test"

    def test_get_nonexistent(self):
        o = FleetOrchestrator()
        assert o.get_fleet("nonexistent") is None

    def test_list_all(self):
        o = FleetOrchestrator()
        o.create_fleet("f1")
        o.create_fleet("f2")
        assert len(o.list_all()) == 2

    def test_list_active(self):
        o = FleetOrchestrator()
        f = o.create_fleet("active")
        o.update_status(f.id, FleetStatus.ACTIVE)
        o.create_fleet("forming")
        assert len(o.list_active()) == 1

    def test_update_status(self):
        o = FleetOrchestrator()
        f = o.create_fleet("test")
        updated = o.update_status(f.id, FleetStatus.ACTIVE)
        assert updated is not None
        assert updated.status == FleetStatus.ACTIVE

    def test_update_status_nonexistent(self):
        o = FleetOrchestrator()
        assert o.update_status("nonexistent", FleetStatus.ACTIVE) is None

    def test_dissolve(self):
        o = FleetOrchestrator()
        f = o.create_fleet("test")
        assert o.dissolve(f.id)
        fleet = o.get_fleet(f.id)
        assert fleet is not None
        assert fleet.status == FleetStatus.DISSOLVED

    def test_dissolve_nonexistent(self):
        o = FleetOrchestrator()
        assert not o.dissolve("nonexistent")


class TestFanOut:
    def test_fan_out_distributes_items(self):
        o = FleetOrchestrator()
        f = o.create_fleet("fanout", agent_ids=("a1", "a2", "a3"))
        items = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py", "file6.py"]
        batch = o.fan_out(f.id, items, list(f.agent_ids))
        assert len(batch.tasks) == 6
        assert batch.agent_count == 3

    def test_fan_out_round_robin_assignment(self):
        o = FleetOrchestrator()
        f = o.create_fleet("rr", agent_ids=("a1", "a2"))
        items = ["f1", "f2", "f3", "f4"]
        batch = o.fan_out(f.id, items, list(f.agent_ids))
        agents = [t.assigned_agent for t in batch.tasks]
        assert agents == ["a1", "a2", "a1", "a2"]

    def test_fan_out_nonexistent_fleet(self):
        o = FleetOrchestrator()
        batch = o.fan_out("nonexistent", ["item1"])
        assert len(batch.tasks) == 0

    def test_fan_out_no_agents(self):
        o = FleetOrchestrator()
        f = o.create_fleet("no-agents")
        batch = o.fan_out(f.id, ["item1"])
        assert len(batch.tasks) == 0

    def test_fan_out_custom_agents(self):
        o = FleetOrchestrator()
        f = o.create_fleet("custom", agent_ids=("fleet-a1", "fleet-a2"))
        items = ["a", "b", "c"]
        batch = o.fan_out(f.id, items, agent_ids=["external-a1"])
        assert batch.agent_count == 1
        assert all(t.assigned_agent == "external-a1" for t in batch.tasks)

    def test_fan_out_updates_fleet_tasks(self):
        o = FleetOrchestrator()
        f = o.create_fleet("update", agent_ids=("a1",))
        items = ["f1", "f2"]
        o.fan_out(f.id, items)
        fleet = o.get_fleet(f.id)
        assert fleet is not None
        assert fleet.task_count == 2


class TestCompleteTask:
    def test_complete_task_success(self):
        o = FleetOrchestrator()
        f = o.create_fleet("ct", agent_ids=("a1",))
        batch = o.fan_out(f.id, ["t1"])
        task_id = batch.tasks[0].id
        completed = o.complete_task(f.id, task_id, "Done!")
        assert completed is not None
        assert completed.status == TaskItemStatus.COMPLETED
        assert completed.result == "Done!"

    def test_complete_task_failure(self):
        o = FleetOrchestrator()
        f = o.create_fleet("fail", agent_ids=("a1",))
        batch = o.fan_out(f.id, ["t1"])
        task_id = batch.tasks[0].id
        completed = o.complete_task(f.id, task_id, "Error: fail", success=False)
        assert completed is not None
        assert completed.status == TaskItemStatus.FAILED
        assert completed.error == "Error: fail"

    def test_complete_nonexistent_task(self):
        o = FleetOrchestrator()
        f = o.create_fleet("nonexist", agent_ids=("a1",))
        assert o.complete_task(f.id, "nonexistent", "result") is None

    def test_complete_nonexistent_fleet(self):
        o = FleetOrchestrator()
        assert o.complete_task("nonexistent", "t1", "result") is None


class TestMapReduce:
    def test_map_reduce_basic(self):
        o = FleetOrchestrator()
        f = o.create_fleet("mr", agent_ids=("a1", "a2", "a3"))
        items = ["src/a.py", "src/b.py", "src/c.py"]
        result = o.map_reduce(f.id, "analyze", "synthesize", items)
        assert len(result.map_results) == 3
        assert "synthesize" in result.synthesis
        assert result.map_agent_count >= 1

    def test_map_reduce_empty(self):
        o = FleetOrchestrator()
        f = o.create_fleet("empty-mr")
        result = o.map_reduce(f.id, "map", "reduce", [])
        assert len(result.map_results) == 0

    def test_map_reduce_single_item(self):
        o = FleetOrchestrator()
        f = o.create_fleet("single-mr", agent_ids=("a1",))
        result = o.map_reduce(f.id, "analyze", "synthesize", ["single.py"])
        assert len(result.map_results) == 1
        assert result.reduce_agent == "a1"


class TestFleetOrchestratorMetrics:
    def test_refresh_metrics(self):
        o = FleetOrchestrator()
        f = o.create_fleet("m", agent_ids=("a1", "a2"))
        batch = o.fan_out(f.id, ["f1", "f2", "f3", "f4"])
        o.complete_task(f.id, batch.tasks[0].id, "done")
        o.complete_task(f.id, batch.tasks[1].id, "done")
        metrics = o.refresh_metrics(f.id)
        assert metrics is not None
        assert metrics.total_tasks == 4
        assert metrics.completed_tasks == 2

    def test_get_metrics(self):
        o = FleetOrchestrator()
        f = o.create_fleet("gm")
        metrics = o.get_metrics(f.id)
        assert metrics is not None
        assert metrics.total_tasks == 0

    def test_metrics_nonexistent_fleet(self):
        o = FleetOrchestrator()
        assert o.get_metrics("nope") is None
        assert o.refresh_metrics("nope") is None

    def test_metrics_throughput(self):
        o = FleetOrchestrator()
        f = o.create_fleet("tp", agent_ids=("a1",))
        batch = o.fan_out(f.id, ["f1"])
        o.complete_task(f.id, batch.tasks[0].id, "done")
        metrics = o.refresh_metrics(f.id)
        assert metrics is not None
        assert metrics.throughput_tasks_per_min >= 0


class TestFleetOrchestratorStats:
    def test_stats_empty(self):
        o = FleetOrchestrator()
        s = o.stats()
        assert s["total_fleets"] == 0
        assert s["total_tasks"] == 0

    def test_stats_with_fleets(self):
        o = FleetOrchestrator()
        f1 = o.create_fleet("f1", agent_ids=("a1", "a2"))
        o.create_fleet("f2", agent_ids=("a3",))
        o.update_status(f1.id, FleetStatus.ACTIVE)
        batch = o.fan_out(f1.id, ["a", "b", "c"])
        o.complete_task(f1.id, batch.tasks[0].id, "ok")
        s = o.stats()
        assert s["total_fleets"] == 2
        assert s["active_fleets"] == 1
        assert s["total_agents"] == 3
        assert s["total_tasks"] == 3


class TestUtilities:
    def test_chunk_items_even(self):
        result = chunk_items(["a", "b", "c", "d", "e", "f"], 2)
        assert result == [["a", "b"], ["c", "d"], ["e", "f"]]

    def test_chunk_items_uneven(self):
        result = chunk_items(["a", "b", "c", "d", "e"], 2)
        assert result == [["a", "b"], ["c", "d"], ["e"]]

    def test_chunk_items_empty(self):
        assert chunk_items([], 3) == []

    def test_estimate_fleet_cost(self):
        cost = estimate_fleet_cost(task_count=100, avg_tokens_per_task=2000)
        assert cost == pytest.approx(0.6)

    def test_estimate_fleet_cost_default(self):
        cost = estimate_fleet_cost(task_count=10)
        assert cost == pytest.approx(0.06)


class TestEnums:
    def test_fleet_status_values(self):
        assert FleetStatus.FORMING.value == "forming"
        assert FleetStatus.ACTIVE.value == "active"
        assert FleetStatus.PAUSED.value == "paused"
        assert FleetStatus.COMPLETED.value == "completed"
        assert FleetStatus.FAILED.value == "failed"
        assert FleetStatus.DISSOLVED.value == "dissolved"

    def test_execution_pattern_values(self):
        assert ExecutionPattern.FAN_OUT.value == "fan_out"
        assert ExecutionPattern.MAP_REDUCE.value == "map_reduce"
        assert ExecutionPattern.DAG.value == "dag"

    def test_task_item_status_values(self):
        assert TaskItemStatus.QUEUED.value == "queued"
        assert TaskItemStatus.RUNNING.value == "running"
        assert TaskItemStatus.COMPLETED.value == "completed"
        assert TaskItemStatus.FAILED.value == "failed"
