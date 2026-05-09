"""Contract tests for the prompt-cache coordinator (Phase 5g — PolyKV-equivalent).

The coordinator is the production hosted-API absorption of PolyKV
(arXiv:2604.24971). These tests pin the contract so a future refactor
can't silently change anchor identity, miss-classify hits/writes, or
break sibling-subagent sharing.
"""
from __future__ import annotations

from lyra_core.providers.prompt_cache import (
    DEFAULT_CACHE_FLOOR_CHARS,
    AnthropicAdapter,
    CacheStatus,
    DeepSeekAdapter,
    GeminiAdapter,
    NoopAdapter,
    OpenAIAdapter,
    PromptCacheCoordinator,
    default_coordinator,
    get_adapter,
    register_adapter,
    reset_default_coordinator,
)

# ---------------------------------------------------------------------------
# Coordinator core: write/hit/skip semantics
# ---------------------------------------------------------------------------


def test_short_prefix_below_floor_returns_skip() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=4_000)
    status, anchor = coord.coordinate(provider="anthropic", shared_text="hi")
    assert status is CacheStatus.SKIP
    assert anchor is None


def test_first_call_for_long_prefix_returns_write() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    status, anchor = coord.coordinate(provider="anthropic", shared_text="x" * 100)
    assert status is CacheStatus.WRITE
    assert anchor is not None
    assert anchor.provider == "anthropic"
    assert anchor.chars == 100


def test_second_call_with_same_prefix_returns_hit() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    text = "x" * 100
    coord.coordinate(provider="anthropic", shared_text=text)
    status, anchor = coord.coordinate(provider="anthropic", shared_text=text)
    assert status is CacheStatus.HIT
    assert anchor is not None


def test_anchor_identity_preserved_across_hits() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    text = "x" * 100
    _, anchor_write = coord.coordinate(provider="anthropic", shared_text=text)
    _, anchor_hit_a = coord.coordinate(provider="anthropic", shared_text=text)
    _, anchor_hit_b = coord.coordinate(provider="anthropic", shared_text=text)
    assert anchor_write is anchor_hit_a is anchor_hit_b


def test_different_providers_get_different_anchors() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    text = "x" * 100
    _, a = coord.coordinate(provider="anthropic", shared_text=text)
    _, b = coord.coordinate(provider="openai", shared_text=text)
    assert a is not None and b is not None
    assert a is not b
    assert a.digest == b.digest


def test_different_text_same_provider_get_different_anchors() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    _, a = coord.coordinate(provider="anthropic", shared_text="x" * 100)
    _, b = coord.coordinate(provider="anthropic", shared_text="y" * 100)
    assert a is not None and b is not None
    assert a.digest != b.digest


def test_unknown_provider_falls_back_to_noop_adapter() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    status, anchor = coord.coordinate(provider="weirdcorp", shared_text="x" * 100)
    assert status is CacheStatus.WRITE
    assert anchor is not None
    assert anchor.provider_directive is None  # noop adapter


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


def test_expired_anchor_triggers_fresh_write() -> None:
    fake_now = [0.0]

    def clock() -> float:
        return fake_now[0]

    coord = PromptCacheCoordinator(
        cache_floor_chars=10,
        ttl_seconds=60,
        clock=clock,
    )
    text = "x" * 100
    status1, anchor1 = coord.coordinate(provider="anthropic", shared_text=text)
    fake_now[0] = 70  # past TTL
    status2, anchor2 = coord.coordinate(provider="anthropic", shared_text=text)
    assert status1 is CacheStatus.WRITE
    assert status2 is CacheStatus.WRITE
    assert anchor1 is not anchor2


def test_active_anchors_excludes_expired() -> None:
    fake_now = [0.0]

    def clock() -> float:
        return fake_now[0]

    coord = PromptCacheCoordinator(
        cache_floor_chars=10, ttl_seconds=60, clock=clock
    )
    coord.coordinate(provider="anthropic", shared_text="x" * 100)
    assert coord.active_anchors() == 1
    fake_now[0] = 70
    assert coord.active_anchors() == 0


# ---------------------------------------------------------------------------
# Metrics + reset
# ---------------------------------------------------------------------------


def test_metrics_accumulate_correctly() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    text = "x" * 100
    coord.coordinate(provider="anthropic", shared_text=text)  # write
    coord.coordinate(provider="anthropic", shared_text=text)  # hit
    coord.coordinate(provider="anthropic", shared_text=text)  # hit
    coord.coordinate(provider="anthropic", shared_text="hi")  # skip (below floor)
    snap = coord.snapshot()
    assert snap.writes == 1
    assert snap.hits == 2
    assert snap.skips == 1
    assert snap.chars_cached == 100
    assert snap.chars_skipped == 2


def test_reset_clears_anchors_and_metrics() -> None:
    coord = PromptCacheCoordinator(cache_floor_chars=10)
    coord.coordinate(provider="anthropic", shared_text="x" * 100)
    assert coord.active_anchors() == 1
    coord.reset()
    assert coord.active_anchors() == 0
    snap = coord.snapshot()
    assert snap.writes == 0 and snap.hits == 0


# ---------------------------------------------------------------------------
# Adapter contracts (Anthropic, OpenAI, DeepSeek, Gemini, Noop)
# ---------------------------------------------------------------------------


