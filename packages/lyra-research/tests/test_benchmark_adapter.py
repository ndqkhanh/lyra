"""Tests for the ResearcherBench BenchmarkAdapter."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest

from lyra_research.benchmark_adapter import BenchmarkAdapter


@dataclass
class _FakeReport:
    citation_fidelity: float
    coverage_score: float
    quality_score: float


@dataclass
class _FakeProgress:
    papers_analyzed: int = 12
    repos_analyzed: int = 4
    report: object = None


def _progress(citation_fidelity: float, coverage: float, quality: float) -> Any:
    return cast(
        Any,
        _FakeProgress(
            report=_FakeReport(
                citation_fidelity=citation_fidelity,
                coverage_score=coverage,
                quality_score=quality,
            )
        ),
    )


def test_default_question_set_has_65() -> None:
    a = BenchmarkAdapter()
    assert len(a.questions) == 65


def test_question_lookup_by_id() -> None:
    a = BenchmarkAdapter()
    q = a.get("Q01")
    assert q is not None
    assert q.domain == "agents"


def test_domain_filter() -> None:
    a = BenchmarkAdapter()
    ml_questions = a.by_domain("ml")
    assert all(q.domain == "ml" for q in ml_questions)
    assert len(ml_questions) >= 10


def test_difficulty_filter() -> None:
    a = BenchmarkAdapter()
    hard = a.by_difficulty("hard")
    assert all(q.difficulty == "hard" for q in hard)
    assert len(hard) > 0


def test_score_passing_session() -> None:
    a = BenchmarkAdapter()
    q = a.questions[0]
    result = a.score(q, _progress(1.0, 0.85, 0.88), verified_citations=18, total_claims=20)
    assert result.passed is True
    assert result.faithfulness == 1.0
    assert result.groundedness == 0.9


def test_score_failing_on_hallucination() -> None:
    a = BenchmarkAdapter()
    q = a.questions[0]
    result = a.score(q, _progress(0.85, 0.85, 0.80), verified_citations=18, total_claims=20)
    assert result.passed is False
    assert result.faithfulness == 0.85


def test_score_failing_on_low_groundedness() -> None:
    a = BenchmarkAdapter()
    q = a.questions[0]
    result = a.score(q, _progress(1.0, 0.85, 0.85), verified_citations=10, total_claims=20)
    assert result.passed is False  # groundedness 0.5 < 0.8


def test_persistence_roundtrip(tmp_path: Path) -> None:
    a = BenchmarkAdapter(results_path=tmp_path / "rb.jsonl")
    q = a.questions[0]
    result = a.score(q, _progress(1.0, 0.85, 0.88), verified_citations=18, total_claims=20)
    a.save(result)
    a.save(result)
    loaded = a.load_all()
    assert len(loaded) == 2
    assert loaded[0].question_id == q.id


def test_summary_no_data(tmp_path: Path) -> None:
    a = BenchmarkAdapter(results_path=tmp_path / "rb.jsonl")
    s = a.summary()
    assert s["answered"] == 0
    assert s["total_questions"] == 65
    assert s["pass_rate"] == 0.0


def test_summary_aggregates_by_domain(tmp_path: Path) -> None:
    a = BenchmarkAdapter(results_path=tmp_path / "rb.jsonl")
    pass_prog = _progress(1.0, 0.9, 0.9)
    fail_prog = _progress(0.7, 0.6, 0.6)
    for q in a.by_domain("agents")[:3]:
        a.save(a.score(q, pass_prog, verified_citations=20, total_claims=20))
    for q in a.by_domain("ml")[:2]:
        a.save(a.score(q, fail_prog, verified_citations=10, total_claims=20))

    s = a.summary()
    assert s["answered"] == 5
    assert s["by_domain"]["agents"]["passed"] == 3
    assert s["by_domain"]["ml"]["passed"] == 0
    assert s["mean_faithfulness"] == pytest.approx((1.0 * 3 + 0.7 * 2) / 5)
