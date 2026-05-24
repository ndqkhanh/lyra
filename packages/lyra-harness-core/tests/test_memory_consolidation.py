"""Tests for harness_core.memory_consolidation."""
from __future__ import annotations

import pytest

from harness_core.memory_consolidation import (
    ConsolidationPolicy,
    ConsolidationReport,
    ExtractiveSummarizer,
    MemoryConsolidator,
    TagGrouping,
    TokenJaccardGrouping,
)
from harness_core.memory_store import MemoryItem, MemoryKind, MemoryStore
from harness_core.provenance import WitnessLattice


# --- Fixtures ---------------------------------------------------------


def _store_with_old_episodic(n: int, *, tag: str, namespace: str = "default") -> MemoryStore:
    """Build a store containing N old EPISODIC items sharing one tag."""
    store = MemoryStore()
    for i in range(n):
        item = MemoryItem.create(
            kind=MemoryKind.EPISODIC,
            content=f"Event {i}: agent-{tag} performed action {i}",
            namespace=namespace,
            importance=0.5,
            tags=(tag, "session-1"),
            timestamp=1_000_000.0 + i,  # deterministic; far in the past
        )
        store.insert(item)
    return store


# --- ConsolidationPolicy validation ----------------------------------


class TestConsolidationPolicy:
    def test_default_construction(self):
        p = ConsolidationPolicy()
        assert p.min_group_size == 3
        assert p.target_kinds == (MemoryKind.EPISODIC, MemoryKind.WORKING)

    def test_negative_age_rejected(self):
        with pytest.raises(ValueError):
            ConsolidationPolicy(min_age_seconds=-1)

    def test_min_group_size_below_2_rejected(self):
        with pytest.raises(ValueError):
            ConsolidationPolicy(min_group_size=1)

    def test_importance_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            ConsolidationPolicy(preserve_min_importance=1.5)

    def test_empty_target_kinds_rejected(self):
        with pytest.raises(ValueError):
            ConsolidationPolicy(target_kinds=())


# --- TagGrouping ------------------------------------------------------


class TestTagGrouping:
    def test_groups_items_with_shared_tag(self):
        a = MemoryItem.create(kind=MemoryKind.EPISODIC, content="x", tags=("alpha",))
        b = MemoryItem.create(kind=MemoryKind.EPISODIC, content="y", tags=("alpha",))
        c = MemoryItem.create(kind=MemoryKind.EPISODIC, content="z", tags=("beta",))
        groups = TagGrouping().group([a, b, c])
        sizes = sorted(len(g) for g in groups)
        assert sizes == [1, 2]

    def test_min_shared_tags_two(self):
        a = MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="x", tags=("alpha", "beta"),
        )
        b = MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="y", tags=("alpha", "gamma"),
        )
        c = MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="z", tags=("alpha", "beta"),
        )
        # min_shared_tags=2: a & c share two; b shares only one with both.
        groups = TagGrouping(min_shared_tags=2).group([a, b, c])
        sizes = sorted(len(g) for g in groups)
        assert sizes == [1, 2]

    def test_untagged_items_singletons(self):
        items = [
            MemoryItem.create(kind=MemoryKind.EPISODIC, content=f"x{i}")
            for i in range(3)
        ]
        groups = TagGrouping().group(items)
        # Untagged → no shared tags → each item is its own group.
        assert len(groups) == 3
        assert all(len(g) == 1 for g in groups)

    def test_empty_input(self):
        assert TagGrouping().group([]) == []

    def test_invalid_min_shared_tags(self):
        with pytest.raises(ValueError):
            TagGrouping(min_shared_tags=0)


# --- TokenJaccardGrouping ---------------------------------------------


class TestTokenJaccardGrouping:
    def test_high_overlap_grouped(self):
        a = MemoryItem.create(
            kind=MemoryKind.EPISODIC,
            content="agent retrieved doc about paris france",
        )
        b = MemoryItem.create(
            kind=MemoryKind.EPISODIC,
            content="agent retrieved doc about paris museums",
        )
        c = MemoryItem.create(
            kind=MemoryKind.EPISODIC,
            content="completely unrelated text about quantum physics topics",
        )
        groups = TokenJaccardGrouping(threshold=0.4).group([a, b, c])
        sizes = sorted(len(g) for g in groups)
        assert sizes == [1, 2]

    def test_threshold_validation(self):
        with pytest.raises(ValueError):
            TokenJaccardGrouping(threshold=0.0)
        with pytest.raises(ValueError):
            TokenJaccardGrouping(threshold=1.5)

    def test_empty_input(self):
        assert TokenJaccardGrouping().group([]) == []


# --- ExtractiveSummarizer --------------------------------------------


