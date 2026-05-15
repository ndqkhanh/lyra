"""Core routine types — Routine, RoutineFire, RoutineHandler Protocol."""
from __future__ import annotations

import enum
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


class TriggerKind(str, enum.Enum):
    """How a routine fire was triggered."""

    CRON = "cron"
    API = "api"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class RoutineHandler(Protocol):
    """Callable signature for a routine handler.

    Production wires :class:`harness_core.orchestration.PureFunctionAgent`
    policies; tests use deterministic stubs.
    """

    def __call__(self, *, fire: "RoutineFire") -> Any: ...


def _generate_token(prefix: str = "rt") -> str:
    """Generate a per-routine bearer token. Cryptographically random."""
    return f"{prefix}-{secrets.token_urlsafe(24)}"


@dataclass(frozen=True)
class Routine:
    """A registered routine — handler + schedule + auth + permissions.

    Token equality is the primary auth check; permissions gate what the
    handler may do (compose with :mod:`harness_core.isolation` /
    :mod:`harness_core.permissions`).
    """

    routine_id: str
    name: str
    handler: RoutineHandler
    schedule: Optional[str] = None  # cron expression; None = manual/api/webhook
    permissions: frozenset[str] = frozenset()
    bearer_token: str = field(default_factory=_generate_token)
    enabled: bool = True
    note: str = ""

    def __post_init__(self) -> None:
        if not self.routine_id or not self.routine_id.strip():
            raise ValueError("routine_id must be non-empty")
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.bearer_token:
            raise ValueError("bearer_token must be non-empty")

    def authenticates(self, presented_token: str) -> bool:
        """Constant-time compare of bearer tokens."""
        return secrets.compare_digest(self.bearer_token, presented_token)


@dataclass(frozen=True)
class RoutineFire:
    """One fire of a routine — isolated context, replayable.

    The ``context`` is per-fire and not shared with other fires of the same
    routine. ``namespace_id`` lets the host harness wire an
    :class:`harness_core.isolation.IsolatedContext` keyed by ``fire_id``.
    """

    fire_id: str
    routine_id: str
    triggered_by: TriggerKind
    triggered_at: float
    payload: dict[str, Any] = field(default_factory=dict)
    namespace_id: str = ""

    def __post_init__(self) -> None:
        if not self.fire_id:
            raise ValueError("fire_id must be non-empty")
        if not self.routine_id:
            raise ValueError("routine_id must be non-empty")
        if self.triggered_at < 0:
            raise ValueError(f"triggered_at must be >= 0, got {self.triggered_at}")
        # Default namespace_id to fire_id if not set; satisfied here without
        # reassignment because the dataclass is frozen — caller passes both.

    @property
    def isolation_key(self) -> str:
        """Stable key for an isolation namespace; defaults to fire_id."""
        return self.namespace_id or self.fire_id


__all__ = ["Routine", "RoutineFire", "RoutineHandler", "TriggerKind"]
