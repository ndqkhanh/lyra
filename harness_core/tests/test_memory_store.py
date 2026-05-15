"""Tests for harness_core.memory_store — types + store + working memory."""
from __future__ import annotations

import time

import pytest

from harness_core.memory_store import (
    MemoryItem,
    MemoryKind,
    MemoryStore,
    RetrievalSpec,
    WorkingMemory,
)


# --- MemoryItem --------------------------------------------------------


class TestMemoryItem:
    def test_create(self):
        item = MemoryItem.create(
            kind=MemoryKind.SEMANTIC,
            content="Paris is the capital of France.",
            namespace="default",
        )
        assert item.kind == MemoryKind.SEMANTIC
        assert item.access_count == 0
        assert item.item_id

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            MemoryItem(item_id="", kind=MemoryKind.SEMANTIC, content="x")

    def test_empty_content_rejected(self):
        with pytest.raises(ValueError):
            MemoryItem.create(kind=MemoryKind.SEMANTIC, content="")

    def test_empty_namespace_rejected(self):
        with pytest.raises(ValueError):
            MemoryItem.create(kind=MemoryKind.SEMANTIC, content="x", namespace="")

    def test_invalid_importance_rejected(self):
        with pytest.raises(ValueError):
            MemoryItem.create(kind=MemoryKind.SEMANTIC, content="x", importance=1.5)

    def test_touched_increments_access(self):
        item = MemoryItem.create(kind=MemoryKind.SEMANTIC, content="x")
        touched = item.touched()
        assert touched.access_count == 1
        assert item.access_count == 0  # original unchanged

    def test_with_importance(self):
        item = MemoryItem.create(kind=MemoryKind.SEMANTIC, content="x", importance=0.5)
        new = item.with_importance(0.9)
        assert new.importance == 0.9
        assert item.importance == 0.5

    def test_with_importance_invalid(self):
        item = MemoryItem.create(kind=MemoryKind.SEMANTIC, content="x")
        with pytest.raises(ValueError):
            item.with_importance(1.5)


class TestRetrievalSpec:
    def test_valid(self):
        s = RetrievalSpec(query="paris", top_k=5)
        assert s.top_k == 5

    def test_invalid_top_k(self):
        with pytest.raises(ValueError):
            RetrievalSpec(top_k=0)

    def test_invalid_min_importance(self):
        with pytest.raises(ValueError):
            RetrievalSpec(min_importance=1.5)

    def test_invalid_sort_by(self):
        with pytest.raises(ValueError):
            RetrievalSpec(sort_by="bogus")


# --- MemoryStore -------------------------------------------------------


class TestMemoryStoreCRUD:
    def test_write_and_get(self):
        store = MemoryStore()
        item = store.write(kind=MemoryKind.SEMANTIC, content="paris is france capital")
        retrieved = store.get(item.item_id)
        assert retrieved is not None
        assert retrieved.content == "paris is france capital"

    def test_get_with_touch(self):
        store = MemoryStore()
        item = store.write(kind=MemoryKind.SEMANTIC, content="x")
        retrieved = store.get(item.item_id, touch=True)
        assert retrieved.access_count == 1
        # Re-fetch confirms persistence.
        again = store.get(item.item_id)
        assert again.access_count == 1

    def test_get_missing_returns_none(self):
        store = MemoryStore()
        assert store.get("nonexistent") is None

    def test_insert_existing_item(self):
        store = MemoryStore()
        item = MemoryItem.create(kind=MemoryKind.SEMANTIC, content="x")
        store.insert(item)
        assert store.get(item.item_id) is item

    def test_insert_duplicate_rejected(self):
        store = MemoryStore()
        item = store.write(kind=MemoryKind.SEMANTIC, content="x")
        with pytest.raises(ValueError):
            store.insert(item)

    def test_delete(self):
        store = MemoryStore()
        item = store.write(kind=MemoryKind.SEMANTIC, content="x")
        assert store.delete(item.item_id) is True
        assert store.delete(item.item_id) is False

    def test_update_importance(self):
        store = MemoryStore()
        item = store.write(kind=MemoryKind.SEMANTIC, content="x", importance=0.5)
        updated = store.update_importance(item.item_id, 0.9)
        assert updated.importance == 0.9
        assert store.update_importance("nonexistent", 0.9) is None

    def test_len_and_contains(self):
        store = MemoryStore()
        assert len(store) == 0
        item = store.write(kind=MemoryKind.SEMANTIC, content="x")
        assert len(store) == 1
        assert item.item_id in store
        assert "missing" not in store


