"""Cross-Agent Learning — pattern extraction, skill improvement, and knowledge transfer.

Implements cross-agent learning for agent swarms:
  - Experience recording with reward signals
  - Pattern extraction from successful/failed tasks
  - Success rate tracking with running averages
  - Proven pattern identification (high success rate + usage)
  - Pattern recommendations for new tasks
  - Agent-specific experience history
"""

from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class PatternType(StrEnum):
    """Category of learned pattern."""

    ARCHITECTURE = "architecture"
    BUG_FIX = "bug_fix"
    OPTIMIZATION = "optimization"
    SECURITY = "security"
    TESTING = "testing"
    DEVOPS = "devops"
    GENERAL = "general"


@dataclass(frozen=True)
class ExperienceRecord:
    """A single experience from an agent completing a task."""

    agent_id: str
    task: str
    outcome: str  # "success" or "failure"
    reward: float  # 0.0-1.0
    extracted_patterns: tuple[str, ...] = ()
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class LearningPattern:
    """A learned pattern extracted from agent experiences."""

    pattern_id: str
    name: str
    pattern_type: PatternType = PatternType.GENERAL
    success_rate: float = 0.0
    usage_count: int = 0
    keywords: tuple[str, ...] = ()
    description: str = ""

    @property
    def is_proven(self) -> bool:
        """A pattern is proven if it has high success rate and sufficient usage."""
        return self.success_rate >= 0.75 and self.usage_count >= 3

    def update_success_rate(self, success: bool) -> LearningPattern:
        """Return a new pattern with updated success rate."""
        new_count = self.usage_count + 1
        new_rate = (self.success_rate * self.usage_count + (1.0 if success else 0.0)) / new_count
        return LearningPattern(
            pattern_id=self.pattern_id,
            name=self.name,
            pattern_type=self.pattern_type,
            success_rate=new_rate,
            usage_count=new_count,
            keywords=self.keywords,
            description=self.description,
        )


class CrossAgentLearning:
    """Manages cross-agent learning and knowledge transfer.

    Records agent experiences, extracts reusable patterns, and
    provides recommendations based on proven patterns.

    Usage::

        cal = CrossAgentLearning()
        cal.record_experience(
            agent_id="agent-1",
            task="Implement rate limiting middleware",
            outcome="success",
            reward=0.95,
            patterns=["rate_limit_before_auth", "sliding_window_redis"],
        )
        recs = cal.recommend_patterns(task_description="Add auth rate limiting")
    """

    def __init__(self) -> None:
        self._experiences: list[ExperienceRecord] = []
        self._patterns: dict[str, LearningPattern] = {}
        self._agent_experiences: dict[str, list[str]] = defaultdict(list)

    # ── Properties ───────────────────────────────────────────────

    @property
    def experience_count(self) -> int:
        return len(self._experiences)

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)

    # ── Recording ────────────────────────────────────────────────

    def record_experience(
        self,
        agent_id: str,
        task: str,
        outcome: str,
        reward: float,
        patterns: list[str] | None = None,
        pattern_type: PatternType = PatternType.GENERAL,
    ) -> ExperienceRecord:
        """Record an agent's experience completing a task."""
        record = ExperienceRecord(
            agent_id=agent_id,
            task=task,
            outcome=outcome,
            reward=max(0.0, min(1.0, reward)),
            extracted_patterns=tuple(patterns or []),
        )
        self._experiences.append(record)
        self._agent_experiences[agent_id].append(record.record_id)

        for pattern_name in record.extracted_patterns:
            self._upsert_pattern(pattern_name, outcome, pattern_type, task)

        return record

    def get_pattern(self, name: str) -> LearningPattern | None:
        """Get a learned pattern by name."""
        return self._patterns.get(name)

    # ── Queries ──────────────────────────────────────────────────

    def get_proven_patterns(self) -> list[LearningPattern]:
        """Get all patterns that have proven effective."""
        return [p for p in self._patterns.values() if p.is_proven]

    def get_patterns_by_type(self, pattern_type: PatternType) -> list[LearningPattern]:
        """Get patterns of a specific type."""
        return [p for p in self._patterns.values() if p.pattern_type == pattern_type]

    def get_agent_experiences(self, agent_id: str) -> list[ExperienceRecord]:
        """Get all experiences recorded for an agent."""
        record_ids = self._agent_experiences.get(agent_id, [])
        id_set = set(record_ids)
        return [e for e in self._experiences if e.record_id in id_set]

    def recommend_patterns(
        self,
        task_description: str,
        limit: int = 5,
    ) -> list[LearningPattern]:
        """Recommend proven patterns for a task based on keyword matching."""
        task_lower = task_description.lower()
        scored: list[tuple[float, LearningPattern]] = []

        for pattern in self._patterns.values():
            if not pattern.is_proven:
                continue
            score = 0.0
            for keyword in pattern.keywords:
                if keyword.lower() in task_lower:
                    score += 1.0
            if pattern.name.lower() in task_lower:
                score += 2.0
            if score > 0:
                scored.append((score, pattern))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def get_skill_improvements(self, agent_id: str) -> list[dict]:
        """Get skill improvements suggested for an agent based on patterns."""
        experiences = self.get_agent_experiences(agent_id)
        proven = self.get_proven_patterns()

        used_patterns: set[str] = {p for exp in experiences for p in exp.extracted_patterns}

        improvements: list[dict] = []
        for pattern in proven:
            if pattern.name not in used_patterns:
                improvements.append({
                    "pattern": pattern.name,
                    "type": pattern.pattern_type.value,
                    "success_rate": pattern.success_rate,
                    "reason": f"Proven pattern not yet used by {agent_id}",
                })

        return improvements

    def get_learning_summary(self) -> dict:
        """Get a summary of all learning activity."""
        successes = sum(1 for e in self._experiences if e.outcome == "success")
        total = max(1, len(self._experiences))
        return {
            "total_experiences": len(self._experiences),
            "total_patterns": len(self._patterns),
            "proven_patterns": len(self.get_proven_patterns()),
            "success_rate": successes / total,
            "agents_learned": len(self._agent_experiences),
        }

    def reset(self) -> None:
        """Reset all learning state."""
        self._experiences.clear()
        self._patterns.clear()
        self._agent_experiences.clear()

    # ── Private ───────────────────────────────────────────────────

    def _upsert_pattern(
        self,
        name: str,
        outcome: str,
        pattern_type: PatternType,
        task: str,
    ) -> None:
        """Create or update a learned pattern."""
        keywords = tuple(self._extract_keywords(task))
        existing = self._patterns.get(name)

        if existing:
            self._patterns[name] = existing.update_success_rate(
                success=outcome == "success"
            )
        else:
            self._patterns[name] = LearningPattern(
                pattern_id=f"pat-{uuid.uuid4().hex[:12]}",
                name=name,
                pattern_type=pattern_type,
                success_rate=1.0 if outcome == "success" else 0.0,
                usage_count=1,
                keywords=keywords,
                description=f"Learned from task: {task[:100]}",
            )

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract meaningful keywords from task description."""
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())
        stopwords = {
            "the", "and", "for", "with", "from", "that", "this", "was",
            "are", "has", "have", "been", "will", "can", "not", "but",
            "you", "all", "any", "each", "our", "its",
        }
        return [w for w in words if w not in stopwords][:8]
