"""Tests for the evolution_metrics module."""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest
from lyra_meta_editor import (
    EvolutionConfig,
    EvolutionCycle,
    EvolutionMetrics,
    EvolutionMetricsError,
    EvolutionReport,
)


@pytest.fixture
def metrics() -> EvolutionMetrics:
    """Create EvolutionMetrics with a temp data dir."""
    tmpdir = tempfile.mkdtemp()
    cfg = EvolutionConfig(data_dir=tmpdir)
    m = EvolutionMetrics(cfg)
    yield m
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestEvolutionConfig:
    """Tests for EvolutionConfig."""

    def test_defaults(self) -> None:
        cfg = EvolutionConfig()
        assert cfg.track_cycles is True
        assert cfg.baseline_file == ""
        assert cfg.data_dir == ""


class TestEvolutionCycle:
    """Tests for EvolutionCycle."""

    def test_creation(self) -> None:
        c = EvolutionCycle(
            cycle_id=1,
            timestamp=1000.0,
            files_changed=3,
            quality_delta=0.5,
            perf_delta=0.2,
            test_delta=10,
        )
        assert c.cycle_id == 1
        assert c.quality_delta == 0.5
        assert c.test_delta == 10

    def test_immutable(self) -> None:
        c = EvolutionCycle(1, 1.0, 0, 0.0, 0.0, 0)
        with pytest.raises(AttributeError):
            c.cycle_id = 99  # type: ignore[misc]


class TestEvolutionReport:
    """Tests for EvolutionReport."""

    def test_empty_report(self) -> None:
        report = EvolutionReport(
            cycles=(),
            total_cycles=0,
            quality_trend=(),
            convergence_rate=0.0,
        )
        assert report.total_cycles == 0

    def test_with_cycles(self) -> None:
        cycles = (
            EvolutionCycle(1, 1.0, 2, 0.1, 0.2, 5),
            EvolutionCycle(2, 2.0, 3, 0.3, 0.4, 10),
        )
        report = EvolutionReport(
            cycles=cycles,
            total_cycles=2,
            quality_trend=(0.1, 0.3),
            convergence_rate=0.95,
        )
        assert report.total_cycles == 2
        assert report.convergence_rate == 0.95


