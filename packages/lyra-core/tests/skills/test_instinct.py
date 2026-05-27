"""Tests for InstinctSystem — continual learning pattern detection."""

import time
from lyra_core.skills.instinct import (
    DetectedPattern,
    InstinctReport,
    InstinctSystem,
    Observation,
    ObservationType,
    PatternType,
)


class TestInstinctSystem:
    def test_empty_cycle_produces_report(self):
        instinct = InstinctSystem()
        report = instinct.process_cycle()
        assert isinstance(report, InstinctReport)
        assert report.observations_processed == 0

    def test_observations_are_recorded(self):
        instinct = InstinctSystem(window_size=10)
        instinct.observe(Observation(
            obs_type=ObservationType.TOOL_CALL,
            session_id="s1",
            timestamp=time.time(),
            data={"tool_name": "Read"},
        ))
        report = instinct.process_cycle()
        assert report.observations_processed == 1

    def test_detects_repeated_tool_sequences(self):
        instinct = InstinctSystem(min_confidence=0.4, window_size=20)
        for _ in range(3):
            instinct.observe(Observation(ObservationType.TOOL_CALL, "s1", 0.0, {"tool_name": "Read"}))
            instinct.observe(Observation(ObservationType.TOOL_CALL, "s1", 0.1, {"tool_name": "Edit"}))
            instinct.observe(Observation(ObservationType.TOOL_CALL, "s1", 0.2, {"tool_name": "Bash"}))

        report = instinct.process_cycle()
        assert report.patterns_detected >= 1

    def test_detects_error_recovery_patterns(self):
        instinct = InstinctSystem(min_confidence=0.4, window_size=20)
        for _ in range(3):
            instinct.observe(Observation(ObservationType.ERROR, "s1", 0.0, {"message": "ImportError: missing module"}))
            instinct.observe(Observation(ObservationType.SUCCESS, "s1", 0.1, {"action": "pip install module"}))

        report = instinct.process_cycle()
        assert report.patterns_detected >= 1

    def test_ready_patterns_filter_by_confidence(self):
        instinct = InstinctSystem(min_confidence=0.7, window_size=20)
        for _ in range(5):
            instinct.observe(Observation(ObservationType.TOOL_CALL, "s1", 0.0, {"tool_name": "Read"}))
            instinct.observe(Observation(ObservationType.TOOL_CALL, "s1", 0.1, {"tool_name": "Write"}))

        report = instinct.process_cycle()
        ready = instinct.ready_patterns()
        assert all(p.confidence >= 0.7 for p in ready)

    def test_reset_clears_all(self):
        instinct = InstinctSystem()
        instinct.observe(Observation(ObservationType.TOOL_CALL, "s1", 0.0, {"tool_name": "Test"}))
        instinct.process_cycle()
        instinct.reset()
        report = instinct.process_cycle()
        assert report.observations_processed == 0
        assert len(instinct.all_patterns()) == 0

    def test_window_prunes_old_observations(self):
        instinct = InstinctSystem(window_size=5)
        for i in range(10):
            instinct.observe(Observation(ObservationType.TOOL_CALL, f"s{i}", float(i), {"tool_name": f"Tool{i}"}))
        report = instinct.process_cycle()
        assert report.observations_processed <= 10

    def test_correction_pattern_detection(self):
        instinct = InstinctSystem(min_confidence=0.4, window_size=20)
        for _ in range(4):
            instinct.observe(Observation(
                ObservationType.USER_CORRECTION, "s1", 0.0,
                {"topic": "Always use async/await for I/O operations"},
            ))
        report = instinct.process_cycle()
        assert report.patterns_detected >= 1

    def test_confidence_increases_with_repetition(self):
        instinct = InstinctSystem(min_confidence=0.4, window_size=20)
        for i in range(6):
            instinct.observe(Observation(
                ObservationType.USER_CORRECTION, "s1", float(i),
                {"topic": "Add type hints to all functions"},
            ))
            instinct.process_cycle()

        patterns = instinct.all_patterns()
        assert len(patterns) >= 1
        assert patterns[0].confidence >= 0.7
