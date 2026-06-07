"""Multi-model consensus judging with 3-model panels."""

from __future__ import annotations

from dataclasses import dataclass

from .adaptive_rubric import AdaptiveRubric, RubricTemplate
from .exceptions import CrossModelError


@dataclass(frozen=True)
class JudgeModel:
    """A model that can serve as a judge."""

    model_id: str
    family: str
    tier: str
    bias_profile: tuple[float, ...]


@dataclass(frozen=True)
class ModelVerdict:
    """Verdict from a single judge model."""

    model_id: str
    score: float
    reasoning: str
    confidence: float
    dissent_flags: tuple[str, ...]


@dataclass(frozen=True)
class ConsensusResult:
    """Consensus outcome from multiple judge models."""

    verdicts: tuple[ModelVerdict, ...]
    consensus_score: float
    agreement_level: float
    majority_opinion: str
    dissenting_opinions: tuple[str, ...]


@dataclass(frozen=True)
class JudgePanel:
    """A panel of judges for evaluation."""

    models: tuple[JudgeModel, ...]
    primary: JudgeModel
    secondary: tuple[JudgeModel, ...]


_AVAILABLE_JUDGES: tuple[JudgeModel, ...] = (
    JudgeModel("judge-opus-01", "claude", "opus", (0.05, -0.02, 0.01)),
    JudgeModel("judge-sonnet-01", "claude", "sonnet", (0.02, 0.01, -0.01)),
    JudgeModel("judge-haiku-01", "claude", "haiku", (-0.03, 0.04, -0.02)),
    JudgeModel("judge-gpt4-01", "openai", "gpt4", (0.04, -0.01, 0.03)),
    JudgeModel("judge-gemini-01", "google", "gemini", (-0.01, 0.02, 0.01)),
)


class CrossModelJudge:
    """Manages multi-model consensus judging."""

    def __init__(self) -> None:
        self._rubric = AdaptiveRubric()
        self._judges: dict[str, JudgeModel] = {j.model_id: j for j in _AVAILABLE_JUDGES}
        self._verdict_history: list[ModelVerdict] = []

    async def convene_panel(self, num_judges: int = 3) -> JudgePanel:
        """Convene a panel of judges."""
        if num_judges < 2:
            raise CrossModelError("Panel must have at least 2 judges")
        if num_judges > len(_AVAILABLE_JUDGES):
            raise CrossModelError(
                f"Only {len(_AVAILABLE_JUDGES)} judges available, requested {num_judges}"
            )

        selected = _AVAILABLE_JUDGES[:num_judges]
        primary = selected[0]
        secondary = selected[1:]

        return JudgePanel(
            models=selected,
            primary=primary,
            secondary=secondary,
        )

    async def solicit_verdict(
        self, model: JudgeModel, response: str, rubric: RubricTemplate
    ) -> ModelVerdict:
        """Solicit a verdict from a single judge model."""
        if not response:
            raise CrossModelError("Cannot evaluate an empty response")

        result = await self._rubric.score_response(response, rubric)
        bias = model.bias_profile

        # Apply model bias to the score (deterministic)
        bias_adjustment = sum(bias) / len(bias) if bias else 0.0
        adjusted_score = min(max(result.total_score + bias_adjustment, 0.0), 1.0)

        # Generate deterministic reasoning
        if adjusted_score >= 0.8:
            reasoning = "High quality response"
        elif adjusted_score >= 0.5:
            reasoning = "Adequate response with minor issues"
        else:
            reasoning = "Response needs significant improvement"

        confidence = _compute_judge_confidence(adjusted_score, len(response))

        # Compute dissent flags
        flags: list[str] = []
        if bias_adjustment > 0.03:
            flags.append("lenient_bias_detected")
        elif bias_adjustment < -0.03:
            flags.append("strict_bias_detected")
        if adjusted_score < 0.3:
            flags.append("low_score_flag")
        if confidence < 0.4:
            flags.append("low_confidence")

        verdict = ModelVerdict(
            model_id=model.model_id,
            score=round(adjusted_score, 4),
            reasoning=reasoning,
            confidence=round(confidence, 4),
            dissent_flags=tuple(flags),
        )

        self._verdict_history.append(verdict)
        return verdict

    async def reach_consensus(
        self, verdicts: tuple[ModelVerdict, ...]
    ) -> ConsensusResult:
        """Reach consensus among multiple model verdicts."""
        if not verdicts:
            raise CrossModelError("No verdicts to reach consensus on")
        if len(verdicts) < 2:
            raise CrossModelError("Need at least 2 verdicts for consensus")

        scores = [v.score for v in verdicts]
        consensus_score = sum(scores) / len(scores)

        # Agreement level: how close scores are to each other
        max_diff = max(scores) - min(scores) if scores else 0.0
        agreement_level = max(0.0, 1.0 - max_diff)

        # Majority opinion
        passed_count = sum(1 for s in scores if s >= 0.5)
        total = len(scores)
        if passed_count > total / 2:
            majority_opinion = "pass"
        elif passed_count < total / 2:
            majority_opinion = "fail"
        else:
            majority_opinion = "split"

        # Dissenting opinions
        dissenting: list[str] = []
        for v in verdicts:
            if (consensus_score >= 0.5 and v.score < 0.5) or (
                consensus_score < 0.5 and v.score >= 0.5
            ):
                dissenting.append(f"{v.model_id}: {v.reasoning}")

        return ConsensusResult(
            verdicts=verdicts,
            consensus_score=round(consensus_score, 4),
            agreement_level=round(agreement_level, 4),
            majority_opinion=majority_opinion,
            dissenting_opinions=tuple(dissenting),
        )

    async def judge(
        self,
        response: str,
        rubric: RubricTemplate,
        panel: JudgePanel | None = None,
    ) -> ConsensusResult:
        """End-to-end: convene a panel, judge the response, reach consensus."""
        if panel is None:
            panel = await self.convene_panel(num_judges=3)

        verdicts: list[ModelVerdict] = []
        for model in panel.models:
            verdict = await self.solicit_verdict(model, response, rubric)
            verdicts.append(verdict)

        return await self.reach_consensus(tuple(verdicts))


def _compute_judge_confidence(score: float, response_length: int) -> float:
    """Compute confidence for a judge's verdict."""
    length_conf = min(response_length / 30.0, 1.0)
    score_conf = 0.6 + 0.4 * abs(score - 0.5) * 2
    return (length_conf + score_conf) / 2.0
