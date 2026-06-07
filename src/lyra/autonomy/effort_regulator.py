"""
EffortRegulator — SAAS-style over-search mitigation via effort/reward calibration.

Implements the core calibration loop from arXiv:2605.29796:
1. Track effort/reward history per task type
2. Learn optimal stop point via diminishing returns detection
3. Adapt profiles per task type (code, chat, research)

The regulator learns the effort/reward curve for each task type and uses it
to decide *when to stop* — preventing wasted compute on tasks that have
already plateaued.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EffortLevel(str, Enum):
    """Autonomy effort levels — controls how aggressively the loop pursues a task.

    Each level maps to an :class:`EffortProfile` that governs max_steps,
    confidence threshold, and early-stop patience.
    """

    CONSERVATIVE = "conservative"  # Minimal compute, stop early
    BALANCED = "balanced"         # Default midpoint
    AGGRESSIVE = "aggressive"     # High compute, high confidence target
    ADAPTIVE = "adaptive"         # Auto-tune based on observed returns


@dataclass(frozen=True)
class EffortProfile:
    """Calibration parameters for a given effort level.

    Attributes:
        max_steps: Maximum iterations before forced stop.
        confidence_threshold: Target confidence (0-1) for accepting a result.
        early_stop_patience: Number of consecutive flat/down improvements
            before triggering early stop.
    """

    max_steps: int
    confidence_threshold: float
    early_stop_patience: int


# ── Built-in profiles ──────────────────────────────────────────────

_PROFILES: dict[str, EffortProfile] = {
    "code": EffortProfile(
        max_steps=50,
        confidence_threshold=0.92,
        early_stop_patience=5,
    ),
    "chat": EffortProfile(
        max_steps=10,
        confidence_threshold=0.75,
        early_stop_patience=2,
    ),
    "research": EffortProfile(
        max_steps=30,
        confidence_threshold=0.85,
        early_stop_patience=4,
    ),
}

_EFFORT_PROFILES: dict[EffortLevel, EffortProfile] = {
    EffortLevel.CONSERVATIVE: EffortProfile(
        max_steps=10,
        confidence_threshold=0.70,
        early_stop_patience=2,
    ),
    EffortLevel.BALANCED: EffortProfile(
        max_steps=30,
        confidence_threshold=0.85,
        early_stop_patience=4,
    ),
    EffortLevel.AGGRESSIVE: EffortProfile(
        max_steps=80,
        confidence_threshold=0.95,
        early_stop_patience=8,
    ),
    EffortLevel.ADAPTIVE: EffortProfile(
        max_steps=50,
        confidence_threshold=0.88,
        early_stop_patience=5,
    ),
}


@dataclass
class TaskHistoryEntry:
    """A single data point in the calibration history.

    Attributes:
        task_type: The type of task (e.g. "code", "chat", "research").
        steps_taken: Number of steps the loop ran.
        final_confidence: Achieved confidence (0-1) at stop time.
        improvement_sequence: Per-step improvement deltas.
        wall_time_seconds: Total elapsed wall time.
        tokens_consumed: Approximate tokens used.
    """

    task_type: str
    steps_taken: int
    final_confidence: float
    improvement_sequence: list[float]
    wall_time_seconds: float
    tokens_consumed: int


@dataclass
class SessionState:
    """Snapshot of the current execution session, used by ``should_continue``.

    Attributes:
        step: Current step index (0-based).
        confidence: Current confidence estimate (0-1).
        improvements: Recent improvement deltas (most recent last).
        tokens_consumed: Cumulative tokens consumed so far.
        wall_time_seconds: Elapsed wall time.
        consecutive_failures: How many recent tasks failed.
    """

    step: int = 0
    confidence: float = 0.0
    improvements: list[float] = field(default_factory=list)
    tokens_consumed: int = 0
    wall_time_seconds: float = 0.0
    consecutive_failures: int = 0


@dataclass
class Budget:
    """Resource budget for a task execution.

    Attributes:
        max_steps: Hard cap on iteration count.
        max_tokens: Hard cap on token consumption.
        max_wall_time_seconds: Hard cap on elapsed time.
    """

    max_steps: int = 100
    max_tokens: int = 100_000
    max_wall_time_seconds: float = 3600.0


# ── A simple moving-window calibration store ───────────────────────


class _CalibrationDB:
    """In-memory calibration history with basic persistence."""

    def __init__(self) -> None:
        self._history: dict[str, list[TaskHistoryEntry]] = defaultdict(list)

    def record(self, entry: TaskHistoryEntry) -> None:
        self._history[entry.task_type].append(entry)

    def history(self, task_type: str) -> list[TaskHistoryEntry]:
        return self._history.get(task_type, [])

    def average_steps(self, task_type: str, window: int = 5) -> float:
        entries = self._history.get(task_type, [])[-window:]
        if not entries:
            return 0.0
        return sum(e.steps_taken for e in entries) / len(entries)

    def average_confidence(self, task_type: str, window: int = 5) -> float:
        entries = self._history.get(task_type, [])[-window:]
        if not entries:
            return 0.0
        return sum(e.final_confidence for e in entries) / len(entries)

    def best_profile_for(
        self, task_type: str, profiles: dict[str, EffortProfile]
    ) -> str | None:
        """Return the profile name that historically gives best
        effort/reward ratio for *task_type*."""
        entries = self._history.get(task_type, [])
        if not entries:
            return None

        best_score = -1.0
        best_name: str | None = None

        # Group entries by the number of steps they used (proxy for profile)
        score_by_steps: dict[int, float] = {}
        count_by_steps: dict[int, int] = {}
        for e in entries:
            s = e.steps_taken
            if e.steps_taken == 0:
                continue
            # Score = final_confidence / steps_taken  (effort/reward ratio)
            score = e.final_confidence / max(e.steps_taken, 1)
            score_by_steps[s] = score_by_steps.get(s, 0.0) + score
            count_by_steps[s] = count_by_steps.get(s, 0) + 1

        for steps, total_score in score_by_steps.items():
            avg = total_score / count_by_steps[steps]
            if avg > best_score:
                best_score = avg
                # Map steps back to a profile name (closest match)
                best_name = min(
                    profiles,
                    key=lambda n: abs(profiles[n].max_steps - steps),
                )
        return best_name


# ── EffortRegulator ─────────────────────────────────────────────────


class EffortRegulator:
    """Calibrates task effort based on historical reward curves.

    SAAS-style over-search mitigation: learns the effort/reward curve per
    task type and decides when to stop pursuing a task.

    Usage::

        regulator = EffortRegulator()
        level = regulator.calibrate("code", history=[])
        # ... run task, collect improvements ...
        if regulator.diminishing_returns_check(improvements):
            print("Plateau detected, stopping early.")
    """

    def __init__(self, profiles: dict[str, EffortProfile] | None = None) -> None:
        self._profiles = profiles or dict(_PROFILES)
        self._db = _CalibrationDB()

    # ── Public API ─────────────────────────────────────────────────

    def calibrate(
        self,
        task_type: str,
        history: list[TaskHistoryEntry] | None = None,
    ) -> EffortLevel:
        """Learn the appropriate effort level for a task type.

        Uses historical data to pick the effort level that maximises the
        effort/reward ratio.  Falls back to a sensible default when no
        history exists.

        Args:
            task_type: One of ``"code"``, ``"chat"``, ``"research"``.
            history: Optional pre-loaded history (overrides internal DB).

        Returns:
            The recommended :class:`EffortLevel`.
        """
        if history is None:
            history = self._db.history(task_type)

        if not history:
            return self._default_level(task_type)

        # Calculate average effort/reward ratio per effort band
        best_level = EffortLevel.BALANCED
        best_ratio = -1.0

        for level in EffortLevel:
            profile = _EFFORT_PROFILES[level]
            matched = [
                h
                for h in history
                if h.steps_taken <= profile.max_steps
                and h.final_confidence >= profile.confidence_threshold * 0.8
            ]
            if not matched:
                continue

            avg_confidence = sum(h.final_confidence for h in matched) / len(matched)
            avg_steps = sum(h.steps_taken for h in matched) / len(matched)
            ratio = avg_confidence / max(avg_steps, 1)

            if ratio > best_ratio:
                best_ratio = ratio
                best_level = level

        return best_level

    def should_continue(
        self,
        session_state: SessionState,
        budget: Budget,
    ) -> bool:
        """Decide whether the loop should keep running.

        Checks three axes:
        1. Hard budget caps (steps, tokens, wall time)
        2. Confidence threshold met
        3. Diminishing returns (plateau)

        Args:
            session_state: Current session snapshot.
            budget: Resource budget for the task.

        Returns:
            ``True`` if execution should continue, ``False`` to stop.
        """
        # ── Hard caps ───────────────────────────────────────────
        if session_state.step >= budget.max_steps:
            return False
        if session_state.tokens_consumed >= budget.max_tokens:
            return False
        if session_state.wall_time_seconds >= budget.max_wall_time_seconds:
            return False

        # ── Confidence threshold ────────────────────────────────
        profile = self._profile_for_steps(session_state.step)
        if session_state.confidence >= profile.confidence_threshold:
            return False

        # ── Diminishing returns ─────────────────────────────────
        if self.diminishing_returns_check(session_state.improvements):
            return False

        return True

    def diminishing_returns_check(
        self,
        improvements: list[float],
        patience: int | None = None,
    ) -> bool:
        """Detect whether improvements have plateaued.

        Uses a simple sliding-window heuristic: if *patience* consecutive
        improvements are flat or negative, the curve has plateaued.

        Args:
            improvements: Sequence of per-step improvement deltas (most
                recent last).  Each value is the absolute improvement in
                the metric (e.g. confidence gain).
            patience: How many consecutive flat/negative deltas trigger
                a plateau.  Falls back to the BALANCED profile's patience
                if not provided.

        Returns:
            ``True`` if improvements have plateaued.
        """
        if len(improvements) < 2:
            return False

        patience = patience or _EFFORT_PROFILES[EffortLevel.BALANCED].early_stop_patience

        # Take the most recent N improvements
        recent = improvements[-patience:]
        if len(recent) < patience:
            return False

        # If all recent improvements are near-zero or negative → plateau
        threshold = 0.01  # 1% improvement minimum
        return all(abs(delta) < threshold for delta in recent)

    def record_outcome(self, entry: TaskHistoryEntry) -> None:
        """Record a task outcome for future calibration.

        Args:
            entry: Completed task history entry.
        """
        self._db.record(entry)

    def profile(self, task_type: str) -> EffortProfile:
        """Return the :class:`EffortProfile` for a task type.

        Falls back to the ``"code"`` profile if the type is unknown.
        """
        return self._profiles.get(task_type, _PROFILES["code"])

    def all_profiles(self) -> dict[str, EffortProfile]:
        """Return the full set of registered task profiles."""
        return dict(self._profiles)

    def calibration_stats(self, task_type: str) -> dict[str, Any]:
        """Return summary calibration statistics for a task type.

        Args:
            task_type: Task type to query.

        Returns:
            A dict with keys ``average_steps``, ``average_confidence``,
            ``total_tasks``, ``best_effort_level``.
        """
        history = self._db.history(task_type)
        return {
            "task_type": task_type,
            "average_steps": self._db.average_steps(task_type),
            "average_confidence": self._db.average_confidence(task_type),
            "total_tasks": len(history),
            "best_effort_level": self.calibrate(task_type).value,
        }

    # ── Internal helpers ───────────────────────────────────────────

    def _profile_for_steps(self, steps: int) -> EffortProfile:
        """Return the effort profile that best matches the current step count."""
        if steps <= _EFFORT_PROFILES[EffortLevel.CONSERVATIVE].max_steps:
            return _EFFORT_PROFILES[EffortLevel.CONSERVATIVE]
        if steps <= _EFFORT_PROFILES[EffortLevel.BALANCED].max_steps:
            return _EFFORT_PROFILES[EffortLevel.BALANCED]
        return _EFFORT_PROFILES[EffortLevel.AGGRESSIVE]

    @staticmethod
    def _default_level(task_type: str) -> EffortLevel:
        """Return a sensible default effort level for a task type."""
        defaults = {
            "code": EffortLevel.AGGRESSIVE,
            "chat": EffortLevel.CONSERVATIVE,
            "research": EffortLevel.ADAPTIVE,
        }
        return defaults.get(task_type, EffortLevel.BALANCED)
