"""Tests for KV-Cache-First Context Design (P2-B3)."""
from __future__ import annotations

import pytest

from lyra_harness_core.kv_cache import (
    AppendOnlyContext,
    CacheBreakpoint,
    CacheFriendlySerializer,
    cache_fingerprint,
    estimate_cache_savings,
    stable_system_prefix,
)


# ---------------------------------------------------------------------------
# CacheBreakpoint
# ---------------------------------------------------------------------------


class TestCacheBreakpoint:
    def test_create(self):
        cb = CacheBreakpoint("system_prompt", 42, "stable prefix")
        assert cb.name == "system_prompt"
        assert cb.position == 42
        assert cb.reason == "stable prefix"

    def test_default_reason(self):
        cb = CacheBreakpoint("test", 0)
        assert cb.reason == ""

    def test_repr(self):
        cb = CacheBreakpoint("system_prompt", 100)
        r = repr(cb)
        assert "system_prompt" in r
        assert "100" in r

    def test_slots_no_dict(self):
        cb = CacheBreakpoint("test", 0)
        assert not hasattr(cb, "__dict__")


# ---------------------------------------------------------------------------
# stable_system_prefix
# ---------------------------------------------------------------------------


class TestStableSystemPrefix:
    def test_returns_prompt_unchanged(self):
        prompt = "You are a helpful assistant."
        assert stable_system_prefix(prompt) == prompt

    def test_deterministic(self):
        prompt = "System prompt here."
        assert stable_system_prefix(prompt) == stable_system_prefix(prompt)


# ---------------------------------------------------------------------------
# cache_fingerprint
# ---------------------------------------------------------------------------


class TestCacheFingerprint:
    def test_same_prompt_same_fingerprint(self):
        p = "System: You are helpful."
        assert cache_fingerprint(p) == cache_fingerprint(p)

    def test_different_prompt_different_fingerprint(self):
        assert cache_fingerprint("prompt A") != cache_fingerprint("prompt B")

    def test_length_is_16(self):
        assert len(cache_fingerprint("test")) == 16

    def test_hex_only(self):
        fp = cache_fingerprint("test")
        int(fp, 16)


# ---------------------------------------------------------------------------
# AppendOnlyContext
# ---------------------------------------------------------------------------


class TestAppendOnlyContext:
    @pytest.fixture
    def ctx(self):
        return AppendOnlyContext()

    def test_empty(self, ctx):
        assert ctx.is_empty
        assert ctx.char_count == 0
        assert ctx.segment_count == 0

    def test_append_returns_count(self, ctx):
        n = ctx.append("user", "hello")
        assert n == 5

    def test_append_system_adds_breakpoint(self, ctx):
        ctx.append_system("You are helpful.")
        assert len(ctx.breakpoints) == 1
        bp = ctx.breakpoints[0]
        assert bp.name == "system_prompt"
        assert bp.position == len("You are helpful.")

    def test_append_user_no_breakpoint(self, ctx):
        ctx.append_user("hello")
        assert len(ctx.breakpoints) == 0

    def test_append_assistant_no_breakpoint(self, ctx):
        ctx.append_assistant("hello")
        assert len(ctx.breakpoints) == 0

    def test_text_concatenates(self, ctx):
        ctx.append_system("System")
        ctx.append_user("User")
        ctx.append_assistant("Assistant")
        text = ctx.text()
        assert "System" in text
        assert "User" in text
        assert "Assistant" in text

    def test_text_custom_separator(self, ctx):
        ctx.append("user", "A")
        ctx.append("assistant", "B")
        assert ctx.text("\n") == "A\nB"

    def test_char_count_accumulates(self, ctx):
        ctx.append("user", "abc")
        ctx.append("assistant", "def")
        assert ctx.char_count == 6

    def test_segment_count(self, ctx):
        ctx.append_system("s")
        ctx.append_user("u")
        assert ctx.segment_count == 2

    def test_snapshot_is_copy(self, ctx):
        ctx.append("user", "hello")
        snap = ctx.snapshot()
        assert snap == [("user", "hello")]
        snap.pop()
        assert ctx.segment_count == 1  # original unchanged

    def test_breakpoints_is_copy(self, ctx):
        ctx.append_system("sys")
        bps = ctx.breakpoints
        assert len(bps) == 1
        bps.pop()
        assert len(ctx.breakpoints) == 1  # original unchanged

    def test_cacheable_prefix_system_only(self, ctx):
        ctx.append_system("System prompt")
        ctx.append_user("User message")
        prefix = ctx.cacheable_prefix()
        assert prefix == "System prompt"
        assert "User message" not in prefix

    def test_cacheable_prefix_multiple_system(self, ctx):
        ctx.append_system("Part 1")
        ctx.append_system("Part 2")
        ctx.append_user("User message")
        # Both system parts are cacheable
        prefix = ctx.cacheable_prefix()
        assert "Part 1" in prefix
        assert "Part 2" in prefix

    def test_cacheable_prefix_empty(self, ctx):
        assert ctx.cacheable_prefix() == ""

    def test_cacheable_prefix_length(self, ctx):
        ctx.append_system("ABC")
        assert ctx.cacheable_prefix_length() == 3

    def test_len(self, ctx):
        ctx.append("user", "hello")
        assert len(ctx) == 5

    def test_append_tool_result(self, ctx):
        ctx.append_tool_result("echo", "result")
        assert ctx.segment_count == 1
        assert ctx.text() == "result"

    def test_is_empty_false_after_append(self, ctx):
        ctx.append("user", "hi")
        assert not ctx.is_empty

    def test_complex_workflow(self, ctx):
        ctx.append_system("You are a helpful assistant.")
        ctx.append_user("What is 2+2?")
        ctx.append_assistant("4")
        ctx.append_user("Now multiply by 3.")
        ctx.append_assistant("12")

        assert ctx.segment_count == 5
        assert len(ctx.breakpoints) == 1  # only system
        assert ctx.cacheable_prefix_length() > 0

        text = ctx.text()
        assert "2+2" in text
        assert "12" in text


