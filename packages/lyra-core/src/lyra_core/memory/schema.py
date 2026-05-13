"""Unified Fragment schema for Lyra's shared-memory layer (Phase M1).

Defines the canonical data models used across all four memory tiers:

  T0 Working   — live context window (compaction-managed, not persisted)
  T1 Session   — per-session episodic buffer (LRU, ~32 fragments)
  T2 Semantic  — repo-knowledge facts (continuously refreshed)
  T2 Procedural— decisions, skills, ADRs (append-only, supersession)
  T3 User      — private preferences (markdown-first)
  T3 Team      — shared team rules (markdown + git-synced)

All memory operations (Encoder, Writer, Retriever, ForgetPolicy,
SubAgentDigest broadcast, access-policy graph) speak this schema.

Research grounding:
  - CoALA (Sumers et al. TMLR 2024) — 4-tier working/episodic/semantic/
    procedural split.
  - Graphiti/Zep — bi-temporal valid_from / invalid_at per-fragment.
  - Collaborative Memory (Rezazadeh et al. ICLR 2026) — immutable
    provenance + bipartite access graph.
  - SRMT (Sagirova et al. ICLR 2025) — SubAgentDigest broadcast as the
    closed-LLM analog of pooled-memory cross-attention.
  - FluxMem (Lu et al. ICML 2026) — three-tier STIM/MTEM/LTSM hierarchy.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MemoryTier(str, Enum):
    T0_WORKING = "t0_working"
    T1_SESSION = "t1_session"
    T2_SEMANTIC = "t2_semantic"
    T2_PROCEDURAL = "t2_procedural"
    T3_USER = "t3_user"
    T3_TEAM = "t3_team"


class FragmentType(str, Enum):
    FACT = "fact"               # "auth uses JWT, key AUTH_JWT_SECRET"
    DECISION = "decision"       # rationale + conclusion, bi-temporal
    PREFERENCE = "preference"   # user-level preference
    SKILL = "skill"             # executable snippet (Voyager-style)
    OBSERVATION = "observation" # low-confidence, ephemeral


VisibilityScope = Literal["private", "task", "project", "team"]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@dataclass
class Provenance:
    """Immutable authorship record for every fragment.

    Every fragment knows which agent wrote it, which session/task it
    came from, which tools and resources were consulted. Required by the
    Collaborative Memory access-policy graph.
    """

    agent_id: str
    session_id: str
    user_id: str = "local"
    model: str | None = None
    task_id: str | None = None
    tool_calls: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model": self.model,
            "task_id": self.task_id,
            "tool_calls": list(self.tool_calls),
            "resources": list(self.resources),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Provenance":
        return cls(
            agent_id=d["agent_id"],
            session_id=d["session_id"],
            user_id=d.get("user_id", "local"),
            model=d.get("model"),
            task_id=d.get("task_id"),
            tool_calls=list(d.get("tool_calls", [])),
            resources=list(d.get("resources", [])),
        )


# ---------------------------------------------------------------------------
# Fragment — the atomic unit of memory
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class Fragment:
    """One atomic unit of persistent memory.

    Bi-temporal: valid_from / invalid_at (Graphiti-style). A fragment is
    *currently valid* when invalid_at is None. Supersession preserves
    the audit chain — old fragments are archived, not deleted.

    DECISION fragments MUST include "rationale" in structured — this is
    the critical missing field in all current memory systems (design
    proposal §12 open question 4).
    """

    id: str
    tier: MemoryTier
    type: FragmentType
    content: str                      # ≤200 chars, dense, natural-language
    provenance: Provenance
    visibility: VisibilityScope = "private"

    # Type-specific structured payload. DECISION must include "rationale".
    structured: dict[str, Any] = field(default_factory=dict)

    # Extracted entities (noun-phrases / symbols) for entity-match retrieval
    entities: list[str] = field(default_factory=list)

    # Dense embedding — set by Encoder, None until embedded
    embedding: list[float] | None = field(default=None, repr=False)

    # Confidence in [0, 1]; OBSERVATION defaults to 0.5
    confidence: float = 0.7

    # Pinned fragments are never evicted by ForgetPolicy
    pinned: bool = False

    # Bi-temporal validity window
    valid_from: datetime = field(default_factory=_now)
    invalid_at: datetime | None = None     # None = currently valid
    created_at: datetime = field(default_factory=_now)

    # Supersession chain (A-MEM Zettelkasten + Graphiti invalidation)
    supersedes: list[str] = field(default_factory=list)   # ids this replaces
    related: list[str] = field(default_factory=list)       # sibling links

    # Access telemetry (ForgetPolicy utility scoring)
    access_count: int = 0
    last_accessed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Fragment.id must be non-empty")
        if not self.content:
            raise ValueError("Fragment.content must be non-empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        if self.type is FragmentType.DECISION and "rationale" not in self.structured:
            raise ValueError(
                "DECISION fragments must include structured['rationale']"
            )

    @property
    def is_valid(self) -> bool:
        """True when this fragment is currently active (not superseded)."""
        return self.invalid_at is None

    def invalidate(self, at: datetime | None = None) -> None:
        """Mark fragment invalid (superseded or forgotten)."""
        self.invalid_at = at or _now()

    def touch(self) -> None:
        """Record a retrieval access for ForgetPolicy scoring."""
        self.access_count += 1
        self.last_accessed_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier.value,
            "type": self.type.value,
            "content": self.content,
            "provenance": self.provenance.to_dict(),
            "visibility": self.visibility,
            "structured": self.structured,
            "entities": list(self.entities),
            "confidence": self.confidence,
            "pinned": self.pinned,
            "valid_from": self.valid_from.isoformat(),
            "invalid_at": self.invalid_at.isoformat() if self.invalid_at else None,
            "created_at": self.created_at.isoformat(),
            "supersedes": list(self.supersedes),
            "related": list(self.related),
            "access_count": self.access_count,
            "last_accessed_at": (
                self.last_accessed_at.isoformat() if self.last_accessed_at else None
            ),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Fragment":
        def _dt(v: str | None) -> datetime | None:
            return datetime.fromisoformat(v) if v else None

        return cls(
            id=d["id"],
            tier=MemoryTier(d["tier"]),
            type=FragmentType(d["type"]),
            content=d["content"],
            provenance=Provenance.from_dict(d["provenance"]),
            visibility=d.get("visibility", "private"),
            structured=dict(d.get("structured", {})),
            entities=list(d.get("entities", [])),
            confidence=float(d.get("confidence", 0.7)),
            pinned=bool(d.get("pinned", False)),
            valid_from=datetime.fromisoformat(d["valid_from"]),
            invalid_at=_dt(d.get("invalid_at")),
            created_at=datetime.fromisoformat(d["created_at"]),
            supersedes=list(d.get("supersedes", [])),
            related=list(d.get("related", [])),
            access_count=int(d.get("access_count", 0)),
            last_accessed_at=_dt(d.get("last_accessed_at")),
        )

    @classmethod
    def make(
        cls,
        *,
        tier: MemoryTier,
        type: FragmentType,
        content: str,
        provenance: Provenance,
        visibility: VisibilityScope = "private",
        structured: dict[str, Any] | None = None,
        entities: list[str] | None = None,
        confidence: float | None = None,
        pinned: bool = False,
    ) -> "Fragment":
        """Convenience constructor — generates id and timestamps."""
        if confidence is None:
            confidence = 0.5 if type is FragmentType.OBSERVATION else 0.7
        return cls(
            id=str(uuid.uuid4()),
            tier=tier,
            type=type,
            content=content,
            provenance=provenance,
            visibility=visibility,
            structured=structured or {},
            entities=entities or [],
            confidence=confidence,
            pinned=pinned,
        )


# ---------------------------------------------------------------------------
# ConflictEvent
# ---------------------------------------------------------------------------


@dataclass
class ConflictEvent:
    """Logged whenever the Writer detects a contradiction.

    The Writer never silently overwrites — it archives the old fragment
    and emits a ConflictEvent so the orchestrator and audit trail both
    know what happened.
    """

    id: str
    old_fragment_id: str
    new_fragment_id: str
    reason: Literal["contradiction", "stale", "agent_disagreement"]
    resolution: Literal["supersede", "branch", "human_required"]
    resolved_by: str | None = None
    created_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "old_fragment_id": self.old_fragment_id,
            "new_fragment_id": self.new_fragment_id,
            "reason": self.reason,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def make(
        cls,
        old_id: str,
        new_id: str,
        reason: Literal["contradiction", "stale", "agent_disagreement"],
        resolution: Literal["supersede", "branch", "human_required"] = "supersede",
        resolved_by: str | None = None,
    ) -> "ConflictEvent":
        return cls(
            id=str(uuid.uuid4()),
            old_fragment_id=old_id,
            new_fragment_id=new_id,
            reason=reason,
            resolution=resolution,
            resolved_by=resolved_by,
        )


# ---------------------------------------------------------------------------
# AccessEdge — bipartite access-policy graph
# ---------------------------------------------------------------------------


@dataclass
class AccessEdge:
    """One edge in the user × agent × resource access graph.

    Implements the Collaborative Memory bipartite permission model.
    Edges have validity windows — permissions change over time without
    retroactively altering historical fragment visibility.
    """

    user_id: str
    agent_id: str
    resource_glob: str    # e.g. "tier:t3_team" or "repo:org/repo/**"
    perms: set[Literal["read", "write"]] = field(default_factory=lambda: {"read"})
    valid_from: datetime = field(default_factory=_now)
    valid_to: datetime | None = None

    def is_active(self, at: datetime | None = None) -> bool:
        t = at or _now()
        if t < self.valid_from:
            return False
        if self.valid_to is not None and t > self.valid_to:
            return False
        return True

    def allows(self, perm: Literal["read", "write"], at: datetime | None = None) -> bool:
        return self.is_active(at) and perm in self.perms


# ---------------------------------------------------------------------------
# SubAgentDigest — SRMT-style broadcast
# ---------------------------------------------------------------------------


@dataclass
class SubAgentDigest:
    """Compact per-step broadcast from a sub-agent to its peers.

    The closed-LLM analog of SRMT's pooled-memory cross-attention.
    Each sub-agent emits one digest per step; the orchestrator's prompt
    is auto-augmented with the latest digest per peer (capped at 600 tokens
    total across all peers).

    Not embedded / not part of vector search — stored in a dedicated
    fast-access table, retrieved by task_id.
    """

    agent_id: str
    task_id: str
    step: int
    last_action: str               # "ran pytest tests/test_auth.py; 3 failures"
    findings: list[str] = field(default_factory=list)       # bullet points
    open_questions: list[str] = field(default_factory=list)
    next_intent: str | None = None
    confidence: float = 0.7
    emitted_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "step": self.step,
            "last_action": self.last_action,
            "findings": list(self.findings),
            "open_questions": list(self.open_questions),
            "next_intent": self.next_intent,
            "confidence": self.confidence,
            "emitted_at": self.emitted_at.isoformat(),
        }

    def render_compact(self, max_chars: int = 300) -> str:
        """Render a compact text summary for orchestrator prompt injection."""
        lines = [f"[{self.agent_id} step={self.step}] {self.last_action}"]
        for f in self.findings[:3]:
            lines.append(f"  • {f}")
        if self.open_questions:
            lines.append(f"  ? {self.open_questions[0]}")
        if self.next_intent:
            lines.append(f"  → {self.next_intent}")
        return "\n".join(lines)[:max_chars]


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "AccessEdge",
    "ConflictEvent",
    "Fragment",
    "FragmentType",
    "MemoryTier",
    "Provenance",
    "SubAgentDigest",
    "VisibilityScope",
]