# --- MemoryStore search ------------------------------------------------


class TestMemoryStoreSearch:
    def _populate(self) -> MemoryStore:
        store = MemoryStore()
        store.write(
            kind=MemoryKind.SEMANTIC,
            content="Paris is the capital of France",
            tags=("geography", "europe"),
            importance=0.9,
        )
        store.write(
            kind=MemoryKind.SEMANTIC,
            content="Tokyo is the capital of Japan",
            tags=("geography", "asia"),
            importance=0.8,
        )
        store.write(
            kind=MemoryKind.EPISODIC,
            content="Yesterday I visited the Louvre in Paris",
            tags=("travel",),
            importance=0.6,
        )
        return store

    def test_keyword_search(self):
        store = self._populate()
        hits = store.search(RetrievalSpec(query="paris"))
        # Both the Paris fact and the Louvre event match.
        assert len(hits) == 2

    def test_filter_by_kind(self):
        store = self._populate()
        hits = store.search(RetrievalSpec(query="paris", kind=MemoryKind.SEMANTIC))
        assert len(hits) == 1
        assert hits[0].kind == MemoryKind.SEMANTIC

    def test_filter_by_tag(self):
        store = self._populate()
        hits = store.search(RetrievalSpec(query="capital", tags=frozenset({"asia"})))
        assert len(hits) == 1
        assert "Tokyo" in hits[0].content

    def test_filter_by_namespace(self):
        store = MemoryStore()
        store.write(kind=MemoryKind.SEMANTIC, content="x", namespace="ns1")
        store.write(kind=MemoryKind.SEMANTIC, content="x", namespace="ns2")
        hits = store.search(RetrievalSpec(query="x", namespace="ns1"))
        assert len(hits) == 1
        assert hits[0].namespace == "ns1"

    def test_filter_by_min_importance(self):
        store = self._populate()
        hits = store.search(RetrievalSpec(query="capital", min_importance=0.85))
        # Only Paris fact (0.9) passes.
        assert len(hits) == 1
        assert "Paris" in hits[0].content

    def test_top_k(self):
        store = self._populate()
        hits = store.search(RetrievalSpec(query="capital", top_k=1))
        assert len(hits) == 1

    def test_no_query_ranks_by_importance(self):
        store = self._populate()
        hits = store.search(RetrievalSpec(top_k=10))
        # Highest importance (Paris fact, 0.9) first.
        assert "Paris" in hits[0].content

    def test_sort_by_recency(self):
        store = MemoryStore()
        store.write(kind=MemoryKind.SEMANTIC, content="old", importance=0.9)
        time.sleep(0.001)  # ensure different timestamps
        store.write(kind=MemoryKind.SEMANTIC, content="new", importance=0.5)
        hits = store.search(RetrievalSpec(top_k=10, sort_by="recency"))
        # Most recent first regardless of importance.
        assert hits[0].content == "new"

    def test_sort_by_access_count(self):
        store = MemoryStore()
        a = store.write(kind=MemoryKind.SEMANTIC, content="A", importance=0.5)
        b = store.write(kind=MemoryKind.SEMANTIC, content="B", importance=0.5)
        # Touch A twice, B once.
        store.get(a.item_id, touch=True)
        store.get(a.item_id, touch=True)
        store.get(b.item_id, touch=True)
        hits = store.search(RetrievalSpec(top_k=10, sort_by="access_count"))
        assert hits[0].content == "A"

    def test_keyword_score_ranks_by_overlap(self):
        store = MemoryStore()
        store.write(kind=MemoryKind.SEMANTIC, content="paris france capital")
        store.write(kind=MemoryKind.SEMANTIC, content="paris is great")
        hits = store.search(RetrievalSpec(query="paris france capital"))
        # First doc matches all 3 query tokens; second matches only "paris".
        assert hits[0].content == "paris france capital"

    def test_search_no_match_returns_empty(self):
        store = MemoryStore()
        store.write(kind=MemoryKind.SEMANTIC, content="paris")
        hits = store.search(RetrievalSpec(query="xyz123"))
        assert hits == []

    def test_search_empty_store_returns_empty(self):
        store = MemoryStore()
        assert store.search(RetrievalSpec(query="x")) == []


