"""Phase M.3 - period rollups across sessions."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from lyra_cli.observatory.aggregator import aggregate


def _write_session(root: Path, sid: str, lines: list[dict]) -> None:
    d = root / sid
    d.mkdir(parents=True, exist_ok=True)
    with (d / "turns.jsonl").open("w") as fh:
        for ln in lines:
            fh.write(json.dumps(ln) + "\n")


@pytest.fixture
def two_sessions(tmp_path):
    root = tmp_path / "sessions"
    _write_session(root, "20260427-100000-aaa", [
        {"kind": "turn", "turn": 1, "ts": 1.0, "user_input": "fix bug",
         "mode": "agent", "model": "deepseek-v4-pro",
         "tokens_in": 1000, "tokens_out": 500, "cost_delta_usd": 0.003},
        {"kind": "turn", "turn": 2, "ts": 2.0, "user_input": "still broken",
         "mode": "agent", "model": "deepseek-v4-pro",
         "tokens_in": 1100, "tokens_out": 550, "cost_delta_usd": 0.0033},
    ])
    _write_session(root, "20260427-110000-bbb", [
        {"kind": "turn", "turn": 1, "ts": 100.0, "user_input": "explain",
         "mode": "ask", "model": "deepseek-v4-flash",
         "tokens_in": 200, "tokens_out": 400, "cost_delta_usd": 0.00046},
    ])
    return root


def test_aggregate_total_cost_sums_cost_delta(two_sessions):
    rep = aggregate(two_sessions)
    assert rep.total_cost_usd == Decimal("0.0067600")


def test_aggregate_total_turns(two_sessions):
    assert aggregate(two_sessions).total_turns == 3


def test_aggregate_by_model_groups(two_sessions):
    rep = aggregate(two_sessions)
    models = {m.model: m for m in rep.by_model}
    assert "deepseek-v4-pro" in models
    assert models["deepseek-v4-pro"].turns == 2
    assert models["deepseek-v4-flash"].turns == 1


def test_aggregate_by_category(two_sessions):
    rep = aggregate(two_sessions)
    cats = {c.category for c in rep.by_category}
    assert "debugging" in cats
    assert "explore" in cats


def test_aggregate_by_session_two_rows(two_sessions):
    rep = aggregate(two_sessions)
    assert len(rep.by_session) == 2


def test_aggregate_session_primary_model(two_sessions):
    rep = aggregate(two_sessions)
    rows = {r.session_id: r for r in rep.by_session}
    assert rows["20260427-100000-aaa"].primary_model == "deepseek-v4-pro"


def test_aggregate_since_filters_old_turns(two_sessions):
    rep = aggregate(two_sessions, since=50.0)
    assert rep.total_turns == 1


def test_aggregate_until_filters_new_turns(two_sessions):
    rep = aggregate(two_sessions, until=10.0)
    assert rep.total_turns == 2


def test_aggregate_one_shot_rate(two_sessions):
    """Two debugging turns: first is 1-shot, second is retry -> 0.5."""
    rep = aggregate(two_sessions)
    assert rep.one_shot_rate == pytest.approx(0.5)


def test_aggregate_handles_partial_rows(tmp_path):
    """Old transcripts (pre-Phase-L) lack model/tokens - must not crash."""
    root = tmp_path / "sessions"
    _write_session(root, "old-session-aaa", [
        {"kind": "turn", "turn": 1, "user_input": "hi"},
    ])
    rep = aggregate(root)
    assert rep.total_turns == 1
    assert rep.total_cost_usd == Decimal("0")


def test_aggregate_empty_root_returns_empty_report(tmp_path):
    rep = aggregate(tmp_path / "sessions")
    assert rep.total_turns == 0
    assert rep.total_cost_usd == Decimal("0")


def test_aggregate_skips_chat_kind_when_summing_turns(two_sessions):
    """Chat rows mirror their turn - must not double-count."""
    sid = "20260427-100000-aaa"
    line = {"kind": "chat", "turn": 1, "user": "x", "assistant": "y",
            "model": "deepseek-v4-pro", "tokens_in": 1000, "tokens_out": 500,
            "cost_delta_usd": 0.003}
    with (two_sessions / sid / "turns.jsonl").open("a") as fh:
        fh.write(json.dumps(line) + "\n")
    rep = aggregate(two_sessions)
    assert rep.total_turns == 3
