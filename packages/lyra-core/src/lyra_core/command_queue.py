"""Command Queue & Three-Surface Protocol — tmux-inspired CMD_RETURN_WAIT pattern.

Inspired by tmux's command queue:
  - FIFO command queue with CMD_RETURN_WAIT references
  - Command groups with atomic failure and compensating actions
  - Three-surface protocol: Control, Data, Notification

Also incorporates rmux's unified protocol concept:
  - Same command model for CLI, SDK, and WebSocket interfaces
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from lyra_core.events import EventBus, EventCategory

logger = logging.getLogger(__name__)


# ── Command ──────────────────────────────────────────────────────────────────


class CommandStatus(str, Enum):
    """Command lifecycle states."""
    PENDING = "pending"          # Queued, not yet started
    RUNNING = "running"          # Currently executing
    WAITING = "waiting"          # CMD_RETURN_WAIT — blocked on a reference
    COMPLETED = "completed"      # Successfully finished
    FAILED = "failed"            # Execution failed
    CANCELLED = "cancelled"      # Cancelled before completion
    ROLLED_BACK = "rolled_back"  # Reversed via compensating action


class CommandPriority(int, Enum):
    """Priority levels. Lower values = higher priority (runs first)."""
    CRITICAL = 0
    HIGH = 10
    NORMAL = 50
    LOW = 100
    BACKGROUND = 200


@dataclass
class Command:
    """A single command in the queue. Like tmux's cmd_entry.

    Supports CMD_RETURN_WAIT: a command can declare references that must
    be resolved before subsequent dependent commands can proceed.
    """

    id: str
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: CommandPriority = CommandPriority.NORMAL
    status: CommandStatus = CommandStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    result: Any = None

    # CMD_RETURN_WAIT: references this command produces (blocked until resolved)
    produces_refs: list[str] = field(default_factory=list)
    # CMD_RETURN_WAIT: references this command waits on before running
    waits_on_refs: list[str] = field(default_factory=list)

    # Compensating action for rollback on atomic group failure
    compensator: Callable[[], Any] | None = field(default=None, repr=False)
    # Callback on completion
    on_complete: Callable[["Command"], None] | None = field(default=None, repr=False)

    @property
    def is_terminal(self) -> bool:
        return self.status in (CommandStatus.COMPLETED, CommandStatus.FAILED,
                               CommandStatus.CANCELLED, CommandStatus.ROLLED_BACK)

    @property
    def is_blocked(self) -> bool:
        return self.status == CommandStatus.WAITING

    @property
    def elapsed_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000.0


# ── Command Queue ────────────────────────────────────────────────────────────


class CommandQueue:
    """FIFO command queue with priority ordering and CMD_RETURN_WAIT references.

    Like tmux's cmdq: commands are enqueued and processed sequentially.
    Priority is respected within the queue. References enable synchronization
    between commands — a command that produces a reference blocks dependent
    commands until it completes.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._queue: deque[Command] = deque()
        self._bus = bus or EventBus.get()
        self._history: list[Command] = []
        self._pending_refs: set[str] = set()  # References not yet resolved
        self._resolved_refs: set[str] = set()  # References now available
        self._lock = asyncio.Lock()
        self._process_task: asyncio.Task[None] | None = None

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def pending_commands(self) -> list[Command]:
        return [c for c in self._queue if c.status == CommandStatus.PENDING]

    @property
    def waiting_commands(self) -> list[Command]:
        return [c for c in self._queue if c.status == CommandStatus.WAITING]

    async def enqueue(self, cmd: Command) -> None:
        """Add a command to the queue. Respects priority ordering."""
        async with self._lock:
            cmd.status = CommandStatus.PENDING
            # Insert in priority order (maintain stability for same priority)
            inserted = False
            for i, existing in enumerate(self._queue):
                if cmd.priority.value < existing.priority.value:
                    self._queue.insert(i, cmd)
                    inserted = True
                    break
            if not inserted:
                self._queue.append(cmd)

            self._bus.publish(
                category=EventCategory.LIFECYCLE,
                name="command.enqueued",
                origin=__name__,
                payload={"command_id": cmd.id, "type": cmd.type,
                        "queue_size": len(self._queue)},
            )

        # Start processing if not already running
        if self._process_task is None or self._process_task.done():
            self._process_task = asyncio.create_task(self._process())

    async def enqueue_many(self, commands: list[Command]) -> None:
        """Enqueue multiple commands atomically."""
        for cmd in commands:
            await self.enqueue(cmd)

    async def cancel(self, command_id: str) -> bool:
        """Cancel a pending or waiting command."""
        async with self._lock:
            for cmd in self._queue:
                if cmd.id == command_id and not cmd.is_terminal:
                    cmd.status = CommandStatus.CANCELLED
                    cmd.completed_at = time.time()
                    self._history.append(cmd)
                    self._queue.remove(cmd)
                    self._bus.publish(
                        category=EventCategory.LIFECYCLE,
                        name="command.cancelled",
                        origin=__name__,
                        payload={"command_id": command_id},
                    )
                    return True
        return False

    async def get_command(self, command_id: str) -> Command | None:
        """Find a command by ID (in queue or history)."""
        for cmd in self._queue:
            if cmd.id == command_id:
                return cmd
        for cmd in self._history:
            if cmd.id == command_id:
                return cmd
        return None

    async def drain(self) -> None:
        """Wait for the queue to be fully processed."""
        if self._process_task and not self._process_task.done():
            await self._process_task

    async def _process(self) -> None:
        """Process commands from the queue sequentially."""
        while True:
            cmd: Command | None = None
            async with self._lock:
                if not self._queue:
                    break
                # Find the next runnable command
                for c in self._queue:
                    if c.status == CommandStatus.PENDING:
                        # Check if all waited-on refs are resolved
                        if self._are_refs_satisfied(c):
                            c.status = CommandStatus.RUNNING
                            c.started_at = time.time()
                            cmd = c
                            break
                        else:
                            c.status = CommandStatus.WAITING
                if cmd is None:
                    break  # No runnable commands

            # Execute outside lock so other commands can be enqueued
            try:
                await self._execute(cmd)
            except Exception:
                logger.exception("Command %s execution failed", cmd.id)

    async def _execute(self, cmd: Command) -> None:
        """Execute a single command and handle its result."""
        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="command.started",
            origin=__name__,
            payload={"command_id": cmd.id, "type": cmd.type},
        )

        try:
            # The actual execution is done by an external executor.
            # The queue manages lifecycle; the caller invokes the work.
            # We mark completion via resolve().
            pass
        except Exception as exc:
            async with self._lock:
                cmd.status = CommandStatus.FAILED
                cmd.error = str(exc)
                cmd.completed_at = time.time()
                self._history.append(cmd)
                self._queue.remove(cmd)

            self._bus.publish(
                category=EventCategory.LIFECYCLE,
                name="command.failed",
                origin=__name__,
                payload={"command_id": cmd.id, "error": cmd.error},
            )

    async def resolve(self, command_id: str, result: Any = None,
                     error: str | None = None) -> bool:
        """Mark a command as completed or failed. Resolves CMD_RETURN_WAIT refs."""
        async with self._lock:
            cmd = None
            for c in self._queue:
                if c.id == command_id:
                    cmd = c
                    break

            if cmd is None or cmd.status != CommandStatus.RUNNING:
                return False

            if error:
                cmd.status = CommandStatus.FAILED
                cmd.error = error
            else:
                cmd.status = CommandStatus.COMPLETED
                cmd.result = result

            cmd.completed_at = time.time()

            # Resolve any references this command produced
            for ref in cmd.produces_refs:
                self._pending_refs.discard(ref)
                self._resolved_refs.add(ref)

            self._history.append(cmd)
            self._queue.remove(cmd)

        # Emit event
        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="command.resolved",
            origin=__name__,
            payload={"command_id": command_id, "status": cmd.status.value,
                    "resolved_refs": cmd.produces_refs},
        )

        # Fire callback
        if cmd.on_complete:
            cmd.on_complete(cmd)

        # Wake up waiting commands
        if self._process_task is None or self._process_task.done():
            self._process_task = asyncio.create_task(self._process())

        return True

    def _are_refs_satisfied(self, cmd: Command) -> bool:
        """Check if all references a command waits on are resolved."""
        for ref in cmd.waits_on_refs:
            if ref not in self._resolved_refs:
                return False
        return True

    def declare_ref(self, ref: str) -> None:
        """Declare a reference that must be produced before dependent commands run."""
        self._pending_refs.add(ref)

    @property
    def unresolved_refs(self) -> frozenset[str]:
        return frozenset(self._pending_refs - self._resolved_refs)


