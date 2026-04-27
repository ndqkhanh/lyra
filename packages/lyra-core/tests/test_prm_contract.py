"""Wave-F Task 4 — Rubric Process Reward Model contract."""
from __future__ import annotations

import pytest

from lyra_core.eval import (
    Rubric,
    RubricSet,
    RubricSetReport,
    prm_score,
)


# ---- validation ----------------------------------------------------


def test_rubric_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        Rubric(name="", description="…", weight=1.0)


def test_rubric_rejects_negative_weight() -> None:
    with pytest.raises(ValueError):
        Rubric(name="x", description="…", weight=-0.1)


def test_rubric_set_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError):
        RubricSet(
            (
                Rubric(name="clarity", description="a"),
                Rubric(name="clarity", description="b"),
            )
        )


# ---- scoring -------------------------------------------------------


def test_weighted_average_uses_weights() -> None:
    rubrics = [
        Rubric(name="clarity", description="clear prose", weight=3.0),
        Rubric(name="correctness", description="true claims", weight=1.0),
    ]
    canned = {"clarity": 1.0, "correctness": 0.0}

    def judge(*, rubric, output):
        return canned[rubric.name]

    report = prm_score(output="anything", rubrics=rubrics, judge=judge)
    # (1.0 * 3 + 0.0 * 1) / 4 = 0.75
    assert report.weighted_score == pytest.approx(0.75)


def test_all_zero_weights_degrades_to_zero() -> None:
    rubrics = [
        Rubric(name="a", description="…", weight=0.0),
        Rubric(name="b", description="…", weight=0.0),
    ]

    def judge(*, rubric, output):
        return 1.0

    report = prm_score(output="anything", rubrics=rubrics, judge=judge)
    assert report.weighted_score == 0.0


def test_scores_are_clamped_to_unit_interval() -> None:
    rubrics = [Rubric(name="r", description="…")]

    def judge(*, rubric, output):
        return 42.0  # wildly out of range

    report = prm_score(output="anything", rubrics=rubrics, judge=judge)
    assert report.scores[0].score == 1.0


def test_negative_score_is_clamped_to_zero() -> None:
    rubrics = [Rubric(name="r", description="…")]

    def judge(*, rubric, output):
        return -17.0

    report = prm_score(output="anything", rubrics=rubrics, judge=judge)
    assert report.scores[0].score == 0.0


def test_worst_returns_lowest_rubric() -> None:
    rubrics = [
        Rubric(name="a", description="…"),
        Rubric(name="b", description="…"),
        Rubric(name="c", description="…"),
    ]
    canned = {"a": 0.9, "b": 0.1, "c": 0.5}

    def judge(*, rubric, output):
        return canned[rubric.name]

    report = prm_score(output="anything", rubrics=rubrics, judge=judge)
    assert report.worst is not None
    assert report.worst.rubric.name == "b"


def test_non_numeric_judge_result_rejected() -> None:
    rubrics = [Rubric(name="r", description="…")]

    def bad_judge(*, rubric, output):
        return "very good"

    with pytest.raises(TypeError):
        prm_score(output="x", rubrics=rubrics, judge=bad_judge)  # type: ignore[arg-type]


def test_prm_score_accepts_rubricset_or_list() -> None:
    rubrics = [Rubric(name="only", description="…")]
    rs = RubricSet(tuple(rubrics))

    def judge(*, rubric, output):
        return 0.5

    r1 = prm_score(output="x", rubrics=rubrics, judge=judge)
    r2 = prm_score(output="x", rubrics=rs, judge=judge)
    assert isinstance(r1, RubricSetReport) and isinstance(r2, RubricSetReport)
    assert r1.weighted_score == r2.weighted_score == 0.5


def test_report_serialises() -> None:
    rubrics = [
        Rubric(name="a", description="…", weight=2.0),
        Rubric(name="b", description="…", weight=1.0),
    ]

    def judge(*, rubric, output):
        return {"a": 0.8, "b": 0.4}[rubric.name]

    rep = prm_score(output="x", rubrics=rubrics, judge=judge)
    data = rep.to_dict()
    assert data["weighted_score"] == rep.weighted_score
    assert {s["name"] for s in data["scores"]} == {"a", "b"}
    assert data["worst"]["name"] == "b"
