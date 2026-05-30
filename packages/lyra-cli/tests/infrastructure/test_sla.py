"""Tests for SLA tracking infrastructure."""

from __future__ import annotations

import pytest

from lyra_cli.infrastructure.sla_tracker import (
    SLAComplianceReport,
    SLADefinition,
    SLAMeasurement,
    SLATracker,
    SLAViolation,
    Severity,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def sla_tracker():
    return SLATracker()


@pytest.fixture
def sample_sla():
    return SLADefinition(
        name="api-availability",
        target=99.9,
        window_hours=24.0,
        metric_name="uptime_pct",
    )


# ── TestSLADefinition ─────────────────────────────────────────


class TestSLADefinition:
    def test_sla_creation(self):
        sla = SLADefinition(
            name="api-latency",
            target=99.0,
            window_hours=1.0,
            metric_name="latency_p95_ms",
        )
        assert sla.name == "api-latency"
        assert sla.target == 99.0
        assert sla.window_hours == 1.0

    def test_sla_immutability(self):
        sla = SLADefinition(name="uptime", target=99.9, window_hours=24.0,
                            metric_name="uptime_pct")
        with pytest.raises(Exception):
            sla.target = 95.0


# ── TestSLAMeasurement ────────────────────────────────────────


class TestSLAMeasurement:
    def test_measurement_compliant(self):
        m = SLAMeasurement(
            sla_name="api-availability",
            value=99.95,
            target=99.9,
        )
        assert m.is_compliant

    def test_measurement_violation(self):
        m = SLAMeasurement(
            sla_name="api-availability",
            value=98.5,
            target=99.9,
        )
        assert not m.is_compliant

    def test_measurement_immutability(self):
        m = SLAMeasurement(sla_name="uptime", value=99.9, target=99.9)
        with pytest.raises(Exception):
            m.value = 50.0


# ── TestSLAViolation ──────────────────────────────────────────


class TestSLAViolation:
    def test_violation_creation(self):
        v = SLAViolation(
            sla_name="api-availability",
            current_value=98.5,
            target=99.9,
            severity=Severity.HIGH,
        )
        assert v.sla_name == "api-availability"
        assert v.severity == Severity.HIGH

    def test_violation_immutability(self):
        v = SLAViolation(
            sla_name="latency",
            current_value=500.0,
            target=100.0,
            severity=Severity.CRITICAL,
        )
        with pytest.raises(Exception):
            v.severity = Severity.LOW


# ── TestSLAComplianceReport ───────────────────────────────────


class TestSLAComplianceReport:
    def test_report_creation(self):
        r = SLAComplianceReport(
            overall_compliance=99.5,
            total_slas=5,
            slas_in_violation=1,
        )
        assert r.overall_compliance == 99.5
        assert not r.is_overall_compliant  # has violations

    def test_report_compliant(self):
        r = SLAComplianceReport(
            overall_compliance=100.0,
            total_slas=5,
            slas_in_violation=0,
        )
        assert r.is_overall_compliant

    def test_report_not_compliant(self):
        r = SLAComplianceReport(
            overall_compliance=85.0,
            total_slas=5,
            slas_in_violation=3,
        )
        assert not r.is_overall_compliant

    def test_report_immutability(self):
        r = SLAComplianceReport(overall_compliance=99.0, total_slas=3,
                                slas_in_violation=0)
        with pytest.raises(Exception):
            r.overall_compliance = 50.0


# ── TestSLATrackerBasic ───────────────────────────────────────


class TestSLATrackerBasic:
    def test_empty_tracker(self, sla_tracker):
        assert sla_tracker.sla_count == 0

    def test_register_sla(self, sla_tracker, sample_sla):
        sla_tracker.register_sla(sample_sla)
        assert sla_tracker.sla_count == 1

    def test_register_duplicate_sla(self, sla_tracker, sample_sla):
        sla_tracker.register_sla(sample_sla)
        with pytest.raises(ValueError, match="already registered"):
            sla_tracker.register_sla(sample_sla)

    def test_get_sla(self, sla_tracker, sample_sla):
        sla_tracker.register_sla(sample_sla)
        result = sla_tracker.get_sla("api-availability")
        assert result is not None
        assert result.name == "api-availability"

    def test_get_sla_missing(self, sla_tracker):
        assert sla_tracker.get_sla("nonexistent") is None

    def test_unregister_sla(self, sla_tracker, sample_sla):
        sla_tracker.register_sla(sample_sla)
        sla_tracker.unregister_sla("api-availability")
        assert sla_tracker.sla_count == 0

    def test_record_measurement(self, sla_tracker, sample_sla):
        sla_tracker.register_sla(sample_sla)
        sla_tracker.record_measurement("api-availability", value=99.95)
        measurement = sla_tracker.get_latest_measurement("api-availability")
        assert measurement is not None
        assert measurement.value == 99.95

    def test_record_measurement_missing_sla(self, sla_tracker):
        with pytest.raises(ValueError, match="not registered"):
            sla_tracker.record_measurement("nonexistent", value=99.0)

    def test_get_measurements_in_window(self, sla_tracker, sample_sla):
        sla_tracker.register_sla(sample_sla)
        for i in range(5):
            sla_tracker.record_measurement("api-availability", value=99.9 + i * 0.01)
        measurements = sla_tracker.get_measurements("api-availability")
        assert len(measurements) == 5

    def test_check_compliance_all_good(self, sla_tracker):
        sla = SLADefinition(name="uptime", target=99.0, window_hours=24.0,
                            metric_name="uptime_pct")
        sla_tracker.register_sla(sla)
        sla_tracker.record_measurement("uptime", value=99.95)
        report = sla_tracker.check_compliance()
        assert report.slas_in_violation == 0

    def test_check_compliance_with_violation(self, sla_tracker):
        sla = SLADefinition(name="uptime", target=99.9, window_hours=24.0,
                            metric_name="uptime_pct")
        sla_tracker.register_sla(sla)
        sla_tracker.record_measurement("uptime", value=85.0)
        report = sla_tracker.check_compliance()
        assert report.slas_in_violation > 0

    def test_get_active_violations(self, sla_tracker):
        sla = SLADefinition(name="latency", target=99.0, window_hours=1.0,
                            metric_name="latency_p95_ms")
        sla_tracker.register_sla(sla)
        sla_tracker.record_measurement("latency", value=50.0)  # Below target
        violations = sla_tracker.get_active_violations()
        assert len(violations) > 0

    def test_get_active_violations_none(self, sla_tracker):
        sla = SLADefinition(name="uptime", target=99.0, window_hours=24.0,
                            metric_name="uptime_pct")
        sla_tracker.register_sla(sla)
        sla_tracker.record_measurement("uptime", value=99.99)
        violations = sla_tracker.get_active_violations()
        assert len(violations) == 0

    def test_get_compliance_report(self, sla_tracker):
        sla_tracker.register_sla(
            SLADefinition(name="uptime", target=99.0, window_hours=24.0,
                          metric_name="uptime_pct")
        )
        sla_tracker.register_sla(
            SLADefinition(name="latency", target=95.0, window_hours=1.0,
                          metric_name="latency_p95_ms")
        )
        sla_tracker.record_measurement("uptime", value=99.95)
        sla_tracker.record_measurement("latency", value=98.0)
        report = sla_tracker.get_compliance_report()
        assert report.total_slas == 2
        assert report.overall_compliance > 0

    def test_get_violation_history(self, sla_tracker):
        sla = SLADefinition(name="uptime", target=99.9, window_hours=24.0,
                            metric_name="uptime_pct")
        sla_tracker.register_sla(sla)
        sla_tracker.record_measurement("uptime", value=50.0)
        sla_tracker.record_measurement("uptime", value=99.99)  # back to good
        history = sla_tracker.get_violation_history("uptime")
        assert len(history) >= 1

    def test_get_violation_history_missing(self, sla_tracker):
        history = sla_tracker.get_violation_history("nonexistent")
        assert len(history) == 0

    def test_reset(self, sla_tracker, sample_sla):
        sla_tracker.register_sla(sample_sla)
        sla_tracker.record_measurement("api-availability", value=99.95)
        sla_tracker.reset()
        assert sla_tracker.sla_count == 0


class TestSeverity:
    def test_severity_values(self):
        assert Severity.CRITICAL is not None
        assert Severity.HIGH is not None
        assert Severity.MEDIUM is not None
        assert Severity.LOW is not None
