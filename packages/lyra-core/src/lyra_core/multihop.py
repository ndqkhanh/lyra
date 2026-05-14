"""Interleaved Retrieval + Chain-of-Thought (IRCoT) engine — Phase C.

Implements multi-hop reasoning where each step alternates between
retrieval and a short reasoning chain.  Hop-level provenance is
recorded so Phase E Reflexion can replay and critique any step.

Grounded in:
- arXiv:2212.10509 — IRCoT: Interleaved Retrieval with Chain-of-Thought Reasoning
- Doc 324 §5 — Multi-hop graph reasoning for Lyra
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


__all__ = [
    "HopRecord",
    "MultiHopAnswer",
    "Retriever",
    "Reasoner",
    "IRCoTEngine",
]


# ------------------------------------------------------------------ #
# Data types                                                           #
# ------------------------------------------------------------------ #

@dataclass
class HopRecord:
    """Evidence + reasoning produced by one IRCoT hop."""

    hop_index: int
    query: str
    passages: list[str] = field(default_factory=list)
    support_score: float = 0.0   # [0, 1]
    reasoning: str = ""
    source_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.support_score <= 1.0:
            raise ValueError(f"support_score must be in [0, 1], got {self.support_score!r}")


@dataclass(frozen=True)
class MultiHopAnswer:
    """Final answer after N hops."""

    answer: str
    hops: tuple[HopRecord, ...]
    stopped_early: bool

    @property
    def mean_support(self) -> float:
        if not self.hops:
            return 0.0
        return sum(h.support_score for h in self.hops) / len(self.hops)


# ------------------------------------------------------------------ #
# Protocols                                                            #
# ------------------------------------------------------------------ #

class Retriever(Protocol):
    """Fetches passages relevant to a query."""

    def retrieve(self, query: str, top_k: int = 3) -> list[str]: ...


class Reasoner(Protocol):
    """Produces a reasoning step + support score from passages."""

    def reason(
        self,
        question: str,
        passages: list[str],
        prior_hops: list[HopRecord],
    ) -> tuple[str, float, list[str]]:
        """Returns (reasoning_text, support_score, source_refs)."""
        ...


# ------------------------------------------------------------------ #
# IRCoT Engine                                                         #
# ------------------------------------------------------------------ #

class IRCoTEngine:
    """Run interleaved retrieval + reasoning for multi-hop questions.

    Usage::

        engine = IRCoTEngine(retriever, reasoner, max_hops=4)
        result = engine.run("What module calls the skill router?")
    """

    def __init__(
        self,
        retriever: Retriever,
        reasoner: Reasoner,
        max_hops: int = 4,
        stop_threshold: float = 0.90,
        top_k: int = 3,
    ) -> None:
        if max_hops < 1:
            raise ValueError("max_hops must be >= 1")
        if not 0.0 <= stop_threshold <= 1.0:
            raise ValueError("stop_threshold must be in [0, 1]")
        self._retriever = retriever
        self._reasoner = reasoner
        self._max_hops = max_hops
        self._stop_threshold = stop_threshold
        self._top_k = top_k

    def run(self, question: str) -> MultiHopAnswer:
        hops: list[HopRecord] = []

        for hop_idx in range(self._max_hops):
            query = self._build_query(question, hops)
            passages = self._retriever.retrieve(query, top_k=self._top_k)
            reasoning, support, refs = self._reasoner.reason(question, passages, hops)

            hop = HopRecord(
                hop_index=hop_idx,
                query=query,
                passages=passages,
                support_score=support,
                reasoning=reasoning,
                source_refs=refs,
            )
            hops.append(hop)

            if support >= self._stop_threshold or "final answer:" in reasoning.lower():
                return MultiHopAnswer(
                    answer=reasoning,
                    hops=tuple(hops),
                    stopped_early=True,
                )

        return MultiHopAnswer(
            answer=hops[-1].reasoning if hops else "",
            hops=tuple(hops),
            stopped_early=False,
        )

    @staticmethod
    def _build_query(question: str, prior_hops: list[HopRecord]) -> str:
        if not prior_hops:
            return question
        context = " ".join(h.reasoning for h in prior_hops if h.reasoning)
        return f"{question} | context: {context}"
