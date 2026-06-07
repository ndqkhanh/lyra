"""
Supervisor — Persistent background daemon for managing agent sessions.

Tracks session state, enforces idle timeouts, persists state to SQLite,
and provides a fleet-view of all sessions.
"""

from src.supervisor.daemon import SupervisorDaemon
from src.supervisor.state import ProcessState, SessionInfo, SessionState

__all__ = [
    "SupervisorDaemon",
    "SessionState",
    "ProcessState",
    "SessionInfo",
]
