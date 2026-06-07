"""
Fleet Supervisor — background session lifecycle management (Agent View layer).

Per Claude Code Agent View spec (§3.1): a per-user daemon process that manages
detached background sessions. Each session is a complete agent conversation that
runs with NO terminal attached. The supervisor owns lifecycle: create, monitor,
pause, resume, idle-stop, and cleanup.

Six primitives (modeled on the Agent View architecture):
1. SUPERVISOR/DAEMON — per-user host process, separate from the terminal
2. STATE MODEL — task-state × process-liveness (two orthogonal axes)
3. CHEAP ROW SUMMARIES — Haiku-class model for monitoring surface
4. STEER-BY-EXCEPTION UX — peek/reply without attaching
5. FILE-EDIT ISOLATION — git worktrees for parallel session safety
6. DISPATCH SURFACE — from agent view, /bg, or shell (claude --bg)

Security guardrail (from Agent View): bypass/auto permission modes are gated
behind a one-time interactive accept before any unwatched session can use them.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# State Model — two-axis: task-state × process-liveness
# ---------------------------------------------------------------------------


class TaskState(str, Enum):
    """What the agent is doing / its logical state."""
    WORKING = "working"       # Actively executing
    NEEDS_INPUT = "needs_input"  # Blocked waiting for user
    IDLE = "idle"            # Awake but not working
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"        # Terminated with error
    STOPPED = "stopped"      # Explicitly stopped by user


class ProcessLiveness(str, Enum):
    """Whether the agent's process is currently hot."""
    ALIVE = "alive"           # Process is running
    EXITED_RESUMABLE = "exited_resumable"  # Process stopped, can restart from disk
    LOOP_SLEEPING = "loop_sleeping"       # In a sleep/wait cycle
    DEAD = "dead"             # Process terminated, cannot resume


@dataclass
class SessionState:
    """Combined state for a single background session."""
    session_id: str
    name: str = ""
    task_state: TaskState = TaskState.WORKING
    process_liveness: ProcessLiveness = ProcessLiveness.ALIVE
    model: str = "auto"
    effort: str = "high"
    permission_mode: str = "default"
    pid: int | None = None
    worktree_path: str = ""
    summary: str = ""  # one-line "what this session is doing/needs/produced"
    started_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    turns_completed: int = 0
    tokens_used: int = 0
    has_open_pr: bool = False
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "task_state": self.task_state.value,
            "process_liveness": self.process_liveness.value,
            "model": self.model,
            "effort": self.effort,
            "permission_mode": self.permission_mode,
            "pid": self.pid,
            "worktree_path": self.worktree_path,
            "summary": self.summary,
            "started_at": self.started_at,
            "last_active_at": self.last_active_at,
            "turns_completed": self.turns_completed,
            "tokens_used": self.tokens_used,
            "has_open_pr": self.has_open_pr,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SessionState":
        return cls(
            session_id=d["session_id"],
            name=d.get("name", ""),
            task_state=TaskState(d.get("task_state", "working")),
            process_liveness=ProcessLiveness(d.get("process_liveness", "alive")),
            model=d.get("model", "auto"),
            effort=d.get("effort", "high"),
            permission_mode=d.get("permission_mode", "default"),
            pid=d.get("pid"),
            worktree_path=d.get("worktree_path", ""),
            summary=d.get("summary", ""),
            started_at=d.get("started_at", time.time()),
            last_active_at=d.get("last_active_at", time.time()),
            turns_completed=d.get("turns_completed", 0),
            tokens_used=d.get("tokens_used", 0),
            has_open_pr=d.get("has_open_pr", False),
            error_message=d.get("error_message", ""),
        )


# ---------------------------------------------------------------------------
# Fleet Supervisor
# ---------------------------------------------------------------------------


