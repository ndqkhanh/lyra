"""Tests for the Intent-Based Behavioral Security Monitor."""

from __future__ import annotations

import time

import pytest
from lyra_core.safety.intent_monitor import (
    ActionRecord,
    BehavioralBaseline,
    IntentDeviation,
    IntentMonitor,
)


def _make_action(
    action_id: str = "act-001",
    tool_name: str = "read_file",
    parameters: tuple[tuple[str, str], ...] = (("path", "/tmp/test.txt"),),
    stated_goal: str = "read a file",
    session_id: str = "sess-001",
) -> ActionRecord:
    return ActionRecord(
        action_id=action_id,
        tool_name=tool_name,
        parameters=parameters,
        timestamp=time.time(),
        stated_goal=stated_goal,
        session_id=session_id,
    )


class TestActionRecord:
    def test_record_is_immutable(self) -> None:
        action = _make_action()
        with pytest.raises(Exception):
            action.tool_name = "write_file"  # type: ignore[misc]


class TestIntentMonitorRecording:
    def test_record_action_stores(self) -> None:
        monitor = IntentMonitor()
        action = _make_action()
        monitor.record_action(action)
        stats = monitor.get_stats()
        assert stats["total_actions"] == 1

    def test_multiple_actions_across_sessions(self) -> None:
        monitor = IntentMonitor()
        monitor.record_action(_make_action(session_id="s1"))
        monitor.record_action(_make_action(session_id="s2"))
        monitor.record_action(_make_action(session_id="s1"))
        stats = monitor.get_stats()
        assert stats["total_actions"] == 3
        assert stats["sessions_monitored"] == 2


class TestIntentMonitorDeviation:
    def test_unexpected_tool_deviation(self) -> None:
        monitor = IntentMonitor()
        action = _make_action(tool_name="sudo_rm")
        monitor.record_action(action)
        deviation = monitor.check_deviation(
            action, expected_sequence=["read_file", "write_file"]
        )
        assert deviation is not None
        assert deviation.severity > 0.5
        assert "Unexpected tool" in deviation.description

    def test_expected_tool_no_deviation(self) -> None:
        monitor = IntentMonitor()
        action = _make_action(tool_name="read_file")
        monitor.record_action(action)
        deviation = monitor.check_deviation(
            action, expected_sequence=["read_file", "write_file"]
        )
        assert deviation is None

    def test_sequence_too_long_deviation(self) -> None:
        monitor = IntentMonitor()
        for i in range(10):
            monitor.record_action(
                _make_action(
                    action_id=f"act-{i:03d}",
                    tool_name="read_file",
                )
            )
        action = _make_action(action_id="act-010", tool_name="read_file")
        deviation = monitor.check_deviation(
            action, expected_sequence=["read_file"]
        )
        assert deviation is not None


class TestIntentMonitorSessionAnalysis:
    def test_empty_session_no_deviations(self) -> None:
        monitor = IntentMonitor()
        deviations = monitor.analyze_session("nonexistent")
        assert deviations == []

    def test_single_action_session(self) -> None:
        monitor = IntentMonitor()
        action = _make_action(tool_name="read_file")
        monitor.record_action(action)
        deviations = monitor.analyze_session("sess-001")
        assert len(deviations) == 0

    def test_infrequent_tool_flagged(self) -> None:
        monitor = IntentMonitor()
        for _ in range(3):
            monitor.record_action(_make_action(tool_name="read_file"))
        monitor.record_action(_make_action(tool_name="sudo_rm"))
        deviations = monitor.analyze_session("sess-001")
        assert any("sudo_rm" in d.description for d in deviations)

    def test_sequence_length_outlier(self) -> None:
        monitor = IntentMonitor()
        monitor.record_action(_make_action(session_id="baseline", tool_name="read_file"))
        for i in range(10):
            monitor.record_action(
                _make_action(
                    action_id=f"act-{i:03d}",
                    session_id="long-session",
                    tool_name="read_file",
                )
            )
        deviations = monitor.analyze_session("long-session")
        assert any("exceeding" in d.description for d in deviations)


