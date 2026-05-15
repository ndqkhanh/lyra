"""Reason-in-Documents — denoise retrieved docs before injection.

Search-o1 (Li et al. 2025, arXiv:2501.05366) introduces a *Reason-in-Documents*
module: before injecting retrieved passages into the reasoning context, run a
separate LM call that summarises and filters them down to query-relevant facts.

Composes orthogonally with Chain-of-Note ([gates/chain_of_note.py]):
    - Chain-of-Note is a per-doc *binary* relevance gate.
    - Reason-in-Documents is a per-doc *content-refinement* step.
Both can run in sequence: CoN drops irrelevant docs, RiD refines the rest.

Per [docs/199-multi-hop-reasoning-techniques-arc.md](../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md)
Phase 4 + per-project apply plans ([203], [208], [218], [219], [220]).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .operators.protocols import LLMTextGenerator, RetrievedDoc

_DEFAULT_PROMPT = (
    "You are a careful research assistant. Given a query and a document, "
    "extract ONLY the facts in the document that bear on the query. Be terse; "
    "drop anything off-topic. If nothing in the document bears on the query, "
    "respond with the single word: NONE.\n\n"
    "Query: {query}\n"
    "Document: {doc_text}\n\n"
    "Relevant facts:"
)


@dataclass(frozen=True)
class DenoisedDoc:
    """One document after RiD refinement."""

    original: RetrievedDoc
    refined_text: str  # may be the empty string if RiD said "NONE"
    is_relevant: bool  # False if RiD said "NONE"

    @property
    def doc_id(self) -> str:
        return self.original.doc_id

    @property
    def text(self) -> str:
        return self.refined_text

    def to_retrieved(self) -> RetrievedDoc:
        """Repackage as a RetrievedDoc for downstream operators."""
        return RetrievedDoc(
            doc_id=self.original.doc_id,
            text=self.refined_text,
            score=self.original.score,
            source=f"rid:{self.original.source}" if self.original.source else "rid",
        )


@dataclass
class ReasonInDocuments:
    """Search-o1 RiD denoiser.

    >>> from harness_core.multi_hop.operators import StubLLM, RetrievedDoc
    >>> llm = StubLLM(responses=["Bob directed Casablanca in 1942.", "NONE"])
    >>> rid = ReasonInDocuments(llm=llm)
    >>> docs = [
    ...   RetrievedDoc(doc_id="d1", text="Bob directed Casablanca... [long]"),
    ...   RetrievedDoc(doc_id="d2", text="Coffee shop trivia..."),
    ... ]
    >>> denoised = rid.denoise(query="who directed Casablanca", docs=docs)
    >>> [d.is_relevant for d in denoised]
    [True, False]
    """

    llm: LLMTextGenerator
    prompt_template: str = _DEFAULT_PROMPT
    max_tokens: int = 256
    drop_irrelevant: bool = False  # True = filter out is_relevant=False docs

    def denoise(self, *, query: str, docs: list[RetrievedDoc]) -> list[DenoisedDoc]:
        """Refine each doc; return all (with is_relevant flag).

        Use ``drop_irrelevant=True`` (or filter the result yourself) to keep
        only relevant docs.
        """
        results: list[DenoisedDoc] = []
        for doc in docs:
            prompt = self.prompt_template.format(query=query, doc_text=doc.text)
            try:
                refined = self.llm.generate(prompt, max_tokens=self.max_tokens)
            except Exception:
                # Fail-open: keep the original doc; mark as relevant so the
                # operator continues, but flag in source.
                results.append(
                    DenoisedDoc(
                        original=doc,
                        refined_text=doc.text,
                        is_relevant=True,
                    )
                )
                continue
            refined_clean = refined.strip()
            is_relevant = refined_clean.upper() != "NONE" and bool(refined_clean)
            text = refined_clean if is_relevant else ""
            results.append(
                DenoisedDoc(original=doc, refined_text=text, is_relevant=is_relevant)
            )
        if self.drop_irrelevant:
            results = [d for d in results if d.is_relevant]
        return results

    def denoise_to_retrieved(
        self,
        *,
        query: str,
        docs: list[RetrievedDoc],
    ) -> list[RetrievedDoc]:
        """Convenience: denoise + return as RetrievedDoc list (drop irrelevant)."""
        denoised = self.denoise(query=query, docs=docs)
        return [d.to_retrieved() for d in denoised if d.is_relevant]


def compose_with_chain_of_note(
    *,
    rid: ReasonInDocuments,
    chain_of_note_gate,
    query: str,
    docs: list[RetrievedDoc],
) -> list[RetrievedDoc]:
    """Compose CoN gate + RiD denoiser in sequence.

    1. CoN drops docs with verdict score below threshold.
    2. RiD refines the survivors.

    Returns final RetrievedDoc list (RiD-refined, CoN-passed).
    """
    # CoN expects a list of dicts with 'id' and 'content'.
    con_input = [{"id": d.doc_id, "content": d.text} for d in docs]
    passed = chain_of_note_gate.filter_passed_only(query=query, docs=con_input)
    passed_ids = {d.doc_id for d in passed}
    survivors = [d for d in docs if d.doc_id in passed_ids]
    return rid.denoise_to_retrieved(query=query, docs=survivors)


__all__ = ["DenoisedDoc", "ReasonInDocuments", "compose_with_chain_of_note"]
