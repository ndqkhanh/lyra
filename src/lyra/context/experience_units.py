"""
Typed Experience Units — ACON-style memory evolution for Lyra's adaptive fabric.

Defines the four experience unit types (Memory, Strategy, Workflow, Skill) that
form the basis of ACE-style evolving contexts. Units are stored, scored, and
pruned by UnitLibrary, while the Scheduler allocates generation budget to the
weakest library types.

Enhancements in v8.1
--------------------
- ``UnitScoring``: Tracks success rate per unit type across all units of that
  type, providing aggregate quality signals for ACE-style memory evolution.
- ``prune_by_usage_threshold()``: Removes units that fall below a minimum
  usage count, complementing the existing age-based pruning.
- Cross-session persistence: ``save()`` / ``load()`` methods on ``UnitLibrary``
  for JSON-based survival across session restarts.

References
----------
- ACON (Adaptive Context Optimization): evolves context composition per task
  type by treating context as typed experience units.
- ACE (Adaptive Context Engine): evolving contexts where each unit type
  captures a different dimension of agent experience.
- IdleSpec: speculative planning that pre-computes likely next context during
  tool-waiting periods.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ExperienceUnitType(str, Enum):
    """The four types of experience units in the ACE architecture.

    - MEMORY:   Stored observations, key facts, and historical context.
    - STRATEGY: Approach patterns — how tasks of this type are best tackled.
    - WORKFLOW: Step sequences — ordering of tools and reasoning for a task.
    - SKILL:    Reusable competency — distilled knowledge for a sub-task.
    """

    MEMORY = "memory"
    STRATEGY = "strategy"
    WORKFLOW = "workflow"
    SKILL = "skill"


@dataclass
class TypedExperienceUnit:
    """A single typed experience unit.

    Attributes:
        unit_id:      Unique identifier for deduplication.
        unit_type:    One of MEMORY, STRATEGY, WORKFLOW, SKILL.
        content:      The unit's data (serializable text or structured dict).
        source:       How this unit was created (e.g. 'compaction', 'speculation',
                      'evolution', 'manual').
        task_type:    The task category this unit was derived from
                      (e.g. 'code_search', 'debug', 'plan').
        score:        Cumulative usage score — incremented on successful reuse.
        created_at:   Timestamp of first creation.
        last_used_at: Timestamp of most recent successful reuse.
        use_count:    Number of times this unit has been successfully reused.
    """

    unit_id: str
    unit_type: ExperienceUnitType
    content: str
    source: str = "manual"
    task_type: str = "general"
    score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0

    def record_use(self, feedback: float = 1.0) -> None:
        """Record a successful reuse and update the score.

        Uses an exponential moving average so recent feedback is weighted
        more heavily than old feedback.

        Args:
            feedback: Quality signal for this reuse (0.0 = useless, 1.0 = perfect).
        """
        alpha = 0.3  # EMA weight for new feedback
        self.score = (1 - alpha) * self.score + alpha * feedback
        self.use_count += 1
        self.last_used_at = datetime.now(timezone.utc)

    def is_stale(
        self,
        max_age_days: float = 30.0,
        min_uses: int = 1,
        score_threshold: float = 0.1,
    ) -> bool:
        """Check if this unit is stale and should be pruned.

        A unit is stale if ALL of these hold:
        1. It was last used more than ``max_age_days`` ago.
        2. It has been used fewer than ``min_uses`` times.
        3. Its score is below ``score_threshold``.

        Args:
            max_age_days:   Age beyond which a unit is candidate for pruning.
            min_uses:       Minimum uses to avoid pruning regardless of age.
            score_threshold: Score below which a unit is candidate for pruning.

        Returns:
            True if the unit should be pruned.
        """
        now = datetime.now(timezone.utc)
        age_days = (now - self.last_used_at).total_seconds() / 86400
        return age_days > max_age_days and self.use_count < min_uses and self.score < score_threshold

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict for persistence."""
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type.value,
            "content": self.content,
            "source": self.source,
            "task_type": self.task_type,
            "score": self.score,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat(),
            "use_count": self.use_count,
        }


