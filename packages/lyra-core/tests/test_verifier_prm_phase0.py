"""RED tests for v1.8 Wave-2 §8.5 — Process Reward Model adapter."""
from __future__ import annotations

from lyra_core.verifier import (
    PrmAdapter,
    PrmStepScore,
    PrmTrajectoryScore,
    StepLabel,
)


class _StubPrm(PrmAdapter):
    """Toy PRM: alternates good/neutral/bad based on step index."""

    def score_step(self, step_index: int, step: str) -> PrmStepScore:
        labels = [StepLabel.GOOD, StepLabel.NEUTRAL, StepLabel.BAD]
        scores = [0.95, 0.5, 0.05]
        return PrmStepScore(
            step_index=step_index,
            label=labels[step_index % 3],
            score=scores[step_index % 3],
            rationale=f"toy at idx {step_index}",
        )

    def score_trajectory(self, steps):  # type: ignore[override]
        scored = tuple(self.score_step(i, s) for i, s in enumerate(steps))
        return PrmTrajectoryScore(
            overall=sum(s.score for s in scored) / max(len(scored), 1),
            worst_step_index=min(scored, key=lambda s: s.score).step_index,
            worst_step_label=min(scored, key=lambda s: s.score).label,
            step_scores=scored,
        )


def test_step_label_is_a_three_value_enum() -> None:
    """Lyra fixes the label space to {good, neutral, bad}."""
    assert {label.value for label in StepLabel} == {"good", "neutral", "bad"}


def test_stub_prm_satisfies_protocol() -> None:
    """Sanity-check that the Protocol matches a concrete adapter at instantiation."""
    prm: PrmAdapter = _StubPrm()
    score = prm.score_step(0, "do thing")
    assert isinstance(score, PrmStepScore)
    assert 0.0 <= score.score <= 1.0


def test_stub_prm_aggregates_over_steps() -> None:
    """``score_trajectory`` returns step_scores aligned with input length."""
    prm: PrmAdapter = _StubPrm()
    out = prm.score_trajectory(["a", "b", "c", "d"])
    assert len(out.step_scores) == 4
    assert 0.0 <= out.overall <= 1.0


# The downstream wiring (PRM-as-discriminator inside TournamentTts; PRM as
# confidence source inside ConfidenceCascadeRouter) is a Phase-1 contract
# that lives in those modules; the RED tests below are reserved.


def test_default_prm_adapter_distinguishes_obvious_bad_from_obvious_good_step() -> None:
    """The property contract for any Lyra PRM, real or heuristic.

    v1.8 ships a deterministic ``HeuristicArithmeticPrm`` as the default
    so this test passes offline; v1.9 Phase 1 swaps the factory's return
    value to a Qwen2.5-Math-PRM-7B-backed adapter behind a feature flag.
    Both must satisfy the same property: ``score_step('1+1=2')`` ≫
    ``score_step('1+1=11')``.
    """
    from lyra_core.verifier import prm as _prm
    from lyra_core.verifier.prm import PrmAdapter as _Adapter

    backend = getattr(_prm, "default_prm_adapter", None)
    assert callable(backend), "default_prm_adapter() must be exposed"
    prm: _Adapter = backend()
    good = prm.score_step(0, "1 + 1 = 2")
    bad = prm.score_step(0, "1 + 1 = 11")
    assert good.score > bad.score
