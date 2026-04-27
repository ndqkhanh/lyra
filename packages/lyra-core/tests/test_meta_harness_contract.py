"""Wave-F Task 11 — meta-harness outer loop + parity corpus contract."""
from __future__ import annotations

import pytest

from lyra_core.meta import (
    CandidateConfig,
    HarnessTask,
    MetaHarness,
    ParityCorpus,
    default_parity_corpus,
)
from lyra_core.meta.outer_loop import StaticProposer


# ---- corpus --------------------------------------------------------


def test_default_parity_corpus_is_non_empty() -> None:
    corpus = default_parity_corpus()
    assert len(corpus) >= 10
    categories = {t.category for t in corpus.tasks}
    assert {"planning", "tdd", "bugfix", "refactor", "safety"}.issubset(categories)


def test_corpus_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError):
        ParityCorpus(
            tasks=(
                HarnessTask(id="a", category="x", prompt="p"),
                HarnessTask(id="a", category="y", prompt="q"),
            )
        )


def test_corpus_extend_preserves_originals() -> None:
    c = default_parity_corpus()
    extra = HarnessTask(id="extra-1", category="planning", prompt="…")
    bigger = c.extend((extra,))
    assert len(bigger) == len(c) + 1
    assert any(t.id == "extra-1" for t in bigger.tasks)


def test_corpus_by_category_filters() -> None:
    c = default_parity_corpus()
    safety = c.by_category("safety")
    assert all(t.category == "safety" for t in safety)
    assert len(safety) >= 2


def test_task_validate_substring() -> None:
    task = HarnessTask(
        id="x",
        category="plan",
        prompt="…",
        expected_substrings=("plan", "step"),
    )
    assert task.validate("here is a plan with a step")
    assert not task.validate("unrelated answer")


def test_task_validate_refusal() -> None:
    task = HarnessTask(id="x", category="safety", prompt="…", must_refuse=True)
    assert task.validate("I refuse to do that.")
    assert not task.validate("Here is the content you asked for.")


# ---- outer loop ---------------------------------------------------


def _always_passes(*, config, task):
    if task.must_refuse:
        return "I refuse."
    if task.expected_substrings:
        return " ".join(task.expected_substrings)
    return "an answer"


def _always_fails(*, config, task):
    return ""


def test_meta_harness_picks_winner() -> None:
    corpus = ParityCorpus(
        tasks=(
            HarnessTask(id="t1", category="x", prompt="p", expected_substrings=("ok",)),
            HarnessTask(id="t2", category="x", prompt="p", expected_substrings=("yes",)),
        )
    )
    c1 = CandidateConfig(name="bad")
    c2 = CandidateConfig(name="good")
    proposer = StaticProposer(candidates=[c1, c2])

    def evaluator(*, config, task):
        if config.name == "good":
            return " ".join(task.expected_substrings)
        return ""

    mh = MetaHarness(corpus=corpus, evaluator=evaluator, proposer=proposer)
    report = mh.run()
    assert report.winner is not None
    assert report.winner.config.name == "good"
    assert report.winner.pass_rate == 1.0


def test_meta_harness_respects_max_candidates() -> None:
    corpus = default_parity_corpus()
    configs = [CandidateConfig(name=f"c{i}") for i in range(5)]
    mh = MetaHarness(
        corpus=corpus,
        evaluator=_always_passes,
        proposer=StaticProposer(candidates=configs),
        max_candidates=2,
    )
    report = mh.run()
    assert len(report.reports) == 2


def test_meta_harness_stops_when_proposer_dries_up() -> None:
    corpus = ParityCorpus(
        tasks=(HarnessTask(id="only", category="x", prompt="p", expected_substrings=("ok",)),)
    )
    mh = MetaHarness(
        corpus=corpus,
        evaluator=_always_passes,
        proposer=StaticProposer(candidates=[CandidateConfig(name="solo")]),
        max_candidates=20,
    )
    report = mh.run()
    assert len(report.reports) == 1


def test_category_rates_surface_per_category_breakdown() -> None:
    corpus = ParityCorpus(
        tasks=(
            HarnessTask(id="p1", category="planning", prompt="p", expected_substrings=("ok",)),
            HarnessTask(id="s1", category="safety", prompt="p", must_refuse=True),
        )
    )

    def evaluator(*, config, task):
        if task.category == "planning":
            return "ok"
        return "sure, running it now"  # fails the safety refusal

    mh = MetaHarness(
        corpus=corpus,
        evaluator=evaluator,
        proposer=StaticProposer(candidates=[CandidateConfig(name="half")]),
    )
    report = mh.run()
    cat_rates = report.reports[0].category_rates(corpus)
    assert cat_rates["planning"] == 1.0
    assert cat_rates["safety"] == 0.0


def test_report_serialises() -> None:
    corpus = ParityCorpus(
        tasks=(HarnessTask(id="t1", category="x", prompt="p", expected_substrings=("ok",)),)
    )
    mh = MetaHarness(
        corpus=corpus,
        evaluator=_always_passes,
        proposer=StaticProposer(candidates=[CandidateConfig(name="c")]),
    )
    report = mh.run()
    data = report.to_dict()
    assert data["winner"] == "c"
    assert data["corpus_size"] == 1
    assert data["reports"][0]["pass_rate"] == 1.0


def test_max_candidates_rejected_if_lt_1() -> None:
    with pytest.raises(ValueError):
        MetaHarness(
            corpus=default_parity_corpus(),
            evaluator=_always_passes,
            proposer=StaticProposer(candidates=[]),
            max_candidates=0,
        )
