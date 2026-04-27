"""RED tests for v1.8 Wave-2 §8.2 — Confidence-Cascade Router."""
from __future__ import annotations

import pytest

from lyra_core.routing import (
    CascadeStage,
    ConfidenceCascadeRouter,
    ConfidenceEstimator,
)


class _FixedConfidence(ConfidenceEstimator):
    def __init__(self, confidence: float) -> None:
        self._c = confidence

    def estimate(self, prompt: str, answer: str) -> float:
        return self._c


def _stage(provider_id: str, cost: float, threshold: float) -> CascadeStage:
    return CascadeStage(
        provider_id=provider_id,
        cost_weight=cost,
        accept_above_confidence=threshold,
    )


def _caller(reply: str):
    def _call(prompt: str):
        return reply, len(prompt), len(reply)

    return _call


def test_stage_validation_rejects_out_of_range_thresholds() -> None:
    with pytest.raises(ValueError):
        CascadeStage(provider_id="cheap", cost_weight=1.0, accept_above_confidence=1.5)
    with pytest.raises(ValueError):
        CascadeStage(provider_id="cheap", cost_weight=-1.0, accept_above_confidence=0.5)


def test_router_rejects_non_monotone_cost_ordering() -> None:
    """Cascade only makes sense if costs are non-decreasing."""
    stages = [
        _stage("expensive", 10.0, 0.8),
        _stage("cheap", 1.0, 0.6),
    ]
    callers = {"expensive": _caller("e"), "cheap": _caller("c")}
    with pytest.raises(ValueError, match="non-decreasing"):
        ConfidenceCascadeRouter(stages=stages, callers=callers, estimator=_FixedConfidence(1.0))


def test_router_rejects_missing_provider_callables() -> None:
    stages = [_stage("cheap", 1.0, 0.6), _stage("expensive", 10.0, 0.8)]
    callers = {"cheap": _caller("c")}
    with pytest.raises(ValueError, match="expensive"):
        ConfidenceCascadeRouter(stages=stages, callers=callers, estimator=_FixedConfidence(1.0))


def test_high_confidence_short_circuits_at_first_stage() -> None:
    """Cheap stage with confidence above threshold → never escalate."""
    stages = [_stage("cheap", 1.0, 0.6), _stage("expensive", 10.0, 0.8)]
    callers = {"cheap": _caller("cheap-answer"), "expensive": _caller("expensive-answer")}
    router = ConfidenceCascadeRouter(stages=stages, callers=callers, estimator=_FixedConfidence(0.95))
    result = router.invoke("anything")
    assert result.answer == "cheap-answer"
    assert len(result.invocations) == 1
    assert result.decision.accepted_at_stage_index == 0


def test_low_confidence_escalates_through_full_cascade() -> None:
    """Confidence below every threshold → escalate to the most expensive stage."""
    stages = [_stage("cheap", 1.0, 0.9), _stage("mid", 5.0, 0.95), _stage("expensive", 10.0, 0.0)]
    callers = {
        "cheap": _caller("cheap-answer"),
        "mid": _caller("mid-answer"),
        "expensive": _caller("expensive-answer"),
    }
    router = ConfidenceCascadeRouter(stages=stages, callers=callers, estimator=_FixedConfidence(0.5))
    result = router.invoke("hard question")
    assert result.answer == "expensive-answer"
    assert len(result.invocations) == 3
    assert result.decision.accepted_at_stage_index == 2


def test_total_cost_weight_is_sum_of_invoked_stages() -> None:
    stages = [_stage("cheap", 1.0, 0.99), _stage("mid", 5.0, 0.0)]
    callers = {"cheap": _caller("cheap-answer"), "mid": _caller("mid-answer")}
    router = ConfidenceCascadeRouter(stages=stages, callers=callers, estimator=_FixedConfidence(0.5))
    result = router.invoke("q")
    assert result.total_cost_weight == pytest.approx(6.0)
