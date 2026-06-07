"""Supervisor daemon — persistent background lifecycle manager for agent sessions."""

from __future__ import annotations

import datetime
import logging
import math
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from lyra.supervisor.state import ProcessState, SessionInfo, SessionState
from lyra.supervisor.store import SessionStore

logger = logging.getLogger(__name__)

_IDLE_TIMEOUT_DEFAULT_MINUTES = 60


# ---------------------------------------------------------------------------
# Health dashboard types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DaemonHealth:
    """Snapshot of the supervisor daemon's health.

    Attributes:
        uptime_seconds: Seconds since the daemon started.
        session_count: Total number of tracked sessions.
        active_session_count: Number of WORKING or IDLE sessions.
        error_rate: Errors per minute in the recent window.
        memory_usage_mb: Current RSS memory usage in MB.
        cpu_percent: Approximate CPU utilisation.
        restart_backoff_sessions: Sessions currently in restart back-off.
        session_states: Breakdown of session counts by state.
        details: Additional key-value diagnostics.
    """

    uptime_seconds: float
    session_count: int
    active_session_count: int
    error_rate: float
    memory_usage_mb: float
    cpu_percent: float
    restart_backoff_sessions: int
    session_states: dict[str, int] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionSummary:
    """One-line summary of a single session.

    Used by :meth:`cheap_model_summaries` to produce lightweight status
    lines suitable for dashboard display.

    Attributes:
        session_id: The session identifier.
        name: Human-readable session name.
        state: Current lifecycle state.
        process_state: Current process state.
        summary: One-line human-readable description of session status.
    """

    session_id: str
    name: str
    state: str
    process_state: str
    summary: str


# ---------------------------------------------------------------------------
# SupervisorDaemon (enhanced)
# ---------------------------------------------------------------------------


