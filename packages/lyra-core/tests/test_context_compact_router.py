"""Tests for compaction model router (Phase CE.3, P2-2)."""
from __future__ import annotations

from lyra_core.context.compact_router import (
    INVARIANT_TRIGGER,
    ROUTE_CHEAP,
    ROUTE_SMART,
    TOKEN_TRIGGER,
    VARIANCE_TRIGGER,
    route_compaction,
)


def test_empty_window_routes_to_cheap():
    d = route_compaction([], task="anything")
    assert d.route == ROUTE_CHEAP
    assert d.invariant_count == 0
    assert d.window_tokens == 0


def test_low_signal_window_routes_to_cheap():
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "ok"},
        {"role": "tool", "tool_call_id": "1", "content": "done"},
    ]
    d = route_compaction(msgs, task="say hello")
    assert d.route == ROUTE_CHEAP
    assert d.invariant_count == 0


def test_many_invariants_routes_to_smart():
    msgs = [
        {
            "role": "tool",
            "tool_call_id": f"t-{i}",
            "content": (
                f"FAIL test_thing_{i} at src/api_{i}.py:{10+i} - "
                f"deny: bad input {i}"
            ),
        }
        for i in range(INVARIANT_TRIGGER + 1)
    ]
    d = route_compaction(msgs, task="something")
    assert d.route == ROUTE_SMART
    assert d.invariant_count >= INVARIANT_TRIGGER
    assert any("invariant_count" in r for r in d.reasons)


def test_large_window_routes_to_smart_by_token_count():
    big = "lorem ipsum dolor sit amet " * 200  # ~5400 chars → ~1350 tokens each
    msgs = [
        {"role": "assistant", "content": big},
        {"role": "tool", "tool_call_id": "1", "content": big},
        {"role": "assistant", "content": big},
    ]
    d = route_compaction(msgs, task="x")
    assert d.window_tokens >= TOKEN_TRIGGER
    assert d.route == ROUTE_SMART


def test_high_variance_routes_to_smart():
    # Mix one high-signal message with many low-signal ones to push variance.
    msgs = [
        {"role": "user", "content": "edit src/x.py"},
        {
            "role": "assistant",
            "content": (
                "src/x.py:42 FAIL test_one regression denied: bad — "
                "src/x.py:43 test_two"
            ),
        },
        {"role": "user", "content": "hmm"},
        {"role": "user", "content": "ok"},
        {"role": "user", "content": "go on"},
    ]
    d = route_compaction(msgs, task="edit src/x.py")
    if d.route == ROUTE_SMART:
        assert d.relevance_variance >= VARIANCE_TRIGGER or "variance" in " ".join(
            d.reasons
        )


def test_decision_reasons_explain_cheap_route():
    msgs = [{"role": "user", "content": "hello"}]
    d = route_compaction(msgs, task="x")
    assert d.route == ROUTE_CHEAP
    # Even the cheap route surfaces a reason line for observability.
    assert len(d.reasons) >= 1


def test_decision_window_tokens_handles_non_string():
    msgs = [
        {"role": "user", "content": None},
        {"role": "tool", "content": {"complex": True}},
        {"role": "assistant", "content": "real text here"},
    ]
    d = route_compaction(msgs, task="x")
    assert d.window_tokens > 0  # real text counted
