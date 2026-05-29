"""Tests for HITL callback integration between ClosedLoopController and FleetView."""

from __future__ import annotations

from lyra_core.transparency.agent_view import AttentionPriority, FleetView
from lyra_evolution.controller import ClosedLoopController
from lyra_evolution.integration import create_hitl_callback


def test_hitl_callback_escalates_priority() -> None:
    fleet = FleetView()
    fleet.register("sess-1", summary="Running task", priority=AttentionPriority.P3)

    callback = create_hitl_callback(fleet, AttentionPriority.P0)
    controller = ClosedLoopController("sess-1", "run-1", hitl_callback=callback)

    # Trigger HITL pending
    rec, halt = controller.on_turn(
        turn_index=0, hitl_pending=True, fleet_alert="Manual approval needed"
    )

    # Check FleetView was updated
    agent = fleet.peek("sess-1")
    assert agent is not None
    assert agent.attention_priority == AttentionPriority.P0
    assert agent.state == "waiting"
    assert "HITL pending" in agent.row_summary
    assert "turn 0" in agent.row_summary
    assert "Manual approval needed" in agent.row_summary


def test_hitl_callback_not_triggered_when_not_pending() -> None:
    fleet = FleetView()
    fleet.register("sess-1", summary="Running task", priority=AttentionPriority.P3)

    callback = create_hitl_callback(fleet, AttentionPriority.P0)
    controller = ClosedLoopController("sess-1", "run-1", hitl_callback=callback)

    # Normal turn without HITL
    rec, halt = controller.on_turn(turn_index=0, hitl_pending=False)

    # Priority should remain unchanged
    agent = fleet.peek("sess-1")
    assert agent is not None
    assert agent.attention_priority == AttentionPriority.P3
    assert agent.state == "running"
    assert agent.row_summary == "Running task"


def test_hitl_callback_handles_missing_agent() -> None:
    fleet = FleetView()
    # Don't register the agent

    callback = create_hitl_callback(fleet, AttentionPriority.P0)
    controller = ClosedLoopController("sess-1", "run-1", hitl_callback=callback)

    # Should not crash when agent is not registered
    rec, halt = controller.on_turn(turn_index=0, hitl_pending=True)
    assert rec.hitl_pending is True


def test_controller_without_callback() -> None:
    # Controller should work fine without a callback
    controller = ClosedLoopController("sess-1", "run-1")

    rec, halt = controller.on_turn(turn_index=0, hitl_pending=True)
    assert rec.hitl_pending is True
    assert halt is None


def test_hitl_callback_with_default_reason() -> None:
    fleet = FleetView()
    fleet.register("sess-1", summary="Running task", priority=AttentionPriority.P3)

    callback = create_hitl_callback(fleet, AttentionPriority.P1)
    controller = ClosedLoopController("sess-1", "run-1", hitl_callback=callback)

    # HITL pending without explicit fleet_alert
    rec, halt = controller.on_turn(turn_index=5, hitl_pending=True)

    agent = fleet.peek("sess-1")
    assert agent is not None
    assert agent.attention_priority == AttentionPriority.P1
    assert "HITL pending" in agent.row_summary
    assert "turn 5" in agent.row_summary
    assert "HITL approval required" in agent.row_summary


def test_multiple_hitl_escalations() -> None:
    fleet = FleetView()
    fleet.register("sess-1", summary="Running task", priority=AttentionPriority.P3)

    callback = create_hitl_callback(fleet, AttentionPriority.P0)
    controller = ClosedLoopController("sess-1", "run-1", hitl_callback=callback)

    # First HITL
    controller.on_turn(turn_index=0, hitl_pending=True, fleet_alert="First approval")
    agent = fleet.peek("sess-1")
    assert agent is not None
    assert "turn 0" in agent.row_summary
    assert "First approval" in agent.row_summary

    # Second HITL
    controller.on_turn(turn_index=3, hitl_pending=True, fleet_alert="Second approval")
    agent = fleet.peek("sess-1")
    assert agent is not None
    assert "turn 3" in agent.row_summary
    assert "Second approval" in agent.row_summary
