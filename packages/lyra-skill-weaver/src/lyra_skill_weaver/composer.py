"""Skill composition strategies: sequential, parallel, conditional, iterative, hybrid.

Implements different composition patterns for building skill chains
and provides a unified composer interface.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .exceptions import (
    CompositionError,
    SkillNotFoundError,
)
from .skill_weaver import (
    CompositionPattern,
    CompositionPlan,
    SkillRegistry,
    SkillStatus,
)

logger = logging.getLogger(__name__)


# ── Composition Nodes ──────────────────────────────────────────────────


@dataclass
class CompositionNode:
    """A node in a composition tree.

    Can represent a single skill, a sub-composition, or a control structure.
    """

    node_id: str
    skill_id: str | None = None
    pattern: CompositionPattern = CompositionPattern.SEQUENTIAL
    children: list[CompositionNode] = field(default_factory=list)
    condition: str | None = None  # For conditional nodes
    loop_max: int = 1  # For iterative nodes
    convergence_check: str | None = None  # For iterative nodes
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        """Whether this node is a terminal skill node."""
        return self.skill_id is not None and not self.children


@dataclass
class CompositionResult:
    """Result of executing a composition."""

    plan: CompositionPlan
    success: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    node_results: dict[str, Any] = field(default_factory=dict)


# ── Strategy Protocols ─────────────────────────────────────────────────


class CompositionCallback(Protocol):
    """Protocol for composition execution callbacks."""

    async def on_skill_start(self, skill_id: str, inputs: dict[str, Any]) -> None: ...
    async def on_skill_complete(self, skill_id: str, outputs: dict[str, Any]) -> None: ...
    async def on_skill_error(self, skill_id: str, error: Exception) -> None: ...


# ── Sequential Composer ────────────────────────────────────────────────


class SequentialComposer:
    """Builds sequential (pipeline) compositions.

    Skills are executed in order, with each skill's outputs feeding
    into the next skill's inputs.
    """

    def __init__(self, registry: SkillRegistry, max_chain_length: int = 20) -> None:
        self.registry = registry
        self.max_chain_length = max_chain_length

    def build(
        self,
        required_outputs: list[str],
        available_inputs: dict[str, Any] | None = None,
        context: dict[str, float] | None = None,
    ) -> CompositionPlan:
        """Build a sequential composition plan.

        Args:
            required_outputs: Desired final outputs.
            available_inputs: Available input data.
            context: Context features for skill selection.

        Returns:
            A sequential composition plan.
        """
        available_inputs = available_inputs or {}
        context = context or {}
        needed = set(required_outputs)
        chain: list[str] = []
        used: set[str] = set()

        while needed and len(chain) < self.max_chain_length:
            candidates = self._find_best_next(needed, context, used)
            if not candidates:
                break

            best_id, best_score = candidates[0]
            chain.append(best_id)
            used.add(best_id)

            skill = self.registry.get(best_id)
            if skill:
                # Update needed: add skill's inputs, remove its outputs
                needed -= {o.name for o in skill.outputs}
                for inp in skill.inputs:
                    if inp.name not in available_inputs:
                        needed.add(inp.name)

        if not chain:
            raise CompositionError(
                f"Cannot satisfy outputs: {required_outputs}"
            )

        total_cost = sum(
            self.registry.get(sid).estimated_cost
            for sid in chain if self.registry.get(sid)
        )
        total_latency = sum(
            self.registry.get(sid).avg_latency_ms
            for sid in chain if self.registry.get(sid)
        )

        return CompositionPlan(
            plan_id=f"seq_{int(time.time() * 1000)}",
            modules=chain,
            expected_outputs=required_outputs,
            estimated_cost=total_cost,
            estimated_latency_ms=total_latency,
            pattern=CompositionPattern.SEQUENTIAL,
            quality_score=self._compute_quality(chain),
        )

    def _find_best_next(
        self,
        needed: set[str],
        context: dict[str, float],
        used: set[str],
    ) -> list[tuple[str, float]]:
        """Find the best next skill for the chain."""
        scored: list[tuple[str, float]] = []
        for sid, skill in self.registry._by_id.items():
            if sid in used:
                continue
            if skill.metadata.status not in (SkillStatus.ACTIVE, SkillStatus.REGISTERED):
                continue

            produces = {o.name for o in skill.outputs}
            match = len(produces & needed)
            if match == 0:
                continue

            context_score = (
                sum(1 for k, v in context.items()
                    if skill.context_requirements.get(k, 0) <= v + 0.1)
                / max(len(skill.context_requirements), 1)
                if skill.context_requirements else 0.5
            )

            score = (
                match * 3.0
                + context_score * 1.5
                + skill.quality_score * 2.0
                - skill.estimated_cost * 0.3
                - skill.avg_latency_ms * 0.001
            )
            scored.append((sid, score))

        scored.sort(key=lambda x: -x[1])
        return scored

    def _compute_quality(self, chain: list[str]) -> float:
        """Compute aggregate quality score for a skill chain."""
        if not chain:
            return 0.0
        qualities = [
            self.registry.get(sid).quality_score
            for sid in chain if self.registry.get(sid)
        ]
        return sum(qualities) / len(qualities) if qualities else 0.0


# ── Parallel Composer ──────────────────────────────────────────────────


class ParallelComposer:
    """Builds parallel (fan-out/fan-in) compositions.

    Skills are executed concurrently, and their outputs are merged
    at a join point (fan-in).
    """

    def __init__(self, registry: SkillRegistry, max_parallel: int = 10) -> None:
        self.registry = registry
        self.max_parallel = max_parallel

    def build(
        self,
        required_outputs: list[str],
        context: dict[str, float] | None = None,
    ) -> CompositionPlan:
        """Build a parallel composition plan.

        Args:
            required_outputs: Outputs to produce in parallel.
            context: Context for skill selection.

        Returns:
            A parallel composition plan.
        """
        context = context or {}
        branches: list[str] = []
        used_outputs: set[str] = set()

        for output_name in required_outputs:
            if len(branches) >= self.max_parallel:
                break
            if output_name in used_outputs:
                continue

            producers = self.registry.find_by_output(output_name)
            if not producers:
                continue

            # Select best producer for this output
            best = max(
                producers,
                key=lambda s: s.quality_score * 2.0 - s.estimated_cost - s.avg_latency_ms * 0.001,
            )
            branches.append(best.skill_id)
            for o in best.outputs:
                used_outputs.add(o.name)

        if not branches:
            raise CompositionError(f"No skills found for parallel outputs: {required_outputs}")

        # Fan-out cost = sum, latency = max
        total_cost = sum(
            self.registry.get(sid).estimated_cost
            for sid in branches if self.registry.get(sid)
        )
        max_latency = max(
            (self.registry.get(sid).avg_latency_ms
             for sid in branches if self.registry.get(sid)),
            default=0.0,
        )

        return CompositionPlan(
            plan_id=f"par_{int(time.time() * 1000)}",
            modules=branches,
            expected_outputs=required_outputs,
            estimated_cost=total_cost,
            estimated_latency_ms=max_latency,
            pattern=CompositionPattern.PARALLEL,
            quality_score=self._compute_quality(branches),
        )

    def build_fanout_fanin(
        self,
        source_skill_id: str,
        required_outputs: list[str],
        context: dict[str, float] | None = None,
    ) -> CompositionPlan:
        """Build a fan-out/fan-in pattern: source -> [parallel workers] -> aggregator.

        Args:
            source_skill_id: The source skill that fans out.
            required_outputs: Desired final outputs.
            context: Context for selection.

        Returns:
            A fan-out/fan-in composition plan.
        """
        source = self.registry.get(source_skill_id)
        if source is None:
            raise SkillNotFoundError(source_skill_id)

        # Find workers that consume source outputs and produce needed outputs
        workers: list[str] = []
        for output_name in required_outputs:
            if len(workers) >= self.max_parallel:
                break
            producers = self.registry.find_by_output(output_name)
            for p in producers:
                if p.skill_id not in workers:
                    workers.append(p.skill_id)
                    break

        # Find an aggregator/fan-in skill
        aggregators = self.registry.find_by_capability(
            required_inputs={o.name for o in source.outputs} | set(required_outputs),
            required_outputs={"aggregated_result", "final_output"},
        )

        plan = CompositionPlan(
            plan_id=f"fan_{int(time.time() * 1000)}",
            modules=[source_skill_id] + workers + ([aggregators[0].skill_id] if aggregators else []),
            expected_outputs=required_outputs,
            estimated_cost=source.estimated_cost + sum(
                self.registry.get(sid).estimated_cost
                for sid in workers if self.registry.get(sid)
            ),
            estimated_latency_ms=source.avg_latency_ms + max(
                (self.registry.get(sid).avg_latency_ms
                 for sid in workers if self.registry.get(sid)),
                default=0.0,
            ),
            pattern=CompositionPattern.FANOUT,
            quality_score=self._compute_quality(workers),
        )
        return plan

    def _compute_quality(self, skills: list[str]) -> float:
        """Compute aggregate quality for parallel skills."""
        if not skills:
            return 0.0
        qualities = [
            self.registry.get(sid).quality_score
            for sid in skills if self.registry.get(sid)
        ]
        if not qualities:
            return 0.0
        # Parallel quality: harmonic mean (penalizes one bad skill)
        return len(qualities) / sum(1.0 / max(q, 0.01) for q in qualities)


# ── Conditional Composer ───────────────────────────────────────────────


class ConditionalComposer:
    """Builds conditional (if-then-else) compositions.

    Routes execution through different skill branches based on
    runtime conditions.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def build(
        self,
        condition: str,
        then_required: list[str],
        else_required: list[str],
        context: dict[str, float] | None = None,
    ) -> CompositionPlan:
        """Build a conditional composition.

        Args:
            condition: Description of the condition to evaluate.
            then_required: Outputs needed in the 'then' branch.
            else_required: Outputs needed in the 'else' branch.
            context: Context for skill selection.

        Returns:
            A conditional composition plan.
        """
        seq = SequentialComposer(self.registry)
        then_plan = seq.build(then_required, context=context)
        else_plan = seq.build(else_required, context=context)

        all_modules = list(dict.fromkeys(then_plan.modules + else_plan.modules))

        return CompositionPlan(
            plan_id=f"cond_{int(time.time() * 1000)}",
            modules=all_modules,
            expected_outputs=list(set(then_required + else_required)),
            estimated_cost=max(then_plan.estimated_cost, else_plan.estimated_cost),
            estimated_latency_ms=max(then_plan.estimated_latency_ms, else_plan.estimated_latency_ms),
            pattern=CompositionPattern.CONDITIONAL,
            quality_score=(then_plan.quality_score + else_plan.quality_score) / 2.0,
            metadata={
                "condition": condition,
                "then_branch": then_plan.modules,
                "else_branch": else_plan.modules,
            },
        )


