"""
Cognitive Tick Loop for the Lyra AGI Cognitive Architecture.

Implements the main orchestration loop that cycles through:
Perceive -> Attend -> Reason -> Decide -> Act -> Observe

The loop runs until a task is complete or a maximum tick count is reached.
Supports interrupt injection for high-priority signals.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from lyra_cognitive.dual_system import (
    MetaCognitiveController,
    System1Executor,
    System2Planner,
)
from lyra_cognitive.models import (
    CognitiveState,
    CognitiveTick,
    ConfidenceLevel,
    Plan,
    SystemMode,
    Thought,
)
from lyra_cognitive.reasoning import ReasoningEngine
from lyra_cognitive.theater_of_mind import TheaterOfMind

logger = logging.getLogger(__name__)


class CognitiveLoop:
    """
    Main cognitive loop orchestrator.

    Coordinates the dual-system engine, theater of mind workspace,
    and reasoning strategies through a continuous tick cycle.

    Each tick represents one complete iteration of:
    Perceive -> Attend -> Reason -> Decide -> Act -> Observe
    """

    def __init__(
        self,
        theater: TheaterOfMind | None = None,
        system1: System1Executor | None = None,
        system2: System2Planner | None = None,
        reasoning: ReasoningEngine | None = None,
        max_ticks_default: int = 100,
    ):
        """
        Args:
            theater: Global workspace instance (created if not provided).
            system1: Fast execution engine.
            system2: Deliberate planning engine.
            reasoning: Multi-strategy reasoning engine.
            max_ticks_default: Default maximum ticks per run().
        """
        self._theater = theater or TheaterOfMind()
        self._system1 = system1 or System1Executor()
        self._system2 = system2 or System2Planner()
        self._reasoning = reasoning or ReasoningEngine()
        self._meta = MetaCognitiveController(self._system1, self._system2)
        self._max_ticks_default = max_ticks_default

        self._ticks: list[CognitiveTick] = []
        self._current_plan: Plan | None = None
        self._completed_steps: list[int] = []  # Indices into current plan steps
        self._interrupt_queue: list[Thought] = []
        self._started_at: datetime | None = None
        self._mode: SystemMode = SystemMode.IDLE

    @property
    def theater(self) -> TheaterOfMind:
        """Access the global workspace."""
        return self._theater

    @property
    def current_mode(self) -> SystemMode:
        """Get the current system mode."""
        return self._mode

    @property
    def tick_count(self) -> int:
        """Number of ticks executed in the current run."""
        return len(self._ticks)

    def tick(self, observation: str = "") -> CognitiveTick:
        """
        Execute one full cognitive cycle.

        Args:
            observation: Optional external observation to start with.

        Returns:
            The CognitiveTick record for this cycle.
        """
        index = len(self._ticks)

        # 1. PERCEIVE: gather observations from environment and workspace
        perception = self._perceive(observation)

        # 2. ATTEND: select which signals to focus on
        attended = self._attend()

        # 3. REASON: apply appropriate reasoning strategy
        reasoning_output = self._reason(attended, perception)

        # 4. DECIDE: choose action based on reasoning
        decision = self._decide(reasoning_output)

        # 5. ACT: execute the chosen action
        action_result = self._act(decision)

        # 6. OBSERVE: record the outcome
        obs = self._observe(action_result)

        tick_record = CognitiveTick(
            index=index,
            mode=self._mode,
            perception=tuple(perception),
            attended=frozenset(t.id for t in attended),
            reasoning=reasoning_output,
            decision=decision,
            action=action_result,
            observation=obs,
            timestamp=datetime.now(),
        )

        self._ticks.append(tick_record)
        self._theater.tick_maintenance()

        logger.debug(
            "CognitiveLoop: tick %d complete, mode=%s, attended=%d",
            index,
            self._mode.value,
            len(attended),
        )

        return tick_record

    def run(
        self,
        task: str,
        max_ticks: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[CognitiveTick]:
        """
        Run the cognitive loop until the task is complete or max ticks reached.

        Args:
            task: The high-level task to accomplish.
            max_ticks: Maximum number of ticks (default: self._max_ticks_default).
            context: Optional context for task execution.

        Returns:
            List of CognitiveTick records for the full execution.
        """
        max_t = max_ticks or self._max_ticks_default
        self._started_at = datetime.now()
        self._ticks.clear()
        self._completed_steps.clear()

        logger.info("CognitiveLoop: starting task '%s' (max %d ticks)", task[:80], max_t)

        # Initial mode assessment
        self._mode = self._meta.assess_task(task)

        # If System 2, generate a plan
        if self._mode == SystemMode.SYSTEM2:
            self._current_plan = self._system2.generate_plan(task, context)
            # Publish plan as thought
            plan_thought = Thought(
                source="System2Planner",
                content=f"Plan: {self._current_plan.goal} ({self._current_plan.step_count} steps)",
                confidence=self._current_plan.confidence,
                tags=frozenset({"plan", "system2"}),
            )
            self._theater.publish(plan_thought)

        # Run tick loop
        for tick_idx in range(max_t):
            # Process interrupts
            if self._interrupt_queue:
                interrupt_thought = self._interrupt_queue.pop(0)
                self._theater.publish(interrupt_thought)
                self._theater.focus(interrupt_thought.id)
                logger.info(
                    "CognitiveLoop: processing interrupt: %s",
                    interrupt_thought.content[:60],
                )

            # Execute one tick
            tick_record = self.tick()

            # Check for escalation
            if self._meta.should_escalate(tick_record.observation, self._mode):
                self._mode = SystemMode.SYSTEM2
                self._current_plan = self._system2.generate_plan(
                    f"Escalated: {tick_record.observation}", context
                )
                logger.warning("CognitiveLoop: escalated to System2 at tick %d", tick_idx)

            # Check task completion
            if self._is_task_complete():
                logger.info(
                    "CognitiveLoop: task complete after %d ticks",
                    tick_idx + 1,
                )
                break

        # Cache the plan if applicable
        if self._current_plan and self._meta.should_cache(self._current_plan):
            for i, step in enumerate(self._current_plan.steps):
                result = f"Cached result for step {i}: {step}"
                self._system1.cache_pattern(step, result)

        elapsed = (datetime.now() - self._started_at).total_seconds()
        logger.info(
            "CognitiveLoop: finished in %d ticks (%.1fs), final mode=%s",
            len(self._ticks),
            elapsed,
            self._mode.value,
        )

        return list(self._ticks)

    def interrupt(self, signal: Thought) -> None:
        """
        Inject a high-priority interrupt into the loop.

        The interrupt will be processed at the start of the next tick.

        Args:
            signal: The interrupt thought to inject.
        """
        self._interrupt_queue.append(signal)
        logger.info("CognitiveLoop: interrupt queued: %s", signal.content[:60])

    def get_trace(self) -> list[CognitiveTick]:
        """
        Get the full execution trace for audit/debugging.

        Returns:
            Copy of all CognitiveTick records from the current or last run.
        """
        return list(self._ticks)

    def get_state(self) -> CognitiveState:
        """
        Get a snapshot of the current cognitive state.

        Returns:
            CognitiveState with current mode, attention state, and progress.
        """
        attended = self._theater.attend()
        progress = 0.0
        if self._current_plan and self._current_plan.step_count > 0:
            progress = len(self._completed_steps) / self._current_plan.step_count

        return CognitiveState(
            mode=self._mode,
            active_thoughts=frozenset(t.id for t in attended),
            working_memory=dict(self._theater.get_workspace_state().get("working_memory", {})),
            task_progress=progress,
            cycle_count=len(self._ticks),
            timestamp=datetime.now(),
        )

    def reset(self) -> None:
        """Reset the loop state for a new task."""
        self._ticks.clear()
        self._current_plan = None
        self._completed_steps.clear()
        self._interrupt_queue.clear()
        self._started_at = None
        self._mode = SystemMode.IDLE
        logger.info("CognitiveLoop: reset")

    # ── Tick phase implementations ────────────────────────────────────────

    def _perceive(self, external_observation: str) -> list[str]:
        """Gather observations from environment and workspace state."""
        perceptions: list[str] = []

        if external_observation:
            perceptions.append(f"External: {external_observation}")

        # Gather workspace state
        ws = self._theater.get_workspace_state()
        focused = ws.get("focused_thought")
        if focused:
            perceptions.append(f"Focused: {focused[:120]}")

        # Check current plan progress
        if self._current_plan:
            ready = self._current_plan.get_ready_steps(frozenset(self._completed_steps))
            perceptions.append(
                f"Plan progress: {len(self._completed_steps)}/{self._current_plan.step_count} "
                f"steps done, {len(ready)} ready"
            )

        return perceptions

    def _attend(self) -> list[Thought]:
        """Select which thoughts receive conscious attention."""
        return self._theater.attend()

    def _reason(self, attended: list[Thought], perception: list[str]) -> str:
        """Apply reasoning strategy based on current mode."""
        combined_context = " | ".join(perception[:3]) if perception else "no perception"
        thought_context = " | ".join(t.content[:60] for t in attended)

        if self._mode == SystemMode.SYSTEM2:
            result = self._reasoning.chain_of_thought(
                f"Perception: {combined_context}. Context: {thought_context}"
            )
            return result.conclusion
        else:
            # System 1: fast heuristic reasoning
            if attended:
                return f"Quick assessment: {attended[0].content[:100]}"
            return f"Quick assessment based on: {combined_context[:100]}"

    def _decide(self, reasoning_output: str) -> str:
        """Choose an action based on reasoning."""
        if self._current_plan and self._mode == SystemMode.SYSTEM2:
            ready = self._current_plan.get_ready_steps(frozenset(self._completed_steps))
            if ready:
                step_idx = ready[0]
                step_desc = self._current_plan.steps[step_idx]
                return f"Execute step {step_idx}: {step_desc}"

        return f"Proceed with: {reasoning_output[:100]}"

    def _act(self, decision: str) -> str:
        """Execute the decided action."""
        # Execute through System 1 for speed; escalate if needed
        result = self._system1.execute_step(decision)
        return result

    def _observe(self, action_result: str) -> str:
        """Record and interpret the outcome of the action."""
        # Publish observation as thought
        thought = Thought(
            source="CognitiveLoop",
            content=f"Observed: {action_result[:200]}",
            confidence=ConfidenceLevel.MEDIUM,
            tags=frozenset({"observation"}),
        )
        self._theater.publish(thought)

        # Track step completion
        if self._current_plan:
            for i in range(self._current_plan.step_count):
                step_desc = self._current_plan.steps[i]
                if step_desc[:40] in action_result and i not in self._completed_steps:
                    self._completed_steps.append(i)
                    break

        return action_result

    def _is_task_complete(self) -> bool:
        """Check if the current task is complete."""
        if not self._current_plan:
            # Without a plan, check if we have sufficient ticks
            return len(self._ticks) >= 3

        # With a plan, check if all steps are completed
        return len(self._completed_steps) >= self._current_plan.step_count
