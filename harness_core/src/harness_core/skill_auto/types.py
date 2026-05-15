"""Skill candidate + promotion verdict types."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Optional


def _candidate_id(*, name: str, action_template: tuple[str, ...]) -> str:
    """Stable hash of name + action template — collisions are rare and harmless."""
    payload = f"{name}|{'|'.join(action_template)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SkillCandidate:
    """A pattern observed across trajectories — candidate for promotion.

    >>> c = SkillCandidate.create(
    ...     name="fix-imports",
    ...     task_signature_pattern="refactor:imports",
    ...     action_template=("read", "edit", "test"),
    ...     source_trajectories=("t1", "t2", "t3"),
    ...     occurrence_count=3,
    ...     success_rate=0.67,
    ... )
    >>> c.candidate_id  # auto-computed
    '...'
    """

    candidate_id: str
    name: str
    task_signature_pattern: str
    action_template: tuple[str, ...]
    source_trajectories: tuple[str, ...]
    occurrence_count: int
    success_rate: float
    extracted_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.action_template:
            raise ValueError("action_template must be non-empty")
        if self.occurrence_count < 1:
            raise ValueError(f"occurrence_count must be >= 1, got {self.occurrence_count}")
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError(f"success_rate must be in [0, 1], got {self.success_rate}")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        task_signature_pattern: str,
        action_template: tuple[str, ...],
        source_trajectories: tuple[str, ...],
        occurrence_count: int,
        success_rate: float,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "SkillCandidate":
        """Construct with auto-computed candidate_id."""
        return cls(
            candidate_id=_candidate_id(name=name, action_template=action_template),
            name=name,
            task_signature_pattern=task_signature_pattern,
            action_template=action_template,
            source_trajectories=source_trajectories,
            occurrence_count=occurrence_count,
            success_rate=success_rate,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class PromotionVerdict:
    """Decision on whether a candidate is promoted to a real skill."""

    candidate: SkillCandidate
    promoted: bool
    eval_score: float  # held-out eval score (0..1)
    surrogate_passed: bool
    reason: str = ""
    judged_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not 0.0 <= self.eval_score <= 1.0:
            raise ValueError(f"eval_score must be in [0, 1], got {self.eval_score}")


__all__ = ["PromotionVerdict", "SkillCandidate"]
