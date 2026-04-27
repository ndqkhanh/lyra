"""Skill-RAG hidden-state prober + 4-skill recovery router (v1.8 Wave-1 §3.3).

Inspired by the *Skill-RAG* paper (Univ. Michigan / UPenn, 2026 —
arXiv:2604.15771, mirrored under ``papers/skill-rag.pdf``).

When a vanilla RAG retrieval underperforms, the cause usually fits one
of four buckets:

1. **Query Rewriting** — the embedded query missed lexical or domain
   variants the corpus actually uses.
2. **Question Decomposition** — the question was multi-hop and needs
   to be split.
3. **Evidence Focusing** — the right document came back but inside too
   much noise.
4. **Exit** — the corpus genuinely doesn't contain the answer; calling
   the LLM with the noisy context only hallucinates. Bail out cleanly.

The Hidden-State Prober reads the LLM's own internal state to *diagnose
which bucket applies*, and the SkillRagRouter dispatches to the matching
recovery skill. The fourth skill (Exit) is the most important one — it's
the only currently-deployed RAG that knows when to give up.

Phase 0: contracts only.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class RecoverySkill(str, Enum):
    """The four mutually-exclusive recovery actions Skill-RAG selects from."""

    QUERY_REWRITING = "query_rewriting"
    QUESTION_DECOMPOSITION = "question_decomposition"
    EVIDENCE_FOCUSING = "evidence_focusing"
    EXIT = "exit"


@dataclass(frozen=True)
class RetrievalAttempt:
    """One round-trip through the retriever."""

    query: str
    documents: tuple[str, ...]
    scores: tuple[float, ...]
    extras: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.documents) != len(self.scores):
            raise ValueError("documents and scores must align in length")


@dataclass(frozen=True)
class ProberVerdict:
    """The hidden-state prober's diagnosis of a failed retrieval."""

    recommended_skill: RecoverySkill
    confidence: float            # [0, 1]
    rationale: str
    feature_vector: tuple[float, ...] = ()  # for explainability/debugging


@dataclass(frozen=True)
class RetrievalResult:
    """The end-to-end outcome of a Skill-RAG run."""

    answer: str | None           # None == EXIT skill chose to bail out
    used_skill: RecoverySkill
    rounds: tuple[RetrievalAttempt, ...]
    verdict: ProberVerdict
    cost_tokens: int


class HiddenStateProber(Protocol):
    """Inspects an LLM hidden state to recommend a recovery skill.

    Implementations may be a small linear probe trained on labelled
    retrieval failures, or a heuristic over attention entropy / answer
    perplexity. The Lyra contract is the *interface*, not the algorithm.
    """

    def diagnose(
        self,
        question: str,
        attempt: RetrievalAttempt,
        hidden_state: Sequence[float],
    ) -> ProberVerdict: ...


class RecoveryHandler(Protocol):
    """One of the four skills (rewrite, decompose, focus, exit)."""

    skill: RecoverySkill

    def recover(
        self,
        question: str,
        attempt: RetrievalAttempt,
    ) -> RetrievalResult: ...


class SkillRagRouter:
    """Dispatches a failed retrieval to the recommended recovery skill.

    Phase 0: the router accepts a prober + 4 handlers and a max-rounds cap;
    ``answer`` is unimplemented.
    """

    def __init__(
        self,
        prober: HiddenStateProber,
        handlers: Mapping[RecoverySkill, RecoveryHandler],
        *,
        max_rounds: int = 3,
    ) -> None:
        if max_rounds <= 0:
            raise ValueError("max_rounds must be > 0")
        missing = set(RecoverySkill) - set(handlers.keys())
        if missing:
            raise ValueError(
                f"SkillRagRouter requires a handler for every RecoverySkill; "
                f"missing: {sorted(s.value for s in missing)}"
            )
        self._prober = prober
        self._handlers = dict(handlers)
        self._max_rounds = max_rounds

    def answer(
        self,
        question: str,
        first_attempt: RetrievalAttempt,
        hidden_state: Sequence[float],
    ) -> RetrievalResult:
        """Diagnose, dispatch, and bound a Skill-RAG recovery run.

        Pipeline:

        1. Ask the prober to diagnose ``first_attempt`` (one model call).
        2. Look up the matching ``RecoveryHandler`` from the registry.
        3. Delegate ``recover(...)`` to that handler.
        4. Stitch the handler's rounds onto the leading ``first_attempt``,
           and *cap* the resulting list at ``self._max_rounds`` (any
           handler that explores more than the operator's budget is
           treated as a recoverable bug, not a hard failure).
        5. Return a fresh ``RetrievalResult`` that carries the prober's
           verdict (so downstream telemetry can grep on it) and the
           handler's answer / cost.

        The ``EXIT`` skill's contract — return ``None`` rather than
        hallucinate — is honoured by simply propagating whatever the
        registered ``RecoveryHandler`` returns; the EXIT handler in any
        sane registry returns ``answer=None``.
        """
        verdict = self._prober.diagnose(question, first_attempt, hidden_state)
        handler = self._handlers[verdict.recommended_skill]
        downstream = handler.recover(question, first_attempt)

        all_rounds = (first_attempt, *downstream.rounds)
        capped_rounds = all_rounds[: self._max_rounds]

        return RetrievalResult(
            answer=downstream.answer,
            used_skill=verdict.recommended_skill,
            rounds=capped_rounds,
            verdict=verdict,
            cost_tokens=downstream.cost_tokens,
        )
