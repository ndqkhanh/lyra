"""
Frozen dataclass models for Lyra personalization system.

Implements SAGER-inspired two-representation architecture:
- Rich internal representation with complete user model
- Compact injection representation (~30-200 tokens)

And SPARK-inspired tripartite memory:
- Working memory (session-scoped)
- Episodic memory (recent interactions)
- Semantic memory (long-term knowledge)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SkillLevel(str, Enum):
    """Assessed skill level for a domain."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class AutonomyLevel(str, Enum):
    """Level of autonomous decision-making allowed."""
    FULLY_AUTONOMOUS = "fully_autonomous"
    SUGGEST_ONLY = "suggest_only"
    MANUAL = "manual"


class CommunicationStyle(str, Enum):
    """Communication style dimensions."""
    CONCISE = "concise"
    BALANCED = "balanced"
    VERBOSE = "verbose"
    TECHNICAL = "technical"
    EDUCATIONAL = "educational"


@dataclass(frozen=True)
class InteractionRecord:
    """
    A single interaction between the user and the agent.

    Attributes:
        id: Unique identifier.
        timestamp: When the interaction occurred.
        session_id: Session this interaction belongs to.
        type: Type of interaction (query, command, feedback, etc.).
        content: The interaction content.
        outcome: What resulted from the interaction.
        importance: Importance score 0.0-1.0.
        metadata: Additional structured data.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    type: str = "query"
    content: str = ""
    outcome: str | None = None
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(
                f"Importance must be 0.0-1.0, got {self.importance}"
            )


@dataclass(frozen=True)
class CompactEmbedding:
    """
    Compact injection representation (~30-200 tokens).

    This is the slim user representation injected at inference time,
    designed to not consume significant context budget.
    """

    user_id: str
    vector: list[float] = field(default_factory=list)
    version: int = 1
    compressed_tokens: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate embedding dimension."""
        if self.vector and len(self.vector) < 8:
            logger.warning(
                "Compact embedding dimension (%d) is very low",
                len(self.vector),
            )

    @property
    def token_estimate(self) -> int:
        """Estimate token count from compressed representation."""
        if self.compressed_tokens:
            return max(30, len(self.compressed_tokens.split()))
        return 30


@dataclass(frozen=True)
class RichRepresentation:
    """
    Rich internal representation of a user.

    Contains the complete user model including detailed preferences,
    full interaction history, assessed skill levels, and communication
    style. This is the "heavy" representation used for offline analysis.
    """

    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    skill_levels: dict[str, SkillLevel] = field(default_factory=dict)
    communication_style: CommunicationStyle = CommunicationStyle.BALANCED
    goals: list[str] = field(default_factory=list)
    interaction_history: list[InteractionRecord] = field(default_factory=list)
    conventions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_interactions(self) -> int:
        """Total number of interactions recorded."""
        return len(self.interaction_history)


@dataclass(frozen=True)
class WorkingMemory:
    """
    Session-scoped working memory with TTL-based entries.

    Working memory holds the current session context: active task,
    recent tool calls, and short-term state. Entries expire after
    a configurable TTL.
    """

    entries: dict[str, str] = field(default_factory=dict)
    active_task: str | None = None
    recent_tool_calls: list[str] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    ttl: timedelta = field(default_factory=lambda: timedelta(hours=1))
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if this working memory session has exceeded TTL."""
        return datetime.now() - self.created_at > self.ttl


@dataclass(frozen=True)
class EpisodicMemory:
    """
    Episodic memory storing recent interactions with importance scoring.

    Contains records of specific events, conversations, and resolved
    issues from recent project interactions. Entries are importance-scored
    for pruning decisions.
    """

    records: list[InteractionRecord] = field(default_factory=list)
    last_consolidated: datetime | None = None
    max_records: int = 1000
    importance_threshold: float = 0.3
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def high_importance_records(self) -> list[InteractionRecord]:
        """Return records with importance above threshold."""
        return [
            r for r in self.records
            if r.importance >= self.importance_threshold
        ]


@dataclass(frozen=True)
class SemanticMemory:
    """
    Semantic memory storing long-term user knowledge.

    Holds stable facts about the user: programming conventions,
    domain expertise, preferences, and long-term goals. This is the
    most durable memory tier.
    """

    user_id: str = ""
    preferences: dict[str, Any] = field(default_factory=dict)
    conventions: list[str] = field(default_factory=list)
    domain_expertise: dict[str, SkillLevel] = field(default_factory=dict)
    long_term_goals: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UserProfile:
    """
    Complete user profile combining all representation layers.

    This is the top-level model that ties together the rich
    representation, compact embedding, and tripartite memory.
    """

    user_id: str
    rich_repr: RichRepresentation = field(default_factory=lambda: RichRepresentation(user_id=""))
    compact_embedding: CompactEmbedding | None = None
    working_memory: WorkingMemory = field(default_factory=WorkingMemory)
    episodic_memory: EpisodicMemory = field(default_factory=EpisodicMemory)
    semantic_memory: SemanticMemory = field(default_factory=SemanticMemory)
    autonomy_level: AutonomyLevel = AutonomyLevel.SUGGEST_ONLY
    trust_score: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
