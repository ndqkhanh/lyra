"""Consensus Router — Multi-model consensus routing for high-stakes decisions.

Routes critical tasks to multiple models in parallel, combines their
verdicts via configurable strategies, and detects/escales dissent.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from .dissent_detector import (
    DissentDetector,
    DissentReport,
    DissentSeverity,
)
from .verdict_combiner import (
    CombinedVerdict,
    CombineStrategy,
    ModelVerdict,
    VerdictCombiner,
)

logger = logging.getLogger(__name__)


class ConsensusMode(StrEnum):
    """Routing modes for the consensus router."""

    SINGLE_BEST = "single_best"      # Route to one model only (fast)
    DUAL_VERIFY = "dual_verify"      # Two models, escalate on disagreement
    MAJORITY_QUORUM = "majority_quorum"  # Three models, majority vote
    FULL_CONSENSUS = "full_consensus"    # All eligible models, weighted vote


class ConsensusOutcome(StrEnum):
    """Outcome of a consensus routing operation."""

    CONSENSUS_REACHED = "consensus_reached"
    MAJORITY_ACCEPTED = "majority_accepted"
    TIE_BREAKER_USED = "tie_breaker_used"
    ESCALATED = "escalated"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class ConsensusResult:
    """Complete result of a consensus routing operation."""

    outcome: ConsensusOutcome
    combined_verdict: CombinedVerdict
    dissent_report: DissentReport
    consensus_mode: ConsensusMode
    session_id: str
    models_queried: int
    models_succeeded: int
    models_failed: int
    total_cost_usd: float
    total_latency_ms: float
    retries: int = 0
    escalation_reason: str = ""


@dataclass
class ConsensusSession:
    """Tracks a consensus routing session across retries."""

    session_id: str
    task: str
    mode: ConsensusMode
    created_at: float = field(default_factory=time.monotonic)
    verdicts: list[ModelVerdict] = field(default_factory=list)
    iterations: int = 0
    resolved: bool = False


class ConsensusRouter:
    """Routes tasks to multiple models and combines verdicts via consensus.

    Provides escalating consensus strategies:
    - SINGLE_BEST: Fast path, one model
    - DUAL_VERIFY: Two models, escalate on disagreement
    - MAJORITY_QUORUM: Three models, majority vote
    - FULL_CONSENSUS: All eligible models, weighted combination

    Usage::

        router = ConsensusRouter(model_executor=my_executor)
        result = await router.route(
            "Implement authentication middleware",
            mode=ConsensusMode.DUAL_VERIFY,
            eligible_models=["sonnet", "opus"],
        )
        if result.outcome == ConsensusOutcome.BLOCKED:
            await request_human_review(result)
    """

    def __init__(
        self,
        model_executor=None,
        min_models_for_consensus: int = 2,
        max_retries: int = 2,
        escalation_threshold: DissentSeverity = DissentSeverity.HIGH,
        default_mode: ConsensusMode = ConsensusMode.DUAL_VERIFY,
    ) -> None:
        self._executor = model_executor  # Callable: (task, model_name) -> ModelVerdict
        self.min_models_for_consensus = min_models_for_consensus
        self.max_retries = max_retries
        self.escalation_threshold = escalation_threshold
        self.default_mode = default_mode

        self._combiner = VerdictCombiner()
        self._dissent_detector = DissentDetector()
        self._sessions: dict[str, ConsensusSession] = {}
        self._history: list[ConsensusResult] = []

    async def route(
        self,
        task: str,
        mode: ConsensusMode | None = None,
        eligible_models: list[str] | None = None,
        require_consensus: bool = False,
    ) -> ConsensusResult:
        """Route a task through the consensus pipeline.

        Args:
            task: The task description/prompt
            mode: Consensus mode to use
            eligible_models: List of model names to consider
            require_consensus: If True, escalate until consensus is reached

        Returns:
            ConsensusResult with the final verdict and metadata
        """
        mode = mode or self.default_mode
        eligible_models = eligible_models or ["haiku", "sonnet", "opus"]

        session_id = str(uuid.uuid4())[:12]
        session = ConsensusSession(
            session_id=session_id,
            task=task,
            mode=mode,
        )
        self._sessions[session_id] = session

        models_to_query = self._select_models(mode, eligible_models)
        min_required = 1 if mode == ConsensusMode.SINGLE_BEST else self.min_models_for_consensus

        for iteration in range(self.max_retries + 1):
            session.iterations = iteration

            verdicts = await self._execute_models(task, models_to_query)
            session.verdicts = verdicts  # Replace, don't accumulate
            successful = [v for v in verdicts if v.success]

            if len(successful) < min_required:
                if iteration < self.max_retries:
                    continue
                return self._build_result(
                    session, CombinedVerdict(
                        final_output="",
                        strategy=CombineStrategy.BEST_OF_N,
                        agreement_score=0.0,
                        confidence=0.0,
                        participating_models=len(successful),
                        dissenting_models=len(verdicts) - len(successful),
                        total_cost_usd=sum(v.cost_usd for v in verdicts),
                        total_latency_ms=sum(v.latency_ms for v in verdicts),
                    ),
                    ConsensusOutcome.FAILED,
                    retries=iteration,
                )

            # Combine verdicts
            if mode == ConsensusMode.SINGLE_BEST:
                combined = self._combiner.combine(successful, CombineStrategy.BEST_OF_N)
            elif mode == ConsensusMode.DUAL_VERIFY:
                combined = self._combiner.combine(successful, CombineStrategy.CASCADE)
            elif mode == ConsensusMode.MAJORITY_QUORUM:
                combined = self._combiner.combine(successful, CombineStrategy.MAJORITY_VOTE)
            else:
                combined = self._combiner.combine(successful, CombineStrategy.WEIGHTED_VOTE)

            # Detect dissent
            dissent = self._dissent_detector.detect_from_verdicts(verdicts)

            # Determine outcome
            outcome, should_continue = self._evaluate_outcome(
                combined, dissent, mode, require_consensus, iteration
            )

            if not should_continue:
                result = self._build_result(
                    session, combined, outcome,
                    retries=iteration,
                    escalation_reason=(
                        dissent.recommended_action
                        if outcome in (ConsensusOutcome.ESCALATED, ConsensusOutcome.BLOCKED)
                        else ""
                    ),
                )
                session.resolved = True
                self._history.append(result)
                return result

            # Add a tie-breaker model for next iteration
            if dissent.needs_more_models:
                extra_models = [m for m in eligible_models if m not in models_to_query]
                if extra_models:
                    models_to_query.append(extra_models[0])

        # Max retries exceeded
        combined = self._combiner.combine(
            [v for v in session.verdicts if v.success],
            CombineStrategy.BEST_OF_N,
        )
        return self._build_result(
            session, combined, ConsensusOutcome.ESCALATED,
            retries=self.max_retries,
            escalation_reason="Max retries exceeded without consensus",
        )

    def route_sync(
        self,
        task: str,
        mode: ConsensusMode | None = None,
        eligible_models: list[str] | None = None,
    ) -> ConsensusResult:
        """Synchronous wrapper for route()."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.route(task, mode, eligible_models))
        else:
            raise RuntimeError(
                "Cannot use route_sync inside a running event loop. Use await route() instead."
            )

    def get_session(self, session_id: str) -> ConsensusSession | None:
        """Get a consensus session by ID."""
        return self._sessions.get(session_id)

    def get_history(self) -> list[ConsensusResult]:
        """Return consensus routing history."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Get aggregate statistics on consensus routing."""
        if not self._history:
            return {
                "total_routes": 0,
                "consensus_rate": 0.0,
                "avg_models_per_route": 0.0,
                "avg_cost_per_route": 0.0,
                "escalation_rate": 0.0,
            }

        total = len(self._history)
        consensus_reached = sum(
            1 for r in self._history
            if r.outcome in (ConsensusOutcome.CONSENSUS_REACHED, ConsensusOutcome.MAJORITY_ACCEPTED)
        )
        escalated = sum(
            1 for r in self._history
            if r.outcome in (ConsensusOutcome.ESCALATED, ConsensusOutcome.BLOCKED)
        )
        avg_models = sum(r.models_queried for r in self._history) / total
        avg_cost = sum(r.total_cost_usd for r in self._history) / total

        return {
            "total_routes": total,
            "consensus_rate": consensus_reached / total,
            "avg_models_per_route": round(avg_models, 1),
            "avg_cost_per_route": round(avg_cost, 6),
            "escalation_rate": escalated / total,
            "dissent_rate": self._dissent_detector.get_dissent_rate(),
        }

    def clear(self) -> None:
        """Clear all sessions and history."""
        self._sessions.clear()
        self._history.clear()
        self._dissent_detector.clear()

    # ── Private ────────────────────────────────────────────────────

    @staticmethod
    def _select_models(
        mode: ConsensusMode, eligible: list[str]
    ) -> list[str]:
        """Select which models to query based on consensus mode."""
        if mode == ConsensusMode.SINGLE_BEST:
            # Pick the strongest available model
            tier_order = ["opus", "sonnet", "haiku"]
            for tier in tier_order:
                if any(tier in m.lower() for m in eligible):
                    return [next(m for m in eligible if tier in m.lower())]
            return [eligible[0]] if eligible else []

        if mode == ConsensusMode.DUAL_VERIFY:
            return eligible[:2] if len(eligible) >= 2 else eligible[:1]

        if mode == ConsensusMode.MAJORITY_QUORUM:
            return eligible[:3] if len(eligible) >= 3 else eligible[:2]

        # FULL_CONSENSUS
        return list(eligible)

    async def _execute_models(
        self, task: str, model_names: list[str]
    ) -> list[ModelVerdict]:
        """Execute a task across multiple models."""
        if self._executor is None:
            return self._simulate_execution(task, model_names)

        results: list[ModelVerdict] = []
        for name in model_names:
            try:
                start = time.monotonic()
                output, confidence = await self._executor(task, name)
                elapsed = (time.monotonic() - start) * 1000

                tier = self._infer_tier(name)
                # Estimate cost based on tier
                cost_map = {
                    "agentic": 0.10, "premium": 0.05, "standard": 0.01,
                    "fast": 0.005, "haiku": 0.001, "local_slm": 0.0,
                }
                cost = cost_map.get(tier, 0.01)

                results.append(ModelVerdict(
                    model_name=name,
                    model_tier=tier,
                    output=output,
                    confidence=confidence,
                    latency_ms=elapsed,
                    cost_usd=cost,
                ))
            except Exception as e:
                logger.error(f"Model {name} failed: {e}")
                results.append(ModelVerdict(
                    model_name=name,
                    model_tier=self._infer_tier(name),
                    output="",
                    confidence=0.0,
                    latency_ms=0.0,
                    cost_usd=0.0,
                    success=False,
                    error_message=str(e),
                ))

        return results

    def _simulate_execution(
        self, task: str, model_names: list[str]
    ) -> list[ModelVerdict]:
        """Simulate model execution when no executor is configured (for testing)."""
        results: list[ModelVerdict] = []
        responses = {
            "haiku": ("Implement the requested functionality with error handling and tests", 0.7),
            "sonnet": ("Implement the requested functionality with error handling and comprehensive tests", 0.85),
            "opus": ("Implement the requested functionality with error handling, comprehensive tests, and full documentation", 0.95),
        }

        for name in model_names:
            key = name.lower()
            matched = "sonnet"
            for k in responses:
                if k in key:
                    matched = k
                    break

            output, confidence = responses.get(matched, responses["sonnet"])
            tier = self._infer_tier(name)

            results.append(ModelVerdict(
                model_name=name,
                model_tier=tier,
                output=output,
                confidence=confidence,
                latency_ms=100.0,
                cost_usd=0.01,
            ))

        return results

    @staticmethod
    def _severity_rank(severity: DissentSeverity) -> int:
        """Convert severity to numeric rank for comparison."""
        ranks = {
            DissentSeverity.NONE: 0,
            DissentSeverity.LOW: 1,
            DissentSeverity.MEDIUM: 2,
            DissentSeverity.HIGH: 3,
            DissentSeverity.CRITICAL: 4,
        }
        return ranks.get(severity, 0)

    @staticmethod
    def _infer_tier(model_name: str) -> str:
        """Infer model tier from its name."""
        name = model_name.lower()
        if "opus" in name or "pro" in name:
            return "premium"
        if "sonnet" in name or "gpt-4o" in name:
            return "standard"
        if "haiku" in name or "flash" in name or "mini" in name:
            return "haiku"
        if "deepseek" in name or "lite" in name:
            return "fast"
        return "standard"

    def _evaluate_outcome(
        self,
        combined: CombinedVerdict,
        dissent: DissentReport,
        mode: ConsensusMode,
        require_consensus: bool,
        iteration: int,
    ) -> tuple[ConsensusOutcome, bool]:
        """Evaluate the consensus outcome and decide whether to continue.

        Returns (outcome, should_continue_iterating).
        """
        if dissent.severity == DissentSeverity.CRITICAL:
            return ConsensusOutcome.BLOCKED, False

        if dissent.severity == DissentSeverity.NONE:
            return ConsensusOutcome.CONSENSUS_REACHED, False

        if combined.agreement_score >= 0.8:
            return ConsensusOutcome.CONSENSUS_REACHED, False

        if combined.agreement_score >= 0.6 and not require_consensus:
            return ConsensusOutcome.MAJORITY_ACCEPTED, False

        if self._severity_rank(dissent.severity) >= self._severity_rank(self.escalation_threshold):
            if require_consensus and iteration < self.max_retries:
                return ConsensusOutcome.ESCALATED, True
            return ConsensusOutcome.ESCALATED, False

        # Minor dissent, try once more
        if iteration == 0 and mode == ConsensusMode.DUAL_VERIFY:
            return ConsensusOutcome.TIE_BREAKER_USED, True

        return ConsensusOutcome.MAJORITY_ACCEPTED, False

    def _build_result(
        self,
        session: ConsensusSession,
        combined: CombinedVerdict,
        outcome: ConsensusOutcome,
        retries: int = 0,
        escalation_reason: str = "",
    ) -> ConsensusResult:
        """Build a ConsensusResult from session data."""
        all_verdicts = session.verdicts
        successful = [v for v in all_verdicts if v.success]

        dissent = self._dissent_detector.detect_from_verdicts(all_verdicts)

        return ConsensusResult(
            outcome=outcome,
            combined_verdict=combined,
            dissent_report=dissent,
            consensus_mode=session.mode,
            session_id=session.session_id,
            models_queried=len(all_verdicts),
            models_succeeded=len(successful),
            models_failed=len(all_verdicts) - len(successful),
            total_cost_usd=sum(v.cost_usd for v in all_verdicts),
            total_latency_ms=sum(v.latency_ms for v in all_verdicts),
            retries=retries,
            escalation_reason=escalation_reason,
        )
