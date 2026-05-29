"""Tests for lyra_otel_tracer.drift_integrator."""

from __future__ import annotations

import pytest
from lyra_otel_tracer.drift_integrator import (
    DriftConfig,
    DriftIntegrator,
    DriftMeasurement,
    DriftReport,
)
from lyra_otel_tracer.exceptions import DriftIntegrationError


class TestDriftConfig:
    def test_drift_config_defaults(self) -> None:
        config = DriftConfig()
        assert config.window_size == 100
        assert config.drift_threshold == 0.1
        assert config.metrics == ("latency", "token_count", "cost")

    def test_drift_config_custom(self) -> None:
        config = DriftConfig(window_size=50, drift_threshold=0.2, metrics=("latency",))
        assert config.window_size == 50
        assert config.metrics == ("latency",)


class TestDriftMeasurement:
    def test_drift_measurement_creation(self) -> None:
        m = DriftMeasurement(
            metric="latency",
            reference_mean=100.0,
            current_mean=200.0,
            drift_magnitude=1.0,
            is_drifting=True,
            ks_statistic=0.5,
        )
        assert m.metric == "latency"
        assert m.is_drifting

    def test_drift_measurement_frozen(self) -> None:
        m = DriftMeasurement(
            metric="latency", reference_mean=0, current_mean=0,
            drift_magnitude=0, is_drifting=False, ks_statistic=0,
        )
        with pytest.raises(AttributeError):
            m.metric = "changed"  # type: ignore[misc]


class TestDriftReport:
    def test_drift_report_creation(self) -> None:
        report = DriftReport(overall_drift_score=0.5, requires_attention=True)
        assert report.overall_drift_score == 0.5
        assert report.requires_attention
        assert report.measurements == ()

    def test_drift_report_frozen(self) -> None:
        report = DriftReport()
        with pytest.raises(AttributeError):
            report.overall_drift_score = 1.0  # type: ignore[misc]


class TestDriftIntegrator:
    @pytest.mark.asyncio
    async def test_feed_sample(self) -> None:
        integrator = DriftIntegrator()
        await integrator.feed_sample("latency", 100.0)
        assert "latency" in integrator._samples
        assert integrator._samples["latency"] == [100.0]

    @pytest.mark.asyncio
    async def test_feed_sample_unknown_metric(self) -> None:
        integrator = DriftIntegrator()
        with pytest.raises(DriftIntegrationError, match="Unknown metric"):
            await integrator.feed_sample("unknown_metric", 1.0)

    @pytest.mark.asyncio
    async def test_check_drift_no_data(self) -> None:
        integrator = DriftIntegrator()
        report = await integrator.check_drift()
        assert not report.requires_attention
        assert len(report.measurements) == 3  # latency, token_count, cost

    @pytest.mark.asyncio
    async def test_check_drift_insufficient_data(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10))
        for _ in range(5):
            await integrator.feed_sample("latency", 100.0)
        report = await integrator.check_drift()
        assert not report.requires_attention

    @pytest.mark.asyncio
    async def test_check_drift_no_drift(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10, drift_threshold=0.5))
        for _ in range(30):
            await integrator.feed_sample("latency", 100.0)
        report = await integrator.check_drift()
        # All values are the same, so no drift should be detected
        assert not report.requires_attention

    @pytest.mark.asyncio
    async def test_check_drift_detected(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10, drift_threshold=0.1))
        # Baseline: first 10 samples = 100
        for _ in range(10):
            await integrator.feed_sample("latency", 100.0)
        # Current: next 10 samples shifted to 200
        for _ in range(10):
            await integrator.feed_sample("latency", 200.0)
        report = await integrator.check_drift()
        assert report.requires_attention
        assert len(report.measurements) == 3

    @pytest.mark.asyncio
    async def test_check_drift_multiple_metrics(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10, drift_threshold=0.1))
        for _ in range(10):
            await integrator.feed_sample("latency", 100.0)
            await integrator.feed_sample("token_count", 500.0)
            await integrator.feed_sample("cost", 0.5)
        for _ in range(10):
            await integrator.feed_sample("latency", 200.0)
            await integrator.feed_sample("token_count", 500.0)
            await integrator.feed_sample("cost", 0.5)
        report = await integrator.check_drift()
        measurements = {m.metric: m for m in report.measurements}
        assert measurements["latency"].is_drifting
        assert not measurements["token_count"].is_drifting

    @pytest.mark.asyncio
    async def test_reset_baseline(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10))
        for _ in range(20):
            await integrator.feed_sample("latency", 100.0)
        integrator._baseline["latency"] = 100.0
        assert "latency" in integrator._baseline
        await integrator.reset_baseline()
        assert integrator._baseline == {}

    @pytest.mark.asyncio
    async def test_get_drift_history(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10))
        for _ in range(20):
            await integrator.feed_sample("latency", 100.0)
        history = await integrator.get_drift_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_window_size_enforced(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=5))
        for _ in range(20):
            await integrator.feed_sample("latency", 100.0)
        assert len(integrator._samples["latency"]) <= 10  # 2 * window_size

    @pytest.mark.asyncio
    async def test_recommendations_no_drift(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10))
        for _ in range(20):
            await integrator.feed_sample("latency", 100.0)
            await integrator.feed_sample("token_count", 500.0)
            await integrator.feed_sample("cost", 0.5)
        report = await integrator.check_drift()
        assert len(report.recommendations) >= 1
        assert "No drift detected" in report.recommendations[0]

    @pytest.mark.asyncio
    async def test_recommendations_with_drift(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=5, drift_threshold=0.01))
        for _ in range(5):
            await integrator.feed_sample("latency", 100.0)
        for _ in range(5):
            await integrator.feed_sample("latency", 500.0)
        report = await integrator.check_drift()
        has_drift_recs = any(
            "latency" in r and "drift" in r for r in report.recommendations
        )
        assert has_drift_recs

    @pytest.mark.asyncio
    async def test_ks_statistic_calculation(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=5))
        ref = [1.0, 2.0, 3.0, 4.0, 5.0]
        cur = [1.0, 2.0, 3.0, 4.0, 10.0]
        ks = integrator._compute_ks_statistic(ref, cur)
        assert ks > 0.0

    @pytest.mark.asyncio
    async def test_ks_statistic_identical(self) -> None:
        integrator = DriftIntegrator()
        ref = [1.0, 2.0, 3.0]
        cur = [1.0, 2.0, 3.0]
        ks = integrator._compute_ks_statistic(ref, cur)
        assert ks == 0.0

    @pytest.mark.asyncio
    async def test_ks_statistic_empty(self) -> None:
        integrator = DriftIntegrator()
        ks = integrator._compute_ks_statistic([], [1.0, 2.0])
        assert ks == 0.0

    @pytest.mark.asyncio
    async def test_overall_drift_score_calculation(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=5, drift_threshold=10.0))
        for _ in range(5):
            await integrator.feed_sample("latency", 100.0)
        for _ in range(5):
            await integrator.feed_sample("latency", 200.0)
        report = await integrator.check_drift()
        assert report.overall_drift_score >= 0.0

    @pytest.mark.asyncio
    async def test_baseline_initialization_after_window(self) -> None:
        integrator = DriftIntegrator(DriftConfig(window_size=10))
        for _ in range(10):
            await integrator.feed_sample("latency", 100.0)
        assert integrator._baseline.get("latency") == 100.0
