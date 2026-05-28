"""Meta-knowledge accumulation — distilled insights from agent execution.

Captures high-level insights, invariants, and anti-patterns discovered
across sessions as structured meta-knowledge entries.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class KnowledgeType(StrEnum):
    INVARIANT = "invariant"
    HEURISTIC = "heuristic"
    ANTI_PATTERN = "anti_pattern"
    BEST_PRACTICE = "best_practice"
    CONSTRAINT = "constraint"


class KnowledgeConfidence(StrEnum):
    HYPOTHESIS = "hypothesis"
    OBSERVED = "observed"
    CONFIRMED = "confirmed"
    PROVEN = "proven"


@dataclass(frozen=True)
class MetaKnowledge:
    entry_id: str
    knowledge_type: KnowledgeType
    statement: str
    confidence: KnowledgeConfidence
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    source_sessions: list[str]
    created_at: float
    last_updated: float

    @property
    def evidence_ratio(self) -> float:
        support = len(self.supporting_evidence)
        contradict = len(self.contradicting_evidence)
        if support + contradict == 0:
            return 0.5
        return support / (support + contradict)


class MetaKnowledgeStore:
    """Accumulates distilled insights from agent execution across sessions."""

    def __init__(self) -> None:
        self._entries: dict[str, MetaKnowledge] = {}

    def add(
        self,
        knowledge_type: KnowledgeType,
        statement: str,
        *,
        confidence: KnowledgeConfidence = KnowledgeConfidence.HYPOTHESIS,
        session_id: str | None = None,
        evidence: str | None = None,
    ) -> MetaKnowledge:
        content = f"{knowledge_type.value}|{statement}"
        entry_id = hashlib.sha256(content.encode()).hexdigest()[:14]

        if entry_id in self._entries:
            existing = self._entries[entry_id]
            new_support = list(existing.supporting_evidence)
            if evidence:
                new_support.append(evidence)
            new_confidence = (
                KnowledgeConfidence.CONFIRMED
                if len(new_support) >= 3
                else KnowledgeConfidence.OBSERVED
            )
            updated = MetaKnowledge(
                entry_id=entry_id,
                knowledge_type=knowledge_type,
                statement=statement,
                confidence=new_confidence,
                supporting_evidence=new_support,
                contradicting_evidence=existing.contradicting_evidence,
                source_sessions=list(set(existing.source_sessions + ([session_id] if session_id else []))),
                created_at=existing.created_at,
                last_updated=time.time(),
            )
        else:
            updated = MetaKnowledge(
                entry_id=entry_id,
                knowledge_type=knowledge_type,
                statement=statement,
                confidence=confidence,
                supporting_evidence=[evidence] if evidence else [],
                contradicting_evidence=[],
                source_sessions=[session_id] if session_id else [],
                created_at=time.time(),
                last_updated=time.time(),
            )

        self._entries[entry_id] = updated
        return updated

    def contradict(self, entry_id: str, evidence: str) -> MetaKnowledge | None:
        entry = self._entries.get(entry_id)
        if entry is None:
            return None
        new_contra = list(entry.contradicting_evidence) + [evidence]
        ratio = len(entry.supporting_evidence) / max(len(new_contra), 1)
        new_conf = (
            KnowledgeConfidence.HYPOTHESIS if ratio < 1.0
            else entry.confidence
        )
        updated = MetaKnowledge(
            entry_id=entry.entry_id,
            knowledge_type=entry.knowledge_type,
            statement=entry.statement,
            confidence=new_conf,
            supporting_evidence=entry.supporting_evidence,
            contradicting_evidence=new_contra,
            source_sessions=entry.source_sessions,
            created_at=entry.created_at,
            last_updated=time.time(),
        )
        self._entries[entry_id] = updated
        return updated

    def query(
        self,
        knowledge_type: KnowledgeType | None = None,
        min_confidence: KnowledgeConfidence | None = None,
    ) -> list[MetaKnowledge]:
        results = list(self._entries.values())
        if knowledge_type is not None:
            results = [e for e in results if e.knowledge_type == knowledge_type]
        if min_confidence is not None:
            conf_order = list(KnowledgeConfidence)
            results = [
                e for e in results
                if conf_order.index(e.confidence) >= conf_order.index(min_confidence)
            ]
        return sorted(results, key=lambda e: e.evidence_ratio, reverse=True)

    def stats(self) -> dict:
        return {
            "total_entries": len(self._entries),
            "by_type": {
                kt.value: sum(1 for e in self._entries.values() if e.knowledge_type == kt)
                for kt in KnowledgeType
            },
        }
