"""Tests for CrossModelJudge."""

from __future__ import annotations

import pytest
from lyra_eval_pipeline import (
    AdaptiveRubric,
    ConsensusResult,
    CrossModelJudge,
    JudgeModel,
    JudgePanel,
    ModelVerdict,
    RubricDimension,
)
from lyra_eval_pipeline.exceptions import CrossModelError


class TestJudgeModel:
    def test_model_creation(self) -> None:
        model = JudgeModel(
            model_id="judge-1",
            family="claude",
            tier="sonnet",
            bias_profile=(0.02, -0.01, 0.01),
        )
        assert model.model_id == "judge-1"
        assert model.family == "claude"
        assert model.tier == "sonnet"


class TestModelVerdict:
    def test_verdict_creation(self) -> None:
        verdict = ModelVerdict(
            model_id="judge-1",
            score=0.85,
            reasoning="Good response",
            confidence=0.9,
            dissent_flags=(),
        )
        assert verdict.score == 0.85
        assert verdict.reasoning == "Good response"


class TestConsensusResult:
    def test_consensus_creation(self) -> None:
        result = ConsensusResult(
            verdicts=(),
            consensus_score=0.75,
            agreement_level=0.85,
            majority_opinion="pass",
            dissenting_opinions=(),
        )
        assert result.consensus_score == 0.75
        assert result.majority_opinion == "pass"


class TestJudgePanel:
    def test_panel_creation(self) -> None:
        primary = JudgeModel("p1", "claude", "opus", (0.0,))
        secondary = (
            JudgeModel("s1", "claude", "sonnet", (0.0,)),
            JudgeModel("s2", "openai", "gpt4", (0.0,)),
        )
        panel = JudgePanel(
            models=(primary, secondary[0], secondary[1]),
            primary=primary,
            secondary=secondary,
        )
        assert panel.primary.model_id == "p1"
        assert len(panel.secondary) == 2


