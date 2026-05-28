"""Tests for IncidentResponse — automated incident response engine."""

import time

import pytest

from lyra_core.safety.forensic_collector import ForensicCollector, IncidentCategory
from lyra_core.safety.incident_response import (
    DEFAULT_PLAYBOOKS,
    IncidentRecord,
    IncidentResponse,
    IncidentSeverity,
    Playbook,
    PlaybookAction,
)


class TestIncidentSeverity:
    def test_values(self):
        assert IncidentSeverity.CRITICAL.value == "critical"
        assert IncidentSeverity.HIGH.value == "high"
        assert IncidentSeverity.MEDIUM.value == "medium"
        assert IncidentSeverity.LOW.value == "low"
        assert IncidentSeverity.INFO.value == "info"


class TestPlaybookAction:
    def test_values(self):
        assert PlaybookAction.BLOCK_TOOL.value == "block_tool"
        assert PlaybookAction.ESCALATE_TO_HUMAN.value == "escalate_to_human"
        assert PlaybookAction.TERMINATE_SESSION.value == "terminate_session"


class TestPlaybook:
    def test_create(self):
        pb = Playbook(
            playbook_id="pb-test",
            category=IncidentCategory.TOOL_MISUSE,
            name="Test Playbook",
            actions=[PlaybookAction.BLOCK_TOOL, PlaybookAction.SNAPSHOT_STATE],
            auto_actions=[PlaybookAction.BLOCK_TOOL],
            cooldown_sec=60.0,
            escalation_threshold=IncidentSeverity.HIGH,
        )
        assert pb.playbook_id == "pb-test"
        assert len(pb.actions) == 2
        assert len(pb.auto_actions) == 1

    def test_immutable(self):
        pb = Playbook(
            playbook_id="pb-t", category=IncidentCategory.UNKNOWN,
            name="T", actions=[], auto_actions=[],
            cooldown_sec=1.0, escalation_threshold=IncidentSeverity.LOW,
        )
        with pytest.raises(Exception):
            pb.name = "hacked"  # type: ignore[misc]


class TestIncidentRecord:
    def test_create(self):
        record = IncidentRecord(
            incident_id="inc-001",
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="Test incident",
            playbook_id="pb-test",
            actions_taken=[PlaybookAction.BLOCK_TOOL],
            forensic_snapshot_id="snap-001",
            created_at=time.time(),
            resolved_at=None,
            auto_resolved=False,
        )
        assert record.incident_id == "inc-001"
        assert not record.is_resolved
        assert record.response_time_sec is None

    def test_resolved(self):
        ts = time.time()
        record = IncidentRecord(
            incident_id="inc-002",
            category=IncidentCategory.TOOL_MISUSE,
            severity=IncidentSeverity.MEDIUM,
            description="Resolved",
            playbook_id=None,
            actions_taken=[],
            forensic_snapshot_id=None,
            created_at=ts - 10,
            resolved_at=ts,
            auto_resolved=True,
        )
        assert record.is_resolved
        assert record.response_time_sec == pytest.approx(10.0, abs=1.0)

    def test_immutable(self):
        record = IncidentRecord(
            incident_id="i", category=IncidentCategory.UNKNOWN,
            severity=IncidentSeverity.INFO, description="d",
            playbook_id=None, actions_taken=[], forensic_snapshot_id=None,
            created_at=0.0, resolved_at=None, auto_resolved=False,
        )
        with pytest.raises(Exception):
            record.severity = IncidentSeverity.CRITICAL  # type: ignore[misc]


