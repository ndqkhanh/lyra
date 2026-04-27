"""Red tests for the two-phase verifier.

Phase 1 (objective): deterministic checks on frozen inputs (tests pass,
acceptance list satisfied, expected files touched, forbidden files untouched).

Phase 2 (subjective): a different-family LLM scores the work against a
rubric and returns a PASS/FAIL/NEEDS_MORE verdict.
"""
from __future__ import annotations

from pathlib import Path

from lyra_core.verifier.evaluator_family import (
    EvaluatorFamily,
    detect_family,
    is_degraded_eval,
)
from lyra_core.verifier.objective import (
    ObjectiveEvidence,
    ObjectiveVerdict,
    verify_objective,
)
from lyra_core.verifier.subjective import (
    SubjectiveVerdict,
    verify_subjective,
)


def _evidence(**over) -> ObjectiveEvidence:
    base = dict(
        acceptance_tests_run=["tests/test_x.py::test_a"],
        acceptance_tests_passed=["tests/test_x.py::test_a"],
        expected_files_touched=["src/x.py"],
        forbidden_files_touched=[],
        coverage_before=80.0,
        coverage_after=82.0,
        coverage_tolerance_pct=1.0,
    )
    base.update(over)
    return ObjectiveEvidence(**base)


def test_objective_pass_when_all_acceptance_tests_green() -> None:
    v = verify_objective(_evidence())
    assert v.verdict is ObjectiveVerdict.PASS
    assert v.reason == "all acceptance tests green" or "green" in v.reason


def test_objective_fails_when_any_acceptance_test_not_green() -> None:
    v = verify_objective(
        _evidence(
            acceptance_tests_run=["tests/a::x", "tests/b::y"],
            acceptance_tests_passed=["tests/a::x"],
        )
    )
    assert v.verdict is ObjectiveVerdict.FAIL
    assert "y" in v.reason


def test_objective_fails_when_forbidden_file_touched() -> None:
    v = verify_objective(_evidence(forbidden_files_touched=["package.json"]))
    assert v.verdict is ObjectiveVerdict.FAIL
    assert "package.json" in v.reason


def test_objective_fails_on_coverage_regression() -> None:
    v = verify_objective(_evidence(coverage_before=90.0, coverage_after=70.0))
    assert v.verdict is ObjectiveVerdict.FAIL
    assert "coverage" in v.reason.lower()


def test_objective_needs_more_if_no_acceptance_tests_run() -> None:
    v = verify_objective(
        _evidence(acceptance_tests_run=[], acceptance_tests_passed=[])
    )
    assert v.verdict is ObjectiveVerdict.NEEDS_MORE


# ---------------------------------------------------------------------------
# Subjective (LLM judge) — we mock the LLM through the passed callable
# ---------------------------------------------------------------------------


def test_subjective_parses_pass() -> None:
    def judge(prompt: str) -> str:
        return '{"verdict": "PASS", "score": 0.9, "notes": "looks solid"}'

    v = verify_subjective(
        rubric="unit test quality + readability",
        evidence_summary="diff looks small, tests are clear",
        judge_llm=judge,
    )
    assert v.verdict is SubjectiveVerdict.PASS
    assert v.score == 0.9


def test_subjective_handles_fail() -> None:
    def judge(prompt: str) -> str:
        return '{"verdict":"FAIL","score":0.2,"notes":"test was disabled"}'

    v = verify_subjective(
        rubric="r", evidence_summary="e", judge_llm=judge
    )
    assert v.verdict is SubjectiveVerdict.FAIL


def test_subjective_needs_more_on_unparseable_output() -> None:
    def judge(prompt: str) -> str:
        return "hmm I don't know"

    v = verify_subjective(
        rubric="r", evidence_summary="e", judge_llm=judge
    )
    assert v.verdict is SubjectiveVerdict.NEEDS_MORE


# ---------------------------------------------------------------------------
# Cross-channel & evaluator family
# ---------------------------------------------------------------------------


def test_detect_family_anthropic() -> None:
    assert detect_family("anthropic/claude-3-5-sonnet") is EvaluatorFamily.ANTHROPIC
    assert detect_family("openai/gpt-4o") is EvaluatorFamily.OPENAI
    assert detect_family("google/gemini-1.5-pro") is EvaluatorFamily.GOOGLE
    assert detect_family("unknown/foo") is EvaluatorFamily.UNKNOWN


def test_same_family_flagged_as_degraded() -> None:
    flag = is_degraded_eval(
        agent_model="anthropic/claude-3-5-sonnet",
        judge_model="anthropic/claude-3-7-sonnet",
    )
    assert flag is True


def test_different_family_not_degraded() -> None:
    flag = is_degraded_eval(
        agent_model="anthropic/claude-3-5-sonnet",
        judge_model="openai/gpt-4o",
    )
    assert flag is False


# ---------------------------------------------------------------------------
# Evidence validator: hallucinated file:line rejected
# ---------------------------------------------------------------------------


def test_evidence_validator_rejects_hallucinated_line(tmp_path: Path) -> None:
    from lyra_core.verifier.evidence import EvidenceError, validate_file_line

    f = tmp_path / "src" / "x.py"
    f.parent.mkdir(parents=True)
    f.write_text("a = 1\nb = 2\nc = 3\n")
    # Valid
    validate_file_line(f, line=2, repo_root=tmp_path)
    # Out of range
    import pytest

    with pytest.raises(EvidenceError):
        validate_file_line(f, line=999, repo_root=tmp_path)


def test_evidence_validator_rejects_missing_file(tmp_path: Path) -> None:
    import pytest

    from lyra_core.verifier.evidence import EvidenceError, validate_file_line

    with pytest.raises(EvidenceError):
        validate_file_line(tmp_path / "nope.py", line=1, repo_root=tmp_path)


def test_cross_channel_catches_disabled_test(tmp_path: Path) -> None:
    """An acceptance test that 'passed' while its source was commented out
    must be flagged by cross-channel verification."""
    from lyra_core.verifier.cross_channel import cross_channel_check

    test_file = tmp_path / "tests" / "test_x.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        "def test_a():\n"
        "    # assert False  # deliberately commented-out assertion\n"
        "    pass\n"
    )
    findings = cross_channel_check(
        acceptance_tests_passed=[f"{test_file}::test_a"],
        repo_root=tmp_path,
    )
    assert findings, "must flag disabled/commented-out assertion"
    assert any("assertion" in f.reason.lower() or "comment" in f.reason.lower()
               for f in findings)
