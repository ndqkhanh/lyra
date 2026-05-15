"""Types for continuous_learning — EditEvent, LearnedPreference, Protocols."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass(frozen=True)
class EditEvent:
    """One observed user edit to an agent output.

    The PRELUDE / CIPHER pattern: when a user edits something the agent
    produced, that edit *is* the gradient signal. Recording the
    (agent_output → user_edit) pair plus context lets a downstream
    extractor learn durable preferences.

    >>> e = EditEvent.create(
    ...     agent_output="The user has requested ...",
    ...     user_edit="The user requested ...",
    ...     user_id="alice",
    ... )
    >>> e.user_id
    'alice'
    """

    event_id: str
    agent_output: str
    user_edit: str
    user_id: str
    timestamp: float
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.user_id:
            raise ValueError("user_id must be non-empty")

    @classmethod
    def create(
        cls,
        *,
        agent_output: str,
        user_edit: str,
        user_id: str,
        context: Optional[dict] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> "EditEvent":
        return cls(
            event_id=event_id or str(uuid.uuid4()),
            agent_output=agent_output,
            user_edit=user_edit,
            user_id=user_id,
            timestamp=timestamp if timestamp is not None else time.time(),
            context=dict(context or {}),
        )

    @property
    def shortened(self) -> bool:
        """True iff the user's edit is shorter than the agent's output."""
        return len(self.user_edit) < len(self.agent_output)

    @property
    def lengthened(self) -> bool:
        """True iff the user's edit is longer than the agent's output."""
        return len(self.user_edit) > len(self.agent_output)

    @property
    def length_delta_chars(self) -> int:
        """Character delta (positive = lengthened; negative = shortened)."""
        return len(self.user_edit) - len(self.agent_output)


@dataclass(frozen=True)
class LearnedPreference:
    """A durable preference distilled from one or more edits.

    Examples:
        - "user prefers commit messages under 60 characters" (length pref)
        - "user replaces 'utilize' with 'use'" (vocabulary substitution)
        - "user removes emoji from output" (tone preference)
    """

    preference_id: str
    rule: str
    user_id: str
    confidence: float
    n_supporting_edits: int
    tags: tuple[str, ...] = field(default_factory=tuple)
    discovered_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.preference_id:
            raise ValueError("preference_id must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        if self.n_supporting_edits < 1:
            raise ValueError(
                f"n_supporting_edits must be >= 1, got {self.n_supporting_edits}"
            )

    @classmethod
    def create(
        cls,
        *,
        rule: str,
        user_id: str,
        confidence: float,
        n_supporting_edits: int,
        tags: tuple[str, ...] = (),
        metadata: Optional[dict] = None,
        preference_id: Optional[str] = None,
        discovered_at: Optional[float] = None,
    ) -> "LearnedPreference":
        return cls(
            preference_id=preference_id or str(uuid.uuid4()),
            rule=rule,
            user_id=user_id,
            confidence=min(1.0, max(0.0, confidence)),
            n_supporting_edits=n_supporting_edits,
            tags=tuple(tags),
            discovered_at=discovered_at if discovered_at is not None else time.time(),
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class LearningReport:
    """Outcome of one learning pass."""

    n_edits_examined: int
    n_preferences_learned: int
    preferences: tuple[LearnedPreference, ...] = field(default_factory=tuple)
    preference_witness_ids: tuple[str, ...] = field(default_factory=tuple)
    preference_memory_ids: tuple[str, ...] = field(default_factory=tuple)


class PreferenceExtractor(Protocol):
    """Distill :class:`LearnedPreference` records from a list of edits."""

    def extract(self, edits: list[EditEvent]) -> list[LearnedPreference]: ...


__all__ = [
    "EditEvent",
    "LearnedPreference",
    "LearningReport",
    "PreferenceExtractor",
]
