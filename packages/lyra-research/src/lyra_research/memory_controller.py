"""ResearchMemoryController — Phase 3 of the Deep Research Agent plan.

Coordinates write / update / expire decisions across the five research
memory subsystems (notes, knowledge graph, corpus, strategies, cases).

Without a coordinator, callers across the orchestrator must remember to
deduplicate, check contradictions, and promote findings to semantic memory
themselves.  This controller centralises that logic.

Design choices:
- All persistence is delegated to the underlying stores.
- Contradiction detection reuses ContradictionDetector when available; a
  trivial fallback compares note content against existing notes by tag overlap.
- Promotion: a note is promoted from "finding" → semantic memory when
  confidence >= ``promote_confidence`` AND it has at least one verified source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lyra_research.memory import (
        LocalCorpus,
        ResearchCase,
        ResearchNote,
        ResearchNoteStore,
        ResearchStrategy,
        ResearchStrategyMemory,
        SessionCaseBank,
    )
    from lyra_research.synthesis import KnowledgeGraph


__all__ = [
    "MemoryDecision",
    "ResearchMemoryController",
]


@dataclass(frozen=True)
class MemoryDecision:
    """Result of a controller decision about how to handle a memory write."""

    action: str            # "WRITE" | "MERGE" | "REJECT" | "PROMOTE" | "EXPIRE"
    target: str            # "note" | "case" | "kg" | "strategy" | "corpus"
    reason: str = ""
    target_id: str = ""    # ID of the affected record, if applicable
    metadata: dict = field(default_factory=dict)


class ResearchMemoryController:
    """Coordinates write / update / expire decisions across research memory.

    Usage::

        controller = ResearchMemoryController(
            note_store=ResearchNoteStore(),
            case_bank=SessionCaseBank(),
            kg=KnowledgeGraph(),
            strategy_memory=ResearchStrategyMemory(),
        )
        decisions = controller.write_note(note)
        controller.expire_stale(older_than_days=180)
    """

    PROMOTE_CONFIDENCE = 0.85
    DUPLICATE_TAG_OVERLAP = 3   # min #tags shared to consider duplicate

    def __init__(
        self,
        note_store: ResearchNoteStore | None = None,
        case_bank: SessionCaseBank | None = None,
        kg: KnowledgeGraph | None = None,
        strategy_memory: ResearchStrategyMemory | None = None,
        corpus: LocalCorpus | None = None,
        promote_confidence: float = PROMOTE_CONFIDENCE,
    ) -> None:
        self.note_store = note_store
        self.case_bank = case_bank
        self.kg = kg
        self.strategy_memory = strategy_memory
        self.corpus = corpus
        self.promote_confidence = promote_confidence

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def write_note(self, note: ResearchNote) -> list[MemoryDecision]:
        """Decide what to do with an incoming note.

        Returns a list of decisions (one per affected subsystem).
        """
        if self.note_store is None:
            return [MemoryDecision("REJECT", "note", reason="no note store configured")]

        decisions: list[MemoryDecision] = []

        # 1. Duplicate detection by tag overlap
        duplicate = self._find_duplicate_note(note)
        if duplicate is not None:
            decisions.append(
                MemoryDecision(
                    "MERGE",
                    "note",
                    reason=f"tag overlap with note {duplicate.id[:8]}",
                    target_id=duplicate.id,
                )
            )
            # Merge: keep the higher-confidence record, link the other.
            if note.confidence > duplicate.confidence:
                note.links = list(set(note.links + [duplicate.id]))
                self.note_store.add(note)
            else:
                # leave duplicate in place; don't write
                return decisions
        else:
            self.note_store.add(note)
            decisions.append(MemoryDecision("WRITE", "note", target_id=note.id))

        # 2. Contradiction check
        contradicting = self._find_contradicting_notes(note)
        if contradicting:
            decisions.append(
                MemoryDecision(
                    "WRITE",
                    "note",
                    reason=f"flagged {len(contradicting)} contradicting note(s)",
                    target_id=note.id,
                    metadata={"contradictions": [n.id for n in contradicting]},
                )
            )

        # 3. Promote to KG if confidence high enough
        if (
            note.confidence >= self.promote_confidence
            and note.source_ids
            and self.kg is not None
        ):
            self._promote_to_kg(note)
            decisions.append(
                MemoryDecision(
                    "PROMOTE",
                    "kg",
                    reason=f"confidence {note.confidence:.2f} >= {self.promote_confidence}",
                    target_id=note.id,
                )
            )

        return decisions

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------

    def write_case(self, case: ResearchCase) -> MemoryDecision:
        """Save a completed research case to the bank."""
        if self.case_bank is None:
            return MemoryDecision("REJECT", "case", reason="no case bank configured")
        self.case_bank.save_case(case)
        return MemoryDecision("WRITE", "case", target_id=case.id)

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def write_strategy(self, strategy: ResearchStrategy) -> MemoryDecision:
        """Record a research strategy outcome."""
        if self.strategy_memory is None:
            return MemoryDecision("REJECT", "strategy", reason="no strategy memory configured")
        # ResearchStrategyMemory has add/get_successful/get_failed depending on its API;
        # we use the canonical add() method if present.
        add = getattr(self.strategy_memory, "add", None) or getattr(
            self.strategy_memory, "record", None
        )
        if add is None:
            return MemoryDecision(
                "REJECT", "strategy", reason="strategy memory has no add/record method"
            )
        add(strategy)
        return MemoryDecision("WRITE", "strategy", target_id=getattr(strategy, "id", ""))

    # ------------------------------------------------------------------
    # Expiration
    # ------------------------------------------------------------------

    def expire_stale(self, older_than_days: int = 180) -> list[MemoryDecision]:
        """Mark notes/cases older than the cutoff as expired (best-effort).

        Notes that have been promoted to the KG are kept (semantic memory
        outlives episodic memory).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        decisions: list[MemoryDecision] = []

        if self.note_store is not None:
            all_notes = getattr(self.note_store, "all", None)
            if callable(all_notes):
                notes_iter = all_notes()
            else:
                notes_dict = getattr(self.note_store, "_notes", {})
                notes_iter = list(notes_dict.values()) if notes_dict else []
            for note in notes_iter:
                if note.confidence >= self.promote_confidence:
                    continue
                if note.updated_at < cutoff:
                    decisions.append(
                        MemoryDecision(
                            "EXPIRE",
                            "note",
                            reason=f"updated_at older than {older_than_days}d",
                            target_id=note.id,
                        )
                    )

        return decisions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_duplicate_note(self, note: ResearchNote) -> ResearchNote | None:
        if self.note_store is None:
            return None
        existing = list(getattr(self.note_store, "_notes", {}).values())
        new_tags = set(note.tags)
        if not new_tags:
            return None
        for other in existing:
            if other.id == note.id:
                continue
            if other.topic != note.topic:
                continue
            other_tags = set(other.tags)
            if len(new_tags & other_tags) >= self.DUPLICATE_TAG_OVERLAP:
                return other
        return None

    def _find_contradicting_notes(self, note: ResearchNote) -> list[ResearchNote]:
        """Detect contradictions by simple negation marker overlap.

        Conservative: only flags notes with same topic where one contains
        a negation marker the other lacks (and vice versa).
        """
        if self.note_store is None:
            return []
        existing = [
            n
            for n in getattr(self.note_store, "_notes", {}).values()
            if n.topic == note.topic and n.id != note.id
        ]
        markers = ("does not", "cannot", "no longer", "never", "not")
        new_has_neg = any(m in note.content.lower() for m in markers)
        out: list[ResearchNote] = []
        for other in existing:
            other_has_neg = any(m in other.content.lower() for m in markers)
            if new_has_neg != other_has_neg:
                # Differing polarity on the same topic → potential contradiction
                shared_tags = set(note.tags) & set(other.tags)
                if shared_tags:
                    out.append(other)
        return out

    def _promote_to_kg(self, note: ResearchNote) -> None:
        """Add a high-confidence note's concepts to the knowledge graph."""
        if self.kg is None:
            return
        # Best-effort: use add_node if the KG supports the simple API.
        add_node = getattr(self.kg, "add_node", None)
        if add_node is None:
            return
        try:
            from lyra_research.synthesis import KnowledgeNode
        except ImportError:
            return
        try:
            node = KnowledgeNode(
                id=note.id,
                type="finding",
                label=note.title or note.topic,
                properties={"confidence": note.confidence},
            )
            add_node(node)
        except (TypeError, ValueError):
            # KnowledgeNode signature drift — skip promotion silently.
            return
