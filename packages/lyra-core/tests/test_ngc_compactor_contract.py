"""Wave-F Task 5 — NGC compactor contract."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.context import (
    NGCCompactor,
    NGCItem,
    NGCOutcomeLogger,
)


def _items(n: int, tokens: int = 10) -> list[NGCItem]:
    return [
        NGCItem(id=f"t{i}", tokens=tokens, usage_signal=float(i))
        for i in range(n)
    ]


# ---- plain eviction -----------------------------------------------


def test_under_budget_keeps_everything() -> None:
    items = _items(3, tokens=10)
    comp = NGCCompactor(token_budget=1000, keep_recent=2)
    result = comp.compact(items)
    assert [i.id for i in result.kept] == ["t0", "t1", "t2"]
    assert result.evicted == ()
    assert result.token_count_after == 30
    assert result.tokens_freed == 0


def test_evicts_lowest_score_first() -> None:
    items = [
        NGCItem(id=a, tokens=10, usage_signal=s)
        for a, s in [("a", 0.1), ("b", 0.9), ("c", 0.5)]
    ]
    comp = NGCCompactor(token_budget=20, keep_recent=0)
    result = comp.compact(items)
    kept_ids = {i.id for i in result.kept}
    assert kept_ids == {"b", "c"}
    assert [i.id for i in result.evicted] == ["a"]


def test_keep_recent_protects_tail() -> None:
    items = _items(5, tokens=10)
    # All usage_signals are 0..4, tail is t3,t4.
    comp = NGCCompactor(token_budget=20, keep_recent=2)
    result = comp.compact(items)
    # Budget for 2 items; tail (t3,t4) are anchored as recent.
    assert {i.id for i in result.kept} == {"t3", "t4"}


def test_must_keep_survives_even_low_score() -> None:
    items = [
        NGCItem(id="plan", tokens=10, must_keep=True, usage_signal=0.0),
        NGCItem(id="a", tokens=10, usage_signal=0.99),
        NGCItem(id="b", tokens=10, usage_signal=0.98),
    ]
    comp = NGCCompactor(token_budget=20, keep_recent=0)
    result = comp.compact(items)
    kept = {i.id for i in result.kept}
    assert "plan" in kept
    assert "a" in kept or "b" in kept


def test_anchors_over_budget_still_keep_anchors() -> None:
    items = [
        NGCItem(id="p1", tokens=100, must_keep=True),
        NGCItem(id="p2", tokens=100, must_keep=True),
        NGCItem(id="x", tokens=10, usage_signal=0.9),
    ]
    comp = NGCCompactor(token_budget=50, keep_recent=0)
    result = comp.compact(items)
    assert {i.id for i in result.kept} == {"p1", "p2"}
    assert result.token_count_after == 200  # reported even though > budget


def test_custom_scorer_is_used() -> None:
    items = [
        NGCItem(id="good", tokens=10, usage_signal=0.0, kind="plan"),
        NGCItem(id="bad", tokens=10, usage_signal=1.0, kind="noise"),
    ]

    def scorer(item: NGCItem) -> float:
        return 1.0 if item.kind == "plan" else 0.0

    comp = NGCCompactor(token_budget=10, keep_recent=0, scorer=scorer)
    result = comp.compact(items)
    assert [i.id for i in result.kept] == ["good"]


def test_negative_budget_rejected() -> None:
    with pytest.raises(ValueError):
        NGCCompactor(token_budget=-1)


def test_negative_keep_recent_rejected() -> None:
    with pytest.raises(ValueError):
        NGCCompactor(token_budget=100, keep_recent=-1)


# ---- outcome logging ----------------------------------------------


def test_outcome_logger_appends_jsonl(tmp_path: Path) -> None:
    items = _items(3, tokens=10)
    comp = NGCCompactor(token_budget=20, keep_recent=1)
    result = comp.compact(items)
    logger = NGCOutcomeLogger(path=tmp_path / "log.jsonl")
    logger.log(turn=1, result=result, outcome="pass")
    logger.log(turn=2, result=result, outcome="fail")
    lines = (tmp_path / "log.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["turn"] == 1 and parsed[0]["outcome"] == "pass"
    assert parsed[1]["turn"] == 2 and parsed[1]["outcome"] == "fail"
    assert "tokens_freed" in parsed[0]


def test_outcome_logger_swallows_os_errors(tmp_path: Path) -> None:
    # Point at an illegal path (a file where a directory is expected) to
    # force OSError. The logger must silently no-op rather than raise.
    real_file = tmp_path / "not_a_dir"
    real_file.write_text("x")
    logger = NGCOutcomeLogger(path=real_file / "log.jsonl")
    items = _items(1)
    comp = NGCCompactor(token_budget=100)
    logger.log(turn=1, result=comp.compact(items), outcome="pass")
    # no assertion needed — success == no exception


def test_result_serialises() -> None:
    items = _items(3, tokens=10)
    comp = NGCCompactor(token_budget=15, keep_recent=0)
    result = comp.compact(items)
    data = result.to_dict()
    assert "kept" in data and "evicted" in data
    assert data["token_count_before"] == 30
    assert data["tokens_freed"] == data["token_count_before"] - data["token_count_after"]
