"""ReplayEvent + Trace — typed unified event sequence."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class ReplayEventKind(str, enum.Enum):
    """The typed kinds of replay events.

    Mirrors :class:`harness_core.provenance.WitnessKind` plus a few execution-
    side events not in the witness lattice (TOOL_CALL, ROUTINE_FIRE).
    """

    AGENT_DECISION = "agent_decision"
    TOOL_CALL = "tool_call"
    VERIFIER_VERDICT = "verifier_verdict"
    RETRIEVAL = "retrieval"
    PAGE_EDIT = "page_edit"
    ROUTINE_FIRE = "routine_fire"
    HUMAN_APPROVAL = "human_approval"
    SKILL_PROMOTION = "skill_promotion"
    INFERENCE = "inference"
    CUSTOM = "custom"


@dataclass(frozen=True)
class ReplayEvent:
    """One event in a trace — typed kind + timestamped payload.

    ``parent_event_ids`` records causal predecessors (the same parent-chain
    structure as :class:`harness_core.provenance.Witness`).
    """

    event_id: str
    kind: ReplayEventKind
    timestamp: float
    issued_by: str  # agent or user id
    payload: dict[str, Any] = field(default_factory=dict)
    parent_event_ids: tuple[str, ...] = ()
    namespace_id: str = ""  # IsolatedContext namespace, if applicable

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.issued_by:
            raise ValueError("issued_by must be non-empty")
        if self.timestamp < 0:
            raise ValueError(f"timestamp must be >= 0, got {self.timestamp}")


@dataclass(frozen=True)
class Trace:
    """A complete trace — ordered ReplayEvents from one logical run.

    Events are sorted by ``timestamp`` ascending. Order is stable: events at
    the same timestamp retain insertion order.

    >>> t = Trace.create(trace_id="t1", events=[
    ...     ReplayEvent(event_id="e1", kind=ReplayEventKind.RETRIEVAL,
    ...                  timestamp=2.0, issued_by="r"),
    ...     ReplayEvent(event_id="e2", kind=ReplayEventKind.AGENT_DECISION,
    ...                  timestamp=1.0, issued_by="a"),
    ... ])
    >>> [e.event_id for e in t.events]
    ['e2', 'e1']
    """

    trace_id: str
    events: tuple[ReplayEvent, ...] = ()

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise ValueError("trace_id must be non-empty")

    @classmethod
    def create(cls, *, trace_id: str, events: list[ReplayEvent]) -> "Trace":
        """Construct a Trace with events sorted by timestamp ascending."""
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        return cls(trace_id=trace_id, events=tuple(sorted_events))

    def by_kind(self, kind: ReplayEventKind) -> list[ReplayEvent]:
        return [e for e in self.events if e.kind == kind]

    def for_namespace(self, namespace_id: str) -> list[ReplayEvent]:
        return [e for e in self.events if e.namespace_id == namespace_id]

    def for_issuer(self, issued_by: str) -> list[ReplayEvent]:
        return [e for e in self.events if e.issued_by == issued_by]

    def in_window(self, *, start: float, end: float) -> list[ReplayEvent]:
        return [e for e in self.events if start <= e.timestamp <= end]

    def event_kinds(self) -> tuple[ReplayEventKind, ...]:
        return tuple(e.kind for e in self.events)

    def event_ids(self) -> frozenset[str]:
        return frozenset(e.event_id for e in self.events)

    def stats(self) -> dict[str, int]:
        c = {k.value: 0 for k in ReplayEventKind}
        issuers: set[str] = set()
        namespaces: set[str] = set()
        for e in self.events:
            c[e.kind.value] += 1
            issuers.add(e.issued_by)
            if e.namespace_id:
                namespaces.add(e.namespace_id)
        c["total"] = len(self.events)
        c["issuers"] = len(issuers)
        c["namespaces"] = len(namespaces)
        return c


__all__ = ["ReplayEvent", "ReplayEventKind", "Trace"]
