"""L38-4 — Letta-style memory tool surface tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.hir.events import RingBuffer, clear_subscribers, subscribe
from lyra_core.memory import (
    AutoMemory,
    HeuristicDistiller,
    Lesson,
    MemoryToolset,
    ProceduralMemory,
    RecallResult,
    SkillRecord,
    SqliteReasoningBank,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
)
from lyra_core.memory.auto_memory import MemoryKind


@pytest.fixture
def hir_capture():
    """Captures every HIR emit during the test."""
    buf = RingBuffer(cap=256)
    yield buf
    buf.detach()


@pytest.fixture
def auto_memory(tmp_path: Path) -> AutoMemory:
    return AutoMemory(root=tmp_path / "auto", project="test-project")


@pytest.fixture
def procedural(tmp_path: Path) -> ProceduralMemory:
    return ProceduralMemory(db_path=tmp_path / "skills.db")


@pytest.fixture
def reasoning_bank(tmp_path: Path) -> SqliteReasoningBank:
    bank = SqliteReasoningBank(
        distiller=HeuristicDistiller(),
        db_path=tmp_path / "lessons.db",
    )
    yield bank
    bank.close()


@pytest.fixture
def toolset(auto_memory, procedural, reasoning_bank) -> MemoryToolset:
    return MemoryToolset(
        auto_memory=auto_memory,
        procedural=procedural,
        reasoning_bank=reasoning_bank,
    )


def _kinds(buf: RingBuffer) -> list[str]:
    return [evt["name"] for evt in buf.snapshot()]


# --- recall: per-scope ----------------------------------------------


def test_recall_auto_scope(toolset, auto_memory) -> None:
    auto_memory.save(
        kind=MemoryKind.PROJECT,
        title="Polaris v2.5", body="memory tier P42-P44 landing",
    )
    results = toolset.recall("memory tier", scope="auto", top_k=3)
    assert any(r.scope == "auto" and "Polaris" in r.title for r in results)


def test_recall_skill_scope(toolset, procedural) -> None:
    procedural.put(SkillRecord(
        id="csv-chart", name="Chart from CSV",
        description="generate a chart from a CSV file",
        body="pandas + matplotlib...",
    ))
    results = toolset.recall("chart csv", scope="skill", top_k=3)
    assert any(r.scope == "skill" and r.record_id == "csv-chart" for r in results)


def test_recall_lesson_scope(toolset, reasoning_bank) -> None:
    traj = Trajectory(
        id="t1",
        task_signature="fix off-by-one bug in pagination",
        outcome=TrajectoryOutcome.SUCCESS,
        steps=(TrajectoryStep(index=0, kind="message", payload="off-by-one fixed"),),
        final_artefact="patch applied",
    )
    reasoning_bank.record(traj)
    results = toolset.recall(
        "fix off-by-one bug in pagination", scope="lesson", top_k=3,
    )
    assert any(r.scope == "lesson" for r in results)


def test_recall_any_scope_unions(toolset, auto_memory, procedural) -> None:
    auto_memory.save(kind=MemoryKind.PROJECT, title="proj entry",
                     body="some project notes about chart")
    procedural.put(SkillRecord(
        id="sk1", name="Chart skill", description="make a chart", body="...",
    ))
    results = toolset.recall("chart", scope="any", top_k=10)
    scopes = {r.scope for r in results}
    assert "auto" in scopes
    assert "skill" in scopes


def test_recall_any_truncates_to_top_k(toolset, auto_memory, procedural) -> None:
    for i in range(5):
        auto_memory.save(kind=MemoryKind.PROJECT, title=f"e{i}", body="alpha")
    for i in range(5):
        procedural.put(SkillRecord(
            id=f"sk{i}", name=f"alpha skill {i}",
            description="alpha", body="alpha",
        ))
    results = toolset.recall("alpha", scope="any", top_k=3)
    assert len(results) == 3


def test_recall_emits_start_end(toolset, auto_memory, hir_capture) -> None:
    auto_memory.save(kind=MemoryKind.PROJECT, title="x", body="alpha")
    toolset.recall("alpha", scope="auto", top_k=1)
    kinds = _kinds(hir_capture)
    assert "memory.recall.start" in kinds
    assert "memory.recall.end" in kinds


# --- remember --------------------------------------------------------


def test_remember_auto_appends_entry(toolset, auto_memory) -> None:
    result = toolset.remember(
        "this is a project decision",
        scope="auto", title="decision-1",
        kind=MemoryKind.PROJECT,
    )
    assert result.scope == "auto"
    assert result.title == "decision-1"
    assert any(e.title == "decision-1" for e in auto_memory.all())


def test_remember_auto_default_kind_is_project(toolset, auto_memory) -> None:
    toolset.remember("default kind", scope="auto", title="t1")
    entry = next(e for e in auto_memory.all() if e.title == "t1")
    assert entry.kind == MemoryKind.PROJECT


def test_remember_skill_writes_record(toolset, procedural) -> None:
    result = toolset.remember(
        "import pandas; df = pd.read_csv(path)",
        scope="skill",
        skill_id="csv-load", skill_name="Load CSV",
        skill_description="load a csv into a dataframe",
    )
    assert result.scope == "skill"
    assert procedural.get("csv-load") is not None


def test_remember_skill_requires_full_metadata(toolset) -> None:
    with pytest.raises(ValueError, match="skill_id"):
        toolset.remember("body", scope="skill", skill_id="x")


def test_remember_lesson_rejected(toolset) -> None:
    with pytest.raises(ValueError, match="lesson"):
        toolset.remember("x", scope="lesson")


def test_remember_any_scope_rejected(toolset) -> None:
    with pytest.raises(ValueError, match="explicit scope"):
        toolset.remember("x", scope="any")


def test_remember_emits_start_end(toolset, hir_capture) -> None:
    toolset.remember("x", scope="auto", title="t", kind=MemoryKind.FEEDBACK)
    kinds = _kinds(hir_capture)
    assert "memory.remember.start" in kinds
    assert "memory.remember.end" in kinds


# --- forget ----------------------------------------------------------


def test_forget_auto_tombstones(toolset, auto_memory) -> None:
    written = toolset.remember("x", scope="auto", title="t", kind=MemoryKind.PROJECT)
    ok = toolset.forget(written.record_id, scope="auto")
    assert ok is True
    # AutoMemory.forget tombstones; all() with default skips deleted.
    assert not any(e.entry_id == written.record_id for e in auto_memory.all())


def test_forget_unknown_id_returns_false(toolset) -> None:
    ok = toolset.forget("does-not-exist", scope="auto")
    assert ok is False


def test_forget_skill_rejected(toolset) -> None:
    with pytest.raises(ValueError, match="ProceduralMemory"):
        toolset.forget("any", scope="skill")


def test_forget_lesson_rejected(toolset) -> None:
    with pytest.raises(ValueError, match="lesson"):
        toolset.forget("any", scope="lesson")


def test_forget_emits_start_end(toolset, auto_memory, hir_capture) -> None:
    written = toolset.remember("x", scope="auto", title="t", kind=MemoryKind.PROJECT)
    toolset.forget(written.record_id, scope="auto")
    kinds = _kinds(hir_capture)
    assert "memory.forget.start" in kinds
    assert "memory.forget.end" in kinds


# --- improve ---------------------------------------------------------


def test_improve_reports_cardinalities(toolset, auto_memory, procedural) -> None:
    auto_memory.save(kind=MemoryKind.PROJECT, title="x", body="y")
    procedural.put(SkillRecord(id="s1", name="n", description="d", body="b"))
    result = toolset.improve()
    assert result.auto_entries_active >= 1
    assert result.skill_count >= 1
    assert result.duration_s >= 0


def test_improve_emits_start_end(toolset, hir_capture) -> None:
    toolset.improve()
    kinds = _kinds(hir_capture)
    assert "memory.improve.start" in kinds
    assert "memory.improve.end" in kinds


# --- partial wiring -------------------------------------------------


def test_toolset_works_without_lesson_bank(tmp_path: Path) -> None:
    """Substrates are independently optional."""
    auto = AutoMemory(root=tmp_path / "auto", project="p")
    ts = MemoryToolset(auto_memory=auto, procedural=None, reasoning_bank=None)
    auto.save(kind=MemoryKind.PROJECT, title="x", body="alpha")
    results = ts.recall("alpha", scope="any", top_k=5)
    assert len(results) == 1
    assert results[0].scope == "auto"


def test_recall_unwired_scope_returns_empty(tmp_path: Path) -> None:
    ts = MemoryToolset()
    assert ts.recall("anything", scope="any", top_k=5) == ()
    assert ts.recall("anything", scope="auto", top_k=5) == ()
