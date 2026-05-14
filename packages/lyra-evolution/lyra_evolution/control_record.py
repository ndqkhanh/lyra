"""ControlRecord — 8-timescale closed-loop state — Phase E.

One ControlRecord is produced per agent turn and captures the control
signal at each of the 8 timescales defined in Doc 326 §3, from token-level
retry up to fleet-level SRE alert.  The record is stored alongside its
corresponding AER span so Phase E Reflexion can replay and critique the
full control loop.

Grounded in:
- Doc 326 §3 — 8-timescale closed-loop controller
- ATLAS-RTC (token-level adaptive temperature control)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


__all__ = ["ControlRecord", "new_control_record"]


@dataclass
class ControlRecord:
    """Control state across all 8 timescales for one agent turn."""

    # Identity — links to the AER for Reflexion replay
    session_id: str
    run_id: str
    turn_index: int
    aer_span_id: str = ""

    # Timescale 1 — token level (ATLAS-RTC adaptive temperature)
    token_temperature: float = 1.0
    token_retry_count: int = 0

    # Timescale 2 — step level (tool retry on transient failure)
    step_tool_retries: int = 0
    step_last_tool: str = ""

    # Timescale 3 — turn level (evaluator-refine loop score)
    turn_eval_score: float = 0.0
    turn_refinements: int = 0

    # Timescale 4 — episode level (Reflexion lesson)
    episode_lesson: str = ""
    episode_lesson_applied: bool = False

    # Timescale 5 — skill level (Voyager verified-skill gate)
    skill_name: str = ""
    skill_verified: bool = False

    # Timescale 6 — runtime level (checkpoint path)
    checkpoint_path: str = ""
    checkpoint_restored: bool = False

    # Timescale 7 — operator level (HITL approval pending)
    hitl_pending: bool = False
    hitl_decision: str = ""

    # Timescale 8 — fleet level (Agent View SRE alert)
    fleet_sre_alert: str = ""

    # Housekeeping
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def new_control_record(
    session_id: str,
    run_id: str,
    turn_index: int,
    aer_span_id: str = "",
) -> ControlRecord:
    """Factory — create a blank ControlRecord for a new turn."""
    return ControlRecord(
        session_id=session_id,
        run_id=run_id,
        turn_index=turn_index,
        aer_span_id=aer_span_id,
    )
