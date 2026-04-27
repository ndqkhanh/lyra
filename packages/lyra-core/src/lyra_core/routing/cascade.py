"""Confidence-Cascade Router (v1.8 Wave-2 §8.2).

Inspired by *FrugalGPT* (arXiv:2305.05176, mirrored under
``papers/frugalgpt.pdf``), *RouteLLM* (arXiv:2406.18665, mirrored under
``papers/routellm.pdf``) and *Confidence-Driven LLM Router* (arXiv:2308.11601,
mirrored under ``papers/confidence-driven-llm-router.pdf``).

Idea: order providers cheap → expensive. Try cheap first; if a
confidence estimator says the answer is solid, return it. Otherwise
escalate. The Lyra v1.8 router pairs naturally with:

- ``..verifier.tdd_reward`` — escalate on `score < threshold`,
- ``..tts.tournament`` — let the tournament discriminator's score act
  as confidence,
- ``..verifier.prm`` — step-level confidence from PRM.

Phase 0: contracts only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class CascadeStage:
    """One rung of the cascade: a provider id, a cost weight, and a confidence threshold."""

    provider_id: str
    cost_weight: float            # arbitrary unit; lower == cheaper
    accept_above_confidence: float  # in [0, 1]; below this the cascade escalates

    def __post_init__(self) -> None:
        if not 0.0 <= self.accept_above_confidence <= 1.0:
            raise ValueError("accept_above_confidence must be in [0, 1]")
        if self.cost_weight < 0:
            raise ValueError("cost_weight must be >= 0")


@dataclass(frozen=True)
class ProviderInvocation:
    """Recorded outcome of one rung's call."""

    stage: CascadeStage
    answer: str
    confidence: float
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class CascadeDecision:
    """Why the cascade chose to stop where it did."""

    accepted_at_stage_index: int
    reason: str                   # e.g. "confidence 0.93 >= 0.85" / "final stage"


@dataclass(frozen=True)
class CascadeResult:
    """End-to-end outcome of one cascade run."""

    answer: str
    invocations: tuple[ProviderInvocation, ...]
    decision: CascadeDecision
    total_cost_weight: float


class ProviderCallable(Protocol):
    """Anything that can answer a query for one stage."""

    def __call__(self, prompt: str) -> tuple[str, int, int]:
        """Returns ``(answer, tokens_in, tokens_out)``."""
        ...


class ConfidenceEstimator(Protocol):
    """Scores the confidence of a single provider's answer in [0, 1]."""

    def estimate(self, prompt: str, answer: str) -> float: ...


class ConfidenceCascadeRouter:
    """Route a prompt through an ordered cascade of providers.

    Phase 0: validates construction, ``invoke`` raises ``NotImplementedError``.
    """

    def __init__(
        self,
        stages: Sequence[CascadeStage],
        callers: Mapping[str, ProviderCallable],
        estimator: ConfidenceEstimator,
    ) -> None:
        if not stages:
            raise ValueError("ConfidenceCascadeRouter requires at least one stage")
        # The cascade only makes sense if cost is monotonically non-decreasing.
        for prev, curr in zip(stages, stages[1:]):
            if curr.cost_weight < prev.cost_weight:
                raise ValueError(
                    "cascade stages must be ordered cheap -> expensive "
                    "(cost_weight non-decreasing)"
                )
        missing = {s.provider_id for s in stages} - set(callers.keys())
        if missing:
            raise ValueError(
                f"missing ProviderCallable for stage(s): {sorted(missing)}"
            )
        self._stages = tuple(stages)
        self._callers = dict(callers)
        self._estimator = estimator

    def invoke(self, prompt: str) -> CascadeResult:
        invocations: list[ProviderInvocation] = []
        for stage_idx, stage in enumerate(self._stages):
            caller = self._callers[stage.provider_id]
            answer, tokens_in, tokens_out = caller(prompt)
            confidence = self._estimator.estimate(prompt, answer)
            invocation = ProviderInvocation(
                stage=stage,
                answer=answer,
                confidence=confidence,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            invocations.append(invocation)

            if confidence >= stage.accept_above_confidence:
                return CascadeResult(
                    answer=answer,
                    invocations=tuple(invocations),
                    decision=CascadeDecision(
                        accepted_at_stage_index=stage_idx,
                        reason=(
                            f"confidence {confidence:.3f} >= threshold "
                            f"{stage.accept_above_confidence:.3f} "
                            f"at stage {stage_idx} ({stage.provider_id})"
                        ),
                    ),
                    total_cost_weight=sum(inv.stage.cost_weight for inv in invocations),
                )

        # Fell through every threshold: last stage's answer wins by default.
        # This is the safety net; in practice the bottom rung should have
        # ``accept_above_confidence == 0.0`` so this branch never triggers
        # in production, but the contract is explicit so misconfigured
        # cascades degrade to "answer of the most expensive model" rather
        # than raising.
        last = invocations[-1]
        return CascadeResult(
            answer=last.answer,
            invocations=tuple(invocations),
            decision=CascadeDecision(
                accepted_at_stage_index=len(invocations) - 1,
                reason=(
                    f"no stage met its threshold; falling through to final "
                    f"stage {last.stage.provider_id} (confidence "
                    f"{last.confidence:.3f})"
                ),
            ),
            total_cost_weight=sum(inv.stage.cost_weight for inv in invocations),
        )
