"""Tests for hierarchical swarm topology, dynamic reconfiguration, and health monitoring."""

from __future__ import annotations

import pytest
import time

from lyra_agent_swarm.topology.hierarchical import (
    HierarchicalTopology,
    SquadRole,
    SquadTemplate,
    TopologyLevel,
    TopologyNode,
)
from lyra_agent_swarm.topology.dynamic_reconfig import (
    BanditMetrics,
    DynamicReconfig,
    ReconfigAction,
    ReconfigPlan,
    ReconfigTrigger,
)
from lyra_agent_swarm.topology.health_monitor import (
    AgentHealth,
    HealthMonitor,
    HealthProbe,
    HealthStatus,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def workers():
    return ["worker-a", "worker-b", "worker-c"]


@pytest.fixture
def squad_template():
    return SquadTemplate(
        name="backend-squad",
        domain="backend",
        min_workers=2,
        max_workers=5,
        required_roles=(SquadRole.CAPTAIN, SquadRole.WORKER, SquadRole.CRITIC),
    )


@pytest.fixture
def topology():
    return HierarchicalTopology()


@pytest.fixture
def populated_topology(topology, squad_template):
    topology.add_colony("main-colony")
    topology.add_squad("main-colony", "squad-1", squad_template)
    topology.add_worker("squad-1", "captain-1", SquadRole.CAPTAIN)
    topology.add_worker("squad-1", "worker-a", SquadRole.WORKER)
    topology.add_worker("squad-1", "worker-b", SquadRole.WORKER)
    topology.add_worker("squad-1", "critic-1", SquadRole.CRITIC)
    return topology


@pytest.fixture
def reconfig():
    return DynamicReconfig()


@pytest.fixture
def health_monitor():
    return HealthMonitor()


# ── TestHierarchicalTopology ─────────────────────────────────


class TestTopologyNode:
    def test_node_creation(self):
        node = TopologyNode(node_id="n1", level=TopologyLevel.COLONY)
        assert node.node_id == "n1"
        assert node.level == TopologyLevel.COLONY
        assert node.parent_id is None
        assert node.children == ()

    def test_node_immutability(self):
        node = TopologyNode(node_id="n1", level=TopologyLevel.SQUAD)
        with pytest.raises(Exception):
            node.node_id = "n2"

    def test_node_with_parent(self):
        node = TopologyNode(
            node_id="s1", level=TopologyLevel.SQUAD, parent_id="c1"
        )
        assert node.parent_id == "c1"

    def test_node_with_children(self):
        node = TopologyNode(
            node_id="s1",
            level=TopologyLevel.SQUAD,
            children=("w1", "w2"),
        )
        assert node.children == ("w1", "w2")

    def test_node_metadata(self):
        node = TopologyNode(
            node_id="n1",
            level=TopologyLevel.WORKER,
            metadata={"role": "critic", "capability": 0.85},
        )
        assert node.metadata["role"] == "critic"

    def test_node_repr(self):
        node = TopologyNode(node_id="n1", level=TopologyLevel.SQUAD)
        rep = repr(node)
        assert "n1" in rep
        assert "squad" in rep


class TestSquadTemplate:
    def test_template_creation(self):
        t = SquadTemplate(
            name="research-squad",
            domain="research",
            min_workers=2,
            max_workers=8,
            required_roles=(SquadRole.CAPTAIN, SquadRole.WORKER),
        )
        assert t.name == "research-squad"
        assert t.min_workers == 2
        assert t.max_workers == 8

    def test_template_immutability(self):
        t = SquadTemplate(
            name="test", domain="test", min_workers=1, max_workers=3
        )
        with pytest.raises(Exception):
            t.name = "changed"

    def test_template_default_roles(self):
        t = SquadTemplate(name="test", domain="test")
        assert SquadRole.CAPTAIN in t.required_roles
        assert SquadRole.WORKER in t.required_roles

    def test_template_stagnation_threshold(self):
        t = SquadTemplate(
            name="test",
            domain="test",
            stagnation_threshold_ms=5000.0,
        )
        assert t.stagnation_threshold_ms == 5000.0

    def test_template_health_check_interval(self):
        t = SquadTemplate(
            name="test",
            domain="test",
            health_check_interval_ms=1000.0,
        )
        assert t.health_check_interval_ms == 1000.0


class TestHierarchicalTopologyBasic:
    def test_empty_topology(self):
        t = HierarchicalTopology()
        assert t.colony_count == 0
        assert t.squad_count == 0
        assert t.worker_count == 0

    def test_add_colony(self, topology):
        colony = topology.add_colony("main")
        assert colony.node_id == "main"
        assert colony.level == TopologyLevel.COLONY
        assert topology.colony_count == 1

    def test_add_duplicate_colony(self, topology):
        topology.add_colony("main")
        with pytest.raises(ValueError, match="already exists"):
            topology.add_colony("main")

    def test_add_squad(self, topology, squad_template):
        topology.add_colony("main")
        squad = topology.add_squad("main", "squad-1", squad_template)
        assert squad.node_id == "squad-1"
        assert squad.level == TopologyLevel.SQUAD
        assert squad.parent_id == "main"
        assert topology.squad_count == 1

    def test_add_squad_missing_colony(self, topology, squad_template):
        with pytest.raises(ValueError, match="Parent colony.*not found"):
            topology.add_squad("nonexistent", "squad-1", squad_template)

    def test_add_worker(self, topology, squad_template):
        topology.add_colony("main")
        topology.add_squad("main", "squad-1", squad_template)
        worker = topology.add_worker("squad-1", "worker-a", SquadRole.WORKER)
        assert worker.node_id == "worker-a"
        assert worker.level == TopologyLevel.WORKER
        assert worker.parent_id == "squad-1"
        assert topology.worker_count == 1

    def test_add_worker_missing_squad(self, topology):
        with pytest.raises(ValueError, match="Parent squad.*not found"):
            topology.add_worker("nonexistent", "w1", SquadRole.WORKER)

    def test_remove_worker(self, populated_topology):
        populated_topology.remove_worker("worker-a")
        assert populated_topology.worker_count == 3  # captain-1, worker-b, critic-1

    def test_remove_squad_cascades_workers(self, populated_topology):
        populated_topology.remove_squad("squad-1")
        assert populated_topology.squad_count == 0
        assert populated_topology.worker_count == 0

    def test_remove_colony_cascades(self, populated_topology):
        populated_topology.remove_colony("main-colony")
        assert populated_topology.colony_count == 0
        assert populated_topology.squad_count == 0
        assert populated_topology.worker_count == 0

    def test_get_node(self, populated_topology):
        node = populated_topology.get_node("squad-1")
        assert node is not None
        assert node.level == TopologyLevel.SQUAD

    def test_get_node_missing(self, populated_topology):
        assert populated_topology.get_node("nonexistent") is None

    def test_get_children(self, populated_topology):
        children = populated_topology.get_children("squad-1")
        child_ids = {c.node_id for c in children}
        assert "captain-1" in child_ids
        assert "worker-a" in child_ids
        assert "worker-b" in child_ids
        assert "critic-1" in child_ids

    def test_get_parent(self, populated_topology):
        parent = populated_topology.get_parent("worker-a")
        assert parent is not None
        assert parent.node_id == "squad-1"

    def test_get_parent_of_colony(self, populated_topology):
        assert populated_topology.get_parent("main-colony") is None

    def test_get_peers(self, populated_topology):
        peers = populated_topology.get_peers("captain-1")
        peer_ids = {p.node_id for p in peers}
        # Peers are siblings with the same parent (same squad)
        assert "worker-a" in peer_ids
        assert "worker-b" in peer_ids
        assert "critic-1" in peer_ids
        # captain-1 should not be in its own peer list
        assert "captain-1" not in peer_ids


class TestHierarchicalTopologyRouting:
    def test_route_to_captain(self, populated_topology):
        route = populated_topology.route_task(
            target_role=SquadRole.CAPTAIN, squad_id="squad-1"
        )
        assert route is not None
        assert route.node_id == "captain-1"

    def test_route_to_worker(self, populated_topology):
        route = populated_topology.route_task(
            target_role=SquadRole.WORKER, squad_id="squad-1"
        )
        assert route is not None
        assert route.level == TopologyLevel.WORKER

    def test_route_no_matching_role(self, populated_topology):
        route = populated_topology.route_task(
            target_role=SquadRole.SYNTHESIZER, squad_id="squad-1"
        )
        assert route is None

    def test_list_by_level(self, populated_topology):
        colonies = populated_topology.list_by_level(TopologyLevel.COLONY)
        squads = populated_topology.list_by_level(TopologyLevel.SQUAD)
        workers = populated_topology.list_by_level(TopologyLevel.WORKER)
        assert len(colonies) == 1
        assert len(squads) == 1
        assert len(workers) == 4

    def test_get_topology_summary(self, populated_topology):
        summary = populated_topology.get_summary()
        assert summary["colonies"] == 1
        assert summary["squads"] == 1
        assert summary["workers"] == 4

    def test_get_squad_workers(self, populated_topology):
        workers = populated_topology.get_squad_workers("squad-1")
        assert len(workers) == 4

    def test_multi_colony_topology(self, topology, squad_template):
        topology.add_colony("colony-a")
        topology.add_colony("colony-b")
        topology.add_squad("colony-a", "sq-a1", squad_template)
        topology.add_squad("colony-b", "sq-b1", squad_template)
        assert topology.colony_count == 2
        assert topology.squad_count == 2
        assert topology.get_children("colony-a")[0].node_id == "sq-a1"

    def test_add_worker_exceeds_max(self, topology, squad_template):
        t = SquadTemplate(name="small", domain="test", min_workers=1, max_workers=2)
        topology.add_colony("main")
        topology.add_squad("main", "sq-1", t)
        topology.add_worker("sq-1", "w1", SquadRole.WORKER)
        topology.add_worker("sq-1", "w2", SquadRole.WORKER)
        with pytest.raises(ValueError, match="exceeds max"):
            topology.add_worker("sq-1", "w3", SquadRole.WORKER)


# ── TestDynamicReconfig ───────────────────────────────────────


class TestReconfigPlan:
    def test_plan_creation(self):
        plan = ReconfigPlan(
            plan_id="rp-1",
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.REASSIGN_LEADER,
            target_squad_id="squad-1",
            reason="No progress for 10s",
        )
        assert plan.trigger == ReconfigTrigger.STAGNATION
        assert plan.action == ReconfigAction.REASSIGN_LEADER
        assert plan.executed is False

    def test_plan_immutability(self):
        plan = ReconfigPlan(
            plan_id="rp-1",
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.DISSOLVE,
            target_squad_id="s-1",
        )
        with pytest.raises(Exception):
            plan.action = ReconfigAction.MERGE

    def test_plan_with_params(self):
        plan = ReconfigPlan(
            plan_id="rp-1",
            trigger=ReconfigTrigger.LOAD_IMBALANCE,
            action=ReconfigAction.ADD_WORKER,
            target_squad_id="s-1",
            params={"worker_count": 3},
        )
        assert plan.params["worker_count"] == 3


class TestDynamicReconfigBasic:
    def test_empty_state(self, reconfig):
        assert reconfig.plan_count == 0
        assert reconfig.pending_plan_count == 0

    def test_create_plan(self, reconfig):
        plan = reconfig.create_plan(
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.REASSIGN_LEADER,
            target_squad_id="squad-1",
            reason="Stagnation detected",
        )
        assert plan.plan_id.startswith("rp-")
        assert reconfig.plan_count == 1

    def test_plan_starts_pending(self, reconfig):
        plan = reconfig.create_plan(
            trigger=ReconfigTrigger.FAILURE,
            action=ReconfigAction.DISSOLVE,
            target_squad_id="s-1",
        )
        assert not plan.executed
        assert reconfig.pending_plan_count == 1

    def test_execute_plan(self, reconfig):
        plan = reconfig.create_plan(
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.ADD_WORKER,
            target_squad_id="s-1",
        )
        result = reconfig.execute_plan(plan.plan_id)
        assert result is not None
        assert result.executed is True
        assert reconfig.pending_plan_count == 0

    def test_execute_nonexistent_plan(self, reconfig):
        with pytest.raises(ValueError, match="not found"):
            reconfig.execute_plan("nonexistent")

    def test_execute_already_executed(self, reconfig):
        plan = reconfig.create_plan(
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.ADD_WORKER,
            target_squad_id="s-1",
        )
        reconfig.execute_plan(plan.plan_id)
        with pytest.raises(ValueError, match="already executed"):
            reconfig.execute_plan(plan.plan_id)

    def test_multiple_plans(self, reconfig):
        reconfig.create_plan(
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.REASSIGN_LEADER,
            target_squad_id="s-1",
        )
        reconfig.create_plan(
            trigger=ReconfigTrigger.LOAD_IMBALANCE,
            action=ReconfigAction.SPLIT,
            target_squad_id="s-2",
        )
        assert reconfig.plan_count == 2

    def test_get_pending_plans(self, reconfig):
        reconfig.create_plan(
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.DISSOLVE,
            target_squad_id="s-1",
        )
        reconfig.create_plan(
            trigger=ReconfigTrigger.FAILURE,
            action=ReconfigAction.MERGE,
            target_squad_id="s-2",
        )
        pending = reconfig.get_pending_plans()
        assert len(pending) == 2

    def test_clear_executed_plans(self, reconfig):
        p1 = reconfig.create_plan(
            trigger=ReconfigTrigger.STAGNATION,
            action=ReconfigAction.ADD_WORKER,
            target_squad_id="s-1",
        )
        reconfig.execute_plan(p1.plan_id)
        reconfig.create_plan(
            trigger=ReconfigTrigger.LOAD_IMBALANCE,
            action=ReconfigAction.SPLIT,
            target_squad_id="s-2",
        )
        cleared = reconfig.clear_executed()
        assert cleared == 1
        assert reconfig.plan_count == 1


class TestDynamicReconfigStagnation:
    def test_detect_stagnation(self, reconfig):
        result = reconfig.detect_stagnation(
            squad_id="s-1",
            last_progress_ms=15_000.0,
            stagnation_threshold_ms=10_000.0,
        )
        assert result is True

    def test_no_stagnation_under_threshold(self, reconfig):
        result = reconfig.detect_stagnation(
            squad_id="s-1",
            last_progress_ms=5_000.0,
            stagnation_threshold_ms=10_000.0,
        )
        assert result is False

    def test_stagnation_triggers_plan(self, reconfig):
        plan = reconfig.check_and_plan(
            squad_id="s-1",
            last_progress_ms=12_000.0,
            stagnation_threshold_ms=10_000.0,
        )
        assert plan is not None
        assert plan.trigger == ReconfigTrigger.STAGNATION

    def test_recommend_dissolve_for_high_failure(self, reconfig):
        plan = reconfig.check_and_plan(
            squad_id="s-1",
            last_progress_ms=15_000.0,
            stagnation_threshold_ms=10_000.0,
            failure_rate=0.85,
        )
        assert plan is not None
        assert plan.action == ReconfigAction.DISSOLVE

    def test_recommend_reassign_for_moderate_failure(self, reconfig):
        plan = reconfig.check_and_plan(
            squad_id="s-1",
            last_progress_ms=12_000.0,
            stagnation_threshold_ms=10_000.0,
            failure_rate=0.5,
        )
        assert plan is not None
        assert plan.action == ReconfigAction.REASSIGN_LEADER

    def test_no_plan_when_progressing(self, reconfig):
        plan = reconfig.check_and_plan(
            squad_id="s-1",
            last_progress_ms=2_000.0,
            stagnation_threshold_ms=10_000.0,
        )
        assert plan is None


class TestBanditMetrics:
    def test_bandit_creation(self):
        bm = BanditMetrics(squad_id="s-1", arm="add_worker", reward=0.75)
        assert bm.squad_id == "s-1"
        assert bm.arm == "add_worker"
        assert bm.reward == 0.75
        assert bm.trials == 1

    def test_bandit_update(self):
        bm = BanditMetrics(squad_id="s-1", arm="add_worker", reward=0.5)
        updated = bm.update(new_reward=0.8)
        assert updated.trials == 2
        assert pytest.approx(updated.reward) == 0.65

    def test_select_best_arm(self, reconfig):
        reconfig.record_bandit("s-1", "add_worker", 0.7)
        reconfig.record_bandit("s-1", "reassign_lead", 0.9)
        reconfig.record_bandit("s-1", "dissolve", 0.3)
        best = reconfig.select_best_arm("s-1")
        assert best == "reassign_lead"

    def test_select_best_arm_no_data(self, reconfig):
        best = reconfig.select_best_arm("unknown-squad")
        assert best is None


class TestDynamicReconfigLoadBalancing:
    def test_detect_load_imbalance(self, reconfig):
        squad_loads = {"s-1": 0.9, "s-2": 0.2, "s-3": 0.85}
        imbalanced = reconfig.detect_load_imbalance(
            squad_loads, imbalance_threshold=0.3
        )
        assert imbalanced is True

    def test_no_imbalance_within_threshold(self, reconfig):
        squad_loads = {"s-1": 0.6, "s-2": 0.5, "s-3": 0.55}
        imbalanced = reconfig.detect_load_imbalance(
            squad_loads, imbalance_threshold=0.3
        )
        assert imbalanced is False

    def test_generate_rebalance_plan(self, reconfig):
        squad_loads = {"s-1": 0.9, "s-2": 0.2}
        plan = reconfig.generate_rebalance_plan(squad_loads)
        assert plan is not None
        assert plan.trigger == ReconfigTrigger.LOAD_IMBALANCE


# ── TestHealthMonitor ─────────────────────────────────────────


class TestHealthProbe:
    def test_probe_creation(self):
        probe = HealthProbe(
            agent_id="agent-1",
            status=HealthStatus.HEALTHY,
            latency_ms=5.0,
        )
        assert probe.status == HealthStatus.HEALTHY
        assert probe.latency_ms == 5.0

    def test_probe_immutability(self):
        probe = HealthProbe(
            agent_id="agent-1",
            status=HealthStatus.HEALTHY,
            latency_ms=5.0,
        )
        with pytest.raises(Exception):
            probe.status = HealthStatus.DEGRADED

    def test_probe_defaults(self):
        probe = HealthProbe(agent_id="agent-1")
        assert probe.status == HealthStatus.HEALTHY
        assert probe.latency_ms == 0.0

    def test_probe_with_error(self):
        probe = HealthProbe(
            agent_id="agent-2",
            status=HealthStatus.UNHEALTHY,
            error="Connection refused",
        )
        assert probe.error == "Connection refused"


class TestAgentHealth:
    def test_agent_health_creation(self):
        ah = AgentHealth(agent_id="agent-1")
        assert ah.agent_id == "agent-1"
        assert ah.status == HealthStatus.HEALTHY
        assert ah.consecutive_failures == 0

    def test_agent_health_record_probe(self):
        ah = AgentHealth(agent_id="agent-1")
        ah.record_probe(HealthStatus.HEALTHY, latency_ms=10.0)
        assert ah.last_heartbeat > 0
        assert ah.consecutive_failures == 0

    def test_agent_health_degradation(self):
        ah = AgentHealth(agent_id="agent-1")
        for _ in range(3):
            ah.record_probe(HealthStatus.UNHEALTHY, error="timeout")
        assert ah.status == HealthStatus.UNHEALTHY
        assert ah.consecutive_failures == 3

    def test_agent_health_recovery(self):
        ah = AgentHealth(agent_id="agent-1")
        ah.record_probe(HealthStatus.UNHEALTHY, error="timeout")
        ah.record_probe(HealthStatus.HEALTHY, latency_ms=5.0)
        assert ah.status == HealthStatus.HEALTHY
        assert ah.consecutive_failures == 0

    def test_agent_health_dead_after_max_failures(self):
        ah = AgentHealth(agent_id="agent-1", max_consecutive_failures=3)
        for _ in range(4):
            ah.record_probe(HealthStatus.UNHEALTHY, error="crash")
        assert ah.status == HealthStatus.DEAD


class TestHealthMonitorBasic:
    def test_register_agent(self, health_monitor):
        health_monitor.register_agent("agent-1")
        health = health_monitor.get_health("agent-1")
        assert health is not None
        assert health.agent_id == "agent-1"

    def test_register_duplicate_agent(self, health_monitor):
        health_monitor.register_agent("agent-1")
        with pytest.raises(ValueError, match="already registered"):
            health_monitor.register_agent("agent-1")

    def test_unregister_agent(self, health_monitor):
        health_monitor.register_agent("agent-1")
        health_monitor.unregister_agent("agent-1")
        assert health_monitor.get_health("agent-1") is None

    def test_get_health_missing(self, health_monitor):
        assert health_monitor.get_health("nonexistent") is None

    def test_record_heartbeat(self, health_monitor):
        health_monitor.register_agent("agent-1")
        health_monitor.record_heartbeat("agent-1", latency_ms=5.0)
        health = health_monitor.get_health("agent-1")
        assert health.last_heartbeat > 0

    def test_record_heartbeat_missing(self, health_monitor):
        with pytest.raises(ValueError, match="not registered"):
            health_monitor.record_heartbeat("unknown")

    def test_agent_count(self, health_monitor):
        health_monitor.register_agent("a1")
        health_monitor.register_agent("a2")
        health_monitor.register_agent("a3")
        assert health_monitor.agent_count == 3


class TestHealthMonitorStatus:
    def test_get_status_summary(self, health_monitor):
        health_monitor.register_agent("a1")
        health_monitor.register_agent("a2")
        health_monitor.record_heartbeat("a1", latency_ms=5.0)
        summary = health_monitor.get_status_summary()
        assert summary["total"] == 2
        assert "healthy" in summary

    def test_degraded_agents(self, health_monitor):
        health_monitor.register_agent("a1")
        health_monitor.register_agent("a2")
        for _ in range(3):
            health_monitor.record_heartbeat(
                "a1", status=HealthStatus.UNHEALTHY, error="oom"
            )
        degraded = health_monitor.get_degraded_agents()
        assert "a1" in degraded

    def test_check_heartbeat_timeout(self, health_monitor):
        health_monitor.register_agent("a1")
        health_monitor.record_heartbeat("a1", latency_ms=5.0)
        time.sleep(0.002)
        timed_out = health_monitor.check_heartbeat_timeout(
            timeout_ms=0.001
        )
        assert "a1" in timed_out

    def test_squad_health_aggregate(self, health_monitor):
        health_monitor.register_agent("captain", squad_id="s-1")
        health_monitor.register_agent("worker1", squad_id="s-1")
        health_monitor.register_agent("worker2", squad_id="s-1")
        health_monitor.record_heartbeat("captain", latency_ms=5.0)
        health_monitor.record_heartbeat("worker1", latency_ms=8.0)
        health_monitor.record_heartbeat("worker2", latency_ms=12.0)

        squad_health = health_monitor.get_squad_health("s-1")
        assert squad_health is not None
        assert squad_health["agent_count"] == 3
        assert squad_health["healthy_count"] == 3

    def test_squad_health_mixed(self, health_monitor):
        health_monitor.register_agent("a1", squad_id="s-1")
        health_monitor.register_agent("a2", squad_id="s-1")
        health_monitor.record_heartbeat("a1", latency_ms=5.0)
        for _ in range(3):
            health_monitor.record_heartbeat(
                "a2", status=HealthStatus.UNHEALTHY, error="crash"
            )
        squad_health = health_monitor.get_squad_health("s-1")
        assert squad_health["healthy_count"] == 1
        assert len(squad_health["degraded_agents"]) == 1

    def test_get_redundancy_recommendation(self, health_monitor):
        health_monitor.register_agent("a1", squad_id="s-1")
        health_monitor.register_agent("a2", squad_id="s-1")
        for _ in range(4):
            health_monitor.record_heartbeat(
                "a2", status=HealthStatus.UNHEALTHY, error="flaky"
            )
        rec = health_monitor.get_redundancy_recommendation("s-1")
        assert rec is not None
        assert rec["action"] == "add_redundancy"
