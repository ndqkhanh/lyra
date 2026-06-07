"""Supervisor daemon — persistent background lifecycle manager for agent sessions."""

from __future__ import annotations

import datetime
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from src.supervisor.state import ProcessState, SessionInfo, SessionState
from src.supervisor.store import SessionStore

_IDLE_TIMEOUT_DEFAULT_MINUTES = 60


class SupervisorDaemon:
    """Manages the lifecycle of background agent sessions.

    Sessions are tracked in-memory and persisted to a SQLite store.
    Idle sessions are automatically stopped after a configurable timeout.
    """

    def __init__(
        self,
        db_path: str | Path = "supervisor.db",
        idle_timeout_minutes: int = _IDLE_TIMEOUT_DEFAULT_MINUTES,
    ) -> None:
        self._idle_timeout = datetime.timedelta(minutes=idle_timeout_minutes)
        self._store = SessionStore(db_path)
        self._store.init_db()
        self._sessions: Dict[str, SessionInfo] = {}
        self._lock = threading.Lock()
        self._load_existing_sessions()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self, name: str, working_dir: str) -> str:
        """Create and register a new session. Returns the session ID."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        session_id = uuid.uuid4().hex[:12]

        info = SessionInfo(
            session_id=session_id,
            name=name,
            state=SessionState.WORKING,
            process_state=ProcessState.ALIVE,
            working_dir=working_dir,
            created_at=now,
            last_active=now,
            pr_url=None,
        )

        with self._lock:
            self._sessions[session_id] = info
            self._store.save_session(info)

        return session_id

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Return the current state of a session, or None if unknown."""
        with self._lock:
            info = self._sessions.get(session_id)
            return info.state if info else None

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Return full metadata for a session, or None."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> List[SessionInfo]:
        """Return an immutable snapshot of all tracked sessions."""
        with self._lock:
            return sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)

    def stop_session(self, session_id: str) -> None:
        """Mark a session as STOPPED."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        with self._lock:
            if session_id not in self._sessions:
                return
            old = self._sessions[session_id]
            info = SessionInfo(
                session_id=old.session_id,
                name=old.name,
                state=SessionState.STOPPED,
                process_state=ProcessState.EXITED,
                working_dir=old.working_dir,
                created_at=old.created_at,
                last_active=now,
                pr_url=old.pr_url,
            )
            self._sessions[session_id] = info
            self._store.update_state(session_id, SessionState.STOPPED, now=now)

    def update_session_state(
        self,
        session_id: str,
        state: SessionState,
        process_state: ProcessState | None = None,
    ) -> None:
        """Update the state (and optionally process state) of a session."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        with self._lock:
            old = self._sessions.get(session_id)
            if old is None:
                return
            info = SessionInfo(
                session_id=old.session_id,
                name=old.name,
                state=state,
                process_state=process_state or old.process_state,
                working_dir=old.working_dir,
                created_at=old.created_at,
                last_active=now,
                pr_url=old.pr_url,
            )
            self._sessions[session_id] = info
            self._store.update_state(session_id, state, now=now)

    def update_pr_url(self, session_id: str, pr_url: str) -> None:
        """Associate a PR URL with a session."""
        with self._lock:
            old = self._sessions.get(session_id)
            if old is None:
                return
            info = SessionInfo(
                session_id=old.session_id,
                name=old.name,
                state=old.state,
                process_state=old.process_state,
                working_dir=old.working_dir,
                created_at=old.created_at,
                last_active=old.last_active,
                pr_url=pr_url,
            )
            self._sessions[session_id] = info
            self._store.save_session(info)

    # ------------------------------------------------------------------
    # Idle management
    # ------------------------------------------------------------------

    def stop_idle_sessions(self) -> List[str]:
        """Stop all sessions that have been idle past the configured timeout.

        Returns the list of stopped session IDs.
        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        stopped: List[str] = []

        with self._lock:
            for sid, info in list(self._sessions.items()):
                if info.state not in (SessionState.WORKING, SessionState.IDLE):
                    continue
                idle_duration = now - info.last_active
                if idle_duration >= self._idle_timeout:
                    updated = SessionInfo(
                        session_id=info.session_id,
                        name=info.name,
                        state=SessionState.STOPPED,
                        process_state=ProcessState.EXITED,
                        working_dir=info.working_dir,
                        created_at=info.created_at,
                        last_active=now,
                        pr_url=info.pr_url,
                    )
                    self._sessions[sid] = updated
                    self._store.update_state(sid, SessionState.STOPPED, now=now)
                    stopped.append(sid)

        return stopped

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_existing_sessions(self) -> None:
        """Rehydrate in-memory state from the persisted store."""
        stored = self._store.list_sessions()
        for info in stored:
            self._sessions[info.session_id] = info

    @property
    def store(self) -> SessionStore:
        """Expose the underlying store for direct queries if needed."""
        return self._store
