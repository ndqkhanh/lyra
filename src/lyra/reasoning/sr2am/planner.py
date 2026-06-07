"""
Self-Regulated Simulative Planning (SR2AM) — Core implementation.

Architecture
------------
SR2AM implements a three-system planner for AGI agents:

- **System I (Reactive)** returns fast template-based plans for low-complexity
  tasks, consuming a fraction of the token budget.
- **System II (Simulative)** runs chain-of-thought reasoning augmented with a
  causal world model that iteratively simulates and adjusts each plan step.
- **System III (Configurator)** classifies incoming task complexity and chooses
  the appropriate system and planning depth. It learns from execution traces
  via a lightweight reinforcement signal, shifting internal thresholds over
  time so the system becomes more efficient without sacrificing quality.

Learning mechanism
------------------
``learn_from_trace()`` adjusts an internal ``_threshold_offset`` using the
configured ``learning_rate``:

- Successful reactive plans reinforce the fast path (offset decreases).
- Failed reactive plans penalise the fast path (offset increases).
- Simulative outcomes also contribute, at a smaller magnitude.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ── System Level Enum ──────────────────────────────────────────────────────


class SystemLevel(str, Enum):
    """The three planning systems in the SR2AM architecture."""

    REACTIVE = "reactive"
    """System I — fast template-based planning, minimal compute."""

    SIMULATIVE = "simulative"
    """System II — world-model simulation with causal CoT reasoning."""

    CONFIGURATOR = "configurator"
    """System III — learned classifier that selects system and depth."""


# ── Data Models (all frozen for immutability) ─────────────────────────────


@dataclass(frozen=True)
class TaskComplexity:
    """Estimated complexity of a planning task.

    Attributes:
        score: Overall complexity from 1 (trivial) to 10 (extremely complex).
        num_dependencies: Number of identified dependency relationships.
        ambiguity_level: Estimated ambiguity in [0, 1]; higher means more
            underspecified.
        requires_multi_step: Whether the task likely needs multiple steps.
        domain: Detected problem domain (e.g. "backend", "frontend", "general").
    """

    score: float
    num_dependencies: int
    ambiguity_level: float
    requires_multi_step: bool
    domain: str

    def __post_init__(self) -> None:
        """Validate complexity range constraints."""
        if not 1.0 <= self.score <= 10.0:
            raise ValueError(f"score must be in [1.0, 10.0], got {self.score}")
        if not 0.0 <= self.ambiguity_level <= 1.0:
            raise ValueError(
                f"ambiguity_level must be in [0.0, 1.0], got {self.ambiguity_level}"
            )


@dataclass(frozen=True)
class PlanningConfig:
    """Configuration produced by System III (Configurator).

    Attributes:
        system_level: Which planning system to use.
        max_depth: Maximum reasoning / plan steps allowed.
        simulation_rounds: Number of world-model rollouts (System II only).
        token_budget: Maximum tokens the planner may consume.
        temperature: Sampling temperature for generative steps.
        allow_fast_path: Whether System III may skip to System I.
    """

    system_level: SystemLevel
    max_depth: int
    simulation_rounds: int
    token_budget: int
    temperature: float = 0.7
    allow_fast_path: bool = True

    def __post_init__(self) -> None:
        """Validate configuration bounds."""
        if self.max_depth < 1:
            raise ValueError(f"max_depth must be >= 1, got {self.max_depth}")
        if self.simulation_rounds < 0:
            raise ValueError(
                f"simulation_rounds must be >= 0, got {self.simulation_rounds}"
            )
        if self.token_budget < 1:
            raise ValueError(
                f"token_budget must be >= 1, got {self.token_budget}"
            )
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"temperature must be in [0.0, 2.0], got {self.temperature}"
            )


@dataclass(frozen=True)
class PlanNode:
    """A single step in a generated plan.

    Attributes:
        step_id: Unique identifier for this step (e.g. ``"step-1"``).
        action: The action to perform (e.g. ``"analyze"``, ``"implement"``).
        expected_outcome: Description of what this step should accomplish.
        dependencies: Step IDs that must complete before this one.
        confidence: Model's confidence in this step succeeding [0, 1].
        system_used: Which system generated this node.
    """

    step_id: str
    action: str
    expected_outcome: str
    dependencies: tuple[str, ...] = ()
    confidence: float = 0.9
    system_used: SystemLevel = SystemLevel.REACTIVE

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )


@dataclass(frozen=True)
class ExecutionTrace:
    """Record of plan execution used for learning.

    Attributes:
        plan_nodes: The nodes that formed the plan.
        actual_outcomes: Observed outcomes for each step, in order.
        deviations: Descriptions of any plan-vs-execution deviations.
        tokens_used: Actual tokens consumed during execution.
        success: Whether the overall plan succeeded.
    """

    plan_nodes: tuple[PlanNode, ...] = ()
    actual_outcomes: tuple[str, ...] = ()
    deviations: tuple[str, ...] = ()
    tokens_used: int = 0
    success: bool = False


@dataclass(frozen=True)
class PlanningStats:
    """Aggregate statistics across many planning runs.

    Attributes:
        total_plans: Number of plans generated.
        reactive_count: Number of plans that used System I.
        simulative_count: Number of plans that used System II.
        avg_tokens_per_plan: Mean tokens consumed per plan.
        tokens_saved_vs_full: Percentage of tokens saved compared to always
            running full simulation.
        success_rate: Fraction of plans that succeeded.
        avg_complexity: Mean complexity score across all plans.
    """

    total_plans: int = 0
    reactive_count: int = 0
    simulative_count: int = 0
    avg_tokens_per_plan: float = 0.0
    tokens_saved_vs_full: float = 0.0
    success_rate: float = 0.0
    avg_complexity: float = 0.0


# ── SR2AM Planner ──────────────────────────────────────────────────────────


# Keyword maps used by the complexity classifier.  Defined at module level for
# readability and to avoid re-allocation on every invocation.
_HIGH_COMPLEXITY_KWS: dict[str, int] = {
    "refactor": 3,
    "architecture": 3,
    "redesign": 3,
}
_MED_COMPLEXITY_KWS: dict[str, int] = {
    "design": 2,
    "implement": 2,
    "migrate": 2,
    "optimise": 2,
}
_LOW_COMPLEXITY_KWS: dict[str, int] = {
    "debug": 1,
    "update": 1,
    "add": 1,
}
_NEGATIVE_COMPLEXITY_KWS: dict[str, int] = {
    "fix typo": -2,
    "rename": -2,
    "typo": -2,
    "cosmetic": -2,
}
_MULTI_STEP_KWS: tuple[str, ...] = (
    "first",
    "then",
    "after",
    "before",
    "finally",
)
_DOMAIN_SIGNALS: dict[str, tuple[str, ...]] = {
    "backend": ("api", "endpoint", "route", "server", "database", "query", "schema"),
    "frontend": ("ui", "component", "page", "view", "template", "css", "html"),
    "data": ("database", "query", "schema", "pipeline", "etl", "dataset"),
    "testing": ("test", "coverage", "assert", "mock", "fixture"),
    "devops": ("deploy", "ci", "cd", "config", "docker", "kubernetes"),
    "security": ("auth", "permission", "encrypt", "token", "oauth"),
}

# Default thresholds for System III configurator.
_LOW_COMPLEXITY_MAX: float = 3.0
_MED_COMPLEXITY_MAX: float = 6.0

# Simulation step actions and outcomes used by plan_simulative.
_SIM_STEP_ACTIONS: tuple[str, ...] = (
    "decompose_task",
    "analyze_dependencies",
    "design_solution",
    "implement_component",
    "verify_integrity",
    "validate_output",
    "refine_approach",
    "finalize",
)
_SIM_STEP_OUTCOMES: tuple[str, ...] = (
    "Requirements decomposed into actionable sub-tasks",
    "Dependencies mapped and ordered",
    "Solution design completed with causal validation",
    "Component implemented with correctness verification",
    "System integrity confirmed",
    "Output validated against requirements",
    "Approach refined based on simulation feedback",
    "Plan finalized and ready for execution",
)


class SR2AMPlanner:
    """Self-Regulated Simulative Planning agent.

    Implements the three-system SR2AM architecture.  The planner classifies
    task complexity, selects the appropriate system (I or II), generates a
    plan, and learns from execution traces to improve future decisions.

    Args:
        learning_rate: Step size for threshold adjustment during learning.
    """

    def __init__(self, learning_rate: float = 0.01) -> None:
        self.learning_rate: float = learning_rate

        # — Cumulative statistics —
        self._total_plans: int = 0
        self._reactive_plans: int = 0
        self._simulative_plans: int = 0
        self._total_tokens_used: int = 0
        self._tokens_if_full_simulated: int = 0
        self._successful_plans: int = 0
        self._failed_plans: int = 0
        self._total_complexity: float = 0.0

        # Learned offset applied to complexity thresholds (System III).  A
        # positive offset makes the planner more conservative (prefers
        # simulative); a negative offset makes it more aggressive (prefers
        # reactive).
        self._threshold_offset: float = 0.0

    # ── Public API ─────────────────────────────────────────────────────────

    def classify_complexity(self, task_description: str) -> TaskComplexity:
        """Estimate task complexity using keyword and structure heuristics.

        Heuristics used:
        - Domain keywords with weighted scores (refactor/architecture +3,
          fix-typo/rename -2, etc.)
        - File-mention count each contributing +0.5
        - Multi-step language indicators contribute +2 if present
        - Ambiguity is estimated inversely from clarity signals

        Args:
            task_description: Natural-language task description.

        Returns:
            A ``TaskComplexity`` with score clamped to [1, 10].
        """
        text = task_description.lower()

        # ── Keyword scoring ────────────────────────────────────────────
        keyword_score = 0.0

        for kw, val in _HIGH_COMPLEXITY_KWS.items():
            if kw in text:
                keyword_score += val
        for kw, val in _MED_COMPLEXITY_KWS.items():
            if kw in text:
                keyword_score += val
        for kw, val in _LOW_COMPLEXITY_KWS.items():
            if kw in text:
                keyword_score += val
        for kw, val in _NEGATIVE_COMPLEXITY_KWS.items():
            if kw in text:
                keyword_score += val

        # ── File mentions ──────────────────────────────────────────────
        file_mentions = len(
            re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z]{2,4}\b", text)
        )
        keyword_score += file_mentions * 0.5

        # ── Multi-step indicators ──────────────────────────────────────
        multi_step_count = sum(1 for kw in _MULTI_STEP_KWS if kw in text)
        if multi_step_count > 0:
            keyword_score += 2.0

        # Clamp to [1, 10].
        score = max(1.0, min(10.0, keyword_score))

        # ── Derived fields ─────────────────────────────────────────────
        num_dependencies = file_mentions + multi_step_count

        clarity_signals = len(
            re.findall(
                r"\b(specifically|exactly|clearly|precisely|must|always|never)\b",
                text,
            )
        )
        total_words = max(len(text.split()), 1)
        ambiguity_level = max(0.0, min(1.0, 1.0 - (clarity_signals / total_words * 10)))

        requires_multi_step = multi_step_count > 0 or score >= 4.0

        domain = self._detect_domain(text)

        return TaskComplexity(
            score=round(score, 2),
            num_dependencies=num_dependencies,
            ambiguity_level=round(ambiguity_level, 2),
            requires_multi_step=requires_multi_step,
            domain=domain,
        )

    def configure_planning(
        self,
        complexity: TaskComplexity,
        budget: int = 8000,
    ) -> PlanningConfig:
        """System III configurator — decide system level and depth.

        Applies the learned ``_threshold_offset`` to adapt boundaries:

        ============ ============ =========== ================= ============
        Score Range  System Level Max Depth   Simulation Rounds Budget frac
        ============ ============ =========== ================= ============
        1 – 3        REACTIVE     2           0                 10 %
        4 – 6        SIMULATIVE   4           2                 50 %
        7 – 10       SIMULATIVE   8           5                 100 %
        ============ ============ =========== ================= ============

        The learned offset shifts these boundaries so that repeated failures
        on low-complexity tasks push the planner toward using System II.

        Args:
            complexity: Pre-computed complexity estimate.
            budget: Token budget to allocate.

        Returns:
            A ``PlanningConfig`` tuned to the estimated complexity.
        """
        adjusted_score = complexity.score + self._threshold_offset
        efficiency_ratio = complexity.num_dependencies / max(complexity.score, 0.1)
        use_fast_path = complexity.ambiguity_level < 0.5 and efficiency_ratio < 0.5

        if adjusted_score <= _LOW_COMPLEXITY_MAX:
            return PlanningConfig(
                system_level=SystemLevel.REACTIVE,
                max_depth=2,
                simulation_rounds=0,
                token_budget=max(1, int(budget * 0.1)),
                allow_fast_path=use_fast_path,
            )

        if adjusted_score <= _MED_COMPLEXITY_MAX:
            return PlanningConfig(
                system_level=SystemLevel.SIMULATIVE,
                max_depth=4,
                simulation_rounds=2,
                token_budget=max(1, int(budget * 0.5)),
                allow_fast_path=use_fast_path,
            )

        return PlanningConfig(
            system_level=SystemLevel.SIMULATIVE,
            max_depth=8,
            simulation_rounds=5,
            token_budget=max(1, budget),
            allow_fast_path=False,
        )

    def plan_reactive(self, task: str) -> list[PlanNode]:
        """System I — fast template-based plan for simple tasks.

        Returns 2-3 ``PlanNode``\\ s with high confidence (≥0.90).  The plan
        structure adapts slightly to the task type (fix, rename, or general).

        Args:
            task: Task description.

        Returns:
            Ordered list of plan steps.
        """
        text = task.lower()
        steps: list[PlanNode] = []

        # Step 1 — always analyse.
        steps.append(
            PlanNode(
                step_id="step-1",
                action="analyze",
                expected_outcome=f"Understand the requirements of: {task[:80]}",
                dependencies=(),
                confidence=0.92,
                system_used=SystemLevel.REACTIVE,
            )
        )

        # Step 2 — action varies by task type.
        if "fix" in text or "bug" in text:
            action = "patch"
            outcome = "Apply the targeted fix to the identified issue"
        elif "rename" in text or "typo" in text:
            action = "modify"
            outcome = "Make the straightforward rename or correction"
        elif "add" in text:
            action = "create"
            outcome = "Add the requested new content or feature"
        else:
            action = "execute"
            outcome = "Carry out the required task change"

        steps.append(
            PlanNode(
                step_id="step-2",
                action=action,
                expected_outcome=outcome,
                dependencies=("step-1",),
                confidence=0.90,
                system_used=SystemLevel.REACTIVE,
            )
        )

        # Step 3 — always verify.
        steps.append(
            PlanNode(
                step_id="step-3",
                action="verify",
                expected_outcome="Confirm correctness and completeness of the change",
                dependencies=("step-2",),
                confidence=0.91,
                system_used=SystemLevel.REACTIVE,
            )
        )

        return steps

    def plan_simulative(
        self,
        task: str,
        config: PlanningConfig,
    ) -> list[PlanNode]:
        """System II — world-model simulation with causal CoT reasoning.

        Generates a plan up to ``config.max_depth`` steps.  After building
        the initial plan, runs ``config.simulation_rounds`` rounds of causal
        simulation where each step's confidence is adjusted based on the
        simulated health of its dependencies.

        Args:
            task: Task description.
            config: Planning configuration from System III configurator.

        Returns:
            Simulated and adjusted plan steps.
        """
        task.lower()
        nodes: list[PlanNode] = []

        # ── Build initial plan ─────────────────────────────────────────
        # Step 1: Parse requirements (always the root when max_depth >= 1).
        if config.max_depth >= 1:
            nodes.append(
                PlanNode(
                    step_id="step-1",
                    action="parse_requirements",
                    expected_outcome=(
                        "Complete understanding of requirements and constraints"
                    ),
                    dependencies=(),
                    confidence=0.80,
                    system_used=SystemLevel.SIMULATIVE,
                )
            )

            # Step 2: Design approach (depends on step 1, added when max_depth >= 2).
            if config.max_depth >= 2:
                nodes.append(
                    PlanNode(
                        step_id="step-2",
                        action="design_approach",
                        expected_outcome=(
                            "Coherent design approach aligned with requirements"
                        ),
                        dependencies=("step-1",),
                        confidence=0.75,
                        system_used=SystemLevel.SIMULATIVE,
                    )
                )

        # Steps 3 .. max_depth: derived from template pool.
        for i in range(3, config.max_depth + 1):
            idx = i - 3
            action: str = (
                _SIM_STEP_ACTIONS[idx]
                if idx < len(_SIM_STEP_ACTIONS)
                else f"step_{i}"
            )
            expected_outcome: str = (
                _SIM_STEP_OUTCOMES[idx]
                if idx < len(_SIM_STEP_OUTCOMES)
                else f"Step {i} completed successfully"
            )

            # Depend on previous step plus any relevant earlier steps.
            deps = (f"step-{i - 1}",)
            confidence = self._compute_step_confidence(i, config.max_depth)

            nodes.append(
                PlanNode(
                    step_id=f"step-{i}",
                    action=action,
                    expected_outcome=expected_outcome,
                    dependencies=deps,
                    confidence=confidence,
                    system_used=SystemLevel.SIMULATIVE,
                )
            )

        # ── Simulation rounds ──────────────────────────────────────────
        for round_num in range(config.simulation_rounds):
            nodes = self._simulate_round(nodes, round_num, config.max_depth)

        return nodes

    def plan(
        self,
        task: str,
        budget: int = 8000,
    ) -> tuple[list[PlanNode], PlanningConfig]:
        """Main entry point — classify, configure, and generate a plan.

        Workflow:
        1. ``classify_complexity`` — estimate the task difficulty.
        2. ``configure_planning`` — System III decides system + depth.
        3. ``plan_reactive`` or ``plan_simulative`` — generate the plan.
        4. Update internal statistics.

        Args:
            task: Task description to plan for.
            budget: Token budget for the planner (default 8000).

        Returns:
            A tuple of ``(plan_steps, config_used)``.
        """
        complexity = self.classify_complexity(task)
        config = self.configure_planning(complexity, budget)

        if config.system_level == SystemLevel.REACTIVE:
            nodes = self.plan_reactive(task)
            self._reactive_plans += 1
            # If we used the fast path, "full simulation" cost is estimated
            # as the mid-range budget.
            self._tokens_if_full_simulated += int(budget * 0.5)
        else:
            nodes = self.plan_simulative(task, config)
            self._simulative_plans += 1
            # We paid the simulative cost — no savings for this run.
            self._tokens_if_full_simulated += config.token_budget

        # Estimated tokens consumed for statistics.
        self._total_tokens_used += config.token_budget
        self._total_plans += 1
        self._total_complexity += complexity.score

        logger.info(
            "SR2AM plan | system=%s complexity=%.1f steps=%d budget=%d",
            config.system_level.value,
            complexity.score,
            len(nodes),
            config.token_budget,
        )

        return nodes, config

    def learn_from_trace(self, trace: ExecutionTrace) -> None:
        """Update System III thresholds based on execution outcome.

        Applies a lightweight reinforcement signal:

        - **Reactive + success** → reduce offset (reinforce fast path).
        - **Reactive + failure** → increase offset (penalise fast path).
        - **Simulative + success** → slightly reduce offset.
        - **Simulative + failure** → increase offset more cautiously.

        The offset is clamped to [-3, 3] and shifts complexity boundaries
        for the configurator.

        Args:
            trace: Execution trace containing outcome, tokens, and system
                information.
        """
        self._total_tokens_used += trace.tokens_used

        if trace.success:
            self._successful_plans += 1
        else:
            self._failed_plans += 1

        # Determine primary system from the trace.
        used_reactive = any(
            n.system_used == SystemLevel.REACTIVE for n in trace.plan_nodes
        )

        if used_reactive:
            if trace.success:
                self._threshold_offset -= self.learning_rate * 0.5
            else:
                self._threshold_offset += self.learning_rate * 2.0
        else:
            if trace.success:
                self._threshold_offset -= self.learning_rate * 0.2
            else:
                self._threshold_offset += self.learning_rate * 1.0

        # Clamp offset to prevent runaway.
        self._threshold_offset = max(-3.0, min(3.0, self._threshold_offset))

        logger.debug(
            "SR2AM learn | success=%s used_reactive=%s offset=%.3f",
            trace.success,
            used_reactive,
            self._threshold_offset,
        )

    def get_stats(self) -> dict[str, float | int]:
        """Return aggregate performance statistics.

        Returns:
            Dictionary with keys matching ``PlanningStats`` field names:
            ``total_plans``, ``reactive_plans``, ``simulative_plans``,
            ``avg_tokens_per_plan``, ``tokens_saved_vs_full``,
            ``success_rate``, ``avg_complexity``.
        """
        total = max(self._total_plans, 1)

        avg_tokens = self._total_tokens_used / total

        tokens_saved = 0.0
        if self._tokens_if_full_simulated > 0:
            tokens_saved = (
                (self._tokens_if_full_simulated - self._total_tokens_used)
                / self._tokens_if_full_simulated
                * 100.0
            )

        completed = self._successful_plans + self._failed_plans
        success_rate = self._successful_plans / max(completed, 1)
        avg_complexity = self._total_complexity / total

        return {
            "total_plans": self._total_plans,
            "reactive_plans": self._reactive_plans,
            "simulative_plans": self._simulative_plans,
            "avg_tokens_per_plan": round(avg_tokens, 2),
            "tokens_saved_vs_full": round(tokens_saved, 2),
            "success_rate": round(success_rate, 3),
            "avg_complexity": round(avg_complexity, 2),
        }

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _detect_domain(text: str) -> str:
        """Identify problem domain from keyword signals in *text*."""
        best_domain = "general"
        max_matches = 0

        for domain, keywords in _DOMAIN_SIGNALS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > max_matches:
                max_matches = matches
                best_domain = domain

        return best_domain

    @staticmethod
    def _compute_step_confidence(step_number: int, max_depth: int) -> float:
        """Estimate confidence for a simulation step based on position.

        Earlier steps in a deep plan have lower confidence (more unknowns)
        while later steps benefit from accumulated information.
        """
        progress = step_number / max_depth
        # Start at 0.60 and climb toward 0.90.
        base = 0.60 + progress * 0.30
        return round(min(1.0, base), 3)

    @staticmethod
    def _simulate_round(
        nodes: list[PlanNode],
        round_num: int,
        max_depth: int,
    ) -> list[PlanNode]:
        """Run one round of world-model simulation over *nodes*.

        For each node, examines dependency confidences and adjusts the
        node's own confidence accordingly.  Simulation round index adds a
        small random-like perturbation to prevent converging on a single
        equilibrium.
        """
        node_map = {n.step_id: n for n in nodes}
        updated: list[PlanNode] = []

        for node in nodes:
            # Check dependency health.
            weak_deps = sum(
                1
                for dep_id in node.dependencies
                if dep_id in node_map and node_map[dep_id].confidence < 0.4
            )

            # Apply adjustment.
            if weak_deps > 0:
                adjustment = -0.1 * weak_deps
            elif node.confidence < 0.9:
                # Mild boost for stable but uncertain steps.
                adjustment = 0.03
            else:
                adjustment = 0.0

            # Round-based perturbation: confidence oscillates slightly so the
            # model can explore different decision points across rounds.
            perturbation = math.sin((round_num + 1) * node.confidence * math.pi) * 0.02

            new_confidence = max(0.0, min(1.0, node.confidence + adjustment + perturbation))

            updated.append(
                PlanNode(
                    step_id=node.step_id,
                    action=node.action,
                    expected_outcome=node.expected_outcome,
                    dependencies=node.dependencies,
                    confidence=round(new_confidence, 3),
                    system_used=node.system_used,
                )
            )

        return updated
