"""Tests for FleetOrchestrator research patterns — MAP_REDUCE, DEBATE, DAG."""

from __future__ import annotations

from lyra_agent_swarm.fleet_orchestrator import (
    ExecutionPattern,
    FanOutBatch,
    FleetOrchestrator,
    FleetStatus,
    TaskItem,
    TaskItemStatus,
)


# ── FleetOrchestrator construction ──────────────────────────────────────


class TestFleetConstruction:
    def test_create_fleet_defaults(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("research-fleet")
        assert fleet.id.startswith("fleet_")
        assert fleet.name == "research-fleet"
        assert fleet.status == FleetStatus.FORMING

    def test_create_multiple_fleets(self):
        orch = FleetOrchestrator()
        f1 = orch.create_fleet("fleet-a")
        f2 = orch.create_fleet("fleet-b")
        assert f1.id != f2.id
        stats = orch.stats()
        assert stats["total_fleets"] >= 2


# ── Task management ─────────────────────────────────────────────────────


class TestTaskManagement:
    def test_fan_out_creates_tasks(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("test-fleet", agent_ids=("a1",))
        batch = orch.fan_out(fleet.id, ["Analyze paper about transformer attention"])
        assert len(batch.tasks) == 1
        assert batch.tasks[0].input == "Analyze paper about transformer attention"
        assert batch.tasks[0].status == TaskItemStatus.ASSIGNED

    def test_fan_out_multiple_items(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("lit-review", agent_ids=("a1", "a2"))
        inputs = ["paper-1", "paper-2", "paper-3", "paper-4", "paper-5"]
        batch = orch.fan_out(fleet.id, inputs)
        assert len(batch.tasks) == 5

    def test_task_status_transitions(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("test", agent_ids=("a1",))
        batch = orch.fan_out(fleet.id, ["Research task"])
        task = batch.tasks[0]
        assert task.status == TaskItemStatus.ASSIGNED

        completed = orch.complete_task(fleet.id, task.id, "Research complete")
        assert completed is not None
        assert completed.status == TaskItemStatus.COMPLETED

    def test_complete_task_failure_status(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("test", agent_ids=("a1",))
        batch = orch.fan_out(fleet.id, ["Risky task"])
        task = batch.tasks[0]

        failed = orch.complete_task(fleet.id, task.id, "Error: timeout", success=False)
        assert failed is not None
        assert failed.status == TaskItemStatus.FAILED


# ── FanOut ──────────────────────────────────────────────────────────────


class TestFanOut:
    def test_fan_out_dispatches_all_tasks(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("parallel-discovery", agent_ids=("a1", "a2", "a3"))
        items = [f"discover-source-{i}" for i in range(10)]
        result = orch.fan_out(fleet.id, items)
        assert result.pattern == ExecutionPattern.FAN_OUT
        assert len(result.tasks) == 10

    def test_fan_out_empty_fleet(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("empty")
        result = orch.fan_out(fleet.id, [])
        assert len(result.tasks) == 0


# ── MapReduce ───────────────────────────────────────────────────────────


class TestMapReduce:
    def test_map_reduce_workflow(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("literature-review", agent_ids=("a1", "a2"))
        items = [f"analyze-section-{i}" for i in range(6)]
        result = orch.map_reduce(fleet.id, "analyze_paper", "synthesize_findings", items)
        assert len(result.map_results) == 6
        assert "synthesize_findings" in result.synthesis
        assert result.map_agent_count >= 1


# ── Fleet lifecycle ─────────────────────────────────────────────────────


class TestFleetLifecycle:
    def test_full_lifecycle(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("research-cycle", agent_ids=("a1",))
        items = ["step-1", "step-2"]

        orch.update_status(fleet.id, FleetStatus.ACTIVE)
        f = orch.get_fleet(fleet.id)
        assert f is not None
        assert f.status == FleetStatus.ACTIVE

        batch = orch.fan_out(fleet.id, items)
        for task in batch.tasks:
            orch.complete_task(fleet.id, task.id, f"done-{task.input}")

        orch.update_status(fleet.id, FleetStatus.COMPLETED)
        f = orch.get_fleet(fleet.id)
        assert f is not None
        assert f.status == FleetStatus.COMPLETED

    def test_dissolve_fleet(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("temp-fleet")
        orch.dissolve(fleet.id)
        f = orch.get_fleet(fleet.id)
        assert f is not None
        assert f.status == FleetStatus.DISSOLVED

    def test_fleet_metrics(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("metrics-test", agent_ids=("a1", "a2"))
        items = [f"task-{i}" for i in range(4)]
        orch.fan_out(fleet.id, items)
        metrics = orch.refresh_metrics(fleet.id)
        assert metrics is not None
        assert metrics.total_tasks == 4


# ── Research-specific patterns ──────────────────────────────────────────


class TestResearchDispatchPatterns:
    def test_literature_review_as_map_reduce(self):
        """MAP_REDUCE: fan-out source analysis → reduce to synthesis."""
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("lit-review", agent_ids=("a1", "a2"))
        papers = ["paper-attention", "paper-transformers", "paper-rlhf"]
        result = orch.map_reduce(fleet.id, "Analyze", "Synthesize", papers)
        assert len(result.map_results) == 3
        assert "Synthesize" in result.synthesis

    def test_multi_source_discovery_as_fan_out(self):
        """FAN_OUT: 5 agents discover in parallel → merge unique sources."""
        orch = FleetOrchestrator()
        fleet = orch.create_fleet(
            "multi-source-discovery",
            agent_ids=("arxiv-agent", "semantic-scholar-agent", "github-agent", "pubmed-agent", "wikipedia-agent"),
        )
        sources = ["arxiv", "semantic-scholar", "github", "pubmed", "wikipedia"]
        result = orch.fan_out(fleet.id, [f"Search {src}" for src in sources])
        assert len(result.tasks) == 5

    def test_dag_pipeline_for_research(self):
        """DAG: Discovery→Analysis→Synthesis→Review→Curate via status management."""
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("research-dag", agent_ids=("a1", "a2", "a3"))
        orch.update_status(fleet.id, FleetStatus.ACTIVE)
        f = orch.get_fleet(fleet.id)
        assert f is not None
        assert f.status == FleetStatus.ACTIVE


# ── Batch operations ────────────────────────────────────────────────────


class TestBatchOperations:
    def test_fan_out_batch_creation(self):
        batch = FanOutBatch(
            batch_id="b1",
            tasks=(TaskItem(input="task-1"), TaskItem(input="task-2")),
        )
        assert len(batch.tasks) == 2
        assert batch.batch_id == "b1"

    def test_stats_aggregates(self):
        orch = FleetOrchestrator()
        for i in range(3):
            orch.create_fleet(f"fleet-{i}")
        stats = orch.stats()
        assert stats["total_fleets"] == 3

    def test_list_all_fleets(self):
        orch = FleetOrchestrator()
        orch.create_fleet("fleet-a")
        orch.create_fleet("fleet-b")
        assert len(orch.list_all()) == 2

    def test_list_active_fleets(self):
        orch = FleetOrchestrator()
        f1 = orch.create_fleet("active-one")
        orch.create_fleet("inactive")
        orch.update_status(f1.id, FleetStatus.ACTIVE)
        active = orch.list_active()
        assert len(active) == 1
        assert active[0].name == "active-one"

    def test_complete_task_updates_fleet_metrics(self):
        orch = FleetOrchestrator()
        fleet = orch.create_fleet("batch-metrics", agent_ids=("a1",))
        batch = orch.fan_out(fleet.id, ["item-1", "item-2", "item-3"])
        for task in batch.tasks:
            orch.complete_task(fleet.id, task.id, f"result-{task.input}")
        metrics = orch.refresh_metrics(fleet.id)
        assert metrics is not None
        assert metrics.completed_tasks == 3
