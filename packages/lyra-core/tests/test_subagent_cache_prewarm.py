"""Integration tests for prompt-cache prewarm + sibling subagent fan-out.

Pins the contract that pre-warming the coordinator on the parent
thread produces exactly one cache *write* (paid by the orchestrator
up front) and ``N-1`` cache *hits* across the sibling subagent
workers — the morally-equivalent shape of PolyKV's "shared pool, one
write, many reads" guarantee.
"""
from __future__ import annotations

import threading

import pytest

from lyra_core.providers.prompt_cache import (
    CacheStatus,
    PromptCacheCoordinator,
)
from lyra_core.subagent.cache_prewarm import (
    SharedPromptDescriptor,
    hit_for_sibling,
    prewarm_for_specs,
)

# ---------------------------------------------------------------------------
# Prewarm contract
# ---------------------------------------------------------------------------


def test_prewarm_returns_write_on_fresh_descriptor() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    desc = SharedPromptDescriptor(
        shared_text="some shared plan " * 200, provider="anthropic"
    )
    result = prewarm_for_specs(desc, sibling_count=5, coordinator=coord)
    assert result.status is CacheStatus.WRITE
    assert result.anchor is not None
    assert result.is_active
    assert result.sibling_count == 5


def test_prewarm_short_prefix_returns_skip() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=4_000)
    desc = SharedPromptDescriptor(shared_text="hi", provider="anthropic")
    result = prewarm_for_specs(desc, sibling_count=3, coordinator=coord)
    assert result.status is CacheStatus.SKIP
    assert result.anchor is None
    assert not result.is_active


def test_prewarm_idempotent_within_ttl() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    desc = SharedPromptDescriptor(
        shared_text="shared text " * 200, provider="anthropic"
    )
    first = prewarm_for_specs(desc, sibling_count=3, coordinator=coord)
    second = prewarm_for_specs(desc, sibling_count=3, coordinator=coord)
    assert first.status is CacheStatus.WRITE
    assert second.status is CacheStatus.HIT
    assert first.anchor is second.anchor


def test_prewarm_rejects_non_positive_sibling_count() -> None:
    desc = SharedPromptDescriptor(shared_text="x" * 5_000, provider="anthropic")
    with pytest.raises(ValueError):
        prewarm_for_specs(desc, sibling_count=0)
    with pytest.raises(ValueError):
        prewarm_for_specs(desc, sibling_count=-1)


# ---------------------------------------------------------------------------
# Sibling lookup
# ---------------------------------------------------------------------------


def test_hit_for_sibling_returns_anchor_after_prewarm() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    desc = SharedPromptDescriptor(
        shared_text="shared " * 1_000, provider="anthropic"
    )
    prewarm_for_specs(desc, sibling_count=3, coordinator=coord)
    status, anchor = hit_for_sibling(desc, coordinator=coord)
    assert status is CacheStatus.HIT
    assert anchor is not None
    assert anchor.provider_directive is not None
    assert anchor.provider_directive["cache_control"] == {"type": "ephemeral"}


def test_hit_without_prewarm_creates_anchor_lazily() -> None:
    """Workers can still benefit even if the parent forgot to pre-warm:
    the first worker becomes the writer; subsequent workers hit."""
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    desc = SharedPromptDescriptor(
        shared_text="shared " * 1_000, provider="anthropic"
    )
    s1, _ = hit_for_sibling(desc, coordinator=coord)
    s2, _ = hit_for_sibling(desc, coordinator=coord)
    s3, _ = hit_for_sibling(desc, coordinator=coord)
    assert s1 is CacheStatus.WRITE
    assert s2 is CacheStatus.HIT
    assert s3 is CacheStatus.HIT


# ---------------------------------------------------------------------------
# Integrated fan-out: parent prewarms, N workers all hit
# ---------------------------------------------------------------------------


def test_prewarm_then_n_workers_yields_one_write_and_n_hits() -> None:
    """The PolyKV-equivalent guarantee for hosted APIs: O(1) writes,
    O(N) hits — cost in the shared prefix is constant in N."""
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    desc = SharedPromptDescriptor(
        shared_text="shared plan body " * 500, provider="anthropic"
    )

    parent_result = prewarm_for_specs(desc, sibling_count=10, coordinator=coord)
    assert parent_result.status is CacheStatus.WRITE

    worker_statuses: list[CacheStatus] = []
    lock = threading.Lock()

    def worker() -> None:
        s, _ = hit_for_sibling(desc, coordinator=coord)
        with lock:
            worker_statuses.append(s)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(worker_statuses) == 10
    assert all(s is CacheStatus.HIT for s in worker_statuses)
    snap = coord.snapshot()
    assert snap.writes == 1
    assert snap.hits == 10


def test_two_descriptors_for_different_providers_dont_collide() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    text = "shared body " * 500
    desc_a = SharedPromptDescriptor(shared_text=text, provider="anthropic")
    desc_b = SharedPromptDescriptor(shared_text=text, provider="openai")

    r_a = prewarm_for_specs(desc_a, sibling_count=3, coordinator=coord)
    r_b = prewarm_for_specs(desc_b, sibling_count=3, coordinator=coord)
    assert r_a.status is CacheStatus.WRITE
    assert r_b.status is CacheStatus.WRITE
    assert r_a.anchor is not r_b.anchor
    assert coord.active_anchors() == 2


def test_descriptor_scope_ids_are_stored_but_not_enforced() -> None:
    """Scope ids are documentation today — assert the contract."""
    desc = SharedPromptDescriptor(
        shared_text="x" * 5_000,
        provider="anthropic",
        scope_ids=("sub-a", "sub-b", "sub-c"),
    )
    assert desc.scope_ids == ("sub-a", "sub-b", "sub-c")
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    result = prewarm_for_specs(desc, sibling_count=3, coordinator=coord)
    assert result.descriptor.scope_ids == ("sub-a", "sub-b", "sub-c")


# ---------------------------------------------------------------------------
# Telemetry: chars saved should grow with sibling count
# ---------------------------------------------------------------------------


def test_chars_cached_recorded_only_once_per_anchor() -> None:
    """The coordinator counts cached chars on write, not on hit — so the
    metric measures *unique* shared prefixes, not duplicated reads."""
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    desc = SharedPromptDescriptor(
        shared_text="x" * 5_000, provider="anthropic"
    )
    prewarm_for_specs(desc, sibling_count=15, coordinator=coord)
    for _ in range(15):
        hit_for_sibling(desc, coordinator=coord)
    snap = coord.snapshot()
    assert snap.chars_cached == 5_000
    assert snap.writes == 1
    assert snap.hits == 15
