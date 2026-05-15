"""Mid-session lesson extraction with confidence + pending queue
(Phase CE.2, P1-3).

Lyra's existing :class:`~lyra_core.memory.reasoning_bank.ReasoningBank`
distills at session end. ECC's continuous-learning v2 emits *during*
the session with a confidence score so the user (or the agent) can
curate which lessons get promoted to the bank.

This module wraps the existing distiller machinery without breaking
the frozen :class:`Lesson` schema:

* :class:`ScoredLesson` — a Lesson + confidence pair.
* :class:`MidSessionExtractor` — runs the distiller every N turns,
  applies a confidence heuristic, and routes each lesson into one of
  three buckets:

  - ``confidence >= AUTO_PROMOTE`` → straight to the bank.
  - ``REJECT_FLOOR <= confidence < AUTO_PROMOTE`` → pending queue.
  - ``confidence < REJECT_FLOOR`` → dropped.

The pending queue is intentionally in-memory + ephemeral — its purpose
is to surface choices for the user; the durable record (the bank
itself) only sees promoted lessons.
"""
from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Callable

from .distillers import HeuristicDistiller
from .reasoning_bank import (
    Distiller,
    Lesson,
    ReasoningBank,
    Trajectory,
    TrajectoryOutcome,
)

AUTO_PROMOTE = 0.8
REJECT_FLOOR = 0.4
DEFAULT_TURN_INTERVAL = 10


@dataclass(frozen=True)
class ScoredLesson:
    """A lesson paired with a confidence score in ``[0, 1]``."""

    lesson: Lesson
    confidence: float
    ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"ScoredLesson.confidence must be in [0, 1]; got {self.confidence}"
            )


@dataclass
class ExtractionResult:
    """Outcome of one :meth:`MidSessionExtractor.extract` call."""

    promoted: tuple[ScoredLesson, ...] = ()
    pending: tuple[ScoredLesson, ...] = ()
    dropped: tuple[ScoredLesson, ...] = ()

    def counts(self) -> dict[str, int]:
        return {
            "promoted": len(self.promoted),
            "pending": len(self.pending),
            "dropped": len(self.dropped),
        }


# ────────────────────────────────────────────────────────────────
# Default confidence heuristic
# ────────────────────────────────────────────────────────────────


def default_confidence(lesson: Lesson, trajectory: Trajectory) -> float:
    """Score a lesson by how trustworthy the distillation looks.

    Signals (each adds to a 0..1 score, clamped):

    * Success-polarity from a multi-step trajectory → higher.
    * Anti-skill (failure) from a single-step trajectory → lower
      (noise risk).
    * Body length above 60 chars → signals substantive content.
    * Title is non-generic (more than 4 words) → adds a small bump.
    """
    score = 0.0
    if lesson.polarity == TrajectoryOutcome.SUCCESS:
        score += 0.5
    else:
        score += 0.3

    step_count = len(trajectory.steps)
    if step_count >= 3:
        score += 0.2
    elif step_count >= 1:
        score += 0.1

    if len(lesson.body) >= 60:
        score += 0.15
    if len(lesson.title.split()) > 4:
        score += 0.1
    if len(lesson.task_signatures) > 1:
        score += 0.05

    return min(1.0, score)


# ────────────────────────────────────────────────────────────────
# Extractor
# ────────────────────────────────────────────────────────────────


