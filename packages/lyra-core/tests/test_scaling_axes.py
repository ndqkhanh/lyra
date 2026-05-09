"""Tests for L311-7 — four-axis scaling-laws aggregator."""
from __future__ import annotations

import pytest

from lyra_core.meta import (
    ScalingAxes,
    ScalingPosition,
    render_scaling_table,
)


def test_default_axes_score_low():
    sa = ScalingAxes()
    snap = sa.snapshot()
    assert {p.axis for p in snap} == {"pretrain", "ttc", "memory", "tool_use"}
    # Default state is conservative — every axis below 0.6.
    for p in snap:
        assert 0.0 <= p.score <= 0.6, f"{p.axis}: {p.score}"


def test_pretrain_70b_lifts_score():
    sa = ScalingAxes()
    sa.record_pretrain(model="claude-opus-4-7", param_b=70.0, quality=0.85)
    snap = {p.axis: p for p in sa.snapshot()}
    assert snap["pretrain"].score > 0.6
    assert "claude-opus-4-7" in snap["pretrain"].current


def test_pretrain_recommends_larger_when_small():
    sa = ScalingAxes()
    sa.record_pretrain(model="tiny", param_b=1.0)
    p = next(x for x in sa.snapshot() if x.axis == "pretrain")
    assert "larger base model" in p.next_lever


def test_ttc_recommends_verifiers_when_few():
    sa = ScalingAxes()
    sa.record_ttc(max_samples=1, verifier_count=0, avg_pass_rate=0.5)
    p = next(x for x in sa.snapshot() if x.axis == "ttc")
    assert "verifier" in p.next_lever.lower()


def test_ttc_recommends_sampling_when_verifiers_present():
    sa = ScalingAxes()
    sa.record_ttc(max_samples=1, verifier_count=8, avg_pass_rate=0.5)
    p = next(x for x in sa.snapshot() if x.axis == "ttc")
    assert "best-of" in p.next_lever.lower() or "sampling" in p.next_lever.lower()


def test_ttc_high_pass_recommends_other_axis():
    sa = ScalingAxes()
    sa.record_ttc(max_samples=8, verifier_count=8, avg_pass_rate=0.92)
    p = next(x for x in sa.snapshot() if x.axis == "ttc")
    assert p.score > 0.7
    assert "memory" in p.next_lever or "tool_use" in p.next_lever


def test_memory_recommends_3tier_when_flat():
    sa = ScalingAxes()
    sa.record_memory(context_tokens=8192, tier_count=1, retrieval_score=0.7)
    p = next(x for x in sa.snapshot() if x.axis == "memory")
    assert "tier" in p.next_lever.lower() or "MEMTIER" in p.next_lever


def test_memory_high_score_with_3tier_long_context():
    sa = ScalingAxes()
    sa.record_memory(context_tokens=200_000, tier_count=3, retrieval_score=0.9)
    p = next(x for x in sa.snapshot() if x.axis == "memory")
    assert p.score > 0.7


def test_tool_use_recommends_mcp_when_few():
    sa = ScalingAxes()
    sa.record_tool_use(native_count=4, mcp_server_count=1, avg_success_rate=0.85)
    p = next(x for x in sa.snapshot() if x.axis == "tool_use")
    assert "MCP" in p.next_lever


def test_tool_use_recommends_aci_when_unreliable():
    sa = ScalingAxes()
    sa.record_tool_use(native_count=10, mcp_server_count=8, avg_success_rate=0.5)
    p = next(x for x in sa.snapshot() if x.axis == "tool_use")
    assert "ACI" in p.next_lever or "success" in p.next_lever.lower()


def test_invalid_quality_raises():
    sa = ScalingAxes()
    with pytest.raises(ValueError):
        sa.record_pretrain(model="x", param_b=1.0, quality=1.5)


def test_invalid_pass_rate_raises():
    sa = ScalingAxes()
    with pytest.raises(ValueError):
        sa.record_ttc(max_samples=1, verifier_count=1, avg_pass_rate=2.0)


def test_invalid_retrieval_score_raises():
    sa = ScalingAxes()
    with pytest.raises(ValueError):
        sa.record_memory(context_tokens=1, tier_count=1, retrieval_score=-0.1)


def test_invalid_success_rate_raises():
    sa = ScalingAxes()
    with pytest.raises(ValueError):
        sa.record_tool_use(native_count=0, mcp_server_count=0, avg_success_rate=1.5)


def test_best_lever_picks_highest_cost_benefit():
    sa = ScalingAxes()
    sa.record_pretrain(model="big", param_b=400.0, quality=0.95)  # saturated
    sa.record_ttc(max_samples=1, verifier_count=0, avg_pass_rate=0.4)  # low; high-leverage
    sa.record_memory(context_tokens=200_000, tier_count=3, retrieval_score=0.9)
    sa.record_tool_use(native_count=12, mcp_server_count=8, avg_success_rate=0.95)
    best = sa.best_lever()
    assert best.axis == "ttc"


def test_render_scaling_table_returns_string():
    sa = ScalingAxes()
    sa.record_pretrain(model="claude-opus", param_b=200.0)
    out = render_scaling_table(sa.snapshot())
    assert "axis" in out
    assert "pretrain" in out
    assert "ttc" in out
    assert "memory" in out
    assert "tool_use" in out


def test_cost_benefit_for_free_lever():
    p = ScalingPosition(
        axis="ttc",
        score=0.5,
        current="x",
        next_lever="y",
        cost_hint=0.0,
        benefit_hint=0.5,
    )
    assert p.cost_benefit == 0.5
