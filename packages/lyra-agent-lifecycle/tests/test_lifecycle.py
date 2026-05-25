"""Comprehensive tests for lyra-agent-lifecycle package."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra_agent_lifecycle import (
    AgentAlreadyRetiredError,
    AgentFactory,
    AgentLifecycleManager,
    AgentNotReadyError,
    AgentRecord,
    AgentRetirement,
    AgentSpawner,
    CapabilityProfile,
    EvolutionTracker,
    HealthCheck,
    HealthCheckFailedError,
    HealthCheckResult,
    InvalidTransitionError,
    KnowledgeExtractor,
    LifecycleError,
    LifecycleEvent,
    LifecycleHooks,
    LifecycleState,
    PerformanceSnapshot,
    ResourceAllocationError,
    RetirementConfig,
    SpawnConfig,
    SpawnError,
    StatePreserver,
    WarmupTimeoutError,
)


# ============================================================================
# Lifecycle state machine tests
# ============================================================================


class TestLifecycleStateMachine:
    @pytest.fixture
    def mgr(self) -> AgentLifecycleManager:
        return AgentLifecycleManager()

    def test_register_agent(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        assert mgr.get_state("agent-1") == LifecycleState.INIT

    def test_duplicate_register_raises(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        with pytest.raises(LifecycleError, match="already registered"):
            mgr.register_agent("agent-1")

    async def test_init_to_ready(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.mark_ready("agent-1")
        assert mgr.get_state("agent-1") == LifecycleState.READY

    async def test_ready_to_active(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.mark_ready("agent-1")
        await mgr.activate("agent-1")
        assert mgr.get_state("agent-1") == LifecycleState.ACTIVE

    async def test_active_to_paused(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.mark_ready("agent-1")
        await mgr.activate("agent-1")
        await mgr.pause("agent-1")
        assert mgr.get_state("agent-1") == LifecycleState.PAUSED

    async def test_paused_resume(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.mark_ready("agent-1")
        await mgr.activate("agent-1")
        await mgr.pause("agent-1")
        await mgr.resume("agent-1")
        assert mgr.get_state("agent-1") == LifecycleState.ACTIVE

    async def test_retire(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.mark_ready("agent-1")
        await mgr.activate("agent-1")
        await mgr.transition("agent-1", LifecycleState.RETIRED, reason="done")
        assert mgr.get_state("agent-1") == LifecycleState.RETIRED

    async def test_retired_cannot_transition(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.transition("agent-1", LifecycleState.RETIRED, reason="test")
        with pytest.raises(InvalidTransitionError):
            await mgr.transition("agent-1", LifecycleState.ACTIVE)

    async def test_can_transition(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        assert mgr.can_transition("agent-1", LifecycleState.READY)
        assert mgr.can_transition("agent-1", LifecycleState.RETIRED)
        assert not mgr.can_transition("agent-1", LifecycleState.ACTIVE)

    async def test_history(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.mark_ready("agent-1")
        await mgr.activate("agent-1")
        await mgr.pause("agent-1")
        history = mgr.get_history("agent-1")
        assert len(history) >= 3
        assert isinstance(history[0], LifecycleEvent)

    def test_get_agents_by_state(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("a")
        mgr.register_agent("b")
        mgr.register_agent("c")
        asyncio.run(mgr.mark_ready("a"))
        asyncio.run(mgr.mark_ready("b"))
        ready = mgr.get_agents_by_state(LifecycleState.READY)
        assert "a" in ready
        assert "b" in ready
        assert "c" not in ready

    async def test_hooks_fire(self, mgr: AgentLifecycleManager) -> None:
        events: list[str] = []

        async def on_ready(aid: str) -> None:
            events.append("ready")

        async def on_activate(aid: str) -> None:
            events.append("activate")

        hooks = LifecycleHooks(on_ready=on_ready, on_activate=on_activate)
        mgr.register_agent("hook-test", hooks=hooks)
        await mgr.mark_ready("hook-test")
        await mgr.activate("hook-test")
        assert "ready" in events
        assert "activate" in events

    def test_stats(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("a")
        mgr.register_agent("b")
        asyncio.run(mgr.mark_ready("a"))
        asyncio.run(mgr.mark_ready("b"))
        asyncio.run(mgr.activate("a"))
        stats = mgr.stats
        assert stats["total"] == 2
        assert "READY" in stats["by_state"]
        assert "ACTIVE" in stats["by_state"]


# ============================================================================
# Shutdown and versioning tests
# ============================================================================


class TestShutdownAndVersioning:
    @pytest.fixture
    def mgr(self) -> AgentLifecycleManager:
        return AgentLifecycleManager(default_shutdown_timeout=5.0)

    async def test_graceful_shutdown(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1")
        await mgr.mark_ready("agent-1")
        await mgr.activate("agent-1")
        result = await mgr.graceful_shutdown("agent-1", timeout=2.0)
        assert result
        assert mgr.get_state("agent-1") == LifecycleState.RETIRED

    async def test_shutdown_all(self, mgr: AgentLifecycleManager) -> None:
        for i in range(3):
            aid = f"agent-{i}"
            mgr.register_agent(aid)
            await mgr.mark_ready(aid)
        results = await mgr.shutdown_all(timeout=2.0)
        assert len(results) == 3
        assert all(results.values())

    async def test_upgrade_agent(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1", version="1.0.0")
        await mgr.mark_ready("agent-1")
        assert await mgr.upgrade_agent("agent-1", "2.0.0")
        assert mgr.get_version("agent-1") == "2.0.0"

    async def test_upgrade_requires_ready(self, mgr: AgentLifecycleManager) -> None:
        mgr.register_agent("agent-1", version="1.0.0")
        await mgr.mark_ready("agent-1")
        await mgr.activate("agent-1")
        with pytest.raises(InvalidTransitionError):
            await mgr.upgrade_agent("agent-1", "2.0.0", require_ready=True)

    async def test_upgrade_hooks(self, mgr: AgentLifecycleManager) -> None:
        upgrades: list[tuple[str, str, str]] = []

        async def on_upgrade(aid: str, old: str, new: str) -> None:
            upgrades.append((aid, old, new))

        hooks = LifecycleHooks(on_upgrade=on_upgrade)
        mgr.register_agent("agent-1", hooks=hooks, version="1.0.0")
        await mgr.mark_ready("agent-1")
        await mgr.upgrade_agent("agent-1", "3.0.0")
        assert len(upgrades) == 1
        assert upgrades[0] == ("agent-1", "1.0.0", "3.0.0")

    async def test_error_hooks(self, mgr: AgentLifecycleManager) -> None:
        errors: list[str] = []

        async def on_error(aid: str, error: Exception) -> None:
            errors.append(str(error))

        hooks = LifecycleHooks(on_error=on_error)
        mgr.register_agent("agent-1", hooks=hooks)
        await mgr.mark_ready("agent-1")
        await mgr.mark_error("agent-1", ValueError("test error"))
        assert len(errors) == 1


# ============================================================================
# Spawner tests
# ============================================================================


class TestAgentSpawner:
    @pytest.fixture
    def lifecycle(self) -> AgentLifecycleManager:
        return AgentLifecycleManager()

    @pytest.fixture
    def spawner(self, lifecycle: AgentLifecycleManager) -> AgentSpawner:
        hc = HealthCheck()

        async def dummy_check(agent_id: str) -> bool:
            return True

        hc.register_check("always_pass", dummy_check)

        factory = AgentFactory()

        async def build_worker(config: SpawnConfig) -> str:
            return f"worker-{id(config)}"

        factory.register_constructor("worker", build_worker)
        factory.register_template("default-worker", SpawnConfig(agent_type="worker", capabilities=["general"]))

        return AgentSpawner(lifecycle, health_check=hc, factory=factory)

    async def test_spawn_agent(self, spawner: AgentSpawner) -> None:
        config = SpawnConfig(agent_type="worker", capabilities=["general"], warmup_timeout=5.0)
        record = await spawner.spawn(config)
        assert record.agent_id
        assert spawner._lifecycle.get_state(record.agent_id) == LifecycleState.ACTIVE

    async def test_spawn_from_template(self, spawner: AgentSpawner) -> None:
        record = await spawner.spawn_from_template("default-worker")
        assert record.agent_id
        assert spawner._lifecycle.get_state(record.agent_id) == LifecycleState.ACTIVE

    async def test_spawn_invalid_template(self, spawner: AgentSpawner) -> None:
        with pytest.raises(SpawnError, match="Template not found"):
            await spawner.spawn_from_template("nonexistent")

    async def test_health_check_failure(self, spawner: AgentSpawner) -> None:
        hc = HealthCheck()

        async def fail_check(agent_id: str) -> bool:
            return False

        hc.register_check("always_fail", fail_check)
        spawner._health_check = hc

        config = SpawnConfig(agent_type="worker", capabilities=["general"], warmup_timeout=5.0, max_retries=0)
        with pytest.raises(SpawnError):
            await spawner.spawn(config)

    def test_spawn_config_validation(self) -> None:
        with pytest.raises(SpawnError):
            SpawnConfig(capabilities=[])
        with pytest.raises(SpawnError):
            SpawnConfig(warmup_timeout=0)

    def test_health_check_result(self) -> None:
        result = HealthCheckResult(passed=True, agent_id="test", checks={"a": True, "b": False})
        assert result.passed_count == 1
        assert result.total_checks == 2

    def test_resource_allocation(self, spawner: AgentSpawner) -> None:
        limits = {"cpu": 1.0, "memory": 512}
        result = asyncio.run(spawner._pre_allocate("test-agent", limits))
        assert result
        assert spawner.get_allocated_resources("test-agent") == limits
        spawner._release_resources("test-agent")
        assert spawner.get_allocated_resources("test-agent") == {}

    async def test_warmup_timeout(self, spawner: AgentSpawner) -> None:
        async def slow_warmup(agent_id: str) -> None:
            await asyncio.sleep(2.0)

        spawner.register_warmup("worker", slow_warmup)
        config = SpawnConfig(agent_type="worker", capabilities=["general"], warmup_timeout=0.01, max_retries=0)
        with pytest.raises(SpawnError):
            await spawner.spawn(config)

    async def test_ad_hoc_health_check(self, spawner: AgentSpawner) -> None:
        config = SpawnConfig(agent_type="worker", capabilities=["general"], warmup_timeout=5.0)
        record = await spawner.spawn(config)
        result = await spawner.health_check_now(record.agent_id)
        assert result.passed


# ============================================================================
# Retirement tests
# ============================================================================


class TestAgentRetirement:
    @pytest.fixture
    def lifecycle(self) -> AgentLifecycleManager:
        return AgentLifecycleManager()

    @pytest.fixture
    def retirement(self, lifecycle: AgentLifecycleManager) -> AgentRetirement:
        ke = KnowledgeExtractor()

        async def extract_caps(agent_id: str) -> dict:
            return {"capabilities": ["nlp", "code"], "score": 0.9}

        ke.register_extractor("capabilities", extract_caps)
        sp = StatePreserver()
        return AgentRetirement(lifecycle, knowledge_extractor=ke, state_preserver=sp)

    async def test_retire_agent(self, retirement: AgentRetirement) -> None:
        aid = "agent-to-retire"
        retirement._lifecycle.register_agent(aid)
        await retirement._lifecycle.mark_ready(aid)
        await retirement._lifecycle.activate(aid)
        entry = await retirement.retire(aid, reason="testing")
        assert entry.agent_id == aid
        assert entry.knowledge_extracted
        assert entry.state_preserved
        assert retirement._lifecycle.get_state(aid) == LifecycleState.RETIRED

    async def test_retire_already_retired(self, retirement: AgentRetirement) -> None:
        aid = "pre-retired"
        retirement._lifecycle.register_agent(aid)
        await retirement._lifecycle.transition(aid, LifecycleState.RETIRED, reason="pre")
        with pytest.raises(AgentAlreadyRetiredError):
            await retirement.retire(aid)

    async def test_retire_without_extraction(self, retirement: AgentRetirement) -> None:
        aid = "agent-no-extract"
        retirement._lifecycle.register_agent(aid)
        await retirement._lifecycle.mark_ready(aid)
        config = RetirementConfig(extract_knowledge=False, preserve_state=False)
        entry = await retirement.retire(aid, config=config, reason="quick")
        assert not entry.knowledge_extracted

    async def test_handoff(self, retirement: AgentRetirement) -> None:
        from_aid = "old-agent"
        to_aid = "new-agent"
        await retirement._state_preserver.save_state(from_aid, {"data": "important"}, label="pre")
        retirement._lifecycle.register_agent(from_aid)
        await retirement._lifecycle.mark_ready(from_aid)
        config = RetirementConfig(handoff_target=to_aid, preserve_state=True)
        entry = await retirement.retire(from_aid, config=config, reason="replaced")
        assert entry.handoff_completed

    def test_audit_log(self, retirement: AgentRetirement) -> None:
        aid = "audit-agent"
        retirement._lifecycle.register_agent(aid)
        asyncio.run(retirement._lifecycle.mark_ready(aid))
        asyncio.run(retirement.retire(aid, reason="audit-test"))
        log = retirement.get_audit_log(agent_id=aid)
        assert len(log) >= 1
        assert log[0].reason == "audit-test"

    def test_knowledge_transfer(self, retirement: AgentRetirement) -> None:
        ke = retirement._knowledge_extractor
        asyncio.run(ke.extract("src"))
        bundles = ke.transfer_knowledge("src", "dst")
        assert len(bundles) >= 1
        assert len(ke.get_knowledge("dst")) >= 1
        assert len(ke.get_knowledge("src")) == 0

    def test_state_preserver(self) -> None:
        sp = StatePreserver()

        async def save() -> str:
            return await sp.save_state("agent-x", {"key": "value"}, label="test")

        sid = asyncio.run(save())
        assert sid
        state = sp.get_latest_state("agent-x")
        assert state is not None
        assert state["state"]["key"] == "value"

        handed = sp.handoff_state("agent-x", "agent-y")
        assert handed is not None
        assert handed["agent_id"] == "agent-y"
        assert sp.get_latest_state("agent-x") is None

    def test_state_history_pruning(self) -> None:
        sp = StatePreserver(max_snapshots_per_agent=3)

        async def save_batch() -> None:
            for i in range(10):
                await sp.save_state("agent-x", {"i": i}, label=f"snap-{i}")

        asyncio.run(save_batch())
        history = sp.get_state_history("agent-x")
        assert len(history) == 3

    def test_state_cleanup(self) -> None:
        sp = StatePreserver()
        asyncio.run(sp.save_state("agent-x", {"data": "test"}, label="cleanup"))
        sp.cleanup_state("agent-x")
        assert sp.get_latest_state("agent-x") is None


# ============================================================================
# Evolution tracker tests
# ============================================================================


class TestEvolutionTracker:
    @pytest.fixture
    def tracker(self) -> EvolutionTracker:
        return EvolutionTracker(snapshot_interval=60.0, extinction_threshold=0.2)

    def test_register_and_record(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("agent-1", ["nlp", "code"])
        tracker.record_task("agent-1", success=True, latency_ms=100, quality=0.9)
        tracker.record_task("agent-1", success=True, latency_ms=150, quality=0.8)
        perf = tracker.get_performance("agent-1")
        assert perf["task_count"] == 2
        assert perf["success_rate"] == 1.0
        assert perf["avg_latency_ms"] > 0

    def test_capability_profile(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("agent-1", ["python"])
        profile = tracker.get_capability_profile("agent-1")
        assert profile is not None
        assert profile.capabilities == ["python"]
        tracker.evolve_capabilities("agent-1", added=["rust", "go"], removed=["python"])
        profile = tracker.get_capability_profile("agent-1")
        assert "rust" in profile.capabilities
        assert "python" not in profile.capabilities

    def test_capability_metrics(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("agent-1", ["nlp", "search", "code"])
        tracker.evolve_capabilities("agent-1", added=["vision"])
        metrics = tracker.get_capability_evolution_metrics("agent-1")
        assert metrics["total_capabilities"] == 4

    def test_snapshot(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("agent-1", ["general"])
        tracker.record_task("agent-1", success=True, latency_ms=50, quality=0.7)
        tracker.record_task("agent-1", success=False, latency_ms=200, quality=0.3)
        snap = tracker.take_snapshot("agent-1")
        assert snap.task_count == 2
        assert snap.success_rate == 0.5
        assert isinstance(snap, PerformanceSnapshot)

    def test_breeding_intersection(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("parent-1", ["nlp", "code", "search"])
        tracker.register_agent("parent-2", ["code", "search", "vision"])
        child_id = tracker.breed(["parent-1", "parent-2"], combination_strategy="intersection")
        child = tracker.get_capability_profile(child_id)
        assert child is not None
        assert "code" in child.capabilities
        assert "search" in child.capabilities
        assert "nlp" not in child.capabilities

    def test_breeding_union(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("p1", ["a", "b"])
        tracker.register_agent("p2", ["c", "d"])
        child_id = tracker.breed(["p1", "p2"], combination_strategy="union")
        child = tracker.get_capability_profile(child_id)
        assert child is not None
        assert len(child.capabilities) == 4

    def test_lineage(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("adam", ["general"])
        tracker.breed(["adam", "adam"], child_id="eve", combination_strategy="union")
        lineage = tracker.get_lineage("adam")
        assert lineage is not None
        assert "eve" in lineage.members
        assert lineage.generations >= 2

    def test_underperformer_detection(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("good", ["general"])
        tracker.register_agent("bad", ["general"])
        for _ in range(15):
            tracker.record_task("good", success=True, quality=0.9)
            tracker.record_task("bad", success=False, quality=0.05)
        for _ in range(5):
            tracker.take_snapshot("good")
            tracker.take_snapshot("bad")
        underperformers = tracker.identify_underperformers(threshold=0.2, min_tasks=10)
        assert "bad" in underperformers
        assert "good" not in underperformers

    def test_mark_extinct(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("doomed", ["legacy"])
        tracker.record_task("doomed", success=False, quality=0.01)
        record = tracker.mark_extinct("doomed", reason="obsolete")
        assert tracker.is_extinct("doomed")
        assert record["reason"] == "obsolete"

    def test_fitness_landscape(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("a", ["x"])
        tracker.register_agent("b", ["y"])
        tracker.register_agent("c", ["z"])
        tracker.record_task("a", success=True, quality=0.9)
        tracker.record_task("b", success=False, quality=0.4)
        tracker.record_task("c", success=True, quality=0.7)
        landscape = tracker.get_fitness_landscape()
        assert landscape["active_agents"] == 3
        assert landscape["avg_success_rate"] == pytest.approx(2.0 / 3.0)
        assert landscape["best_agent"] == "a"

    def test_capability_properties(self) -> None:
        profile = CapabilityProfile(agent_id="test")
        profile.add_capability("skill-a", proficiency=0.8)
        profile.add_capability("skill-b", proficiency=0.6)
        assert profile.breadth == 2
        assert profile.avg_proficiency == 0.7

    def test_record_task_pruning(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("busy", ["general"])
        for i in range(1000):
            tracker.record_task("busy", success=True, latency_ms=10, quality=0.5)
        perf = tracker.get_performance("busy")
        assert perf["task_count"] == 1000

    def test_evolution_snapshot(self, tracker: EvolutionTracker) -> None:
        tracker.register_agent("evolver", ["general"])
        tracker.record_task("evolver", success=True, quality=0.8)
        snap = tracker.snapshot()
        assert snap["tracked_agents"] >= 1


# ============================================================================
# Integration tests
# ============================================================================


class TestLifecycleIntegration:
    async def test_full_spawn_to_retirement_cycle(self) -> None:
        lm = AgentLifecycleManager()
        hc = HealthCheck()

        async def always_ok(agent_id: str) -> bool:
            return True

        hc.register_check("ok", always_ok)

        factory = AgentFactory()

        async def make_agent(config: SpawnConfig) -> str:
            return f"integrated-{id(config)}"

        factory.register_constructor("test", make_agent)
        factory.register_template("test-template", SpawnConfig(agent_type="test", capabilities=["general"]))

        spawner = AgentSpawner(lm, health_check=hc, factory=factory)
        ke = KnowledgeExtractor()
        sp = StatePreserver()
        retirement = AgentRetirement(lm, knowledge_extractor=ke, state_preserver=sp)
        tracker = EvolutionTracker()

        # Spawn
        record = await spawner.spawn(SpawnConfig(agent_type="test", capabilities=["general"], warmup_timeout=5.0))
        aid = record.agent_id
        assert lm.get_state(aid) == LifecycleState.ACTIVE

        # Track
        tracker.register_agent(aid, ["general"])
        tracker.record_task(aid, success=True, quality=0.9)

        # Pause
        await lm.pause(aid)
        assert lm.get_state(aid) == LifecycleState.PAUSED

        # Retire
        await sp.save_state(aid, {"legacy": "data"})
        entry = await retirement.retire(aid, reason="end-to-end-test")
        assert lm.get_state(aid) == LifecycleState.RETIRED
        assert entry.knowledge_extracted

    async def test_1000_agents_simulation(self) -> None:
        lm = AgentLifecycleManager()
        tracker = EvolutionTracker()

        for i in range(1000):
            aid = f"sim-agent-{i}"
            lm.register_agent(aid)
            tracker.register_agent(aid, [f"skill-{i % 10}"])

        assert lm.stats["total"] == 1000
        landscape = tracker.get_fitness_landscape()
        assert landscape["active_agents"] == 1000

        # Retire all in parallel
        tasks = [lm.transition(f"sim-agent-{i}", LifecycleState.RETIRED, reason="sim-end") for i in range(1000)]
        await asyncio.gather(*tasks)

        retired = lm.get_agents_by_state(LifecycleState.RETIRED)
        assert len(retired) == 1000