class MidSessionExtractor:
    """Run the distiller mid-session and bucket the results.

    Thread-safety: not designed for concurrent use; one extractor per
    session.
    """

    def __init__(
        self,
        bank: ReasoningBank,
        *,
        distiller: Distiller | None = None,
        confidence_fn: Callable[[Lesson, Trajectory], float] = default_confidence,
        turn_interval: int = DEFAULT_TURN_INTERVAL,
        auto_promote: float = AUTO_PROMOTE,
        reject_floor: float = REJECT_FLOOR,
    ) -> None:
        if turn_interval <= 0:
            raise ValueError(f"turn_interval must be > 0, got {turn_interval}")
        if not 0.0 <= reject_floor <= auto_promote <= 1.0:
            raise ValueError(
                "thresholds must satisfy 0 <= reject_floor <= auto_promote <= 1; "
                f"got reject_floor={reject_floor}, auto_promote={auto_promote}"
            )
        self._bank = bank
        self._distiller = distiller or HeuristicDistiller()
        self._confidence_fn = confidence_fn
        self._turn_interval = turn_interval
        self._auto_promote = auto_promote
        self._reject_floor = reject_floor
        self._pending: dict[str, ScoredLesson] = {}
        self._turn_counter = 0
        self._last_extracted_at_turn = 0

    @property
    def turn_interval(self) -> int:
        return self._turn_interval

    # ------------------------------------------------------------------ tick
    def tick(self) -> bool:
        """Advance the turn counter. Return True if it's time to extract."""
        self._turn_counter += 1
        return (
            self._turn_counter - self._last_extracted_at_turn
            >= self._turn_interval
        )

    def reset_counter(self) -> None:
        self._last_extracted_at_turn = self._turn_counter

    # --------------------------------------------------------------- extract
    def extract(self, trajectory: Trajectory) -> ExtractionResult:
        """Distill ``trajectory`` and bucket each lesson by confidence."""
        promoted: list[ScoredLesson] = []
        pending: list[ScoredLesson] = []
        dropped: list[ScoredLesson] = []

        for lesson in self._distiller.distill(trajectory):
            confidence = max(
                0.0, min(1.0, self._confidence_fn(lesson, trajectory))
            )
            scored = ScoredLesson(lesson=lesson, confidence=confidence)
            if confidence >= self._auto_promote:
                self._bank.record_lesson(lesson)
                promoted.append(scored)
            elif confidence >= self._reject_floor:
                self._pending[lesson.id] = scored
                pending.append(scored)
            else:
                dropped.append(scored)

        self.reset_counter()
        return ExtractionResult(
            promoted=tuple(promoted),
            pending=tuple(pending),
            dropped=tuple(dropped),
        )

    # --------------------------------------------------------------- pending
    def pending(self) -> tuple[ScoredLesson, ...]:
        """Snapshot of the pending queue in insertion order."""
        return tuple(self._pending.values())

    def promote(self, lesson_id: str) -> ScoredLesson | None:
        """Move a pending lesson into the bank. Returns it, or None."""
        scored = self._pending.pop(lesson_id, None)
        if scored is None:
            return None
        self._bank.record_lesson(scored.lesson)
        return scored

    def reject(self, lesson_id: str) -> ScoredLesson | None:
        """Drop a pending lesson without persisting. Returns it, or None."""
        return self._pending.pop(lesson_id, None)

    def clear_pending(self) -> int:
        """Wipe the queue; returns how many were discarded."""
        n = len(self._pending)
        self._pending.clear()
        return n


# ────────────────────────────────────────────────────────────────
# CLI-adapter shapes (helpers callers can wire to ``lyra memory pending``)
# ────────────────────────────────────────────────────────────────


def render_pending_table(items: Iterable[ScoredLesson]) -> list[dict[str, str]]:
    """Flat dicts suitable for a CLI table renderer."""
    rows: list[dict[str, str]] = []
    for s in items:
        rows.append(
            {
                "id": s.lesson.id,
                "polarity": s.lesson.polarity.value,
                "confidence": f"{s.confidence:.2f}",
                "title": s.lesson.title[:80],
                "signatures": ", ".join(s.lesson.task_signatures),
            }
        )
    return rows


__all__ = [
    "AUTO_PROMOTE",
    "DEFAULT_TURN_INTERVAL",
    "ExtractionResult",
    "MidSessionExtractor",
    "REJECT_FLOOR",
    "ScoredLesson",
    "default_confidence",
    "render_pending_table",
]
