"""Tests for the episodic→semantic consolidator."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory.auto_memory import AutoMemory, MemoryEntry, MemoryKind
from lyra_core.memory.consolidator import (
    ConsolidationProposal,
    MemoryConsolidator,
)
from lyra_core.memory.memory_tools import MemoryToolset


def _entry(
    *,
    entry_id: str,
    kind: MemoryKind = MemoryKind.PROJECT,
    title: str = "",
    body: str = "",
    created_ts: float = 100.0,
    deleted: bool = False,
) -> MemoryEntry:
    return MemoryEntry(
        entry_id=entry_id, kind=kind, title=title, body=body,
        created_ts=created_ts, deleted=deleted,
    )


# --- consolidator ---------------------------------------------------


def test_no_proposal_below_min_cluster_size() -> None:
    entries = [
        _entry(entry_id="a", title="csv chart", body="generate chart from csv"),
        _entry(entry_id="b", title="csv chart", body="csv data plotted"),
    ]
    assert MemoryConsolidator().propose(entries) == ()


def test_cluster_promoted_when_threshold_reached() -> None:
    entries = [
        _entry(entry_id=f"e{i}",
               title="csv chart",
               body=f"generate chart from csv with pandas variant {i}")
        for i in range(4)
    ]
    proposals = MemoryConsolidator().propose(entries)
    assert len(proposals) == 1
    p = proposals[0]
    assert p.member_count == 4
    assert "csv" in p.shared_tokens or "chart" in p.shared_tokens
    assert p.cohesion > 0.0


def test_two_clusters_two_proposals() -> None:
    chart_entries = [
        _entry(entry_id=f"chart{i}",
               title="csv chart",
               body=f"generate chart from csv pandas variant {i}")
        for i in range(3)
    ]
    invoice_entries = [
        _entry(entry_id=f"invoice{i}",
               title="invoice OCR",
               body=f"process invoices with tesseract variant {i}")
        for i in range(3)
    ]
    proposals = MemoryConsolidator().propose(chart_entries + invoice_entries)
    assert len(proposals) == 2
    titles = {p.proposed_title for p in proposals}
    assert any("chart" in t or "csv" in t for t in titles)
    assert any("invoice" in t or "ocr" in t for t in titles)


def test_only_kinds_filter_drops_user_entries() -> None:
    entries = [
        _entry(entry_id=f"u{i}", kind=MemoryKind.USER,
               title="role preference",
               body=f"prefers terse responses variant {i}")
        for i in range(4)
    ]
    proposals = MemoryConsolidator().propose(entries)
    assert proposals == ()


def test_deleted_entries_excluded() -> None:
    entries = [
        _entry(entry_id="a", deleted=True,
               title="csv chart", body="generate chart from csv pandas"),
        *[
            _entry(entry_id=f"b{i}",
                   title="csv chart",
                   body=f"generate chart from csv pandas variant {i}")
            for i in range(3)
        ],
    ]
    proposals = MemoryConsolidator().propose(entries)
    # The deleted entry should not be a member.
    if proposals:
        assert "a" not in proposals[0].member_entry_ids


def test_proposal_records_member_ids_in_temporal_order() -> None:
    entries = [
        _entry(entry_id="late", created_ts=300.0,
               title="csv chart", body="generate chart from csv variant 3"),
        _entry(entry_id="early", created_ts=100.0,
               title="csv chart", body="generate chart from csv variant 1"),
        _entry(entry_id="mid", created_ts=200.0,
               title="csv chart", body="generate chart from csv variant 2"),
    ]
    proposals = MemoryConsolidator().propose(entries)
    assert len(proposals) == 1
    # Members are clustered in created_ts order.
    assert proposals[0].member_entry_ids == ("early", "mid", "late")


def test_proposal_synthesises_title_from_shared_tokens() -> None:
    entries = [
        _entry(entry_id=f"e{i}",
               title="generate csv chart",
               body=f"use pandas to plot dataframes variant {i}")
        for i in range(4)
    ]
    proposals = MemoryConsolidator().propose(entries)
    assert proposals
    title = proposals[0].proposed_title
    # Title should contain at least one of the high-frequency tokens.
    assert any(tok in title for tok in ("csv", "chart", "pandas", "generate"))


def test_max_proposals_caps_output() -> None:
    """With a low cap, only the first N clusters are returned."""
    cluster_words = [
        ("alpha", "beta", "gamma", "delta"),
        ("epsilon", "zeta", "eta", "theta"),
        ("iota", "kappa", "lambda", "sigma"),
        ("rho", "tau", "upsilon", "phi"),
        ("psi", "omega", "ascii", "morpho"),
    ]
    big: list[MemoryEntry] = []
    for cluster_idx, words in enumerate(cluster_words):
        for i in range(3):
            big.append(_entry(
                entry_id=f"c{cluster_idx}_e{i}",
                title=f"{words[0]} {words[1]}",
                body=f"{words[0]} {words[1]} {words[2]} {words[3]} variant",
            ))
    consolidator = MemoryConsolidator(max_proposals=2)
    proposals = consolidator.propose(big)
    assert len(proposals) == 2


# --- MemoryToolset plumbing -------------------------------------------


def test_improve_surfaces_consolidations(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    ts = MemoryToolset(
        auto_memory=am,
        consolidator=MemoryConsolidator(),
    )
    for i in range(4):
        ts.remember(
            f"generate chart from csv pandas variant {i}",
            scope="auto", kind=MemoryKind.PROJECT,
            title="csv chart",
        )
    result = ts.improve()
    assert result.consolidation_count >= 1
    assert all(isinstance(p, ConsolidationProposal) for p in result.consolidations)


def test_improve_no_consolidator_skips(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    ts = MemoryToolset(auto_memory=am)  # no consolidator
    for i in range(4):
        ts.remember(
            f"generate chart from csv variant {i}",
            scope="auto", kind=MemoryKind.PROJECT, title="csv chart",
        )
    result = ts.improve()
    assert result.consolidations == ()


def test_improve_runs_both_passes(tmp_path: Path) -> None:
    """Contradictions and consolidations co-exist on the same heartbeat."""
    from lyra_core.memory.contradictions import ContradictionDetector
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    ts = MemoryToolset(
        auto_memory=am,
        contradiction_detector=ContradictionDetector(),
        consolidator=MemoryConsolidator(),
    )
    # Three project entries form a consolidation cluster.
    for i in range(3):
        ts.remember(
            f"generate chart from csv pandas variant {i}",
            scope="auto", kind=MemoryKind.PROJECT, title="csv chart",
        )
    # Two user entries form a contradiction.
    ts.remember("terse short replies",
                scope="auto", kind=MemoryKind.USER,
                title="response style preference")
    ts.remember("thorough elaborate explanations",
                scope="auto", kind=MemoryKind.USER,
                title="response style preference")
    result = ts.improve()
    assert result.consolidation_count >= 1
    assert result.contradiction_count >= 1
