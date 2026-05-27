"""Tests for Stagnation-Stop Detection (Plan 33.1.2)."""

import pytest

from lyra_core.stagnation import StagnationDetector


class TestStagnationDetector:
    def test_no_stagnation_below_threshold(self):
        det = StagnationDetector(max_repeats=3)
        assert not det.check("output 1").stagnated
        assert not det.check("output 2").stagnated

    def test_detects_stagnation(self):
        det = StagnationDetector(max_repeats=3)
        det.check("same output")
        det.check("same output")
        result = det.check("same output")
        assert result.stagnated
        assert result.consecutive_count == 3

    def test_different_output_breaks_chain(self):
        det = StagnationDetector(max_repeats=3)
        det.check("same")
        det.check("same")
        det.check("different")
        result = det.check("same")
        assert not result.stagnated

    def test_normalize_whitespace(self):
        det = StagnationDetector(max_repeats=2)
        det.check("hello   world")
        result = det.check("hello world")
        assert result.stagnated

    def test_normalize_newlines(self):
        det = StagnationDetector(max_repeats=2)
        det.check("hello\n\nworld")
        result = det.check("hello world")
        assert result.stagnated

    def test_reason_includes_count(self):
        det = StagnationDetector(max_repeats=2)
        det.check("x")
        result = det.check("x")
        assert "2" in result.reason

    def test_repeated_output_truncated(self):
        det = StagnationDetector(max_repeats=2)
        long_output = "x" * 300
        det.check(long_output)
        result = det.check(long_output)
        assert len(result.repeated_output) <= 200

    def test_reset_clears_history(self):
        det = StagnationDetector(max_repeats=2)
        det.check("x")
        det.reset()
        assert not det.check("x").stagnated

    def test_record_different_output(self):
        det = StagnationDetector(max_repeats=3)
        det.check("x")
        det.check("x")
        det.record_different_output("y")
        result = det.check("x")
        assert not result.stagnated

    def test_stagnation_rate(self):
        det = StagnationDetector(max_repeats=2)
        assert det.stagnation_rate == 0.0
        for _ in range(5):
            det.check("a")
            det.check("a")
            det.check("b")
        assert det.stagnation_rate > 0.0

    def test_max_repeats_must_be_at_least_2(self):
        with pytest.raises(ValueError):
            StagnationDetector(max_repeats=1)

    def test_custom_threshold(self):
        det = StagnationDetector(max_repeats=5)
        for _ in range(4):
            assert not det.check("same").stagnated
        assert det.check("same").stagnated

    def test_empty_output(self):
        det = StagnationDetector(max_repeats=2)
        det.check("")
        result = det.check("")
        assert result.stagnated
