"""Beliefs System — domain knowledge distinct from actions.

A Belief is what the agent KNOWS (domain knowledge, patterns, conventions).
A Skill is what the agent DOES (actions, tools, workflows).
This separation enables targeted evolution: evolve knowledge independently of actions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "BeliefSource",
    "Belief",
    "BeliefSystem",
]


class BeliefSource(Enum):
    LEARNED = auto()
    EXPERT_ENCODED = auto()
    EXTRACTED = auto()


@dataclass
class Belief:
    id: str
    domain: str
    statement: str
    confidence: float = 0.5
    source: BeliefSource = BeliefSource.LEARNED
    evidence: list[str] = field(default_factory=list)
    hit_count: int = 0


class BeliefSystem:
    """Encodes, extracts, queries, and verifies beliefs."""

    def __init__(self):
        self._beliefs: dict[str, Belief] = {}
        self._domains: dict[str, list[str]] = {}  # domain → belief_ids
        self._counter = 0

    # ── Encoding ─────────────────────────────────────────────

    def encode_expert(self, domain: str, statement: str, confidence: float = 0.8) -> Belief:
        """Encode an expert belief into the system."""
        self._counter += 1
        belief = Belief(
            id=f"belief_{self._counter}",
            domain=domain,
            statement=statement,
            confidence=confidence,
            source=BeliefSource.EXPERT_ENCODED,
        )
        self._beliefs[belief.id] = belief
        if domain not in self._domains:
            self._domains[domain] = []
        self._domains[domain].append(belief.id)
        return belief

    def extract(self, statement: str, evidence: list[str]) -> Belief:
        """Extract a belief from agent execution trace."""
        self._counter += 1
        domain = self._infer_domain(statement)
        belief = Belief(
            id=f"belief_{self._counter}",
            domain=domain,
            statement=statement,
            confidence=0.4,
            source=BeliefSource.EXTRACTED,
            evidence=evidence,
        )
        self._beliefs[belief.id] = belief
        if domain not in self._domains:
            self._domains[domain] = []
        self._domains[domain].append(belief.id)
        return belief

    def _infer_domain(self, statement: str) -> str:
        statement_lower = statement.lower()
        if "python" in statement_lower or "javascript" in statement_lower:
            return "programming"
        if "api" in statement_lower or "endpoint" in statement_lower:
            return "api_design"
        if "security" in statement_lower or "auth" in statement_lower:
            return "security"
        return "general"

    # ── Retrieval ────────────────────────────────────────────

    def query(self, context: str, top_k: int = 5) -> list[Belief]:
        """Retrieve relevant beliefs for context."""
        scored = []
        context_lower = context.lower()
        for belief in self._beliefs.values():
            score = 0.0
            if belief.domain in context_lower:
                score += 0.3
            for word in belief.statement.lower().split():
                if word in context_lower and len(word) > 3:
                    score += 0.1
            score += belief.confidence * 0.5
            scored.append((score, belief))
        scored.sort(key=lambda x: -x[0])
        return [b for _, b in scored[:top_k]]

    def query_domain(self, domain: str) -> list[Belief]:
        """Get all beliefs in a domain."""
        belief_ids = self._domains.get(domain, [])
        return [self._beliefs[iid] for iid in belief_ids if iid in self._beliefs]

    # ── Verification ─────────────────────────────────────────

    def verify(self, belief_id: str) -> bool:
        """Verify a belief against its evidence."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False
        if belief.source == BeliefSource.EXPERT_ENCODED:
            return True
        return len(belief.evidence) >= 2

    # ── Stats ────────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_beliefs": len(self._beliefs),
            "domains": list(self._domains.keys()),
            "by_source": {
                "learned": sum(1 for b in self._beliefs.values() if b.source == BeliefSource.LEARNED),
                "expert": sum(1 for b in self._beliefs.values() if b.source == BeliefSource.EXPERT_ENCODED),
                "extracted": sum(1 for b in self._beliefs.values() if b.source == BeliefSource.EXTRACTED),
            },
        }
