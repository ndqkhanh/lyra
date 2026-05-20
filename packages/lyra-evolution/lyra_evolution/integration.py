"""Integration helpers for wiring ClosedLoopController to FleetView.

Provides callback factories that connect HITL interrupts from the controller
to FleetView priority escalation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lyra_core.transparency.agent_view import AttentionPriority, FleetView
    from lyra_evolution.controller import HITLCallback


__all__ = [
    "create_hitl_callback",
]


def create_hitl_callback(
    fleet_view: "FleetView",
    priority: "AttentionPriority",
) -> "HITLCallback":
    """Create a callback that escalates agent priority when HITL is pending.

    Usage::

        from lyra_core.transparency.agent_view import AttentionPriority, FleetView
        from lyra_evolution.controller import ClosedLoopController
        from lyra_evolution.integration import create_hitl_callback

        fleet = FleetView()
        fleet.register("sess-1", summary="Running task")

        callback = create_hitl_callback(fleet, AttentionPriority.P0)
        controller = ClosedLoopController("sess-1", "run-1", hitl_callback=callback)

        # When HITL is pending, the callback will escalate priority to P0
        rec, halt = controller.on_turn(turn_index=0, hitl_pending=True)
    """

    def callback(session_id: str, turn_index: int, reason: str) -> None:
        """Escalate agent priority and update summary with HITL reason."""
        agent = fleet_view.peek(session_id)
        if agent is None:
            return

        fleet_view.set_priority(session_id, priority)
        fleet_view.set_state(session_id, "waiting")
        summary = f"HITL pending (turn {turn_index}): {reason}"
        fleet_view.set_summary(session_id, summary)

    return callback