class TestCrossModelJudge:
    @pytest.mark.asyncio
    async def test_convene_panel_default(self) -> None:
        judge = CrossModelJudge()
        panel = await judge.convene_panel()
        assert len(panel.models) == 3
        assert panel.primary.family == "claude"
        assert panel.primary.tier == "opus"

    @pytest.mark.asyncio
    async def test_convene_panel_custom_count(self) -> None:
        judge = CrossModelJudge()
        panel = await judge.convene_panel(num_judges=2)
        assert len(panel.models) == 2

    @pytest.mark.asyncio
    async def test_convene_panel_too_few_raises(self) -> None:
        judge = CrossModelJudge()
        with pytest.raises(CrossModelError, match="at least 2 judges"):
            await judge.convene_panel(num_judges=1)

    @pytest.mark.asyncio
    async def test_convene_panel_too_many_raises(self) -> None:
        judge = CrossModelJudge()
        with pytest.raises(CrossModelError, match="Only 5 judges available"):
            await judge.convene_panel(num_judges=10)

    @pytest.mark.asyncio
    async def test_solicit_verdict(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template(
            "test", [RubricDimension("acc", 1.0, "d", "exact_match")]
        )
        model = JudgeModel("jm1", "claude", "sonnet", (0.0, 0.0, 0.0))
        verdict = await judge.solicit_verdict(model, "good response", rubric)
        assert verdict.model_id == "jm1"
        assert 0.0 <= verdict.score <= 1.0
        assert verdict.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_solicit_verdict_empty_raises(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template("t", [RubricDimension("a", 1.0, "d", "f")])
        model = JudgeModel("jm1", "c", "s", (0.0,))
        with pytest.raises(CrossModelError, match="empty response"):
            await judge.solicit_verdict(model, "", rubric)

    @pytest.mark.asyncio
    async def test_solicit_verdict_applies_bias(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template(
            "t", [RubricDimension("a", 1.0, "d", "exact_match")]
        )
        lenient = JudgeModel("lenient", "c", "s", (0.2, 0.2, 0.2))
        strict = JudgeModel("strict", "c", "s", (-0.2, -0.2, -0.2))
        v1 = await judge.solicit_verdict(lenient, "test", rubric)
        v2 = await judge.solicit_verdict(strict, "test", rubric)
        # Lenient should not flag severe issues if score is adequate
        assert isinstance(v1.score, float)
        assert isinstance(v2.score, float)

    @pytest.mark.asyncio
    async def test_reach_consensus(self) -> None:
        judge = CrossModelJudge()
        verdicts = (
            ModelVerdict("m1", 0.8, "good", 0.9, ()),
            ModelVerdict("m2", 0.7, "ok", 0.8, ()),
            ModelVerdict("m3", 0.9, "excellent", 0.95, ()),
        )
        consensus = await judge.reach_consensus(verdicts)
        assert 0.7 <= consensus.consensus_score <= 0.9
        assert consensus.majority_opinion == "pass"
        assert len(consensus.dissenting_opinions) == 0

    @pytest.mark.asyncio
    async def test_reach_consensus_empty_raises(self) -> None:
        judge = CrossModelJudge()
        with pytest.raises(CrossModelError, match="No verdicts"):
            await judge.reach_consensus(())

    @pytest.mark.asyncio
    async def test_reach_consensus_single_raises(self) -> None:
        judge = CrossModelJudge()
        verdicts = (ModelVerdict("m1", 0.5, "avg", 0.5, ()),)
        with pytest.raises(CrossModelError, match="at least 2 verdicts"):
            await judge.reach_consensus(verdicts)

    @pytest.mark.asyncio
    async def test_reach_consensus_majority_fail(self) -> None:
        judge = CrossModelJudge()
        verdicts = (
            ModelVerdict("m1", 0.2, "bad", 0.8, ()),
            ModelVerdict("m2", 0.3, "poor", 0.7, ()),
            ModelVerdict("m3", 0.9, "good", 0.8, ()),
        )
        consensus = await judge.reach_consensus(verdicts)
        assert consensus.majority_opinion == "fail"

    @pytest.mark.asyncio
    async def test_reach_consensus_dissenting(self) -> None:
        judge = CrossModelJudge()
        verdicts = (
            ModelVerdict("m1", 0.8, "good", 0.9, ()),
            ModelVerdict("m2", 0.2, "bad", 0.8, ()),
        )
        consensus = await judge.reach_consensus(verdicts)
        assert len(consensus.dissenting_opinions) > 0

    @pytest.mark.asyncio
    async def test_judge_end_to_end(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template(
            "test", [RubricDimension("acc", 1.0, "d", "exact_match")]
        )
        result = await judge.judge("A comprehensive and detailed response", rubric)
        assert len(result.verdicts) == 3
        assert result.consensus_score >= 0.0

    @pytest.mark.asyncio
    async def test_judge_with_custom_panel(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template("t", [RubricDimension("a", 1.0, "d", "f")])
        panel = JudgePanel(
            models=(
                JudgeModel("m1", "c", "s", (0.0,)),
                JudgeModel("m2", "c", "s", (0.0,)),
            ),
            primary=JudgeModel("m1", "c", "s", (0.0,)),
            secondary=(JudgeModel("m2", "c", "s", (0.0,)),),
        )
        result = await judge.judge("test response", rubric, panel)
        assert len(result.verdicts) == 2

    @pytest.mark.asyncio
    async def test_judge_agreement_level_high(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template(
            "t", [RubricDimension("a", 1.0, "d", "exact_match")]
        )
        result = await judge.judge("unambiguous correct answer here", rubric)
        assert 0.0 <= result.agreement_level <= 1.0

    @pytest.mark.asyncio
    async def test_solicit_verdict_dissent_flags(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template(
            "t", [RubricDimension("a", 1.0, "d", "exact_match")]
        )
        model = JudgeModel("biased", "c", "s", (0.2, 0.2, 0.2))
        verdict = await judge.solicit_verdict(model, "x", rubric)
        # Bias adjustment should trigger a flag
        assert isinstance(verdict.dissent_flags, tuple)

    @pytest.mark.asyncio
    async def test_reach_consensus_split_opinion(self) -> None:
        judge = CrossModelJudge()
        verdicts = (
            ModelVerdict("m1", 0.6, "ok", 0.7, ()),
            ModelVerdict("m2", 0.4, "bad", 0.6, ()),
        )
        consensus = await judge.reach_consensus(verdicts)
        assert consensus.majority_opinion == "split"

    @pytest.mark.asyncio
    async def test_convene_panel_size(self) -> None:
        judge = CrossModelJudge()
        panel = await judge.convene_panel(num_judges=5)
        assert len(panel.models) == 5
        assert len(panel.secondary) == 4

    @pytest.mark.asyncio
    async def test_judge_with_different_responses(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template(
            "t", [RubricDimension("a", 1.0, "d", "exact_match")]
        )
        short = await judge.judge("short", rubric)
        long = await judge.judge(
            "A very long and detailed response that covers everything well", rubric
        )
        # Longer response should tend to score higher
        assert long.consensus_score >= short.consensus_score

    @pytest.mark.asyncio
    async def test_model_verdict_contains_reasoning(self) -> None:
        judge = CrossModelJudge()
        rubric = AdaptiveRubric().create_template(
            "t", [RubricDimension("a", 1.0, "d", "exact_match")]
        )
        verdict = await judge.solicit_verdict(
            JudgeModel("m", "c", "s", (0.0,)),
            "A perfect score response",
            rubric,
        )
        assert verdict.reasoning in (
            "High quality response",
            "Adequate response with minor issues",
            "Response needs significant improvement",
        )
