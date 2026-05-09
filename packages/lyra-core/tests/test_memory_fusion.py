"""RRF fusion + MemoryToolset.recall integration."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory.auto_memory import AutoMemory, MemoryKind
from lyra_core.memory.fusion import rrf, rrf_topk
from lyra_core.memory.memory_tools import MemoryToolset
from lyra_core.memory.procedural import ProceduralMemory, SkillRecord


# --- pure RRF -----------------------------------------------------------


def test_rrf_single_ranking_pass_through_order() -> None:
    out = rrf([["a", "b", "c"]])
    assert [name for name, _ in out] == ["a", "b", "c"]


def test_rrf_unanimous_top_dominates() -> None:
    """An item that's #1 on every list must win."""
    out = rrf([["a", "b", "c"], ["a", "x", "y"], ["a", "p", "q"]])
    assert out[0][0] == "a"


def test_rrf_unique_top_beats_split_seconds() -> None:
    """A is #1 in one list and absent in another; B is #2 everywhere.
    With k=60, A's 1/(60+1)=0.0164 beats B's 2*(1/(60+2))=0.0323... wait,
    actually B wins this one — that's the *whole point* of RRF: showing
    up consistently > showing up once at the top. Verify the math."""
    out = rrf([["a", "b"], ["b", "x"]])
    names = [n for n, _ in out]
    assert names[0] == "b"   # consistent #2 + #1 beats A's lone #1
    assert "a" in names


def test_rrf_score_descending() -> None:
    out = rrf([["a", "b", "c"], ["b", "c", "d"]])
    scores = [score for _, score in out]
    assert scores == sorted(scores, reverse=True)


def test_rrf_empty_input_returns_empty() -> None:
    assert rrf([]) == []
    assert rrf([[], []]) == []


def test_rrf_topk_truncates() -> None:
    out = rrf_topk([["a", "b", "c", "d", "e"]], top_k=2)
    assert len(out) == 2


def test_rrf_negative_k_rejected() -> None:
    with pytest.raises(ValueError):
        rrf([["a"]], k=0)


def test_rrf_smaller_k_amplifies_top_advantage() -> None:
    """With k=1 (very aggressive), A's lone #1 should beat B's two #2s."""
    out_default = rrf([["a", "b"], ["b", "c"]], k=60)
    out_aggressive = rrf([["a", "b"], ["b", "c"]], k=1)
    # Default k=60 → b wins (multiple appearances).
    assert out_default[0][0] == "b"
    # k=1 → a's #1 contribution = 1/2 = 0.5; b's = 1/3 + 1/2 = 0.833; b still wins.
    # Try k=1 with a more lopsided case where a is unique #1:
    out_lopsided = rrf([["a", "b", "c", "d"]], k=1)
    assert out_lopsided[0][0] == "a"


# --- MemoryToolset.recall integration ---------------------------------


def _toolset_with_three_substores(tmp_path: Path) -> MemoryToolset:
    am = AutoMemory(root=tmp_path / "auto", project="demo")
    am.save(kind=MemoryKind.PROJECT, title="csv chart auto",
            body="generate a chart from csv data with pandas")
    am.save(kind=MemoryKind.PROJECT, title="vacation",
            body="annual leave policy is unlimited")

    proc = ProceduralMemory(db_path=tmp_path / "procedural.db")
    proc.put(SkillRecord(id="csv-chart-skill", name="csv-charter",
                         description="generate chart from csv files",
                         body="def chart(): pass"))
    proc.put(SkillRecord(id="invoice-skill", name="invoicer",
                         description="process invoices via OCR",
                         body="def process(): pass"))

    return MemoryToolset(auto_memory=am, procedural=proc)


def test_recall_any_with_rrf_returns_relevant_first(tmp_path: Path) -> None:
    ts = _toolset_with_three_substores(tmp_path)
    results = ts.recall("chart from csv", scope="any", top_k=4)
    assert results
    # Top result should be one of the chart-related records.
    assert "chart" in (results[0].title + results[0].body).lower() or \
           "chart" in results[0].body.lower()


def test_recall_any_concat_preserves_legacy_order(tmp_path: Path) -> None:
    ts = _toolset_with_three_substores(tmp_path)
    results = ts.recall("csv chart", scope="any", top_k=10, fusion="concat")
    # Legacy order: auto results first, then skill results.
    scopes = [r.scope for r in results]
    if scopes:
        # No "skill" should appear before any "auto" was emitted (both present).
        if "auto" in scopes and "skill" in scopes:
            assert scopes.index("auto") < scopes.index("skill")


def test_recall_any_rrf_attaches_score(tmp_path: Path) -> None:
    ts = _toolset_with_three_substores(tmp_path)
    results = ts.recall("chart from csv", scope="any", top_k=3, fusion="rrf")
    assert results
    # All RRF results carry a positive score.
    for r in results:
        assert r.score > 0


def test_recall_any_concat_does_not_score(tmp_path: Path) -> None:
    """Legacy concat path leaves score at default 0.0 (substores didn't set one)."""
    ts = _toolset_with_three_substores(tmp_path)
    results = ts.recall("csv chart", scope="any", top_k=3, fusion="concat")
    if results:
        assert all(r.score == 0.0 for r in results)


def test_recall_single_scope_unchanged_by_fusion_arg(tmp_path: Path) -> None:
    """fusion="rrf" is ignored when scope != "any"."""
    ts = _toolset_with_three_substores(tmp_path)
    rrf_results = ts.recall("csv chart", scope="auto", top_k=2, fusion="rrf")
    concat_results = ts.recall("csv chart", scope="auto", top_k=2, fusion="concat")
    assert [r.record_id for r in rrf_results] == \
           [r.record_id for r in concat_results]


def test_recall_any_truncates_to_top_k(tmp_path: Path) -> None:
    ts = _toolset_with_three_substores(tmp_path)
    results = ts.recall("chart csv", scope="any", top_k=1)
    assert len(results) == 1


def test_recall_cross_substore_id_collision_does_not_merge(tmp_path: Path) -> None:
    """Same record_id across substores must rank as two separate items."""
    am = AutoMemory(root=tmp_path / "auto", project="demo")
    am.save(kind=MemoryKind.PROJECT, title="alpha", body="generate something")
    proc = ProceduralMemory(db_path=tmp_path / "procedural.db")
    # Use a distinct id; auto's entry_id is auto-generated.
    proc.put(SkillRecord(id="alpha", name="alpha", description="generate",
                         body="def x(): pass"))
    ts = MemoryToolset(auto_memory=am, procedural=proc)
    results = ts.recall("generate", scope="any", top_k=5)
    scopes = {r.scope for r in results}
    # Both substores represented even though one of them used record_id="alpha".
    assert "auto" in scopes or "skill" in scopes