# ── Command Group ────────────────────────────────────────────────────────────


class CommandGroupStatus(str, Enum):
    """Group-level status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class CommandGroup:
    """Atomic group of commands. Like tmux's command group with atomic failure.

    If any command in the group fails, all completed commands in the group
    have their compensating actions invoked in reverse completion order.
    """

    id: str
    commands: list[Command] = field(default_factory=list)
    status: CommandGroupStatus = CommandGroupStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    error: str | None = None
    _completed_order: list[Command] = field(default_factory=list, repr=False)
    _queue: CommandQueue | None = field(default=None, repr=False)

    @property
    def command_ids(self) -> list[str]:
        return [c.id for c in self.commands]

    @property
    def all_completed(self) -> bool:
        return all(c.is_terminal for c in self.commands)

    @property
    def has_failures(self) -> bool:
        return any(c.status in (CommandStatus.FAILED, CommandStatus.CANCELLED)
                   for c in self.commands)

    async def execute(self, queue: CommandQueue,
                     _executor: Callable[[Command], Any] | None = None) -> None:
        """Execute all commands through the queue. Atomic: rollback on any failure."""
        self._queue = queue
        self.status = CommandGroupStatus.RUNNING

        for cmd in sorted(self.commands, key=lambda c: c.priority.value):
            await queue.enqueue(cmd)

        # Wait for all commands to complete
        await queue.drain()

        # Check results
        if self.has_failures:
            self.status = CommandGroupStatus.ROLLING_BACK
            await self._rollback()
        else:
            self.status = CommandGroupStatus.COMPLETED

        self.completed_at = time.time()

    async def _rollback(self) -> None:
        """Execute compensating actions in reverse completion order."""
        failures: list[str] = []
        for cmd in reversed(self._completed_order):
            if cmd.compensator and cmd.status == CommandStatus.COMPLETED:
                try:
                    result = cmd.compensator()
                    if asyncio.iscoroutine(result):
                        await result
                    cmd.status = CommandStatus.ROLLED_BACK
                except Exception as exc:
                    failures.append(f"{cmd.id}: {exc}")
                    logger.error("Rollback failed for %s: %s", cmd.id, exc)

        if failures:
            self.status = CommandGroupStatus.PARTIALLY_FAILED
            self.error = f"Rollback failures: {'; '.join(failures)}"
        else:
            self.status = CommandGroupStatus.ROLLED_BACK

        if self._queue:
            self._queue._bus.publish(
                category=EventCategory.LIFECYCLE,
                name="command_group.rolled_back",
                origin=__name__,
                payload={"group_id": self.id, "failures": failures},
            )

    def record_completion(self, cmd: Command) -> None:
        """Called when a command completes to track order for rollback."""
        self._completed_order.append(cmd)


# ── Three-Surface Protocol ───────────────────────────────────────────────────


class SurfaceKind(str, Enum):
    """The three surfaces of the unified protocol. Inspired by rmux."""
    CONTROL = "control"        # Commands, configuration, lifecycle
    DATA = "data"              # Streaming output, task results, artifacts
    NOTIFICATION = "notification"  # Events, alerts, status changes


@dataclass
class SurfaceMessage:
    """A message on one of the three surfaces."""

    surface: SurfaceKind
    id: str
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None  # Links request/response across surfaces
    timestamp: float = field(default_factory=time.time)
    source: str = ""  # agent_id, project_id, or system component


class ThreeSurfaceProtocol:
    """Unified three-surface interface for agent communication.

    Like rmux's unified protocol: the same message model serves CLI, SDK,
    and WebSocket interfaces. Each surface has distinct semantics:

    - Control surface: Commands, lifecycle ops, configuration changes.
      These are request/response and expect acknowledgments.
    - Data surface: Streaming output and task results.
      These are firehose-style, high-throughput, lossy-tolerant.
    - Notification surface: Events, alerts, and status broadcasts.
      These are fire-and-forget, best-effort delivery.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or EventBus.get()
        self._handlers: dict[SurfaceKind, dict[str, list[Callable]]] = {
            sk: {} for sk in SurfaceKind
        }
        self._message_history: list[SurfaceMessage] = []
        self._correlation_map: dict[str, SurfaceMessage] = {}

    # ── Sending ───────────────────────────────────────────────────────────

    async def send(self, msg: SurfaceMessage) -> None:
        """Send a message on one of the three surfaces."""
        self._message_history.append(msg)

        if msg.correlation_id:
            self._correlation_map[msg.correlation_id] = msg

        self._bus.publish(
            category=self._surface_to_category(msg.surface),
            name=f"surface.{msg.surface.value}.{msg.type}",
            origin=__name__,
            payload={
                "message_id": msg.id,
                "surface": msg.surface.value,
                "type": msg.type,
                "payload": msg.payload,
                "correlation_id": msg.correlation_id,
                "source": msg.source,
            },
        )

        # Dispatch to registered handlers
        handlers = self._handlers[msg.surface].get(msg.type, [])
        for handler in handlers:
            try:
                result = handler(msg)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Handler failed for %s:%s",
                               msg.surface.value, msg.type)

    async def send_control(self, msg_type: str, payload: dict[str, Any] | None = None,
                          correlation_id: str | None = None,
                          source: str = "") -> SurfaceMessage:
        """Send a control-surface message."""
        import uuid
        msg = SurfaceMessage(
            surface=SurfaceKind.CONTROL,
            id=str(uuid.uuid4()),
            type=msg_type,
            payload=payload or {},
            correlation_id=correlation_id,
            source=source,
        )
        await self.send(msg)
        return msg

    async def send_data(self, msg_type: str, payload: dict[str, Any] | None = None,
                       correlation_id: str | None = None,
                       source: str = "") -> SurfaceMessage:
        """Send a data-surface message."""
        import uuid
        msg = SurfaceMessage(
            surface=SurfaceKind.DATA,
            id=str(uuid.uuid4()),
            type=msg_type,
            payload=payload or {},
            correlation_id=correlation_id,
            source=source,
        )
        await self.send(msg)
        return msg

    async def send_notification(self, msg_type: str, payload: dict[str, Any] | None = None,
                               source: str = "") -> SurfaceMessage:
        """Send a notification-surface message."""
        import uuid
        msg = SurfaceMessage(
            surface=SurfaceKind.NOTIFICATION,
            id=str(uuid.uuid4()),
            type=msg_type,
            payload=payload or {},
            source=source,
        )
        await self.send(msg)
        return msg

    # ── Receiving ─────────────────────────────────────────────────────────

    def on(self, surface: SurfaceKind, msg_type: str,
           handler: Callable[[SurfaceMessage], Any]) -> None:
        """Register a handler for a specific surface+message type."""
        if msg_type not in self._handlers[surface]:
            self._handlers[surface][msg_type] = []
        self._handlers[surface][msg_type].append(handler)

    def off(self, surface: SurfaceKind, msg_type: str,
            handler: Callable[[SurfaceMessage], Any]) -> None:
        """Remove a handler."""
        handlers = self._handlers[surface].get(msg_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ── Correlation ───────────────────────────────────────────────────────

    def get_correlated(self, correlation_id: str) -> SurfaceMessage | None:
        """Find a message by correlation ID."""
        return self._correlation_map.get(correlation_id)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _surface_to_category(surface: SurfaceKind) -> EventCategory:
        """Map surface kind to event category."""
        mapping = {
            SurfaceKind.CONTROL: EventCategory.LIFECYCLE,
            SurfaceKind.DATA: EventCategory.TELEMETRY,
            SurfaceKind.NOTIFICATION: EventCategory.NOTIFICATION,
        }
        return mapping.get(surface, EventCategory.LIFECYCLE)

    @property
    def message_count(self) -> int:
        return len(self._message_history)

    def recent_messages(self, surface: SurfaceKind | None = None,
                       limit: int = 50) -> list[SurfaceMessage]:
        """Get recent messages, optionally filtered by surface."""
        msgs = self._message_history
        if surface is not None:
            msgs = [m for m in msgs if m.surface == surface]
        return msgs[-limit:]
