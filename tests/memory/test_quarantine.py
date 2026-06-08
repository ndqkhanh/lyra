"""Tests for the Quarantine module.

Covers QuarantineItem, QuarantinePool, and lifecycle management
of quarantined artifacts.
"""
from __future__ import annotations

import time

import pytest

from lyra.memory.quarantine import (
    DEFAULT_REVIEW_DAYS,
    QUARANTINE_STRIKE_LIMIT,
    RECLAIM_INITIAL_TRUST,
    QuarantineItem,
    QuarantinePool,
)


# ===================================================================
# QuarantineItem tests
# ===================================================================


class TestQuarantineItem:
    """Tests for the QuarantineItem dataclass."""

    def test_creation(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="bad memory",
            reason="low trust score",
        )
        assert item.item_id == "q1"
        assert item.artifact == "bad memory"
        assert item.reason == "low trust score"
        assert item.strikes == 0
        assert item.quarantined_at > 0
        assert item.review_after > item.quarantined_at

    def test_creation_with_explicit_strikes(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            strikes=2,
        )
        assert item.strikes == 2

    def test_creation_with_custom_timestamps(self) -> None:
        now = 1000.0
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            quarantined_at=now,
            review_after=now + 86400,
        )
        assert item.quarantined_at == now
        assert item.review_after == now + 86400

    def test_is_reviewable(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            quarantined_at=0,
            review_after=0,  # Will default to now + 7 days
        )
        # Initially not reviewable (review is 7 days in future)
        assert item.is_reviewable is False

    def test_is_reviewable_past_date(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            quarantined_at=0,
            review_after=time.time() - 1,  # 1 second in the past
        )
        assert item.is_reviewable is True

    def test_is_permanent(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            strikes=QUARANTINE_STRIKE_LIMIT,
        )
        assert item.is_permanent is True

    def test_is_permanent_below_limit(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            strikes=QUARANTINE_STRIKE_LIMIT - 1,
        )
        assert item.is_permanent is False

    def test_with_strike(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            strikes=1,
            quarantined_at=100.0,
            review_after=200.0,
        )
        new_item = item.with_strike()
        assert new_item.strikes == 2
        assert new_item.item_id == "q1"
        assert new_item.artifact == "test"
        assert new_item.reason == "test"
        # Timestamps are reset to current time
        assert new_item.quarantined_at >= item.quarantined_at

    def test_with_strike_resets_review(self) -> None:
        item = QuarantineItem(
            item_id="q1",
            artifact="test",
            reason="test",
            review_after=0,
            quarantined_at=0,
        )
        new_item = item.with_strike()
        assert new_item.review_after > new_item.quarantined_at

    def test_metadata_default(self) -> None:
        item = QuarantineItem(
            item_id="q1", artifact="test", reason="test",
        )
        assert item.metadata == {}

    def test_metadata_custom(self) -> None:
        item = QuarantineItem(
            item_id="q1", artifact="test", reason="test",
            metadata={"source": "agent-1"},
        )
        assert item.metadata["source"] == "agent-1"


# ===================================================================
# QuarantinePool tests
# ===================================================================


