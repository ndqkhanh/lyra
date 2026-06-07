"""
Gradient-free reflective prompt evolution optimizer (GEPA-style).

Implements a GEPA-inspired evolutionary loop that works on any provider
(including closed models) because it operates at the prompt / skill level
rather than on model weights.

References
----------
- GEPA: Genetic-Pareto Evolutionary Prompt Optimisation
  gepa-ai/gepa, MIT License, arXiv:2507.19457
- SkillOpt: Validation-Gated Text Optimization for Large Language Model
  Skills — Microsoft Research, arXiv:2605.23904v2
- TF-TTCL: Training-Free Test-Time Contrastive Learning
  Findings ACL 2026, arXiv:2604.13552v1
- MetaAgent-X: End-to-End RL for Multi-Agent Workflow Optimization
  arXiv:2605.14212v1
"""

from __future__ import annotations

import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, NamedTuple

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# -- types ------------------------------------------------------------------
# ---------------------------------------------------------------------------


class EditType(Enum):
    """Type of edit applied during evolution."""

    PROMPT_REWRITE = "prompt_rewrite"
    STRATEGY_UPDATE = "strategy_update"
    CONSTRAINT_ADD = "constraint_add"
    CONSTRAINT_REMOVE = "constraint_remove"
    PARAMETER_TUNE = "parameter_tune"
    TOOL_ROUTINE_CHANGE = "tool_routine_change"
    MEMORY_UPDATE = "memory_update"


@dataclass(frozen=True)
class Gene:
    """Compact gene representation of a skill (~230 tokens).

    Based on GEP/skill2gep findings: compact control objects outperform
    documentation-heavy representations by +3.0 points (arXiv:2604.15097v2).

    Attributes:
        matching_signals: List of trigger patterns for this gene.
        summary: Short description of when and why this gene applies.
        strategy_steps: Ordered list of strategy steps.
        avoid_cues: Patterns or behaviours to avoid.
        constraints: Applicability constraints.
        edit_history: Tracking of evolution steps applied.
    """

    matching_signals: tuple[str, ...] = ()
    summary: str = ""
    strategy_steps: tuple[str, ...] = ()
    avoid_cues: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    edit_history: tuple[str, ...] = ()

    def to_prompt_section(self) -> str:
        """Render the gene as a compact instruction section for injection.

        Returns a ~230-token prompt section.
        """
        lines: list[str] = []
        if self.matching_signals:
            lines.append("WHEN: " + " | ".join(self.matching_signals))
        if self.summary:
            lines.append("SUMMARY: " + self.summary)
        if self.strategy_steps:
            lines.append("STEPS:")
            for step in self.strategy_steps:
                lines.append(f"  - {step}")
        if self.avoid_cues:
            lines.append("AVOID: " + "; ".join(self.avoid_cues))
        if self.constraints:
            lines.append("CONSTRAINTS: " + "; ".join(self.constraints))
        return "\n".join(lines)

    def with_edit(self, edit_description: str) -> Gene:
        """Return a new ``Gene`` with an appended edit history entry."""
        return Gene(
            matching_signals=self.matching_signals,
            summary=self.summary,
            strategy_steps=self.strategy_steps,
            avoid_cues=self.avoid_cues,
            constraints=self.constraints,
            edit_history=self.edit_history + (edit_description,),
        )


@dataclass(frozen=True)
class VariantResult:
    """Outcome of evaluating a single evolved variant.

    Attributes:
        gene: The evolved gene.
        variant_id: Unique identifier for this variant.
        score: Evaluation score (higher is better).
        regression: Fractional regression relative to incumbent (0.0 = no
            regression, negative = improvement, positive = regression).
        cost_usd: Monetary cost of the evaluation.
        latency_ms: Wall-clock time for the evaluation.
        metadata: Additional evaluation context.
    """

    gene: Gene
    variant_id: str
    score: float
    regression: float
    cost_usd: float
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passes_validation(self) -> bool:
        """Whether the variant passes the <= 1% regression threshold."""
        return self.regression <= 0.01


class EvolutionPhase(Enum):
    """Phase of the GEPA evolution loop."""

    INITIALISE = "initialise"
    GENERATE_VARIANTS = "generate_variants"
    EVALUATE = "evaluate"
    SELECT_WINNER = "select_winner"
    MUTATE = "mutate"
    VALIDATE = "validate"
    PROMOTE = "promote"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# -- mutator: cosine-scheduled edit budget ----------------------------------
# ---------------------------------------------------------------------------


