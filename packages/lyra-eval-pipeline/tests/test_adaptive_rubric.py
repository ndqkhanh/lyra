"""Tests for AdaptiveRubric."""

from __future__ import annotations

import pytest

from lyra_eval_pipeline import AdaptiveRubric, RubricDimension, RubricResult, RubricScore, RubricTemplate
from lyra_eval_pipeline.exceptions import RubricError


class TestRubricDimension:
    def test_dimension_creation(self) -> None:
        dim = RubricDimension(
            name="accuracy",
            weight=0.5,
            description="Factual correctness",
            scoring_function="exact_match",
        )
        assert dim.name == "accuracy"
        assert dim.weight == 0.5

    def test_dimension_frozen(self) -> None:
        dim = RubricDimension("n", 0.5, "d", "f")
        with pytest.raises(AttributeError):
            dim.name = "changed"  # type: ignore[misc]


class TestRubricScore:
    def test_score_creation(self) -> None:
        score = RubricScore(
            dimension="accuracy",
            raw_score=0.9,
            weighted_score=0.45,
            confidence=0.8,
        )
        assert score.dimension == "accuracy"
        assert score.raw_score == 0.9
        assert score.weighted_score == 0.45


class TestRubricResult:
    def test_result_creation(self) -> None:
        result = RubricResult(
            scores=(),
            total_score=0.75,
            grade="B+",
            calibration_factor=1.0,
        )
        assert result.total_score == 0.75
        assert result.grade == "B+"


class TestRubricTemplate:
    def test_template_creation(self) -> None:
        dim = RubricDimension("accuracy", 1.0, "desc", "exact_match")
        template = RubricTemplate(
            name="test_template",
            dimensions=(dim,),
            version="1.0",
            pearson_r=0.79,
        )
        assert template.name == "test_template"
        assert template.pearson_r == 0.79


