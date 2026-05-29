"""Experience extraction — distil reusable patterns from agent trajectories.

Integrates with ``ReasoningBank`` (memory/reasoning_bank.py) for lesson
promotion and ``MemoryConsolidator`` (memory/consolidator.py) for
consolidation seeding.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PatternType(str, Enum):
    """Kind of insight extracted from experience."""
    SUCCESS_STRATEGY = "success_strategy"
    FAILURE_MODE = "failure_mode"
    RECOVERY_PATH = "recovery_path"
    OPTIMIZATION = "optimization"
    WORKAROUND = "workaround"
    ANTI_PATTERN = "anti_pattern"


@dataclass(frozen=True)
class ExperienceRecord:
    """A single agent trajectory captured for learning.

    Distinct from ``rl/trajectory.py::TrajectoryRecord`` (RL-specific) and
    ``memory/reasoning_bank.py::Trajectory`` (reasoning-bank-specific). This
    record carries richer metadata for pattern extraction.
    """

    id: str
    session_id: str
    task_signature: str
    outcome: str  # "success", "failure", "partial"
    turn_count: int
    tool_calls: tuple[dict[str, Any], ...] = ()
    final_artefact: str = ""
    error_message: str = ""
    duration_ms: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def is_success(self) -> bool:
        return self.outcome == "success"

    @property
    def is_failure(self) -> bool:
        return self.outcome == "failure"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "task_signature": self.task_signature,
            "outcome": self.outcome,
            "turn_count": self.turn_count,
            "tool_calls": list(self.tool_calls),
            "final_artefact": self.final_artefact,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExperienceRecord:
        return cls(
            id=d["id"],
            session_id=d["session_id"],
            task_signature=d["task_signature"],
            outcome=d["outcome"],
            turn_count=d["turn_count"],
            tool_calls=tuple(d.get("tool_calls", [])),
            final_artefact=d.get("final_artefact", ""),
            error_message=d.get("error_message", ""),
            duration_ms=d.get("duration_ms", 0.0),
            metadata=d.get("metadata", {}),
            created_at=d.get("created_at", time.time()),
        )


@dataclass(frozen=True)
class ExtractedPattern:
    """A distilled insight from one or more experience records."""

    id: str
    pattern_type: PatternType
    title: str
    description: str
    source_record_ids: tuple[str, ...]
    confidence: float
    tags: tuple[str, ...] = ()
    suggested_action: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class ExperienceExtractor:
    """Analyses experience records and extracts reusable patterns.

    Plugs into ``ReasoningBank`` to promote patterns into lessons and
    ``MemoryConsolidator`` to seed consolidation proposals.
    """

    min_confidence: float = 0.6
    max_patterns_per_run: int = 20
    _patterns: list[ExtractedPattern] = field(default_factory=list)
    _record_count: int = 0

    def extract(self, records: Sequence[ExperienceRecord]) -> tuple[ExtractedPattern, ...]:
        """Extract patterns from a batch of experience records."""
        patterns: list[ExtractedPattern] = []
        for record in records:
            extracted = self.extract_one(record)
            patterns.extend(extracted)
        self._record_count += len(records)
        return tuple(patterns[: self.max_patterns_per_run])

    def extract_one(self, record: ExperienceRecord) -> tuple[ExtractedPattern, ...]:
        """Extract patterns from a single experience record."""
        patterns: list[ExtractedPattern] = []

        if record.is_success and record.turn_count <= 3:
            patterns.append(ExtractedPattern(
                id=uuid.uuid4().hex,
                pattern_type=PatternType.SUCCESS_STRATEGY,
                title=f"Efficient strategy for: {record.task_signature[:60]}",
                description=f"Completed in {record.turn_count} turns. "
                           f"Final artefact: {record.final_artefact[:200]}",
                source_record_ids=(record.id,),
                confidence=0.7 + (0.05 * min(record.turn_count, 4)),
                tags=_derive_tags(record),
            ))

        if record.is_failure:
            patterns.append(ExtractedPattern(
                id=uuid.uuid4().hex,
                pattern_type=PatternType.FAILURE_MODE,
                title=f"Failure on: {record.task_signature[:60]}",
                description=f"Failed after {record.turn_count} turns. "
                           f"Error: {record.error_message[:200]}",
                source_record_ids=(record.id,),
                confidence=0.6,
                suggested_action=f"Avoid approach that led to: {record.error_message[:100]}",
                tags=_derive_tags(record),
            ))

        if record.outcome == "partial":
            patterns.append(ExtractedPattern(
                id=uuid.uuid4().hex,
                pattern_type=PatternType.RECOVERY_PATH,
                title=f"Partial completion: {record.task_signature[:60]}",
                description=f"Partially completed in {record.turn_count} turns.",
                source_record_ids=(record.id,),
                confidence=0.5,
                tags=_derive_tags(record),
            ))

        self._patterns.extend(patterns)
        return tuple(patterns)

    def find_similar(self, pattern: ExtractedPattern,
                     existing: Sequence[ExtractedPattern]) -> list[ExtractedPattern]:
        """Find existing patterns similar to the given one (tag overlap)."""
        similar: list[ExtractedPattern] = []
        p_tags = set(pattern.tags)
        for ep in existing:
            if ep.id == pattern.id:
                continue
            overlap = p_tags & set(ep.tags)
            if overlap:
                similar.append(ep)
        return similar

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "patterns_extracted": len(self._patterns),
            "records_processed": self._record_count,
            "by_type": _count_by_type(self._patterns),
        }


def _derive_tags(record: ExperienceRecord) -> tuple[str, ...]:
    tags: list[str] = [record.outcome]
    if record.turn_count <= 2:
        tags.append("fast")
    elif record.turn_count >= 10:
        tags.append("slow")
    if record.error_message:
        tags.append("error")
    return tuple(tags)


def _count_by_type(patterns: list[ExtractedPattern]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in patterns:
        key = p.pattern_type.value
        counts[key] = counts.get(key, 0) + 1
    return counts
