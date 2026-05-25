"""Tests for DomainEvaluator."""

from __future__ import annotations

import pytest

from lyra_eval_pipeline import (
    DomainEvalConfig,
    DomainEvalReport,
    DomainEvaluator,
    EvalResult,
    EvalSample,
)
from lyra_eval_pipeline.exceptions import DomainEvalError


class TestDomainEvalConfig:
    def test_config_creation(self) -> None:
        config = DomainEvalConfig(
            domain="math",
            metrics=("accuracy", "speed"),
        )
        assert config.domain == "math"
        assert config.metrics == ("accuracy", "speed")
        assert config.threshold == 0.7
        assert config.max_samples == 1000

    def test_config_frozen(self) -> None:
        config = DomainEvalConfig(domain="code", metrics=("pass@1",))
        with pytest.raises(AttributeError):
            config.domain = "math"  # type: ignore[misc]

    def test_config_custom_threshold(self) -> None:
        config = DomainEvalConfig(
            domain="custom", metrics=("m1",), threshold=0.85, max_samples=500
        )
        assert config.threshold == 0.85
        assert config.max_samples == 500


class TestEvalSample:
    def test_sample_creation(self) -> None:
        sample = EvalSample(
            sample_id="s1",
            input_text="What is 2+2?",
            expected_output="4",
        )
        assert sample.sample_id == "s1"
        assert sample.input_text == "What is 2+2?"
        assert sample.expected_output == "4"

    def test_sample_default_metadata(self) -> None:
        sample = EvalSample(sample_id="s2", input_text="q", expected_output="a")
        assert sample.metadata == ()

    def test_sample_with_metadata(self) -> None:
        sample = EvalSample(
            sample_id="s3",
            input_text="q",
            expected_output="a",
            metadata=(("difficulty", "hard"), ("category", "algebra")),
        )
        assert len(sample.metadata) == 2


class TestEvalResult:
    def test_result_creation(self) -> None:
        result = EvalResult(
            sample_id="s1",
            domain="math",
            metric_scores=(("accuracy", 0.95),),
            overall_score=0.95,
            passed=True,
            latency_ms=10.5,
        )
        assert result.sample_id == "s1"
        assert result.passed
        assert result.latency_ms == 10.5

    def test_result_not_passed(self) -> None:
        result = EvalResult(
            sample_id="s2",
            domain="math",
            metric_scores=(("accuracy", 0.3),),
            overall_score=0.3,
            passed=False,
            latency_ms=5.0,
        )
        assert not result.passed


class TestDomainEvalReport:
    def test_report_creation(self) -> None:
        report = DomainEvalReport(
            domain="math",
            results=(),
            pass_rate=0.8,
            avg_score=0.85,
            avg_latency_ms=100.0,
        )
        assert report.domain == "math"
        assert report.pass_rate == 0.8
        assert report.avg_score == 0.85


