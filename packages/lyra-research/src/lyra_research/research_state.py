"""Unified Research State — single source of truth for research session progress.

Replaces the three parallel progress trackers (ResearchState, ResearchProgress,
Phase2ResearchProgress) with one comprehensive, serializable state object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ResearchPhase(str, Enum):
    """Phases of the research pipeline."""
    CLARIFY = "clarify"
    PLAN = "plan"
    SEARCH = "search"
    FILTER = "filter"
    FETCH = "fetch"
    ANALYZE = "analyze"
    EVIDENCE_AUDIT = "evidence_audit"
    SYNTHESIZE = "synthesize"
    REPORT = "report"
    MEMORIZE = "memorize"


class SessionStatus(str, Enum):
    """Status of a research session."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class UnifiedResearchState:
    """Single comprehensive state object for a research session.

    Combines fields from ResearchState, ResearchProgress, and Phase2ResearchProgress.
    """

    session_id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    depth: str = "standard"  # quick, standard, deep

    # Phase tracking
    current_phase: ResearchPhase = ResearchPhase.CLARIFY
    phase_index: int = 0
    phase_history: list[dict[str, Any]] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_checkpoint_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    elapsed_seconds: float = 0.0

    # Status
    status: SessionStatus = SessionStatus.CREATED

    # Discovery progress
    sources_found: int = 0
    sources_filtered: int = 0
    sources_fetched: int = 0
    sources_by_type: dict[str, int] = field(default_factory=dict)

    # Analysis progress
    papers_analyzed: int = 0
    repos_analyzed: int = 0
    claims_verified: int = 0
    claims_falsified: int = 0

    # Gap detection
    gaps_found: int = 0
    gaps_by_severity: dict[str, int] = field(default_factory=dict)

    # Quality metrics
    verification_rate: float = 0.0
    citation_fidelity: float = 0.0
    source_breadth: float = 0.0
    insight_depth: float = 0.0
    overall_quality_score: float = 0.0

    # Model usage tracking
    model_calls: dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Intermediate results
    raw_discovery_results: list[dict[str, Any]] = field(default_factory=list)
    ranked_sources: list[dict[str, Any]] = field(default_factory=list)
    paper_analyses: list[dict[str, Any]] = field(default_factory=list)
    repo_analyses: list[dict[str, Any]] = field(default_factory=list)
    synthesis_result: dict[str, Any] | None = None
    review_notes: list[dict[str, Any]] = field(default_factory=list)
    report_data: dict[str, Any] | None = None

    # Curation
    curated_knowledge: list[dict[str, Any]] = field(default_factory=list)

    # Error tracking
    errors: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0

    # Gate results
    gate_results: dict[str, bool] = field(default_factory=dict)

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def advance_phase(self, next_phase: ResearchPhase | None = None) -> None:
        """Advance to the next research phase."""
        self.phase_history.append({
            "phase": self.current_phase.value,
            "index": self.phase_index,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        if next_phase:
            self.current_phase = next_phase
        else:
            phases = list(ResearchPhase)
            current_idx = phases.index(self.current_phase)
            if current_idx < len(phases) - 1:
                self.current_phase = phases[current_idx + 1]
        self.phase_index += 1

    def record_error(self, error_msg: str, phase: str | None = None) -> None:
        """Record an error with context."""
        self.errors.append({
            "message": error_msg,
            "phase": phase or self.current_phase.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def mark_completed(self) -> None:
        """Mark the session as completed."""
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error_msg: str) -> None:
        """Mark the session as failed."""
        self.status = SessionStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.record_error(error_msg)

    def get_progress_pct(self) -> float:
        """Get overall progress as a percentage."""
        phases = list(ResearchPhase)
        completed = self.phase_index
        return min(100.0, (completed / len(phases)) * 100.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        from dataclasses import asdict

        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["last_checkpoint_at"] = self.last_checkpoint_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        data["current_phase"] = self.current_phase.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnifiedResearchState:
        """Create from dict (reverses to_dict)."""
        data["started_at"] = datetime.fromisoformat(data["started_at"])
        data["last_checkpoint_at"] = datetime.fromisoformat(data["last_checkpoint_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        data["current_phase"] = ResearchPhase(data["current_phase"])
        data["status"] = SessionStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


__all__ = [
    "ResearchPhase",
    "SessionStatus",
    "UnifiedResearchState",
]
