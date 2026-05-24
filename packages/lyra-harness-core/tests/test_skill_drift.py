"""Tests for harness_core.skill_drift."""
from __future__ import annotations

import pytest

from harness_core.provenance import WitnessLattice
from harness_core.skill_drift import (
    DriftAlert,
    DriftPolicy,
    SkillDriftMonitor,
    SkillInvocation,
)


# --- DriftPolicy validation ------------------------------------------


class TestDriftPolicy:
    def test_default(self):
        p = DriftPolicy()
        assert p.recent_window == 10
        assert p.warning_drift < p.critical_drift

    def test_invalid_recent_window(self):
        with pytest.raises(ValueError):
            DriftPolicy(recent_window=0)

    def test_invalid_min_baseline(self):
        with pytest.raises(ValueError):
            DriftPolicy(min_baseline_invocations=1)

    def test_inverted_thresholds_rejected(self):
        # warning > critical → invalid.
        with pytest.raises(ValueError):
            DriftPolicy(warning_drift=0.5, critical_drift=0.2)

    def test_threshold_above_one(self):
        with pytest.raises(ValueError):
            DriftPolicy(critical_drift=1.5)


# --- SkillInvocation -------------------------------------------------


class TestSkillInvocation:
    def test_basic(self):
        i = SkillInvocation.create(skill_id="x", succeeded=True, score=0.9)
        assert i.skill_id == "x"
        assert i.succeeded
        assert i.score == 0.9

    def test_clamp_score(self):
        i = SkillInvocation.create(skill_id="x", succeeded=True, score=1.5)
        assert i.score == 1.0
        i2 = SkillInvocation.create(skill_id="x", succeeded=True, score=-0.5)
        assert i2.score == 0.0

    def test_empty_skill_rejected(self):
        with pytest.raises(ValueError):
            SkillInvocation(
                invocation_id="a", skill_id="", succeeded=True,
                score=1.0, timestamp=0.0,
            )


# --- Monitor --------------------------------------------------------


class TestMonitorRecording:
    def test_record_appends(self):
        mon = SkillDriftMonitor()
        for i in range(5):
            mon.record(skill_id="x", succeeded=True)
        assert len(mon.invocations_for("x")) == 5
        assert mon.known_skills() == ["x"]

    def test_record_per_skill_independent(self):
        mon = SkillDriftMonitor()
        for _ in range(3):
            mon.record(skill_id="x", succeeded=True)
        for _ in range(7):
            mon.record(skill_id="y", succeeded=False, score=0.0)
        assert sorted(mon.known_skills()) == ["x", "y"]
        assert len(mon.invocations_for("x")) == 3
        assert len(mon.invocations_for("y")) == 7


class TestBaselineAndRecent:
    def test_returns_none_when_insufficient_history(self):
        mon = SkillDriftMonitor()
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True)
        # default min_baseline_invocations=20 → not enough yet.
        assert mon.baseline_rate("x") is None
        # default recent_window=10 → also not enough yet.
        assert mon.recent_rate("x") is None

    def test_baseline_uses_first_n(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        )
        # First 5 succeed, next 5 fail.
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True, score=1.0)
        for _ in range(5):
            mon.record(skill_id="x", succeeded=False, score=0.0)
        assert mon.baseline_rate("x") == pytest.approx(1.0)

    def test_recent_uses_last_window(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        )
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True, score=1.0)
        for _ in range(3):
            mon.record(skill_id="x", succeeded=False, score=0.0)
        assert mon.recent_rate("x") == pytest.approx(0.0)