class TestDomainEvaluator:
    @pytest.mark.asyncio
    async def test_add_and_get_config(self) -> None:
        evaluator = DomainEvaluator()
        config = DomainEvalConfig(domain="math", metrics=("accuracy",))
        evaluator.add_config(config)
        retrieved = evaluator.get_config("math")
        assert retrieved is config

    @pytest.mark.asyncio
    async def test_get_config_unknown_raises(self) -> None:
        evaluator = DomainEvaluator()
        with pytest.raises(DomainEvalError, match="No config found"):
            evaluator.get_config("nonexistent")

    @pytest.mark.asyncio
    async def test_load_samples_known_domain(self) -> None:
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        samples = await evaluator.load_samples("math")
        assert len(samples) == 5
        assert samples[0].sample_id == "math-001"

    @pytest.mark.asyncio
    async def test_load_samples_unknown_domain_raises(self) -> None:
        evaluator = DomainEvaluator()
        with pytest.raises(DomainEvalError, match="Unknown domain"):
            await evaluator.load_samples("physics")

    @pytest.mark.asyncio
    async def test_load_samples_respects_max(self) -> None:
        evaluator = DomainEvaluator(
            configs=(
                DomainEvalConfig(
                    domain="code", metrics=("acc",), max_samples=2
                ),
            )
        )
        samples = await evaluator.load_samples("code")
        assert len(samples) == 2

    @pytest.mark.asyncio
    async def test_evaluate_sample_basic(self) -> None:
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        sample = EvalSample(sample_id="t1", input_text="2+2", expected_output="4")
        config = evaluator.get_config("math")
        result = await evaluator.evaluate_sample(sample, config)
        assert result.sample_id == "t1"
        assert isinstance(result.overall_score, float)
        assert isinstance(result.passed, bool)
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_evaluate_domain_report(self) -> None:
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        report = await evaluator.evaluate_domain("math")
        assert report.domain == "math"
        assert len(report.results) == 5
        assert report.pass_rate >= 0.0
        assert report.avg_score >= 0.0

    @pytest.mark.asyncio
    async def test_evaluate_domain_no_config_raises(self) -> None:
        evaluator = DomainEvaluator()
        with pytest.raises(DomainEvalError, match="No config found"):
            await evaluator.evaluate_domain("math")

    @pytest.mark.asyncio
    async def test_evaluate_all_domains(self) -> None:
        evaluator = DomainEvaluator(
            configs=(
                DomainEvalConfig(domain="math", metrics=("acc",)),
                DomainEvalConfig(domain="code", metrics=("acc",)),
            )
        )
        reports = await evaluator.evaluate_all_domains()
        assert len(reports) == 2
        domains = {r.domain for r in reports}
        assert domains == {"math", "code"}

    @pytest.mark.asyncio
    async def test_evaluate_all_domains_no_configs_raises(self) -> None:
        evaluator = DomainEvaluator()
        with pytest.raises(DomainEvalError, match="No domains configured"):
            await evaluator.evaluate_all_domains()

    @pytest.mark.asyncio
    async def test_domains_property(self) -> None:
        evaluator = DomainEvaluator(
            configs=(
                DomainEvalConfig(domain="math", metrics=("acc",)),
                DomainEvalConfig(domain="reasoning", metrics=("acc",)),
            )
        )
        assert "math" in evaluator.domains
        assert "reasoning" in evaluator.domains
        assert len(evaluator.domains) == 2

    @pytest.mark.asyncio
    async def test_domains_property_empty(self) -> None:
        evaluator = DomainEvaluator()
        assert evaluator.domains == ()

    @pytest.mark.asyncio
    async def test_evaluate_domain_passing_threshold(self) -> None:
        evaluator = DomainEvaluator(
            configs=(
                DomainEvalConfig(
                    domain="math", metrics=("acc",), threshold=0.0
                ),
            )
        )
        report = await evaluator.evaluate_domain("math")
        assert report.pass_rate == 1.0

    @pytest.mark.asyncio
    async def test_evaluate_sample_metrics(self) -> None:
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        sample = EvalSample(sample_id="m1", input_text="2+2", expected_output="4")
        config = evaluator.get_config("math")
        result = await evaluator.evaluate_sample(sample, config)
        assert len(result.metric_scores) == 3
        metric_names = [m[0] for m in result.metric_scores]
        assert "accuracy" in metric_names
        assert "relevance" in metric_names
        assert "completeness" in metric_names

    @pytest.mark.asyncio
    async def test_evaluate_domain_reasoning(self) -> None:
        evaluator = DomainEvaluator(
            configs=(
                DomainEvalConfig(domain="reasoning", metrics=("acc",)),
            )
        )
        report = await evaluator.evaluate_domain("reasoning")
        assert report.domain == "reasoning"
        assert len(report.results) == 5

    @pytest.mark.asyncio
    async def test_constructor_with_configs(self) -> None:
        c1 = DomainEvalConfig(domain="math", metrics=("m1",))
        c2 = DomainEvalConfig(domain="code", metrics=("m1",))
        evaluator = DomainEvaluator(configs=(c1, c2))
        assert evaluator.get_config("math") is c1
        assert evaluator.get_config("code") is c2
