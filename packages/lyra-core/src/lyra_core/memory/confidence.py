"""L311-8 — Confidence-scored auto-memory.

Extends Lyra's v3.7 :class:`~lyra_core.memory.auto_memory.AutoMemory`
with per-entry confidence tracking, matching the Claude Code 2026
"instinct extraction" pattern ([`docs/62-everything-claude-code.md`](../../../../../../docs/62-everything-claude-code.md)).
The 2025–2026 lesson from operating long-running self-improving agents:
**every extracted pattern needs a probabilistic weight from the start**,
or junk-memory accumulates and the loop drifts.

Why a sidecar instead of mutating ``MemoryEntry``? ``MemoryEntry`` is
``@dataclass(frozen=True)`` and append-only by ``LBL-AUTO-MEMORY-APPEND-ONLY``.
Confidence, seen_count, and last_seen are *aggregate read-side state*
that grows independently of the audit log. Storing them in a sidecar
(``confidence.json`` next to ``access_stats.json``) keeps the audit
chain intact and lets us update aggregates atomically.

Promotion / demotion rules (L311-8):

* ``seen_count >= 3 AND confidence >= 0.85`` → emit
  ``confidence.promote`` event so the procedural-memory tier can
  durably register the pattern.
* ``seen_count >= 1 AND confidence < 0.30 AND age_days > 7`` → emit
  ``confidence.demote`` event so callers can tombstone the auto-memory
  entry.

The tracker emits events but does not itself perform the durable
register or tombstone — that policy lives one layer up (auto-memory
manager) so the same tracker can be wired to different durable
substrates without coupling.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable


_PROMOTION_SEEN_COUNT = 3
_PROMOTION_CONFIDENCE = 0.85
_DEMOTION_CONFIDENCE = 0.30
_DEMOTION_AGE_DAYS = 7.0
_DAY_SECONDS = 86_400.0


# ---- record dataclass -------------------------------------------------


@dataclass
class ConfidenceRecord:
    """Per-entry confidence aggregates."""

    entry_id: str
    confidence: float = 0.5
    seen_count: int = 1
    last_seen_ts: float = 0.0
    created_ts: float = 0.0
    extracted_by: str = "instinct-extractor-v3"
    promoted: bool = False
    demoted: bool = False

    def __post_init__(self) -> None:
        self._validate_confidence()

    def _validate_confidence(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence} outside [0,1]")

    def to_json(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "confidence": self.confidence,
            "seen_count": self.seen_count,
            "last_seen_ts": self.last_seen_ts,
            "created_ts": self.created_ts,
            "extracted_by": self.extracted_by,
            "promoted": self.promoted,
            "demoted": self.demoted,
        }

    @classmethod
    def from_json(cls, row: dict[str, Any]) -> "ConfidenceRecord":
        return cls(
            entry_id=str(row["entry_id"]),
            confidence=float(row.get("confidence", 0.5)),
            seen_count=int(row.get("seen_count", 1)),
            last_seen_ts=float(row.get("last_seen_ts", 0.0)),
            created_ts=float(row.get("created_ts", 0.0)),
            extracted_by=str(row.get("extracted_by", "instinct-extractor-v3")),
            promoted=bool(row.get("promoted", False)),
            demoted=bool(row.get("demoted", False)),
        )

    @property
    def age_days(self) -> float:
        if self.created_ts <= 0:
            return 0.0
        return max((time.time() - self.created_ts) / _DAY_SECONDS, 0.0)


# ---- event types ------------------------------------------------------


@dataclass(frozen=True)
class PromotionEvent:
    record: ConfidenceRecord
    reason: str = "seen_count + high confidence"


@dataclass(frozen=True)
class DemotionEvent:
    record: ConfidenceRecord
    reason: str = "low confidence over age threshold"


EventListener = Callable[[Any], None]
"""Callable receiving :class:`PromotionEvent` or :class:`DemotionEvent`.
Production callers wire this to the procedural-memory promote / tombstone
ops; tests wire it to a list."""


# ---- the tracker ------------------------------------------------------


@dataclass
class ConfidenceTracker:
    """Manages per-entry confidence, seen_count, and last_seen sidecars.

    Storage: ``{root}/confidence.json`` — atomic write-temp-then-rename.
    """

    root: Path
    listener: EventListener | None = None
    _records: dict[str, ConfidenceRecord] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "confidence.json"
        self._load()

    # ---- mutation -------------------------------------------------

    def record_pattern(
        self,
        *,
        entry_id: str,
        confidence: float,
        extracted_by: str = "instinct-extractor-v3",
    ) -> ConfidenceRecord:
        """First-time extraction of a pattern. Sets ``seen_count=1``."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence {confidence} outside [0,1]")
        with self._lock:
            now = time.time()
            rec = ConfidenceRecord(
                entry_id=entry_id,
                confidence=confidence,
                seen_count=1,
                last_seen_ts=now,
                created_ts=now,
                extracted_by=extracted_by,
            )
            self._records[entry_id] = rec
            self._flush_locked()
        self._maybe_emit(rec)
        return rec

    def observe(
        self,
        *,
        entry_id: str,
        delta_confidence: float = 0.05,
    ) -> ConfidenceRecord:
        """Bump ``seen_count``, raise ``confidence`` (clamped). Returns the new record.

        ``delta_confidence`` is the per-observation lift; the default
        +0.05 means "five observations to fully promote" (5 × 0.05 = 0.25
        from default 0.6 starting confidence). Tune for your use case.
        """
        with self._lock:
            rec = self._records.get(entry_id)
            if rec is None:
                raise KeyError(f"unknown entry {entry_id!r} — call record_pattern first")
            now = time.time()
            new_confidence = min(max(rec.confidence + delta_confidence, 0.0), 1.0)
            updated = ConfidenceRecord(
                entry_id=rec.entry_id,
                confidence=new_confidence,
                seen_count=rec.seen_count + 1,
                last_seen_ts=now,
                created_ts=rec.created_ts,
                extracted_by=rec.extracted_by,
                promoted=rec.promoted,
                demoted=rec.demoted,
            )
            self._records[entry_id] = updated
            self._flush_locked()
        self._maybe_emit(updated)
        return updated

    def decay(
        self,
        *,
        entry_id: str,
        delta_confidence: float = 0.10,
    ) -> ConfidenceRecord:
        """Lower ``confidence`` (e.g. on a contradicted pattern). Bumps ``seen_count``."""
        with self._lock:
            rec = self._records.get(entry_id)
            if rec is None:
                raise KeyError(f"unknown entry {entry_id!r}")
            now = time.time()
            new_confidence = min(max(rec.confidence - delta_confidence, 0.0), 1.0)
            updated = ConfidenceRecord(
                entry_id=rec.entry_id,
                confidence=new_confidence,
                seen_count=rec.seen_count + 1,
                last_seen_ts=now,
                created_ts=rec.created_ts,
                extracted_by=rec.extracted_by,
                promoted=rec.promoted,
                demoted=rec.demoted,
            )
            self._records[entry_id] = updated
            self._flush_locked()
        self._maybe_emit(updated)
        return updated

    def mark_promoted(self, entry_id: str) -> None:
        with self._lock:
            rec = self._records.get(entry_id)
            if rec is None:
                return
            rec.promoted = True
            self._flush_locked()

    def mark_demoted(self, entry_id: str) -> None:
        with self._lock:
            rec = self._records.get(entry_id)
            if rec is None:
                return
            rec.demoted = True
            self._flush_locked()

    # ---- read -----------------------------------------------------

    def get(self, entry_id: str) -> ConfidenceRecord | None:
        return self._records.get(entry_id)

    def all(self) -> tuple[ConfidenceRecord, ...]:
        return tuple(self._records.values())

    def candidates_for_promotion(self) -> tuple[ConfidenceRecord, ...]:
        return tuple(
            r
            for r in self._records.values()
            if not r.promoted
            and r.seen_count >= _PROMOTION_SEEN_COUNT
            and r.confidence >= _PROMOTION_CONFIDENCE
        )

    def candidates_for_demotion(self) -> tuple[ConfidenceRecord, ...]:
        return tuple(
            r
            for r in self._records.values()
            if not r.demoted
            and r.confidence < _DEMOTION_CONFIDENCE
            and r.age_days > _DEMOTION_AGE_DAYS
        )

    # ---- internal -------------------------------------------------

    def _maybe_emit(self, rec: ConfidenceRecord) -> None:
        # Only fire on transitions, not on every observe.
        if (
            not rec.promoted
            and rec.seen_count >= _PROMOTION_SEEN_COUNT
            and rec.confidence >= _PROMOTION_CONFIDENCE
        ):
            self._emit(PromotionEvent(record=rec))
        if (
            not rec.demoted
            and rec.confidence < _DEMOTION_CONFIDENCE
            and rec.age_days > _DEMOTION_AGE_DAYS
        ):
            self._emit(DemotionEvent(record=rec))

    def _emit(self, event: Any) -> None:
        if self.listener is not None:
            try:
                self.listener(event)
            except Exception:
                # listener errors must never break the tracker.
                pass
        try:
            from lyra_core.hir import events

            kind = "confidence.promote" if isinstance(event, PromotionEvent) else "confidence.demote"
            events.emit(
                kind,
                entry_id=event.record.entry_id,
                confidence=event.record.confidence,
                seen_count=event.record.seen_count,
            )
        except Exception:
            pass

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        for row in data.get("records", []):
            try:
                rec = ConfidenceRecord.from_json(row)
            except Exception:
                continue
            self._records[rec.entry_id] = rec

    def _flush_locked(self) -> None:
        # Caller must hold ``self._lock``.
        payload = {
            "records": [r.to_json() for r in self._records.values()],
            "updated_at": time.time(),
        }
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._path)


__all__ = [
    "ConfidenceRecord",
    "ConfidenceTracker",
    "DemotionEvent",
    "EventListener",
    "PromotionEvent",
]