# ── Iterative Composer ────────────────────────────────────────────────


class IterativeComposer:
    """Builds iterative (loop with convergence) compositions.

    Repeats a skill chain until a convergence criterion is met,
    with safeguards against infinite loops.
    """

    def __init__(
        self,
        registry: SkillRegistry,
        max_iterations: int = 10,
    ) -> None:
        self.registry = registry
        self.max_iterations = max_iterations

    def build(
        self,
        transform_skill_id: str,
        convergence_check: str,
        initial_input: dict[str, Any] | None = None,
    ) -> CompositionPlan:
        """Build an iterative composition.

        Args:
            transform_skill_id: Skill to apply repeatedly.
            convergence_check: Description of convergence criterion.
            initial_input: Initial input data.

        Returns:
            An iterative composition plan.
        """
        skill = self.registry.get(transform_skill_id)
        if skill is None:
            raise SkillNotFoundError(transform_skill_id)

        return CompositionPlan(
            plan_id=f"iter_{int(time.time() * 1000)}",
            modules=[transform_skill_id],
            expected_outputs=[o.name for o in skill.outputs],
            estimated_cost=skill.estimated_cost * self.max_iterations,
            estimated_latency_ms=skill.avg_latency_ms * self.max_iterations,
            pattern=CompositionPattern.ITERATIVE,
            quality_score=skill.quality_score,
            metadata={
                "max_iterations": self.max_iterations,
                "convergence_check": convergence_check,
            },
        )