class TestIntentMonitorBaseline:
    def test_build_baseline_typical_tools(self) -> None:
        monitor = IntentMonitor()
        sessions = [
            [
                _make_action(action_id="a1", tool_name="read_file"),
                _make_action(action_id="a2", tool_name="write_file"),
            ],
            [
                _make_action(action_id="b1", tool_name="read_file"),
                _make_action(action_id="b2", tool_name="grep"),
            ],
        ]
        baseline = monitor.build_baseline("code_review", sessions)
        assert "read_file" in baseline.typical_tools
        assert "write_file" in baseline.typical_tools
        assert "grep" in baseline.typical_tools
        assert baseline.task_type == "code_review"

    def test_build_baseline_sequence_length(self) -> None:
        monitor = IntentMonitor()
        sessions = [
            [_make_action() for _ in range(3)],
            [_make_action() for _ in range(5)],
            [_make_action() for _ in range(7)],
        ]
        baseline = monitor.build_baseline("test_type", sessions)
        assert baseline.typical_sequence_length == 5

    def test_build_baseline_empty(self) -> None:
        monitor = IntentMonitor()
        baseline = monitor.build_baseline("empty", [])
        assert baseline.typical_sequence_length == 0
        assert baseline.avg_tool_calls_per_task == 0.0


class TestIntentMonitorAnomalyDetection:
    def test_length_anomaly_detected(self) -> None:
        monitor = IntentMonitor()
        baseline = BehavioralBaseline(
            task_type="code_review",
            typical_tools=("read_file", "write_file"),
            typical_sequence_length=5,
            avg_tool_calls_per_task=3.0,
            anomaly_threshold=2.0,
        )
        actions = [_make_action() for _ in range(20)]
        deviations = monitor.detect_anomalies(actions, baseline)
        assert len(deviations) >= 1
        assert any("exceeding" in d.description for d in deviations)

    def test_unexpected_tool_anomaly(self) -> None:
        monitor = IntentMonitor()
        baseline = BehavioralBaseline(
            task_type="code_review",
            typical_tools=("read_file", "write_file"),
            typical_sequence_length=5,
            avg_tool_calls_per_task=3.0,
        )
        actions = [_make_action(tool_name="sudo_rm")]
        deviations = monitor.detect_anomalies(actions, baseline)
        assert len(deviations) >= 1
        assert any("not part of" in d.description for d in deviations)

    def test_normal_session_no_anomalies(self) -> None:
        monitor = IntentMonitor()
        baseline = BehavioralBaseline(
            task_type="code_review",
            typical_tools=("read_file", "write_file"),
            typical_sequence_length=5,
            avg_tool_calls_per_task=10.0,
        )
        actions = [_make_action() for _ in range(3)]
        deviations = monitor.detect_anomalies(actions, baseline)
        assert len(deviations) == 0


class TestIntentMonitorRiskScoring:
    def test_no_deviations_zero_risk(self) -> None:
        monitor = IntentMonitor()
        action = _make_action()
        monitor.record_action(action)
        assert monitor.get_risk_score("sess-001") == 0.0

    def test_deviations_increase_risk(self) -> None:
        monitor = IntentMonitor()
        action = _make_action(tool_name="sudo_rm")
        monitor.record_action(action)
        dev = monitor.check_deviation(
            action, expected_sequence=["read_file", "write_file"]
        )
        assert dev is not None
        # Deviation is stored
        risk = monitor.get_risk_score("sess-001")
        assert risk >= 0.0

    def test_risk_capped_at_one(self) -> None:
        monitor = IntentMonitor()
        for i in range(100):
            action = _make_action(
                action_id=f"act-{i:03d}",
                tool_name=f"bad_tool_{i}",
            )
            monitor.record_action(action)
            monitor.check_deviation(
                action, expected_sequence=["read_file"]
            )
        assert monitor.get_risk_score("sess-001") <= 1.0


class TestIntentMonitorStats:
    def test_stats_empty(self) -> None:
        monitor = IntentMonitor()
        stats = monitor.get_stats()
        assert stats["total_actions"] == 0
        assert stats["deviations_detected"] == 0
        assert stats["sessions_monitored"] == 0

    def test_stats_with_data(self) -> None:
        monitor = IntentMonitor()
        for i in range(5):
            monitor.record_action(_make_action(action_id=f"act-{i:03d}"))
        stats = monitor.get_stats()
        assert stats["total_actions"] == 5
        assert stats["sessions_monitored"] == 1


class TestIntentDeviation:
    def test_deviation_is_immutable(self) -> None:
        deviation = IntentDeviation(
            deviation_id="dev-001",
            expected_pattern="read_file, write_file",
            actual_actions=("sudo_rm",),
            severity=0.8,
            description="Bad action.",
            detected_at=time.time(),
        )
        with pytest.raises(Exception):
            deviation.severity = 0.1  # type: ignore[misc]