class TestIncidentResponse:
    def test_declare_incident(self):
        ir = IncidentResponse()
        incident = ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="Injection detected in user prompt",
        )
        assert incident.category == IncidentCategory.PROMPT_INJECTION
        assert incident.severity == IncidentSeverity.HIGH
        assert len(incident.incident_id) == 20

    def test_declare_triggers_playbook(self):
        ir = IncidentResponse()
        incident = ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="Test",
        )
        assert incident.playbook_id == "pb-prompt-injection"
        # Auto-actions should have been taken
        assert PlaybookAction.BLOCK_TOOL in incident.actions_taken
        assert PlaybookAction.QUARANTINE_OUTPUT in incident.actions_taken

    def test_declare_unknown_category_no_playbook(self):
        ir = IncidentResponse()
        # Unregister the UNKNOWN playbook
        ir = IncidentResponse.__new__(IncidentResponse)
        ir._playbooks = {}
        ir._incidents = []
        ir._incidents_by_id = {}
        ir._last_activation = {}
        ir._action_handlers = {}

        incident = ir.declare(
            category=IncidentCategory.UNKNOWN,
            severity=IncidentSeverity.LOW,
            description="Mystery incident",
        )
        assert incident.playbook_id is None
        assert incident.actions_taken == []

    def test_resolve_incident(self):
        ir = IncidentResponse()
        incident = ir.declare(
            category=IncidentCategory.TOOL_MISUSE,
            severity=IncidentSeverity.MEDIUM,
            description="Tool used unexpectedly",
        )
        assert not incident.is_resolved

        resolved = ir.resolve(incident.incident_id)
        assert resolved is not None
        assert resolved.is_resolved
        assert resolved.response_time_sec is not None
        assert resolved.response_time_sec >= 0

    def test_resolve_nonexistent(self):
        ir = IncidentResponse()
        assert ir.resolve("fake-id") is None

    def test_get_incident(self):
        ir = IncidentResponse()
        inc = ir.declare(
            category=IncidentCategory.DESTRUCTIVE_OPERATION,
            severity=IncidentSeverity.CRITICAL,
            description="rm -rf detected",
        )
        assert ir.get_incident(inc.incident_id) is not None

    def test_get_active_incidents(self):
        ir = IncidentResponse()
        ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="First",
        )
        inc2 = ir.declare(
            category=IncidentCategory.TOOL_MISUSE,
            severity=IncidentSeverity.MEDIUM,
            description="Second",
        )
        ir.resolve(inc2.incident_id)
        active = ir.get_active_incidents()
        assert len(active) == 1

    def test_get_playbook(self):
        ir = IncidentResponse()
        pb = ir.get_playbook(IncidentCategory.PROMPT_INJECTION)
        assert pb is not None
        assert pb.name == "Prompt Injection Response"

    def test_get_playbook_nonexistent(self):
        ir = IncidentResponse()
        # Category not in DEFAULT_PLAYBOOKS
        pb = ir.get_playbook(IncidentCategory.DATA_EXFILTRATION)
        assert pb is None

    def test_register_custom_playbook(self):
        ir = IncidentResponse()
        custom = Playbook(
            playbook_id="pb-custom",
            category=IncidentCategory.DATA_EXFILTRATION,
            name="Custom Data Exfil Response",
            actions=[PlaybookAction.LOG_AND_CONTINUE],
            auto_actions=[PlaybookAction.LOG_AND_CONTINUE],
            cooldown_sec=10.0,
            escalation_threshold=IncidentSeverity.MEDIUM,
        )
        ir.register_playbook(custom)
        pb = ir.get_playbook(IncidentCategory.DATA_EXFILTRATION)
        assert pb is not None
        assert pb.name == "Custom Data Exfil Response"

    def test_register_action_handler(self):
        ir = IncidentResponse()
        handled = []

        def handler(incident: IncidentRecord) -> None:
            handled.append(incident.incident_id)

        ir.register_action_handler(PlaybookAction.BLOCK_TOOL, handler)
        ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="Test with handler",
        )
        assert len(handled) >= 1

    def test_cooldown_respected(self):
        ir = IncidentResponse()
        # Override cooldown to a longer period for this test
        ir._playbooks[IncidentCategory.PROMPT_INJECTION] = Playbook(
            playbook_id="pb-prompt-injection",
            category=IncidentCategory.PROMPT_INJECTION,
            name="Prompt Injection Response",
            actions=[PlaybookAction.BLOCK_TOOL],
            auto_actions=[PlaybookAction.BLOCK_TOOL],
            cooldown_sec=999.0,
            escalation_threshold=IncidentSeverity.HIGH,
        )

        handled: list[str] = []

        def handler(incident: IncidentRecord) -> None:
            handled.append(incident.incident_id)

        ir.register_action_handler(PlaybookAction.BLOCK_TOOL, handler)

        ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="First",
        )
        assert len(handled) == 1

        ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="Second (should be on cooldown)",
        )
        assert len(handled) == 1  # cooldown blocked second activation

    def test_stats(self):
        ir = IncidentResponse()
        ir.declare(
            category=IncidentCategory.PROMPT_INJECTION,
            severity=IncidentSeverity.HIGH,
            description="Inc 1",
        )
        ir.declare(
            category=IncidentCategory.TOOL_MISUSE,
            severity=IncidentSeverity.MEDIUM,
            description="Inc 2",
        )
        stats = ir.stats()
        assert stats["total_incidents"] == 2
        assert stats["active"] == 2
        assert stats["resolved"] == 0
        assert stats["playbooks_configured"] == len(DEFAULT_PLAYBOOKS)


class TestDefaultPlaybooks:
    def test_all_critical_categories_covered(self):
        assert len(DEFAULT_PLAYBOOKS) >= 5

    def test_prompt_injection_has_auto_actions(self):
        pb = [p for p in DEFAULT_PLAYBOOKS if p.category == IncidentCategory.PROMPT_INJECTION][0]
        assert PlaybookAction.BLOCK_TOOL in pb.auto_actions
        assert PlaybookAction.SNAPSHOT_STATE in pb.auto_actions

    def test_credential_exposure_rotates(self):
        pb = [p for p in DEFAULT_PLAYBOOKS if p.category == IncidentCategory.CREDENTIAL_EXPOSURE][0]
        assert PlaybookAction.ROTATE_CREDENTIALS in pb.actions

    def test_destructive_operation_terminates(self):
        pb = [p for p in DEFAULT_PLAYBOOKS if p.category == IncidentCategory.DESTRUCTIVE_OPERATION][0]
        assert PlaybookAction.TERMINATE_SESSION in pb.auto_actions
