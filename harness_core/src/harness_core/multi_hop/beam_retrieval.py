"""Beam Retrieval for multi-hop QA (Zhang et al. NAACL 2024, arXiv:2308.08973).

Joint encoder + classification heads across all hops with beam-width
hypothesis tracking. Per [docs/199-multi-hop-reasoning-techniques-arc.md]
(../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md)
Phase 3 — **~50 % gain on MuSiQue-Ans, 99.9 % precision on 2WikiMultiHopQA**.

The SOTA solution when hops > 2. Most retrievers are trained per-hop and only
support 2 hops; Beam Retrieval keeps the top-K hypotheses across all hops with
re-ranking each step.

Implementation: at each hop, every surviving beam expands with the retriever's
top-N candidates conditioned on the beam's accumulated context; a scorer
(Protocol-typed; production = LLM judge or learned ranker; tests = stub) ranks
the new (beam + candidate) tuples; the top ``beam_width`` survive to the next
hop. Termination: a beam is "final" when the scorer flags it accept — the
operator returns the highest-scoring final beam.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, Sequence  # noqa: F401

from .operators.protocols import Retriever, RetrievedDoc


@dataclass(frozen=True, order=True)
class BeamCandidate:
    """One candidate path through the retrieval beam.

    Ordered by ``-score`` so ``sorted(candidates)`` returns best-first.
    Non-sort fields use ``compare=False`` so equal-score candidates don't
    fall through to comparing :class:`RetrievedDoc` tuples (which aren't
    orderable).
    """

    sort_key: float  # negation of score for sort order
    score: float = field(compare=False)
    docs: tuple[RetrievedDoc, ...] = field(default=(), compare=False)
    accept: bool = field(default=False, compare=False)
    reason: str = field(default="", compare=False)

    @classmethod
    def make(
        cls,
        *,
        score: float,
        docs: tuple[RetrievedDoc, ...] | Sequence[RetrievedDoc],
        accept: bool = False,
        reason: str = "",
    ) -> "BeamCandidate":
        return cls(
            sort_key=-score,
            score=score,
            docs=tuple(docs),
            accept=accept,
            reason=reason,
        )

    def doc_ids(self) -> tuple[str, ...]:
        return tuple(d.doc_id for d in self.docs)

    @property
    def n_hops(self) -> int:
        return len(self.docs)


class BeamScorer(Protocol):
    """Score a partial beam against the query.

    Returns ``(score, accept)``: score in [0, 1]; accept = True if this beam
    looks like a complete answer and the search can terminate on this branch.
    """

    name: str

    def score(self, *, query: str, docs: tuple[RetrievedDoc, ...]) -> tuple[float, bool]: ...


@dataclass
class CoverageScorer:
    """Default scorer: rewards keyword coverage of the query across docs.

    Score = (unique query tokens covered) / (total query tokens). Marks the
    beam as ``accept`` once coverage ≥ ``accept_threshold``. Zero-dep; suitable
    for cold-start + as a baseline against which LLM scorers are compared.
    """

    accept_threshold: float = 0.8
    name: str = "coverage-scorer-v1"

    def score(self, *, query: str, docs: tuple[RetrievedDoc, ...]) -> tuple[float, bool]:
        if not query.strip():
            return 0.0, False
        query_tokens = {t.lower() for t in query.split() if len(t) > 2}
        if not query_tokens:
            return 0.0, False
        joined = " ".join(d.text.lower() for d in docs)
        covered = sum(1 for t in query_tokens if t in joined)
        coverage = covered / len(query_tokens)
        return coverage, coverage >= self.accept_threshold


@dataclass
class BeamResult:
    """The full beam search trace + best beam."""

    query: str
    beams: tuple[BeamCandidate, ...]  # all surviving beams at termination
    best: Optional[BeamCandidate]  # highest-scoring (accept-flagged if any)
    n_retrieval_calls: int = 0
    n_score_calls: int = 0
    n_hops_executed: int = 0


@dataclass
class BeamRetriever:
    """Beam search over multi-hop retrieval paths.

    >>> from harness_core.multi_hop.operators import StubRetriever
    >>> from harness_core.multi_hop import RetrievedDoc
    >>> ret = StubRetriever(fixtures={
    ...     "casablanca director": [
    ...         RetrievedDoc(doc_id="d1", text="Casablanca was directed by Curtiz"),
    ...     ],
    ...     "Curtiz": [
    ...         RetrievedDoc(doc_id="d2", text="Michael Curtiz was Hungarian"),
    ...     ],
    ... })
    """

    retriever: Retriever
    beam_width: int = 3
    expand_per_hop: int = 5  # top-N candidates per beam expansion
    max_hops: int = 4
    scorer: BeamScorer = field(default_factory=CoverageScorer)

    def retrieve(self, query: str) -> BeamResult:
        """Run beam search; return all surviving beams + the best."""
        if not query or not query.strip():
            return BeamResult(query=query, beams=(), best=None)

        n_retr = 0
        n_score = 0
        n_hops_executed = 0

        # Hop 0: seed beams with the top-N candidates for the raw query.
        seed_docs = self.retriever.retrieve(query, top_k=self.expand_per_hop)
        n_retr += 1
        if not seed_docs:
            return BeamResult(query=query, beams=(), best=None,
                              n_retrieval_calls=n_retr)

        beams: list[BeamCandidate] = []
        for doc in seed_docs:
            score, accept = self.scorer.score(query=query, docs=(doc,))
            n_score += 1
            beams.append(BeamCandidate.make(
                score=score,
                docs=(doc,),
                accept=accept,
                reason=f"hop=0 score={score:.3f}",
            ))
        beams.sort()
        beams = beams[: self.beam_width]
        n_hops_executed = 1

        # Hops 1..max_hops: expand only non-accept beams.
        for hop in range(1, self.max_hops):
            if all(b.accept for b in beams):
                break

            next_beams: list[BeamCandidate] = []
            # Carry forward already-accepted beams unchanged.
            next_beams.extend(b for b in beams if b.accept)

            for beam in beams:
                if beam.accept:
                    continue
                # Construct next-hop query from accumulated docs (last doc text
                # is the simplest informative seed; production wires the LLM).
                last_text = beam.docs[-1].text if beam.docs else ""
                next_query = self._next_hop_query(query, last_text)
                candidates = self.retriever.retrieve(
                    next_query, top_k=self.expand_per_hop
                )
                n_retr += 1
                seen_ids = {d.doc_id for d in beam.docs}
                for doc in candidates:
                    if doc.doc_id in seen_ids:
                        continue  # skip duplicates within a beam
                    new_docs = beam.docs + (doc,)
                    score, accept = self.scorer.score(query=query, docs=new_docs)
                    n_score += 1
                    next_beams.append(BeamCandidate.make(
                        score=score,
                        docs=new_docs,
                        accept=accept,
                        reason=f"hop={hop} score={score:.3f}",
                    ))

            if not next_beams:
                break

            next_beams.sort()
            beams = next_beams[: self.beam_width]
            n_hops_executed = hop + 1

        # Pick best: prefer accept-flagged; among them, highest score.
        accepted = [b for b in beams if b.accept]
        best = (accepted[0] if accepted else (beams[0] if beams else None))
        if best is not None and accepted:
            # accepted is already sorted because beams is sorted.
            pass

        return BeamResult(
            query=query,
            beams=tuple(beams),
            best=best,
            n_retrieval_calls=n_retr,
            n_score_calls=n_score,
            n_hops_executed=n_hops_executed,
        )

    @staticmethod
    def _next_hop_query(original_query: str, last_doc_text: str) -> str:
        """Compose the next-hop retrieval query.

        Default: concatenate query + last doc text (truncated). Production
        wires an LLM that extracts the bridge entity; tests use this default.
        """
        truncated = last_doc_text[:200]
        return f"{original_query} {truncated}".strip()


__all__ = [
    "BeamCandidate",
    "BeamResult",
    "BeamRetriever",
    "BeamScorer",
    "CoverageScorer",
]
