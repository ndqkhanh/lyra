"""
L5: Experience Memory Layer - Distilled reasoning strategies from trajectories.

This layer stores high-level strategies learned from successful and failed attempts.
Implements ReasoningBank-style experience learning with conservative retrieval.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


@dataclass
class ExperienceRecord:
    """A learned strategy from past experience."""

    experience_id: str
    strategy_pattern: str  # "When X, do Y because Z"
    success_contexts: List[Dict[str, Any]]  # Task features where it worked
    failure_contexts: List[Dict[str, Any]]  # Task features where it failed
    confidence_score: float  # 0.0 to 1.0
    evidence: List[str]  # Trajectory IDs that support this strategy
    created_at: str
    last_used: Optional[str] = None
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experience_id": self.experience_id,
            "strategy_pattern": self.strategy_pattern,
            "success_contexts": self.success_contexts,
            "failure_contexts": self.failure_contexts,
            "confidence_score": self.confidence_score,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceRecord":
        """Create from dictionary."""
        return cls(**data)


class ExperienceMemoryStore:
    """Storage for experience records."""

    def __init__(self, data_dir: str = "./data/l5_experience"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.experiences_file = self.data_dir / "experiences.json"
        self._load_experiences()

    def _load_experiences(self):
        """Load experiences from disk."""
        if self.experiences_file.exists():
            with open(self.experiences_file, "r") as f:
                data = json.load(f)
                self.experiences = {
                    exp_id: ExperienceRecord.from_dict(exp_data)
                    for exp_id, exp_data in data.items()
                }
        else:
            self.experiences = {}

    def _save_experiences(self):
        """Save experiences to disk."""
        data = {
            exp_id: exp.to_dict()
            for exp_id, exp in self.experiences.items()
        }
        with open(self.experiences_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_experience(self, experience: ExperienceRecord) -> str:
        """Add a new experience."""
        self.experiences[experience.experience_id] = experience
        self._save_experiences()
        return experience.experience_id

    def get_experience(self, experience_id: str) -> Optional[ExperienceRecord]:
        """Get an experience by ID."""
        return self.experiences.get(experience_id)

    def search_experiences(
        self,
        task_features: Dict[str, Any],
        min_confidence: float = 0.5,
        limit: int = 5
    ) -> List[ExperienceRecord]:
        """
        Search for relevant experiences using conservative retrieval.

        Conservative retrieval (CoPS-style) to avoid negative transfer:
        - Only return experiences with high confidence
        - Check distribution match between task and success contexts
        - Filter out experiences with similar failure contexts
        """
        results = []

        for exp in self.experiences.values():
            if exp.confidence_score < min_confidence:
                continue

            # Check if task matches success contexts
            success_match = self._context_similarity(
                task_features,
                exp.success_contexts
            )

            # Check if task matches failure contexts (avoid these)
            failure_match = self._context_similarity(
                task_features,
                exp.failure_contexts
            )

            # Conservative: only use if strong success match and weak failure match
            if success_match > 0.7 and failure_match < 0.3:
                results.append((exp, success_match))

        # Sort by confidence and match score
        results.sort(
            key=lambda x: (x[0].confidence_score, x[1]),
            reverse=True
        )

        return [exp for exp, _ in results[:limit]]

    def _context_similarity(
        self,
        task_features: Dict[str, Any],
        contexts: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate similarity between task and contexts.

        Simple feature overlap for now. Can be enhanced with embeddings.
        """
        if not contexts:
            return 0.0

        max_similarity = 0.0
        for context in contexts:
            # Count matching features
            matching = sum(
                1 for key in task_features
                if key in context and task_features[key] == context[key]
            )
            total = len(set(task_features.keys()) | set(context.keys()))
            similarity = matching / total if total > 0 else 0.0
            max_similarity = max(max_similarity, similarity)

        return max_similarity

    def record_usage(
        self,
        experience_id: str,
        success: bool,
        task_features: Dict[str, Any]
    ):
        """Record experience usage and update metrics."""
        if experience_id not in self.experiences:
            return

        exp = self.experiences[experience_id]

        # Update usage stats
        exp.usage_count += 1
        exp.last_used = datetime.now().isoformat()

        if success:
            exp.success_count += 1
            # Add to success contexts if not already present
            if task_features not in exp.success_contexts:
                exp.success_contexts.append(task_features)
        else:
            exp.failure_count += 1
            # Add to failure contexts
            if task_features not in exp.failure_contexts:
                exp.failure_contexts.append(task_features)

        # Update confidence score
        if exp.usage_count > 0:
            exp.confidence_score = exp.success_count / exp.usage_count

        self._save_experiences()

    def get_top_experiences(self, limit: int = 10) -> List[ExperienceRecord]:
        """Get top experiences by confidence and usage."""
        experiences = list(self.experiences.values())
        experiences.sort(
            key=lambda e: (e.confidence_score, e.usage_count),
            reverse=True
        )
        return experiences[:limit]