class SupervisorDaemon:
    """Manages the lifecycle of background agent sessions.

    Sessions are tracked in-memory and persisted to a SQLite store.
    Idle sessions are automatically stopped after a configurable timeout.
    Provides health dashboard metrics, cheap model summaries, and
    auto-restart of failed sessions with exponential backoff.
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

        # Health dashboard internals
        self._start_time: float = time.time()
        self._error_timestamps: list[float] = []
        self._error_lock = threading.Lock()

        # Auto-restart state
        self._restart_backoff: dict[str, RestartState] = {}
        self._restart_lock = threading.Lock()
        self._on_restart: Callable[[str], Any] | None = None

        # Summary generators (cheap model summaries hook)
        self._summary_generators: list[Callable[[SessionInfo], str | None]] = []

    # ── Session lifecycle ─────────────────────────────────────────────

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
            return sorted(
                self._sessions.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )

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

        # Clear restart backoff on manual stop
        with self._restart_lock:
            self._restart_backoff.pop(session_id, None)

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

    # ── Idle management ───────────────────────────────────────────────

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

    # ── Health dashboard integration ───────────────────────────────────
    # ── daemon_status() ────────────────────────────────────────────────

    def daemon_status(self) -> DaemonHealth:
        """Return a comprehensive health snapshot of the supervisor daemon.

        Aggregates session counts, resource usage, error rate, and backoff
        state into a single :class:`DaemonHealth` dataclass.

        Returns:
            A DaemonHealth snapshot.
        """
        uptime = time.time() - self._start_time

        with self._lock:
            session_count = len(self._sessions)
            active_count = sum(
                1 for info in self._sessions.values()
                if info.state in (SessionState.WORKING, SessionState.IDLE)
            )
            state_counts: dict[str, int] = {}
            for info in self._sessions.values():
                state_counts[info.state.value] = state_counts.get(info.state.value, 0) + 1

        with self._error_lock:
            error_rate = self._compute_error_rate()

        memory_mb = self._get_memory_mb()
        cpu_pct = self._get_cpu_percent()

        with self._restart_lock:
            backoff_count = len(self._restart_backoff)

        return DaemonHealth(
            uptime_seconds=uptime,
            session_count=session_count,
            active_session_count=active_count,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
            cpu_percent=cpu_pct,
            restart_backoff_sessions=backoff_count,
            session_states=state_counts,
            details={
                "idle_timeout_minutes": int(self._idle_timeout.total_seconds() / 60),
                "db_path": str(self._store._db_path),
            },
        )

    def record_error(self) -> None:
        """Record an error occurrence for error rate tracking."""
        with self._error_lock:
            self._error_timestamps.append(time.time())

    # ── Cheap model summaries ──────────────────────────────────────────

    def register_summary_generator(
        self,
        generator: Callable[[SessionInfo], str | None],
    ) -> None:
        """Register a callback that produces one-line session summaries.

        Each generator receives a :class:`SessionInfo` and should return
        a short string (e.g. ``"Idle for 12m"``) or ``None`` to defer to
        the next generator.  Generators are tried in registration order.

        This is the hook point for a Haiku-based summary: register a
        lambda/callable that invokes the cheap model and returns the
        one-line result.

        Args:
            generator: A callable ``(SessionInfo) -> str | None``.
        """
        self._summary_generators.append(generator)

    def cheap_model_summaries(self) -> list[SessionSummary]:
        """Produce one-line status summaries for every tracked session.

        Iterates registered summary generators for each session.  Falls
        back to a built-in rule-based summary when no generator produces
        a result.

        Returns:
            A list of :class:`SessionSummary` objects, one per session.
        """
        results: list[SessionSummary] = []

        with self._lock:
            sessions = list(self._sessions.values())

        for info in sessions:
            summary: str | None = None

            # Try registered generators first
            for gen in self._summary_generators:
                try:
                    result = gen(info)
                    if result is not None:
                        summary = result
                        break
                except Exception:
                    logger.debug("Summary generator failed for session '%s'", info.session_id)

            # Fallback: rule-based summary
            if summary is None:
                summary = self._default_summary(info)

            results.append(SessionSummary(
                session_id=info.session_id,
                name=info.name,
                state=info.state.value,
                process_state=info.process_state.value,
                summary=summary,
            ))

        return results

    # ── Auto-restart with exponential backoff ──────────────────────────

    def set_restart_handler(self, handler: Callable[[str], Any]) -> None:
        """Set the callback invoked when a session is auto-restarted.

        The handler receives the session ID and is expected to re-spawn
        or restart the agent process.

        Args:
            handler: A callable ``(session_id: str) -> Any``.
        """
        self._on_restart = handler

    def auto_restart_failed_sessions(self) -> list[str]:
        """Attempt to restart sessions that have FAILED.

        Uses exponential backoff: first retry after 1s, then 2s, 4s, 8s,
        up to a maximum of 300s (5 minutes).  A successful restart clears
        the backoff state.

        Returns:
            List of session IDs that were successfully restarted.
        """
        now = time.time()
        restarted: list[str] = []

        with self._lock:
            failed_session_ids = [
                sid
                for sid, info in self._sessions.items()
                if info.state == SessionState.FAILED
            ]

        for sid in failed_session_ids:
            should_restart, backoff = self._check_restart_eligibility(sid, now)
            if not should_restart:
                continue

            # Attempt restart via handler
            if self._on_restart is not None:
                try:
                    result = self._on_restart(sid)
                    import asyncio
                    if asyncio.iscoroutine(result):
                        # Cannot await here; handler should handle async internally
                        logger.warning(
                            "Restart handler returned coroutine for session '%s'; "
                            "use a synchronous handler or fire-and-forget.",
                            sid,
                        )
                    restarted.append(sid)

                    # Update session state back to WORKING
                    self.update_session_state(
                        sid,
                        SessionState.WORKING,
                        process_state=ProcessState.ALIVE,
                    )

                    # Record restart and schedule next backoff
                    with self._restart_lock:
                        backoff._attempt += 1
                        backoff._last_attempt = now
                        backoff._next_retry = now + backoff.backoff_delay(backoff._max_delay)
                        self._restart_backoff[sid] = backoff

                    logger.info(
                        "Auto-restarted session '%s' (attempt %d, next in %.0fs)",
                        sid,
                        backoff._attempt,
                        backoff._next_retry - now,
                    )

                except Exception:
                    logger.exception("Auto-restart handler failed for session '%s'", sid)
                    self.record_error()
            else:
                logger.debug(
                    "No restart handler set; cannot auto-restart session '%s'",
                    sid,
                )

        # Clean up backoff entries for sessions that are no longer FAILED
        self._prune_restart_backoff()

        return restarted

    def restart_backoff_status(self) -> dict[str, dict[str, Any]]:
        """Return the current restart backoff state for all sessions.

        Returns:
            Dict mapping session ID to backoff details.
        """
        now = time.time()
        with self._restart_lock:
            return {
                sid: {
                    "attempt": rs._attempt,
                    "last_attempt": rs._last_attempt,
                    "next_retry": rs._next_retry,
                    "seconds_until_retry": max(0.0, rs._next_retry - now),
                    "current_delay": rs.backoff_delay(rs._max_delay),
                    "max_delay": rs._max_delay,
                }
                for sid, rs in self._restart_backoff.items()
            }

    # ── Internal helpers ───────────────────────────────────────────────

    def _load_existing_sessions(self) -> None:
        """Rehydrate in-memory state from the persisted store."""
        stored = self._store.list_sessions()
        for info in stored:
            self._sessions[info.session_id] = info

    # ── Health helpers ─────────────────────────────────────────────────

    def _compute_error_rate(self, window_seconds: int = 300) -> float:
        """Return errors per minute in the recent time window."""
        cutoff = time.time() - window_seconds
        recent = [t for t in self._error_timestamps if t > cutoff]
        if not recent:
            return 0.0
        return len(recent) / (window_seconds / 60.0)

    def _get_memory_mb(self) -> float:
        """Return approximate RSS memory usage in MB."""
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            rss_bytes = (
                usage.ru_maxrss / 1024.0
                if os.uname().sysname == "Darwin"
                else usage.ru_maxrss
            )
            return rss_bytes / 1024.0
        except (ImportError, AttributeError, OSError):
            try:
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            return float(parts[1]) / 1024  # kB -> MB
            except OSError:
                pass
            return 0.0

    def _get_cpu_percent(self) -> float:
        """Return approximate CPU utilisation percentage."""
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            uptime = max(time.time() - self._start_time, 0.01)
            total_cpu = usage.ru_utime + usage.ru_stime
            return min((total_cpu / uptime) * 100.0, 100.0)
        except (ImportError, AttributeError):
            return 0.0

    # ── Summary helpers ────────────────────────────────────────────────

    @staticmethod
    def _default_summary(info: SessionInfo) -> str:
        """Built-in rule-based summary fallback."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        idle_minutes = (now - info.last_active).total_seconds() / 60.0

        if info.state == SessionState.WORKING:
            if idle_minutes < 1:
                return "Active"
            return f"Active (idle {idle_minutes:.0f}m)"
        if info.state == SessionState.IDLE:
            return f"Idle for {idle_minutes:.0f}m"
        if info.state == SessionState.STOPPED:
            return "Stopped"
        if info.state == SessionState.FAILED:
            return "Failed"
        if info.state == SessionState.COMPLETED:
            return "Completed"
        if info.state == SessionState.NEEDS_INPUT:
            return f"Waiting for input ({idle_minutes:.0f}m)"
        return info.state.value

    # ── Restart helpers ────────────────────────────────────────────────

    def _check_restart_eligibility(
        self,
        session_id: str,
        now: float,
    ) -> tuple[bool, RestartState]:
        """Check whether a session is eligible for restart.

        Returns:
            (eligible, backoff_state) tuple.
        """
        with self._restart_lock:
            backoff = self._restart_backoff.get(session_id)
            if backoff is None:
                # First attempt
                backoff = RestartState(
                    _attempt=0,
                    _last_attempt=0.0,
                    _next_retry=now,
                    _max_delay=300.0,
                )
                self._restart_backoff[session_id] = backoff
                return True, backoff

            if now >= backoff._next_retry:
                return True, backoff

            return False, backoff

    def _prune_restart_backoff(self) -> None:
        """Remove backoff entries for sessions that are no longer FAILED."""
        with self._lock, self._restart_lock:
            for sid in list(self._restart_backoff.keys()):
                info = self._sessions.get(sid)
                if info is None or info.state != SessionState.FAILED:
                    self._restart_backoff.pop(sid, None)

    @property
    def store(self) -> SessionStore:
        """Expose the underlying store for direct queries if needed."""
        return self._store


# ---------------------------------------------------------------------------
# RestartState — exponential backoff tracker
# ---------------------------------------------------------------------------


@dataclass
class RestartState:
    """Tracks exponential backoff for a single session.

    Attributes:
        _attempt: Number of restart attempts so far.
        _last_attempt: Timestamp of the last restart attempt.
        _next_retry: Earliest timestamp at which the next restart is allowed.
        _max_delay: Maximum delay between retries in seconds.
    """

    _attempt: int = 0
    _last_attempt: float = 0.0
    _next_retry: float = 0.0
    _max_delay: float = 300.0  # 5 minutes

    def backoff_delay(self, max_delay: float | None = None) -> float:
        """Compute the delay for the current attempt using exponential backoff.

        Delay = min(base * 2^attempt, max_delay), where base = 1 second.

        Args:
            max_delay: Override the maximum delay. Uses instance default if None.

        Returns:
            Delay in seconds.
        """
        max_d = max_delay if max_delay is not None else self._max_delay
        base = 1.0
        delay = base * (2 ** self._attempt)
        return min(delay, max_d)