# --- MemoryStore maintenance ------------------------------------------


class TestMemoryStoreMaintenance:
    def test_garbage_collect_by_age(self):
        store = MemoryStore()
        # Insert a synthetic-aged item.
        old_ts = time.time() - 1000
        store.insert(MemoryItem.create(
            kind=MemoryKind.WORKING,
            content="old",
            timestamp=old_ts,
        ))
        store.write(kind=MemoryKind.WORKING, content="new")
        removed = store.garbage_collect(max_age_seconds=500)
        assert removed == 1
        assert len(store) == 1

    def test_garbage_collect_top_k(self):
        store = MemoryStore()
        for i in range(5):
            store.write(
                kind=MemoryKind.SEMANTIC,
                content=f"item{i}",
                importance=0.1 * i,
            )
        # Keep top-2 by importance; drop 3.
        removed = store.garbage_collect(keep_top_k=2)
        assert removed == 3
        assert len(store) == 2
        # Highest-importance items survive.
        remaining = list(store._items.values())
        importances = sorted([i.importance for i in remaining], reverse=True)
        assert importances[0] == pytest.approx(0.4)
        assert importances[1] == pytest.approx(0.3)

    def test_garbage_collect_scoped_by_kind(self):
        store = MemoryStore()
        store.write(kind=MemoryKind.SEMANTIC, content="keep me", importance=0.9)
        for i in range(3):
            store.write(kind=MemoryKind.WORKING, content=f"work{i}", importance=0.1)
        # GC only working memory; keep top-1.
        removed = store.garbage_collect(keep_top_k=1, kind=MemoryKind.WORKING)
        assert removed == 2  # 2 of 3 working dropped
        # Semantic preserved.
        assert any(i.kind == MemoryKind.SEMANTIC for i in store._items.values())

    def test_clear_namespace(self):
        store = MemoryStore()
        store.write(kind=MemoryKind.SEMANTIC, content="A", namespace="proj-A")
        store.write(kind=MemoryKind.SEMANTIC, content="B", namespace="proj-A")
        store.write(kind=MemoryKind.SEMANTIC, content="C", namespace="proj-B")
        n = store.clear_namespace("proj-A")
        assert n == 2
        assert len(store) == 1

    def test_stats(self):
        store = MemoryStore()
        store.write(kind=MemoryKind.SEMANTIC, content="x", namespace="A", tags=("t1",))
        store.write(kind=MemoryKind.SEMANTIC, content="y", namespace="B", tags=("t2",))
        store.write(kind=MemoryKind.EPISODIC, content="z", namespace="A", tags=("t1", "t3"))
        s = store.stats()
        assert s["total"] == 3
        assert s["semantic"] == 2
        assert s["episodic"] == 1
        assert s["namespaces"] == 2
        assert s["distinct_tags"] == 3


# --- WorkingMemory -----------------------------------------------------


