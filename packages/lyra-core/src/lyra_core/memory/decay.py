"""Ebbinghaus-style decay + access-strengthening (steal from agentmemory).

Pure functions, zero side-effects. Memory layers compose them in their
own retrieve paths so the decay knobs stay configurable per-substore.

Two ideas, both lifted from agentmemory's lifecycle layer:

1. **Forgetting curve** — older memories should rank below fresher ones,
   all else equal. We use exponential decay with a per-kind half-life.
2. **Access-strengthening** — frequently-accessed memories should
   resist decay. We add a bounded log-scaled boost for ``access_count``.

The combined score is::

    decay = exp(-(now - last_accessed_ts) / half_life)
    boost = 1 + log1p(access_count) / log(1 + access_saturation)
    weighted = base_score * decay * boost

``access_saturation`` caps the strengthening contribution so a hot
record doesn't drown out a fresh-but-rarely-recalled one. Default 50:
above that, the boost plateaus.

Per-kind half-lives default to:

    user / project    → ∞ (no decay)
    feedback          → 7 days
    reference         → 30 days

These are knobs, not laws. Callers may pass any half-life dict.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass


# Per-MemoryKind half-life defaults (seconds). The string keys mirror
# :class:`~lyra_core.memory.auto_memory.MemoryKind` values; we don't
# import the enum here to keep this module's dependency tree minimal.
DEFAULT_HALF_LIFE_S: dict[str, float] = {
    "user": float("inf"),         # role / preferences — never decay
    "project": float("inf"),      # ongoing work — never decay
    "feedback": 86_400.0 * 7,     # corrections / confirmations — 7d
    "reference": 86_400.0 * 30,   # external pointers — 30d
}

DEFAULT_ACCESS_SATURATION: int = 50


@dataclass(frozen=True)
class AccessStats:
    """In-memory side-table row attached to one entry."""

    last_accessed_ts: float = 0.0
    access_count: int = 0


def ebbinghaus_decay(
    age_s: float, half_life_s: float,
) -> float:
    """``exp(-age / half_life)``; saturates to 1.0 when half_life is ∞.

    Negative ages clamp to 0 (i.e. we never amplify a "future"
    timestamp to > 1.0). When ``age_s ≥ 0`` and ``half_life_s == inf``
    the return is 1.0 — no decay applied.
    """
    if not math.isfinite(half_life_s):
        return 1.0
    if half_life_s <= 0:
        return 1.0
    if age_s < 0:
        age_s = 0.0
    return math.exp(-age_s * math.log(2) / half_life_s)


def access_boost(
    access_count: int,
    *,
    saturation: int = DEFAULT_ACCESS_SATURATION,
) -> float:
    """Logarithmic strengthening; bounded by ``saturation``.

    Returns 1.0 for unaccessed records (so unobserved memories keep
    their base score). Saturates to ~2.0 by ``access_count =
    saturation``; the cap matters because telemetry can otherwise
    promote a popular-but-stale record indefinitely.
    """
    if access_count <= 0:
        return 1.0
    if saturation <= 0:
        return 1.0
    return 1.0 + math.log1p(access_count) / math.log1p(saturation)


def weighted_score(
    *,
    base_score: float,
    last_accessed_ts: float,
    access_count: int,
    half_life_s: float,
    now_ts: float | None = None,
    access_saturation: int = DEFAULT_ACCESS_SATURATION,
    fallback_ts: float = 0.0,
) -> float:
    """The full Ebbinghaus + strengthening composition.

    ``last_accessed_ts == 0`` (never accessed) falls back to
    ``fallback_ts`` (typically the entry's ``created_ts``) so a
    just-written entry doesn't read as "infinitely old".
    """
    now = now_ts if now_ts is not None else time.time()
    anchor_ts = last_accessed_ts if last_accessed_ts > 0 else fallback_ts
    if anchor_ts <= 0:
        # No anchor info at all → don't decay; treat as freshly written.
        decay = 1.0
    else:
        age = max(0.0, now - anchor_ts)
        decay = ebbinghaus_decay(age, half_life_s)
    boost = access_boost(access_count, saturation=access_saturation)
    return base_score * decay * boost


def half_life_for(
    kind: str,
    *,
    overrides: dict[str, float] | None = None,
) -> float:
    """Look up a half-life for a kind, falling back to default."""
    if overrides and kind in overrides:
        return overrides[kind]
    return DEFAULT_HALF_LIFE_S.get(kind, float("inf"))


__all__ = [
    "AccessStats",
    "DEFAULT_ACCESS_SATURATION",
    "DEFAULT_HALF_LIFE_S",
    "access_boost",
    "ebbinghaus_decay",
    "half_life_for",
    "weighted_score",
]