class TestEvolutionMetrics:
    """Tests for EvolutionMetrics."""

    @pytest.mark.asyncio
    async def test_record_cycle(self, metrics: EvolutionMetrics) -> None:
        cycle = await metrics.record_cycle(
            files_changed=5, quality=0.8, perf=0.6, tests=20
        )
        assert cycle.cycle_id == 1
        assert cycle.files_changed == 5
        assert cycle.quality_delta == 0.8

    @pytest.mark.asyncio
    async def test_record_cycle_increments_id(
        self, metrics: EvolutionMetrics
    ) -> None:
        c1 = await metrics.record_cycle(1, 0.1, 0.1, 1)
        c2 = await metrics.record_cycle(2, 0.2, 0.2, 2)
        assert c1.cycle_id == 1
        assert c2.cycle_id == 2

    @pytest.mark.asyncio
    async def test_record_cycle_disabled(self) -> None:
        cfg = EvolutionConfig(track_cycles=False)
        m = EvolutionMetrics(cfg)
        with pytest.raises(EvolutionMetricsError, match="disabled"):
            await m.record_cycle(1, 0.1, 0.1, 1)

    @pytest.mark.asyncio
    async def test_get_progress_empty(self, metrics: EvolutionMetrics) -> None:
        report = await metrics.get_progress()
        assert report.total_cycles == 0
        assert report.quality_trend == ()

    @pytest.mark.asyncio
    async def test_get_progress_with_cycles(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(2, 0.5, 0.3, 10)
        await metrics.record_cycle(3, 0.7, 0.4, 15)
        report = await metrics.get_progress()
        assert report.total_cycles == 2
        assert len(report.quality_trend) == 2

    @pytest.mark.asyncio
    async def test_get_progress_trend_order(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(1, 0.1, 0.1, 1)
        await metrics.record_cycle(2, 0.2, 0.2, 2)
        await metrics.record_cycle(3, 0.3, 0.3, 3)
        report = await metrics.get_progress()
        assert report.quality_trend == (0.1, 0.2, 0.3)

    @pytest.mark.asyncio
    async def test_estimate_convergence_few_cycles(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(1, 1.0, 1.0, 1)
        conv = await metrics.estimate_convergence()
        assert conv == 0.0  # less than 2 cycles

    @pytest.mark.asyncio
    async def test_estimate_convergence_two_cycles(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(1, 0.5, 0.3, 5)
        await metrics.record_cycle(2, 0.7, 0.4, 8)
        conv = await metrics.estimate_convergence()
        assert conv == 0.5  # 2 cycles = intermediate

    @pytest.mark.asyncio
    async def test_estimate_convergence_three_cycles(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(1, 0.1, 0.1, 1)
        await metrics.record_cycle(2, 0.2, 0.2, 2)
        await metrics.record_cycle(3, 0.25, 0.25, 3)
        conv = await metrics.estimate_convergence()
        assert 0.0 <= conv <= 1.0

    @pytest.mark.asyncio
    async def test_compare_to_baseline_not_found(
        self, metrics: EvolutionMetrics
    ) -> None:
        with pytest.raises(EvolutionMetricsError, match="not found"):
            await metrics.compare_to_baseline("/nonexistent.json")

    @pytest.mark.asyncio
    async def test_compare_to_baseline_with_data(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(2, 0.8, 0.5, 15)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cycles": [], "avg_quality": 0.5, "avg_perf": 0.3}, f)
            baseline = f.name
        try:
            comparison = await metrics.compare_to_baseline(baseline)
            assert comparison["current_cycles"] == 1
            assert comparison["baseline_path"] == baseline
        finally:
            os.unlink(baseline)

    @pytest.mark.asyncio
    async def test_compare_to_baseline_no_current_cycles(
        self, metrics: EvolutionMetrics
    ) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cycles": [1, 2, 3], "avg_quality": 0.5, "avg_perf": 0.3}, f)
            baseline = f.name
        try:
            comparison = await metrics.compare_to_baseline(baseline)
            assert comparison["quality_comparison"] == {}
        finally:
            os.unlink(baseline)

    @pytest.mark.asyncio
    async def test_persistence(self) -> None:
        tmpdir = tempfile.mkdtemp()
        cfg = EvolutionConfig(data_dir=tmpdir)
        m1 = EvolutionMetrics(cfg)
        await m1.record_cycle(3, 0.9, 0.8, 25)
        await m1.record_cycle(4, 0.95, 0.85, 30)

        # Create a new instance pointing to the same dir
        m2 = EvolutionMetrics(cfg)
        report = await m2.get_progress()
        assert report.total_cycles == 2

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_persistence_corrupted(self) -> None:
        tmpdir = tempfile.mkdtemp()
        # Write invalid JSON
        with open(os.path.join(tmpdir, "cycles.json"), "w") as f:
            f.write("not valid json")
        cfg = EvolutionConfig(data_dir=tmpdir)
        m = EvolutionMetrics(cfg)
        # Should handle gracefully
        report = await m.get_progress()
        assert report.total_cycles == 0

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_estimate_convergence_empty(
        self, metrics: EvolutionMetrics
    ) -> None:
        conv = await metrics.estimate_convergence()
        assert conv == 0.0

    @pytest.mark.asyncio
    async def test_record_cycle_timestamp(
        self, metrics: EvolutionMetrics
    ) -> None:
        before = time.time()
        cycle = await metrics.record_cycle(1, 0.5, 0.3, 5)
        after = time.time()
        assert before <= cycle.timestamp <= after

    @pytest.mark.asyncio
    async def test_record_cycle_negative_deltas(
        self, metrics: EvolutionMetrics
    ) -> None:
        cycle = await metrics.record_cycle(5, -0.1, -0.2, -3)
        assert cycle.quality_delta == -0.1
        assert cycle.perf_delta == -0.2
        assert cycle.test_delta == -3

    @pytest.mark.asyncio
    async def test_convergence_rate_in_report(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(1, 0.8, 0.6, 10)
        await metrics.record_cycle(2, 0.85, 0.65, 12)
        report = await metrics.get_progress()
        assert report.convergence_rate >= 0.0

    @pytest.mark.asyncio
    async def test_compare_to_baseline_invalid_json(
        self, metrics: EvolutionMetrics
    ) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("broken json {")
            baseline = f.name
        try:
            with pytest.raises(EvolutionMetricsError, match="read"):
                await metrics.compare_to_baseline(baseline)
        finally:
            os.unlink(baseline)

    @pytest.mark.asyncio
    async def test_multiple_records_preserve_order(
        self, metrics: EvolutionMetrics
    ) -> None:
        await metrics.record_cycle(1, 0.0, 0.0, 0)
        await metrics.record_cycle(5, 0.5, 0.5, 5)
        await metrics.record_cycle(3, 1.0, 1.0, 10)
        report = await metrics.get_progress()
        assert [c.files_changed for c in report.cycles] == [1, 5, 3]

    def test_custom_data_dir(self) -> None:
        tmpdir = tempfile.mkdtemp()
        cfg = EvolutionConfig(data_dir=tmpdir)
        EvolutionMetrics(cfg)
        assert os.path.isdir(tmpdir)
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