@dataclass
class SkillOptMutator:
    """Produces mutated variants of a gene with cosine-scheduled edit budget.

    The edit budget follows a cosine schedule (SkillOpt — Microsoft Research):
    starts at ``L=4`` and decays to ``L=2`` over the evolution steps.

    A rejected-edit buffer prevents cyclic mutations.

    Reference
    ---------
    SkillOpt §3.2 — arXiv:2605.23904v2
    """

    initial_budget: int = 4
    final_budget: int = 2
    total_steps: int = 8
    _rejected_edits: set[str] = field(default_factory=set)

    @property
    def budget(self) -> int:
        """Current edit budget (cosine-scheduled). Unused in cold start.

        This property returns the starting budget. The full schedule is
        computed via ``budget_at_step(step)``.
        """
        return self.initial_budget

    def budget_at_step(self, step: int) -> int:
        """Compute cosine-scheduled edit budget at a given evolution step.

        Args:
            step: Current evolution step (0-indexed).

        Returns:
            Integer edit budget (clamped between ``final_budget`` and
            ``initial_budget``).
        """
        if self.total_steps <= 1:
            return self.initial_budget
        cosine = 0.5 * (1.0 + math.cos(math.pi * step / (self.total_steps - 1)))
        raw = self.final_budget + (self.initial_budget - self.final_budget) * cosine
        return max(self.final_budget, min(self.initial_budget, round(raw)))

    def mark_rejected(self, edit_description: str) -> None:
        """Add an edit description to the rejected-edit buffer.

        Args:
            edit_description: Description of the rejected edit.
        """
        self._rejected_edits.add(edit_description)

    def is_rejected(self, edit_description: str) -> bool:
        """Check whether this edit was previously rejected.

        Args:
            edit_description: Edit description to check.

        Returns:
            ``True`` if the edit was previously rejected.
        """
        return edit_description in self._rejected_edits

    def mutate(
        self,
        gene: Gene,
        step: int,
        generate_fn: Callable[[Gene, int, int], Gene] | None = None,
    ) -> Gene:
        """Produce a mutated variant of the gene.

        When a ``generate_fn`` is provided (real evolution path), it is
        called with the gene, budget, and step. Otherwise a simple
        random mutation is applied for testing / cold-start.

        Args:
            gene: The gene to mutate.
            step: Current evolution step.
            generate_fn: Optional LLM-driven generation function that
                produces a new gene given the existing gene and budget.

        Returns:
            A mutated ``Gene``.
        """
        budget = self.budget_at_step(step)

        if generate_fn is not None:
            return generate_fn(gene, budget, step)

        # Fallback: trivial random mutation for testing
        edits: list[str] = []
        current = gene.matching_signals
        if current and random.random() < 0.5:
            # Rotate a signal
            signals = list(current)
            if len(signals) > 1:
                signals[0], signals[-1] = signals[-1], signals[0]
            edits.append("rotated matching signals")
            return Gene(
                matching_signals=tuple(signals),
                summary=gene.summary,
                strategy_steps=gene.strategy_steps,
                avoid_cues=gene.avoid_cues,
                constraints=gene.constraints,
                edit_history=gene.edit_history + tuple(edits),
            )

        return gene


# ---------------------------------------------------------------------------
# -- evaluator (frozen, never co-evolves) -----------------------------------
# ---------------------------------------------------------------------------


