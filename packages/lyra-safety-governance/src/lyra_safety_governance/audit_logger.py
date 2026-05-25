from __future__ import annotations

import json
import uuid
from collections import Counter
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from .exceptions import AuditError
from .governance_engine import (
    ActionRequest,
    ActionType,
    Decision,
    GovernanceDecision,
    GovernanceLayer,
)


@dataclass(frozen=True)
class AuditEntry:
    entry_id: str
    timestamp: datetime
    decision: GovernanceDecision
    request: ActionRequest
    layer: GovernanceLayer
    agent_id: str
    details: str


@dataclass(frozen=True)
class AuditQuery:
    agent_id: str | None = None
    time_range: tuple[datetime, datetime] | None = None
    decision_type: Decision | None = None
    action_type: ActionType | None = None


@dataclass(frozen=True)
class AuditStats:
    total_entries: int = 0
    deny_rate: float = 0.0
    top_agents: tuple[tuple[str, int], ...] = ()
    top_actions: tuple[tuple[ActionType, int], ...] = ()
    recent_escalations: tuple[AuditEntry, ...] = ()


class AuditLogger:
    """Immutable audit trail for all governance decisions.

    This is an append-only log. Entries cannot be modified or deleted
    once recorded, ensuring a tamper-evident audit trail.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log_decision(self, decision: GovernanceDecision) -> str:
        """Record a governance decision in the audit log.

        Returns the entry_id for the newly created audit entry.
        """
        entry_id = f"audit-{uuid.uuid4().hex[:12]}"
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=datetime.now(timezone.utc),
            decision=decision,
            request=decision.action_request,
            layer=decision.layer,
            agent_id=decision.action_request.agent_id,
            details=(
                f"Decision: {decision.decision.value}, "
                f"Layer: {decision.layer.value}, "
                f"Risk: {decision.risk_score:.2f}, "
                f"Reason: {decision.reasoning}"
            ),
        )
        self._entries.append(entry)
        return entry_id

    def query_audit_log(self, query: AuditQuery) -> tuple[AuditEntry, ...]:
        """Query the audit log with optional filters."""
        results = list(self._entries)

        if query.agent_id is not None:
            results = [e for e in results if e.agent_id == query.agent_id]

        if query.time_range is not None:
            start, end = query.time_range
            results = [e for e in results if start <= e.timestamp <= end]

        if query.decision_type is not None:
            results = [e for e in results if e.decision.decision == query.decision_type]

        if query.action_type is not None:
            results = [e for e in results if e.request.action_type == query.action_type]

        return tuple(results)

    def get_agent_audit_trail(self, agent_id: str) -> tuple[AuditEntry, ...]:
        """Get the complete audit trail for a specific agent."""
        return tuple(e for e in self._entries if e.agent_id == agent_id)

    def compute_stats(self) -> AuditStats:
        """Compute summary statistics from the audit log."""
        if not self._entries:
            return AuditStats()

        total = len(self._entries)
        denied = sum(1 for e in self._entries if e.decision.decision == Decision.DENY)
        deny_rate = denied / max(total, 1)

        agent_counter: Counter[str] = Counter()
        action_counter: Counter[ActionType] = Counter()
        escalations: list[AuditEntry] = []

        for entry in self._entries:
            agent_counter[entry.agent_id] += 1
            action_counter[entry.request.action_type] += 1
            if entry.decision.decision in (Decision.ESCALATE, Decision.REQUIRE_HUMAN):
                escalations.append(entry)

        top_agents = tuple(agent_counter.most_common(5))
        top_actions = tuple(action_counter.most_common(5))

        recent_escalations = tuple(escalations[-10:])

        return AuditStats(
            total_entries=total,
            deny_rate=round(deny_rate, 4),
            top_agents=top_agents,
            top_actions=top_actions,
            recent_escalations=recent_escalations,
        )

    def export_audit_log(self, format: str = "json") -> str:
        """Export the audit log in the specified format.

        Currently supports 'json' format only.
        """
        if format != "json":
            raise AuditError(f"Unsupported export format: {format}")

        def _serialize(obj: object) -> object:
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, ActionRequest):
                return {
                    "request_id": obj.request_id,
                    "agent_id": obj.agent_id,
                    "action_type": obj.action_type.value,
                    "target": obj.target,
                    "parameters": obj.parameters,
                    "context": obj.context,
                }
            if isinstance(obj, GovernanceDecision):
                return {
                    "action_request": _serialize(obj.action_request),
                    "decision": obj.decision.value,
                    "layer": obj.layer.value,
                    "reasoning": obj.reasoning,
                    "risk_score": obj.risk_score,
                    "timestamp": obj.timestamp.isoformat(),
                }
            if isinstance(obj, AuditEntry):
                return {
                    "entry_id": obj.entry_id,
                    "timestamp": obj.timestamp.isoformat(),
                    "decision": _serialize(obj.decision),
                    "request": _serialize(obj.request),
                    "layer": obj.layer.value,
                    "agent_id": obj.agent_id,
                    "details": obj.details,
                }
            if hasattr(obj, "__dataclass_fields__"):
                return {f: _serialize(getattr(obj, f)) for f in obj.__dataclass_fields__}
            return str(obj)

        data = [_serialize(e) for e in self._entries]
        return json.dumps(data, indent=2, default=_serialize)
