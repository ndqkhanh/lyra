"""Unit tests for CostAccumulator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.transparency.event_store import EventStore, make_event
from lyra_core.transparency.cost_accumulator import CostAccumulator, _cost_usd


@pytest.fixture
def store(tmp_path: Path) -> EventStore:
    return EventStore(tmp_path / "test.db")


@pytest.mark.unit
def test_empty_session_zero_cost(store: EventStore) -> None:
    acc = CostAccumulator(store)
    cost = acc.get("nonexistent")
    assert cost.cost_usd == 0.0
    assert cost.tokens_in == 0


@pytest.mark.unit
def test_accumulates_turn_tokens(store: EventStore) -> None:
    payload = {"usage": {"input_tokens": 1000, "output_tokens": 500}}
    ev = make_event("PostToolUse", session_id="s1", payload=payload)
    store.append(ev)
    acc = CostAccumulator(store)
    cost = acc.get("s1")
    assert cost.tokens_in == 1000
    assert cost.tokens_out == 500
    assert cost.cost_usd > 0


@pytest.mark.unit
def test_cost_usd_sonnet_pricing() -> None:
    cost = _cost_usd(1_000_000, 0, 0, 0, "claude-sonnet-4-6")
    assert abs(cost - 3.0) < 0.001


@pytest.mark.unit
def test_cost_usd_haiku_cheaper_than_sonnet() -> None:
    cost_haiku = _cost_usd(100_000, 50_000, 0, 0, "claude-haiku-4-5")
    cost_sonnet = _cost_usd(100_000, 50_000, 0, 0, "claude-sonnet-4-6")
    assert cost_haiku < cost_sonnet


@pytest.mark.unit
def test_get_total_sums_sessions(store: EventStore) -> None:
    for sid in ("s1", "s2"):
        payload = {"usage": {"input_tokens": 500, "output_tokens": 200}}
        store.append(make_event("PostToolUse", session_id=sid, payload=payload))
    acc = CostAccumulator(store)
    total = acc.get_total()
    assert total.tokens_in == 1000
    assert total.tokens_out == 400