class GeneEvaluator:
    """Frozen evaluator that scores gene variants on held-out tasks.

    A *frozen* evaluator means its evaluation logic and reference data
    never change during the optimisation loop. This prevents evaluator
    drift and reward hacking.

    Reference
    ---------
    Misevolve §4 — Shao et al., arXiv:2509.26354v2
    SkillOpt §2.4 — Microsoft Research
    """

    def __init__(
        self,
        held_out_tasks: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialise the evaluator.

        Args:
            held_out_tasks: List of evaluation tasks. Each task is a dict
                with ``query``, ``expected``, and ``weight`` keys.
        """
        self._tasks: list[dict[str, Any]] = held_out_tasks or []
        self._frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        """Whether the evaluator is frozen (immutable)."""
        return self._frozen

    def freeze(self) -> None:
        """Freeze the evaluator — no more tasks can be added."""
        self._frozen = True
        logger.info("gene evaluator frozen", task_count=len(self._tasks))

    def add_task(self, task: dict[str, Any]) -> None:
        """Add an evaluation task.

        Args:
            task: Dict with ``query``, ``expected``, and optionally
                ``weight``.

        Raises:
            RuntimeError: If the evaluator is frozen.
        """
        if self._frozen:
            raise RuntimeError(
                "Cannot add tasks to a frozen evaluator. "
                "Evaluator is immutable once frozen.",
            )
        self._tasks.append(task)

    def evaluate(self, gene: Gene) -> VariantResult:
        """Score a gene variant on held-out tasks.

        In cold-start mode (no tasks, no LLM runner), returns a
        placeholder score. In production this delegates to an LLM-based
        evaluation harness.

        Args:
            gene: The gene variant to evaluate.

        Returns:
            A ``VariantResult`` with the evaluation outcome.
        """
        if not self._tasks:
            # Cold-start: return a neutral evaluation
            return VariantResult(
                gene=gene,
                variant_id=f"v_{int(time.time())}",
                score=0.5,
                regression=0.0,
                cost_usd=0.0,
                latency_ms=0.0,
                metadata={"source": "cold_start"},
            )

        # Placeholder: in production this calls the LLM evaluation harness
        total_score = 0.0
        total_weight = 0.0
        for task in self._tasks:
            weight = task.get("weight", 1.0)
            total_score += weight * self._score_task(gene, task)
            total_weight += weight

        avg_score = total_score / max(total_weight, 1.0)
        return VariantResult(
            gene=gene,
            variant_id=f"v_{int(time.time())}_{random.randint(1000, 9999)}",
            score=avg_score,
            regression=0.0,
            cost_usd=0.001,
            latency_ms=50.0,
        )

    def _score_task(self, gene: Gene, task: dict[str, Any]) -> float:
        """Score a single task against a gene.

        Cold-start implementation: returns a random score in [0.5, 0.9].
        """
        _ = gene  # unused in cold-start
        return 0.5 + 0.4 * random.random()


# ---------------------------------------------------------------------------
# -- GEPA optimizer ---------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class GEPAOptimizer:
    """Gradient-free reflective prompt evolution optimizer.

    The evolution loop for each generation:

        1. **Generate variants** — Mutate the incumbent gene, generating
           ``N`` variants via the LLM.
        2. **Evaluate** — Score each variant on the frozen evaluator.
        3. **Select winner** — Pick the best variant that passes the
           validation gate (<= 1% regression vs. incumbent).
        4. **Mutate** — Apply cosine-scheduled mutation to the winner.
        5. **Validation gate** — Confirm the winner passes regression check.
        6. **Promote** — If accepted, the winner becomes the new incumbent.

    The loop is **gradient-free**: it works with any provider including
    closed models because it operates on prompt text, not model weights.

    References
    ----------
    GEPA (ICLR 2026 Oral) — arXiv:2507.19457
    SkillOpt (Microsoft Research) — arXiv:2605.23904v2
    """

    # The incumbent gene (current best)
    incumbent: Gene = field(default_factory=Gene)

    # Sub-components
    mutator: SkillOptMutator = field(default_factory=SkillOptMutator)
    evaluator: GeneEvaluator = field(default_factory=GeneEvaluator)

    # Configuration
    variants_per_generation: int = 4
    max_generations: int = 10
    regression_threshold: float = 0.01  # 1%
    warmup_steps: int = 2

    # State
    phase: EvolutionPhase = EvolutionPhase.INITIALISE
    generation: int = 0
    _history: list[tuple[int, Gene, VariantResult]] = field(default_factory=list)
    _best_score: float = 0.0
    _iteration_cost_usd: float = 0.0

    # Optional LLM-driven mutation and evaluation callables
    _mutate_fn: Callable[[Gene, int, int], Gene] | None = None
    _evaluate_fn: Callable[[Gene], VariantResult] | None = None

    def set_mutate_fn(
        self,
        fn: Callable[[Gene, int, int], Gene],
    ) -> None:
        """Set the LLM-driven mutation function.

        Args:
            fn: Callable ``(gene, budget, step) -> Gene``.
        """
        self._mutate_fn = fn

    def set_evaluate_fn(
        self,
        fn: Callable[[Gene], VariantResult],
    ) -> None:
        """Set the LLM-driven evaluation function.

        Args:
            fn: Callable ``(gene) -> VariantResult``.
        """
        self._evaluate_fn = fn

    def run_generation(self) -> VariantResult | None:
        """Execute one full generation of the evolution loop.

        Returns:
            The winning ``VariantResult`` if a valid variant is found,
            ``None`` otherwise.
        """
        if self.generation >= self.max_generations:
            logger.info("max generations reached", n=self.max_generations)
            self.phase = EvolutionPhase.COMPLETED
            return None

        self.phase = EvolutionPhase.GENERATE_VARIANTS
        self.generation += 1

        logger.info(
            "evolution generation starting",
            generation=self.generation,
            incumbent_score=round(self._best_score, 4),
        )

        # 1. Generate variants
        variants: list[tuple[Gene, str]] = []
        for i in range(self.variants_per_generation):
            mutated = self.mutator.mutate(
                self.incumbent,
                self.generation,
                generate_fn=self._mutate_fn,
            )
            variant_id = f"gen{self.generation}_v{i}"
            variants.append((mutated, variant_id))

        # 2. Evaluate each variant
        self.phase = EvolutionPhase.EVALUATE
        results: list[VariantResult] = []

        for gene, variant_id in variants:
            if self._evaluate_fn is not None:
                result = self._evaluate_fn(gene)
            else:
                result = self.evaluator.evaluate(gene)

            # Compute regression against incumbent
            if self._best_score > 0:
                regression = (self._best_score - result.score) / max(self._best_score, 1e-8)
            else:
                regression = 0.0

            result = VariantResult(
                gene=result.gene,
                variant_id=variant_id,
                score=result.score,
                regression=max(regression, 0.0),
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
                metadata=result.metadata,
            )
            results.append(result)
            self._iteration_cost_usd += result.cost_usd

            logger.info(
                "variant evaluated",
                variant_id=variant_id,
                score=round(result.score, 4),
                regression=round(result.regression, 6),
            )

        # 3. Select winner — best scoring variant that passes validation
        self.phase = EvolutionPhase.SELECT_WINNER
        passing = [r for r in results if r.passes_validation]
        if not passing:
            # No variant passes: keep incumbent, log rejection
            rejected_ids = [r.variant_id for r in results]
            logger.warning(
                "no variant passes validation gate",
                generation=self.generation,
                rejected=rejected_ids,
            )
            # Add to rejected edit buffer
            for r in results:
                if r.gene.edit_history:
                    self.mutator.mark_rejected(r.gene.edit_history[-1])

            self._history.append(
                (self.generation, self.incumbent, results[-1]),
            )
            self.phase = EvolutionPhase.MUTATE
            return None

        winner = max(passing, key=lambda r: r.score)

        # 4. Validation gate (<= 1% regression)
        self.phase = EvolutionPhase.VALIDATE
        if not winner.passes_validation and self._best_score > 0:
            logger.warning(
                "winner fails validation gate",
                regression=round(winner.regression, 6),
                threshold=self.regression_threshold,
            )
            self.mutator.mark_rejected(
                winner.gene.edit_history[-1] if winner.gene.edit_history else "unknown",
            )
            self._history.append(
                (self.generation, self.incumbent, winner),
            )
            self.phase = EvolutionPhase.MUTATE
            return None

        # 5. Promote winner
        self.phase = EvolutionPhase.PROMOTE
        self.incumbent = winner.gene
        self._best_score = winner.score
        self._history.append((self.generation, self.incumbent, winner))

        logger.info(
            "variant promoted",
            generation=self.generation,
            variant_id=winner.variant_id,
            score=round(winner.score, 4),
            regression=round(winner.regression, 6),
        )

        self.phase = EvolutionPhase.MUTATE
        return winner

    def run(self, steps: int | None = None) -> list[VariantResult | None]:
        """Run the evolution loop for a given number of generations.

        Args:
            steps: Number of generations to run. Defaults to
                ``max_generations``.

        Returns:
            List of generation results (one per generation).
        """
        steps = steps if steps is not None else self.max_generations
        results: list[VariantResult | None] = []
        for _ in range(steps):
            result = self.run_generation()
            results.append(result)
            if self.phase == EvolutionPhase.COMPLETED:
                break
        self.phase = EvolutionPhase.COMPLETED if self.phase != EvolutionPhase.FAILED else EvolutionPhase.FAILED
        return results

    @property
    def best_score(self) -> float:
        """The highest score achieved by any promoted variant."""
        return self._best_score

    @property
    def iteration_cost(self) -> float:
        """Total monetary cost of all evaluations in USD."""
        return self._iteration_cost_usd

    @property
    def generation_count(self) -> int:
        """Number of generations completed."""
        return self.generation

    @property
    def history(self) -> list[tuple[int, Gene, VariantResult]]:
        """Full evolution history as ``(generation, gene, result)`` tuples."""
        return list(self._history)

    def to_dict(self) -> dict[str, Any]:
        """Serialize optimizer state to a JSON-compatible dictionary."""
        return {
            "phase": self.phase.value,
            "generation": self.generation,
            "best_score": self._best_score,
            "iteration_cost_usd": self._iteration_cost_usd,
            "max_generations": self.max_generations,
            "variants_per_generation": self.variants_per_generation,
            "regression_threshold": self.regression_threshold,
            "edit_budget_initial": self.mutator.initial_budget,
            "edit_budget_final": self.mutator.final_budget,
            "history_count": len(self._history),
            "incumbent": {
                "summary": self.incumbent.summary,
                "signal_count": len(self.incumbent.matching_signals),
                "strategy_count": len(self.incumbent.strategy_steps),
                "edit_count": len(self.incumbent.edit_history),
            },
        }
