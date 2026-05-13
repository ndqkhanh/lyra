"""Cache telemetry — per-turn cache token accounting.

Tracks cache_read_input_tokens, cache_creation_input_tokens, and
input_tokens per turn to compute the cache hit ratio and alert on drops.

Research grounding: §5.1 (Anthropic prompt caching mechanics), §11 step 4
(cache-aware request builder), Anthropic April 2026 postmortem — a cache-
busting bug caused every turn to be a miss for weeks before telemetry caught it.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CacheTurnRecord:
    """Token counts for one API turn."""

    turn_id: int
    input_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    output_tokens: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    @property
    def hit_ratio(self) -> float:
        """Fraction of input tokens served from cache (0.0–1.0)."""
        if self.input_tokens == 0:
            return 0.0
        return self.cache_read_tokens / self.input_tokens

    @property
    def effective_cost_multiplier(self) -> float:
        """Cost relative to paying full price for all input tokens.

        Anthropic pricing: cache reads ≈ 0.1×, cache writes ≈ 1.25×, pass-through 1.0×.
        """
        total = self.input_tokens
        if total == 0:
            return 1.0
        read_cost = self.cache_read_tokens * 0.1
        write_cost = self.cache_creation_tokens * 1.25
        pass_through = (
            total - self.cache_read_tokens - self.cache_creation_tokens
        ) * 1.0
        return (read_cost + write_cost + pass_through) / total


@dataclass(frozen=True)
class CacheSessionSummary:
    """Aggregate cache stats for a session."""

    turn_count: int
    total_input_tokens: int
    total_cache_creation_tokens: int
    total_cache_read_tokens: int
    total_output_tokens: int
    mean_hit_ratio: float
    min_hit_ratio: float
    alert_count: int


class CacheTelemetry:
    """Accumulate per-turn cache token records and surface hit-ratio alerts.

    Usage::
        tel = CacheTelemetry(alert_threshold=0.70)
        rec = tel.record(input_tokens=1000, cache_read_tokens=800)
        if tel.should_alert():
            print("Cache hit ratio dropped:", tel.last_hit_ratio())
    """

    def __init__(
        self,
        *,
        alert_threshold: float = 0.70,
        store_path: Path | None = None,
    ) -> None:
        self._threshold = alert_threshold
        self._store_path = store_path
        self._records: list[CacheTurnRecord] = []
        if store_path and store_path.exists():
            self._load(store_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        input_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        output_tokens: int = 0,
    ) -> CacheTurnRecord:
        """Record one turn's token counts. Returns the stored record."""
        rec = CacheTurnRecord(
            turn_id=len(self._records),
            input_tokens=input_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            output_tokens=output_tokens,
        )
        self._records.append(rec)
        if self._store_path:
            self._save(self._store_path)
        return rec

    def hit_ratio(self) -> float:
        """Mean hit ratio across all recorded turns. 0.0 if no turns."""
        if not self._records:
            return 0.0
        return sum(r.hit_ratio for r in self._records) / len(self._records)

    def last_hit_ratio(self) -> float | None:
        """Hit ratio of the most recent turn, or None if no turns yet."""
        return self._records[-1].hit_ratio if self._records else None

    def should_alert(self) -> bool:
        """True when the last turn's hit ratio is below the alert threshold."""
        ratio = self.last_hit_ratio()
        return ratio is not None and ratio < self._threshold

    def records(self) -> list[CacheTurnRecord]:
        return list(self._records)

    def summary(self) -> CacheSessionSummary:
        if not self._records:
            return CacheSessionSummary(0, 0, 0, 0, 0, 0.0, 0.0, 0)
        ratios = [r.hit_ratio for r in self._records]
        return CacheSessionSummary(
            turn_count=len(self._records),
            total_input_tokens=sum(r.input_tokens for r in self._records),
            total_cache_creation_tokens=sum(
                r.cache_creation_tokens for r in self._records
            ),
            total_cache_read_tokens=sum(
                r.cache_read_tokens for r in self._records
            ),
            total_output_tokens=sum(r.output_tokens for r in self._records),
            mean_hit_ratio=sum(ratios) / len(ratios),
            min_hit_ratio=min(ratios),
            alert_count=sum(
                1 for r in self._records if r.hit_ratio < self._threshold
            ),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(r) for r in self._records], indent=2))

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text())
            self._records = [CacheTurnRecord(**r) for r in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._records = []


__all__ = [
    "CacheTurnRecord",
    "CacheSessionSummary",
    "CacheTelemetry",
]