# ---------------------------------------------------------------------------
# CacheFriendlySerializer
# ---------------------------------------------------------------------------


class TestCacheFriendlySerializer:
    @pytest.fixture
    def ser(self):
        return CacheFriendlySerializer()

    def test_dumps_dict_sorted_keys(self, ser):
        result = ser.dumps({"z": 1, "a": 2})
        assert '"a"' in result
        assert result.index('"a"') < result.index('"z"')  # sorted

    def test_deterministic_output(self, ser):
        obj = {"b": 1, "a": 2, "c": [3, 4]}
        r1 = ser.dumps(obj)
        r2 = ser.dumps(obj)
        assert r1 == r2

    def test_tool_output(self, ser):
        result = ser.tool_output("echo", {"output": "hello"})
        assert "echo" in result
        assert "hello" in result

    def test_tool_output_deterministic(self, ser):
        r1 = ser.tool_output("echo", {"x": 1, "y": 2})
        r2 = ser.tool_output("echo", {"y": 2, "x": 1})
        assert r1 == r2

    def test_message(self, ser):
        msg = ser.message("user", "hello")
        assert "user" in msg
        assert "hello" in msg

    def test_message_deterministic(self, ser):
        m1 = ser.message("user", "hello")
        m2 = ser.message("user", "hello")
        assert m1 == m2

    def test_with_indent(self):
        ser = CacheFriendlySerializer(indent=2)
        result = ser.dumps({"a": 1})
        assert "\n" in result

    def test_no_sort_keys(self):
        ser = CacheFriendlySerializer(sort_keys=False)
        result = ser.dumps({"z": 1, "a": 2})
        # Should preserve insertion order (Python 3.7+)
        assert result.startswith('{"z"')


# ---------------------------------------------------------------------------
# estimate_cache_savings
# ---------------------------------------------------------------------------


class TestEstimateCacheSavings:
    def test_full_cache_hit(self):
        r = estimate_cache_savings(1000000, 1000000)
        assert r["cache_hit_rate"] == 1.0
        assert r["savings"] > 0

    def test_no_cache_hit(self):
        r = estimate_cache_savings(1000000, 0)
        assert r["cache_hit_rate"] == 0.0
        assert r["savings"] == 0.0

    def test_partial_cache(self):
        r = estimate_cache_savings(1000000, 500000)
        assert r["cache_hit_rate"] == 0.5
        assert 0 < r["savings"] < r["uncached_cost"]

    def test_savings_positive_for_cached(self):
        r = estimate_cache_savings(1000, 500)
        assert r["savings"] > 0

    def test_zero_tokens(self):
        r = estimate_cache_savings(0, 0)
        assert r["cache_hit_rate"] == 0.0
        assert r["cached_cost"] == 0.0

    def test_custom_prices(self):
        r = estimate_cache_savings(
            1000000, 500000,
            cached_price_per_mtok=0.50,
            uncached_price_per_mtok=5.00,
        )
        assert r["cached_cost"] > 0
        assert r["uncached_cost"] > r["cached_cost"]
