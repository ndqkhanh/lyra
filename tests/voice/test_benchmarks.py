"""Tests for the voice pipeline benchmark framework.

Covers MetricCollector, ContinuousMonitor, TauVoiceBridge, and
FDB-v3 metric computation.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from lyra.voice.benchmarks import (
    BenchmarkError,
    BenchmarkMetric,
    BenchmarkReport,
    ContinuousMonitor,
    FDBV3Metrics,
    FDBV3_CASCADED_BASELINE,
    FDBV3_GPT_REALTIME,
    MetricCollector,
    PercentileResult,
    PipelineStage,
    TauVoiceBridge,
)


# ===================================================================
# MetricCollector tests
# ===================================================================


class TestMetricCollector:
    """Tests for the MetricCollector."""

    def test_creation(self) -> None:
        mc = MetricCollector()
        assert mc.total_samples() == 0
        assert mc.utterance_count() == 0

    def test_record_single_sample(self) -> None:
        mc = MetricCollector()
        mc.record("stt", 150.0)
        assert mc.stage_count("stt") == 1
        assert mc.total_samples() == 1

    def test_record_multiple_samples(self) -> None:
        mc = MetricCollector()
        for i in range(5):
            mc.record("stt", 100.0 + i)
        assert mc.stage_count("stt") == 5
        assert mc.total_samples() == 5

    def test_record_with_utterance_id(self) -> None:
        mc = MetricCollector()
        mc.record("stt", 150.0, utterance_id="utt-1")
        mc.record("tts", 200.0, utterance_id="utt-1")
        assert mc.utterance_count() == 1
        mc.record("stt", 100.0, utterance_id="utt-2")
        assert mc.utterance_count() == 2

    def test_record_with_metadata(self) -> None:
        mc = MetricCollector()
        mc.record("stt", 150.0, utterance_id="utt-1", metadata={"model": "whisper"})
        assert mc.stage_count("stt") == 1

    def test_record_latency_enum(self) -> None:
        mc = MetricCollector()
        mc.record_latency(PipelineStage.STT, 150.0)
        assert mc.stage_count("stt") == 1

    def test_percentiles_single_stage(self) -> None:
        mc = MetricCollector()
        for v in [100.0, 200.0, 300.0, 400.0, 500.0]:
            mc.record("stt", v)

        results = mc.percentiles()
        assert len(results) == 1
        stt = results[0]
        assert stt.stage == "stt"
        assert stt.count == 5
        assert stt.min_ms == 100.0
        assert stt.max_ms == 500.0
        assert stt.mean_ms == 300.0
        assert stt.p50_ms == 300.0
        assert stt.p95_ms == 500.0
        assert stt.p99_ms == 500.0

    def test_percentiles_multiple_stages(self) -> None:
        mc = MetricCollector()
        mc.record("stt", 150.0)
        mc.record("tts", 200.0)
        mc.record("router", 50.0)

        results = mc.percentiles()
        assert len(results) == 3
        stage_names = [r.stage for r in results]
        assert "stt" in stage_names
        assert "tts" in stage_names
        assert "router" in stage_names

    def test_percentiles_empty(self) -> None:
        mc = MetricCollector()
        results = mc.percentiles()
        assert results == []

    def test_stage_count_unknown(self) -> None:
        mc = MetricCollector()
        assert mc.stage_count("unknown") == 0

    def test_clear(self) -> None:
        mc = MetricCollector()
        mc.record("stt", 150.0)
        mc.record("tts", 200.0, utterance_id="utt-1")
        mc.clear()
        assert mc.total_samples() == 0
        assert mc.utterance_count() == 0

    def test_as_report(self) -> None:
        mc = MetricCollector()
        mc.record("stt", 150.0)
        mc.record("tts", 200.0)
        report = mc.as_report(duration_s=10.0)
        assert isinstance(report, BenchmarkReport)
        assert report.sample_count == 2
        assert report.duration_s == 10.0
        assert len(report.latency_results) == 2

    def test_percentiles_custom_percentiles(self) -> None:
        mc = MetricCollector()
        for v in range(1, 101):
            mc.record("stt", float(v))

        results = mc.percentiles(percentiles=[50, 90])
        assert len(results) == 1
        # p50 uses index int(100 * 50 / 100) = 50 → value 51.0
        assert results[0].p50_ms == 51.0

    def test_as_report_fdbv3_metrics(self) -> None:
        mc = MetricCollector()
        mc.record("stt", 150.0)
        mc.record("end_to_end", 2000.0)
        report = mc.as_report()
        assert report.fdbv3_metrics.end_to_end_latency_s == 2.0
        assert report.fdbv3_metrics.turn_take_reliability >= 0

    def test_as_report_fdbv3_empty(self) -> None:
        mc = MetricCollector()
        report = mc.as_report()
        assert report.fdbv3_metrics.end_to_end_latency_s == 0.0
        assert report.fdbv3_metrics.sample_count == 0


# ===================================================================
# PipelineStage enum tests
# ===================================================================


class TestPipelineStage:
    """Tests for PipelineStage enum."""

    def test_values(self) -> None:
        assert PipelineStage.STT.value == "stt"
        assert PipelineStage.TTS.value == "tts"
        assert PipelineStage.CAPTURE.value == "capture"
        assert PipelineStage.VAD.value == "vad"
        assert PipelineStage.AEC.value == "aec"
        assert PipelineStage.END_TO_END.value == "end_to_end"
        assert PipelineStage.END_TO_END in PipelineStage

    def test_all_stages(self) -> None:
        stages = list(PipelineStage)
        assert len(stages) == 13


# ===================================================================
# FDBV3Metrics tests
# ===================================================================


class TestFDBV3Metrics:
    """Tests for FDBV3Metrics dataclass."""

    def test_defaults(self) -> None:
        m = FDBV3Metrics()
        assert m.tool_selection_f1 == 0.0
        assert m.self_correction_pass_at_1 == 0.0
        assert m.turn_take_reliability == 0.0
        assert m.end_to_end_latency_s == 0.0

    def test_custom_values(self) -> None:
        m = FDBV3Metrics(
            tool_selection_f1=0.8,
            self_correction_pass_at_1=0.5,
            turn_take_reliability=1.0,
            end_to_end_latency_s=5.0,
            sample_count=100,
        )
        assert m.tool_selection_f1 == 0.8
        assert m.sample_count == 100


# ===================================================================
# BenchmarkReport tests
# ===================================================================


class TestBenchmarkReport:
    """Tests for BenchmarkReport dataclass."""

    def test_defaults(self) -> None:
        report = BenchmarkReport(
            latency_results=[],
            fdbv3_metrics=FDBV3Metrics(),
        )
        assert report.latency_results == []
        assert report.sample_count == 0
        assert report.duration_s == 0.0


# ===================================================================
# ContinuousMonitor tests
# ===================================================================


class TestContinuousMonitor:
    """Tests for the ContinuousMonitor."""

    def test_creation(self) -> None:
        monitor = ContinuousMonitor(window_size=100, report_interval_s=60.0)
        assert monitor.last_report is None

    def test_record_stage(self) -> None:
        monitor = ContinuousMonitor()
        monitor.record_stage(PipelineStage.STT, 150.0)
        samples = monitor._collector._samples["stt"]
        assert len(samples) == 1

    def test_record_sample(self) -> None:
        monitor = ContinuousMonitor()
        monitor.record_sample("stt", 150.0)
        assert monitor._collector.stage_count("stt") == 1

    def test_snapshot(self) -> None:
        monitor = ContinuousMonitor()
        monitor.record_stage(PipelineStage.STT, 150.0)
        monitor.record_stage(PipelineStage.TTS, 200.0)
        report = monitor.snapshot()
        assert isinstance(report, BenchmarkReport)
        assert report.sample_count >= 2

    def test_snapshot_empty(self) -> None:
        monitor = ContinuousMonitor()
        report = monitor.snapshot()
        assert isinstance(report, BenchmarkReport)
        assert report.latency_results == []

    def test_should_report_initially(self) -> None:
        monitor = ContinuousMonitor(report_interval_s=0.0)
        assert monitor.should_report() is True

    def test_should_report_after_interval(self) -> None:
        monitor = ContinuousMonitor(report_interval_s=0.01)
        assert monitor.should_report() is True
        monitor._last_report_time = time.monotonic()
        assert monitor.should_report() is False

    def test_report_if_needed_returns_none(self) -> None:
        monitor = ContinuousMonitor(report_interval_s=3600.0)
        monitor._last_report_time = time.monotonic()
        result = monitor.report_if_needed()
        assert result is None

    def test_report_if_needed_returns_report(self) -> None:
        monitor = ContinuousMonitor(report_interval_s=0.0)
        result = monitor.report_if_needed()
        assert isinstance(result, BenchmarkReport)

    def test_sliding_window(self) -> None:
        monitor = ContinuousMonitor(window_size=3)
        for i in range(10):
            monitor.record_stage(PipelineStage.STT, float(i))
        samples = monitor._collector._samples["stt"]
        assert len(samples) == 3  # Only 3 kept

    def test_reset(self) -> None:
        monitor = ContinuousMonitor()
        monitor.record_stage(PipelineStage.STT, 150.0)
        monitor.reset()
        assert monitor._collector.total_samples() == 0
        assert monitor.last_report is None


# ===================================================================
# TauVoiceBridge tests
# ===================================================================


class TestTauVoiceBridge:
    """Tests for the tau-Voice integration bridge."""

    def test_creation_with_default_collector(self) -> None:
        bridge = TauVoiceBridge()
        assert bridge.collector.total_samples() == 0

    def test_creation_with_custom_collector(self) -> None:
        mc = MetricCollector()
        bridge = TauVoiceBridge(collector=mc)
        assert bridge.collector is mc

    def test_on_turn_start(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_turn_start("utt-1")
        assert bridge.collector.stage_count("end_to_end") == 1

    def test_on_asr_complete(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_asr_complete("utt-1", 150.0)
        assert bridge.collector.stage_count("stt") == 1

    def test_on_llm_complete(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_llm_complete("utt-1", 500.0)
        assert bridge.collector.stage_count("llm_inference") == 1

    def test_on_tts_complete(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_tts_complete("utt-1", 200.0)
        assert bridge.collector.stage_count("tts") == 1

    def test_on_turn_complete(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_turn_complete("utt-1", 2000.0, metadata={"tool_call": True})
        samples = bridge.collector._samples["end_to_end"]
        assert len(samples) == 1
        assert samples[0] == 2000.0

    def test_on_turn_complete_without_metadata(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_turn_complete("utt-1", 1500.0)
        assert bridge.collector.stage_count("end_to_end") == 1

    def test_on_tool_call_correct(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_tool_call("search", correct=True)
        assert bridge.collector.stage_count("tool_selection_f1") == 1

    def test_on_tool_call_incorrect(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_tool_call("delete", correct=False)
        assert bridge.collector.stage_count("tool_selection_f1") == 1

    def test_on_interruption(self) -> None:
        bridge = TauVoiceBridge()
        bridge.on_interruption("utt-1", coherence_score=3.5)
        assert bridge.collector.stage_count("user_interruption_coherence") == 1


# ===================================================================
# FDB-v3 baseline constants tests
# ===================================================================


class TestFDBV3Baselines:
    """Tests for FDB-v3 baseline constants."""

    def test_cascaded_baseline(self) -> None:
        assert FDBV3_CASCADED_BASELINE["tool_selection_f1"] == 0.803
        assert FDBV3_CASCADED_BASELINE["self_correction_pass_at_1"] == 0.176

    def test_gpt_realtime(self) -> None:
        assert FDBV3_GPT_REALTIME["tool_selection_f1"] == 0.876
        assert FDBV3_GPT_REALTIME["end_to_end_latency_s"] == 6.89
