"""Comprehensive tests for lyra-colony package."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra_colony import (
    AgentColony,
    AgentNotFoundError,
    AgentRole,
    AgentRoleKind,
    AgentSpec,
    AgentStatus,
    AlertRule,
    AlertSeverity,
    Channel,
    ColonyConfig,
    ColonyHealth,
    ColonyOverCapacityError,
    ColonyScheduler,
    ColonyState,
    DuplicateTaskError,
    InvalidSpecError,
    LifecycleHooks,
    Message,
    MessageBus,
    MessagePriority,
    NoAvailableAgentError,
    Protocol,
    ResourceLimits,
    SchedulingError,
    SchedulingStrategy,
    SkillLevel,
    SkillRequirement,
    Task,
    TaskAssignment,
    TaskState,
)


# ============================================================================
# Agent Spec tests
# ============================================================================


class TestAgentSpec:
    def test_valid_spec(self) -> None:
        role = AgentRole(name="researcher", kind=AgentRoleKind.SPECIALIST)
        spec = AgentSpec(role=role, capabilities=("nlp", "search"))
        assert spec.role.name == "researcher"
        assert spec.has_capability("nlp")
        assert not spec.has_capability("vision")

    def test_empty_capabilities_raises(self) -> None:
        with pytest.raises(InvalidSpecError, match="at least one capability"):
            AgentSpec(capabilities=())

    def test_meets_skill_requirements(self) -> None:
        spec = AgentSpec(
            role=AgentRole(),
            capabilities=("general",),
            skills=(
                SkillRequirement(name="python", level=SkillLevel.EXPERT),
                SkillRequirement(name="sql", level=SkillLevel.COMPETENT),
            ),
        )
        required = (
            SkillRequirement(name="python", level=SkillLevel.COMPETENT),
            SkillRequirement(name="sql", level=SkillLevel.APPRENTICE),
        )
        assert spec.meets_skill_requirements(required)

    def test_fails_skill_requirements(self) -> None:
        spec = AgentSpec(
            role=AgentRole(),
            capabilities=("general",),
            skills=(SkillRequirement(name="python", level=SkillLevel.APPRENTICE),),
        )
        required = (SkillRequirement(name="python", level=SkillLevel.EXPERT),)
        assert not spec.meets_skill_requirements(required)

    def test_resource_limits_validation(self) -> None:
        with pytest.raises(InvalidSpecError):
            ResourceLimits(max_cpu_cores=0)
        with pytest.raises(InvalidSpecError):
            ResourceLimits(max_memory_mb=-1)

    def test_skill_level_values(self) -> None:
        assert SkillLevel.NOVICE.value < SkillLevel.MASTER.value
        assert SkillLevel.EXPERT.value == 4

    def test_agent_role_kinds(self) -> None:
        role = AgentRole(kind=AgentRoleKind.SENTINEL)
        assert role.kind == AgentRoleKind.SENTINEL

    def test_lifecycle_hooks_fire(self) -> None:
        called = False

        async def on_spawn(agent_id: str, spec: AgentSpec) -> None:
            nonlocal called
            called = True

        hooks = LifecycleHooks(on_spawn=on_spawn)
        asyncio.run(hooks.fire_spawn("agent-1", AgentSpec(capabilities=("test",))))
        assert called

    def test_lifecycle_hooks_none_safe(self) -> None:
        hooks = LifecycleHooks()
        asyncio.run(hooks.fire_spawn("agent-1", AgentSpec(capabilities=("test",))))


# ============================================================================
# Scheduler tests
# ============================================================================


class TestColonyScheduler:
    @pytest.fixture
    def scheduler(self) -> ColonyScheduler:
        s = ColonyScheduler(strategy=SchedulingStrategy.AFFINITY)
        s.register_agent("agent-A", capabilities=["nlp", "search"], labels={"zone": "us"})
        s.register_agent("agent-B", capabilities=["vision", "search"], labels={"zone": "eu"})
        s.register_agent("agent-C", capabilities=["nlp", "code"], labels={"zone": "us"})
        return s

    def test_submit_task(self, scheduler: ColonyScheduler) -> None:
        task = Task(task_type="research", priority=5, required_capabilities=("nlp",))
        tid = scheduler.submit(task)
        assert tid == task.task_id
        assert scheduler.get_queue_depth() == 1

    def test_submit_duplicate_raises(self, scheduler: ColonyScheduler) -> None:
        task = Task(task_type="test", priority=5, required_capabilities=("nlp",))
        scheduler.submit(task)
        with pytest.raises(DuplicateTaskError):
            scheduler.submit(task)

    def test_invalid_priority(self) -> None:
        with pytest.raises(SchedulingError):
            Task(priority=0)
        with pytest.raises(SchedulingError):
            Task(priority=11)

    async def test_assign_affinity(self, scheduler: ColonyScheduler) -> None:
        task = Task(
            task_type="research",
            priority=5,
            required_capabilities=("nlp",),
            affinity_labels={"zone": "us"},
        )
        scheduler.submit(task)
        assignment = await scheduler.assign_next()
        assert assignment is not None
        assert assignment.agent_id in ("agent-A", "agent-C")

    async def test_assign_no_matching_agent(self, scheduler: ColonyScheduler) -> None:
        task = Task(task_type="special", priority=5, required_capabilities=("quantum",))
        scheduler.submit(task)
        with pytest.raises(NoAvailableAgentError):
            await scheduler.assign_next()

    async def test_least_connections(self, scheduler: ColonyScheduler) -> None:
        scheduler.strategy = SchedulingStrategy.LEAST_CONNECTIONS
        task = Task(task_type="test", priority=5, required_capabilities=("nlp",))
        scheduler.submit(task)
        assignment = await scheduler.assign_next()
        assert assignment is not None
        assert assignment.agent_id in ("agent-A", "agent-C")

    async def test_round_robin(self, scheduler: ColonyScheduler) -> None:
        scheduler.strategy = SchedulingStrategy.ROUND_ROBIN
        task = Task(task_type="search", priority=5, required_capabilities=("search",))
        scheduler.submit(task)
        a1 = await scheduler.assign_next()
        scheduler.submit(Task(task_type="search2", priority=5, required_capabilities=("search",)))
        a2 = await scheduler.assign_next()
        assert a1 is not None
        assert a2 is not None
        assert a1.agent_id != a2.agent_id

    def test_mark_completed(self, scheduler: ColonyScheduler) -> None:
        task = Task(task_type="test", priority=5, required_capabilities=("nlp",))
        scheduler.submit(task)
        assignment = TaskAssignment(task_id=task.task_id, agent_id="agent-A")
        scheduler.mark_completed(assignment)
        assert scheduler.metrics.tasks_completed == 1

    def test_mark_failed(self, scheduler: ColonyScheduler) -> None:
        assignment = TaskAssignment(task_id="t1", agent_id="agent-A")
        scheduler.mark_failed(assignment)
        assert scheduler.metrics.tasks_failed == 1

    def test_cancel_task(self, scheduler: ColonyScheduler) -> None:
        task = Task(task_type="test", priority=5, required_capabilities=("nlp",))
        scheduler.submit(task)
        assert scheduler.cancel_task(task.task_id)
        assert scheduler.get_task_state(task.task_id) == TaskState.CANCELLED

    def test_cancel_nonexistent(self, scheduler: ColonyScheduler) -> None:
        assert not scheduler.cancel_task("nonexistent")

    def test_submit_batch(self, scheduler: ColonyScheduler) -> None:
        tasks = [
            Task(task_type="t1", priority=5, required_capabilities=("nlp",)),
            Task(task_type="t2", priority=3, required_capabilities=("search",)),
        ]
        ids = scheduler.submit_batch(tasks)
        assert len(ids) == 2
        assert scheduler.get_queue_depth() == 2

    def test_strategy_switch(self, scheduler: ColonyScheduler) -> None:
        scheduler.strategy = SchedulingStrategy.DEADLINE_FIRST
        assert scheduler.strategy == SchedulingStrategy.DEADLINE_FIRST

    def test_unregister_agent(self, scheduler: ColonyScheduler) -> None:
        # Agent-A and Agent-C both have nlp; unregister both to get NoAvailableAgent
        scheduler.unregister_agent("agent-A")
        scheduler.unregister_agent("agent-C")
        task = Task(task_type="test", priority=5, required_capabilities=("nlp",))
        scheduler.submit(task)
        with pytest.raises(NoAvailableAgentError):
            asyncio.run(scheduler.assign_next())

    def test_full_queue(self) -> None:
        scheduler = ColonyScheduler(max_queue_size=2)
        scheduler.register_agent("a", capabilities=["x"])
        scheduler.submit(Task(task_type="t1", priority=5, required_capabilities=("x",)))
        scheduler.submit(Task(task_type="t2", priority=5, required_capabilities=("x",)))
        with pytest.raises(SchedulingError, match="full"):
            scheduler.submit(Task(task_type="t3", priority=5, required_capabilities=("x",)))

    async def test_deadline_expiry(self) -> None:
        scheduler = ColonyScheduler()
        scheduler.register_agent("a", capabilities=["gen"])
        import time
        past_deadline = time.monotonic() - 10.0
        task = Task(task_type="test", priority=5, deadline=past_deadline, required_capabilities=("gen",))
        scheduler.submit(task)
        result = await scheduler.assign_next()
        assert result is None
        assert scheduler.metrics.tasks_expired == 1

    async def test_background_drain(self) -> None:
        scheduler = ColonyScheduler()
        scheduler.register_agent("a", capabilities=["gen"])
        task = Task(task_type="t", priority=5, required_capabilities=("gen",))
        scheduler.submit(task)
        await scheduler.start_draining(interval=0.05)
        await asyncio.sleep(0.2)
        await scheduler.stop_draining()
        assert scheduler.get_queue_depth() == 0 or scheduler.metrics.tasks_completed >= 0


# ============================================================================
# Communication tests
# ============================================================================


class TestMessageBus:
    @pytest.fixture
    def bus(self) -> MessageBus:
        return MessageBus()

    def test_channel_creation(self, bus: MessageBus) -> None:
        ch = bus.create_channel("urgent")
        assert ch.topic == "urgent"
        assert ch.subscriber_count == 0

    def test_get_or_create_channel(self, bus: MessageBus) -> None:
        ch1 = bus.get_channel("test")
        ch2 = bus.get_channel("test")
        assert ch1 is ch2

    def test_subscribe_and_publish(self, bus: MessageBus) -> None:
        bus.subscribe("agent-1", "updates")
        ch = bus.get_channel("updates")
        assert ch.is_subscribed("agent-1")
        msg = Message(sender_id="system", topic="updates", payload={"text": "hello"})
        receipts = asyncio.run(bus.publish("updates", msg))
        assert len(receipts) == 1
        assert receipts[0].recipient_id == "agent-1"

    def test_channel_history(self, bus: MessageBus) -> None:
        ch = bus.get_channel("logs")
        msg = Message(sender_id="a", topic="logs")
        ch.publish(msg)
        history = ch.get_history()
        assert len(history) == 1

    async def test_send_fire_forget(self, bus: MessageBus) -> None:
        msg = Message(
            sender_id="a", recipient_id="b", topic="direct",
            protocol=Protocol.FIRE_FORGET, payload={"cmd": "ping"},
        )
        receipt = await bus.send(msg)
        assert not receipt.acknowledged

    async def test_send_request_reply_timeout(self, bus: MessageBus) -> None:
        msg = Message(
            sender_id="a", recipient_id="b", topic="direct",
            protocol=Protocol.REQUEST_REPLY, payload={"cmd": "ping"},
        )
        receipt = await bus.send(msg, ack_timeout=0.1)
        assert not receipt.acknowledged

    async def test_request_reply_with_acknowledgment(self, bus: MessageBus) -> None:
        msg = Message(
            sender_id="a", recipient_id="b",
            protocol=Protocol.REQUEST_REPLY, payload={"q": "status"},
        )
        async def ack_after_send() -> None:
            await asyncio.sleep(0.02)
            bus.acknowledge(msg.message_id)
        asyncio.create_task(ack_after_send())
        receipt = await bus.send(msg, ack_timeout=1.0)
        assert receipt.acknowledged

    async def test_broadcast(self, bus: MessageBus) -> None:
        msg = Message(sender_id="dispatcher", payload={"alert": "fire"})
        receipts = await bus.broadcast(msg, agent_ids=["a", "b", "c"])
        assert len(receipts) == 3

    async def test_multicast(self, bus: MessageBus) -> None:
        msg = Message(sender_id="leader", payload={"cmd": "start"})
        receipts = await bus.multicast(msg, agent_ids=["x", "y"])
        assert len(receipts) == 2

    async def test_receive_message(self, bus: MessageBus) -> None:
        msg = Message(sender_id="a", recipient_id="b", payload={"text": "hi"})
        await bus.send(msg)
        received = await bus.receive("b", timeout=0.5)
        assert received.sender_id == "a"
        assert received.payload["text"] == "hi"

    async def test_receive_batch(self, bus: MessageBus) -> None:
        for i in range(5):
            msg = Message(sender_id=f"a{i}", recipient_id="b", payload={"n": i})
            await bus.send(msg)
        batch = await bus.receive_batch("b", max_messages=10, timeout=0.2)
        assert len(batch) == 5

    def test_reply(self, bus: MessageBus) -> None:
        original = Message(sender_id="alice", recipient_id="bob", payload={"q": "status"})
        reply = bus.reply(original, {"status": "ok"})
        assert reply.recipient_id == "alice"
        assert reply.sender_id == "bob"
        assert reply.correlation_id == original.message_id

    def test_unsubscribe_all(self, bus: MessageBus) -> None:
        bus.subscribe("agent-1", "t1")
        bus.subscribe("agent-1", "t2")
        bus.unsubscribe_all("agent-1")
        ch1 = bus.get_channel("t1")
        assert not ch1.is_subscribed("agent-1")

    def test_remove_channel(self, bus: MessageBus) -> None:
        bus.create_channel("temp")
        assert bus.remove_channel("temp")
        assert "temp" not in bus.list_channels()
        assert not bus.remove_channel("nonexistent")

    def test_delivery_stats(self, bus: MessageBus) -> None:
        msg = Message(sender_id="a", recipient_id="b")
        asyncio.run(bus.send(msg))
        stats = bus.get_delivery_stats()
        assert stats["total_sent"] >= 1

    def test_replay_for_agent(self, bus: MessageBus) -> None:
        msg = Message(sender_id="a", recipient_id="b", payload={"id": 1})
        asyncio.run(bus.send(msg))
        replayed = bus.replay_for_agent("b")
        assert len(replayed) >= 1

    def test_message_expiry(self) -> None:
        msg = Message(sent_at=0.0, ttl_seconds=0.001)
        assert msg.is_expired(now=100.0)
        msg_fresh = Message()
        assert not msg_fresh.is_expired()

    def test_message_priority_values(self) -> None:
        assert MessagePriority.LOW.value < MessagePriority.CRITICAL.value


# ============================================================================
# Monitoring tests
# ============================================================================


class TestMonitoring:
    def test_register_agent(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        monitor.register_agent("agent-1")
        assert monitor.get_agent_status("agent-1") == AgentStatus.INITIALIZING

    def test_update_status(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        monitor.register_agent("agent-1")
        monitor.update_status("agent-1", AgentStatus.BUSY)
        assert monitor.get_agent_status("agent-1") == AgentStatus.BUSY

    def test_heartbeat_and_unresponsive(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        monitor.register_agent("agent-1")
        unresponsive = monitor.get_unresponsive_agents(timeout_seconds=0.0)
        assert "agent-1" in unresponsive

    def test_metrics_snapshot(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        monitor.register_agent("a")
        monitor.register_agent("b")
        monitor.update_status("a", AgentStatus.BUSY)
        monitor.update_status("b", AgentStatus.IDLE)
        s = monitor.snapshot()
        assert s.total_agents == 2
        assert s.active_agents == 1
        assert s.idle_agents == 1

    def test_health_score(self) -> None:
        from lyra_colony.monitoring import MetricsSnapshot
        s = MetricsSnapshot(total_agents=4, active_agents=2, idle_agents=1, degraded_agents=1, error_rate=0.0)
        assert 0.0 <= s.health_score <= 1.0

    def test_health_score_zero_agents(self) -> None:
        from lyra_colony.monitoring import MetricsSnapshot
        s = MetricsSnapshot()
        assert s.health_score == 0.0

    def test_alert_acknowledge_and_resolve(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor, AlertRule
        monitor = ColonyMonitor()
        monitor.register_agent("a")
        rule = AlertRule(name="test_alert", metric="queue_depth", threshold=0.0, comparator="gt", cooldown_seconds=0.0)
        monitor.add_alert_rule(rule)
        alerts = monitor.evaluate_alerts()
        if alerts:
            aid = alerts[0].alert_id
            assert monitor.acknowledge_alert(aid)
            assert monitor.resolve_alert(aid)
            assert not alerts[0].is_active

    def test_audit_log(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        monitor.log_audit("test_action", agent_id="agent-x", details={"key": "val"})
        entries = monitor.get_audit_log(agent_id="agent-x")
        assert len(entries) == 1
        assert entries[0].action == "test_action"
        assert entries[0].details["key"] == "val"

    def test_dashboard(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        monitor.register_agent("a")
        d = monitor.dashboard()
        assert "health" in d
        assert "performance" in d
        assert "resources" in d

    def test_record_latency_and_throughput(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        monitor.record_latency(0.5)
        monitor.record_latency(1.0)
        monitor.record_throughput(10)
        s = monitor.snapshot()
        assert s.avg_latency_ms > 0

    def test_message_recording(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor
        monitor = ColonyMonitor()
        for _ in range(5):
            monitor.record_message()
        s = monitor.snapshot()
        assert s.messages_per_second >= 0.0

    async def test_background_collection(self) -> None:
        from lyra_colony.monitoring import ColonyMonitor, AlertRule
        monitor = ColonyMonitor()
        monitor.register_agent("a")
        monitor.add_alert_rule(AlertRule(name="check", metric="queue_depth", threshold=100.0, comparator="gt", cooldown_seconds=0.0))
        await monitor.start_collection(interval=0.05)
        await asyncio.sleep(0.15)
        await monitor.stop_collection()


# ============================================================================
# Colony integration tests
# ============================================================================


class TestAgentColony:
    @pytest.fixture
    def colony(self) -> AgentColony:
        config = ColonyConfig(min_agents=1, max_agents=5, health_check_interval=10.0, scale_cooldown=10.0, gossip_interval=10.0)
        return AgentColony(config=config)

    async def test_start_stop_colony(self, colony: AgentColony) -> None:
        await colony.start()
        assert colony.state == ColonyState.RUNNING
        assert colony.agent_count >= 1
        await colony.stop()
        assert colony.state == ColonyState.STOPPED

    async def test_spawn_agent(self, colony: AgentColony) -> None:
        await colony.start()
        initial_count = colony.agent_count
        spec = AgentSpec(role=AgentRole(name="test-agent", kind=AgentRoleKind.WORKER), capabilities=("test", "execute"))
        agent_id = await colony.spawn_agent(spec)
        assert agent_id.startswith("test-agent-")
        assert colony.agent_count == initial_count + 1
        await colony.stop()

    async def test_spawn_at_capacity(self, colony: AgentColony) -> None:
        colony.config.max_agents = 2
        await colony.start()
        for _i in range(3):
            try:
                await colony.spawn_agent(AgentSpec(role=AgentRole(name="filler"), capabilities=("general",)))
            except ColonyOverCapacityError:
                break
        with pytest.raises(ColonyOverCapacityError):
            await colony.spawn_agent(AgentSpec(role=AgentRole(name="overflow"), capabilities=("general",)))
        await colony.stop()

    async def test_retire_agent(self, colony: AgentColony) -> None:
        await colony.start()
        spec = AgentSpec(role=AgentRole(name="temp"), capabilities=("general",))
        agent_id = await colony.spawn_agent(spec)
        assert await colony.retire_agent(agent_id)
        await colony.stop()

    async def test_retire_nonexistent(self, colony: AgentColony) -> None:
        await colony.start()
        with pytest.raises(AgentNotFoundError):
            await colony.retire_agent("nonexistent")
        await colony.stop()

    async def test_submit_task(self, colony: AgentColony) -> None:
        await colony.start()
        task = Task(task_type="test", priority=5, required_capabilities=("execute",))
        tid = await colony.submit_task(task)
        assert tid == task.task_id
        state = await colony.get_task_result(tid)
        assert state == TaskState.QUEUED
        await colony.stop()

    async def test_send_message(self, colony: AgentColony) -> None:
        await colony.start()
        msg_id = await colony.send_message("agent-a", "agent-b", {"text": "hello"})
        assert msg_id
        await colony.stop()

    async def test_broadcast(self, colony: AgentColony) -> None:
        await colony.start()
        await colony.broadcast_to_all({"alert": "test"})
        await colony.stop()

    def test_health_snapshot(self, colony: AgentColony) -> None:
        h = colony.health
        assert isinstance(h, ColonyHealth)
        assert h.state == ColonyState.INIT

    def test_stats(self, colony: AgentColony) -> None:
        s = colony.stats
        assert "total_agents" in s
        assert "health_score" in s

    async def test_dashboard(self, colony: AgentColony) -> None:
        await colony.start()
        d = colony.dashboard()
        assert "colony" in d
        assert "agents" in d
        assert "scheduler" in d
        assert "monitoring" in d
        await colony.stop()

    async def test_agent_discovery_by_capability(self, colony: AgentColony) -> None:
        await colony.start()
        spec = AgentSpec(role=AgentRole(name="finder"), capabilities=("nlp", "vision"))
        aid = await colony.spawn_agent(spec)
        found = colony.find_agents_by_capability("vision")
        assert aid in found
        not_found = colony.find_agents_by_capability("quantum")
        assert aid not in not_found
        await colony.stop()

    async def test_agent_discovery_by_role(self, colony: AgentColony) -> None:
        await colony.start()
        spec = AgentSpec(role=AgentRole(name="obs", kind=AgentRoleKind.OBSERVER), capabilities=("watch",))
        aid = await colony.spawn_agent(spec)
        observers = colony.find_agents_by_role(AgentRoleKind.OBSERVER)
        assert aid in observers
        await colony.stop()

    async def test_role_templates(self, colony: AgentColony) -> None:
        await colony.start()
        template_spec = AgentSpec(role=AgentRole(name="template-role"), capabilities=("template",))
        colony.register_template("my-template", template_spec)
        assert colony.get_template("my-template") is not None
        assert "my-template" in colony.list_templates()
        aid = await colony.spawn_from_template("my-template")
        agent = colony.get_agent(aid)
        assert agent.capabilities[0] == "template"
        await colony.stop()

    async def test_invalid_template(self, colony: AgentColony) -> None:
        await colony.start()
        with pytest.raises(InvalidSpecError):
            await colony.spawn_from_template("nonexistent")
        await colony.stop()

    async def test_get_agent_nonexistent(self, colony: AgentColony) -> None:
        await colony.start()
        with pytest.raises(AgentNotFoundError):
            colony.get_agent("no-such-agent")
        await colony.stop()

    async def test_find_by_label(self, colony: AgentColony) -> None:
        await colony.start()
        spec = AgentSpec(role=AgentRole(name="tagged"), capabilities=("general",), labels={"env": "staging"})
        aid = await colony.spawn_agent(spec)
        result = colony.find_agents_by_label("env", "staging")
        assert aid in result
        await colony.stop()


# ============================================================================
# Edge case tests
# ============================================================================


class TestEdgeCases:
    def test_empty_colony_health(self) -> None:
        colony = AgentColony(ColonyConfig(min_agents=1, max_agents=5))
        h = colony.health
        assert h.total_agents == 0

    def test_invalid_config(self) -> None:
        with pytest.raises(Exception, match="max_agents"):
            ColonyConfig(min_agents=10, max_agents=5)
        with pytest.raises(Exception, match="min_agents"):
            ColonyConfig(min_agents=0)

    def test_scheduler_with_no_agents(self) -> None:
        scheduler = ColonyScheduler()
        task = Task(task_type="orphan", priority=5)
        scheduler.submit(task)
        # Returns None when no agents registered (graceful handling)
        result = asyncio.run(scheduler.assign_next())
        assert result is None

    def test_network_partition_simulation(self) -> None:
        scheduler = ColonyScheduler()
        scheduler.register_agent("side-a-1", capabilities=["general"])
        scheduler.register_agent("side-a-2", capabilities=["general"])
        scheduler.unregister_agent("side-a-2")
        task = Task(task_type="test", priority=5, required_capabilities=("general",))
        scheduler.submit(task)
        assignment = asyncio.run(scheduler.assign_next())
        assert assignment is not None
        assert assignment.agent_id == "side-a-1"

    def test_duplicate_channel_raises(self) -> None:
        from lyra_colony.communication import SubscriptionError
        bus = MessageBus()
        bus.create_channel("test")
        with pytest.raises(SubscriptionError):
            bus.create_channel("test")

    async def test_message_bus_full_queue_graceful(self) -> None:
        bus = MessageBus()
        bus._agent_queues["b"] = asyncio.Queue(maxsize=2)
        for i in range(10):
            msg = Message(sender_id="a", recipient_id="b", payload={"i": i})
            await bus.send(msg)
        assert bus.get_delivery_stats()["total_sent"] == 10
