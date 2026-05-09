"""Tests for v3.11 LifecycleEvent additions (team.* / confidence.* / bundle.*)."""
from __future__ import annotations

from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent


def test_v311_team_events_present():
    names = {e.value for e in LifecycleEvent}
    expected = {
        "team.create", "team.spawn", "team.task_created",
        "team.task_completed", "team.task_failed",
        "team.teammate_idle", "team.shutdown",
    }
    assert expected <= names


def test_v311_confidence_events_present():
    names = {e.value for e in LifecycleEvent}
    assert {"confidence.promote", "confidence.demote"} <= names


def test_v311_bundle_events_present():
    names = {e.value for e in LifecycleEvent}
    expected = {
        "bundle.provision", "bundle.register_skills",
        "bundle.wire_tools", "bundle.smoke_eval", "bundle.attest",
    }
    assert expected <= names


def test_team_event_dispatches_through_bus():
    captured: list = []
    bus = LifecycleBus()
    bus.subscribe(LifecycleEvent.TEAM_TASK_COMPLETED, captured.append)
    bus.emit(LifecycleEvent.TEAM_TASK_COMPLETED, {"team": "auth", "task_id": "001"})
    assert len(captured) == 1
    assert captured[0]["team"] == "auth"


def test_legacy_events_still_present():
    """Make sure v3.11 additions did not remove any pre-existing events."""
    names = {e.value for e in LifecycleEvent}
    legacy = {
        "session_start", "turn_start", "skills_activated",
        "turn_complete", "turn_rejected", "tool_call", "session_end",
    }
    assert legacy <= names
