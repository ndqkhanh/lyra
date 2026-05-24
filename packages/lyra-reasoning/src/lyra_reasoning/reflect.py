"""
ReflAct Reasoning — Reflexion + Acting loop.

The agent reasons (thought), acts, observes, and reflects on outcomes.
Inspired by the ReAct / Reflexion line of research:
- Yao et al. "ReAct: Synergizing Reasoning and Acting in Language Models"
- Shinn et al. "Reflexion: Language Agents with Verbal Reinforcement Learning"

This module implements the core loop plus meta-cognitive operations:
reflection, adaptation, and cross-episode synthesis.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .models import ReasoningStep, ReasoningTrace, ReflActEpisode

logger = logging.getLogger(__name__)


class ReflActReasoner:
    """Reflexion + Acting reasoning engine.

    The core loop reasons step-by-step through a task, acts on its
    reasoning, observes the (simulated or real) outcome, and adjusts its
    confidence. After completing a trace it can *reflect* to extract
    lessons, *adapt* its approach for the next attempt, and *synthesize*
    knowledge across multiple traces.
    """

    def __init__(
        self,
        *,
        default_max_steps: int = 10,
        confidence_threshold: float = 0.7,
        reflection_temperature: float = 0.3,
    ) -> None:
        self.default_max_steps = default_max_steps
        self.confidence_threshold = confidence_threshold
        self.reflection_temperature = reflection_temperature
        self._episode_history: List[ReflActEpisode] = []

    # ── Core loop ──────────────────────────────────────────────────────────

    def reason(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None,
    ) -> ReasoningTrace:
        """Run the ReflAct loop on *task*.

        Each iteration produces a thought, an action, and an observation.
        The loop stops when confidence exceeds *confidence_threshold*, the
        step budget is exhausted, or a terminal action is emitted.

        Args:
            task: Description of the task to solve.
            context: Optional extra context (e.g. retrieved documents).
            max_steps: Maximum number of reasoning steps (overrides default).

        Returns:
            A complete ``ReasoningTrace``.
        """
        max_steps = max_steps if max_steps is not None else self.default_max_steps
        trace = ReasoningTrace(task=task, strategy="reflect")
        start = time.monotonic()

        ctx = context or {}
        current_state: Dict[str, Any] = {"task": task, "context": ctx, "history": []}

        for step_num in range(1, max_steps + 1):
            thought = self._think(step_num, current_state)
            action = self._act(thought, current_state)
            observation = self._observe(action, current_state)
            confidence = self._estimate_confidence(thought, action, observation)

            step = ReasoningStep(
                step_number=step_num,
                thought=thought,
                action=action,
                observation=observation,
                confidence=confidence,
            )
            trace = trace.add_step(step)
            current_state["history"].append(
                {"thought": thought, "action": action, "observation": observation}
            )

            logger.debug(
                "ReflAct step %d | confidence=%.2f | action=%s",
                step_num,
                confidence,
                action[:80],
            )

            if confidence >= self.confidence_threshold:
                logger.info(
                    "ReflAct converged after %d steps (confidence=%.2f)",
                    step_num,
                    confidence,
                )
                break
            if self._is_terminal(action, observation):
                logger.info("ReflAct terminal action at step %d", step_num)
                break

        elapsed = time.monotonic() - start
        final_step = trace.final_step()
        outcome = "success" if final_step and final_step.confidence >= self.confidence_threshold else "incomplete"

        trace = ReasoningTrace(
            task=trace.task,
            steps=trace.steps,
            outcome=outcome,
            duration=elapsed,
            token_count=sum(len(s.thought) + len(s.action) + len(s.observation) for s in trace.steps),
            strategy=trace.strategy,
            metadata=trace.metadata,
        )

        logger.info(
            "ReflAct finished: outcome=%s steps=%d duration=%.2fs",
            outcome,
            trace.num_steps,
            elapsed,
        )
        return trace

    # ── Meta-cognition ─────────────────────────────────────────────────────

    def reflect(self, trace: ReasoningTrace) -> Tuple[str, ...]:
        """Extract lessons learned from a completed trace.

        Analyses what worked and what did not, returning actionable
        lessons that can be fed back into ``adapt``.

        Args:
            trace: A completed reasoning trace.

        Returns:
            Tuple of lesson strings.
        """
        lessons: List[str] = []

        if not trace.steps:
            lessons.append("No reasoning steps were taken — task may be too trivial or ill-defined.")
            return tuple(lessons)

        # Analyse step confidences
        confidences = [s.confidence for s in trace.steps]
        low_conf_steps = [s for s in trace.steps if s.confidence < 0.5]

        if low_conf_steps:
            lessons.append(
                f"{len(low_conf_steps)} step(s) had low confidence (<0.5); "
                f"consider gathering more context before similar actions."
            )

        # Check for improvement trend
        if len(confidences) >= 2:
            early_avg = sum(confidences[: len(confidences) // 2]) / (len(confidences) // 2)
            late_avg = sum(confidences[len(confidences) // 2 :]) / (len(confidences) - len(confidences) // 2)
            if late_avg > early_avg + 0.1:
                lessons.append("Confidence improved over time — iterative refinement is working.")
            elif late_avg < early_avg - 0.1:
                lessons.append("Confidence decreased — may indicate drift or compounding errors.")

        # Detect ineffective actions
        for step in trace.steps:
            if "error" in step.observation.lower() or "fail" in step.observation.lower():
                lessons.append(
                    f"Action '{step.action[:60]}' resulted in error/failure; "
                    f"avoid similar actions in this context."
                )

        if not lessons:
            lessons.append("All steps completed with adequate confidence.")

        logger.info(
            "Reflection on task '%s': extracted %d lesson(s)",
            trace.task[:60],
            len(lessons),
        )
        return tuple(lessons)

    def adapt(self, task: str, lessons: Sequence[str]) -> Dict[str, Any]:
        """Modify the reasoner's approach based on prior lessons.

        Returns an updated context dict that should be passed to
        subsequent ``reason`` calls for the same or similar task.

        Args:
            task: The task being adapted to.
            lessons: Lessons from ``reflect``.

        Returns:
            Adaptation context dict.
        """
        adaptation: Dict[str, Any] = {
            "task": task,
            "lessons_applied": list(lessons),
            "strategy_modifiers": {},
        }

        for lesson in lessons:
            lesson_lower = lesson.lower()
            if "low confidence" in lesson_lower or "confidence decreased" in lesson_lower:
                adaptation["strategy_modifiers"]["extra_verification"] = True
                adaptation["strategy_modifiers"]["confidence_threshold_boost"] = 0.1
            if "error" in lesson_lower or "fail" in lesson_lower:
                adaptation["strategy_modifiers"]["avoid_risky_actions"] = True
            if "gather" in lesson_lower or "context" in lesson_lower:
                adaptation["strategy_modifiers"]["enrich_context"] = True

        logger.info(
            "Adaptation for task '%s': modifiers=%s",
            task[:60],
            adaptation["strategy_modifiers"],
        )
        return adaptation

    def synthesize(self, traces: Sequence[ReasoningTrace]) -> List[str]:
        """Combine learning from multiple traces into cross-episode insights.

        Args:
            traces: Multiple completed reasoning traces.

        Returns:
            List of synthesized insights.
        """
        if not traces:
            return ["No traces available for synthesis."]

        insights: List[str] = []

        successful = [t for t in traces if t.outcome == "success"]
        failed = [t for t in traces if t.outcome != "success"]
        success_rate = len(successful) / len(traces) if traces else 0.0

        insights.append(
            f"Aggregate success rate: {success_rate:.1%} ({len(successful)}/{len(traces)} traces)"
        )

        # Average steps
        avg_steps = sum(t.num_steps for t in traces) / len(traces)
        insights.append(f"Average steps per trace: {avg_steps:.1f}")

        # Common failure patterns
        if failed:
            failed_tasks = [t.task for t in failed]
            insights.append(
                f"Failed on {len(failed)} task(s): {', '.join(failed_tasks[:3])}..."
                if len(failed_tasks) > 3
                else f"Failed on {len(failed)} task(s): {', '.join(failed_tasks)}"
            )

        # Confidence trajectories
        all_confidences = [
            s.confidence for t in traces for s in t.steps if t.steps
        ]
        if all_confidences:
            avg_confidence = sum(all_confidences) / len(all_confidences)
            insights.append(f"Average step confidence across all traces: {avg_confidence:.2f}")

        # Efficiency insight
        if success_rate > 0.8:
            insights.append("High success rate — consider reducing step budget for efficiency.")
        elif success_rate < 0.5:
            insights.append(
                "Low success rate — consider increasing max_steps or enriching task context."
            )

        logger.info("Synthesis complete: %d insight(s) from %d traces", len(insights), len(traces))
        return insights

    # ── Episode management ─────────────────────────────────────────────────

    def record_episode(
        self,
        task: str,
        trace: ReasoningTrace,
        lessons: Optional[Sequence[str]] = None,
    ) -> ReflActEpisode:
        """Record a completed episode for longitudinal learning.

        Args:
            task: The task that was solved.
            trace: The completed reasoning trace.
            lessons: Optional pre-computed lessons.

        Returns:
            The recorded ``ReflActEpisode``.
        """
        computed_lessons = tuple(lessons) if lessons is not None else self.reflect(trace)

        episode = ReflActEpisode(
            task=task,
            trace=trace,
            outcome=trace.outcome,
            lessons_learned=computed_lessons,
            success=trace.outcome == "success",
            score=trace.final_step().confidence if trace.final_step() else 0.0,
        )
        self._episode_history.append(episode)
        logger.info("Recorded episode for task '%s' (total episodes: %d)", task[:60], len(self._episode_history))
        return episode

    @property
    def episode_count(self) -> int:
        return len(self._episode_history)

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    def _think(step_num: int, state: Dict[str, Any]) -> str:
        """Produce the next thought given the current state.

        In a production system this would call an LLM. Here we implement
        a simple rule-based thought generator that produces plausible
        reasoning text for testing and demonstration.
        """
        task = state.get("task", "")
        history = state.get("history", [])

        if not history:
            return f"Understand the task: {task}. Identify key components and constraints."

        last_obs = history[-1].get("observation", "") if history else ""

        if step_num <= 2:
            return f"Analyse the initial observation and formulate a plan for '{task}'."
        elif "error" in last_obs.lower() or "fail" in last_obs.lower():
            return "The previous action failed. Revise the approach and consider alternative strategies."
        else:
            return f"Build on progress: evaluate current findings and determine the next logical step for '{task}'."

    @staticmethod
    def _act(thought: str, state: Dict[str, Any]) -> str:
        """Choose an action based on the current thought."""
        thought_lower = thought.lower()

        if "understand" in thought_lower or "identify" in thought_lower:
            return "decompose_task"
        if "analyse" in thought_lower or "plan" in thought_lower:
            return "analyse_and_plan"
        if "revise" in thought_lower or "alternative" in thought_lower:
            return "explore_alternative"
        if "evaluate" in thought_lower or "build" in thought_lower:
            return "synthesize_findings"
        return "continue_reasoning"

    @staticmethod
    def _observe(action: str, state: Dict[str, Any]) -> str:
        """Simulate observation of the action's outcome."""
        observations = {
            "decompose_task": "Task decomposed into sub-components. Structure is clear.",
            "analyse_and_plan": "Analysis complete. A step-by-step plan has been formulated.",
            "explore_alternative": "Alternative approach identified. New path shows promise.",
            "synthesize_findings": "Findings synthesized into coherent intermediate conclusion.",
            "continue_reasoning": "Reasoning continues. More information needed for conclusive result.",
        }
        return observations.get(action, f"Action '{action}' executed. Observing outcome.")

    @staticmethod
    def _estimate_confidence(thought: str, action: str, observation: str) -> float:
        """Estimate confidence in the current step (0.0-1.0)."""
        base = 0.6
        obs_lower = observation.lower()

        if "error" in obs_lower or "fail" in obs_lower:
            base -= 0.3
        if "complete" in obs_lower or "synthesized" in obs_lower or "conclusive" in obs_lower:
            base += 0.2
        if "alternative" in obs_lower:
            base += 0.1
        if len(thought) > 80:
            base += 0.05

        return min(1.0, max(0.0, base))

    @staticmethod
    def _is_terminal(action: str, observation: str) -> bool:
        """Check whether the episode has reached a terminal state."""
        terminal_actions = {"synthesize_findings"}
        terminal_indicators = ["conclusive", "final answer", "complete"]
        return action in terminal_actions or any(
            ind in observation.lower() for ind in terminal_indicators
        )