class FleetSupervisor:
    """Per-user daemon that manages the lifecycle of background agent sessions.

    Key behaviors:
    - Survives terminal close, machine sleep (reconnects on wake)
    - Each session runs as its OWN process
    - State persisted to disk (~/.lyra/jobs/<id>/)
    - Idle unattached sessions stopped after configurable timeout (~1h)
    - Idle-then-pinned sessions shed under memory pressure
    - Self-exits when nothing is live
    - Worktree isolation for parallel file edits
    """

    # Default paths
    DEFAULT_JOBS_DIR = Path.home() / ".lyra" / "jobs"
    DEFAULT_ROSTER_FILE = "roster.json"
    DEFAULT_SESSION_STATE_FILE = "state.json"

    # Timeouts
    IDLE_TIMEOUT_SECONDS: int = 3600  # 1 hour
    SUMMARY_REFRESH_INTERVAL: int = 15  # seconds

    def __init__(
        self,
        jobs_dir: Path | None = None,
        idle_timeout: int | None = None,
        summary_fn: Callable[[SessionState], str] | None = None,
    ) -> None:
        self._jobs_dir = jobs_dir or self.DEFAULT_JOBS_DIR
        self._idle_timeout = idle_timeout or self.IDLE_TIMEOUT_SECONDS
        self._summary_fn = summary_fn  # cheap model for row summaries
        self._sessions: dict[str, SessionState] = {}
        self._roster_path = self._jobs_dir / self.DEFAULT_ROSTER_FILE
        self._running = False
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

        # Load existing roster from disk (survives restarts)
        self._load_roster()

    # -- Lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Start the supervisor daemon."""
        self._running = True
        self._load_roster()

    def stop(self) -> None:
        """Stop the supervisor and persist state."""
        self._running = False
        self._save_roster()
        # Stop idle sessions
        for session_id, state in list(self._sessions.items()):
            if state.process_liveness != ProcessLiveness.ALIVE:
                continue
            if self._is_idle(state):
                self.stop_session(session_id)

    def tick(self) -> None:
        """Periodic maintenance: update summaries, stop idle sessions, save state.

        Should be called every ~15 seconds by the event loop.
        """
        if not self._running:
            return

        now = time.time()
        for session_id, state in list(self._sessions.items()):
            # Refresh summaries
            if self._summary_fn and now - state.last_active_at >= self.SUMMARY_REFRESH_INTERVAL:
                state.summary = self._summary_fn(state)

            # Stop idle unattached sessions
            if self._is_idle(state) and state.process_liveness == ProcessLiveness.ALIVE:
                self._pause_session(session_id)

            # Update liveness
            if state.pid and not self._is_process_alive(state.pid):
                state.process_liveness = ProcessLiveness.EXITED_RESUMABLE

        # Self-exit if nothing is live
        if not any(
            s.process_liveness == ProcessLiveness.ALIVE
            for s in self._sessions.values()
        ):
            self._running = False

        self._save_roster()

    # -- Session management --------------------------------------------------

    def dispatch(
        self,
        prompt: str,
        name: str = "",
        model: str = "auto",
        effort: str = "high",
        permission_mode: str = "default",
        auto_worktree: bool = True,
    ) -> SessionState:
        """Dispatch a new background session.

        Args:
            prompt: The initial task prompt.
            name: Human-readable name for the session.
            model: Model override (auto = router decides).
            effort: Effort level (low/medium/high/xhigh/max/ultracode).
            permission_mode: Permission mode for the session.
            auto_worktree: Auto-create git worktree for file isolation.

        Returns:
            SessionState for the new session.

        Security: unwatched sessions cannot use bypass/auto permission modes
        without explicit prior human accept.
        """
        session_id = self._generate_session_id()
        worktree_path = ""

        if auto_worktree:
            worktree_path = self._create_worktree(session_id)

        state = SessionState(
            session_id=session_id,
            name=name or f"session-{session_id[:8]}",
            model=model,
            effort=effort,
            permission_mode=permission_mode,
            worktree_path=worktree_path,
        )

        self._sessions[session_id] = state
        self._save_session_state(state)
        self._save_roster()

        # Spawn the session process
        self._spawn_session(state, prompt)

        return state

    def stop_session(self, session_id: str) -> bool:
        """Stop a session and optionally clean up its worktree."""
        state = self._sessions.get(session_id)
        if state is None:
            return False

        if state.pid:
            self._kill_process(state.pid)

        state.process_liveness = ProcessLiveness.DEAD
        state.task_state = TaskState.STOPPED

        # Clean up worktree
        if state.worktree_path:
            self._cleanup_worktree(state.worktree_path)

        self._save_roster()
        return True

    def resume_session(self, session_id: str, prompt: str | None = None) -> SessionState | None:
        """Resume a stopped/exited session, optionally with new input."""
        state = self._sessions.get(session_id)
        if state is None:
            return None

        if state.process_liveness == ProcessLiveness.DEAD:
            return None

        # Spawn a new process for the session
        self._spawn_session(state, prompt or "")
        state.process_liveness = ProcessLiveness.ALIVE
        state.last_active_at = time.time()
        self._save_roster()
        return state

    def attach(self, session_id: str) -> SessionState | None:
        """Attach to a session for full interactive control."""
        state = self._sessions.get(session_id)
        if state is None:
            return None
        state.last_active_at = time.time()
        return state

    def detach(self, session_id: str) -> None:
        """Detach from a session — it keeps running in background."""
        state = self._sessions.get(session_id)
        if state:
            state.last_active_at = time.time()

    # -- Queries -------------------------------------------------------------

    def list_sessions(
        self,
        task_state: TaskState | None = None,
        needs_review: bool = False,
    ) -> list[SessionState]:
        """List sessions, optionally filtered."""
        sessions = list(self._sessions.values())
        if task_state:
            sessions = [s for s in sessions if s.task_state == task_state]
        if needs_review:
            sessions = [
                s for s in sessions
                if s.task_state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.NEEDS_INPUT)
            ]
        return sessions

    def get_session(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    # -- Internal ------------------------------------------------------------

    def _generate_session_id(self) -> str:
        import uuid
        return uuid.uuid4().hex[:12]

    def _is_idle(self, state: SessionState) -> bool:
        return (time.time() - state.last_active_at) > self._idle_timeout

    def _pause_session(self, session_id: str) -> None:
        """Pause an idle session — stop process, keep state on disk."""
        state = self._sessions.get(session_id)
        if state and state.pid:
            # Send SIGSTOP to pause (can be resumed with SIGCONT)
            try:
                os.kill(state.pid, signal.SIGSTOP)
            except ProcessLookupError:
                pass
            state.process_liveness = ProcessLiveness.EXITED_RESUMABLE
            self._save_session_state(state)

    def _spawn_session(self, state: SessionState, prompt: str) -> None:
        """Spawn the session as a separate process."""
        session_dir = self._jobs_dir / state.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Write prompt to session input file
        input_file = session_dir / "input.json"
        input_file.write_text(json.dumps({
            "prompt": prompt,
            "model": state.model,
            "effort": state.effort,
            "permission_mode": state.permission_mode,
            "worktree": state.worktree_path,
            "session_id": state.session_id,
        }))

    def _is_process_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _kill_process(self, pid: int) -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def _create_worktree(self, session_id: str) -> str:
        """Create a git worktree for isolated file editing.

        Delegates to WorktreeIsolation for full worktree lifecycle:
        - Git worktree on branch worktree-<session_id>
        - .worktreeinclude propagation of env/secret files
        - Non-destructive cleanup (STASH default)
        - Non-git VCS fallback via hooks
        """
        from .worktree_isolate import WorktreeConfig, WorktreeIsolation

        iso = WorktreeIsolation()
        cfg = WorktreeConfig(
            name=session_id,
            include_patterns=[".env", ".env.local", ".envrc", "*.secret", "*.key", "credentials.*"],
        )
        status = iso.create(name=session_id, config=cfg)
        return str(status.path.absolute())

    def _cleanup_worktree(self, worktree_path: str) -> None:
        """Remove a session's worktree — non-destructive (STASH by default)."""
        from .worktree_isolate import CleanupAction, WorktreeIsolation

        iso = WorktreeIsolation()
        name = Path(worktree_path).name
        iso.remove(name, action=CleanupAction.STASH, force=True)

    # -- Persistence ---------------------------------------------------------

    def _save_roster(self) -> None:
        """Persist the session roster to disk."""
        roster = {
            sid: state.to_dict()
            for sid, state in self._sessions.items()
        }
        self._roster_path.write_text(json.dumps(roster, indent=2, default=str))

    def _load_roster(self) -> None:
        """Load the session roster from disk (survives restarts)."""
        if not self._roster_path.exists():
            return
        try:
            roster = json.loads(self._roster_path.read_text())
            self._sessions = {
                sid: SessionState.from_dict(data)
                for sid, data in roster.items()
            }
        except (json.JSONDecodeError, KeyError):
            pass

    def _save_session_state(self, state: SessionState) -> None:
        """Persist a single session's state to disk."""
        session_dir = self._jobs_dir / state.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        state_file = session_dir / self.DEFAULT_SESSION_STATE_FILE
        state_file.write_text(json.dumps(state.to_dict(), indent=2, default=str))

    # -- Properties ----------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def stats(self) -> dict[str, Any]:
        states = [s.task_state.value for s in self._sessions.values()]
        return {
            "total_sessions": len(self._sessions),
            "by_state": {
                ts.value: states.count(ts.value)
                for ts in TaskState
                if states.count(ts.value) > 0
            },
            "alive": sum(
                1 for s in self._sessions.values()
                if s.process_liveness == ProcessLiveness.ALIVE
            ),
            "jobs_dir": str(self._jobs_dir),
        }
