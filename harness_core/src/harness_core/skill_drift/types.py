"""Types for skill_drift — invocation records, alerts, and policy."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SkillInvocation:
    """One observed use of a promoted skill.

    >>> i = SkillInvocation.create(
    ...     skill_id="fix-imports", succeeded=True, score=1.0,
    ... )
    >>> i.skill_id
    'fix-imports'
    """

    invocation_id: str
    skill_id: str
    succeeded: bool
    score: float
    timestamp: float
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.skill_id:
            raise ValueError("skill_id must be non-empty")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")

    @classmethod
    def create(
        cls,
        *,
        skill_id: str,
        succeeded: bool,
        score: float = 1.0,
        metadata: Optional[dict] = None,
        invocation_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> "SkillInvocation":
        return cls(
            invocation_id=invocation_id or str(uuid.uuid4()),
            skill_id=skill_id,
            succeeded=succeeded,
            score=min(1.0, max(0.0, score)),
            timestamp=timestamp if timestamp is not None else time.time(),
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class DriftPolicy:
    """Thresholds for drift detection.

    Defaults bias toward stable production: a 20-invocation baseline avoids
    triggering on the first few flakes; a 10pp drop is a warning;
    a 30pp drop is critical.

    Fields:
        min_baseline_invocations: don't compare until the skill has
            this many invocations of established history.
        recent_window: compare against the last N invocations.
        warning_drift: drift in (warning_drift, critical_drift] → severity
            ``"warning"``.
        critical_drift: drift > critical_drift → severity ``"critical"``.
        info_drift: any drift below ``warning_drift`` and above ``info_drift``
            → severity ``"info"`` (logged, not alerted).
    """

    min_baseline_invocations: int = 20
    recent_window: int = 10
    info_drift: float = 0.05
    warning_drift: float = 0.10
    critical_drift: float = 0.30

    def __post_init__(self) -> None:
        if self.min_baseline_invocations < 2:
            raise ValueError(
                f"min_baseline_invocations must be >= 2, got "
                f"{self.min_baseline_invocations}"
            )
        if self.recent_window < 1:
            raise ValueError(
                f"recent_window must be >= 1, got {self.recent_window}"
            )
        # Ordering: 0 <= info_drift <= warning_drift <= critical_drift <= 1.
        if not (
            0.0 <= self.info_drift
            <= self.warning_drift
            <= self.critical_drift
            <= 1.0
        ):
            raise ValueError(
                "drift thresholds must satisfy "
                "0 <= info_drift <= warning_drift <= critical_drift <= 1, "
                f"got {self.info_drift}, {self.warning_drift}, "
                f"{self.critical_drift}"
            )


@dataclass(frozen=True)
class DriftAlert:
    """One detected drift event for a skill."""

    skill_id: str
    baseline_rate: float
    recent_rate: float
    drift: float  # baseline_rate - recent_rate (positive = degradation)
    n_baseline: int
    n_recent: int
    severity: str  # "info" | "warning" | "critical"
    note: str = ""
    detected_at: float = 0.0

    def __post_init__(self) -> None:
        if self.severity not in ("info", "warning", "critical"):
            raise ValueError(
                f"severity must be info|warning|critical, got {self.severity!r}"
            )


__all__ = ["DriftAlert", "DriftPolicy", "SkillInvocation"]
