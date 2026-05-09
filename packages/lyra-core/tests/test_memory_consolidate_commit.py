"""Tests for the consolidation-commit path: episodic → semantic lesson."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory.auto_memory import AutoMemory, MemoryKind
from lyra_core.memory.consolidator import (
    ConsolidationProposal,
    MemoryConsolidator,
)
from lyra_core.memory.memory_tools import MemoryToolset
from lyra_core.memory.reasoning_bank import (
    Distiller,
    Lesson,
    Trajectory,
    TrajectoryOutcome,
)
from lyra_core.memory.reasoning_bank_store import SqliteReasoningBank


class _NoopDistiller(Distiller):
    """No-op distiller; the commit path doesn't go through it."""

    def distill(self, trajectory: Trajectory):
        return ()


def _toolset(tmp_path: Path) -> MemoryToolset:
    am = AutoMemory(root=tmp_path / "auto", project="demo")
    bank = SqliteReasoningBank(
        db_path=tmp_path / "bank.db", distiller=_NoopDistiller(),
    )
    return MemoryToolset(
        auto_memory=am,
        reasoning_bank=bank,
        consolidator=MemoryConsolidator(),
    )


def test_commit_consolidation_writes_lesson(tmp_path: Path) -> None:
    ts = _toolset(tmp_path)
    for i in range(4):
        ts.remember(
            f"generate chart from csv pandas variant {i}",
            scope="auto", kind=MemoryKind.PROJECT, title="csv chart",
        )
    result = ts.improve()
    assert result.consolidations
    proposal = result.consolidations[0]
    lesson = ts.commit_consolidation(proposal)
    assert isinstance(lesson, Lesson)
    assert lesson.title == proposal.proposed_title
    assert lesson.source_trajectory_ids == proposal.member_entry_ids
    # Bank now retrievable via task_signature.
    found = ts.reasoning_bank.recall(task_signature="csv", k=5)
    assert any(l.id == lesson.id for l in found)


def test_commit_consolidation_idempotent(tmp_path: Path) -> None:
    """Committing the same proposal twice doesn't create two lessons."""
    ts = _toolset(tmp_path)
    for i in range(3):
        ts.remember(
            f"generate chart from csv pandas variant {i}",
            scope="auto", kind=MemoryKind.PROJECT, title="csv chart",
        )
    result = ts.improve()
    proposal = result.consolidations[0]
    l1 = ts.commit_consolidation(proposal)
    l2 = ts.commit_consolidation(proposal)
    assert l1.id == l2.id
    # Only one row by that id in the bank.
    stats = ts.reasoning_bank.stats()
    assert stats.get("lessons_total", 0) == 1


def test_commit_consolidation_polarity_failure(tmp_path: Path) -> None:
    """A FAILURE-polarity commit becomes an anti-skill."""
    ts = _toolset(tmp_path)
    for i in range(3):
        ts.remember(
            f"flaky build error variant {i} retry timeout",
            scope="auto", kind=MemoryKind.PROJECT, title="flaky build error",
        )
    result = ts.improve()
    if not result.consolidations:
        pytest.skip("clustering didn't fire on this fixture")
    proposal = result.consolidations[0]
    lesson = ts.commit_consolidation(
        proposal, polarity=TrajectoryOutcome.FAILURE,
    )
    assert lesson.polarity is TrajectoryOutcome.FAILURE


def test_commit_consolidation_requires_bank(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    ts = MemoryToolset(auto_memory=am)  # no bank wired
    proposal = ConsolidationProposal(
        cluster_kind=MemoryKind.PROJECT,
        member_entry_ids=("a", "b", "c"),
        shared_tokens=("csv", "chart"),
        proposed_title="csv chart",
        proposed_body="x",
        cohesion=1.0,
    )
    with pytest.raises(ValueError, match="reasoning_bank"):
        ts.commit_consolidation(proposal)


def test_commit_consolidation_rejects_empty_members(tmp_path: Path) -> None:
    ts = _toolset(tmp_path)
    proposal = ConsolidationProposal(
        cluster_kind=MemoryKind.PROJECT,
        member_entry_ids=(),
        shared_tokens=("x",),
        proposed_title="x",
        proposed_body="x",
        cohesion=1.0,
    )
    with pytest.raises(ValueError, match="no members"):
        ts.commit_consolidation(proposal)


def test_commit_consolidation_signatures_drive_recall(tmp_path: Path) -> None:
    """Lesson is retrievable by any of the proposal's shared tokens."""
    ts = _toolset(tmp_path)
    for i in range(3):
        ts.remember(
            f"generate chart from csv pandas variant {i}",
            scope="auto", kind=MemoryKind.PROJECT, title="csv chart",
        )
    proposal = ts.improve().consolidations[0]
    ts.commit_consolidation(proposal)
    # Recall via "pandas" should find the lesson if pandas is in shared tokens.
    if "pandas" in proposal.shared_tokens:
        results = ts.reasoning_bank.recall(task_signature="pandas", k=5)
        assert results
