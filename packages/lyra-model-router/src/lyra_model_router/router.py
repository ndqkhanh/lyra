"""Main ModelRouter class orchestrating all routing decisions.

Integrates CapabilityAnalyzer, CostOptimizer, KnowingDoingGapDetector,
and CrossModelVerifier into a unified routing pipeline. Provides async
routing with timeout fallback and full audit trail.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Sequence

from .capability_analyzer import (
    CapabilityAnalyzer,
    DomainType,
    MatchScore,
    ModelCapability,
    TaskProfile,
)
from .cost_optimizer import CostOptimizer, CostTier
from .knowing_doing_gap import GapRecommendation, KnowingDoingGapDetector, ToolCategory
from .cross_model_verifier import CrossModelVerifier, ValidationResult
from .router_config import FallbackRule, ModelRegistryEntry, RouterConfig, RoutingPolicy
from .usage_tracker import UsageRecord, UsageTracker
from .exceptions import (
    CapabilityMismatchError,
    ModelNotFoundError,
    RoutingError,
)


@dataclass(frozen=True)
class ModelSelection:
    """The result of a routing decision."""
    model_id: str
    confidence: float  # 0.0-1.0
    reasoning: str
    alternatives: tuple[MatchScore, ...] = field(default_factory=tuple)
    tier: str = ""
    estimated_cost: float = 0.0
    gaps_detected: tuple[GapRecommendation, ...] = field(default_factory=tuple)
    verification: ValidationResult | None = None
    routing_time_ms: float = 0.0
    task_id: str = ""


@dataclass(frozen=True)
class RouterPipeline:
    """Snapshot of pipeline stage results for audit."""
    capability_scores: tuple[MatchScore, ...] = field(default_factory=tuple)
    selected_score: MatchScore | None = None
    gaps: tuple[GapRecommendation, ...] = field(default_factory=tuple)
    verification: ValidationResult | None = None
    cost_analysis: dict[str, Any] = field(default_factory=dict)


class ModelRouter:
    """Main router that orchestrates model selection decisions.

    Routes tasks through the full pipeline:
    TaskProfile → CapabilityAnalyzer → CostOptimizer → KnowingDoingGapDetector
    → CrossModelVerifier → ModelSelection

    Supports async routing with timeout fallback, full audit trail,
    and integration with UsageTracker for cost monitoring.
    """

    def __init__(
        self,
        config: RouterConfig | None = None,
        capability_analyzer: CapabilityAnalyzer | None = None,
        cost_optimizer: CostOptimizer | None = None,
        gap_detector: KnowingDoingGapDetector | None = None,
        verifier: CrossModelVerifier | None = None,
        usage_tracker: UsageTracker | None = None,
    ) -> None:
        self._capability_analyzer = capability_analyzer or CapabilityAnalyzer()
        self._cost_optimizer = cost_optimizer or CostOptimizer(
            capability_analyzer=self._capability_analyzer,
        )
        self._gap_detector = gap_detector or KnowingDoingGapDetector()
        self._verifier = verifier or CrossModelVerifier()
        self._usage_tracker = usage_tracker or UsageTracker()
        self._config = config or RouterConfig()
        self._audit_log: list[dict[str, Any]] = []
        self._pipeline_history: list[RouterPipeline] = []

    @property
    def config(self) -> RouterConfig:
        return self._config

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)

    @property
    def usage(self) -> UsageTracker:
        return self._usage_tracker

    @property
    def pipeline_history(self) -> list[RouterPipeline]:
        return list(self._pipeline_history)

    # ── Public API ────────────────────────────────────────────────────

    def route(
        self,
        task: TaskProfile,
        task_description: str = "",
        task_id: str | None = None,
        preferred_tier: CostTier | None = None,
        budget_constraint: float | None = None,
        verify_reviewer: str | None = None,
    ) -> ModelSelection:
        """Run the full routing pipeline for a task.

        Args:
            task: The task profile to route.
            task_description: Optional natural language description for gap detection.
            task_id: Optional identifier for audit trail.
            preferred_tier: Optional cost tier preference.
            budget_constraint: Optional per-task budget limit.
            verify_reviewer: Optional reviewer model ID for cross-model verification.

        Returns:
            A ModelSelection with the chosen model and supporting details.

        Raises:
            CapabilityMismatchError: If no model can handle the task.
            RoutingError: If the routing pipeline fails.
        """
        start_time = time.time()
        rid = task_id or f"task_{uuid.uuid4().hex[:8]}"

        # ── Stage 1: Capability Analysis ──────────────────────────────
        scores = self._capability_analyzer.analyze(task)
        if not scores:
            raise CapabilityMismatchError(
                task_type=task.domain.value,
                reason="No models registered in capability analyzer",
            )

        selected_score = scores[0]

        # ── Stage 2: Cost Optimization ────────────────────────────────
        optimized = self._cost_optimizer.optimize(
            task=task,
            scored_models=scores,
            budget_constraint=budget_constraint,
            preferred_tier=preferred_tier,
        )
        if optimized is not None:
            selected_score = optimized

        # ── Stage 3: Knowing-Doing Gap Detection ──────────────────────
        gaps: list[GapRecommendation] = []
        if task_description:
            gaps = self._gap_detector.analyze(task, task_description)

        # ── Stage 4: Cross-Model Verification ─────────────────────────
        verification: ValidationResult | None = None
        if verify_reviewer:
            verification = self._verifier.verify(
                generator_model=selected_score.model_id,
                reviewer_model=verify_reviewer,
            )

        # ── Stage 5: Fallback Check ───────────────────────────────────
        if not self._is_model_available(selected_score.model_id):
            fallback = self._resolve_fallback(selected_score.model_id, task, scores)
            if fallback is not None:
                selected_score = fallback

        # ── Build Result ────────────────────────────────────────────
        selected_cap = self._capability_analyzer.get_model(selected_score.model_id)
        estimated_cost = 0.0
        if selected_cap is not None:
            estimated_cost = selected_cap.cost_for_tokens(task.estimated_tokens)

        routing_time_ms = (time.time() - start_time) * 1000.0

        selection = ModelSelection(
            model_id=selected_score.model_id,
            confidence=selected_score.total_score,
            reasoning=self._build_reasoning(selected_score, verification),
            alternatives=tuple(scores),
            tier=selected_cap.tier if selected_cap else "",
            estimated_cost=estimated_cost,
            gaps_detected=tuple(gaps),
            verification=verification,
            routing_time_ms=round(routing_time_ms, 2),
            task_id=rid,
        )

        # ── Record Usage ──────────────────────────────────────────────
        self._usage_tracker.record(UsageRecord(
            model_id=selection.model_id,
            task_type=task.domain.value,
            cost=estimated_cost,
            model_tier=selection.tier,
            timestamp=time.time(),
        ))

        # ── Audit ─────────────────────────────────────────────────────
        pipeline = RouterPipeline(
            capability_scores=tuple(scores),
            selected_score=selected_score,
            gaps=tuple(gaps),
            verification=verification,
            cost_analysis={"estimated_cost": estimated_cost},
        )
        self._pipeline_history.append(pipeline)
        self._audit_log.append({
            "task_id": rid,
            "task_domain": task.domain.value,
            "selected_model": selection.model_id,
            "confidence": selection.confidence,
            "estimated_cost": estimated_cost,
            "routing_time_ms": routing_time_ms,
            "verification_passed": verification.passed if verification else None,
            "gaps_count": len(gaps),
            "timestamp": time.time(),
        })

        return selection

    async def route_async(
        self,
        task: TaskProfile,
        task_description: str = "",
        task_id: str | None = None,
        preferred_tier: CostTier | None = None,
        budget_constraint: float | None = None,
        verify_reviewer: str | None = None,
        timeout: float = 5.0,
    ) -> ModelSelection:
        """Async routing with timeout fallback.

        Same as route() but wrapped with a timeout. Falls back to default model
        on timeout.
        """
        try:
            return await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self.route,
                    task,
                    task_description,
                    task_id,
                    preferred_tier,
                    budget_constraint,
                    verify_reviewer,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            # Fallback to fastest available model
            fallback = self._get_fallback_model()
            return ModelSelection(
                model_id=fallback,
                confidence=0.3,
                reasoning=f"Async routing timed out after {timeout}s, fell back to {fallback}",
                routing_time_ms=timeout * 1000.0,
                task_id=task_id or "timeout",
            )

    def route_with_review(
        self,
        task: TaskProfile,
        reviewer_model: str,
        task_description: str = "",
    ) -> tuple[ModelSelection, ModelSelection]:
        """Route a task and also select a reviewer model.

        Returns (generator_selection, reviewer_selection).
        The reviewer will be from a different family than the generator.
        """
        gen_selection = self.route(
            task=task,
            task_description=task_description,
            verify_reviewer=reviewer_model,
        )

        # Verify reviewer choice is valid
        if not self._verifier.verify(gen_selection.model_id, reviewer_model).passed:
            alt_families = self._verifier.suggest_reviewer_families(gen_selection.model_id)
            alt_model = f"claude-sonnet-4.6"
            if alt_families:
                family = alt_families[0]
                if family.name == "OPENAI":
                    alt_model = "gpt-4o"
                elif family.name == "DEEPSEEK":
                    alt_model = "deepseek-v4-pro"

            reviewer_selection = ModelSelection(
                model_id=alt_model,
                confidence=0.5,
                reasoning=f"Original reviewer '{reviewer_model}' same family; suggested '{alt_model}'",
            )
        else:
            reviewer_selection = ModelSelection(
                model_id=reviewer_model,
                confidence=0.7,
                reasoning=f"Reviewer '{reviewer_model}' from different family, passes verification",
            )

        return gen_selection, reviewer_selection

    # ── Internal Methods ──────────────────────────────────────────────

    def _is_model_available(self, model_id: str) -> bool:
        """Check if a model is available in config and healthy."""
        available = self._config.get_available_models()
        return model_id in available

    def _resolve_fallback(
        self,
        failed_model: str,
        task: TaskProfile,
        scores: list[MatchScore],
    ) -> MatchScore | None:
        """Resolve fallback when primary model is unavailable."""
        chain = self._config.get_fallback_chain(failed_model)
        score_map: dict[str, MatchScore] = {s.model_id: s for s in scores}
        for model_id in chain:
            if model_id != failed_model and model_id in score_map and self._is_model_available(model_id):
                return score_map[model_id]
        return None

    def _get_fallback_model(self) -> str:
        """Get a safe fallback model."""
        available = self._config.get_available_models()
        if available:
            return available[0]
        return "claude-sonnet-4.6"

    @staticmethod
    def _build_reasoning(
        score: MatchScore,
        verification: ValidationResult | None,
    ) -> str:
        """Build human-readable reasoning for the selection."""
        parts = [
            f"Model '{score.model_id}' selected with total_score={score.total_score:.4f}",
            f"reasoning={score.reasoning_score:.4f}, coding={score.coding_score:.4f}, "
            f"speed={score.speed_score:.4f}, cost={score.cost_score:.4f}",
        ]
        if verification is not None:
            status = "passed" if verification.passed else "failed"
            parts.append(f"Cross-model verification: {status} (diversity={verification.diversity_score:.2f})")
        return "; ".join(parts)

    # ── Utility ───────────────────────────────────────────────────────

    def get_routing_stats(self) -> dict[str, float]:
        """Return summary routing statistics."""
        model_counts: dict[str, float] = {}
        for pipeline in self._pipeline_history:
            if pipeline.selected_score is not None:
                mid = pipeline.selected_score.model_id
                model_counts[mid] = model_counts.get(mid, 0.0) + 1.0
        total = sum(model_counts.values()) or 1.0
        return {mid: c / total for mid, c in model_counts.items()}

    def export_audit_log(self, indent: int = 2) -> str:
        """Export the audit log as JSON."""
        return json.dumps(self._audit_log, indent=indent)

    def clear_history(self) -> None:
        """Clear audit log and pipeline history."""
        self._audit_log.clear()
        self._pipeline_history.clear()
