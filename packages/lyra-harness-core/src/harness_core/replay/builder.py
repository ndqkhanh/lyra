"""TraceBuilder — consume from witnesses + trajectories + decisions; emit Trace.

The builder reads from the canonical sources:
    - :class:`harness_core.provenance.WitnessLattice` — witnesses become events
      preserving kind + issuer + timestamp + content + parents.
    - :class:`harness_core.forensic.Trajectory` — agent decisions become
      AGENT_DECISION events; side-effect records become TOOL_CALL events.

Add custom events directly via :meth:`TraceBuilder.add_event` for sources not
yet covered (PAGE_EDIT from pages.PageHistory, ROUTINE_FIRE from
RoutineRegistry, etc.).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..forensic import Trajectory
from ..orchestration import AgentDecision, SideEffectRecord
from ..provenance import ProvenanceLedger, Witness, WitnessKind
from .types import ReplayEvent, ReplayEventKind, Trace


_WITNESS_TO_EVENT_KIND: dict[WitnessKind, ReplayEventKind] = {
    WitnessKind.AGENT_DECISION: ReplayEventKind.AGENT_DECISION,
    WitnessKind.TOOL_RESULT: ReplayEventKind.TOOL_CALL,
    WitnessKind.VERIFIER_VERDICT: ReplayEventKind.VERIFIER_VERDICT,
    WitnessKind.HUMAN_APPROVAL: ReplayEventKind.HUMAN_APPROVAL,
    WitnessKind.RETRIEVAL: ReplayEventKind.RETRIEVAL,
    WitnessKind.INFERENCE: ReplayEventKind.INFERENCE,
    WitnessKind.ROUTINE_FIRE: ReplayEventKind.ROUTINE_FIRE,
    WitnessKind.PAGE_EDIT: ReplayEventKind.PAGE_EDIT,
    WitnessKind.CUSTOM: ReplayEventKind.CUSTOM,
}


@dataclass
class TraceBuilder:
    """Build a :class:`Trace` from harness_core data sources.

    >>> from harness_core.provenance import WitnessLattice
    >>> lattice = WitnessLattice()
    >>> w = lattice.record_retrieval(
    ...     retriever_name="hipporag", query="X", doc_ids=["d1"],
    ... )
    >>> builder = TraceBuilder(trace_id="incident-2026-05-09")
    >>> builder.add_witnesses_from(lattice.ledger)
    >>> trace = builder.build()
    >>> trace.events[0].kind
    <ReplayEventKind.RETRIEVAL: 'retrieval'>
    """

    trace_id: str
    _events: list[ReplayEvent] = field(default_factory=list)

    def add_witnesses_from(self, ledger: ProvenanceLedger) -> int:
        """Convert all witnesses in the ledger to events. Returns count added."""
        n = 0
        for w in ledger.witnesses_for():
            self._events.append(self._witness_to_event(w))
            n += 1
        return n

    def add_trajectory(self, trajectory: Trajectory, *, base_timestamp: float = 0.0) -> int:
        """Convert a Trajectory's decisions + side-effects to events.

        Each decision gets a synthetic timestamp ``base_timestamp + i``;
        each side-effect uses its recorded ``timestamp`` directly. Decisions
        are issued_by the trajectory_id; side-effects by ``trajectory.trajectory_id``
        with the tool_name in the payload.

        Returns count of events added.
        """
        n = 0
        for i, d in enumerate(trajectory.decisions):
            self._events.append(self._decision_to_event(
                decision=d,
                trajectory_id=trajectory.trajectory_id,
                fallback_ts=base_timestamp + i,
            ))
            n += 1
        for r in trajectory.side_effects:
            self._events.append(self._side_effect_to_event(
                record=r,
                trajectory_id=trajectory.trajectory_id,
            ))
            n += 1
        return n

    def add_event(
        self,
        *,
        kind: ReplayEventKind,
        issued_by: str,
        timestamp: float,
        payload: Optional[dict[str, Any]] = None,
        parent_event_ids: tuple[str, ...] = (),
        namespace_id: str = "",
        event_id: Optional[str] = None,
    ) -> ReplayEvent:
        """Add a custom event (PAGE_EDIT, ROUTINE_FIRE, etc.)."""
        eid = event_id or str(uuid.uuid4())
        event = ReplayEvent(
            event_id=eid,
            kind=kind,
            timestamp=timestamp,
            issued_by=issued_by,
            payload=payload or {},
            parent_event_ids=parent_event_ids,
            namespace_id=namespace_id,
        )
        self._events.append(event)
        return event

    def build(self) -> Trace:
        """Emit the final :class:`Trace` (events sorted by timestamp)."""
        return Trace.create(trace_id=self.trace_id, events=list(self._events))

    @staticmethod
    def _witness_to_event(w: Witness) -> ReplayEvent:
        kind = _WITNESS_TO_EVENT_KIND.get(w.kind, ReplayEventKind.CUSTOM)
        return ReplayEvent(
            event_id=w.witness_id,
            kind=kind,
            timestamp=w.issued_at,
            issued_by=w.issued_by,
            payload=dict(w.content),
            parent_event_ids=w.parent_witnesses,
        )

    @staticmethod
    def _decision_to_event(
        *,
        decision: AgentDecision,
        trajectory_id: str,
        fallback_ts: float,
    ) -> ReplayEvent:
        return ReplayEvent(
            event_id=decision.fingerprint or f"{trajectory_id}-d-{fallback_ts}",
            kind=ReplayEventKind.AGENT_DECISION,
            timestamp=fallback_ts,
            issued_by=trajectory_id,
            payload={"action": decision.action, **dict(decision.payload)},
        )

    @staticmethod
    def _side_effect_to_event(
        *,
        record: SideEffectRecord,
        trajectory_id: str,
    ) -> ReplayEvent:
        return ReplayEvent(
            event_id=record.call_id,
            kind=ReplayEventKind.TOOL_CALL,
            timestamp=record.timestamp,
            issued_by=trajectory_id,
            payload={
                "tool_name": record.tool_name,
                "args": dict(record.args),
                "result": record.result,
                "is_replayable": record.is_replayable,
            },
        )


__all__ = ["TraceBuilder"]
