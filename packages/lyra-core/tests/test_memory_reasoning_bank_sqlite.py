"""Tests for the SQLite-backed ReasoningBank persistence layer (v1.8 §3.2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory import (
    HeuristicDistiller,
    Lesson,
    SqliteReasoningBank,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
    default_db_path,
    open_default_bank,
)
from lyra_core.memory.reasoning_bank import ReasoningBank


def _trajectory(
    *,
    outcome: TrajectoryOutcome,
    sig: str = "parse-json",
    payload: str = "ok",
) -> Trajectory:
    return Trajectory(
        id=f"t-{outcome.value}-{sig}-{payload[:8]}",
        task_signature=sig,
        outcome=outcome,
        steps=(
            TrajectoryStep(index=0, kind="tool_call", payload=payload),
            TrajectoryStep(index=1, kind="message", payload=payload),
        ),
    )


@pytest.fixture
def bank(tmp_path: Path) -> SqliteReasoningBank:
    db_path = tmp_path / "rb.sqlite"
    return SqliteReasoningBank(distiller=HeuristicDistiller(), db_path=db_path)


# ---------------------------------------------------------------------------
# Persistence basics
# ---------------------------------------------------------------------------


def test_record_persists_lesson(bank: SqliteReasoningBank, tmp_path: Path) -> None:
    bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="parse-json"))
    bank.close()

    reopened = SqliteReasoningBank(
        distiller=HeuristicDistiller(), db_path=tmp_path / "rb.sqlite"
    )
    found = reopened.recall("parse-json", k=5)
    assert len(found) == 1
    assert found[0].polarity is TrajectoryOutcome.SUCCESS
    assert "parse-json" in found[0].task_signatures


def test_record_failure_persists_anti_skill(bank: SqliteReasoningBank) -> None:
    bank.record(
        _trajectory(
            outcome=TrajectoryOutcome.FAILURE,
            sig="parse-json",
            payload="error: bad syntax",
        )
    )
    found = bank.recall("parse-json", polarity=TrajectoryOutcome.FAILURE, k=5)
    assert len(found) >= 1
    assert all(lesson.polarity is TrajectoryOutcome.FAILURE for lesson in found)


def test_recall_returns_empty_when_bank_is_empty(bank: SqliteReasoningBank) -> None:
    assert bank.recall("parse-json", k=5) == ()


def test_recall_filters_by_polarity(bank: SqliteReasoningBank) -> None:
    bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="parse-json"))
    bank.record(
        _trajectory(
            outcome=TrajectoryOutcome.FAILURE,
            sig="parse-json",
            payload="error: bad syntax",
        )
    )
    only_failures = bank.recall(
        "parse-json", polarity=TrajectoryOutcome.FAILURE, k=5
    )
    assert all(lesson.polarity is TrajectoryOutcome.FAILURE for lesson in only_failures)


def test_recall_respects_k(bank: SqliteReasoningBank) -> None:
    for i in range(8):
        bank.record(
            _trajectory(
                outcome=TrajectoryOutcome.SUCCESS, sig="parse-json", payload=f"step-{i}"
            )
        )
    out = bank.recall("parse-json", k=3)
    assert len(out) <= 3


def test_recall_substring_via_fts_or_like(bank: SqliteReasoningBank) -> None:
    bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="json-parser-fix"))
    out = bank.recall("parser", k=5)
    assert len(out) >= 1


# ---------------------------------------------------------------------------
# MaTTS contract (the bank's prefix behaviour survives persistence)
# ---------------------------------------------------------------------------


def test_matts_prefix_diversifies_across_attempts(bank: SqliteReasoningBank) -> None:
    for i in range(5):
        bank.record(
            _trajectory(
                outcome=TrajectoryOutcome.SUCCESS, sig="parse-json", payload=f"step-{i}"
            )
        )
    p0 = bank.matts_prefix("parse-json", attempt_index=0)
    p1 = bank.matts_prefix("parse-json", attempt_index=1)
    p2 = bank.matts_prefix("parse-json", attempt_index=2)
    assert len({p0, p1, p2}) >= 2


def test_matts_prefix_no_lessons_returns_marker(bank: SqliteReasoningBank) -> None:
    out = bank.matts_prefix("never-recorded", attempt_index=0)
    assert "no lessons" in out


# ---------------------------------------------------------------------------
# Stats / wipe / introspection
# ---------------------------------------------------------------------------


def test_stats_counts_polarities(bank: SqliteReasoningBank) -> None:
    bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="a"))
    bank.record(
        _trajectory(outcome=TrajectoryOutcome.FAILURE, sig="b", payload="error")
    )
    stats = bank.stats()
    assert stats["lessons_total"] >= 2
    assert stats["lessons_success"] >= 1
    assert stats["lessons_failure"] >= 1
    assert stats["task_signatures"] >= 2


def test_wipe_clears_everything(bank: SqliteReasoningBank) -> None:
    bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="parse-json"))
    deleted = bank.wipe()
    assert deleted >= 1
    assert bank.stats()["lessons_total"] == 0
    assert bank.recall("parse-json", k=5) == ()


def test_all_lessons_filters(bank: SqliteReasoningBank) -> None:
    bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="a"))
    bank.record(
        _trajectory(outcome=TrajectoryOutcome.FAILURE, sig="b", payload="error")
    )
    successes = bank.all_lessons(polarity=TrajectoryOutcome.SUCCESS)
    failures = bank.all_lessons(polarity=TrajectoryOutcome.FAILURE)
    assert all(lesson.polarity is TrajectoryOutcome.SUCCESS for lesson in successes)
    assert all(lesson.polarity is TrajectoryOutcome.FAILURE for lesson in failures)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def test_default_db_path_under_repo(tmp_path: Path) -> None:
    p = default_db_path(tmp_path)
    assert p.parent.name == "memory"
    assert p.parent.parent.name == ".lyra"
    assert p.name.endswith(".sqlite")


def test_open_default_bank_in_memory_when_no_path() -> None:
    obj = open_default_bank(distiller=HeuristicDistiller(), db_path=None)
    assert isinstance(obj, ReasoningBank)


def test_open_default_bank_sqlite_when_path_given(tmp_path: Path) -> None:
    obj = open_default_bank(
        distiller=HeuristicDistiller(), db_path=tmp_path / "rb.sqlite"
    )
    assert isinstance(obj, SqliteReasoningBank)


# ---------------------------------------------------------------------------
# Integration with the heuristic distiller
# ---------------------------------------------------------------------------


def test_lesson_carries_back_pointer(bank: SqliteReasoningBank) -> None:
    """Audit-trail contract preserved across the SQLite hop."""
    t = _trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="parse-json")
    bank.record(t)
    lessons = bank.recall("parse-json", k=5)
    assert lessons
    assert any(t.id in lesson.source_trajectory_ids for lesson in lessons)


def test_record_replays_idempotently(bank: SqliteReasoningBank) -> None:
    """Re-recording the same trajectory must not duplicate lessons."""
    t = _trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="parse-json")
    bank.record(t)
    n1 = bank.stats()["lessons_total"]
    bank.record(t)
    n2 = bank.stats()["lessons_total"]
    assert n1 == n2
    # And lessons remain readable after replay.
    found: tuple[Lesson, ...] = bank.recall("parse-json", k=5)
    assert found
