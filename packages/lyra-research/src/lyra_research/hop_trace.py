"""Hop-level provenance for IRCoT multi-hop reasoning — Phase C.

Each retrieval-reasoning hop produces a HopTrace that records what was
retrieved, how much it supported the reasoning step, and what conclusion
the model drew.  A sequence of HopTraces forms a verifiable audit trail
for multi-hop answers, enabling Reflexion replay in Phase E.

Grounded in:
- arXiv:2212.10509 — IRCoT: Interleaved Retrieval with Chain-of-Thought
- Doc 324 §5 — Multi-hop graph reasoning for Lyra
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


__all__ = [
    "HopTrace",
    "MultiHopResult",
    "SearchPolicy",
    "GreedySearchPolicy",
]


@dataclass
class HopTrace:
    """Evidence + reasoning produced by one retrieval hop."""

    hop_index: int
    query: str                        # retrieval query issued this hop
    passages: list[str] = field(default_factory=list)
    support_score: float = 0.0        # [0, 1] — how well passages support the step
    reasoning_step: str = ""          # model's CoT sentence(s) for this hop
    source_refs: list[str] = field(default_factory=list)  # node IDs / doc IDs cited

    def __post_init__(self) -> None:
        if not 0.0 <= self.support_score <= 1.0:
            raise ValueError(f"support_score must be in [0, 1], got {self.support_score!r}")


@dataclass(frozen=True)
class MultiHopResult:
    """Final answer produced after N hops, with full trace."""

    answer: str
    hops: tuple[HopTrace, ...]
    terminated_early: bool    # True if a hop reached support_score >= stop_threshold
    total_hops: int

    @property
    def mean_support(self) -> float:
        if not self.hops:
            return 0.0
        return sum(h.support_score for h in self.hops) / len(self.hops)

    def weakest_hop(self) -> Optional[HopTrace]:
        if not self.hops:
            return None
        return min(self.hops, key=lambda h: h.support_score)


# ------------------------------------------------------------------ #
# Search policy                                                        #
# ------------------------------------------------------------------ #

class SearchPolicy:
    """Abstract base — controls query generation and early stopping."""

    def next_query(self, _question: str, _traces: list[HopTrace]) -> str:
        raise NotImplementedError

    def should_stop(self, _traces: list[HopTrace]) -> bool:
        raise NotImplementedError


class GreedySearchPolicy(SearchPolicy):
    """Greedy policy: append the previous reasoning step as new query context.

    Stops when the latest hop's support_score exceeds *stop_threshold*
    or the answer phrase 'final answer:' appears in the reasoning step.
    """

    def __init__(self, stop_threshold: float = 0.85) -> None:
        if not 0.0 <= stop_threshold <= 1.0:
            raise ValueError("stop_threshold must be in [0, 1]")
        self.stop_threshold = stop_threshold

    def next_query(self, question: str, traces: list[HopTrace]) -> str:
        if not traces:
            return question
        last_step = traces[-1].reasoning_step
        return f"{question} | context: {last_step}" if last_step else question

    def should_stop(self, traces: list[HopTrace]) -> bool:
        if not traces:
            return False
        last = traces[-1]
        if last.support_score >= self.stop_threshold:
            return True
        return "final answer:" in last.reasoning_step.lower()
