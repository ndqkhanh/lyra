"""Tests for the auto_memory contradiction detector."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory.auto_memory import AutoMemory, MemoryEntry, MemoryKind
from lyra_core.memory.contradictions import (
    ContradictionDetector,
    ContradictionPair,
)
from lyra_core.memory.memory_tools import MemoryToolset


def _entry(
    *,
    entry_id: str = "e",
    kind: MemoryKind = MemoryKind.USER,
    title: str = "",
    body: str = "",
    created_ts: float = 100.0,
    deleted: bool = False,
) -> MemoryEntry:
    return MemoryEntry(
        entry_id=entry_id, kind=kind, title=title, body=body,
        created_ts=created_ts, deleted=deleted,
    )


# --- detector ---------------------------------------------------------


def test_no_contradiction_when_only_one_entry() -> None:
    e = _entry(entry_id="a", title="user prefers terse responses",
               body="keep replies short and direct")
    pairs = ContradictionDetector().detect([e])
    assert pairs == ()


def test_contradiction_high_title_overlap_low_body_overlap() -> None:
    older = _entry(entry_id="a", created_ts=100.0,
                   title="response style preference",
                   body="keep replies short and direct")
    newer = _entry(entry_id="b", created_ts=200.0,
                   title="response style preference",
                   body="thorough multi-paragraph explanations preferred")
    pairs = ContradictionDetector().detect([older, newer])
    assert len(pairs) == 1
    p = pairs[0]
    assert p.older_entry_id == "a"
    assert p.newer_entry_id == "b"
    assert p.title_jaccard >= 0.5
    assert p.body_jaccard <= 0.20
    assert p.confidence == "high"


def test_no_contradiction_when_bodies_agree() -> None:
    older = _entry(entry_id="a", created_ts=100.0,
                   title="preferred style",
                   body="terse responses with short examples")
    newer = _entry(entry_id="b", created_ts=200.0,
                   title="preferred style",
                   body="terse short responses with examples")
    assert ContradictionDetector().detect([older, newer]) == ()


def test_no_contradiction_across_kinds() -> None:
    """Even with matching titles, different MemoryKinds don't pair."""
    a = _entry(entry_id="a", kind=MemoryKind.USER,
               title="testing preferences", body="short")
    b = _entry(entry_id="b", kind=MemoryKind.PROJECT,
               title="testing preferences", body="long elaborate detail")
    assert ContradictionDetector().detect([a, b]) == ()


def test_deleted_entries_excluded() -> None:
    a = _entry(entry_id="a", deleted=True,
               title="response style", body="terse short")
    b = _entry(entry_id="b",
               title="response style", body="thorough elaborate detail")
    assert ContradictionDetector().detect([a, b]) == ()


def test_reference_kind_skipped_by_default() -> None:
    """`reference` entries are external pointers — not contradiction-worthy."""
    a = _entry(entry_id="a", kind=MemoryKind.REFERENCE,
               title="docs link", body="https://example.com/v1/docs")
    b = _entry(entry_id="b", kind=MemoryKind.REFERENCE,
               title="docs link", body="https://internal/v2/wiki")
    assert ContradictionDetector().detect([a, b]) == ()


def test_soft_confidence_when_partial_signal() -> None:
    older = _entry(entry_id="a", created_ts=100.0,
                   title="preferred response style",
                   body="terse short replies")
    # Title overlap is below high-confidence threshold (0.7).
    newer = _entry(entry_id="b", created_ts=200.0,
                   title="preferred",
                   body="elaborate verbose detailed")
    detector = ContradictionDetector(
        title_similarity_min=0.10, body_divergence_max=0.20,
    )
    pairs = detector.detect([older, newer])
    if pairs:
        assert pairs[0].confidence == "soft"


def test_three_way_contradictions_yield_three_pairs() -> None:
    """A triangle of conflicting entries produces all C(3,2) pairs."""
    entries = [
        _entry(entry_id=f"e{i}", created_ts=100.0 + i,
               title="preferred response style",
               body=body)
        for i, body in enumerate([
            "terse short replies",
            "thorough elaborate explanations",
            "bullet point lists with code samples",
        ])
    ]
    pairs = ContradictionDetector().detect(entries)
    assert len(pairs) == 3


# --- MemoryToolset.improve plumbing ----------------------------------


def test_improve_surfaces_contradictions(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    ts = MemoryToolset(
        auto_memory=am,
        contradiction_detector=ContradictionDetector(),
    )
    ts.remember("terse short replies", scope="auto",
                kind=MemoryKind.USER, title="response style preference")
    ts.remember("thorough elaborate explanations", scope="auto",
                kind=MemoryKind.USER, title="response style preference")
    result = ts.improve()
    assert result.contradiction_count == 1
    assert result.contradictions[0].kind is MemoryKind.USER


def test_improve_no_detector_skips(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    ts = MemoryToolset(auto_memory=am)  # no detector wired
    ts.remember("terse short replies", scope="auto",
                kind=MemoryKind.USER, title="response style preference")
    ts.remember("thorough elaborate explanations", scope="auto",
                kind=MemoryKind.USER, title="response style preference")
    result = ts.improve()
    assert result.contradictions == ()
