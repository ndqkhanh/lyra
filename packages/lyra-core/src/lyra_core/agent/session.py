"""Agent-as-session model — persistent lifecycle wrapper with snapshot support.

Inspired by tmux's session model and cmux/rmux agent-as-session patterns:
  - Each agent runs as a persistent session with well-defined lifecycle states
  - Sessions survive restarts via structured snapshots
  - Winlink-style indirection allows multiple observers to reference the same agent
  - Colored status rings encode lifecycle state for visualization
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from lyra_core.events import EventBus, EventCategory
from lyra_core.protocol import (
    AgentHealth,
    AgentIdentity,
    AgentLifecycle,
    AgentProtocol,
    AgentState,
    Task,
    TaskResult,
)


class SessionStatus(str, Enum):
    """Coarse-grained session status for visualization (colored rings)."""
    SPAWNING = "spawning"    # Blue — session being created
    RUNNING = "running"      # Green — actively processing
    PAUSED = "paused"        # Yellow — suspended, awaiting input
    ERROR = "error"          # Red — faulted, needs attention
    COMPLETED = "completed"  # Grey — finished successfully
    TERMINATED = "terminated"  # Dark grey — killed or expired

    def color(self) -> str:
        """Return ANSI color code for terminal visualization."""
        return {
            SessionStatus.SPAWNING: "blue",
            SessionStatus.RUNNING: "green",
            SessionStatus.PAUSED: "yellow",
            SessionStatus.ERROR: "red",
            SessionStatus.COMPLETED: "bright_black",
            SessionStatus.TERMINATED: "grey",
        }.get(self, "white")


@dataclass
class SessionSnapshot:
    """Serializable snapshot of agent session state.

    Like rmux's PaneSnapshot — captures enough state to reconstruct
    the agent session after a restart.
    """

    session_id: str
    agent_id: str
    status: SessionStatus
    lifecycle: AgentLifecycle
    health: AgentHealth
    created_at: float
    updated_at: float
    task_count: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    last_output: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    mode_stack: list[str] = field(default_factory=list)


class AgentSession:
    """Persistent session wrapping an AgentProtocol instance.

    Sessions are the unit of lifecycle management. They:
      - Own a reference to the underlying agent
      - Maintain coarse-grained status for visualization
      - Support snapshot/restore for crash recovery
      - Track task history and performance metrics
      - Emit lifecycle events for the sidecar metadata bus

    Multiple observers can reference the same session (winlink pattern).
    """

    def __init__(
        self,
        agent: AgentProtocol,
        *,
        session_id: str | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._agent = agent
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
        self._bus = bus or EventBus.get()

        self._status = SessionStatus.SPAWNING
        self._created_at = time.time()
        self._updated_at = time.time()
        self._task_count = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._last_output = ""
        self._metadata: dict[str, str] = {}
        self._refcount = 0  # Winlink-style reference counting
        self._history: list[TaskResult] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialize the agent and transition to RUNNING."""
        self._transition(SessionStatus.SPAWNING)
        try:
            await self._agent.initialize()
            self._transition(SessionStatus.RUNNING)
        except Exception:
            self._transition(SessionStatus.ERROR)
            raise

    async def run(self, task: Task) -> TaskResult:
        """Execute a task on the agent and track the result."""
        self._transition(SessionStatus.RUNNING)
        self._task_count += 1

        output_parts: list[str] = []
        try:
            async for chunk in self._agent.run(task):
                output_parts.append(chunk)
            output = "".join(output_parts)
            self._last_output = output
            result = TaskResult(
                task_id=task.task_id,
                agent_id=self._agent.identity.agent_id,
                success=True,
                output=output,
                error="",
                metrics={},
                artifacts=[],
            )
            self._completed_tasks += 1
        except Exception as exc:
            result = TaskResult(
                task_id=task.task_id,
                agent_id=self._agent.identity.agent_id,
                success=False,
                output="",
                error=str(exc),
                metrics={},
                artifacts=[],
            )
            self._failed_tasks += 1
            self._transition(SessionStatus.ERROR)

        self._history.append(result)
        if self._status != SessionStatus.ERROR:
            self._transition(SessionStatus.RUNNING)
        return result

    async def pause(self) -> None:
        """Pause the session — agent awaits further input."""
        self._transition(SessionStatus.PAUSED)
        self._emit("session.paused", {"session_id": self.session_id})

    async def resume(self) -> None:
        """Resume a paused session."""
        if self._status == SessionStatus.PAUSED:
            self._transition(SessionStatus.RUNNING)
            self._emit("session.resumed", {"session_id": self.session_id})

    async def shutdown(self) -> None:
        """Graceful shutdown — terminates the underlying agent."""
        self._transition(SessionStatus.TERMINATED)
        try:
            await self._agent.shutdown()
        except Exception:
            pass
        self._emit("session.shutdown", {"session_id": self.session_id})

    # ── Reference counting (winlink indirection) ──────────────────────────

    def acquire(self) -> None:
        """Increment reference count — an observer is watching."""
        self._refcount += 1

    def release(self) -> None:
        """Decrement reference count. Session may be cleaned up at zero."""
        self._refcount = max(0, self._refcount - 1)

    @property
    def refcount(self) -> int:
        return self._refcount

    # ── Snapshot / Restore ────────────────────────────────────────────────

    def snapshot(self) -> SessionSnapshot:
        """Capture current session state for persistence."""
        return SessionSnapshot(
            session_id=self.session_id,
            agent_id=self._agent.identity.agent_id,
            status=self._status,
            lifecycle=self._agent.state.lifecycle,
            health=self._agent.state.health,
            created_at=self._created_at,
            updated_at=self._updated_at,
            task_count=self._task_count,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
            last_output=self._last_output,
            metadata=dict(self._metadata),
            mode_stack=[m.__class__.__name__ for m in self._agent.mode_stack],
        )

    def restore(self, snap: SessionSnapshot) -> None:
        """Restore session metadata from a snapshot (does not restore agent state)."""
        self._task_count = snap.task_count
        self._completed_tasks = snap.completed_tasks
        self._failed_tasks = snap.failed_tasks
        self._last_output = snap.last_output
        self._metadata = dict(snap.metadata)
        self._updated_at = snap.updated_at

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def agent(self) -> AgentProtocol:
        return self._agent

    @property
    def status(self) -> SessionStatus:
        return self._status

    @property
    def identity(self) -> AgentIdentity:
        return self._agent.identity

    @property
    def state(self) -> AgentState:
        return self._agent.state

    @property
    def task_count(self) -> int:
        return self._task_count

    @property
    def success_rate(self) -> float:
        if self._task_count == 0:
            return 1.0
        return self._completed_tasks / self._task_count

    @property
    def history(self) -> list[TaskResult]:
        return list(self._history)

    def summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent_id": self._agent.identity.agent_id,
            "status": self._status.value,
            "color": self._status.color(),
            "task_count": self._task_count,
            "completed": self._completed_tasks,
            "failed": self._failed_tasks,
            "success_rate": self.success_rate,
            "refcount": self._refcount,
            "uptime_s": time.time() - self._created_at,
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _transition(self, new_status: SessionStatus) -> None:
        old = self._status
        self._status = new_status
        self._updated_at = time.time()
        self._emit("session.status_change", {
            "session_id": self.session_id,
            "old": old.value,
            "new": new_status.value,
            "color": new_status.color(),
        })

    def _emit(self, name: str, payload: dict) -> None:
        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name=name,
            origin=__name__,
            payload=payload,
        )
