"""Heartbeat cycle orchestrator — drives the collective intelligence loop.

AutoScientists-inspired "list-decide-read" protocol:
  1. LIST   — Survey available work (hypotheses, experiments, review queues)
  2. DECIDE — Select what to work on using signals + champion state + dead-end proximity
  3. EXECUTE — Run the selected work through agent teams
  4. READ   — Process results, update champion state, register dead-ends, emit events

The heartbeat runs continuously until a terminal condition is met (all work complete,
budget exhausted, or user interrupt). Each cycle advances the collective state.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum

from lyra_core.events import EventBus, EventCategory

from . import CollectiveState, HypothesisTeam
from .champion_tracker import ChampionStatus, ChampionTracker

logger = logging.getLogger(__name__)


# ── Work item model ────────────────────────────────────────────────────────────


class WorkKind(str, Enum):
    """Kinds of work the orchestrator can dispatch."""
    VERIFY_HYPOTHESIS = "verify_hypothesis"
    PROPOSE_HYPOTHESIS = "propose_hypothesis"
    PEER_REVIEW = "peer_review"
    EXPERIMENT = "experiment"
    COVERAGE_AUDIT = "coverage_audit"
    DEAD_END_RECHECK = "dead_end_recheck"


class WorkPriority(str, Enum):
    """Priority levels for work items."""
    CRITICAL = "critical"    # Confirmed champion under threat
    HIGH = "high"            # Active champion needs verification
    MEDIUM = "medium"        # New proposal
    LOW = "low"              # Exploratory / audit


@dataclass
class WorkItem:
    """A unit of work discovered during the LIST phase."""

    id: str
    kind: WorkKind
    priority: WorkPriority = WorkPriority.MEDIUM
    hypothesis_id: str | None = None
    team_id: str | None = None
    description: str = ""
    assigned_to: str | None = None  # agent_id
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class HeartbeatResult:
    """Result of one complete heartbeat cycle."""

    cycle: int
    work_items_listed: int
    work_items_selected: int
    work_items_completed: int
    champions_updated: int
    hypotheses_verified: int
    hypotheses_falsified: int
    dead_ends_registered: int
    elapsed_s: float
    terminal: bool = False
    terminal_reason: str = ""


class HeartbeatPhase(str, Enum):
    """Phases within a single heartbeat cycle."""
    LIST = "list"
    DECIDE = "decide"
    EXECUTE = "execute"
    READ = "read"


# ── Executor protocol ──────────────────────────────────────────────────────────

AgentExecutor = Callable[[WorkItem, HypothesisTeam], Coroutine[None, None, dict]]


# ── Heartbeat Orchestrator ─────────────────────────────────────────────────────


class HeartbeatOrchestrator:
    """Drives the collective intelligence cycle using list-decide-read.

    This is the central coordinator that replaces ad-hoc agent coordination
    with a structured cycle:

      LIST → DECIDE → EXECUTE → READ → (repeat)

    Each phase emits lifecycle events for observability. The orchestrator
    integrates with CollectiveState (shared state, forum, dead-ends),
    ChampionTracker (champion lifecycle), and agent teams.

    Usage::

        state = CollectiveState()
        orchestrator = HeartbeatOrchestrator(state)

        async for result in orchestrator.run(max_cycles=50):
            print(f"Cycle {result.cycle}: {result.work_items_completed} done")
            if result.terminal:
                break
    """

    def __init__(
        self,
        state: CollectiveState,
        *,
        champion_tracker: ChampionTracker | None = None,
        bus: EventBus | None = None,
        max_cycles: int = 100,
        min_work_items_per_cycle: int = 1,
        confirmation_threshold: int = 2,
        staleness_threshold_s: float = 600.0,
    ) -> None:
        self.state = state
        self.champions = champion_tracker or ChampionTracker(
            confirmation_threshold=confirmation_threshold,
            staleness_threshold_s=staleness_threshold_s,
        )
        self._bus = bus or EventBus.get()
        self.max_cycles = max_cycles
        self.min_work_items = min_work_items_per_cycle

        self._executor: AgentExecutor | None = None
        self._cycle: int = 0
        self._terminal: bool = False
        self._terminal_reason: str = ""
        self._cycle_history: list[HeartbeatResult] = []

    # ── Executor registration ─────────────────────────────────────────────

    def set_executor(self, executor: AgentExecutor) -> None:
        """Register an async executor for work items.

        The executor receives (WorkItem, HypothesisTeam) and returns a
        result dict with keys: success, output, score, verifier_id.
        """
        self._executor = executor

    # ── Main loop ─────────────────────────────────────────────────────────

    async def run(self) -> HeartbeatResult:
        """Run one complete heartbeat cycle. Call in a loop.

        Returns HeartbeatResult — check .terminal to stop.
        """
        t0 = time.time()

        if self._terminal:
            return self._last_result()

        # 1. LIST
        items = self._list_work()
        self._emit_phase(HeartbeatPhase.LIST, {"count": len(items)})

        # 2. DECIDE
        selected = self._decide(items)
        self._emit_phase(HeartbeatPhase.DECIDE,
                        {"candidates": len(items), "selected": len(selected)})

        # 3. EXECUTE
        completed = 0
        verified = 0
        falsified = 0
        champions_updated = 0

        executor = self._executor
        for item in selected:
            if executor is None:
                result = self._execute_fallback(item)
            else:
                team = self._resolve_team(item)
                result = await executor(item, team) if team else {"success": False}

            if result.get("success"):
                completed += 1

            # Process verification results
            if item.kind == WorkKind.VERIFY_HYPOTHESIS and item.hypothesis_id:
                score = float(result.get("score", 0.5))
                verifier = str(result.get("verifier_id", "system"))

                # Auto-register hypothesis as champion if not yet tracked
                hyp = self.state.hypotheses.get(item.hypothesis_id)
                champ = self.champions.get_champion_by_id(item.hypothesis_id)
                if champ is None and hyp is not None:
                    self.champions.propose_champion(
                        item.hypothesis_id,
                        hyp.statement,
                        hyp.proposed_by,
                    )

                if result.get("verified", score >= 0.5):
                    try:
                        self.champions.verify_champion(
                            item.hypothesis_id, score, verifier)
                    except KeyError:
                        pass
                    self.state.verify_hypothesis(
                        item.hypothesis_id,
                        str(result.get("output", "")),
                        verified=True,
                        verifier_id=verifier,
                    )
                    verified += 1
                else:
                    self.champions.falsify_champion(
                        item.hypothesis_id,
                        str(result.get("output", "verification failed")),
                    )
                    self.state.verify_hypothesis(
                        item.hypothesis_id,
                        str(result.get("output", "")),
                        verified=False,
                        verifier_id=verifier,
                    )
                    falsified += 1
                champions_updated += 1

        self._emit_phase(HeartbeatPhase.EXECUTE, {"completed": completed})

        # 4. READ — process results, update state
        dead_ends = self._read_results(selected)
        self._emit_phase(HeartbeatPhase.READ, {"dead_ends": dead_ends})

        # 5. Advance cycle + check staleness
        self.state.advance_cycle()
        self._cycle += 1
        stale = self.champions.check_staleness()
        if stale:
            logger.info("Stale champions detected: %s", stale)

        # Terminal checks (deferred until at least one cycle has run)
        terminal = False
        reason = ""

        if self._cycle >= self.max_cycles:
            terminal = True
            reason = f"max_cycles ({self.max_cycles}) reached"
        elif self._cycle >= 1 and not self.state.active_teams and len(items) == 0:
            terminal = True
            reason = "no active teams and no pending work"
        elif self._cycle >= 1 and len(self.champions.confirmed_champions) > 0 and len(items) == 0:
            terminal = True
            reason = "all champions confirmed, no pending work"

        self._terminal = terminal
        self._terminal_reason = reason

        result = HeartbeatResult(
            cycle=self._cycle,
            work_items_listed=len(items),
            work_items_selected=len(selected),
            work_items_completed=completed,
            champions_updated=champions_updated,
            hypotheses_verified=verified,
            hypotheses_falsified=falsified,
            dead_ends_registered=dead_ends,
            elapsed_s=time.time() - t0,
            terminal=terminal,
            terminal_reason=reason,
        )
        self._cycle_history.append(result)
        return result

    async def run_until_terminal(self) -> list[HeartbeatResult]:
        """Run heartbeat cycles until a terminal condition is met."""
        results: list[HeartbeatResult] = []
        while not self._terminal:
            result = await self.run()
            results.append(result)
        return results

    # ── LIST phase ────────────────────────────────────────────────────────

    def _list_work(self) -> list[WorkItem]:
        """Survey available work across all active teams and hypotheses.

        The "list-decide-read" protocol starts here: enumerate
        everything that could be done, then decide what to pick.
        """
        items: list[WorkItem] = []

        # 1. Unverified hypotheses → verification work
        for hid, hyp in self.state.hypotheses.items():
            if hyp.status in ("proposed", "discussion", "queued"):
                is_dead, _ = self.state.dead_ends.is_known_dead_end(hyp.statement)
                if is_dead:
                    continue
                priority = WorkPriority.HIGH if hyp.priority >= 2 else WorkPriority.MEDIUM
                items.append(WorkItem(
                    id=f"verify_{hid}",
                    kind=WorkKind.VERIFY_HYPOTHESIS,
                    priority=priority,
                    hypothesis_id=hid,
                    description=f"Verify hypothesis: {hyp.statement[:120]}",
                ))

        # 2. Active teams without work → propose work
        for team in self.state.active_teams:
            if team.status in ("forming", "discussing"):
                items.append(WorkItem(
                    id=f"propose_{team.id}",
                    kind=WorkKind.PROPOSE_HYPOTHESIS,
                    priority=WorkPriority.MEDIUM,
                    team_id=team.id,
                    description=f"Team {team.id} needs a hypothesis to test",
                ))

        # 3. Stale champions → re-verification
        for champ in self.champions.active_champions:
            if champ.staleness_s > self.champions.staleness_threshold_s * 0.5:
                items.append(WorkItem(
                    id=f"reverify_{champ.hypothesis_id}",
                    kind=WorkKind.VERIFY_HYPOTHESIS,
                    priority=WorkPriority.CRITICAL,
                    hypothesis_id=champ.hypothesis_id,
                    description=f"Re-verify stale champion: {champ.statement[:120]}",
                ))

        # 4. Contested champions → peer review
        for champ in self.champions.active_champions:
            if champ.status == ChampionStatus.CONTESTED:
                items.append(WorkItem(
                    id=f"review_{champ.hypothesis_id}",
                    kind=WorkKind.PEER_REVIEW,
                    priority=WorkPriority.HIGH,
                    hypothesis_id=champ.hypothesis_id,
                    description=f"Peer review contested champion: {champ.statement[:120]}",
                ))

        # 5. Coverage audit — periodic check for gaps
        if self._cycle % 5 == 0 and self._cycle > 0:
            items.append(WorkItem(
                id=f"audit_{self._cycle}",
                kind=WorkKind.COVERAGE_AUDIT,
                priority=WorkPriority.LOW,
                description="Periodic coverage audit for unexplored areas",
            ))

        return items

    # ── DECIDE phase ──────────────────────────────────────────────────────

    def _decide(self, items: list[WorkItem]) -> list[WorkItem]:
        """Select which work items to execute this cycle.

        Decision rules (first-match):
          1. CRITICAL items always selected
          2. HIGH items selected up to capacity
          3. MEDIUM items selected if capacity remains
          4. LOW items fill remaining slots
          5. Skip items matching known dead-ends
        """
        if not items:
            return []

        # Sort by priority
        priority_order = {
            WorkPriority.CRITICAL: 0,
            WorkPriority.HIGH: 1,
            WorkPriority.MEDIUM: 2,
            WorkPriority.LOW: 3,
        }
        sorted_items = sorted(items, key=lambda i: priority_order.get(i.priority, 99))

        selected: list[WorkItem] = []
        capacity = max(self.min_work_items, len(self.state.active_teams) * 2)

        for item in sorted_items:
            if len(selected) >= capacity:
                break

            # Filter: skip known dead-ends
            if item.hypothesis_id:
                hyp = self.state.hypotheses.get(item.hypothesis_id)
                if hyp:
                    is_dead, _ = self.state.dead_ends.is_known_dead_end(hyp.statement)
                    if is_dead:
                        continue

            # Filter: skip verification if team is too young for external review
            # (but allow a team to verify its own hypothesis at any time)
            if item.kind == WorkKind.VERIFY_HYPOTHESIS and item.hypothesis_id:
                team = self._resolve_team(item)
                if (team and team.cycles_completed < team.min_lifetime_cycles
                        and team.hypothesis.id != item.hypothesis_id):
                    if item.priority != WorkPriority.CRITICAL:
                        continue

            selected.append(item)

        return selected

    # ── EXECUTE phase (fallback) ──────────────────────────────────────────

    def _execute_fallback(self, item: WorkItem) -> dict:
        """Synchronous fallback when no async executor is registered.

        Performs basic heuristic evaluation — useful for testing and
        simple scenarios where full agent execution isn't needed.
        """
        if item.kind == WorkKind.VERIFY_HYPOTHESIS and item.hypothesis_id:
            hyp = self.state.hypotheses.get(item.hypothesis_id)
            if hyp is None:
                return {"success": False, "output": "unknown hypothesis"}

            # Heuristic scoring based on hypothesis properties
            score = 0.5
            if len(hyp.statement) > 100:
                score += 0.1
            if len(hyp.test_criteria) > 20:
                score += 0.1
            if hyp.confidence > 0.5:
                score += 0.1

            is_dead, _ = self.state.dead_ends.is_known_dead_end(hyp.statement)
            if is_dead:
                score -= 0.4

            verified = score >= 0.5
            return {
                "success": True,
                "output": f"Heuristic evaluation: score={score:.2f}",
                "score": min(1.0, max(0.0, score)),
                "verified": verified,
                "verifier_id": "heuristic_fallback",
            }

        return {"success": True, "output": "noop"}

    # ── READ phase ────────────────────────────────────────────────────────

    def _read_results(self, executed: list[WorkItem]) -> int:
        """Process execution results: register dead-ends, update forum.

        Returns the number of dead-ends registered this cycle.
        """
        dead_ends_registered = 0

        for item in executed:
            if item.hypothesis_id is None:
                continue

            hyp = self.state.hypotheses.get(item.hypothesis_id)
            if hyp is None:
                continue

            # Register newly falsified hypotheses as dead-ends
            if hyp.status == "falsified":
                from . import DeadEndEntry
                entry = DeadEndEntry(
                    id=f"de_{item.hypothesis_id}_{self._cycle}",
                    hypothesis=hyp.statement,
                    approach=f"Proposed by {hyp.proposed_by}",
                    failure_reason=hyp.result or "unknown",
                    discovered_by=item.assigned_to or "heartbeat_orchestrator",
                )
                self.state.dead_ends.register(entry)
                dead_ends_registered += 1

        return dead_ends_registered

    # ── Helpers ───────────────────────────────────────────────────────────

    def _resolve_team(self, item: WorkItem) -> HypothesisTeam | None:
        """Find the team responsible for a work item."""
        if item.team_id:
            return self.state.teams.get(item.team_id)
        if item.hypothesis_id:
            for team in self.state.teams.values():
                if team.hypothesis.id == item.hypothesis_id:
                    return team
        # Fall back to any available forming/discussing team
        for team in self.state.active_teams:
            if team.status in ("forming", "discussing", "working"):
                return team
        return None

    def _emit_phase(self, phase: HeartbeatPhase, detail: dict) -> None:
        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name=f"heartbeat.{phase.value}",
            origin=__name__,
            payload={"cycle": self._cycle, "phase": phase.value, **detail},
        )

    def _last_result(self) -> HeartbeatResult:
        if self._cycle_history:
            return self._cycle_history[-1]
        return HeartbeatResult(
            cycle=self._cycle,
            work_items_listed=0,
            work_items_selected=0,
            work_items_completed=0,
            champions_updated=0,
            hypotheses_verified=0,
            hypotheses_falsified=0,
            dead_ends_registered=0,
            elapsed_s=0.0,
            terminal=True,
            terminal_reason=self._terminal_reason,
        )

    # ── Query ─────────────────────────────────────────────────────────────

    @property
    def cycle(self) -> int:
        return self._cycle

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def history(self) -> list[HeartbeatResult]:
        return list(self._cycle_history)

    def summary(self) -> dict:
        return {
            "cycle": self._cycle,
            "terminal": self._terminal,
            "terminal_reason": self._terminal_reason,
            "active_teams": len(self.state.active_teams),
            "champions": self.champions.summary(),
            "history_length": len(self._cycle_history),
            "dead_ends": self.state.dead_ends.entry_count,
        }