class TestDriftAlerting:
    def test_no_drift_no_alert(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        )
        for _ in range(8):
            mon.record(skill_id="x", succeeded=True)
        assert mon.check("x") is None

    def test_critical_drift_severity(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(
                min_baseline_invocations=5, recent_window=3,
                info_drift=0.05, warning_drift=0.10, critical_drift=0.30,
            ),
        )
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True, score=1.0)
        for _ in range(3):
            mon.record(skill_id="x", succeeded=False, score=0.0)
        alert = mon.check("x")
        assert alert is not None
        assert alert.severity == "critical"
        assert alert.drift == pytest.approx(1.0)

    def test_warning_drift_severity(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(
                min_baseline_invocations=10, recent_window=10,
                info_drift=0.05, warning_drift=0.10, critical_drift=0.30,
            ),
        )
        # Baseline = 1.0 over 10. Recent: 8/10 succeed → 0.8. Drift = 0.2.
        # 0.2 in (warning_drift=0.10, critical_drift=0.30] → "warning".
        for _ in range(10):
            mon.record(skill_id="x", succeeded=True, score=1.0)
        for i in range(10):
            mon.record(skill_id="x", succeeded=(i < 8), score=1.0 if i < 8 else 0.0)
        alert = mon.check("x")
        assert alert is not None
        assert alert.severity == "warning"

    def test_info_drift_severity(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(
                min_baseline_invocations=10, recent_window=10,
                info_drift=0.05, warning_drift=0.20, critical_drift=0.30,
            ),
        )
        # Baseline 1.0; recent 0.9 → drift = 0.1 → in (info=0.05, warn=0.20] → "info".
        for _ in range(10):
            mon.record(skill_id="x", succeeded=True, score=1.0)
        for i in range(10):
            mon.record(skill_id="x", succeeded=(i < 9), score=1.0 if i < 9 else 0.0)
        alert = mon.check("x")
        assert alert is not None
        assert alert.severity == "info"

    def test_check_all_returns_only_alerting_skills(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        )
        # x degrades; y stays good.
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True, score=1.0)
        for _ in range(3):
            mon.record(skill_id="x", succeeded=False, score=0.0)
        for _ in range(8):
            mon.record(skill_id="y", succeeded=True, score=1.0)
        alerts = mon.check_all()
        assert len(alerts) == 1
        assert alerts[0].skill_id == "x"

    def test_alerts_persisted(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        )
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True)
        for _ in range(3):
            mon.record(skill_id="x", succeeded=False)
        mon.check("x")
        mon.check("x")
        # check() called twice → two persisted alerts (each reflects a snapshot).
        assert len(mon.alerts()) == 2

    def test_witness_emitted(self):
        lattice = WitnessLattice()
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
            lattice=lattice,
        )
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True)
        for _ in range(3):
            mon.record(skill_id="x", succeeded=False)
        alert = mon.check("x")
        assert alert is not None
        # Witness recorded.
        ws = lattice.ledger.witnesses_for()
        assert len(ws) == 1
        assert ws[0].issued_by == "skill-drift-monitor"
        assert ws[0].content["action"] == "drift_alert"

    def test_no_lattice_no_witness(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        )
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True)
        for _ in range(3):
            mon.record(skill_id="x", succeeded=False)
        # No exception when lattice not wired.
        assert mon.check("x") is not None


class TestStats:
    def test_stats_basic(self):
        mon = SkillDriftMonitor()
        for _ in range(3):
            mon.record(skill_id="x", succeeded=True, score=1.0)
        for _ in range(2):
            mon.record(skill_id="x", succeeded=False, score=0.0)
        s = mon.stats()
        assert "x" in s
        assert s["x"]["n_invocations"] == 5
        assert s["x"]["success_rate"] == pytest.approx(0.6)
        assert s["x"]["n_alerts"] == 0

    def test_stats_includes_alert_count(self):
        mon = SkillDriftMonitor(
            policy=DriftPolicy(min_baseline_invocations=5, recent_window=3),
        )
        for _ in range(5):
            mon.record(skill_id="x", succeeded=True)
        for _ in range(3):
            mon.record(skill_id="x", succeeded=False)
        mon.check("x")
        s = mon.stats()
        assert s["x"]["n_alerts"] == 1


# --- DriftAlert validation -------------------------------------------


class TestDriftAlert:
    def test_invalid_severity(self):
        with pytest.raises(ValueError):
            DriftAlert(
                skill_id="x",
                baseline_rate=1.0, recent_rate=0.5, drift=0.5,
                n_baseline=10, n_recent=5,
                severity="ALARMING",  # invalid
            )