class UnitLibrary:
    """Stores, scores, and prunes typed experience units.

    The library maintains separate collections for each ExperienceUnitType
    and provides operations for insertion, retrieval by task type, scoring
    on reuse, and pruning of stale entries.

    Usage::

        lib = UnitLibrary()
        unit = TypedExperienceUnit(
            unit_id="mem-001",
            unit_type=ExperienceUnitType.MEMORY,
            content="Module X is the entry point",
            task_type="code_search",
        )
        lib.add(unit)
        matches = lib.find_by_task("code_search")
        lib.score_unit(unit_id="mem-001", feedback=0.9)
    """

    def __init__(self) -> None:
        self._units: dict[str, TypedExperienceUnit] = {}
        self._by_type: dict[ExperienceUnitType, set[str]] = {
            t: set() for t in ExperienceUnitType
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_units(self) -> int:
        """Number of units currently in the library."""
        return len(self._units)

    def add(self, unit: TypedExperienceUnit) -> None:
        """Add a unit to the library (replaces if unit_id exists).

        Args:
            unit: The experience unit to add.
        """
        existing = self._units.get(unit.unit_id)
        if existing:
            self._by_type[existing.unit_type].discard(unit.unit_id)

        self._units[unit.unit_id] = unit
        self._by_type[unit.unit_type].add(unit.unit_id)

    def get(self, unit_id: str) -> TypedExperienceUnit | None:
        """Retrieve a unit by ID.

        Args:
            unit_id: The unique identifier.

        Returns:
            The unit, or None if not found.
        """
        return self._units.get(unit_id)

    def find_by_task(self, task_type: str) -> list[TypedExperienceUnit]:
        """Return all units associated with a given task type, sorted by
        score descending (highest first).

        Args:
            task_type: Task category to filter by (e.g. 'code_search').

        Returns:
            List of matching units.
        """
        matches = [
            u for u in self._units.values()
            if u.task_type == task_type
        ]
        matches.sort(key=lambda u: u.score, reverse=True)
        return matches

    def find_by_type(self, unit_type: ExperienceUnitType) -> list[TypedExperienceUnit]:
        """Return all units of a given type, sorted by score descending.

        Args:
            unit_type: The unit type to filter by.

        Returns:
            List of matching units.
        """
        ids = self._by_type.get(unit_type, set())
        units = [self._units[uid] for uid in ids if uid in self._units]
        units.sort(key=lambda u: u.score, reverse=True)
        return units

    def score_unit(self, unit_id: str, feedback: float = 1.0) -> float | None:
        """Record a reuse and update the unit's score.

        Args:
            unit_id:  The unit to score.
            feedback: Quality signal for this reuse (0.0 to 1.0).

        Returns:
            The new score, or None if unit_id was not found.
        """
        unit = self._units.get(unit_id)
        if unit is None:
            return None
        unit.record_use(feedback)
        return unit.score

    def prune_stale(
        self,
        max_age_days: float = 30.0,
        min_uses: int = 1,
        score_threshold: float = 0.1,
    ) -> int:
        """Remove stale units and return the count of pruned entries.

        Args:
            max_age_days:    Age beyond which a unit is candidate for pruning.
            min_uses:        Minimum uses to avoid pruning.
            score_threshold: Score below which a unit is candidate for pruning.

        Returns:
            Number of units pruned.
        """
        stale_ids = [
            uid
            for uid, unit in self._units.items()
            if unit.is_stale(
                max_age_days=max_age_days,
                min_uses=min_uses,
                score_threshold=score_threshold,
            )
        ]
        for uid in stale_ids:
            unit = self._units[uid]
            self._by_type[unit.unit_type].discard(uid)
            del self._units[uid]
        return len(stale_ids)

    def stats(self) -> dict[str, Any]:
        """Return summary statistics about the library.

        Returns:
            Dict with total count, per-type counts, and average scores.
        """
        per_type: dict[str, dict[str, Any]] = {}
        for t in ExperienceUnitType:
            units = self.find_by_type(t)
            per_type[t.value] = {
                "count": len(units),
                "avg_score": round(sum(u.score for u in units) / max(len(units), 1), 3),
            }
        return {
            "total_units": self.total_units,
            "per_type": per_type,
        }


class Scheduler:
    """Allocates generation budget to the weakest library types.

    The scheduler inspects the UnitLibrary and decides which experience unit
    types need more generation budget. Types with low average score or few
    units receive a larger allocation.

    Usage::

        lib = UnitLibrary()
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(lib)
        # budget: {"memory": 0.2, "strategy": 0.4, "workflow": 0.25, "skill": 0.15}
    """

    # Baseline allocation when a type has no units yet
    _BASE_ALLOCATION: float = 0.15

    def allocate_budget(self, library: UnitLibrary) -> dict[str, float]:
        """Allocate budget fractions to each unit type.

        Types with low average score or zero units receive a larger slice.
        Returns a dict mapping type names to fractions that sum to 1.0.

        Args:
            library: The unit library to inspect.

        Returns:
            Dict e.g. {"memory": 0.25, "strategy": 0.30, ...}.
        """
        stats = library.stats()
        raw_weights: dict[str, float] = {}

        for type_name, info in stats["per_type"].items():
            count = info["count"]
            avg_score = info["avg_score"]

            if count == 0:
                # No units yet — this type needs initial generation budget
                raw_weights[type_name] = self._BASE_ALLOCATION + 0.25
            else:
                # Lower average score -> more budget needed
                need = 1.0 - avg_score
                raw_weights[type_name] = max(0.05, need)

        # Normalize to sum to 1.0
        total = sum(raw_weights.values())
        if total == 0:
            return {t: 0.25 for t in raw_weights}

        normalized = {
            name: round(weight / total, 3)
            for name, weight in raw_weights.items()
        }

        # Ensure we sum to 1.0 (fix rounding)
        diff = 1.0 - sum(normalized.values())
        if diff != 0.0 and normalized:
            # Add rounding remainder to the type with largest weight
            largest = max(normalized, key=normalized.get)  # type: ignore[arg-type]
            normalized[largest] = round(normalized[largest] + diff, 3)

        return normalized


# ---------------------------------------------------------------------------
# UnitScoring — ACE integration
# ---------------------------------------------------------------------------


@dataclass
class UnitScoring:
    """Tracks success rate per unit type across the UnitLibrary.

    Provides aggregate quality signals that ACE uses to decide which unit
    types need more generation budget and which are performing well.

    Attributes:
        unit_type:  The experience unit type this scoring is for.
        successes:  Number of successful (high-quality) uses.
        failures:   Number of failed (low-quality) uses.
        total_score: Cumulative score across all units of this type.
    """

    unit_type: ExperienceUnitType
    successes: int = 0
    failures: int = 0
    total_score: float = 0.0

    @property
    def total_attempts(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        """Fraction of attempts that were successful (0.0-1.0)."""
        if self.total_attempts == 0:
            return 0.0
        return self.successes / self.total_attempts

    @property
    def avg_score(self) -> float:
        """Average score per unit of this type."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_score / self.total_attempts

    def record_use(self, feedback: float, threshold: float = 0.6) -> None:
        """Record a use, classifying as success or failure.

        Args:
            feedback:  Quality signal (0.0-1.0).
            threshold: Score above which is considered a success.
        """
        self.total_score += feedback
        if feedback >= threshold:
            self.successes += 1
        else:
            self.failures += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_type": self.unit_type.value,
            "successes": self.successes,
            "failures": self.failures,
            "total_score": self.total_score,
            "success_rate": self.success_rate,
            "avg_score": self.avg_score,
        }


# ---------------------------------------------------------------------------
# Cross-session persistence helpers
# ---------------------------------------------------------------------------


def _units_to_serializable(units: dict[str, TypedExperienceUnit]) -> list[dict[str, Any]]:
    """Convert the unit dictionary to a list of serializable dicts."""
    return [u.to_dict() for u in units.values()]


def _units_from_serializable(data: list[dict[str, Any]]) -> dict[str, TypedExperienceUnit]:
    """Rehydrate units from a list of serialized dicts."""
    units: dict[str, TypedExperienceUnit] = {}
    for d in data:
        try:
            unit = TypedExperienceUnit(
                unit_id=d["unit_id"],
                unit_type=ExperienceUnitType(d["unit_type"]),
                content=d["content"],
                source=d.get("source", "manual"),
                task_type=d.get("task_type", "general"),
                score=float(d.get("score", 0.0)),
                created_at=datetime.fromisoformat(d["created_at"]),
                last_used_at=datetime.fromisoformat(d["last_used_at"]),
                use_count=int(d.get("use_count", 0)),
            )
            units[unit.unit_id] = unit
        except (KeyError, ValueError, TypeError) as exc:
            # Skip malformed entries
            continue
    return units


# ---------------------------------------------------------------------------
# Enhanced UnitLibrary — new module-level methods
# ---------------------------------------------------------------------------


def library_save_to_json(
    library: UnitLibrary,
    path: str | Path,
) -> None:
    """Save all units in *library* to a JSON file for cross-session persistence.

    Args:
        library: The UnitLibrary to persist.
        path:    File path for the JSON output.
    """
    data = _units_to_serializable(library._units)
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(json.dumps(data, indent=2))


def library_load_from_json(
    library: UnitLibrary,
    path: str | Path,
) -> int:
    """Load units from a JSON file into *library*.

    Existing units with the same ``unit_id`` are replaced.

    Args:
        library: The UnitLibrary to load into.
        path:    File path to the JSON file.

    Returns:
        Number of units loaded.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return 0
    data = json.loads(path_obj.read_text())
    if not isinstance(data, list):
        return 0
    units = _units_from_serializable(data)
    for unit in units.values():
        library.add(unit)
    return len(units)


def library_prune_by_usage_threshold(
    library: UnitLibrary,
    min_use_count: int = 2,
    task_type: str | None = None,
) -> int:
    """Prune units that have been used fewer than *min_use_count* times.

    Optionally restricts to a specific ``task_type``. This complements the
    age-based ``prune_stale()`` method.

    Args:
        library:      The UnitLibrary to prune.
        min_use_count: Minimum number of uses to avoid pruning.
        task_type:    If set, only prunes units of this task type.

    Returns:
        Number of units pruned.
    """
    to_prune: list[str] = []
    for uid, unit in library._units.items():
        if task_type is not None and unit.task_type != task_type:
            continue
        if unit.use_count < min_use_count:
            to_prune.append(uid)

    for uid in to_prune:
        unit = library._units[uid]
        library._by_type[unit.unit_type].discard(uid)
        del library._units[uid]

    return len(to_prune)


def library_get_scoring(
    library: UnitLibrary,
) -> dict[str, UnitScoring]:
    """Return :class:`UnitScoring` data for each unit type in the library.

    Args:
        library: The UnitLibrary to score.

    Returns:
        Dict mapping ``ExperienceUnitType`` value strings to ``UnitScoring``.
    """
    scores: dict[ExperienceUnitType, UnitScoring] = {}
    for t in ExperienceUnitType:
        scores[t] = UnitScoring(unit_type=t)

    for unit in library._units.values():
        sc = scores.get(unit.unit_type)
        if sc is not None:
            sc.total_score += unit.score
            if unit.use_count > 0:
                avg = unit.score / max(unit.use_count, 1)
                sc.record_use(feedback=avg)

    return {k.value: v for k, v in scores.items()}


__all__ = [
    "ExperienceUnitType",
    "Scheduler",
    "TypedExperienceUnit",
    "UnitLibrary",
    "UnitScoring",
    "library_save_to_json",
    "library_load_from_json",
    "library_prune_by_usage_threshold",
    "library_get_scoring",
]
