"""Closed-loop controller — Phase E of the Lyra 322-326 evolution plan.

Integrates the 8-timescale control loop: on each agent turn it checks
stability budgets, records Reflexion lessons, and emits ControlRecords.
The controller is the central coordination point for self-evolution.

Grounded in:
- Doc 326 §3 — 8-timescale closed-loop controller
- Doc 326 §6 — Safety halt conditions
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .control_record import ControlRecord, new_control_record
from .reflexion import ReflexionEngine, ReflexionLesson
from .stability import StabilityBudget, StabilityState, BudgetViolation


__all__ = [
    "ControllerConfig",
    "ClosedLoopController",
    "HaltSignal",
]


@dataclass(frozen=True)
class HaltSignal:
    """Emitted when a stability budget is violated and execution must stop."""

    session_id: str
    turn_index: int
    violations: tuple[BudgetViolation, ...]

    @property
    def reason(self) -> str:
        return "; ".join(f"{v.budget_name}={v.current_value:.3f} > {v.limit:.3f}"
                         for v in self.violations)


@dataclass(frozen=True)
class ControllerConfig:
    halt_on_violation: bool = True
    max_turn_refinements: int = 3


class ClosedLoopController:
    """Per-session controller that enforces stability and accumulates lessons.

    Usage::

        controller = ClosedLoopController("sess-1", "run-1")
        ctrl_rec, halt = controller.on_turn(turn_index=0, aer_span_id="span-1",
                                             tool_cost_usd=0.02, policy_blocked=False)
        if halt:
            # stop execution
            ...
    """

    def __init__(
        self,
        session_id: str,
        run_id: str,
        budget: Optional[StabilityBudget] = None,
        config: Optional[ControllerConfig] = None,
        reflexion: Optional[ReflexionEngine] = None,
    ) -> None:
        self.session_id = session_id
        self.run_id = run_id
        self._budget = budget or StabilityBudget()
        self._config = config or ControllerConfig()
        self._reflexion = reflexion or ReflexionEngine()
        self._state = StabilityState()
        self._records: list[ControlRecord] = []

    # ---------------------------------------------------------------- #
    # Core interface                                                     #
    # ---------------------------------------------------------------- #

    def on_turn(
        self,
        turn_index: int,
        aer_span_id: str = "",
        tool_cost_usd: float = 0.0,
        tool_retries: int = 0,
        policy_blocked: bool = False,
        verifier_failed: bool = False,
        eval_score: float = 0.0,
        hitl_pending: bool = False,
        fleet_alert: str = "",
        behavior_drift: float = 0.0,
    ) -> tuple[ControlRecord, Optional[HaltSignal]]:
        """Process one agent turn. Returns (ControlRecord, HaltSignal or None)."""
        self._state.record_cost(tool_cost_usd)
        self._state.retry_count += tool_retries
        if policy_blocked:
            self._state.record_unsafe_action()
        if verifier_failed:
            self._state.record_failed_test()
        if behavior_drift > 0:
            self._state.set_behavior_drift(behavior_drift)

        rec = new_control_record(self.session_id, self.run_id, turn_index, aer_span_id)
        rec.turn_eval_score = eval_score
        rec.step_tool_retries = tool_retries
        rec.hitl_pending = hitl_pending
        rec.fleet_sre_alert = fleet_alert

        self._records.append(rec)

        violations = self._state.check(self._budget)
        if violations and self._config.halt_on_violation:
            halt = HaltSignal(
                session_id=self.session_id,
                turn_index=turn_index,
                violations=tuple(violations),
            )
            return rec, halt

        return rec, None

    def record_lesson(self, lesson: ReflexionLesson) -> None:
        self._reflexion.record(lesson)

    @property
    def state(self) -> StabilityState:
        return self._state

    @property
    def records(self) -> list[ControlRecord]:
        return list(self._records)

    @property
    def lessons(self) -> list[ReflexionLesson]:
        return self._reflexion.lessons_for_session(self.session_id)
