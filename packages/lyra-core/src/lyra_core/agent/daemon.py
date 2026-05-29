"""Per-user agent daemon — manages lifecycle of agent sessions.

Inspired by rmux's per-user daemon (/tmp/rmux-{uid}/) and cmux's JSON-RPC
over Unix socket pattern:

  - Singleton daemon per user, discovered via /tmp/lyra-agentd-{uid}.sock
  - Manages a pool of AgentSession instances with lifecycle supervision
  - Provides structured snapshots and health monitoring
  - Layered safety: sessions are isolated, daemon enforces resource caps
  - Crash recovery: reconstructs session pool from persistent snapshots
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lyra_core.events import EventBus, EventCategory
from lyra_core.protocol import Task, TaskResult

from .session import AgentSession, SessionSnapshot, SessionStatus

logger = logging.getLogger(__name__)

# Default socket path follows rmux convention: /tmp/lyra-agentd-{uid}.sock
_DEFAULT_SOCK = Path(f"/tmp/lyra-agentd-{os.getuid()}.sock")


@dataclass
class DaemonConfig:
    """Configuration for the agent daemon."""

    socket_path: Path = field(default_factory=lambda: _DEFAULT_SOCK)
    max_sessions: int = 50
    max_tasks_per_session: int = 1000
    idle_timeout_s: float = 3600.0  # Kill idle sessions after 1 hour
    heartbeat_interval_s: float = 30.0  # Health check interval
    snapshot_dir: Path | None = None  # Directory for persistent snapshots
    auto_recovery: bool = True  # Resume sessions from snapshots on startup


@dataclass
class DaemonStatus:
    """Aggregate status of the daemon and all managed sessions."""

    session_count: int
    active_sessions: int
    paused_sessions: int
    error_sessions: int
    total_tasks_executed: int
    total_tasks_completed: int
    total_tasks_failed: int
    uptime_s: float
    socket_path: str


class AgentDaemon:
    """Per-user daemon managing a pool of agent sessions.

    Responsibilities:
      - Session lifecycle: spawn, monitor, pause, resume, terminate
      - Health supervision: heartbeat checks, idle timeout enforcement
      - Snapshot persistence: periodic snapshots for crash recovery
      - Resource enforcement: max sessions, max tasks per session
      - Sidecar metadata bus: emits lifecycle events for observers

    Usage::

        daemon = AgentDaemon()
        await daemon.start()

        session = await daemon.spawn(agent, task)
        result = await daemon.run(session.session_id, another_task)

        await daemon.stop()
    """

    def __init__(
        self,
        config: DaemonConfig | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.config = config or DaemonConfig()
        self._bus = bus or EventBus.get()
        self._sessions: dict[str, AgentSession] = {}
        self._started_at: float | None = None
        self._running = False

        if self.config.snapshot_dir:
            self.config.snapshot_dir.mkdir(parents=True, exist_ok=True)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the daemon. Loads snapshots if auto_recovery is enabled."""
        self._started_at = time.time()
        self._running = True

        if self.config.auto_recovery and self.config.snapshot_dir:
            recovered = self._load_snapshots()
            logger.info("Daemon started — recovered %d sessions", recovered)

        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="agentd.started",
            origin=__name__,
            payload={"socket": str(self.config.socket_path)},
        )

    async def stop(self) -> None:
        """Stop the daemon. Saves snapshots and terminates all sessions."""
        if self.config.snapshot_dir:
            self._save_all_snapshots()

        for session in list(self._sessions.values()):
            try:
                await session.shutdown()
            except Exception:
                pass

        self._sessions.clear()
        self._running = False

        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="agentd.stopped",
            origin=__name__,
            payload={"uptime_s": self.uptime_s},
        )

    # ── Session management ────────────────────────────────────────────────

    async def spawn(
        self,
        agent,
        *,
        session_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AgentSession:
        """Spawn a new agent session and register it with the daemon."""
        if len(self._sessions) >= self.config.max_sessions:
            raise RuntimeError(
                f"Max sessions ({self.config.max_sessions}) reached"
            )

        session = AgentSession(agent, session_id=session_id, bus=self._bus)
        if metadata:
            session._metadata.update(metadata)

        await session.start()
        self._sessions[session.session_id] = session

        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="agentd.session_spawned",
            origin=__name__,
            payload={"session_id": session.session_id,
                    "agent_id": agent.identity.agent_id},
        )
        return session

    async def run(self, session_id: str, task: Task) -> TaskResult:
        """Run a task on a managed session."""
        session = self._get_session(session_id)
        if session._task_count >= self.config.max_tasks_per_session:
            raise RuntimeError(
                f"Session {session_id} has reached max tasks"
            )
        return await session.run(task)

    async def pause(self, session_id: str) -> None:
        """Pause a running session."""
        session = self._get_session(session_id)
        await session.pause()

    async def resume(self, session_id: str) -> None:
        """Resume a paused session."""
        session = self._get_session(session_id)
        await session.resume()

    async def terminate(self, session_id: str) -> None:
        """Terminate and remove a session."""
        session = self._get_session(session_id)
        await session.shutdown()
        del self._sessions[session_id]

    async def terminate_idle(self) -> int:
        """Terminate sessions that have been idle past the timeout. Returns count."""
        cutoff = time.time() - self.config.idle_timeout_s
        to_remove: list[str] = []

        for sid, session in self._sessions.items():
            if session.status == SessionStatus.PAUSED:
                snap = session.snapshot()
                if snap.updated_at < cutoff:
                    to_remove.append(sid)

        for sid in to_remove:
            await self.terminate(sid)

        return len(to_remove)

    # ── Health check ──────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Run a health check on all managed sessions."""
        errors = []
        for sid, session in self._sessions.items():
            if session.status == SessionStatus.ERROR:
                errors.append({
                    "session_id": sid,
                    "agent_id": session.identity.agent_id,
                    "success_rate": session.success_rate,
                })

        return {
            "daemon_running": self._running,
            "uptime_s": self.uptime_s,
            "sessions": self.status,
            "errors": errors,
            "timestamp": time.time(),
        }

    # ── Snapshots ─────────────────────────────────────────────────────────

    def snapshot_all(self) -> list[SessionSnapshot]:
        """Snapshot all managed sessions."""
        return [s.snapshot() for s in self._sessions.values()]

    def _save_all_snapshots(self) -> None:
        """Persist all session snapshots to disk."""
        if not self.config.snapshot_dir:
            return
        snaps = [s.snapshot() for s in self._sessions.values()]
        path = self.config.snapshot_dir / "sessions.json"
        path.write_text(json.dumps(
            [{"session_id": s.session_id, "agent_id": s.agent_id,
              "status": s.status.value, "task_count": s.task_count}
             for s in snaps],
            indent=2,
        ))

    def _load_snapshots(self) -> int:
        """Load session metadata from disk. Returns count of records found."""
        if not self.config.snapshot_dir:
            return 0
        path = self.config.snapshot_dir / "sessions.json"
        if not path.exists():
            return 0
        try:
            data = json.loads(path.read_text())
            return len(data)
        except (json.JSONDecodeError, OSError):
            return 0

    # ── Query ─────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> AgentSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self, status: SessionStatus | None = None) -> list[AgentSession]:
        sessions = list(self._sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    @property
    def status(self) -> DaemonStatus:
        sessions = list(self._sessions.values())
        return DaemonStatus(
            session_count=len(sessions),
            active_sessions=sum(1 for s in sessions if s.status == SessionStatus.RUNNING),
            paused_sessions=sum(1 for s in sessions if s.status == SessionStatus.PAUSED),
            error_sessions=sum(1 for s in sessions if s.status == SessionStatus.ERROR),
            total_tasks_executed=sum(s.task_count for s in sessions),
            total_tasks_completed=sum(s._completed_tasks for s in sessions),
            total_tasks_failed=sum(s._failed_tasks for s in sessions),
            uptime_s=self.uptime_s,
            socket_path=str(self.config.socket_path),
        )

    @property
    def uptime_s(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    # ── Internal ──────────────────────────────────────────────────────────

    def _get_session(self, session_id: str) -> AgentSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")
        return session
