"""Retraction-aware retrieval gate.

Per [docs/219-helix-bio-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/219-helix-bio-multi-hop-collaborative-apply-plan.md) §3.1,
[docs/172-polaris-2026-deep-research-roadmap.md](../../../../../../research/harness-engineering/docs/172-polaris-2026-deep-research-roadmap.md) §3 Gap 5,
and JMIR 2026 e88766 — **retracted papers must be filtered at the retrieval
layer, not the LLM-prompt layer**. Major AI tools cite retracted literature
without warning even when explicitly asked.

This module ships a :class:`RetractionGate` that:
    1. Looks up each retrieved doc against a :class:`RetractionIndex` Protocol
       (production wires RetractionWatch / PubMed retraction databases).
    2. Drops retracted docs from the result.
    3. Returns the audit list of what was retracted (so the agent can flag it
       in the answer's provenance).

A retracted paper *cited as load-bearing evidence* is the kind of failure that
ends a biomed agent's deployment. This is Tier-0 for Helix-Bio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass(frozen=True)
class RetractionRecord:
    """One retracted-paper record."""

    paper_id: str  # DOI, PMID, ArXiv ID, or whatever the index uses
    retracted_at: float = 0.0  # epoch seconds; 0 = unknown
    reason: str = ""
    source: str = ""  # "RetractionWatch" | "PubMed" | "JournalNotice"


class RetractionIndex(Protocol):
    """Protocol: look up whether a paper id has been retracted.

    Production wires a database client to RetractionWatch / PubMed.
    Tests use the dict-backed :class:`StaticRetractionIndex`.
    """

    name: str

    def is_retracted(self, paper_id: str) -> Optional[RetractionRecord]: ...


@dataclass
class StaticRetractionIndex:
    """Dict-backed retraction index — for tests + cold-start defaults.

    >>> idx = StaticRetractionIndex(records={
    ...   "10.1038/nature.2020.fake": RetractionRecord(
    ...     paper_id="10.1038/nature.2020.fake",
    ...     reason="data fabrication",
    ...     source="RetractionWatch",
    ...   ),
    ... })
    >>> rec = idx.is_retracted("10.1038/nature.2020.fake")
    >>> rec is not None
    True
    """

    records: dict[str, RetractionRecord] = field(default_factory=dict)
    name: str = "static-retraction-index"

    def add(self, record: RetractionRecord) -> None:
        self.records[record.paper_id] = record

    def is_retracted(self, paper_id: str) -> Optional[RetractionRecord]:
        return self.records.get(paper_id)


@dataclass(frozen=True)
class RetractionVerdict:
    """The gate's per-doc decision."""

    doc_id: str
    paper_id: Optional[str]  # may be None if the doc had no extractable id
    is_retracted: bool
    record: Optional[RetractionRecord]
    note: str = ""


@dataclass
class RetractionGate:
    """Drop retracted papers from retrieved doc lists.

    Two extraction modes for paper IDs:
        - ``id_field``: read a named attribute / dict key (default ``paper_id``).
        - ``id_extractor``: caller-supplied callable that derives the id from
          arbitrary doc shapes (string, dict, dataclass, etc.).

    Fail-closed semantics: when the index lookup raises (network failure), the
    doc is **dropped** (with a "lookup error" note in the audit). Conservative
    by design — a citation a regulator can't verify is worse than a missing
    citation.
    """

    index: RetractionIndex
    fail_closed: bool = True

    def filter(
        self,
        docs: list[dict],
        *,
        id_field: str = "paper_id",
    ) -> tuple[list[dict], list[RetractionVerdict]]:
        """Filter retracted docs out. Returns ``(kept, all_verdicts)``.

        ``all_verdicts`` includes every doc — kept ones with ``is_retracted=False``,
        dropped ones with ``is_retracted=True``. Use this for the audit log;
        attach to the agent's answer as provenance.
        """
        kept: list[dict] = []
        verdicts: list[RetractionVerdict] = []
        for doc in docs:
            doc_id = str(doc.get("id") or doc.get("doc_id") or "")
            paper_id_raw = doc.get(id_field)
            paper_id = str(paper_id_raw) if paper_id_raw else None
            verdict = self._check(doc_id=doc_id, paper_id=paper_id)
            verdicts.append(verdict)
            if not verdict.is_retracted:
                kept.append(doc)
        return kept, verdicts

    def _check(self, *, doc_id: str, paper_id: Optional[str]) -> RetractionVerdict:
        if not paper_id:
            return RetractionVerdict(
                doc_id=doc_id,
                paper_id=None,
                is_retracted=False,
                record=None,
                note="no paper_id; cannot check retraction status",
            )
        try:
            record = self.index.is_retracted(paper_id)
        except Exception as exc:
            if self.fail_closed:
                # Treat lookup failure as retracted (drop the doc).
                return RetractionVerdict(
                    doc_id=doc_id,
                    paper_id=paper_id,
                    is_retracted=True,
                    record=None,
                    note=f"fail_closed: index error: {exc.__class__.__name__}",
                )
            # Fail-open: assume not retracted; flag in note.
            return RetractionVerdict(
                doc_id=doc_id,
                paper_id=paper_id,
                is_retracted=False,
                record=None,
                note=f"fail_open: index error: {exc.__class__.__name__}",
            )
        if record is not None:
            return RetractionVerdict(
                doc_id=doc_id,
                paper_id=paper_id,
                is_retracted=True,
                record=record,
                note=f"retracted: {record.reason or 'unspecified'}",
            )
        return RetractionVerdict(
            doc_id=doc_id,
            paper_id=paper_id,
            is_retracted=False,
            record=None,
            note="not retracted",
        )

    def stats(self, verdicts: list[RetractionVerdict]) -> dict[str, int]:
        return {
            "total": len(verdicts),
            "retracted": sum(1 for v in verdicts if v.is_retracted),
            "kept": sum(1 for v in verdicts if not v.is_retracted),
            "no_paper_id": sum(1 for v in verdicts if v.paper_id is None),
        }


__all__ = [
    "RetractionGate",
    "RetractionIndex",
    "RetractionRecord",
    "RetractionVerdict",
    "StaticRetractionIndex",
]
