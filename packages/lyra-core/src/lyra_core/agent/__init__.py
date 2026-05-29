"""Agent primitives for lyra.

``lyra_core.agent`` provides the canonical run-loop, persistent sessions,
and the agent daemon:

- :class:`AgentLoop` — main ``run_conversation`` loop with plugin seams.
- :class:`AgentSession` — persistent lifecycle wrapper with snapshots.
- :class:`AgentDaemon` — per-user daemon managing session pools.
- :class:`SessionStatus` — coarse-grained status with colored rings.
"""

from __future__ import annotations

from .daemon import AgentDaemon, DaemonConfig, DaemonStatus
from .loop import AgentLoop, IterationBudget, TurnResult
from .session import AgentSession, SessionSnapshot, SessionStatus

__all__ = [
    "AgentDaemon",
    "AgentLoop",
    "AgentSession",
    "DaemonConfig",
    "DaemonStatus",
    "IterationBudget",
    "SessionSnapshot",
    "SessionStatus",
    "TurnResult",
]
