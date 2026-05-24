"""TraceComparator — compute structural delta between two traces.

Used for:
    - **Sabotage detection** (Orion-Code [docs/220] §4.9, Cipher-Sec) — flag
      a current trace that diverges from past similar traces.
    - **Incident replay validation** (Aegis-Ops [docs/221] §3.5) — confirm a
      replayed trace matches the recorded one.
    - **Regression detection** (Polaris/Helix) — detect when a research
      pipeline's trace pattern shifts between releases.

The delta types capture the canonical differences:
    - ``EVENT_ADDED`` — present in B, absent in A.
    - ``EVENT_REMOVED`` — present in A, absent in B.
    - ``EVENT_KIND_DIVERGED`` — same event_id, different kind (rare).
    - ``ORDER_DIVERGED`` — same kinds + ids but in different order.
    - ``PAYLOAD_DIVERGED`` — same event_id, different payload content.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

from .types import ReplayEvent, Trace


class TraceDeltaKind(str, enum.Enum):
    EVENT_ADDED = "event_added"  # in target, not in reference
    EVENT_REMOVED = "event_removed"  # in reference, not in target
    EVENT_KIND_DIVERGED = "event_kind_diverged"
    ORDER_DIVERGED = "order_diverged"
    PAYLOAD_DIVERGED = "payload_diverged"


@dataclass(frozen=True)
class TraceDelta:
    """One difference between two traces."""

    kind: TraceDeltaKind
    event_id: str = ""
    reference_event: Optional[ReplayEvent] = None
    target_event: Optional[ReplayEvent] = None
    note: str = ""


@dataclass
class TraceComparator:
    """Compute :class:`TraceDelta` records between a reference and target.

    Ignores timestamp differences by default — two traces are "structurally
    equivalent" if they have the same events in the same order, regardless of
    wall-clock timing. Set ``check_timestamps=True`` to flag time differences.

    >>> from harness_core.replay import TraceBuilder, ReplayEventKind
    >>> ref = TraceBuilder(trace_id="ref")
    >>> ref.add_event(kind=ReplayEventKind.RETRIEVAL, issued_by="r",
    ...                timestamp=1.0, event_id="e1")
    >>> ref.add_event(kind=ReplayEventKind.AGENT_DECISION, issued_by="a",
    ...                timestamp=2.0, event_id="e2")
    >>> ref_trace = ref.build()
    >>> tgt = TraceBuilder(trace_id="tgt")
    >>> tgt.add_event(kind=ReplayEventKind.RETRIEVAL, issued_by="r",
    ...                timestamp=1.0, event_id="e1")
    >>> tgt.add_event(kind=ReplayEventKind.AGENT_DECISION, issued_by="a",
    ...                timestamp=2.0, event_id="e2")
    >>> deltas = TraceComparator().compare(reference=ref_trace, target=tgt.build())
    >>> deltas
    []
    """

    check_payloads: bool = True
    check_timestamps: bool = False

    def compare(
        self,
        *,
        reference: Trace,
        target: Trace,
    ) -> list[TraceDelta]:
        """Compute deltas: what changed from reference to target."""
        deltas: list[TraceDelta] = []
        ref_ids = reference.event_ids()
        tgt_ids = target.event_ids()

        # Removed: in reference but not in target.
        for ref_event in reference.events:
            if ref_event.event_id not in tgt_ids:
                deltas.append(TraceDelta(
                    kind=TraceDeltaKind.EVENT_REMOVED,
                    event_id=ref_event.event_id,
                    reference_event=ref_event,
                    note=f"{ref_event.kind.value} event missing in target",
                ))

        # Added: in target but not in reference.
        for tgt_event in target.events:
            if tgt_event.event_id not in ref_ids:
                deltas.append(TraceDelta(
                    kind=TraceDeltaKind.EVENT_ADDED,
                    event_id=tgt_event.event_id,
                    target_event=tgt_event,
                    note=f"{tgt_event.kind.value} event added in target",
                ))

        # Per-event divergence (kind, payload) for shared event_ids.
        ref_by_id = {e.event_id: e for e in reference.events}
        tgt_by_id = {e.event_id: e for e in target.events}
        for eid in sorted(ref_ids & tgt_ids):
            ref_e = ref_by_id[eid]
            tgt_e = tgt_by_id[eid]
            if ref_e.kind != tgt_e.kind:
                deltas.append(TraceDelta(
                    kind=TraceDeltaKind.EVENT_KIND_DIVERGED,
                    event_id=eid,
                    reference_event=ref_e,
                    target_event=tgt_e,
                    note=f"kind: {ref_e.kind.value} → {tgt_e.kind.value}",
                ))
                continue  # don't bother checking payload if kinds differ
            if self.check_payloads and ref_e.payload != tgt_e.payload:
                deltas.append(TraceDelta(
                    kind=TraceDeltaKind.PAYLOAD_DIVERGED,
                    event_id=eid,
                    reference_event=ref_e,
                    target_event=tgt_e,
                    note="payload mismatch",
                ))
            if self.check_timestamps and ref_e.timestamp != tgt_e.timestamp:
                deltas.append(TraceDelta(
                    kind=TraceDeltaKind.PAYLOAD_DIVERGED,
                    event_id=eid,
                    reference_event=ref_e,
                    target_event=tgt_e,
                    note=f"timestamp mismatch: {ref_e.timestamp} → {tgt_e.timestamp}",
                ))

        # Order divergence: same set of event_ids, different sequence.
        if ref_ids == tgt_ids:
            ref_seq = [e.event_id for e in reference.events]
            tgt_seq = [e.event_id for e in target.events]
            if ref_seq != tgt_seq:
                # First mismatching index.
                first_diff = next(
                    (i for i, (a, b) in enumerate(zip(ref_seq, tgt_seq)) if a != b),
                    -1,
                )
                deltas.append(TraceDelta(
                    kind=TraceDeltaKind.ORDER_DIVERGED,
                    event_id="",
                    note=f"event order differs at index {first_diff}",
                ))

        return deltas

    def is_equivalent(
        self,
        *,
        reference: Trace,
        target: Trace,
    ) -> bool:
        """Convenience: True if no deltas."""
        return len(self.compare(reference=reference, target=target)) == 0

    def summarize(
        self,
        *,
        reference: Trace,
        target: Trace,
    ) -> dict[str, int]:
        """Counts of each delta kind."""
        deltas = self.compare(reference=reference, target=target)
        c = {k.value: 0 for k in TraceDeltaKind}
        c["total"] = len(deltas)
        for d in deltas:
            c[d.kind.value] += 1
        return c


__all__ = ["TraceComparator", "TraceDelta", "TraceDeltaKind"]
