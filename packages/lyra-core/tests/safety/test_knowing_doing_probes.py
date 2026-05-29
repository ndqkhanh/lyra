"""Tests for Knowing-Doing Probes — bridging the knowledge-execution gap."""

import pytest
from lyra_core.safety.knowing_doing_probes import (
    GapReport,
    GapSeverity,
    KnowingDoingProbe,
    ProbeConfig,
    ProbeResult,
)


class TestGapSeverity:
    def test_severity_values(self):
        assert GapSeverity.NONE.value == "none"
        assert GapSeverity.MINOR.value == "minor"
        assert GapSeverity.MODERATE.value == "moderate"
        assert GapSeverity.SEVERE.value == "severe"
        assert GapSeverity.CRITICAL.value == "critical"


class TestProbeResult:
    def test_no_gap(self):
        result = ProbeResult(
            tool_name="bash",
            expected_action="ls -la",
            actual_action="ls -la",
            knowledge_confidence=0.95,
            execution_confidence=0.92,
            gap_score=0.03,
            severity=GapSeverity.NONE,
        )
        assert result.gap_score == 0.03
        assert result.severity == GapSeverity.NONE

    def test_severe_gap(self):
        result = ProbeResult(
            tool_name="deploy",
            expected_action="kubectl apply",
            actual_action="kubectl delete",
            knowledge_confidence=0.88,
            execution_confidence=0.34,
            gap_score=0.54,
            severity=GapSeverity.SEVERE,
        )
        assert result.gap_score > 0.5
        assert result.severity == GapSeverity.SEVERE

    def test_result_immutable(self):
        r = ProbeResult("t", "exp", "act", 0.8, 0.7, 0.1, GapSeverity.MINOR)
        with pytest.raises(Exception):
            r.gap_score = 0.9


class TestGapReport:
    def test_empty_report(self):
        report = GapReport(
            probes=(),
            mean_gap=0.0,
            max_gap=0.0,
            severe_count=0,
            overall_severity=GapSeverity.NONE,
        )
        assert report.mean_gap == 0.0

    def test_report_with_gaps(self):
        p1 = ProbeResult("t1", "e1", "a1", 0.9, 0.5, 0.4, GapSeverity.MODERATE)
        p2 = ProbeResult("t2", "e2", "a2", 0.85, 0.30, 0.55, GapSeverity.SEVERE)
        report = GapReport(
            probes=(p1, p2),
            mean_gap=0.475,
            max_gap=0.55,
            severe_count=1,
            overall_severity=GapSeverity.SEVERE,
        )
        assert len(report.probes) == 2
        assert report.max_gap == 0.55
        assert report.severe_count == 1

    def test_report_immutable(self):
        r = GapReport(
            probes=(), mean_gap=0.0, max_gap=0.0, severe_count=0, overall_severity=GapSeverity.NONE
        )
        with pytest.raises(Exception):
            r.mean_gap = 1.0


class TestProbeConfig:
    def test_default_config(self):
        config = ProbeConfig()
        assert config.gap_threshold_minor == 0.1
        assert config.gap_threshold_moderate == 0.25
        assert config.gap_threshold_severe == 0.4
        assert config.gap_threshold_critical == 0.6

    def test_custom_config(self):
        config = ProbeConfig(gap_threshold_minor=0.2, gap_threshold_critical=0.8)
        assert config.gap_threshold_minor == 0.2


class TestKnowingDoingProbe:
    def test_probe_small_gap(self):
        kdp = KnowingDoingProbe()
        result = kdp.probe(
            tool_name="read",
            expected_action="read_file",
            actual_action="read_file",
            knowledge_confidence=0.95,
            execution_confidence=0.94,
        )
        assert isinstance(result, ProbeResult)
        assert result.gap_score < 0.1

    def test_probe_large_gap(self):
        kdp = KnowingDoingProbe()
        result = kdp.probe(
            tool_name="deploy",
            expected_action="safe_deploy",
            actual_action="force_deploy",
            knowledge_confidence=0.90,
            execution_confidence=0.40,
        )
        assert result.gap_score > 0.3

    def test_generate_report_empty(self):
        kdp = KnowingDoingProbe()
        report = kdp.generate_report()
        assert report.mean_gap == 0.0
        assert report.overall_severity == GapSeverity.NONE

    def test_generate_report_with_probes(self):
        kdp = KnowingDoingProbe()
        kdp.probe("t1", "exp", "act", 0.9, 0.5)
        kdp.probe("t2", "exp", "act", 0.8, 0.3)
        report = kdp.generate_report()
        assert report.mean_gap > 0.0
        assert len(report.probes) == 2

    def test_config_custom_threshold(self):
        config = ProbeConfig(gap_threshold_minor=0.3)
        kdp = KnowingDoingProbe(config=config)
        assert kdp.config.gap_threshold_minor == 0.3

    def test_total_probes(self):
        kdp = KnowingDoingProbe()
        assert kdp.total_probes == 0
        kdp.probe("t", "e", "a", 0.8, 0.5)
        assert kdp.total_probes == 1

    def test_mean_gap_property(self):
        kdp = KnowingDoingProbe()
        assert kdp.mean_gap == 0.0
        kdp.probe("t1", "e", "a", 0.9, 0.4)
        kdp.probe("t2", "e", "a", 0.7, 0.3)
        assert kdp.mean_gap > 0.3
