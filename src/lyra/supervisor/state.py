"""State enumerations and data types for the supervisor daemon."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum


class SessionState(str, Enum):
    """Lifecycle states for an agent session."""

    WORKING = "WORKING"
    IDLE = "IDLE"
    NEEDS_INPUT = "NEEDS_INPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class ProcessState(str, Enum):
    """Runtime states for a session's underlying process."""

    ALIVE = "ALIVE"
    EXITED = "EXITED"
    LOOP_SLEEPING = "LOOP_SLEEPING"


@dataclass(frozen=True)
class SessionInfo:
    """Immutable snapshot of a single session's metadata."""

    session_id: str
    name: str
    state: SessionState
    process_state: ProcessState
    working_dir: str
    created_at: datetime.datetime
    last_active: datetime.datetime
    pr_url: str | None = None