class TestExtractiveSummarizer:
    def test_picks_highest_importance_as_headline(self):
        a = MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="low importance", importance=0.3,
        )
        b = MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="HIGH importance", importance=0.9,
        )
        out = ExtractiveSummarizer().summarize([a, b])
        # Headline should mention the high-importance content.
        assert "HIGH importance" in out.split("\n")[0]

    def test_includes_count(self):
        items = [
            MemoryItem.create(kind=MemoryKind.EPISODIC, content=f"event {i}")
            for i in range(4)
        ]
        out = ExtractiveSummarizer().summarize(items)
        assert "4 items" in out

    def test_truncates_long_bullets(self):
        long_text = "x" * 500
        items = [
            MemoryItem.create(
                kind=MemoryKind.EPISODIC, content="headline", importance=0.9,
            ),
            MemoryItem.create(
                kind=MemoryKind.EPISODIC, content=long_text, importance=0.3,
            ),
        ]
        out = ExtractiveSummarizer(max_bullet_chars=50).summarize(items)
        assert long_text not in out
        assert "..." in out

    def test_empty_returns_empty_string(self):
        assert ExtractiveSummarizer().summarize([]) == ""

    def test_more_than_max_bullets_shows_remaining(self):
        items = [
            MemoryItem.create(kind=MemoryKind.EPISODIC, content=f"event {i}")
            for i in range(10)
        ]
        out = ExtractiveSummarizer(max_bullets=3).summarize(items)
        # 1 headline + 3 bullets + remainder line.
        assert "+ 6 more" in out


# --- MemoryConsolidator ---------------------------------------------


