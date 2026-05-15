"""Tests for memory backend protocol + in-memory default (Phase CE.3, P2-5)."""
from __future__ import annotations

import pytest

from lyra_core.memory.backend import (
    InMemoryBackend,
    MemoryRecord,
    SearchHit,
    make_record,
)


# ────────────────────────────────────────────────────────────────
# MemoryRecord / SearchHit validation
# ────────────────────────────────────────────────────────────────


def test_record_rejects_empty_id():
    with pytest.raises(ValueError):
        MemoryRecord(id="", kind="fact", content="x", ts=1.0)


def test_record_rejects_empty_kind():
    with pytest.raises(ValueError):
        MemoryRecord(id="r1", kind="", content="x", ts=1.0)


def test_search_hit_rejects_negative_score():
    rec = MemoryRecord(id="r1", kind="fact", content="x", ts=1.0)
    with pytest.raises(ValueError):
        SearchHit(record=rec, score=-0.01)


# ────────────────────────────────────────────────────────────────
# make_record helper
# ────────────────────────────────────────────────────────────────


def test_make_record_defaults_ts_to_now():
    rec = make_record(id="r1", kind="fact", content="x")
    assert rec.ts > 0


def test_make_record_propagates_metadata_copy():
    md = {"src": "test"}
    rec = make_record(id="r1", kind="fact", content="x", metadata=md)
    md["src"] = "mutated"
    assert rec.metadata == {"src": "test"}  # not aliased


# ────────────────────────────────────────────────────────────────
# write / get / delete
# ────────────────────────────────────────────────────────────────


def test_write_then_get_roundtrip():
    b = InMemoryBackend()
    rec = make_record(id="r1", kind="fact", content="hello")
    b.write(rec)
    assert b.get("r1") == rec


def test_write_is_idempotent_by_id():
    b = InMemoryBackend()
    b.write(make_record(id="r1", kind="fact", content="first"))
    b.write(make_record(id="r1", kind="fact", content="second"))
    assert len(b) == 1
    assert b.get("r1") is not None
    assert b.get("r1").content == "second"  # type: ignore[union-attr]


def test_get_missing_returns_none():
    assert InMemoryBackend().get("nope") is None


def test_delete_returns_true_when_present():
    b = InMemoryBackend()
    b.write(make_record(id="r1", kind="fact", content="x"))
    assert b.delete("r1") is True
    assert b.delete("r1") is False
    assert b.get("r1") is None


# ────────────────────────────────────────────────────────────────
# search
# ────────────────────────────────────────────────────────────────


def test_search_finds_keyword_overlap():
    b = InMemoryBackend()
    b.write(make_record(id="a", kind="fact", content="postgres 17 with pgvector"))
    b.write(make_record(id="b", kind="fact", content="redis caching for hot path"))
    hits = b.search("postgres")
    assert len(hits) == 1
    assert hits[0].record.id == "a"


def test_search_orders_by_score_then_ts():
    b = InMemoryBackend()
    b.write(make_record(id="a", kind="fact", content="alpha beta", ts=1.0))
    b.write(make_record(id="b", kind="fact", content="alpha", ts=2.0))
    hits = b.search("alpha beta")
    # 'a' scores 2/2; 'b' scores 1/2
    assert [h.record.id for h in hits] == ["a", "b"]


def test_search_respects_limit():
    b = InMemoryBackend()
    for i in range(10):
        b.write(make_record(id=f"r{i}", kind="fact", content="needle"))
    hits = b.search("needle", limit=3)
    assert len(hits) == 3


def test_search_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        InMemoryBackend().search("q", limit=0)


def test_search_excludes_private_by_default():
    b = InMemoryBackend()
    b.write(make_record(id="public", kind="fact", content="needle"))
    b.write(make_record(id="secret", kind="fact", content="needle", is_private=True))
    hits = b.search("needle")
    assert [h.record.id for h in hits] == ["public"]


def test_search_includes_private_when_requested():
    b = InMemoryBackend()
    b.write(make_record(id="secret", kind="fact", content="needle", is_private=True))
    hits = b.search("needle", include_private=True)
    assert hits[0].record.id == "secret"


def test_search_uses_tag_index_too():
    b = InMemoryBackend()
    b.write(make_record(id="a", kind="fact", content="db notes", tags=("postgres",)))
    hits = b.search("postgres")
    assert len(hits) == 1


def test_search_empty_query_returns_no_hits():
    b = InMemoryBackend()
    b.write(make_record(id="a", kind="fact", content="anything"))
    assert b.search("") == []
    assert b.search("   ") == []


# ────────────────────────────────────────────────────────────────
# timeline
# ────────────────────────────────────────────────────────────────


def test_timeline_orders_newest_first():
    b = InMemoryBackend()
    b.write(make_record(id="old", kind="fact", content="x", ts=1.0))
    b.write(make_record(id="new", kind="fact", content="x", ts=2.0))
    rows = b.timeline()
    assert [r.id for r in rows] == ["new", "old"]


def test_timeline_filters_by_tag():
    b = InMemoryBackend()
    b.write(make_record(id="a", kind="fact", content="x", tags=("db",), ts=1.0))
    b.write(make_record(id="b", kind="fact", content="x", tags=("ui",), ts=2.0))
    rows = b.timeline(tag="db")
    assert [r.id for r in rows] == ["a"]


def test_timeline_filters_by_time_window():
    b = InMemoryBackend()
    for i in range(5):
        b.write(make_record(id=f"r{i}", kind="fact", content="x", ts=float(i)))
    rows = b.timeline(since=2.0, until=3.5)
    ids = {r.id for r in rows}
    assert ids == {"r2", "r3"}


def test_timeline_respects_limit():
    b = InMemoryBackend()
    for i in range(10):
        b.write(make_record(id=f"r{i}", kind="fact", content="x", ts=float(i)))
    rows = b.timeline(limit=4)
    assert len(rows) == 4


def test_timeline_excludes_private_by_default():
    b = InMemoryBackend()
    b.write(
        make_record(id="public", kind="fact", content="x", ts=1.0)
    )
    b.write(
        make_record(id="secret", kind="fact", content="x", ts=2.0, is_private=True)
    )
    rows = b.timeline()
    assert [r.id for r in rows] == ["public"]


def test_timeline_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        InMemoryBackend().timeline(limit=0)


# ────────────────────────────────────────────────────────────────
# admin helpers
# ────────────────────────────────────────────────────────────────


def test_len_reflects_store_size():
    b = InMemoryBackend()
    assert len(b) == 0
    b.write(make_record(id="r1", kind="fact", content="x"))
    assert len(b) == 1


def test_all_yields_everything_including_private():
    b = InMemoryBackend()
    b.write(make_record(id="public", kind="fact", content="x"))
    b.write(make_record(id="secret", kind="fact", content="x", is_private=True))
    ids = {r.id for r in b.all()}
    assert ids == {"public", "secret"}


# ────────────────────────────────────────────────────────────────
# Protocol conformance
# ────────────────────────────────────────────────────────────────


def test_in_memory_backend_satisfies_protocol():
    """Importing as Protocol should structurally match."""
    from lyra_core.memory.backend import MemoryBackend

    backend: MemoryBackend = InMemoryBackend()
    backend.write(make_record(id="r", kind="fact", content="x"))
    assert backend.get("r") is not None
