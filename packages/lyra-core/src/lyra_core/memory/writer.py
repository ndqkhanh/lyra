"""Fragment Writer — routes new fragments to ADD/UPDATE/SUPERSEDE/DEDUPE/NOOP.

The Writer is the single entry-point for persisting new memory. It compares
each incoming Fragment against the existing store and classifies the write:

  ADD      — no match found; insert new fragment.
  UPDATE   — same predicate exists with lower confidence; update content only.
  SUPERSEDE— contradiction detected; invalidate old, link new via supersedes[].
             Emits a ConflictEvent for the audit trail.
  DEDUPE   — near-duplicate (content similarity ≥ threshold); merge provenance,
             increment access_count, no new row.
  NOOP     — the fragment is already represented accurately; discard.

ConflictResolver decides between SUPERSEDE and NOOP when the incoming fragment
contradicts an existing one: if the new one is higher confidence or newer, we
SUPERSEDE; otherwise NOOP.

The Writer never deletes. Superseded fragments are kept with invalid_at set
so the audit chain is intact and historical queries remain possible.

Research grounding:
  - Mem0 four-way classifier (ADD/UPDATE/DELETE/NOOP) — we replace DELETE
    with SUPERSEDE to preserve history (design proposal §3.2).
  - Graphiti bi-temporal invalidation (§3.3).
  - Design proposal ConflictResolver flow (§3.3, §9 multi-agent conflict).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .schema import ConflictEvent, Fragment


# ---------------------------------------------------------------------------
# Write classification
# ---------------------------------------------------------------------------


class WriteAction(str, Enum):
    ADD = "add"
    UPDATE = "update"
    SUPERSEDE = "supersede"
    DEDUPE = "dedupe"
    NOOP = "noop"


@dataclass
class WriteResult:
    action: WriteAction
    fragment: Fragment
    conflict: ConflictEvent | None = None
    merged_into: str | None = None   # id of the surviving fragment on DEDUPE


# ---------------------------------------------------------------------------
# Similarity helpers (no heavy deps — pure Python)
# ---------------------------------------------------------------------------


def _token_set(text: str) -> set[str]:
    return {w.lower() for w in text.split() if len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _content_similarity(a: str, b: str) -> float:
    return _jaccard(_token_set(a), _token_set(b))


def _entity_overlap(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return _jaccard(sa, sb)


# ---------------------------------------------------------------------------
# ConflictResolver
# ---------------------------------------------------------------------------


class ConflictResolver:
    """Decides how a contradiction between two fragments is resolved.

    Rules (in order):
    1. If new fragment has higher confidence → SUPERSEDE (new wins).
    2. If new fragment comes from a different agent → agent_disagreement;
       SUPERSEDE with resolution="branch" (both kept valid until orchestrator
       resolves via memory.forget or memory.pin).
    3. If new fragment is from the same agent and lower confidence → NOOP.
    """

    SUPERSEDE_CONFIDENCE_DELTA = 0.05  # new must be this much higher to win

    def resolve(
        self,
        existing: Fragment,
        incoming: Fragment,
    ) -> tuple[WriteAction, ConflictEvent | None]:
        same_agent = (
            existing.provenance.agent_id == incoming.provenance.agent_id
        )
        confidence_gain = incoming.confidence - existing.confidence

        if not same_agent:
            # Different agents disagree → branch; both stay valid until human/orchestrator resolves
            ev = ConflictEvent.make(
                existing.id,
                incoming.id,
                reason="agent_disagreement",
                resolution="branch",
            )
            return WriteAction.SUPERSEDE, ev

        if confidence_gain >= self.SUPERSEDE_CONFIDENCE_DELTA:
            ev = ConflictEvent.make(
                existing.id,
                incoming.id,
                reason="contradiction",
                resolution="supersede",
            )
            return WriteAction.SUPERSEDE, ev

        # Same agent, lower or equal confidence → incoming is noisier; discard
        return WriteAction.NOOP, None


# ---------------------------------------------------------------------------
# In-memory fragment store (used by Writer; real backends plug in via Protocol)
# ---------------------------------------------------------------------------


class FragmentStore:
    """Minimal in-memory store — the reference backend for Writer.

    Keys: fragment id → Fragment.
    Active index: only non-invalidated fragments.
    """

    def __init__(self) -> None:
        self._all: dict[str, Fragment] = {}

    def put(self, fragment: Fragment) -> None:
        self._all[fragment.id] = fragment

    def get(self, fid: str) -> Fragment | None:
        return self._all.get(fid)

    def active(self) -> list[Fragment]:
        return [f for f in self._all.values() if f.is_valid]

    def all_fragments(self) -> list[Fragment]:
        return list(self._all.values())

    def __len__(self) -> int:
        return len(self._all)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


class Writer:
    """Routes each incoming Fragment to the correct write action.

    Parameters
    ----------
    store:
        A FragmentStore (or compatible Protocol) to read/write from.
    dedupe_threshold:
        Jaccard similarity above which two fragments are considered duplicates.
    conflict_resolver:
        Strategy for resolving contradictions; defaults to ConflictResolver().
    """

    def __init__(
        self,
        store: FragmentStore | None = None,
        dedupe_threshold: float = 0.85,
        conflict_resolver: ConflictResolver | None = None,
    ) -> None:
        self._store = store or FragmentStore()
        self._dedupe_threshold = dedupe_threshold
        self._resolver = conflict_resolver or ConflictResolver()
        self._conflict_log: list[ConflictEvent] = []

    @property
    def store(self) -> FragmentStore:
        return self._store

    @property
    def conflicts(self) -> list[ConflictEvent]:
        return list(self._conflict_log)

    def write(self, incoming: Fragment) -> WriteResult:
        """Classify and persist an incoming fragment. Returns the WriteResult."""
        active = self._store.active()

        # ── Step 1: check for near-duplicates ─────────────────────────────
        for existing in active:
            if existing.type is not incoming.type:
                continue
            sim = _content_similarity(existing.content, incoming.content)
            if sim >= self._dedupe_threshold:
                # Merge provenance (add incoming's agent to existing's tool_calls)
                existing.access_count += 1
                existing.provenance.tool_calls.extend(
                    t for t in incoming.provenance.tool_calls
                    if t not in existing.provenance.tool_calls
                )
                return WriteResult(
                    action=WriteAction.DEDUPE,
                    fragment=existing,
                    merged_into=existing.id,
                )

        # ── Step 2: check for contradiction (same type + entity overlap) ──
        for existing in active:
            if existing.type is not incoming.type:
                continue
            if existing.tier is not incoming.tier:
                continue
            entity_sim = _entity_overlap(existing.entities, incoming.entities)
            content_sim = _content_similarity(existing.content, incoming.content)

            # Contradiction: shared entities on the same topic + diverging content
            if entity_sim >= 0.3 and content_sim < self._dedupe_threshold:
                action, conflict = self._resolver.resolve(existing, incoming)
                if action is WriteAction.SUPERSEDE:
                    return self._do_supersede(existing, incoming, conflict)
                return WriteResult(action=WriteAction.NOOP, fragment=existing)

        # ── Step 3: check for UPDATE (same content key, higher confidence) ─
        for existing in active:
            if existing.type is not incoming.type:
                continue
            content_sim = _content_similarity(existing.content, incoming.content)
            if content_sim >= 0.6 and incoming.confidence > existing.confidence:
                existing.content = incoming.content
                existing.confidence = incoming.confidence
                existing.entities = incoming.entities or existing.entities
                existing.structured.update(incoming.structured)
                return WriteResult(action=WriteAction.UPDATE, fragment=existing)

        # ── Step 4: ADD ────────────────────────────────────────────────────
        self._store.put(incoming)
        return WriteResult(action=WriteAction.ADD, fragment=incoming)

    def _do_supersede(
        self,
        existing: Fragment,
        incoming: Fragment,
        conflict: ConflictEvent | None,
    ) -> WriteResult:
        existing.invalidate()
        incoming.supersedes.append(existing.id)

        # For agent_disagreement / branch: keep existing valid too (both stored)
        if conflict and conflict.resolution == "branch":
            existing.invalid_at = None  # revert invalidation — both survive

        self._store.put(incoming)
        if conflict:
            self._conflict_log.append(conflict)
        return WriteResult(
            action=WriteAction.SUPERSEDE,
            fragment=incoming,
            conflict=conflict,
        )