def test_anthropic_adapter_emits_cache_control_block() -> None:
    adapter = AnthropicAdapter()
    directive = adapter.make_directive(
        digest="deadbeef" * 8, chars=5_000, ttl_seconds=300, is_write=True
    )
    assert directive is not None
    assert directive["cache_control"] == {"type": "ephemeral"}
    assert directive["_lyra_cache_role"] == "write"


def test_anthropic_adapter_role_flips_on_hit() -> None:
    adapter = AnthropicAdapter()
    directive = adapter.make_directive(
        digest="d" * 64, chars=5_000, ttl_seconds=300, is_write=False
    )
    assert directive is not None and directive["_lyra_cache_role"] == "hit"


def test_openai_adapter_returns_none_directive() -> None:
    """OpenAI auto-caches by prefix — no payload knob, only telemetry."""
    adapter = OpenAIAdapter()
    assert (
        adapter.make_directive(digest="d" * 64, chars=5_000, ttl_seconds=300, is_write=True)
        is None
    )


def test_deepseek_adapter_returns_none_directive() -> None:
    """DeepSeek context cache is automatic on identical prefixes."""
    adapter = DeepSeekAdapter()
    assert (
        adapter.make_directive(digest="d" * 64, chars=5_000, ttl_seconds=300, is_write=False)
        is None
    )


def test_gemini_adapter_emits_cached_content_reference() -> None:
    adapter = GeminiAdapter()
    directive = adapter.make_directive(
        digest="abcdef" * 8, chars=5_000, ttl_seconds=600, is_write=True
    )
    assert directive is not None
    assert directive["cached_content"] == "lyra-cache-abcdefabcdefabcd"
    assert directive["ttl"] == "600s"
    assert directive["_lyra_cache_role"] == "write"


def test_noop_adapter_returns_none_directive() -> None:
    assert (
        NoopAdapter().make_directive(
            digest="d" * 64, chars=1, ttl_seconds=1, is_write=True
        )
        is None
    )


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------


def test_get_adapter_returns_builtin_for_known_provider() -> None:
    assert isinstance(get_adapter("anthropic"), AnthropicAdapter)
    assert isinstance(get_adapter("openai"), OpenAIAdapter)
    assert isinstance(get_adapter("deepseek"), DeepSeekAdapter)
    assert isinstance(get_adapter("gemini"), GeminiAdapter)


def test_get_adapter_returns_noop_for_unknown_provider() -> None:
    a = get_adapter("nonexistent-provider")
    assert isinstance(a, NoopAdapter)
    assert a.provider_name == "nonexistent-provider"


def test_register_adapter_overrides_builtin() -> None:
    class _Custom:
        @property
        def provider_name(self) -> str:
            return "anthropic"

        def make_directive(self, **_: object) -> dict[str, str]:
            return {"custom": "yes"}

    custom = _Custom()
    register_adapter(custom)
    try:
        adapter = get_adapter("anthropic")
        assert adapter is custom
    finally:
        register_adapter(AnthropicAdapter())  # restore


# ---------------------------------------------------------------------------
# Process-global default
# ---------------------------------------------------------------------------


def test_default_coordinator_is_singleton() -> None:
    reset_default_coordinator()
    a = default_coordinator()
    b = default_coordinator()
    assert a is b
    reset_default_coordinator()


def test_reset_default_coordinator_drops_anchors() -> None:
    reset_default_coordinator()
    coord = default_coordinator()
    coord.coordinate(provider="anthropic", shared_text="x" * 5_000)
    assert coord.active_anchors() == 1
    reset_default_coordinator()
    fresh = default_coordinator()
    assert fresh is not coord
    assert fresh.active_anchors() == 0
    reset_default_coordinator()


# ---------------------------------------------------------------------------
# Defaults sanity
# ---------------------------------------------------------------------------


def test_default_floor_is_4k_chars() -> None:
    assert DEFAULT_CACHE_FLOOR_CHARS == 4_000


def test_floor_validation_uses_char_count_not_token_count() -> None:
    """The coordinator counts characters, not tokens; document the contract."""
    coord = PromptCacheCoordinator(cache_floor_chars=100)
    status, _ = coord.coordinate(provider="anthropic", shared_text="x" * 99)
    assert status is CacheStatus.SKIP
    status, _ = coord.coordinate(provider="anthropic", shared_text="x" * 100)
    assert status is CacheStatus.WRITE


# ---------------------------------------------------------------------------
# Concurrency: no torn anchors under threaded coordination
# ---------------------------------------------------------------------------


def test_concurrent_coordination_produces_one_write_and_n_minus_one_hits() -> None:
    """Multiple threads coordinating the same digest race only on the write."""
    import threading

    coord = PromptCacheCoordinator(cache_floor_chars=10)
    text = "x" * 5_000
    statuses: list[CacheStatus] = []
    lock = threading.Lock()

    def worker() -> None:
        s, _ = coord.coordinate(provider="anthropic", shared_text=text)
        with lock:
            statuses.append(s)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(statuses) == 20
    assert statuses.count(CacheStatus.WRITE) == 1
    assert statuses.count(CacheStatus.HIT) == 19
    snap = coord.snapshot()
    assert snap.writes == 1 and snap.hits == 19
