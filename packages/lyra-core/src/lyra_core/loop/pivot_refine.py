"""Pivot/Refine failure recovery loop — self-healing from execution failures.

When an agent attempt fails the platform needs more than just "try again".
This module implements a structured failure-recovery pipeline that:

1. Records every failure as a structured :class:`ErrorRecord` with task context,
   stack trace, and attempt metadata.
2. Classifies the failure against a persistent :class:`ErrorDatabase` that
   supports pattern matching across runs so the platform learns from past
   mistakes (cross-run evolution).
3. Selects a :class:`RecoveryStrategy` — RETRY (same approach), PIVOT (change
   tactic), DECOMPOSE (split into sub-tasks), ESCALATE (delegate to a stronger
   agent), or ABORT (give up).
4. Generates concrete alternatives for PIVOT / DECOMPOSE strategies.
5. Executes the recovery plan and captures the outcome in a
   :class:`RecoveryResult` including the lesson learned for future runs.

The pipeline is strategy-agnostic — callers bring their own implementation for
``alternative_generator``, ``executor``, etc., so the loop works identically
whether backed by an LLM, a rule engine, or human-in-the-loop.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional


__all__ = [
    "ErrorRecord",
    "ErrorDatabase",
    "RecoveryStrategy",
    "PivotRefineExecutor",
    "RecoveryResult",
]


# ---------------------------------------------------------------------------
# Error record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorRecord:
    """A single structured failure observation.

    Every field is intentionally concrete so consumers can match on any
    dimension — error type, task fingerprint, failure stage, or textual
    similarity of the message.

    ``attempt_count`` starts at 1 for fresh records and increments for
    re-recordings of the same logical failure (discouraged; prefer the
    database's built-in pattern matching).
    """

    error_type: str
    message: str
    task_context: str
    failure_stage: str
    timestamp: float = field(default_factory=time.time)
    stack_trace: str = ""
    attempt_count: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "task_context": self.task_context,
            "failure_stage": self.failure_stage,
            "timestamp": self.timestamp,
            "stack_trace": self.stack_trace,
            "attempt_count": self.attempt_count,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ErrorRecord:
        _ts = payload.get("timestamp")
        _ac = payload.get("attempt_count")

        timestamp: float = time.time()
        if isinstance(_ts, (int, float)):
            timestamp = float(_ts)

        attempt_count: int = 1
        if isinstance(_ac, int):
            attempt_count = _ac

        return cls(
            error_type=str(payload["error_type"]),
            message=str(payload["message"]),
            task_context=str(payload.get("task_context", "")),
            failure_stage=str(payload.get("failure_stage", "")),
            timestamp=timestamp,
            stack_trace=str(payload.get("stack_trace", "")),
            attempt_count=attempt_count,
        )


# ---------------------------------------------------------------------------
# Recovery strategy
# ---------------------------------------------------------------------------


class RecoveryStrategy(Enum):
    """What the executor should do next given the failure analysis."""

    RETRY = auto()
    """Try the exact same approach again (transient error)."""

    PIVOT = auto()
    """Change the approach while keeping the same goal (semantic error)."""

    ESCALATE = auto()
    """Delegate to a stronger / more specialised agent (capability gap)."""

    ABORT = auto()
    """Give up on this task entirely (unrecoverable)."""

    DECOMPOSE = auto()
    """Break the task into smaller sub-tasks and attack each one separately."""


# ---------------------------------------------------------------------------
# Error database
# ---------------------------------------------------------------------------

_SimilarityScorer = Callable[[ErrorRecord, ErrorRecord], float]
"""``(a, b) -> similarity in [0, 1]`` where 1 means identical."""


def _default_similarity(a: ErrorRecord, b: ErrorRecord) -> float:
    """Baseline token-overlap scorer used when no custom scorer is provided.

    Compares error type (exact match = 1.0), failure stage (exact match = 1.0),
    and a simple word-overlap on the message. The combined score is a weighted
    average of the three dimensions.
    """
    score = 0.0
    if a.error_type == b.error_type:
        score += 0.4
    if a.failure_stage == b.failure_stage:
        score += 0.2

    # Word-overlap on message text.
    a_words = set(a.message.lower().split())
    b_words = set(b.message.lower().split())
    if a_words and b_words:
        overlap = len(a_words & b_words)
        total = len(a_words | b_words)
        score += 0.4 * (overlap / total)

    return score


@dataclass(frozen=True)
class ErrorPattern:
    """A recurring failure pattern discovered by the database."""

    error_type: str
    frequency: int
    typical_message: str
    typical_stage: str
    last_seen: float


class ErrorDatabase:
    """Persistent error store with pattern matching across runs.

    Stores :class:`ErrorRecord` instances in memory and optionally persists
    to a JSON file on disk (write-temp + rename for atomicity). Provides
    similarity-based retrieval so the same logical failure is recognised
    even when the message text varies (e.g. different LLM invocation at
    different temperatures).
    """

    def __init__(
        self,
        *,
        path: Optional[Path] = None,
        similarity_scorer: Optional[_SimilarityScorer] = None,
    ) -> None:
        self._records: list[ErrorRecord] = []
        self._path: Optional[Path] = Path(path) if path is not None else None
        self._scorer: _SimilarityScorer = similarity_scorer or _default_similarity
        if self._path is not None and self._path.exists():
            self._load()

    # ---- public API --------------------------------------------------------

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    def record(self, error: ErrorRecord) -> None:
        """Persist a single failure and auto-persist when a snapshot path is set."""
        self._records.append(error)
        self._save()

    def find_similar(
        self,
        error: ErrorRecord,
        *,
        threshold: float = 0.6,
    ) -> list[tuple[ErrorRecord, float]]:
        """Return all stored errors whose similarity to *error* >= *threshold*.

        Results are sorted by descending similarity so the caller can pick
        the best match with ``results[0]``.
        """
        matches: list[tuple[ErrorRecord, float]] = []
        for stored in self._records:
            sim = self._scorer(error, stored)
            if sim >= threshold:
                matches.append((stored, sim))
        matches.sort(key=lambda pair: pair[1], reverse=True)
        return matches

    def get_patterns(self) -> list[ErrorPattern]:
        """Aggregate stored errors into recurring failure patterns.

        Patterns are grouped by ``error_type`` and sorted by frequency
        (most common first). This is the primary input for the executor's
        ``analyze_failure`` method.
        """
        groups: dict[str, list[ErrorRecord]] = {}
        for r in self._records:
            groups.setdefault(r.error_type, []).append(r)

        patterns: list[ErrorPattern] = []
        for error_type, group in groups.items():
            typical_msg = max(
                group,
                key=lambda r: sum(
                    1 for other in group if self._scorer(r, other) > 0.5
                ),
            ).message
            typical_stage = max(
                set(r.failure_stage for r in group),
                key=lambda s: sum(1 for r in group if r.failure_stage == s),
            )
            patterns.append(
                ErrorPattern(
                    error_type=error_type,
                    frequency=len(group),
                    typical_message=typical_msg,
                    typical_stage=typical_stage,
                    last_seen=max(r.timestamp for r in group),
                )
            )

        patterns.sort(key=lambda p: p.frequency, reverse=True)
        return patterns

    def get_statistics(self) -> dict[str, object]:
        """Return aggregate statistics about the error corpus.

        Useful for dashboards, telemetry, and deciding whether to escalate.
        """
        if not self._records:
            return {
                "total_errors": 0,
                "unique_types": 0,
                "most_common_type": None,
                "total_attempts": 0,
                "avg_attempts_per_error": 0.0,
                "time_span_seconds": 0.0,
            }

        types = [r.error_type for r in self._records]
        type_counts: dict[str, int] = {}
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1
        most_common = max(type_counts, key=type_counts.__getitem__)

        timestamps = [r.timestamp for r in self._records]
        return {
            "total_errors": len(self._records),
            "unique_types": len(type_counts),
            "most_common_type": most_common,
            "total_attempts": sum(r.attempt_count for r in self._records),
            "avg_attempts_per_error": round(
                sum(r.attempt_count for r in self._records) / len(self._records), 2
            ),
            "time_span_seconds": round(max(timestamps) - min(timestamps), 2),
        }

    def clear(self) -> None:
        """Remove all stored records."""
        self._records = []
        self._save()

    # ---- persistence -------------------------------------------------------

    def _save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(
                [r.to_dict() for r in self._records],
                indent=2,
                ensure_ascii=False,
            )
        )
        tmp.replace(self._path)

    def _load(self) -> None:
        assert self._path is not None
        try:
            payload = json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(payload, list):
            return
        self._records = [
            ErrorRecord.from_dict(p) for p in payload if isinstance(p, dict)
        ]


# ---------------------------------------------------------------------------
# Recovery result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecoveryResult:
    """The outcome of one recovery attempt."""

    success: bool
    strategy_used: RecoveryStrategy
    alternative_chosen: str
    tokens_spent: int
    lesson_learned: str

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "strategy_used": self.strategy_used.name,
            "alternative_chosen": self.alternative_chosen,
            "tokens_spent": self.tokens_spent,
            "lesson_learned": self.lesson_learned,
        }


# ---------------------------------------------------------------------------
# Type aliases for pluggable callables
# ---------------------------------------------------------------------------

AnalyzeFailureHook = Callable[
    [ErrorRecord, ErrorDatabase, RecoveryStrategy],
    RecoveryStrategy,
]
"""Optional hook that can override the strategy chosen by the executor."""

AlternativeGenerator = Callable[
    [str, ErrorRecord, RecoveryStrategy],
    Sequence[str],
]
"""``(task, error, strategy) -> list of alternative approach descriptions``."""

RecoveryExecutor = Callable[
    [str, RecoveryStrategy, Sequence[str]],
    RecoveryResult,
]
"""``(task, strategy, alternatives) -> RecoveryResult``."""


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------


class PivotRefineExecutor:
    """Self-healing failure recovery loop.

    The executor orchestrates four phases:

    1. **Analyze** — inspect the failure and the error database to pick a
       :class:`RecoveryStrategy`.
    2. **Generate** — produce a list of alternative approaches for PIVOT /
       DECOMPOSE strategies.
    3. **Execute** — run the recovery plan and capture the result.
    4. **Learn** — persist the outcome back to the database so future runs
       benefit from this experience.

    Each phase accepts an optional callable override so callers can inject
    LLM-backed logic, rule engines, or human-in-the-loop decisions.
    """

    def __init__(
        self,
        *,
        alternative_generator: Optional[AlternativeGenerator] = None,
        executor: Optional[RecoveryExecutor] = None,
        analyze_hook: Optional[AnalyzeFailureHook] = None,
        default_strategy: RecoveryStrategy = RecoveryStrategy.RETRY,
    ) -> None:
        self._alternative_generator = alternative_generator
        self._executor = executor
        self._analyze_hook = analyze_hook
        self._default_strategy = default_strategy

    def analyze_failure(
        self,
        error: ErrorRecord,
        error_db: ErrorDatabase,
    ) -> RecoveryStrategy:
        """Classify a failure and return the most appropriate strategy.

        The analysis considers:

        * How many times this error (or a similar one) has been seen before.
        * What ``failure_stage`` the error occurred in.
        * Whether the error has a clear textual signature.

        Callers can override the final decision by passing an
        ``analyze_hook`` to the constructor.

        Args:
            error: The failure to analyse.
            error_db: Database of historical errors for pattern matching.

        Returns:
            The chosen recovery strategy.
        """
        similar = error_db.find_similar(error, threshold=0.6)
        patterns = error_db.get_patterns()

        # Abort if the same error has been recurring beyond reason.
        if sum(s[0].attempt_count for s in similar[:5]) >= 10:
            strategy = RecoveryStrategy.ABORT
        # Escalate if we see this error type reported frequently across the DB.
        elif any(
            p.error_type == error.error_type and p.frequency >= 5
            for p in patterns
        ):
            strategy = RecoveryStrategy.ESCALATE
        # Decompose complex task-context failures.
        elif "subtask" in error.task_context.lower() or len(error.task_context) > 2000:
            strategy = RecoveryStrategy.DECOMPOSE
        # Pivot on semantic / logic errors.
        elif "logic" in error.error_type.lower() or "semantic" in error.error_type.lower():
            strategy = RecoveryStrategy.PIVOT
        # Retry everything else (transient, infrastructure, etc.).
        else:
            strategy = RecoveryStrategy.RETRY

        # Give the optional hook the final word.
        if self._analyze_hook is not None:
            strategy = self._analyze_hook(error, error_db, strategy)

        return strategy

    def generate_alternatives(
        self,
        task: str,
        error: ErrorRecord,
        strategy: RecoveryStrategy,
    ) -> list[str]:
        """Produce concrete alternative approaches for the given strategy.

        When no custom ``alternative_generator`` is provided the executor
        returns a single generic fallback suggestion. Production callers
        should always wire an LLM-backed generator so the alternatives are
        context-aware.

        Args:
            task: The original task description.
            error: The failure that triggered recovery.
            strategy: The recovery strategy selected by :meth:`analyze_failure`.

        Returns:
            A list of alternative approach descriptions.
        """
        if self._alternative_generator is not None:
            return list(self._alternative_generator(task, error, strategy))

        # Default fallback — generic alternatives keyed by strategy.
        if strategy == RecoveryStrategy.RETRY:
            return [
                f"Retry with backoff (delay before re-attempt). "
                f"Previous error: {error.error_type} — {error.message[:120]}"
            ]
        if strategy == RecoveryStrategy.PIVOT:
            return [
                f"Pivot approach for stage '{error.failure_stage}'. "
                f"Change the methodology while keeping the goal fixed.",
                f"Break the task into smaller probing steps before committing "
                f"to a full solution.",
            ]
        if strategy == RecoveryStrategy.DECOMPOSE:
            return [
                f"Decompose task by extracting the sub-task that failed at "
                f"stage '{error.failure_stage}' and solving it independently.",
            ]
        if strategy == RecoveryStrategy.ESCALATE:
            return [
                f"Escalate task with full error context: {error.error_type} "
                f"(seen {len(error.task_context)} chars of context). "
                f"Delegating to a stronger agent with broader capabilities.",
            ]
        # ABORT
        return [
            f"Abort task. Error {error.error_type} at stage "
            f"'{error.failure_stage}' is not recoverable.",
        ]

    def execute_recovery(
        self,
        task: str,
        strategy: RecoveryStrategy,
        alternatives: Sequence[str],
    ) -> RecoveryResult:
        """Run the recovery plan.

        When a custom ``executor`` callable is set (recommended for production)
        it is invoked with the task, strategy, and alternatives. Otherwise a
        placeholder result is returned with ``success=False`` and zero tokens
        spent — this ensures tests always have a valid result even when no
        executor is configured.

        Args:
            task: The original task description.
            strategy: The recovery strategy to execute.
            alternatives: Alternative approaches from :meth:`generate_alternatives`.

        Returns:
            The recovery outcome.
        """
        if self._executor is not None:
            return self._executor(task, strategy, alternatives)

        # Placeholder for callers that haven't wired a custom executor.
        chosen = alternatives[0] if alternatives else "(no alternatives)"
        return RecoveryResult(
            success=False,
            strategy_used=strategy,
            alternative_chosen=chosen,
            tokens_spent=0,
            lesson_learned=(
                f"No recovery executor configured. "
                f"Strategy was {strategy.name}, selected '{chosen[:80]}'."
            ),
        )

    def learn_from_failure(
        self,
        error: ErrorRecord,
        result: RecoveryResult,
        error_db: ErrorDatabase,
    ) -> None:
        """Persist a failure + outcome pair so the platform learns cross-run.

        The error is recorded in the database (building up the pattern library)
        and if the recovery produced a useful lesson that lesson is embedded in
        the recorded message for future similarity matching.

        Args:
            error: The original failure.
            result: The recovery outcome.
            error_db: The database to persist into.
        """
        enriched = ErrorRecord(
            error_type=error.error_type,
            message=f"{error.message} | lesson: {result.lesson_learned}",
            task_context=error.task_context,
            failure_stage=error.failure_stage,
            stack_trace=error.stack_trace,
            attempt_count=error.attempt_count + 1,
        )
        error_db.record(enriched)
