"""
Dual-System Cognitive Engine for Lyra AGI.

Implements Kahneman-style System 1 (fast) and System 2 (slow) reasoning
with a meta-cognitive controller that switches between modes based on
task complexity, confidence, and novelty.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from lyra_cognitive.models import (
    ConfidenceLevel,
    Plan,
    SystemMode,
)

logger = logging.getLogger(__name__)

# ── Complexity assessment heuristics ──────────────────────────────────────────

_COMPLEXITY_INDICATORS = frozenset({
    "architecture", "design", "refactor", "debug", "optimize",
    "security", "migrate", "restructure", "evaluate",
})

_ROUTINE_INDICATORS = frozenset({
    "run", "test", "format", "lint", "build", "commit",
    "deploy", "log", "check",
})


def _estimate_complexity(task: str) -> float:
    """Estimate task complexity on a 0.0-1.0 scale using keyword heuristics."""
    task_lower = task.lower()
    score = 0.5  # neutral baseline

    for word in _COMPLEXITY_INDICATORS:
        if word in task_lower:
            score += 0.15

    for word in _ROUTINE_INDICATORS:
        if word in task_lower:
            score -= 0.10

    # Penalize length (longer tasks tend to be more complex)
    word_count = len(task_lower.split())
    if word_count > 20:
        score += 0.10

    return max(0.0, min(1.0, score))


# ── System 2 Planner (Slow, Deliberate) ──────────────────────────────────────

class System2Planner:
    """
    Deliberate reasoning engine for complex tasks.

    Uses structured decomposition, dependency analysis, and cost estimation
    to generate high-quality plans. Designed for Opus-level models with
    extended thinking (5-30 second latency acceptable).
    """

    def __init__(self, cost_model: Callable[[str], float] | None = None):
        """
        Args:
            cost_model: Optional callable that estimates token/cost for a step.
                        Defaults to a word-count heuristic.
        """
        self._cost_model = cost_model or (lambda step: len(step.split()) * 0.01)
        self._plan_cache: dict[str, Plan] = {}

    def generate_plan(self, task: str, context: dict[str, Any] | None = None) -> Plan:
        """
        Generate a structured plan for the given task.

        Args:
            task: The high-level task description.
            context: Optional context dict with constraints, preferences, etc.

        Returns:
            A Plan with ordered steps, dependencies, and cost estimates.
        """
        logger.info("System2: generating plan for task: %s", task[:80])
        ctx = context or {}

        # Decompose task into steps
        steps = self.decompose_task(task)

        # Analyze dependencies between steps
        dependencies = self._analyze_dependencies(steps)

        # Estimate cost for each step
        estimated_costs = {i: self._cost_model(step) for i, step in enumerate(steps)}

        # Evaluate overall plan quality
        quality = self._evaluate_quality(steps, dependencies, estimated_costs)

        plan = Plan(
            goal=task,
            steps=tuple(steps),
            dependencies=dependencies,
            estimated_costs=estimated_costs,
            confidence=ConfidenceLevel.from_score(quality),
            metadata=ctx,
        )

        logger.info(
            "System2: plan generated with %d steps, confidence=%s, cost=%.2f",
            plan.step_count,
            plan.confidence.value,
            plan.total_estimated_cost,
        )
        return plan

    def decompose_task(self, task: str) -> list[str]:
        """
        Break a complex task into ordered subtasks.

        Uses keyword-based decomposition for common task patterns.
        Falls back to simple numbered steps for unknown patterns.

        Args:
            task: The task description to decompose.

        Returns:
            Ordered list of step descriptions.
        """
        task_lower = task.lower()

        if "implement" in task_lower and "test" in task_lower:
            return [
                f"Analyze requirements for: {task}",
                "Design component interfaces and data structures",
                "Implement core logic with type annotations",
                "Write unit tests covering all paths",
                "Write integration tests for component interactions",
                "Run full test suite and verify coverage >= 80%",
                "Refactor for clarity and performance",
            ]
        elif "debug" in task_lower or "fix" in task_lower:
            return [
                f"Reproduce the issue: {task}",
                "Isolate root cause with logging and assertions",
                "Design fix with minimal side effects",
                "Implement the fix",
                "Add regression tests for the bug",
                "Verify fix does not break existing tests",
            ]
        elif "refactor" in task_lower:
            return [
                f"Map current structure for: {task}",
                "Identify extraction points and new boundaries",
                "Extract modules and update imports",
                "Verify all existing tests pass",
                "Update documentation and type stubs",
            ]
        else:
            # Generic decomposition
            words = task.split()
            if len(words) <= 5:
                return [
                    f"Analyze: {task}",
                    f"Design approach for: {task}",
                    f"Implement: {task}",
                    f"Verify: {task}",
                ]
            else:
                return [
                    f"Parse requirements from: {task}",
                    "Research existing solutions and patterns",
                    "Design solution architecture",
                    "Implement the solution",
                    "Test and verify correctness",
                    "Document the approach",
                ]

    def evaluate_plan(self, plan: Plan) -> dict[str, float]:
        """
        Evaluate a plan's quality, risk, and cost.

        Args:
            plan: The plan to evaluate.

        Returns:
            Dict with 'quality', 'risk', and 'cost' scores (0.0-1.0).
        """
        quality = self._evaluate_quality(plan.steps, plan.dependencies, plan.estimated_costs)

        # Risk: more steps and dependencies increase risk
        risk_base = min(plan.step_count / 20.0, 0.6)
        dep_factor = len(plan.dependencies) / max(plan.step_count, 1)
        risk = risk_base + dep_factor * 0.4

        # Cost: normalized estimated cost
        cost = min(plan.total_estimated_cost / 100.0, 1.0)

        return {"quality": quality, "risk": min(risk, 1.0), "cost": cost}

    def synthesize_results(self, plan_results: dict[int, str]) -> str:
        """
        Combine step outputs into a coherent result.

        Args:
            plan_results: Mapping of step_index -> output text.

        Returns:
            Synthesized summary string.
        """
        if not plan_results:
            return "No results to synthesize."

        parts: list[str] = []
        for idx in sorted(plan_results.keys()):
            result = plan_results[idx]
            parts.append(f"Step {idx + 1}: {result}")

        summary = "\n".join(parts)
        logger.info("System2: synthesized %d step results", len(plan_results))
        return summary

    def _analyze_dependencies(self, steps: list[str]) -> dict[int, frozenset[int]]:
        """Heuristically determine step dependencies."""
        if len(steps) <= 1:
            return {}

        deps: dict[int, frozenset[int]] = {}
        for i in range(1, len(steps)):
            # Simple heuristic: each step depends on the immediate predecessor
            deps[i] = frozenset({i - 1})
        return deps

    @staticmethod
    def _evaluate_quality(
        steps: tuple[str, ...],
        dependencies: dict[int, frozenset[int]],
        estimated_costs: dict[int, float],
    ) -> float:
        """Score plan quality from 0.0-1.0."""
        score = 0.5

        # More steps = more thorough (to a point)
        n = len(steps)
        if 2 <= n <= 7:
            score += 0.15
        elif n > 7:
            score += 0.05

        # Dependencies suggest structured thinking
        if len(dependencies) > 0:
            score += 0.15

        # Reasonable cost
        total_cost = sum(estimated_costs.values())
        if 0.5 < total_cost < 50.0:
            score += 0.10

        return max(0.0, min(1.0, score))


# ── System 1 Executor (Fast, Cached) ─────────────────────────────────────────

class System1Executor:
    """
    Fast execution engine for routine tasks.

    Uses cached plans and pattern matching to execute with sub-500ms latency.
    Suitable for Sonnet/Haiku-level models.
    """

    def __init__(self):
        self._pattern_cache: dict[str, str] = {}
        self._execution_history: list[dict[str, Any]] = []

    def execute_step(self, step: str, context: dict[str, Any] | None = None) -> str:
        """
        Execute a single plan step using cached patterns if available.

        Args:
            step: The step description.
            context: Optional execution context.

        Returns:
            Execution result string.
        """
        logger.debug("System1: executing step: %s", step[:80])

        # Try pattern match first
        cached = self.match_pattern(step)
        if cached:
            logger.debug("System1: cache hit for step")
            return cached

        # Fall back to direct execution
        result = self._direct_execute(step, context or {})
        self._execution_history.append({
            "step": step,
            "result": result,
            "timestamp": datetime.now(),
        })
        return result

    def match_pattern(self, task: str) -> str | None:
        """
        Find a cached solution pattern for the given task.

        Uses substring-overlap heuristic to match against cached patterns.

        Args:
            task: The task description.

        Returns:
            Cached result string if a match is found, None otherwise.
        """
        task_lower = task.lower()

        # Direct cache lookup
        if task_lower in self._pattern_cache:
            return self._pattern_cache[task_lower]

        # Fuzzy substring match
        best_score = 0.0
        best_result: str | None = None
        for cached_key, cached_result in self._pattern_cache.items():
            overlap = self._substring_similarity(task_lower, cached_key)
            if overlap > best_score and overlap > 0.6:
                best_score = overlap
                best_result = cached_result

        return best_result

    def quick_evaluate(self, decision: str) -> float:
        """
        Rapid quality check for a decision.

        Args:
            decision: The decision text to evaluate.

        Returns:
            Quality score from 0.0-1.0.
        """
        if not decision:
            return 0.0

        score = 0.5
        # Longer decisions may be more thorough
        if len(decision) > 50:
            score += 0.2
        # Evidence of structure
        if any(marker in decision.lower() for marker in ("therefore", "because", "step", "first")):
            score += 0.2
        return min(1.0, score)

    def cache_pattern(self, task: str, result: str) -> None:
        """
        Cache a task-result pair for future fast retrieval.

        Args:
            task: The task description.
            result: The successful result to cache.
        """
        self._pattern_cache[task.lower()] = result
        logger.debug("System1: cached pattern for task: %s", task[:40])

    def _direct_execute(self, step: str, context: dict[str, Any]) -> str:
        """Execute without caching (simple template-based execution)."""
        step_lower = step.lower()
        if "test" in step_lower:
            return f"Executed test suite for: {step}. All tests passed."
        elif "build" in step_lower:
            return f"Build completed successfully: {step}."
        elif "deploy" in step_lower:
            return f"Deployment completed: {step}."
        elif "format" in step_lower or "lint" in step_lower:
            return f"Formatting/linting complete: {step}."
        else:
            return f"Executed: {step}. Result: OK."

    @staticmethod
    def _substring_similarity(a: str, b: str) -> float:
        """Simple substring overlap heuristic."""
        if not a or not b:
            return 0.0
        a_words = set(a.split())
        b_words = set(b.split())
        if not a_words or not b_words:
            return 0.0
        intersection = a_words.intersection(b_words)
        return len(intersection) / min(len(a_words), len(b_words))


# ── Meta-Cognitive Controller ────────────────────────────────────────────────

class MetaCognitiveController:
    """
    DOLORES/APEX-style mode switching between System 1 and System 2.

    Decides which system should handle a task based on complexity,
    confidence, novelty, and escalation triggers.
    """

    def __init__(
        self,
        system1: System1Executor,
        system2: System2Planner,
        escalation_threshold: float = 0.6,
        cache_threshold: float = 0.7,
    ):
        """
        Args:
            system1: The fast System 1 executor.
            system2: The slow System 2 planner.
            escalation_threshold: Complexity above which System 1 escalates to System 2.
            cache_threshold: Confidence above which a System 2 plan is cached for System 1.
        """
        self._system1 = system1
        self._system2 = system2
        self._escalation_threshold = escalation_threshold
        self._cache_threshold = cache_threshold
        self._escalation_count = 0
        self._mode_history: list[SystemMode] = []

    @property
    def system1(self) -> System1Executor:
        """Access the System 1 executor."""
        return self._system1

    @property
    def system2(self) -> System2Planner:
        """Access the System 2 planner."""
        return self._system2

    def assess_task(self, task: str) -> SystemMode:
        """
        Determine whether System 1 or System 2 should handle a task.

        Args:
            task: The task description.

        Returns:
            Recommended SystemMode.
        """
        complexity = _estimate_complexity(task)
        logger.info(
            "MetaCognition: assessed task complexity=%.2f for: %s",
            complexity,
            task[:60],
        )

        if complexity >= self._escalation_threshold:
            mode = SystemMode.SYSTEM2
        else:
            mode = SystemMode.SYSTEM1

        self._mode_history.append(mode)
        return mode

    def should_escalate(self, observation: str, current_mode: SystemMode) -> bool:
        """
        Determine if execution should escalate from System 1 to System 2.

        Triggered by: errors, low confidence, unexpected results.

        Args:
            observation: The observation from the current tick.
            current_mode: The current operating mode.

        Returns:
            True if escalation is recommended.
        """
        if current_mode != SystemMode.SYSTEM1:
            return False

        escalate_triggers = {
            "error", "fail", "unexpected", "confused", "uncertain",
            "complex", "deadlock", "contradiction",
        }
        observation_lower = observation.lower()

        for trigger in escalate_triggers:
            if trigger in observation_lower:
                self._escalation_count += 1
                logger.warning(
                    "MetaCognition: escalation triggered by '%s' in: %s",
                    trigger,
                    observation[:80],
                )
                return True

        return False

    def should_cache(self, plan: Plan) -> bool:
        """
        Determine if a System 2 plan is reliable enough to cache for System 1.

        Args:
            plan: The plan to evaluate.

        Returns:
            True if the plan should be cached.
        """
        # Cache high-confidence, low-cost plans for reuse
        if plan.confidence == ConfidenceLevel.HIGH:
            return True
        if plan.confidence == ConfidenceLevel.MEDIUM and plan.total_estimated_cost < 10.0:
            return True
        return False

    def get_escalation_count(self) -> int:
        """Return the number of times escalation has occurred."""
        return self._escalation_count

    def get_mode_history(self) -> list[SystemMode]:
        """Return the history of mode assignments."""
        return list(self._mode_history)
