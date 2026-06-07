"""Meta-Harness Optimization Loop.

Outer-loop system that searches over Lyra's own harness code to
identify bottlenecks, propose improvements, validate them against
a test suite, and deploy optimisations.

Phase 13.4 — Meta-Harness: Self-Referential Harness Optimizer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    """Generate a unique candidate identifier."""
    return uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HarnessComponent(Enum):
    """Components of the Lyra harness that can be optimised.

    Values:
        AGENT_LOOP: The main agent execution loop.
        TOOL_KERNEL: Tool invocation and routing kernel.
        MEMORY_SYSTEM: Memory storage, retrieval, and consolidation.
        ROUTER: Model and strategy router.
        VERIFIER: Output verification and validation.
        SAFETY_LAYER: Safety and guardrail systems.
        SKILL_REGISTRY: Skill loading and management.
        FLEET_ORCHESTRATOR: Multi-agent fleet orchestration.
    """

    AGENT_LOOP = auto()
    TOOL_KERNEL = auto()
    MEMORY_SYSTEM = auto()
    ROUTER = auto()
    VERIFIER = auto()
    SAFETY_LAYER = auto()
    SKILL_REGISTRY = auto()
    FLEET_ORCHESTRATOR = auto()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodeCandidate:
    """A proposed improvement to a harness component.

    Attributes:
        candidate_id: Unique identifier for this proposal.
        component: The harness component being modified.
        file_path: Path to the source file being changed.
        proposed_change: Description of the diff/patch to apply.
        rationale: Reasoning behind the proposed change.
        expected_improvement: Estimated improvement in performance points.
        risk_level: Estimated risk of regression (0.0 = safe, 1.0 = high risk).
        validated: Whether the change passed validation.
    """

    candidate_id: str = field(default_factory=_new_id)
    component: HarnessComponent = HarnessComponent.AGENT_LOOP
    file_path: str = ""
    proposed_change: str = ""
    rationale: str = ""
    expected_improvement: float = 0.0
    risk_level: float = 0.0
    validated: bool = False

    def __post_init__(self) -> None:
        if self.expected_improvement < 0:
            raise ValueError(
                f"expected_improvement must be non-negative, "
                f"got {self.expected_improvement}"
            )
        if not 0.0 <= self.risk_level <= 1.0:
            raise ValueError(
                f"risk_level must be in [0, 1], got {self.risk_level}"
            )

    @property
    def expected_value(self) -> float:
        """Risk-adjusted expected value of the improvement."""
        return self.expected_improvement * (1.0 - self.risk_level)


@dataclass(frozen=True)
class OptimizationResult:
    """The outcome of deploying a code optimisation.

    Attributes:
        candidate: The ``CodeCandidate`` that was evaluated.
        actual_improvement: Measured improvement in performance points.
        tokens_saved_pct: Percentage of tokens saved (0–100).
        regression_detected: Whether a regression was detected.
        deployed: Whether the change was deployed.
    """

    candidate: CodeCandidate
    actual_improvement: float = 0.0
    tokens_saved_pct: float = 0.0
    regression_detected: bool = False
    deployed: bool = False

    def __post_init__(self) -> None:
        if self.actual_improvement < 0:
            raise ValueError(
                f"actual_improvement must be non-negative, "
                f"got {self.actual_improvement}"
            )
        if not 0.0 <= self.tokens_saved_pct <= 100.0:
            raise ValueError(
                f"tokens_saved_pct must be in [0, 100], "
                f"got {self.tokens_saved_pct}"
            )


# ---------------------------------------------------------------------------
# Meta-Harness Optimizer
# ---------------------------------------------------------------------------


class MetaHarnessOptimizer:
    """Self-referential harness optimisation loop.

    Analyses execution traces to find bottlenecks in the Lyra harness,
    proposes improvements, validates them against a test suite, and
    ranks results by expected improvement.

    Usage::

        optimizer = MetaHarnessOptimizer()
        traces = [
            {"component": "AGENT_LOOP", "token_usage": 5000, ...},
        ]
        results = optimizer.optimize(traces, test_suite=["test_agent.py"])
    """

    def __init__(self) -> None:
        self._proposals: list[CodeCandidate] = []
        self._results: list[OptimizationResult] = []
        self._deployed: list[OptimizationResult] = []

    # ------------------------------------------------------------------
    # Bottleneck analysis
    # ------------------------------------------------------------------

    def analyze_bottlenecks(
        self,
        traces: list[dict[str, Any]],
    ) -> dict[HarnessComponent, float]:
        """Score components by bottleneck severity from trace data.

        Analyses execution traces and assigns a bottleneck score (0–1)
        to each component based on token usage, failure rates, and
        latency.

        Args:
            traces: List of execution trace dicts. Each trace should
                contain keys ``component`` (str matching a
                ``HarnessComponent`` name), ``token_usage`` (int),
                ``failure_rate`` (float 0–1), and ``latency_ms`` (float).

        Returns:
            Mapping of ``HarnessComponent`` to bottleneck severity (0–1).
        """
        component_scores: dict[str, list[float]] = {}

        for trace in traces:
            comp_name = trace.get("component", "AGENT_LOOP")
            token_usage = float(trace.get("token_usage", 0))
            failure_rate = float(trace.get("failure_rate", 0.0))
            latency_ms = float(trace.get("latency_ms", 0.0))

            # Normalise each metric to a 0–1 scale and combine
            token_score = min(1.0, token_usage / 10_000)
            latency_score = min(1.0, latency_ms / 5_000)
            severity = max(
                failure_rate,
                token_score * 0.3 + latency_score * 0.3 + failure_rate * 0.4,
            )

            if comp_name not in component_scores:
                component_scores[comp_name] = []
            component_scores[comp_name].append(severity)

        result: dict[HarnessComponent, float] = {}
        for comp in HarnessComponent:
            scores = component_scores.get(comp.name, [])
            result[comp] = (
                sum(scores) / len(scores) if scores else 0.0
            )

        logger.debug(
            "Bottleneck analysis: %s",
            {k.name: round(v, 3) for k, v in sorted(result.items(), key=lambda x: -x[1])[:5]},
        )

        return result

    # ------------------------------------------------------------------
    # Proposal generation
    # ------------------------------------------------------------------

    def propose_improvements(
        self,
        bottlenecks: dict[HarnessComponent, float],
        top_k: int = 5,
    ) -> list[CodeCandidate]:
        """Generate improvement proposals for the worst bottlenecks.

        Produces a heuristic set of improvement candidates for the
        components with the highest bottleneck scores.

        Args:
            bottlenecks: Component-to-severity mapping from
                ``analyze_bottlenecks``.
            top_k: Maximum number of proposals to generate.

        Returns:
            List of ``CodeCandidate`` proposals.
        """
        # Sort by severity descending and take top_k
        sorted_bottlenecks = sorted(
            bottlenecks.items(), key=lambda x: -x[1]
        )[:top_k]

        proposals: list[CodeCandidate] = []

        for component, severity in sorted_bottlenecks:
            if severity < 0.01:
                continue

            proposal = self._generate_proposal(component, severity)
            proposals.append(proposal)

        self._proposals.extend(proposals)

        logger.info(
            "Generated %d improvement proposal(s) (top_k=%d)",
            len(proposals),
            top_k,
        )

        return proposals

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_candidate(
        self,
        candidate: CodeCandidate,
        test_suite: list[str],
    ) -> CodeCandidate:
        """Run a proposed change against a test suite for validation.

        This is a **stub** implementation. In production, this would
        execute the test suite with the proposed change applied and
        measure the actual outcome.

        Args:
            candidate: The ``CodeCandidate`` to validate.
            test_suite: List of test identifiers or paths.

        Returns:
            A new ``CodeCandidate`` with ``validated`` set and an
            updated ``risk_level`` based on simulated test results.
        """
        # Simulated validation logic
        passed = 0
        total = len(test_suite) if test_suite else 1

        for _ in test_suite:
            # Stub: 90% pass rate
            import random as _random
            if _random.random() < 0.9:
                passed += 1

        pass_rate = passed / total
        # Lower pass rate = higher risk
        estimated_risk = max(0.0, 1.0 - pass_rate)
        # Blend with original risk estimate
        blended_risk = (candidate.risk_level + estimated_risk) / 2.0

        return CodeCandidate(
            candidate_id=candidate.candidate_id,
            component=candidate.component,
            file_path=candidate.file_path,
            proposed_change=candidate.proposed_change,
            rationale=candidate.rationale,
            expected_improvement=candidate.expected_improvement,
            risk_level=round(blended_risk, 4),
            validated=pass_rate >= 0.5,  # Validated if majority pass
        )

    # ------------------------------------------------------------------
    # Full optimisation cycle
    # ------------------------------------------------------------------

    def optimize(
        self,
        traces: list[dict[str, Any]],
        test_suite: list[str],
    ) -> list[OptimizationResult]:
        """Run the full optimisation cycle.

        Steps:
            1. Analyse traces to find bottlenecks.
            2. Propose improvements for top bottlenecks.
            3. Validate proposals against the test suite.
            4. Rank by expected risk-adjusted value.
            5. Return results sorted by actual improvement.

        Args:
            traces: Execution trace data for bottleneck analysis.
            test_suite: Test identifiers/paths for validation.

        Returns:
            List of ``OptimizationResult`` sorted by improvement
            (descending).
        """
        # Step 1: Analyse
        bottlenecks = self.analyze_bottlenecks(traces)

        # Step 2: Propose
        proposals = self.propose_improvements(bottlenecks)

        # Step 3: Validate
        results: list[OptimizationResult] = []
        for proposal in proposals:
            validated = self.validate_candidate(proposal, test_suite)

            if not validated.validated:
                logger.info(
                    "Candidate %s failed validation, skipping",
                    validated.candidate_id,
                )
                continue

            # Step 4: Estimate actual impact (stub)
            actual_improvement = validated.expected_improvement * (
                1.0 - validated.risk_level
            )
            tokens_saved = self.estimate_token_savings(validated)
            regression = validated.risk_level > 0.3

            result = OptimizationResult(
                candidate=validated,
                actual_improvement=round(actual_improvement, 4),
                tokens_saved_pct=round(tokens_saved, 2),
                regression_detected=regression,
                deployed=True,  # Stub: deploy all validated changes
            )
            results.append(result)

        # Step 5: Sort by improvement descending
        results.sort(key=lambda r: -r.actual_improvement)

        self._results.extend(results)
        self._deployed.extend(
            [r for r in results if r.deployed and not r.regression_detected]
        )

        logger.info(
            "Optimisation cycle complete: %d result(s), "
            "%.2f avg improvement",
            len(results),
            sum(r.actual_improvement for r in results) / max(len(results), 1),
        )

        return results

    # ------------------------------------------------------------------
    # Token savings estimation
    # ------------------------------------------------------------------

    def estimate_token_savings(
        self,
        candidate: CodeCandidate,
    ) -> float:
        """Estimate the percentage of tokens saved by a proposed change.

        Uses a heuristic based on the component type and change scope.

        Args:
            candidate: The ``CodeCandidate`` to estimate.

        Returns:
            Estimated token savings percentage (0–100).
        """
        base_savings: dict[HarnessComponent, float] = {
            HarnessComponent.AGENT_LOOP: 15.0,
            HarnessComponent.TOOL_KERNEL: 10.0,
            HarnessComponent.MEMORY_SYSTEM: 25.0,
            HarnessComponent.ROUTER: 12.0,
            HarnessComponent.VERIFIER: 8.0,
            HarnessComponent.SAFETY_LAYER: 5.0,
            HarnessComponent.SKILL_REGISTRY: 10.0,
            HarnessComponent.FLEET_ORCHESTRATOR: 20.0,
        }

        savings = base_savings.get(candidate.component, 10.0)

        # Reduce by risk level (higher risk = less certain savings)
        savings *= 1.0 - (candidate.risk_level * 0.5)

        return max(0.0, savings)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate optimisation statistics.

        Returns:
            Dict with keys: ``components_analyzed``,
            ``proposals_generated``, ``validated``, ``deployed``,
            ``avg_improvement``, ``total_tokens_saved``.
        """
        components_analyzed = len(HarnessComponent)

        validated_count = sum(1 for r in self._results if r.candidate.validated)
        deployed_count = len(self._deployed)

        avg_improvement = (
            sum(r.actual_improvement for r in self._results)
            / max(len(self._results), 1)
        )
        total_tokens_saved = sum(
            r.tokens_saved_pct for r in self._results
        )

        return {
            "components_analyzed": components_analyzed,
            "proposals_generated": len(self._proposals),
            "validated": validated_count,
            "deployed": deployed_count,
            "avg_improvement": round(avg_improvement, 4),
            "total_tokens_saved": round(total_tokens_saved, 2),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _generate_proposal(
        self,
        component: HarnessComponent,
        severity: float,
    ) -> CodeCandidate:
        """Generate a heuristic improvement proposal for a component."""
        proposals_map: dict[HarnessComponent, tuple[str, str, str, float, float]] = {
            HarnessComponent.AGENT_LOOP: (
                "src/lyra_core/agent_loop.py",
                "Refactor main loop to batch tool calls and reduce per-step overhead",
                "Batching reduces repeated dispatch overhead and token waste "
                "from redundant context reconstruction",
                2.5,
                0.15,
            ),
            HarnessComponent.TOOL_KERNEL: (
                "src/lyra_core/tool_kernel.py",
                "Add parallel tool execution with dependency-aware scheduling",
                "Sequential tool calls inflate latency; parallel execution "
                "with dependency resolution reduces wall-clock time",
                1.8,
                0.25,
            ),
            HarnessComponent.MEMORY_SYSTEM: (
                "src/lyra_memory/core.py",
                "Introduce tiered memory with LRU eviction and compressed summaries",
                "Unbounded memory growth increases token usage; tiered storage "
                "keeps only relevant context in the active window",
                3.2,
                0.10,
            ),
            HarnessComponent.ROUTER: (
                "src/lyra_router/router.py",
                "Add cost-cascading fallback with early-exit on confidence threshold",
                "Current router always queries expensive models; early-exit "
                "at high confidence saves tokens without quality loss",
                2.0,
                0.20,
            ),
            HarnessComponent.VERIFIER: (
                "src/lyra_verification/verifier.py",
                "Cache verification results and skip redundant re-verification",
                "Identical outputs verified multiple times; a content-hash "
                "cache eliminates redundant verification calls",
                1.2,
                0.10,
            ),
            HarnessComponent.SAFETY_LAYER: (
                "src/lyra_safety/guardrails.py",
                "Optimise safety checks with pre-filtering and batch classification",
                "Per-call safety checks duplicate computation; pre-filtering "
                "reduces classification load by 40%",
                0.8,
                0.05,
            ),
            HarnessComponent.SKILL_REGISTRY: (
                "src/lyra_skills/registry.py",
                "Lazy-load skills on first use instead of eager registration",
                "Loading all skills at startup wastes memory; lazy loading "
                "reduces cold-start token consumption",
                1.5,
                0.08,
            ),
            HarnessComponent.FLEET_ORCHESTRATOR: (
                "src/lyra_orchestration/fleet.py",
                "Implement shared context cache across parallel agent workers",
                "Each agent independently rebuilds context; a shared cache "
                "reduces redundant context construction by up to 60%",
                2.8,
                0.18,
            ),
        }

        file_path, change, rationale, expected_imp, risk = proposals_map[
            component
        ]

        # Scale expected improvement by severity
        scaled_improvement = expected_imp * severity
        scaled_risk = risk * (1.0 + 0.5 * (1.0 - severity))

        return CodeCandidate(
            candidate_id=_new_id(),
            component=component,
            file_path=file_path,
            proposed_change=change,
            rationale=rationale,
            expected_improvement=round(scaled_improvement, 4),
            risk_level=round(min(1.0, scaled_risk), 4),
        )


__all__ = [
    "CodeCandidate",
    "HarnessComponent",
    "MetaHarnessOptimizer",
    "OptimizationResult",
]