class TestAdaptiveRubric:
    @pytest.mark.asyncio
    async def test_create_template(self) -> None:
        rubric = AdaptiveRubric()
        dimensions = [
            RubricDimension("accuracy", 0.5, "Correctness", "exact_match"),
            RubricDimension("relevance", 0.3, "Relevance", "keyword_match"),
            RubricDimension("completeness", 0.2, "Completeness", "length_based"),
        ]
        template = rubric.create_template("eval_v1", dimensions)
        assert template.name == "eval_v1"
        assert len(template.dimensions) == 3
        assert template.version.startswith("1.")

    @pytest.mark.asyncio
    async def test_create_template_empty_raises(self) -> None:
        rubric = AdaptiveRubric()
        with pytest.raises(RubricError, match="at least one dimension"):
            rubric.create_template("empty", [])

    @pytest.mark.asyncio
    async def test_create_template_bad_weights_raises(self) -> None:
        rubric = AdaptiveRubric()
        dimensions = [
            RubricDimension("a", 0.3, "desc", "f"),
            RubricDimension("b", 0.3, "desc", "f"),
        ]
        with pytest.raises(RubricError, match="weights must sum to 1"):
            rubric.create_template("bad", dimensions)

    @pytest.mark.asyncio
    async def test_score_response(self) -> None:
        rubric = AdaptiveRubric()
        dims = [RubricDimension("accuracy", 1.0, "desc", "exact_match")]
        template = rubric.create_template("test", dims)
        result = await rubric.score_response("correct answer", template)
        assert len(result.scores) == 1
        assert result.total_score >= 0.0
        assert result.total_score <= 1.0
        assert result.grade in ("A+", "A", "B+", "B", "C", "D", "F")

    @pytest.mark.asyncio
    async def test_score_response_empty_raises(self) -> None:
        rubric = AdaptiveRubric()
        dims = [RubricDimension("a", 1.0, "d", "f")]
        template = rubric.create_template("t", dims)
        with pytest.raises(RubricError, match="empty response"):
            await rubric.score_response("", template)

    @pytest.mark.asyncio
    async def test_score_multiple_dimensions(self) -> None:
        rubric = AdaptiveRubric()
        dims = [
            RubricDimension("a", 0.5, "d1", "exact_match"),
            RubricDimension("b", 0.5, "d2", "keyword_match"),
        ]
        template = rubric.create_template("t", dims)
        result = await rubric.score_response("test response with content", template)
        assert len(result.scores) == 2
        assert result.scores[0].dimension == "a"
        assert result.scores[1].dimension == "b"

    @pytest.mark.asyncio
    async def test_calibrate_empty(self) -> None:
        rubric = AdaptiveRubric()
        factor = await rubric.calibrate([])
        assert factor == 1.0

    @pytest.mark.asyncio
    async def test_calibrate_with_results(self) -> None:
        rubric = AdaptiveRubric()
        results = [
            RubricResult(
                scores=(),
                total_score=0.5,
                grade="C",
                calibration_factor=1.0,
            ),
            RubricResult(
                scores=(),
                total_score=0.7,
                grade="B",
                calibration_factor=1.0,
            ),
        ]
        factor = await rubric.calibrate(results)
        assert 0.1 <= factor <= 5.0

    @pytest.mark.asyncio
    async def test_auto_adjust_thresholds(self) -> None:
        rubric = AdaptiveRubric()
        dims = [RubricDimension("accuracy", 1.0, "d", "exact_match")]
        template = rubric.create_template("t", dims)
        result = await rubric.score_response("good response", template)
        adjusted = await rubric.auto_adjust_thresholds([result, result])
        assert adjusted.name == "auto_adjusted"
        assert len(adjusted.dimensions) == 1

    @pytest.mark.asyncio
    async def test_auto_adjust_empty_raises(self) -> None:
        rubric = AdaptiveRubric()
        with pytest.raises(RubricError, match="No domain results"):
            await rubric.auto_adjust_thresholds([])

    @pytest.mark.asyncio
    async def test_auto_adjust_adjusts_weights(self) -> None:
        rubric = AdaptiveRubric()
        dims = [
            RubricDimension("acc", 0.5, "d", "exact_match"),
            RubricDimension("rel", 0.5, "d", "keyword_match"),
        ]
        template = rubric.create_template("t", dims)
        short_response = rubric.create_template("short", [
            RubricDimension("acc", 0.5, "d", "exact_match"),
            RubricDimension("rel", 0.5, "d", "keyword_match"),
        ])
        result = await rubric.score_response("good answer", template)
        adjusted = await rubric.auto_adjust_thresholds([result])
        total_weight = sum(d.weight for d in adjusted.dimensions)
        assert abs(total_weight - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_score_with_keyword_match(self) -> None:
        rubric = AdaptiveRubric()
        dims = [RubricDimension("kw", 1.0, "d", "keyword_match")]
        template = rubric.create_template("t", dims)
        result = await rubric.score_response("one two three four five six", template)
        assert result.total_score >= 0.0
        assert result.scores[0].raw_score >= 0.0

    @pytest.mark.asyncio
    async def test_score_with_length_based(self) -> None:
        rubric = AdaptiveRubric()
        dims = [RubricDimension("len", 1.0, "d", "length_based")]
        template = rubric.create_template("t", dims)
        result = await rubric.score_response("A" * 100, template)
        assert result.total_score >= 0.0

    @pytest.mark.asyncio
    async def test_version_increments(self) -> None:
        rubric = AdaptiveRubric()
        d = [RubricDimension("a", 1.0, "d", "f")]
        t1 = rubric.create_template("t", d)
        t2 = rubric.create_template("t", d)
        assert t2.version > t1.version

    @pytest.mark.asyncio
    async def test_grade_boundaries(self) -> None:
        rubric = AdaptiveRubric()
        d = [RubricDimension("a", 1.0, "d", "exact_match")]
        template = rubric.create_template("t", d)
        r1 = await rubric.score_response("perfect answer here very good excellent", template)
        assert isinstance(r1.grade, str)
        assert len(r1.grade) > 0

    @pytest.mark.asyncio
    async def test_calibration_in_applies_to_scoring(self) -> None:
        rubric = AdaptiveRubric()
        d = [RubricDimension("a", 1.0, "d", "exact_match")]
        template = rubric.create_template("t", d)
        result = await rubric.score_response("test", template)
        assert result.calibration_factor == 1.0

    @pytest.mark.asyncio
    async def test_score_result_has_confidence(self) -> None:
        rubric = AdaptiveRubric()
        d = [RubricDimension("a", 1.0, "d", "exact_match")]
        template = rubric.create_template("t", d)
        result = await rubric.score_response("a response with enough length", template)
        for score in result.scores:
            assert 0.0 <= score.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_calibrate_scales_factor(self) -> None:
        rubric = AdaptiveRubric()
        # Very low score -> calibration should try to boost, but clamped to max 5.0
        results = [RubricResult(scores=(), total_score=0.1, grade="F", calibration_factor=1.0)]
        factor = await rubric.calibrate(results)
        assert factor == 5.0  # target 0.75 / 0.1 = 7.5, clamped to max 5.0

    @pytest.mark.asyncio
    async def test_calibrate_very_high_scores(self) -> None:
        rubric = AdaptiveRubric()
        results = [RubricResult(scores=(), total_score=0.95, grade="A", calibration_factor=1.0)]
        factor = await rubric.calibrate(results)
        assert factor < 1.0
        assert factor >= 0.1
