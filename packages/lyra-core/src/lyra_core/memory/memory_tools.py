"""Letta-style memory tool surface (L38-4).

Exposes a single ``MemoryToolset`` whose four ops — ``recall``,
``remember``, ``forget``, ``improve`` — fan out across Lyra's three
existing memory substores:

* :class:`~lyra_core.memory.auto_memory.AutoMemory` — user / feedback /
  project / reference entries (the v3.7 L37-6 substrate).
* :class:`~lyra_core.memory.procedural.ProceduralMemory` — skill /
  procedure storage with SQLite FTS5.
* :class:`~lyra_core.memory.reasoning_bank_store.SqliteReasoningBank` —
  trajectory-distilled lessons.

Each op emits typed HIR events via :func:`lyra_core.hir.events.emit` so
the agent's reasoning trace records every memory access — the Letta
inversion (memory ops as tool calls, not out-of-band runtime).

L38-1 (mem0) and L38-2 (Cognee) wire-ins land later as adapters that
add new ``scope`` values without changing this surface. L38-3 (PPR
fusion) extends ``recall`` to fuse rankings across scopes.

See [`docs/185-memory-integration-playbook.md`](../../../../../../docs/185-memory-integration-playbook.md)
§2.2 for the full Lyra v3.8 plan.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Union

from ..hir.events import emit as hir_emit
from .auto_memory import AutoMemory, MemoryEntry, MemoryKind
from .consolidator import ConsolidationProposal, MemoryConsolidator
from .contradictions import ContradictionDetector, ContradictionPair
from .fusion import rrf_topk
from .procedural import ProceduralMemory, SkillRecord
from .reasoning_bank import Lesson, ReasoningBank, TrajectoryOutcome
from .reasoning_bank_store import SqliteReasoningBank
from .redactor import redact_pair


Scope = str   # "auto" | "skill" | "lesson" | "any"

# A single returned record can be one of three shapes — the toolset
# normalises shape via ``RecallResult.payload`` so callers don't need to
# branch on type.
SourceRecord = Union[MemoryEntry, SkillRecord, Lesson]


@dataclass(frozen=True)
class RecallResult:
    """One result row from :meth:`MemoryToolset.recall`.

    ``scope`` reports which substrate produced the row — useful when
    the caller asks ``scope="any"`` and gets a mixed result set.
    """

    scope: str          # "auto" | "skill" | "lesson"
    record_id: str      # entry_id / skill id / lesson id
    title: str
    body: str
    score: float = 0.0  # tier-local rank score (not cross-scope normalised)
    payload: Optional[SourceRecord] = field(default=None, repr=False)


@dataclass(frozen=True)
class ImproveResult:
    """Outcome of a :meth:`MemoryToolset.improve` heartbeat call."""

    auto_entries_active: int
    skill_count: int
    lesson_count: int
    duration_s: float
    contradictions: tuple["ContradictionPair", ...] = ()
    consolidations: tuple["ConsolidationProposal", ...] = ()

    @property
    def contradiction_count(self) -> int:
        return len(self.contradictions)

    @property
    def consolidation_count(self) -> int:
        return len(self.consolidations)


@dataclass
class MemoryToolset:
    """Letta-style tool surface over Lyra's memory substores.

    All substores are optional; the toolset handles whatever is wired.
    Tests typically inject one of each; production wires from
    application config.
    """

    auto_memory: Optional[AutoMemory] = None
    procedural: Optional[ProceduralMemory] = None
    reasoning_bank: Optional[Union[SqliteReasoningBank, ReasoningBank]] = None
    contradiction_detector: Optional[ContradictionDetector] = None
    consolidator: Optional[MemoryConsolidator] = None

    # --- recall ----------------------------------------------------------

    def recall(
        self,
        query: str,
        *,
        scope: Scope = "any",
        top_k: int = 5,
        fusion: str = "rrf",
        rrf_k: int = 60,
    ) -> tuple[RecallResult, ...]:
        """Return the top-K records across the chosen scope.

        ``scope`` is one of ``"auto"`` / ``"skill"`` / ``"lesson"`` /
        ``"any"``.

        For ``scope="any"`` two ``fusion`` modes are supported:

        * ``"rrf"`` (default, v3.8) — Reciprocal Rank Fusion (k=60)
          merges the per-substore rankings into one distribution-
          invariant ordering. Closes the gap that score scales aren't
          comparable across auto / procedural / lesson.
        * ``"concat"`` — legacy v3.7 behaviour: per-substore order
          preserved, results concatenated and truncated.

        Single-scope calls ignore ``fusion`` and return scope-local order.
        """
        hir_emit(
            "memory.recall.start",
            query_preview=query[:200], scope=scope, top_k=top_k,
            fusion=fusion if scope == "any" else "single",
        )
        per_scope: dict[str, list[RecallResult]] = {}

        if scope in ("auto", "any") and self.auto_memory is not None:
            per_scope["auto"] = [
                _recall_from_entry(entry)
                for entry in self.auto_memory.retrieve(query, top_n=top_k)
            ]

        if scope in ("skill", "any") and self.procedural is not None:
            per_scope["skill"] = [
                _recall_from_skill(skill)
                for skill in self.procedural.search(query)
            ]

        if scope in ("lesson", "any") and self.reasoning_bank is not None:
            per_scope["lesson"] = [
                _recall_from_lesson(lesson)
                for lesson in self.reasoning_bank.recall(
                    task_signature=query, k=top_k,
                )
            ]

        if scope != "any" or fusion == "concat":
            # Concatenate in the legacy order (auto, skill, lesson).
            ordered: list[RecallResult] = []
            for s in ("auto", "skill", "lesson"):
                ordered.extend(per_scope.get(s, []))
            out = tuple(ordered[:top_k])
        else:
            # RRF over the three rankings. Keys are namespaced by scope
            # so a record_id collision across substores doesn't merge.
            rankings = []
            lookup: dict[str, RecallResult] = {}
            for s, results in per_scope.items():
                rk = []
                for r in results:
                    key = f"{s}::{r.record_id}"
                    rk.append(key)
                    lookup[key] = r
                if rk:
                    rankings.append(rk)
            merged = rrf_topk(rankings, top_k=top_k, k=rrf_k)
            out = tuple(
                _with_score(lookup[key], score) for key, score in merged
                if key in lookup
            )

        hir_emit(
            "memory.recall.end",
            query_preview=query[:200], scope=scope,
            result_count=len(out),
            top_scope=out[0].scope if out else None,
            fusion=fusion if scope == "any" else "single",
        )
        return out

    # --- remember --------------------------------------------------------

    def remember(
        self,
        text: str,
        *,
        scope: Scope,
        title: str = "",
        kind: Optional[MemoryKind] = None,
        skill_id: Optional[str] = None,
        skill_name: Optional[str] = None,
        skill_description: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> RecallResult:
        """Write a new memory to the chosen substrate.

        Per scope:

        * ``"auto"`` — pass ``kind`` (``MemoryKind``); ``title`` defaults
          to first 80 chars of ``text``. Returns the appended entry.
        * ``"skill"`` — pass ``skill_id`` + ``skill_name`` +
          ``skill_description``; ``text`` is the skill body.
        * ``"lesson"`` — not supported via ``remember`` (lessons are
          distilled from trajectories, not directly authored).
        """
        if scope == "any":
            raise ValueError(
                "remember() needs an explicit scope ('auto', 'skill'); "
                "'any' is read-only"
            )
        hir_emit("memory.remember.start", scope=scope, title_preview=title[:80])

        # LBL-MEMORY-WRITE-REDACT: strip known secret patterns before
        # they reach disk. Audit-trail the hits so a near-miss is
        # visible in the HIR replay.
        (redacted_text, redacted_title), hits = redact_pair(text, title)
        if hits:
            hir_emit(
                "memory.remember.redacted",
                scope=scope,
                hits=list(hits),
                bright_line="LBL-MEMORY-WRITE-REDACT",
            )
        text = redacted_text
        title = redacted_title

        if scope == "auto":
            if self.auto_memory is None:
                raise ValueError("remember(scope='auto') requires auto_memory wired")
            entry_kind = kind if kind is not None else MemoryKind.PROJECT
            written = self.auto_memory.save(
                kind=entry_kind,
                title=title or text[:80],
                body=text,
                extra=extra,
            )
            result = _recall_from_entry(written)
        elif scope == "skill":
            if self.procedural is None:
                raise ValueError("remember(scope='skill') requires procedural wired")
            if not (skill_id and skill_name and skill_description is not None):
                raise ValueError(
                    "remember(scope='skill') requires skill_id, skill_name, "
                    "skill_description"
                )
            record = SkillRecord(
                id=skill_id, name=skill_name,
                description=skill_description, body=text,
            )
            self.procedural.put(record)
            result = _recall_from_skill(record)
        elif scope == "lesson":
            raise ValueError(
                "remember(scope='lesson') is not supported; lessons are "
                "distilled from trajectories via ReasoningBank.record()"
            )
        else:
            raise ValueError(f"unknown scope {scope!r}")

        hir_emit(
            "memory.remember.end",
            scope=scope, record_id=result.record_id, ok=True,
        )
        return result

    # --- forget ----------------------------------------------------------

    def forget(self, record_id: str, *, scope: Scope) -> bool:
        """Tombstone a memory record. Returns True on success.

        Lessons cannot be forgotten via this surface (they are
        immutable distillations); callers must rebuild the bank.
        """
        hir_emit("memory.forget.start", scope=scope, record_id=record_id)
        ok = False
        if scope == "auto":
            if self.auto_memory is None:
                raise ValueError("forget(scope='auto') requires auto_memory wired")
            try:
                self.auto_memory.forget(record_id)
                ok = True
            except KeyError:
                ok = False
        elif scope == "skill":
            raise ValueError(
                "forget(scope='skill') is not supported on ProceduralMemory; "
                "use put() with replacement content instead"
            )
        elif scope == "lesson":
            raise ValueError(
                "forget(scope='lesson') is not supported; lessons are "
                "immutable distillations of trajectories"
            )
        else:
            raise ValueError(f"unknown scope {scope!r}")

        hir_emit("memory.forget.end", scope=scope, record_id=record_id, ok=ok)
        return ok

    # --- commit consolidation -------------------------------------------

    def commit_consolidation(
        self,
        proposal: ConsolidationProposal,
        *,
        polarity: TrajectoryOutcome = TrajectoryOutcome.SUCCESS,
        lesson_id: Optional[str] = None,
    ) -> Lesson:
        """Promote a :class:`ConsolidationProposal` into a reasoning_bank lesson.

        Closes the episodic→semantic→procedural ladder: the consolidator
        proposes (in :meth:`improve`), the host reviews, the host commits.
        The proposal's ``member_entry_ids`` become the lesson's
        ``source_trajectory_ids`` so audit can trace back to the
        auto_memory entries that fed the consolidation.

        ``polarity`` defaults to SUCCESS (a strategy lesson). Pass
        ``FAILURE`` to commit a failure-pattern proposal as an
        anti-skill.

        Bright-line: ``LBL-MEMORY-CONSOLIDATE-COMMIT`` — every commit
        emits a HIR event with the bright-line code and the proposal's
        member ids so the audit log records the promotion.
        """
        if self.reasoning_bank is None:
            raise ValueError(
                "commit_consolidation requires reasoning_bank to be wired"
            )
        if not proposal.member_entry_ids:
            raise ValueError("commit_consolidation: proposal has no members")
        lid = lesson_id or _consolidation_lesson_id(proposal)
        # Use the cluster's shared-token core as the task signatures so
        # downstream `recall(task_signature=...)` finds the lesson by
        # any of the consolidated entries' top tokens.
        signatures = tuple(proposal.shared_tokens[:8]) or (proposal.proposed_title,)
        lesson = Lesson(
            id=lid,
            polarity=polarity,
            title=proposal.proposed_title,
            body=proposal.proposed_body,
            task_signatures=signatures,
            source_trajectory_ids=proposal.member_entry_ids,
        )
        self.reasoning_bank.record_lesson(lesson)
        hir_emit(
            "memory.consolidate.commit",
            lesson_id=lid,
            cluster_kind=proposal.cluster_kind.value,
            member_count=proposal.member_count,
            cohesion=proposal.cohesion,
            bright_line="LBL-MEMORY-CONSOLIDATE-COMMIT",
        )
        return lesson

    # --- improve ---------------------------------------------------------

    def improve(self) -> ImproveResult:
        """Heartbeat hook — cardinalities + contradiction + consolidation pass.

        v3.8 (steal from agentmemory): runs two analysis passes when
        the corresponding analyser is wired:

        * :class:`ContradictionDetector` flags pairs of auto-memory
          entries with similar titles but divergent bodies. Surfaced
          for the host harness to resolve; never auto-forgotten.
        * :class:`MemoryConsolidator` groups recurring auto-memory
          entries by token cluster and proposes one semantic-lesson
          candidate per cluster of ≥ 3 members.
        """
        hir_emit("memory.improve.start")
        start = time.time()
        auto_active = len(self.auto_memory) if self.auto_memory else 0
        skill_count = len(self.procedural.all()) if self.procedural else 0
        if self.reasoning_bank is not None:
            stats = self.reasoning_bank.stats()
            lesson_count = stats.get("lessons", 0)
        else:
            lesson_count = 0

        contradictions: tuple[ContradictionPair, ...] = ()
        consolidations: tuple[ConsolidationProposal, ...] = ()
        if self.auto_memory is not None:
            entries = self.auto_memory.all()
            if self.contradiction_detector is not None:
                contradictions = self.contradiction_detector.detect(entries)
            if self.consolidator is not None:
                consolidations = self.consolidator.propose(entries)

        result = ImproveResult(
            auto_entries_active=auto_active,
            skill_count=skill_count,
            lesson_count=lesson_count,
            duration_s=time.time() - start,
            contradictions=contradictions,
            consolidations=consolidations,
        )
        hir_emit(
            "memory.improve.end",
            auto_entries_active=result.auto_entries_active,
            skill_count=result.skill_count,
            lesson_count=result.lesson_count,
            duration_s=result.duration_s,
            contradiction_count=result.contradiction_count,
            consolidation_count=result.consolidation_count,
            ok=True,
        )
        return result


# --- internal converters ---------------------------------------------


def _recall_from_entry(entry: MemoryEntry) -> RecallResult:
    return RecallResult(
        scope="auto", record_id=entry.entry_id,
        title=entry.title, body=entry.body, payload=entry,
    )


def _recall_from_skill(skill: SkillRecord) -> RecallResult:
    return RecallResult(
        scope="skill", record_id=skill.id,
        title=skill.name, body=skill.body, payload=skill,
    )


def _recall_from_lesson(lesson: Lesson) -> RecallResult:
    return RecallResult(
        scope="lesson", record_id=lesson.id,
        title=lesson.title, body=lesson.body, payload=lesson,
    )


def _with_score(result: RecallResult, score: float) -> RecallResult:
    """Return a copy of ``result`` with the RRF score attached."""
    return RecallResult(
        scope=result.scope, record_id=result.record_id,
        title=result.title, body=result.body, score=score,
        payload=result.payload,
    )


def _consolidation_lesson_id(proposal: ConsolidationProposal) -> str:
    """Stable lesson id derived from the proposal's member ids.

    Two commits of the same cluster (e.g. on consecutive heartbeats)
    produce the same id, so the bank's idempotent ``record_lesson``
    safely de-dupes.
    """
    import hashlib
    payload = (
        proposal.cluster_kind.value
        + "|"
        + "|".join(sorted(proposal.member_entry_ids))
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"consolidation-{digest}"


__all__ = [
    "ImproveResult",
    "MemoryToolset",
    "RecallResult",
    "Scope",
    "SourceRecord",
]