# ── Hybrid Composer ───────────────────────────────────────────────────


class HybridComposer:
    """Builds hybrid compositions combining multiple patterns.

    Constructs complex composition trees that mix sequential, parallel,
    conditional, and iterative patterns as needed.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry
        self.seq = SequentialComposer(registry)
        self.par = ParallelComposer(registry)
        self.cond = ConditionalComposer(registry)
        self.iter = IterativeComposer(registry)

    def build(
        self,
        output_spec: dict[str, str],  # output_name -> pattern
        context: dict[str, float] | None = None,
    ) -> CompositionPlan:
        """Build a hybrid composition from an output specification.

        Args:
            output_spec: Maps output names to composition patterns.
            context: Context for skill selection.

        Returns:
            A hybrid composition plan.
        """
        context = context or {}
        all_modules: list[str] = []
        total_cost = 0.0
        max_latency = 0.0
        qualities: list[float] = []

        for output_name, pattern_str in output_spec.items():
            if pattern_str == "sequential":
                plan = self.seq.build([output_name], context=context)
            elif pattern_str == "parallel":
                plan = self.par.build([output_name], context=context)
            elif pattern_str == "conditional":
                plan = self.cond.build("auto", [output_name], [], context=context)
            else:
                plan = self.seq.build([output_name], context=context)

            all_modules.extend(plan.modules)
            total_cost += plan.estimated_cost
            max_latency = max(max_latency, plan.estimated_latency_ms)
            qualities.append(plan.quality_score)

        all_modules = list(dict.fromkeys(all_modules))  # Deduplicate

        return CompositionPlan(
            plan_id=f"hybrid_{int(time.time() * 1000)}",
            modules=all_modules,
            expected_outputs=list(output_spec.keys()),
            estimated_cost=total_cost,
            estimated_latency_ms=max_latency,
            pattern=CompositionPattern.HYBRID,
            quality_score=sum(qualities) / len(qualities) if qualities else 0.0,
            metadata={"output_spec": output_spec},
        )


# ── Master Composer ────────────────────────────────────────────────────


class MasterComposer:
    """Unified interface for all composition strategies.

    Selects the appropriate composer based on the desired pattern
    and provides a single entry point for building any composition.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry
        self._sequential = SequentialComposer(registry)
        self._parallel = ParallelComposer(registry)
        self._conditional = ConditionalComposer(registry)
        self._iterative = IterativeComposer(registry)
        self._hybrid = HybridComposer(registry)

    def compose(
        self,
        required_outputs: list[str],
        pattern: CompositionPattern = CompositionPattern.SEQUENTIAL,
        context: dict[str, float] | None = None,
        **kwargs: Any,
    ) -> CompositionPlan:
        """Build a composition using the specified pattern.

        Args:
            required_outputs: Desired outputs.
            pattern: Composition pattern to use.
            context: Context for selection.
            **kwargs: Additional pattern-specific arguments.

        Returns:
            A composition plan.
        """
        if pattern == CompositionPattern.SEQUENTIAL or pattern == CompositionPattern.PIPELINE:
            return self._sequential.build(required_outputs, context=context, **kwargs)
        elif pattern == CompositionPattern.PARALLEL:
            return self._parallel.build(required_outputs, context=context, **kwargs)
        elif pattern == CompositionPattern.CONDITIONAL:
            condition = kwargs.get("condition", "auto")
            else_outputs = kwargs.get("else_outputs", [])
            return self._conditional.build(condition, required_outputs, else_outputs, context=context)
        elif pattern == CompositionPattern.ITERATIVE:
            skill_id = kwargs.get("skill_id", "")
            check = kwargs.get("convergence_check", "auto")
            return self._iterative.build(skill_id, check)
        elif pattern == CompositionPattern.FANOUT:
            return self._parallel.build_fanout_fanin(
                kwargs.get("source_skill_id", ""),
                required_outputs,
                context=context,
            )
        elif pattern == CompositionPattern.HYBRID:
            output_spec = kwargs.get("output_spec", dict.fromkeys(required_outputs, "sequential"))
            return self._hybrid.build(output_spec, context=context)
        else:
            return self._sequential.build(required_outputs, context=context, **kwargs)

    def get_available_patterns(self) -> list[str]:
        """List available composition patterns."""
        return [p.name for p in CompositionPattern]

    @property
    def registry_stats(self) -> dict[str, Any]:
        """Get statistics about the underlying registry."""
        return {
            "total_skills": self.registry.skill_count,
            "composition_patterns": self.get_available_patterns(),
        }
