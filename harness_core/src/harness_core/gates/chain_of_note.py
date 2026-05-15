"""Chain-of-Note: per-doc relevance gate before reasoning injection.

Yu et al. 2024 (arXiv:2311.09210). For each retrieved doc, prompt the LM to
write a short note assessing whether the doc actually contributes to the query.
Docs scored below threshold are dropped; the rest enter reasoning.

Headline numbers: +7.9 EM on entirely-noisy retrievals; +10.5 rejection rate
on out-of-knowledge questions.

Why a gate, not a skill:
    - Per [docs/172] §2 — quality checks belong in the gate layer where they
      can fail closed.
    - Composes orthogonally with multi-hop chain construction; every hop's
      retrieval can be CoN-gated.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol


class NoteVerdict(str, enum.Enum):
    """Three-way verdict on a doc's relevance."""

    RELEVANT = "relevant"
    PARTIAL = "partial"
    IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class DocVerdict:
    """The LM's per-doc judgement."""

    doc_id: str
    verdict: NoteVerdict
    note: str  # short note explaining the verdict
    score: float = 0.0  # 0.0..1.0; relevance score derived from verdict + heuristics

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")


@dataclass
class ScoredDoc:
    """A doc that passed (or failed) the gate, with the verdict attached."""

    doc_id: str
    content: str
    verdict: DocVerdict
    passed: bool


class _NoteWriter(Protocol):
    """Protocol for the LM-side note-writer.

    Production: wires an LLM call. Tests: deterministic stub.
    """

    def __call__(self, *, query: str, doc_id: str, content: str) -> DocVerdict: ...


def _default_score_for(verdict: NoteVerdict) -> float:
    """Map verdict to a numeric score; tunable per deployment."""
    return {
        NoteVerdict.RELEVANT: 1.0,
        NoteVerdict.PARTIAL: 0.5,
        NoteVerdict.IRRELEVANT: 0.0,
    }[verdict]


@dataclass
class ChainOfNoteGate:
    """Per-doc relevance gate.

    >>> def stub(*, query, doc_id, content):
    ...     v = NoteVerdict.RELEVANT if "match" in content else NoteVerdict.IRRELEVANT
    ...     return DocVerdict(doc_id=doc_id, verdict=v, note="stub", score=_default_score_for(v))
    >>> gate = ChainOfNoteGate(note_writer=stub, threshold=0.5)
    >>> docs = [{"id": "a", "content": "match here"}, {"id": "b", "content": "no"}]
    >>> kept = gate.filter(query="q", docs=docs)
    >>> [d.doc_id for d in kept if d.passed]
    ['a']
    """

    note_writer: _NoteWriter
    threshold: float = 0.5
    score_fn: Callable[[NoteVerdict], float] = field(default=_default_score_for)
    fail_closed: bool = True  # on note_writer error, drop the doc

    def filter(
        self,
        *,
        query: str,
        docs: list[dict[str, str]],
    ) -> list[ScoredDoc]:
        """Return scored docs (all of them, with .passed bool).

        Caller usually does ``[d for d in gate.filter(...) if d.passed]``.

        ``docs`` is a list of dicts with ``id`` and ``content`` keys.
        """
        results: list[ScoredDoc] = []
        for doc in docs:
            doc_id = str(doc["id"])
            content = str(doc.get("content", ""))
            try:
                verdict = self.note_writer(query=query, doc_id=doc_id, content=content)
            except Exception as exc:
                if self.fail_closed:
                    verdict = DocVerdict(
                        doc_id=doc_id,
                        verdict=NoteVerdict.IRRELEVANT,
                        note=f"fail_closed: {exc.__class__.__name__}",
                        score=0.0,
                    )
                else:
                    raise
            passed = verdict.score >= self.threshold
            results.append(
                ScoredDoc(doc_id=doc_id, content=content, verdict=verdict, passed=passed)
            )
        return results

    def filter_passed_only(
        self,
        *,
        query: str,
        docs: list[dict[str, str]],
    ) -> list[ScoredDoc]:
        """Convenience: return only the docs that cleared the threshold."""
        return [d for d in self.filter(query=query, docs=docs) if d.passed]

    def stats(self, results: list[ScoredDoc]) -> dict[str, int]:
        """Aggregate counts: relevant / partial / irrelevant / passed / dropped."""
        c = {"relevant": 0, "partial": 0, "irrelevant": 0, "passed": 0, "dropped": 0}
        for r in results:
            c[r.verdict.verdict.value] += 1
            c["passed" if r.passed else "dropped"] += 1
        return c


__all__ = ["ChainOfNoteGate", "DocVerdict", "NoteVerdict", "ScoredDoc"]
