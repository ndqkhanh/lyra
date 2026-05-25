"""
CBT Belief Hierarchy — 3-tier belief system where identity emerges from
core beliefs, intermediate rules, and automatic thoughts.

Cathartic updates: strong emotional experiences can trigger belief revision
at intermediate and core levels, simulating cognitive behavioral therapy dynamics.

Tiers:
    Core Beliefs          — Fundamental beliefs about capability/identity ("I am capable")
    Intermediate Beliefs  — If-then rules and attitudes ("If I plan well, I succeed")
    Automatic Thoughts    — Surface-level situation-specific thoughts ("This looks hard")

Source: Human-Like Lifelong Memory (QufkvHbQs7), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class Belief:
    """A single belief in the CBT hierarchy."""

    id: str = field(default_factory=lambda: uuid4().hex)
    content: str = ""
    confidence: float = 1.0
    evidence_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_experiences: list[str] = field(default_factory=list)

    def strengthen(self, experience_id: str, delta: float = 0.05) -> None:
        """Increase confidence based on supporting experience."""
        self.evidence_count += 1
        self.confidence = min(1.0, self.confidence + delta)
        self.source_experiences.append(experience_id)
        self.last_updated = datetime.now(timezone.utc)

    def weaken(self, experience_id: str, delta: float = 0.1) -> None:
        """Decrease confidence based on contradictory experience."""
        self.evidence_count += 1
        self.confidence = max(0.0, self.confidence - delta)
        self.source_experiences.append(experience_id)
        self.last_updated = datetime.now(timezone.utc)

    @property
    def is_stable(self) -> bool:
        """Beliefs with high confidence after many experiences are stable."""
        return self.confidence >= 0.8 and self.evidence_count >= 3


@dataclass
class CBTBeliefHierarchy:
    """3-tier cognitive behavioral therapy belief hierarchy.

    Core beliefs are the most stable and resistant to change. Cathartic
    updates (strong emotional valence) are required to modify them.
    """

    core_beliefs: list[Belief] = field(default_factory=list)
    intermediate_beliefs: list[Belief] = field(default_factory=list)
    automatic_thoughts: list[Belief] = field(default_factory=list)

    def add_core_belief(self, content: str, confidence: float = 0.5) -> Belief:
        belief = Belief(content=content, confidence=confidence)
        self.core_beliefs.append(belief)
        return belief

    def add_intermediate_belief(self, content: str, confidence: float = 0.5) -> Belief:
        belief = Belief(content=content, confidence=confidence)
        self.intermediate_beliefs.append(belief)
        return belief

    def add_automatic_thought(self, content: str, confidence: float = 0.5) -> Belief:
        belief = Belief(content=content, confidence=confidence)
        self.automatic_thoughts.append(belief)
        return belief

    def cathartic_update(
        self,
        experience_content: str,
        emotional_valence: float,
        experience_id: str | None = None,
    ) -> list[Belief]:
        """Apply cathartic belief update triggered by strong emotional experience.

        Emotional valence magnitude determines impact depth:
        - |valence| >= 0.9: can revise core beliefs (rare, transformative)
        - |valence| >= 0.7: can revise intermediate beliefs
        - |valence| >= 0.5: can revise automatic thoughts
        - |valence| <  0.5: no cathartic effect, just strengthens existing

        Returns list of beliefs that were modified.
        """
        eid = experience_id or uuid4().hex
        abs_val = abs(emotional_valence)
        is_positive = emotional_valence > 0
        modified: list[Belief] = []

        # Automatic thoughts: always impacted by any significant experience
        if abs_val >= 0.5:
            for belief in self.automatic_thoughts:
                if self._experience_relevant(experience_content, belief.content):
                    if is_positive:
                        belief.strengthen(eid, delta=abs_val * 0.1)
                    else:
                        belief.weaken(eid, delta=abs_val * 0.1)
                    modified.append(belief)

        # Intermediate beliefs: impacted by stronger experiences
        if abs_val >= 0.7:
            for belief in self.intermediate_beliefs:
                if self._experience_relevant(experience_content, belief.content):
                    if is_positive:
                        belief.strengthen(eid, delta=abs_val * 0.08)
                    else:
                        belief.weaken(eid, delta=abs_val * 0.15)
                    modified.append(belief)

        # Core beliefs: only impacted by transformative experiences
        if abs_val >= 0.9:
            for belief in self.core_beliefs:
                if self._experience_relevant(experience_content, belief.content):
                    if is_positive:
                        belief.strengthen(eid, delta=abs_val * 0.05)
                    else:
                        belief.weaken(eid, delta=abs_val * 0.1)
                    modified.append(belief)

        return modified

    def get_active_beliefs(self, context: str) -> list[Belief]:
        """Get beliefs relevant to the current context (keyword overlap)."""
        context_lower = context.lower()
        active = []

        for tier in [self.automatic_thoughts, self.intermediate_beliefs, self.core_beliefs]:
            for belief in tier:
                if any(word in belief.content.lower() for word in context_lower.split()):
                    active.append(belief)

        return active

    @property
    def total_beliefs(self) -> int:
        return len(self.core_beliefs) + len(self.intermediate_beliefs) + len(self.automatic_thoughts)

    @property
    def stable_core_count(self) -> int:
        return sum(1 for b in self.core_beliefs if b.is_stable)

    @staticmethod
    def _experience_relevant(experience: str, belief_content: str) -> bool:
        """Check if experience is relevant to a belief via keyword overlap."""
        exp_words = set(experience.lower().split())
        belief_words = set(belief_content.lower().split())
        overlap = exp_words & belief_words
        return len(overlap) > 0
