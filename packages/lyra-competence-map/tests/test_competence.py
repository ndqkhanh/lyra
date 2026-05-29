"""Tests for Competence Map package."""

from lyra_competence_map import CompetenceMap, RegressionDetector


class TestCompetenceMap:
    def test_record_attempt(self):
        m = CompetenceMap()
        e = m.record_attempt("ctx:python", "code_gen", True)
        assert e.skill_name == "code_gen"
        assert e.total_attempts == 1

    def test_best_skill(self):
        m = CompetenceMap()
        for _ in range(5):
            m.record_attempt("ctx:python", "code_gen", True)
        for _ in range(3):
            m.record_attempt("ctx:python", "debug", False)
        best = m.best_skill_for_context("ctx:python")
        assert best == "code_gen"

    def test_no_skill_for_unknown_context(self):
        m = CompetenceMap()
        best = m.best_skill_for_context("unknown")
        assert best is None

    def test_stats(self):
        m = CompetenceMap()
        m.record_attempt("ctx:a", "skill1", True)
        m.record_attempt("ctx:b", "skill2", True)
        s = m.stats
        assert s["total_entries"] == 2


class TestRegressionDetector:
    def test_no_regression_without_baseline(self):
        d = RegressionDetector()
        assert not d.check_regression("unknown", 0.5)

    def test_regression_detected(self):
        d = RegressionDetector(threshold=0.1)
        d.set_baseline("code_gen", 0.9)
        assert d.check_regression("code_gen", 0.5)
