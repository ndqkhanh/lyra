"""Incident response engine for Lyra safety governance.

Implements automated incident classification, severity assessment,
playbook-driven response actions, and post-incident review workflows.
Integrates with ForensicCollector for trace capture and AuditEngine
for cryptographic audit trails.

Architecture:
    - IncidentSeverity: 5-level severity classification
    - IncidentRecord: frozen dataclass for immutable incident tracking
    - Playbook: predefined response procedures per incident type
    - IncidentResponse: main engine coordinating detection → response
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

from .forensic_collector import ForensicCollector, IncidentCategory


class IncidentSeverity(StrEnum):
    """Severity levels for incident classification."""

    CRITICAL = "critical"    # immediate system halt required
    HIGH = "high"            # active threat, rapid response needed
    MEDIUM = "medium"        # concerning, investigation warranted
    LOW = "low"              # minor anomaly, log and monitor
    INFO = "info"            # informational, no action needed


class PlaybookAction(StrEnum):
    """Actions available in incident response playbooks."""

    BLOCK_TOOL = "block_tool"
    REVOKE_PERMISSION = "revoke_permission"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    TERMINATE_SESSION = "terminate_session"
    QUARANTINE_OUTPUT = "quarantine_output"
    ROTATE_CREDENTIALS = "rotate_credentials"
    NOTIFY_ONCALL = "notify_oncall"
    LOG_AND_CONTINUE = "log_and_continue"
    THROTTLE_RATE = "throttle_rate"
    SNAPSHOT_STATE = "snapshot_state"


@dataclass(frozen=True)
class Playbook:
    """Predefined response playbook for an incident category.

    Attributes:
        playbook_id: unique identifier for the playbook
        category: which incident category this playbook handles
        name: human-readable name
        actions: ordered list of response actions
        auto_actions: actions executed automatically (no human approval)
        cooldown_sec: minimum time between playbook activations
        escalation_threshold: severity at which to escalate
    """

    playbook_id: str
    category: IncidentCategory
    name: str
    actions: list[PlaybookAction]
    auto_actions: list[PlaybookAction]
    cooldown_sec: float
    escalation_threshold: IncidentSeverity


@dataclass(frozen=True)
class IncidentRecord:
    """Immutable record of a safety incident and its response.

    Attributes:
        incident_id: unique identifier
        category: incident classification
        severity: assessed severity level
        description: human-readable description
        playbook_id: the playbook activated (if any)
        actions_taken: actions that were executed
        forensic_snapshot_id: link to forensic trace
        created_at: when the incident was detected
        resolved_at: when the incident was resolved (if resolved)
        auto_resolved: whether the system resolved this automatically
    """

    incident_id: str
    category: IncidentCategory
    severity: IncidentSeverity
    description: str
    playbook_id: str | None
    actions_taken: list[PlaybookAction]
    forensic_snapshot_id: str | None
    created_at: float
    resolved_at: float | None
    auto_resolved: bool

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None

    @property
    def response_time_sec(self) -> float | None:
        if self.resolved_at is None:
            return None
        return self.resolved_at - self.created_at


DEFAULT_PLAYBOOKS: list[Playbook] = [
    Playbook(
        playbook_id="pb-prompt-injection",
        category=IncidentCategory.PROMPT_INJECTION,
        name="Prompt Injection Response",
        actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.QUARANTINE_OUTPUT,
            PlaybookAction.SNAPSHOT_STATE,
            PlaybookAction.TERMINATE_SESSION,
            PlaybookAction.NOTIFY_ONCALL,
        ],
        auto_actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.QUARANTINE_OUTPUT,
            PlaybookAction.SNAPSHOT_STATE,
        ],
        cooldown_sec=60.0,
        escalation_threshold=IncidentSeverity.HIGH,
    ),
    Playbook(
        playbook_id="pb-credential-exposure",
        category=IncidentCategory.CREDENTIAL_EXPOSURE,
        name="Credential Exposure Response",
        actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.ROTATE_CREDENTIALS,
            PlaybookAction.REVOKE_PERMISSION,
            PlaybookAction.SNAPSHOT_STATE,
            PlaybookAction.NOTIFY_ONCALL,
        ],
        auto_actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.ROTATE_CREDENTIALS,
            PlaybookAction.SNAPSHOT_STATE,
        ],
        cooldown_sec=30.0,
        escalation_threshold=IncidentSeverity.CRITICAL,
    ),
    Playbook(
        playbook_id="pb-destructive-op",
        category=IncidentCategory.DESTRUCTIVE_OPERATION,
        name="Destructive Operation Response",
        actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.TERMINATE_SESSION,
            PlaybookAction.REVOKE_PERMISSION,
            PlaybookAction.SNAPSHOT_STATE,
            PlaybookAction.NOTIFY_ONCALL,
        ],
        auto_actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.TERMINATE_SESSION,
            PlaybookAction.SNAPSHOT_STATE,
        ],
        cooldown_sec=30.0,
        escalation_threshold=IncidentSeverity.HIGH,
    ),
    Playbook(
        playbook_id="pb-tool-misuse",
        category=IncidentCategory.TOOL_MISUSE,
        name="Tool Misuse Response",
        actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.SNAPSHOT_STATE,
            PlaybookAction.THROTTLE_RATE,
            PlaybookAction.ESCALATE_TO_HUMAN,
        ],
        auto_actions=[
            PlaybookAction.BLOCK_TOOL,
            PlaybookAction.SNAPSHOT_STATE,
            PlaybookAction.THROTTLE_RATE,
        ],
        cooldown_sec=120.0,
        escalation_threshold=IncidentSeverity.MEDIUM,
    ),
    Playbook(
        playbook_id="pb-unknown",
        category=IncidentCategory.UNKNOWN,
        name="Unknown Incident Response",
        actions=[
            PlaybookAction.SNAPSHOT_STATE,
            PlaybookAction.LOG_AND_CONTINUE,
            PlaybookAction.ESCALATE_TO_HUMAN,
        ],
        auto_actions=[
            PlaybookAction.SNAPSHOT_STATE,
            PlaybookAction.LOG_AND_CONTINUE,
        ],
        cooldown_sec=300.0,
        escalation_threshold=IncidentSeverity.LOW,
    ),
]


class IncidentResponse:
    """Automated incident response engine.

    Coordinates detection, classification, playbook activation, and
    forensic trace collection. Executes auto-actions immediately and
    queues manual actions for human review.

    Usage::

        ir = IncidentResponse()
        incident = ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="Detected injection pattern in user input",
            forensic_collector=forensic_collector,
        )
        ir.resolve(incident.incident_id)
    """

    def __init__(self) -> None:
        self._playbooks: dict[IncidentCategory, Playbook] = {}
        self._incidents: list[IncidentRecord] = []
        self._incidents_by_id: dict[str, IncidentRecord] = {}
        self._last_activation: dict[str, float] = {}
        self._action_handlers: dict[PlaybookAction, Callable[[IncidentRecord], None]] = {}

        for pb in DEFAULT_PLAYBOOKS:
            self._playbooks[pb.category] = pb

    def register_playbook(self, playbook: Playbook) -> None:
        self._playbooks[playbook.category] = playbook

    def register_action_handler(
        self, action: PlaybookAction, handler: Callable[[IncidentRecord], None]
    ) -> None:
        self._action_handlers[action] = handler

    def declare(
        self,
        category: IncidentCategory,
        severity: IncidentSeverity,
        description: str,
        forensic_collector: ForensicCollector | None = None,
        forensic_snapshot_id: str | None = None,
    ) -> IncidentRecord:
        """Declare an incident and activate the appropriate playbook.

        Auto-actions are executed immediately. Manual actions are
        recorded for later review.
        """
        incident_id = hashlib.sha256(
            f"{category.value}|{severity.value}|{time.time()}".encode()
        ).hexdigest()[:20]

        if forensic_collector is not None and forensic_snapshot_id is None:
            snap = forensic_collector.capture(
                category=category, agent_id="system", session_id=incident_id,
                safety_flags=[severity.value],
            )
            forensic_snapshot_id = snap.snapshot_id

        playbook = self._playbooks.get(category)
        playbook_id = playbook.playbook_id if playbook else None
        actions_taken: list[PlaybookAction] = []

        if playbook is not None:
            now = time.time()
            last = self._last_activation.get(playbook.playbook_id, 0.0)
            if now - last >= playbook.cooldown_sec:
                self._last_activation[playbook.playbook_id] = now
                for action in playbook.auto_actions:
                    handler = self._action_handlers.get(action)
                    if handler is not None:
                        try:
                            handler(
                                IncidentRecord(
                                    incident_id=incident_id,
                                    category=category,
                                    severity=severity,
                                    description=description,
                                    playbook_id=playbook_id,
                                    actions_taken=actions_taken,
                                    forensic_snapshot_id=forensic_snapshot_id,
                                    created_at=now,
                                    resolved_at=None,
                                    auto_resolved=False,
                                )
                            )
                        except Exception:
                            pass
                actions_taken = list(playbook.auto_actions)

        record = IncidentRecord(
            incident_id=incident_id,
            category=category,
            severity=severity,
            description=description,
            playbook_id=playbook_id,
            actions_taken=actions_taken,
            forensic_snapshot_id=forensic_snapshot_id,
            created_at=time.time(),
            resolved_at=None,
            auto_resolved=len(actions_taken) > 0,
        )

        self._incidents.append(record)
        self._incidents_by_id[incident_id] = record
        return record

    def resolve(self, incident_id: str) -> IncidentRecord | None:
        """Mark an incident as resolved."""
        current = self._incidents_by_id.get(incident_id)
        if current is None:
            return None
        resolved = IncidentRecord(
            incident_id=current.incident_id,
            category=current.category,
            severity=current.severity,
            description=current.description,
            playbook_id=current.playbook_id,
            actions_taken=current.actions_taken,
            forensic_snapshot_id=current.forensic_snapshot_id,
            created_at=current.created_at,
            resolved_at=time.time(),
            auto_resolved=current.auto_resolved,
        )
        self._incidents_by_id[incident_id] = resolved
        self._incidents = [
            resolved if r.incident_id == incident_id else r
            for r in self._incidents
        ]
        return resolved

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        return self._incidents_by_id.get(incident_id)

    def get_active_incidents(self) -> list[IncidentRecord]:
        return [r for r in self._incidents if not r.is_resolved]

    def get_playbook(self, category: IncidentCategory) -> Playbook | None:
        return self._playbooks.get(category)

    def stats(self) -> dict[str, Any]:
        total = len(self._incidents)
        resolved = sum(1 for r in self._incidents if r.is_resolved)
        by_category: dict[str, int] = {}
        for r in self._incidents:
            key = r.category.value
            by_category[key] = by_category.get(key, 0) + 1
        return {
            "total_incidents": total,
            "active": total - resolved,
            "resolved": resolved,
            "by_category": by_category,
            "playbooks_configured": len(self._playbooks),
        }
