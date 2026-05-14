"""Tests for Phase K — EvoSkills co-evolutionary verification."""
import pytest

from lyra_evolution.evoverifier import (
    CoEvolutionGate,
    IsolatedVerifier,
    VerificationOutcome,
    VerificationReport,
    VerificationTask,
)


class _AlwaysPass:
    """Stub runner: always returns True."""
    def run(self, _skill_content: str, _task: VerificationTask) -> bool:
        return True


class _AlwaysFail:
    """Stub runner: always returns False."""
    def run(self, _skill_content: str, _task: VerificationTask) -> bool:
        return False


class _ContentRunner:
    """Stub runner: returns True iff skill_content contains task.expected_outcome."""
    def run(self, skill_content: str, task: VerificationTask) -> bool:
        return task.expected_outcome in skill_content


def _task(tid="t1", ctx="web") -> VerificationTask:
    return VerificationTask(
        task_id=tid,
        description=f"task {tid}",
        expected_outcome="ok",
        context_tag=ctx,
    )


class TestVerificationReport:
    def test_frozen(self):
        r = VerificationReport("s", VerificationOutcome.PASS, 1.0, "all good")
        with pytest.raises((AttributeError, TypeError)):
            r.score = 0.5  # type: ignore[misc]


class TestIsolatedVerifier:
    def test_empty_task_pool_inconclusive(self):
        v = IsolatedVerifier()
        report = v.verify("s", "content", _AlwaysPass())
        assert report.outcome == VerificationOutcome.INCONCLUSIVE

    def test_all_pass_above_threshold(self):
        v = IsolatedVerifier(pass_threshold=0.70)
        v.register_task(_task("t1"))
        v.register_task(_task("t2"))
        report = v.verify("s", "content", _AlwaysPass())
        assert report.outcome == VerificationOutcome.PASS
        assert report.score == pytest.approx(1.0)

    def test_all_fail_below_threshold(self):
        v = IsolatedVerifier(pass_threshold=0.70)
        v.register_task(_task("t1"))
        report = v.verify("s", "content", _AlwaysFail())
        assert report.outcome == VerificationOutcome.FAIL
        assert report.score == pytest.approx(0.0)

    def test_partial_pass(self):
        v = IsolatedVerifier(pass_threshold=0.50)
        v.register_task(VerificationTask("t1", "desc", "ok", "web"))
        v.register_task(VerificationTask("t2", "desc", "nope", "web"))
        runner = _ContentRunner()
        report = v.verify("s", "ok", runner)
        assert report.tasks_run == 2
        assert report.tasks_passed == 1
        assert report.score == pytest.approx(0.5)

    def test_context_filter_applies(self):
        v = IsolatedVerifier(pass_threshold=0.5)
        v.register_task(_task("t1", ctx="web"))
        v.register_task(_task("t2", ctx="cli"))
        report = v.verify("s", "content", _AlwaysFail(), context_filter="web")
        assert report.tasks_run == 1

    def test_context_filter_empty_result_inconclusive(self):
        v = IsolatedVerifier()
        v.register_task(_task("t1", ctx="web"))
        report = v.verify("s", "content", _AlwaysPass(), context_filter="mobile")
        assert report.outcome == VerificationOutcome.INCONCLUSIVE

    def test_history_records_all_verifications(self):
        v = IsolatedVerifier()
        v.register_task(_task())
        v.verify("s1", "c1", _AlwaysPass())
        v.verify("s2", "c2", _AlwaysFail())
        assert len(v.history) == 2

    def test_pass_rate_calculation(self):
        v = IsolatedVerifier(pass_threshold=0.5)
        v.register_task(_task())
        v.verify("s1", "c", _AlwaysPass())
        v.verify("s2", "c", _AlwaysFail())
        assert v.pass_rate() == pytest.approx(0.5)

    def test_pass_rate_empty(self):
        v = IsolatedVerifier()
        assert v.pass_rate() == 0.0


class TestCoEvolutionGate:
    def setup_method(self):
        self.verifier = IsolatedVerifier(pass_threshold=0.70)
        self.verifier.register_task(_task("t1"))
        self.verifier.register_task(_task("t2"))

    def test_pass_skill_admitted(self):
        gate = CoEvolutionGate(self.verifier, _AlwaysPass())
        report = gate.evaluate("good-skill", "content")
        assert report.outcome == VerificationOutcome.PASS
        assert "good-skill" in gate.admitted_ids

    def test_fail_skill_rejected(self):
        gate = CoEvolutionGate(self.verifier, _AlwaysFail())
        report = gate.evaluate("bad-skill", "content")
        assert report.outcome == VerificationOutcome.FAIL
        assert "bad-skill" in gate.rejected_ids

    def test_admitted_not_in_rejected(self):
        gate = CoEvolutionGate(self.verifier, _AlwaysPass())
        gate.evaluate("skill-a", "content")
        assert "skill-a" not in gate.rejected_ids

    def test_admission_rate_all_pass(self):
        gate = CoEvolutionGate(self.verifier, _AlwaysPass())
        gate.evaluate("s1", "c")
        gate.evaluate("s2", "c")
        assert gate.admission_rate() == pytest.approx(1.0)

    def test_admission_rate_mixed(self):
        gate = CoEvolutionGate(self.verifier, _AlwaysPass())
        gate.evaluate("pass-skill", "c")
        fail_v = IsolatedVerifier(pass_threshold=0.70)
        fail_v.register_task(_task())
        fail_gate = CoEvolutionGate(fail_v, _AlwaysFail())
        fail_gate.evaluate("fail-skill", "c")
        assert gate.admission_rate() == pytest.approx(1.0)
        assert fail_gate.admission_rate() == pytest.approx(0.0)

    def test_admission_rate_empty(self):
        gate = CoEvolutionGate(self.verifier, _AlwaysPass())
        assert gate.admission_rate() == 0.0

    def test_context_filter_propagated(self):
        gate = CoEvolutionGate(self.verifier, _AlwaysPass())
        # Only one web task, so filter still works
        report = gate.evaluate("s", "c", context_filter="web")
        assert report.outcome in {VerificationOutcome.PASS, VerificationOutcome.FAIL}
