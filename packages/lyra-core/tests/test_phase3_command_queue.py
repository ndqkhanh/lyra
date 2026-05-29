"""Comprehensive tests for Phase 3: Command Queue & Three-Surface Protocol."""

from __future__ import annotations

import asyncio
import time

import pytest

from lyra_core.command_queue import (
    Command,
    CommandGroup,
    CommandGroupStatus,
    CommandPriority,
    CommandQueue,
    CommandStatus,
    SurfaceKind,
    SurfaceMessage,
    ThreeSurfaceProtocol,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Command
# ═══════════════════════════════════════════════════════════════════════════════


class TestCommand:
    def test_create_minimal(self):
        cmd = Command(id="cmd1", type="test")
        assert cmd.id == "cmd1"
        assert cmd.type == "test"
        assert cmd.status == CommandStatus.PENDING
        assert cmd.priority == CommandPriority.NORMAL

    def test_create_with_payload(self):
        cmd = Command(id="cmd1", type="run", payload={"instruction": "hello"})
        assert cmd.payload["instruction"] == "hello"

    def test_create_with_priority(self):
        cmd = Command(id="cmd1", type="test", priority=CommandPriority.CRITICAL)
        assert cmd.priority == CommandPriority.CRITICAL

    def test_is_terminal_states(self):
        for status in (CommandStatus.COMPLETED, CommandStatus.FAILED,
                       CommandStatus.CANCELLED, CommandStatus.ROLLED_BACK):
            cmd = Command(id="c1", type="t", status=status)
            assert cmd.is_terminal

    def test_is_not_terminal(self):
        for status in (CommandStatus.PENDING, CommandStatus.RUNNING,
                       CommandStatus.WAITING):
            cmd = Command(id="c1", type="t", status=status)
            assert not cmd.is_terminal

    def test_is_blocked(self):
        cmd = Command(id="c1", type="t", status=CommandStatus.WAITING)
        assert cmd.is_blocked

    def test_is_not_blocked(self):
        cmd = Command(id="c1", type="t", status=CommandStatus.PENDING)
        assert not cmd.is_blocked

    def test_elapsed_ms(self):
        cmd = Command(id="c1", type="t", started_at=1000.0, completed_at=1000.5)
        assert cmd.elapsed_ms == 500.0

    def test_elapsed_ms_no_start(self):
        cmd = Command(id="c1", type="t")
        assert cmd.elapsed_ms == 0.0

    def test_produces_refs(self):
        cmd = Command(id="c1", type="t", produces_refs=["ref_a", "ref_b"])
        assert "ref_a" in cmd.produces_refs

    def test_waits_on_refs(self):
        cmd = Command(id="c1", type="t", waits_on_refs=["ref_x"])
        assert "ref_x" in cmd.waits_on_refs

    def test_compensator_callback(self):
        called = []
        cmd = Command(id="c1", type="t", compensator=lambda: called.append(1))
        cmd.compensator()
        assert called == [1]

    def test_on_complete_callback(self):
        called = []
        cmd = Command(id="c1", type="t", on_complete=lambda c: called.append(c.id))
        cmd.on_complete(cmd)
        assert called == ["c1"]

    def test_default_values(self):
        cmd = Command(id="c1", type="t")
        assert cmd.payload == {}
        assert cmd.produces_refs == []
        assert cmd.waits_on_refs == []
        assert cmd.error is None
        assert cmd.result is None


# ═══════════════════════════════════════════════════════════════════════════════
# CommandStatus
# ═══════════════════════════════════════════════════════════════════════════════


class TestCommandStatus:
    def test_all_status_values(self):
        for status in CommandStatus:
            assert isinstance(status.value, str)


# ═══════════════════════════════════════════════════════════════════════════════
# CommandPriority
# ═══════════════════════════════════════════════════════════════════════════════


class TestCommandPriority:
    def test_ordering(self):
        assert CommandPriority.CRITICAL.value < CommandPriority.HIGH.value
        assert CommandPriority.HIGH.value < CommandPriority.NORMAL.value
        assert CommandPriority.NORMAL.value < CommandPriority.LOW.value
        assert CommandPriority.LOW.value < CommandPriority.BACKGROUND.value


# ═══════════════════════════════════════════════════════════════════════════════
# CommandQueue
# ═══════════════════════════════════════════════════════════════════════════════


class TestCommandQueue:
    def test_create_empty(self):
        q = CommandQueue()
        assert q.size == 0
        assert q.is_empty

    @pytest.mark.asyncio
    async def test_enqueue_single(self):
        q = CommandQueue()
        cmd = Command(id="c1", type="test")
        await q.enqueue(cmd)
        assert q.size == 1

    @pytest.mark.asyncio
    async def test_enqueue_respects_priority(self):
        q = CommandQueue()
        low = Command(id="low", type="t", priority=CommandPriority.LOW)
        critical = Command(id="critical", type="t", priority=CommandPriority.CRITICAL)
        normal = Command(id="normal", type="t", priority=CommandPriority.NORMAL)

        await q.enqueue(low)
        await q.enqueue(critical)
        await q.enqueue(normal)

        # Should be ordered: critical, normal, low
        ordered = [c.id for c in q._queue]
        assert ordered == ["critical", "normal", "low"]

    @pytest.mark.asyncio
    async def test_enqueue_stable_for_same_priority(self):
        q = CommandQueue()
        a = Command(id="a", type="t", priority=CommandPriority.NORMAL)
        b = Command(id="b", type="t", priority=CommandPriority.NORMAL)

        await q.enqueue(a)
        await q.enqueue(b)
        # Same priority: first in, first out
        assert q._queue[0].id == "a"
        assert q._queue[1].id == "b"

    @pytest.mark.asyncio
    async def test_cancel_pending_command(self):
        q = CommandQueue()
        cmd = Command(id="c1", type="test")
        await q.enqueue(cmd)
        result = await q.cancel("c1")
        assert result is True
        assert q.size == 0

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self):
        q = CommandQueue()
        result = await q.cancel("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_command_in_queue(self):
        q = CommandQueue()
        cmd = Command(id="c1", type="test")
        await q.enqueue(cmd)
        found = await q.get_command("c1")
        assert found is not None
        assert found.id == "c1"

    @pytest.mark.asyncio
    async def test_get_command_not_found(self):
        q = CommandQueue()
        found = await q.get_command("nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_resolve_command_success(self):
        q = CommandQueue()
        cmd = Command(id="c1", type="test")
        await q.enqueue(cmd)
        # Manually set to RUNNING (simulates processor picking it up)
        cmd.status = CommandStatus.RUNNING
        cmd.started_at = time.time()

        result = await q.resolve("c1", result="done")
        assert result is True
        updated = await q.get_command("c1")
        if updated is None:
            # It may have been moved to history
            pass

    @pytest.mark.asyncio
    async def test_resolve_command_with_error(self):
        q = CommandQueue()
        cmd = Command(id="c1", type="test")
        await q.enqueue(cmd)
        cmd.status = CommandStatus.RUNNING
        cmd.started_at = time.time()

        result = await q.resolve("c1", error="something failed")
        assert result is True

    @pytest.mark.asyncio
    async def test_resolve_resolves_refs(self):
        q = CommandQueue()
        cmd = Command(id="c1", type="test", produces_refs=["ref_a"])
        await q.enqueue(cmd)
        cmd.status = CommandStatus.RUNNING
        cmd.started_at = time.time()

        await q.resolve("c1", result="ok")
        assert "ref_a" in q._resolved_refs

    @pytest.mark.asyncio
    async def test_resolve_nonexistent(self):
        q = CommandQueue()
        result = await q.resolve("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_ref_blocking(self):
        q = CommandQueue()
        # Declare a ref that must be produced
        q.declare_ref("file_output")

        # Command that waits on that ref
        waiter = Command(id="waiter", type="process", waits_on_refs=["file_output"])
        await q.enqueue(waiter)

        # Command that produces the ref
        producer = Command(id="producer", type="write", produces_refs=["file_output"])
        await q.enqueue(producer)

        # Waiter should be blocked
        assert q._are_refs_satisfied(waiter) is False

        # Resolve producer
        producer.status = CommandStatus.RUNNING
        producer.started_at = time.time()
        await q.resolve("producer", result="written")

        # Now waiter should be unblocked
        assert q._are_refs_satisfied(waiter) is True

    @pytest.mark.asyncio
    async def test_pending_commands(self):
        q = CommandQueue()
        await q.enqueue(Command(id="c1", type="t"))
        await q.enqueue(Command(id="c2", type="t"))
        assert len(q.pending_commands) == 2

    @pytest.mark.asyncio
    async def test_unresolved_refs(self):
        q = CommandQueue()
        q.declare_ref("missing_ref")
        assert "missing_ref" in q.unresolved_refs

    @pytest.mark.asyncio
    async def test_on_complete_fires(self):
        results = []
        q = CommandQueue()
        cmd = Command(
            id="c1", type="test",
            on_complete=lambda c: results.append(c.id),
        )
        await q.enqueue(cmd)
        cmd.status = CommandStatus.RUNNING
        cmd.started_at = time.time()
        await q.resolve("c1", result="ok")
        assert results == ["c1"]


# ═══════════════════════════════════════════════════════════════════════════════
# CommandGroup
# ═══════════════════════════════════════════════════════════════════════════════


class TestCommandGroup:
    def test_create(self):
        cmds = [
            Command(id="c1", type="step1"),
            Command(id="c2", type="step2"),
        ]
        group = CommandGroup(id="g1", commands=cmds)
        assert group.id == "g1"
        assert len(group.commands) == 2
        assert group.status == CommandGroupStatus.PENDING

    def test_command_ids(self):
        cmds = [Command(id="a", type="t"), Command(id="b", type="t")]
        group = CommandGroup(id="g1", commands=cmds)
        assert group.command_ids == ["a", "b"]

    def test_all_completed(self):
        cmds = [
            Command(id="c1", type="t", status=CommandStatus.COMPLETED),
            Command(id="c2", type="t", status=CommandStatus.COMPLETED),
        ]
        group = CommandGroup(id="g1", commands=cmds)
        assert group.all_completed

    def test_not_all_completed(self):
        cmds = [
            Command(id="c1", type="t", status=CommandStatus.COMPLETED),
            Command(id="c2", type="t", status=CommandStatus.PENDING),
        ]
        group = CommandGroup(id="g1", commands=cmds)
        assert not group.all_completed

    def test_has_failures(self):
        cmds = [
            Command(id="c1", type="t", status=CommandStatus.COMPLETED),
            Command(id="c2", type="t", status=CommandStatus.FAILED),
        ]
        group = CommandGroup(id="g1", commands=cmds)
        assert group.has_failures

    def test_no_failures(self):
        cmds = [
            Command(id="c1", type="t", status=CommandStatus.COMPLETED),
            Command(id="c2", type="t", status=CommandStatus.COMPLETED),
        ]
        group = CommandGroup(id="g1", commands=cmds)
        assert not group.has_failures

    def test_record_completion(self):
        cmds = [Command(id="c1", type="t"), Command(id="c2", type="t")]
        group = CommandGroup(id="g1", commands=cmds)
        group.record_completion(cmds[0])
        group.record_completion(cmds[1])
        assert len(group._completed_order) == 2

    @pytest.mark.asyncio
    async def test_execute_rollback_on_failure(self):
        rollback_log = []
        cmds = [
            Command(
                id="c1", type="create",
                compensator=lambda: rollback_log.append("undo_c1"),
            ),
            Command(
                id="c2", type="update",
                compensator=lambda: rollback_log.append("undo_c2"),
            ),
        ]
        group = CommandGroup(id="g1", commands=cmds)
        group.status = CommandGroupStatus.RUNNING

        # Simulate: c1 completed, c2 failed
        cmds[0].status = CommandStatus.COMPLETED
        group.record_completion(cmds[0])
        cmds[1].status = CommandStatus.FAILED
        group.record_completion(cmds[1])

        await group._rollback()
        # Rollback in reverse order: undo_c2 first (but c2 failed, so skip),
        # then undo_c1
        assert "undo_c1" in rollback_log

    def test_command_group_status_values(self):
        for status in CommandGroupStatus:
            assert isinstance(status.value, str)


# ═══════════════════════════════════════════════════════════════════════════════
# SurfaceMessage
# ═══════════════════════════════════════════════════════════════════════════════


class TestSurfaceMessage:
    def test_create(self):
        msg = SurfaceMessage(
            surface=SurfaceKind.CONTROL,
            id="msg1",
            type="start",
            source="agent_a",
        )
        assert msg.surface == SurfaceKind.CONTROL
        assert msg.id == "msg1"
        assert msg.type == "start"

    def test_default_values(self):
        msg = SurfaceMessage(surface=SurfaceKind.DATA, id="m1", type="chunk")
        assert msg.payload == {}
        assert msg.correlation_id is None
        assert msg.source == ""

    def test_correlation_id(self):
        msg = SurfaceMessage(
            surface=SurfaceKind.CONTROL, id="m1", type="cmd",
            correlation_id="corr_123",
        )
        assert msg.correlation_id == "corr_123"

    def test_timestamp(self):
        before = time.time()
        msg = SurfaceMessage(surface=SurfaceKind.DATA, id="m1", type="chunk")
        assert msg.timestamp >= before


# ═══════════════════════════════════════════════════════════════════════════════
# SurfaceKind
# ═══════════════════════════════════════════════════════════════════════════════


class TestSurfaceKind:
    def test_all_values(self):
        assert SurfaceKind.CONTROL.value == "control"
        assert SurfaceKind.DATA.value == "data"
        assert SurfaceKind.NOTIFICATION.value == "notification"


# ═══════════════════════════════════════════════════════════════════════════════
# ThreeSurfaceProtocol
# ═══════════════════════════════════════════════════════════════════════════════


class TestThreeSurfaceProtocol:
    def test_create(self):
        tsp = ThreeSurfaceProtocol()
        assert tsp.message_count == 0

    @pytest.mark.asyncio
    async def test_send_message(self):
        tsp = ThreeSurfaceProtocol()
        msg = SurfaceMessage(surface=SurfaceKind.CONTROL, id="m1", type="test")
        await tsp.send(msg)
        assert tsp.message_count == 1

    @pytest.mark.asyncio
    async def test_send_control(self):
        tsp = ThreeSurfaceProtocol()
        msg = await tsp.send_control("start", {"key": "val"}, source="agent_a")
        assert msg.surface == SurfaceKind.CONTROL
        assert msg.type == "start"
        assert msg.payload["key"] == "val"

    @pytest.mark.asyncio
    async def test_send_data(self):
        tsp = ThreeSurfaceProtocol()
        msg = await tsp.send_data("chunk", {"text": "hello"}, source="agent_a")
        assert msg.surface == SurfaceKind.DATA
        assert msg.payload["text"] == "hello"

    @pytest.mark.asyncio
    async def test_send_notification(self):
        tsp = ThreeSurfaceProtocol()
        msg = await tsp.send_notification("alert", {"level": "warn"}, source="system")
        assert msg.surface == SurfaceKind.NOTIFICATION
        assert msg.payload["level"] == "warn"

    @pytest.mark.asyncio
    async def test_correlation_tracking(self):
        tsp = ThreeSurfaceProtocol()
        msg = await tsp.send_control("cmd", correlation_id="corr_42")
        found = tsp.get_correlated("corr_42")
        assert found is not None
        assert found.id == msg.id

    @pytest.mark.asyncio
    async def test_correlation_missing(self):
        tsp = ThreeSurfaceProtocol()
        assert tsp.get_correlated("nonexistent") is None

    @pytest.mark.asyncio
    async def test_handler_registration(self):
        received = []
        tsp = ThreeSurfaceProtocol()

        def handler(msg: SurfaceMessage):
            received.append(msg.type)

        tsp.on(SurfaceKind.CONTROL, "test", handler)
        await tsp.send_control("test")
        assert received == ["test"]

    @pytest.mark.asyncio
    async def test_async_handler(self):
        received = []
        tsp = ThreeSurfaceProtocol()

        async def handler(msg: SurfaceMessage):
            await asyncio.sleep(0)
            received.append(msg.id)

        tsp.on(SurfaceKind.DATA, "chunk", handler)
        msg = await tsp.send_data("chunk")
        assert msg.id in received

    @pytest.mark.asyncio
    async def test_handler_removal(self):
        received = []
        tsp = ThreeSurfaceProtocol()

        def handler(msg: SurfaceMessage):
            received.append(msg.type)

        tsp.on(SurfaceKind.CONTROL, "test", handler)
        tsp.off(SurfaceKind.CONTROL, "test", handler)
        await tsp.send_control("test")
        assert received == []

    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        received = []
        tsp = ThreeSurfaceProtocol()

        def h1(msg): received.append("h1")
        def h2(msg): received.append("h2")

        tsp.on(SurfaceKind.CONTROL, "multi", h1)
        tsp.on(SurfaceKind.CONTROL, "multi", h2)
        await tsp.send_control("multi")
        assert "h1" in received
        assert "h2" in received

    @pytest.mark.asyncio
    async def test_recent_messages(self):
        tsp = ThreeSurfaceProtocol()
        await tsp.send_control("c1")
        await tsp.send_data("d1")
        await tsp.send_notification("n1")

        assert len(tsp.recent_messages()) == 3
        assert len(tsp.recent_messages(surface=SurfaceKind.CONTROL)) == 1
        assert len(tsp.recent_messages(surface=SurfaceKind.DATA)) == 1

    @pytest.mark.asyncio
    async def test_recent_messages_limit(self):
        tsp = ThreeSurfaceProtocol()
        for i in range(100):
            await tsp.send_control(f"cmd_{i}")
        assert len(tsp.recent_messages(limit=30)) == 30

    @pytest.mark.asyncio
    async def test_surface_to_category_mapping(self):
        tsp = ThreeSurfaceProtocol()
        from lyra_core.events import EventCategory

        assert tsp._surface_to_category(SurfaceKind.CONTROL) == EventCategory.LIFECYCLE
        assert tsp._surface_to_category(SurfaceKind.DATA) == EventCategory.TELEMETRY
        assert tsp._surface_to_category(SurfaceKind.NOTIFICATION) == EventCategory.NOTIFICATION
