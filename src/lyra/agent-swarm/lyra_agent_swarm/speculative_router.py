"""Speculative Execution Router — parallel model dispatch with voting and tie-breaking.

Implements speculative execution for LLM routing:
  - Parallel dispatch to multiple model candidates
  - Result comparison via Jaccard token similarity
  - Weighted voting across candidate outputs
  - Tie-breaking by confidence then capability score
  - Cost-aware dispatch strategies (quality-first, cost-optimized, parallel-verified)
  - Timeout management and candidate filtering
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class DispatchStrategy(StrEnum):
    """How to dispatch a task to model candidates."""

    SINGLE_BEST = "single_best"
    PARALLEL_VERIFIED = "parallel_verified"
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_FIRST = "quality_first"


@dataclass(frozen=True)
class ModelCandidate:
    """A model available for speculative dispatch."""

    model_id: str
    capability_score: float
    cost_per_token: float
    latency_ms: float = 500.0
    is_available: bool = True


@dataclass(frozen=True)
class CandidateResult:
    """Result from a single model candidate execution."""

    model_id: str
    output: str
    confidence: float
    latency_ms: float = 0.0
    cost_tokens: int = 0


@dataclass(frozen=True)
class VoteResult:
    """Result of voting across candidate outputs."""

    outcome: str  # "approved", "rejected", "abstained"
    agree_count: int
    total_count: int
    agreement_ratio: float
    winning_output: str = ""
    dissent_notes: tuple[str, ...] = ()

    @property
    def is_consensus(self) -> bool:
        return self.agreement_ratio >= 0.75


@dataclass(frozen=True)
class ExecutionPlan:
    """A plan for speculative execution across model candidates."""

    plan_id: str
    candidates: tuple[ModelCandidate, ...]
    strategy: DispatchStrategy
    timeout_ms: float
    created_at: float = field(default_factory=time.monotonic)

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)


@dataclass
class SpeculativeRouterConfig:
    """Configuration for the speculative execution router."""

    max_parallel_candidates: int = 3
    timeout_ms: float = 5_000.0
    min_agreement_threshold: float = 0.6
    quality_complexity_threshold: float = 0.7
    cost_complexity_threshold: float = 0.3
    tie_break_confidence_weight: float = 0.6
    tie_break_capability_weight: float = 0.4


class SpeculativeRouter:
    """Speculative execution router with parallel dispatch and voting.

    Dispatches tasks to multiple model candidates in parallel,
    compares results, and selects the best output via weighted voting.

    Usage::

        router = SpeculativeRouter()
        router.register_candidate(ModelCandidate("opus", 0.95, 15.0))
        router.register_candidate(ModelCandidate("sonnet", 0.85, 3.0))
        router.register_candidate(ModelCandidate("haiku", 0.75, 1.0))

        plan = router.build_plan(
            task="Implement auth middleware",
            complexity=0.8,
            risk_level=0.5,
            strategy=DispatchStrategy.PARALLEL_VERIFIED,
        )
        # Execute each candidate in plan.candidates, collect CandidateResults
        # vote = router.vote(results)
    """

    def __init__(self, config: SpeculativeRouterConfig | None = None) -> None:
        self.config = config or SpeculativeRouterConfig()
        self._candidates: dict[str, ModelCandidate] = {}

    # ── Properties ───────────────────────────────────────────────

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    # ── Candidate Management ─────────────────────────────────────

    def register_candidate(self, candidate: ModelCandidate) -> None:
        """Register a model candidate for speculative dispatch."""
        if candidate.model_id in self._candidates:
            raise ValueError(f"Candidate '{candidate.model_id}' already registered")
        self._candidates[candidate.model_id] = candidate

    def unregister_candidate(self, model_id: str) -> None:
        """Remove a model candidate."""
        self._candidates.pop(model_id, None)

    def get_candidate(self, model_id: str) -> ModelCandidate | None:
        """Get a registered candidate."""
        return self._candidates.get(model_id)

    # ── Planning ─────────────────────────────────────────────────

    def build_plan(
        self,
        task: str,
        complexity: float = 0.5,
        risk_level: float = 0.3,
        strategy: DispatchStrategy = DispatchStrategy.COST_OPTIMIZED,
    ) -> ExecutionPlan | None:
        _ = task  # Reserved for future keyword-based candidate filtering
        """Build an execution plan for a task.

        Returns None if no candidates are available.
        """
        candidates = self._select_candidates(complexity, risk_level, strategy)
        if not candidates:
            return None

        if strategy == DispatchStrategy.SINGLE_BEST:
            candidates = (candidates[0],)
        elif strategy == DispatchStrategy.COST_OPTIMIZED and complexity <= self.config.cost_complexity_threshold:
            candidates = (candidates[0],)

        timeout = self.config.timeout_ms
        if strategy == DispatchStrategy.QUALITY_FIRST:
            timeout *= 2.0

        return ExecutionPlan(
            plan_id=f"ep-{uuid.uuid4().hex[:12]}",
            candidates=tuple(candidates[: self.config.max_parallel_candidates]),
            strategy=strategy,
            timeout_ms=timeout,
        )

    # ── Voting ───────────────────────────────────────────────────

    def vote(self, results: list[CandidateResult]) -> VoteResult:
        """Vote across candidate results to determine consensus outcome."""
        if not results:
            return VoteResult(
                outcome="abstained",
                agree_count=0,
                total_count=0,
                agreement_ratio=0.0,
            )

        normalized = [self._normalize_output(r.output) for r in results]

        # Group identical (or near-identical) outputs
        groups: dict[str, list[CandidateResult]] = {}
        for i, result in enumerate(results):
            matched = False
            for key in list(groups.keys()):
                if self._similarity(normalized[i], key) >= 0.8:
                    groups[key].append(result)
                    matched = True
                    break
            if not matched:
                groups[normalized[i]] = [result]

        # Find the largest group
        best_key = max(groups, key=lambda k: len(groups[k]))
        best_group = groups[best_key]

        agree_count = len(best_group)
        ratio = agree_count / len(results)

        # Determine outcome
        if ratio >= self.config.min_agreement_threshold:
            outcome = "approved"
        elif ratio >= 0.33:
            outcome = "rejected"
        else:
            outcome = "abstained"

        # Collect dissent
        dissent: list[str] = []
        for key, group in groups.items():
            if key != best_key:
                for r in group:
                    snippet = r.output[:80] if r.output else ""
                    dissent.append(f"{r.model_id}: {snippet}")

        winner = self.tie_break(*best_group)

        return VoteResult(
            outcome=outcome,
            agree_count=agree_count,
            total_count=len(results),
            agreement_ratio=ratio,
            winning_output=winner.output if winner else best_group[0].output,
            dissent_notes=tuple(dissent),
        )

    def compare_results(self, a: CandidateResult, b: CandidateResult) -> float:
        """Compare two results and return similarity score (0-1)."""
        return self._similarity(
            self._normalize_output(a.output),
            self._normalize_output(b.output),
        )

    def tie_break(self, *results: CandidateResult) -> CandidateResult | None:
        """Break a tie between results by confidence then capability."""
        if not results:
            return None

        def score(r: CandidateResult) -> float:
            capability = 0.5
            candidate = self._candidates.get(r.model_id)
            if candidate:
                capability = candidate.capability_score
            return (
                r.confidence * self.config.tie_break_confidence_weight
                + capability * self.config.tie_break_capability_weight
            )

        return max(results, key=score)

    def get_result_summary(
        self,
        results: list[CandidateResult],
        vote: VoteResult,
    ) -> dict:
        """Get a summary of speculative execution results."""
        total_cost = sum(
            r.cost_tokens * self._candidates[r.model_id].cost_per_token
            for r in results
            if r.model_id in self._candidates
        )
        return {
            "total_candidates": len(results),
            "outcome": vote.outcome,
            "agreement_ratio": vote.agreement_ratio,
            "total_latency_ms": max((r.latency_ms for r in results), default=0.0),
            "total_cost": total_cost,
            "winning_model": self._find_winning_model(results, vote.winning_output),
        }

    # ── Internal Selection Logic ─────────────────────────────────

    def _select_candidates(
        self,
        complexity: float,
        risk: float,
        strategy: DispatchStrategy,
    ) -> list[ModelCandidate]:
        """Select and order candidates for a task."""
        available = [
            c for c in self._candidates.values() if c.is_available
        ]

        if strategy == DispatchStrategy.QUALITY_FIRST:
            available.sort(key=lambda c: c.capability_score, reverse=True)
        elif strategy == DispatchStrategy.COST_OPTIMIZED:
            available.sort(key=lambda c: c.cost_per_token)
        elif strategy == DispatchStrategy.PARALLEL_VERIFIED:
            # Balance quality and cost, prefer diversity
            available.sort(key=lambda c: c.capability_score, reverse=True)
        else:  # SINGLE_BEST
            combined = complexity * 0.6 + risk * 0.4
            if combined > 0.7:
                available.sort(key=lambda c: c.capability_score, reverse=True)
            else:
                available.sort(key=lambda c: c.cost_per_token)

        return available

    # ── Private ───────────────────────────────────────────────────

    @staticmethod
    def _normalize_output(output: str) -> str:
        """Normalize output for comparison."""
        return output.strip().lower()

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Compute Jaccard similarity between two output strings."""
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _find_winning_model(
        results: list[CandidateResult],
        winning_output: str,
    ) -> str:
        """Find which model produced the winning output."""
        for r in results:
            if r.output.strip().lower() == winning_output.strip().lower():
                return r.model_id
        return ""

    def reset(self) -> None:
        """Reset all registered candidates."""
        self._candidates.clear()
