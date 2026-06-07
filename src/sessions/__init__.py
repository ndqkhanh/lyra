"""
Session persistence — SQLite-backed save/restore for agent sessions.
"""

from src.sessions.persist import SessionManager, SessionRecord, SessionStatus

__version__ = "0.1.0"

__all__ = [
    "SessionManager",
    "SessionRecord",
    "SessionStatus",
]
