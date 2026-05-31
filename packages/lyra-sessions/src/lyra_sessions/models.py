"""Session data models."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class SessionConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    effort_level: str = "high"
    orchestration_enabled: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    id: str
    session_id: str
    name: str
    created_at: float = field(default_factory=time.time)
    message_count: int = 0
    token_count: int = 0
    git_sha: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    id: str
    status: SessionStatus = SessionStatus.ACTIVE
    config: SessionConfig = field(default_factory=SessionConfig)
    checkpoints: list[Checkpoint] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    parent_session_id: str = ""
    branch_name: str = ""