class TestWorkingMemory:
    def test_push_and_recent(self):
        wm = WorkingMemory(capacity=10)
        wm.push(content="a")
        wm.push(content="b")
        wm.push(content="c")
        recent = wm.recent(n=2)
        # Newest first.
        assert recent[0].content == "c"
        assert recent[1].content == "b"

    def test_capacity_eviction(self):
        wm = WorkingMemory(capacity=3)
        for i in range(5):
            wm.push(content=f"item{i}")
        assert len(wm) == 3
        # Items 0 and 1 evicted; 2, 3, 4 remain.
        all_items = wm.all()
        contents = [i.content for i in all_items]
        assert contents == ["item2", "item3", "item4"]

    def test_at_capacity(self):
        wm = WorkingMemory(capacity=2)
        wm.push(content="a")
        assert wm.at_capacity() is False
        wm.push(content="b")
        assert wm.at_capacity() is True

    def test_utilization(self):
        wm = WorkingMemory(capacity=4)
        wm.push(content="a")
        wm.push(content="b")
        assert wm.utilization == 0.5

    def test_peek(self):
        wm = WorkingMemory(capacity=3)
        assert wm.peek() is None
        wm.push(content="latest")
        assert wm.peek().content == "latest"
        # Peek doesn't remove.
        assert len(wm) == 1

    def test_clear(self):
        wm = WorkingMemory(capacity=3)
        for i in range(3):
            wm.push(content=f"x{i}")
        n = wm.clear()
        assert n == 3
        assert len(wm) == 0

    def test_capacity_must_be_positive(self):
        with pytest.raises(ValueError):
            WorkingMemory(capacity=0)
        with pytest.raises(ValueError):
            WorkingMemory(capacity=-1)

    def test_recent_negative_n(self):
        wm = WorkingMemory()
        with pytest.raises(ValueError):
            wm.recent(n=-1)

    def test_pushed_items_have_working_kind(self):
        wm = WorkingMemory()
        item = wm.push(content="x")
        assert item.kind == MemoryKind.WORKING

    def test_push_with_tags_and_importance(self):
        wm = WorkingMemory()
        item = wm.push(content="x", importance=0.8, tags=("tag1",))
        assert item.importance == 0.8
        assert "tag1" in item.tags


# --- End-to-end Mentat-Learn-style scenario ---------------------------


class TestMentatLearnScenario:
    """Realistic scenario: Mentat-Learn manages per-user memory across
    semantic + episodic + working layers; per-channel namespace isolation
    via the namespace key."""

    def test_per_user_per_channel(self):
        store = MemoryStore()

        # User Alice on Slack channel — semantic + episodic.
        store.write(
            kind=MemoryKind.SEMANTIC,
            content="Alice's manager is Bob.",
            namespace="user:alice/channel:slack",
            importance=0.8,
            tags=("work", "people"),
        )
        store.write(
            kind=MemoryKind.EPISODIC,
            content="On Tuesday, Alice asked about the Q2 deadline.",
            namespace="user:alice/channel:slack",
            importance=0.6,
            tags=("work",),
        )
        # User Bob on Slack — separate namespace.
        store.write(
            kind=MemoryKind.SEMANTIC,
            content="Bob's preferred timezone is PT.",
            namespace="user:bob/channel:slack",
            importance=0.7,
            tags=("personal",),
        )
        # Cross-namespace search isolation.
        alice_hits = store.search(RetrievalSpec(
            query="manager", namespace="user:alice/channel:slack",
        ))
        assert len(alice_hits) == 1
        assert "Bob" in alice_hits[0].content
        # Bob's namespace should not see Alice's data.
        bob_hits = store.search(RetrievalSpec(
            query="manager", namespace="user:bob/channel:slack",
        ))
        assert bob_hits == []

    def test_working_memory_per_session(self):
        """Each session has its own WorkingMemory instance."""
        wm1 = WorkingMemory(capacity=5, namespace="session-1")
        wm2 = WorkingMemory(capacity=5, namespace="session-2")
        wm1.push(content="session 1 thought")
        wm2.push(content="session 2 thought")
        # Each is its own buffer.
        assert wm1.peek().content == "session 1 thought"
        assert wm2.peek().content == "session 2 thought"
        # And the namespace is recorded on the items.
        assert wm1.peek().namespace == "session-1"
        assert wm2.peek().namespace == "session-2"
