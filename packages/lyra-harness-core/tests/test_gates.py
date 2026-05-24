"""Tests for harness_core.gates — Chain-of-Note quality gate."""
from __future__ import annotations

import pytest

from harness_core.gates import (
    ChainOfNoteGate,
    DocVerdict,
    NoteVerdict,
)


def _stub_writer_match(*, query, doc_id, content):
    """Stub note-writer: verdict by substring presence. Check 'kinda' first
    because 'kinda match' contains 'match' as a substring."""
    if "kinda" in content:
        v = NoteVerdict.PARTIAL
        score = 0.5
    elif "match" in content:
        v = NoteVerdict.RELEVANT
        score = 1.0
    else:
        v = NoteVerdict.IRRELEVANT
        score = 0.0
    return DocVerdict(doc_id=doc_id, verdict=v, note=f"contains '{v.value}'", score=score)


def _stub_writer_raises(*, query, doc_id, content):
    raise RuntimeError("LM unreachable")


class TestDocVerdict:
    def test_valid_score(self):
        v = DocVerdict(doc_id="a", verdict=NoteVerdict.RELEVANT, note="x", score=0.8)
        assert v.score == 0.8

    def test_invalid_score(self):
        with pytest.raises(ValueError):
            DocVerdict(doc_id="a", verdict=NoteVerdict.RELEVANT, note="x", score=1.5)

    def test_frozen(self):
        v = DocVerdict(doc_id="a", verdict=NoteVerdict.RELEVANT, note="x", score=0.8)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            v.score = 0.5  # type: ignore[misc]


class TestChainOfNoteGate:
    def test_filter_passes_relevant(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_match, threshold=0.5)
        results = gate.filter(
            query="q",
            docs=[{"id": "a", "content": "match here"}, {"id": "b", "content": "noise"}],
        )
        assert len(results) == 2
        kept = [r for r in results if r.passed]
        assert len(kept) == 1
        assert kept[0].doc_id == "a"

    def test_filter_passed_only(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_match, threshold=0.5)
        kept = gate.filter_passed_only(
            query="q",
            docs=[
                {"id": "a", "content": "match"},
                {"id": "b", "content": "kinda match"},  # 0.5 → passed
                {"id": "c", "content": "noise"},
            ],
        )
        assert {d.doc_id for d in kept} == {"a", "b"}

    def test_threshold_strict(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_match, threshold=0.6)
        kept = gate.filter_passed_only(
            query="q",
            docs=[
                {"id": "a", "content": "match"},  # 1.0 passes
                {"id": "b", "content": "kinda match"},  # 0.5 < 0.6 fails
            ],
        )
        assert {d.doc_id for d in kept} == {"a"}

    def test_fail_closed_on_writer_error(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_raises, threshold=0.5, fail_closed=True)
        results = gate.filter(query="q", docs=[{"id": "a", "content": "any"}])
        assert len(results) == 1
        assert not results[0].passed
        assert results[0].verdict.verdict == NoteVerdict.IRRELEVANT
        assert "fail_closed" in results[0].verdict.note

    def test_fail_open_propagates(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_raises, threshold=0.5, fail_closed=False)
        with pytest.raises(RuntimeError):
            gate.filter(query="q", docs=[{"id": "a", "content": "any"}])

    def test_stats(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_match, threshold=0.5)
        results = gate.filter(
            query="q",
            docs=[
                {"id": "a", "content": "match"},
                {"id": "b", "content": "kinda match"},
                {"id": "c", "content": "noise"},
            ],
        )
        stats = gate.stats(results)
        assert stats["relevant"] == 1
        assert stats["partial"] == 1
        assert stats["irrelevant"] == 1
        assert stats["passed"] == 2
        assert stats["dropped"] == 1

    def test_empty_docs(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_match, threshold=0.5)
        assert gate.filter(query="q", docs=[]) == []

    def test_missing_content_defaults_empty(self):
        gate = ChainOfNoteGate(note_writer=_stub_writer_match, threshold=0.5)
        results = gate.filter(query="q", docs=[{"id": "a"}])
        # Empty content → no "match" or "kinda" → IRRELEVANT, score 0, dropped
        assert results[0].passed is False