class TestMemoryConsolidator:
    def test_basic_consolidation(self):
        store = _store_with_old_episodic(5, tag="research")
        consolidator = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=3),
        )
        report = consolidator.consolidate()
        assert isinstance(report, ConsolidationReport)
        assert report.n_eligible == 5
        assert report.n_consolidated == 5
        assert report.n_summaries_created == 1
        # 5 originals deleted, 1 summary written → store size = 1.
        assert len(store) == 1

    def test_summary_is_semantic_kind(self):
        store = _store_with_old_episodic(4, tag="x")
        MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
        ).consolidate()
        remaining = list(store._items.values())  # noqa: SLF001
        assert len(remaining) == 1
        assert remaining[0].kind == MemoryKind.SEMANTIC

    def test_summary_inherits_max_importance(self):
        store = MemoryStore()
        store.insert(MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="a", tags=("t",), importance=0.3,
            timestamp=1_000_000.0,
        ))
        store.insert(MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="b", tags=("t",), importance=0.7,
            timestamp=1_000_001.0,
        ))
        store.insert(MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="c", tags=("t",), importance=0.5,
            timestamp=1_000_002.0,
        ))
        MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
        ).consolidate()
        summary = list(store._items.values())[0]  # noqa: SLF001
        assert summary.importance == pytest.approx(0.7)

    def test_summary_includes_consolidated_tag(self):
        store = _store_with_old_episodic(3, tag="research")
        MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
        ).consolidate()
        summary = list(store._items.values())[0]  # noqa: SLF001
        assert "consolidated" in summary.tags
        assert "research" in summary.tags

    def test_summary_metadata_tracks_parents(self):
        store = _store_with_old_episodic(3, tag="x")
        original_ids = list(store._items.keys())  # noqa: SLF001
        MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
        ).consolidate()
        summary = list(store._items.values())[0]  # noqa: SLF001
        assert summary.metadata["n_parents"] == 3
        # All original IDs should be in the metadata.
        recorded = set(summary.metadata["consolidated_from"])
        assert recorded == set(original_ids)

    def test_high_importance_items_preserved(self):
        store = MemoryStore()
        # 3 items: 2 ordinary + 1 pinned (importance >= preserve threshold).
        for i in range(2):
            store.insert(MemoryItem.create(
                kind=MemoryKind.EPISODIC, content=f"a{i}", tags=("t",),
                importance=0.5, timestamp=1_000_000.0,
            ))
        store.insert(MemoryItem.create(
            kind=MemoryKind.EPISODIC, content="pinned", tags=("t",),
            importance=0.95, timestamp=1_000_000.0,
        ))
        consolidator = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(
                min_age_seconds=0.0, min_group_size=2,
                preserve_min_importance=0.9,
            ),
        )
        report = consolidator.consolidate()
        # 2 eligible (the pinned one is skipped).
        assert report.n_eligible == 2
        assert report.n_consolidated == 2
        # After: pinned item + 1 summary = 2 total.
        assert len(store) == 2
        # Pinned content should still exist verbatim.
        contents = {it.content for it in store._items.values()}  # noqa: SLF001
        assert "pinned" in contents

    def test_hot_items_not_consolidated(self):
        store = MemoryStore()
        for i in range(3):
            it = MemoryItem.create(
                kind=MemoryKind.EPISODIC, content=f"e{i}", tags=("t",),
                importance=0.5, timestamp=1_000_000.0,
            )
            # Mark item 0 as frequently accessed.
            if i == 0:
                from dataclasses import replace
                it = replace(it, access_count=20)
            store.insert(it)
        consolidator = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(
                min_age_seconds=0.0, min_group_size=2,
                max_access_count=5,
            ),
        )
        report = consolidator.consolidate()
        # Only items 1 and 2 are eligible.
        assert report.n_eligible == 2

    def test_recent_items_not_consolidated(self):
        # All items just created → accessed_at ≈ now → not eligible.
        store = _store_with_old_episodic(5, tag="t")
        consolidator = MemoryConsolidator(
            store=store,
            # Inject a clock right after the timestamps; min_age=10000 → none old enough.
            policy=ConsolidationPolicy(min_age_seconds=10000.0, min_group_size=2),
        )
        consolidator._clock_fn = lambda: 1_000_005.0  # noqa: SLF001
        report = consolidator.consolidate()
        assert report.n_eligible == 0
        assert report.n_consolidated == 0
        assert len(store) == 5  # untouched

    def test_kind_filter_only_target_kinds(self):
        store = MemoryStore()
        store.insert(MemoryItem.create(
            kind=MemoryKind.SEMANTIC, content="fact-1", tags=("t",),
            timestamp=1_000_000.0,
        ))
        store.insert(MemoryItem.create(
            kind=MemoryKind.SEMANTIC, content="fact-2", tags=("t",),
            timestamp=1_000_000.0,
        ))
        report = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(
                min_age_seconds=0.0, min_group_size=2,
                target_kinds=(MemoryKind.EPISODIC,),  # SEMANTIC excluded
            ),
        ).consolidate()
        assert report.n_eligible == 0
        assert len(store) == 2  # untouched

    def test_namespace_isolation(self):
        store = MemoryStore()
        for i in range(3):
            store.insert(MemoryItem.create(
                kind=MemoryKind.EPISODIC, content=f"ns-a-{i}",
                namespace="alice", tags=("t",), timestamp=1_000_000.0,
            ))
        for i in range(3):
            store.insert(MemoryItem.create(
                kind=MemoryKind.EPISODIC, content=f"ns-b-{i}",
                namespace="bob", tags=("t",), timestamp=1_000_000.0,
            ))
        report = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
        ).consolidate()
        # 2 separate summaries — one per namespace.
        assert report.n_summaries_created == 2
        # 6 originals deleted + 2 summaries → 2 remain.
        assert len(store) == 2
        namespaces = {it.namespace for it in store._items.values()}  # noqa: SLF001
        assert namespaces == {"alice", "bob"}

    def test_namespace_scope_argument(self):
        store = MemoryStore()
        for i in range(3):
            store.insert(MemoryItem.create(
                kind=MemoryKind.EPISODIC, content=f"ns-a-{i}",
                namespace="alice", tags=("t",), timestamp=1_000_000.0,
            ))
        for i in range(3):
            store.insert(MemoryItem.create(
                kind=MemoryKind.EPISODIC, content=f"ns-b-{i}",
                namespace="bob", tags=("t",), timestamp=1_000_000.0,
            ))
        report = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
        ).consolidate(namespace="alice")
        # Only alice's namespace touched.
        assert report.n_summaries_created == 1
        # 3 alice originals deleted + 1 summary + 3 bob untouched = 4.
        assert len(store) == 4

    def test_small_group_skipped(self):
        store = _store_with_old_episodic(2, tag="t")  # only 2 items
        report = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=3),
        ).consolidate()
        assert report.n_eligible == 2
        assert report.n_consolidated == 0
        assert report.n_skipped_groups == 1
        assert len(store) == 2  # untouched

    def test_witness_emitted_when_lattice_wired(self):
        store = _store_with_old_episodic(3, tag="t")
        lattice = WitnessLattice()
        report = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
            lattice=lattice,
            agent_id="orion-consolidator",
        ).consolidate()
        assert len(report.summary_witness_ids) == 1
        # Witness is recorded on the lattice.
        wid = report.summary_witness_ids[0]
        w = lattice.ledger.get(wid)
        assert w is not None
        assert w.issued_by == "orion-consolidator"
        assert w.content["action"] == "consolidate_memory"

    def test_idempotent_when_run_again(self):
        store = _store_with_old_episodic(4, tag="t")
        consolidator = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
        )
        consolidator.consolidate()
        # Second pass: only the SEMANTIC summary remains, which is not in
        # target_kinds → no further consolidation.
        report = consolidator.consolidate()
        assert report.n_eligible == 0
        assert report.n_consolidated == 0


# --- End-to-end with TokenJaccard ------------------------------------


class TestEndToEndTokenJaccard:
    def test_text_similarity_clusters_distinct_topics(self):
        store = MemoryStore()
        # Cluster 1: 3 items about "paris museum tour"
        for i in range(3):
            store.insert(MemoryItem.create(
                kind=MemoryKind.EPISODIC,
                content=f"agent visited paris museum tour location {i}",
                timestamp=1_000_000.0,
            ))
        # Cluster 2: 3 items about "berlin conference notes"
        for i in range(3):
            store.insert(MemoryItem.create(
                kind=MemoryKind.EPISODIC,
                content=f"agent took berlin conference notes session {i}",
                timestamp=1_000_000.0,
            ))
        report = MemoryConsolidator(
            store=store,
            policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
            grouping=TokenJaccardGrouping(threshold=0.3),
        ).consolidate()
        # Expect 2 distinct summaries.
        assert report.n_summaries_created == 2
