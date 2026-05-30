"""Dynamic Reconfiguration — stagnation-triggered squad reorganization with bandit optimization.

Implements automatic topology adaptation:
  - Stagnation detection with configurable thresholds
  - Bandit-based action selection (add_worker, reassign_lead, dissolve, etc.)
  - Load-based rebalancing across squads
  - Reconfiguration plan lifecycle: create → execute → clear
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class ReconfigTrigger(StrEnum):
    """What triggered a reconfiguration."""

    STAGNATION = "stagnation"
    LOAD_IMBALANCE = "load_imbalance"
    FAILURE = "failure"
    SCHEDULED = "scheduled"
    HEALTH_DEGRADED = "health_degraded"


class ReconfigAction(StrEnum):
    """Possible reconfiguration actions."""

    DISSOLVE = "dissolve"
    MERGE = "merge"
    SPLIT = "split"
    REASSIGN_LEADER = "reassign_leader"
    ADD_WORKER = "add_worker"
    REMOVE_WORKER = "remove_worker"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class ReconfigPlan:
    """A planned reconfiguration to be executed."""

    plan_id: str
    trigger: ReconfigTrigger
    action: ReconfigAction
    target_squad_id: str
    reason: str = ""
    params: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)
    executed: bool = False


@dataclass
class BanditMetrics:
    """Metrics for bandit-based action selection (epsilon-greedy)."""

    squad_id: str
    arm: str
    reward: float
    trials: int = 1
    last_updated: float = field(default_factory=time.monotonic)

    def update(self, new_reward: float) -> BanditMetrics:
        """Update the running average reward with a new observation."""
        new_trials = self.trials + 1
        new_avg = (self.reward * self.trials + new_reward) / new_trials
        return BanditMetrics(
            squad_id=self.squad_id,
            arm=self.arm,
            reward=new_avg,
            trials=new_trials,
            last_updated=time.monotonic(),
        )


class DynamicReconfig:
    """Manages dynamic topology reconfiguration for the swarm.

    Detects stagnation, load imbalance, and health degradation triggers,
    then generates and executes reconfiguration plans. Uses epsilon-greedy
    bandit optimization to learn which actions work best per squad.

    Usage::

        dr = DynamicReconfig()
        plan = dr.check_and_plan(squad_id="s-1", last_progress_ms=15_000)
        if plan:
            result = dr.execute_plan(plan.plan_id)
    """

    def __init__(self) -> None:
        self._plans: dict[str, ReconfigPlan] = {}
        self._bandit_arms: dict[str, dict[str, BanditMetrics]] = defaultdict(dict)
        self._execution_history: list[ReconfigPlan] = []

    # ── Properties ───────────────────────────────────────────────

    @property
    def plan_count(self) -> int:
        return len(self._plans)

    @property
    def pending_plan_count(self) -> int:
        return sum(1 for p in self._plans.values() if not p.executed)

    # ── Plan Lifecycle ───────────────────────────────────────────

    def create_plan(
        self,
        trigger: ReconfigTrigger,
        action: ReconfigAction,
        target_squad_id: str,
        reason: str = "",
        params: dict | None = None,
    ) -> ReconfigPlan:
        """Create a new reconfiguration plan."""
        plan = ReconfigPlan(
            plan_id=f"rp-{uuid.uuid4().hex[:12]}",
            trigger=trigger,
            action=action,
            target_squad_id=target_squad_id,
            reason=reason,
            params=params or {},
        )
        self._plans[plan.plan_id] = plan
        return plan

    def execute_plan(self, plan_id: str) -> ReconfigPlan:
        """Execute a pending plan. Marks it as executed and records history."""
        plan = self._plans.get(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")
        if plan.executed:
            raise ValueError(f"Plan '{plan_id}' already executed")

        executed = ReconfigPlan(
            plan_id=plan.plan_id,
            trigger=plan.trigger,
            action=plan.action,
            target_squad_id=plan.target_squad_id,
            reason=plan.reason,
            params=plan.params,
            created_at=plan.created_at,
            executed=True,
        )
        self._plans[plan_id] = executed
        self._execution_history.append(executed)
        return executed

    def get_pending_plans(self) -> list[ReconfigPlan]:
        """Get all unexecuted plans."""
        return [p for p in self._plans.values() if not p.executed]

    def get_plan(self, plan_id: str) -> ReconfigPlan | None:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def clear_executed(self) -> int:
        """Remove executed plans and return count cleared."""
        to_remove = [
            pid for pid, p in self._plans.items() if p.executed
        ]
        for pid in to_remove:
            del self._plans[pid]
        return len(to_remove)

    # ── Stagnation Detection ─────────────────────────────────────

    def detect_stagnation(
        self,
        squad_id: str,  # noqa: ARG002
        last_progress_ms: float,
        stagnation_threshold_ms: float = 10_000.0,
    ) -> bool:
        """Check if a squad has stagnated based on time since last progress."""
        _ = squad_id
        return last_progress_ms >= stagnation_threshold_ms

    def check_and_plan(
        self,
        squad_id: str,
        last_progress_ms: float,
        stagnation_threshold_ms: float = 10_000.0,
        failure_rate: float = 0.0,
    ) -> ReconfigPlan | None:
        """Check for stagnation and create a plan if needed.

        Uses bandit-optimized action selection when available,
        falling back to heuristic rule-based selection.
        """
        if not self.detect_stagnation(squad_id, last_progress_ms, stagnation_threshold_ms):
            return None

        action = self._select_action(squad_id, failure_rate)
        return self.create_plan(
            trigger=ReconfigTrigger.STAGNATION,
            action=action,
            target_squad_id=squad_id,
            reason=(
                f"Stagnation: {last_progress_ms:.0f}ms without progress, "
                f"failure_rate={failure_rate:.2f}"
            ),
            params={
                "last_progress_ms": last_progress_ms,
                "failure_rate": failure_rate,
            },
        )

    # ── Bandit Optimization ──────────────────────────────────────

    def record_bandit(self, squad_id: str, arm: str, reward: float) -> None:
        """Record a reward for a bandit arm (action outcome)."""
        existing = self._bandit_arms.get(squad_id, {}).get(arm)
        if existing:
            self._bandit_arms[squad_id][arm] = existing.update(reward)
        else:
            self._bandit_arms[squad_id][arm] = BanditMetrics(
                squad_id=squad_id, arm=arm, reward=reward
            )

    def select_best_arm(self, squad_id: str) -> str | None:
        """Select the best-performing arm for a squad."""
        arms = self._bandit_arms.get(squad_id, {})
        if not arms:
            return None
        return max(arms, key=lambda a: arms[a].reward)

    def _select_action(
        self,
        squad_id: str,
        failure_rate: float,
    ) -> ReconfigAction:
        """Select the best reconfiguration action using bandits or heuristics."""
        best_arm = self.select_best_arm(squad_id)
        if best_arm is not None:
            try:
                return ReconfigAction(best_arm)
            except ValueError:
                pass

        if failure_rate > 0.7:
            return ReconfigAction.DISSOLVE
        if failure_rate > 0.4:
            return ReconfigAction.REASSIGN_LEADER
        return ReconfigAction.ADD_WORKER

    # ── Load Balancing ───────────────────────────────────────────

    def detect_load_imbalance(
        self,
        squad_loads: dict[str, float],
        imbalance_threshold: float = 0.3,
    ) -> bool:
        """Check if load distribution across squads is imbalanced."""
        if len(squad_loads) < 2:
            return False
        loads = list(squad_loads.values())
        return max(loads) - min(loads) > imbalance_threshold

    def generate_rebalance_plan(
        self,
        squad_loads: dict[str, float],
    ) -> ReconfigPlan | None:
        """Generate a rebalancing plan for imbalanced squads."""
        if not self.detect_load_imbalance(squad_loads):
            return None

        overloaded = max(squad_loads, key=lambda k: squad_loads[k])
        underloaded = min(squad_loads, key=lambda k: squad_loads[k])

        return self.create_plan(
            trigger=ReconfigTrigger.LOAD_IMBALANCE,
            action=ReconfigAction.ADD_WORKER,
            target_squad_id=overloaded,
            reason=(
                f"Load imbalance: {overloaded}={squad_loads[overloaded]:.2f} vs "
                f"{underloaded}={squad_loads[underloaded]:.2f}"
            ),
            params={
                "overloaded_squad": overloaded,
                "underloaded_squad": underloaded,
                "overloaded_value": squad_loads[overloaded],
                "underloaded_value": squad_loads[underloaded],
            },
        )

    # ── History & Reset ──────────────────────────────────────────

    def get_history(self) -> list[ReconfigPlan]:
        """Return execution history."""
        return list(self._execution_history)

    def reset(self) -> None:
        """Reset all state."""
        self._plans.clear()
        self._bandit_arms.clear()
        self._execution_history.clear()
