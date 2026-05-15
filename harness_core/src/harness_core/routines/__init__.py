"""harness_core.routines — scheduled-trigger primitives for self-hosted agents.

Per the README's Files **252** (Routines pattern for self-hosted agents) — four
reusable primitives extracted from Anthropic's Routines:

    1. Server-side config — versioned routine definitions in a registry.
    2. Trigger ingresses — cron, API, webhook (any source signs a fire).
    3. Isolated execution per fire — each fire gets a fresh context object.
    4. Per-routine bearer tokens — auth scoped to a single routine.

Composes with:
    - :mod:`harness_core.isolation` — each fire's context is an
      :class:`harness_core.isolation.IsolatedContext` namespaced by fire id.
    - :mod:`harness_core.orchestration` — handlers can be
      :class:`PureFunctionAgent` policies; fires are replayable.
    - :mod:`harness_core.evals` — fire-level token budgets via
      :class:`BudgetController`.

Used by Aegis-Ops (cron runbooks), Mentat-Learn (per-channel reminders),
Polaris (heartbeat schedule per [docs/172] §3 Gap 4), Lyra (background
indexing), Cipher-Sec (continuous CVE checks), and any other in-tree agent
that needs scheduled execution.
"""
from __future__ import annotations

from .cron import CronExpression, CronParseError, parse_cron, next_fire_after
from .registry import (
    FireResult,
    RoutineRegistry,
)
from .types import (
    Routine,
    RoutineFire,
    RoutineHandler,
    TriggerKind,
)

__all__ = [
    "CronExpression",
    "CronParseError",
    "FireResult",
    "Routine",
    "RoutineFire",
    "RoutineHandler",
    "RoutineRegistry",
    "TriggerKind",
    "next_fire_after",
    "parse_cron",
]