class TestQuarantinePool:
    """Tests for the QuarantinePool."""

    def test_creation_empty(self) -> None:
        pool = QuarantinePool()
        assert pool.items == {}

    def test_add_item(self) -> None:
        pool = QuarantinePool()
        item = pool.add(
            artifact="bad memory content",
            reason="low trust score",
            review_after_days=14,
        )
        assert item.item_id in pool.items
        assert item.artifact == "bad memory content"
        assert item.reason == "low trust score"
        assert item.strikes == 0
        assert item.review_after > item.quarantined_at

    def test_add_with_strikes(self) -> None:
        pool = QuarantinePool()
        item = pool.add(
            artifact="test",
            reason="recurring issue",
            strikes=2,
        )
        assert item.strikes == 2

    def test_add_custom_review_days(self) -> None:
        pool = QuarantinePool()
        now = time.time()
        item = pool.add(artifact="test", reason="test", review_after_days=1)
        assert item.review_after <= now + 86401

    def test_review_returns_reviewable_items(self) -> None:
        pool = QuarantinePool()
        # Add an item with a past review date
        past_time = time.time() - 10
        past_item = QuarantineItem(
            item_id="past",
            artifact="old",
            reason="old",
            quarantined_at=past_time,
            review_after=past_time - 1,
        )
        pool.items["past"] = past_item

        reviewable = pool.review()
        assert len(reviewable) == 1
        assert reviewable[0].item_id == "past"

    def test_review_returns_only_past_date(self) -> None:
        pool = QuarantinePool()
        # Add items with future review dates
        future_time = time.time() + 86400 * 30
        item = QuarantineItem(
            item_id="future",
            artifact="new",
            reason="new",
            quarantined_at=time.time(),
            review_after=future_time,
        )
        pool.items["future"] = item

        reviewable = pool.review()
        assert len(reviewable) == 0

    def test_reclaim(self) -> None:
        pool = QuarantinePool()
        pool.add(artifact="reclaimable memory", reason="test")
        item_id = list(pool.items.keys())[0]

        artifact, trust = pool.reclaim(item_id)
        assert artifact == "reclaimable memory"
        assert trust == RECLAIM_INITIAL_TRUST
        assert item_id not in pool.items

    def test_reclaim_nonexistent_raises(self) -> None:
        pool = QuarantinePool()
        with pytest.raises(KeyError, match="not found"):
            pool.reclaim("nonexistent")

    def test_reclaim_permanent_item_raises(self) -> None:
        pool = QuarantinePool()
        item = pool.add(artifact="permanent bad", reason="too many strikes")
        # Manually make it permanent
        item_id = list(pool.items.keys())[0]
        pool.items[item_id].strikes = QUARANTINE_STRIKE_LIMIT

        with pytest.raises(ValueError, match="cannot be reclaimed"):
            pool.reclaim(item_id)

    def test_purge(self) -> None:
        pool = QuarantinePool()
        pool.add(artifact="to delete", reason="test")
        item_id = list(pool.items.keys())[0]

        pool.purge(item_id)
        assert item_id not in pool.items

    def test_purge_nonexistent_raises(self) -> None:
        pool = QuarantinePool()
        with pytest.raises(KeyError, match="not found"):
            pool.purge("nonexistent")

    def test_get_statistics_empty(self) -> None:
        pool = QuarantinePool()
        stats = pool.get_statistics()
        assert stats["total_items"] == 0
        assert stats["reviewable_items"] == 0
        assert stats["permanent_items"] == 0

    def test_get_statistics_with_items(self) -> None:
        pool = QuarantinePool()
        pool.add(artifact="item 1", reason="test")

        # Add a permanent item
        past = time.time() - 10
        perm_item = QuarantineItem(
            item_id="perm",
            artifact="permanent",
            reason="bad",
            quarantined_at=past,
            review_after=past - 1,
            strikes=QUARANTINE_STRIKE_LIMIT,
        )
        pool.items["perm"] = perm_item

        stats = pool.get_statistics()
        assert stats["total_items"] == 2
        assert stats["reviewable_items"] >= 1
        assert stats["permanent_items"] == 1
        assert "strike_counts" in stats

    def test_get_statistics_strike_distribution(self) -> None:
        pool = QuarantinePool()
        pool.add(artifact="a", reason="test", strikes=0)
        pool.add(artifact="b", reason="test", strikes=1)
        pool.add(artifact="c", reason="test", strikes=2)
        stats = pool.get_statistics()
        assert "strike_counts" in stats
        assert stats["strike_counts"]["0"] >= 1
        assert stats["strike_counts"]["1"] >= 1
        assert stats["strike_counts"]["2"] >= 1


# ===================================================================
# Constants tests
# ===================================================================


class TestConstants:
    """Tests for module constants."""

    def test_default_review_days(self) -> None:
        assert DEFAULT_REVIEW_DAYS == 7

    def test_strike_limit(self) -> None:
        assert QUARANTINE_STRIKE_LIMIT == 3

    def test_reclaim_initial_trust(self) -> None:
        assert RECLAIM_INITIAL_TRUST == 0.3
