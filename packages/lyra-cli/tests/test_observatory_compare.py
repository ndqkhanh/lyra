"""Phase M.5 - model-vs-model comparison."""
from __future__ import annotations

import json
import time
from pathlib import Path

from typer.testing import CliRunner

from lyra_cli.__main__ import app
from lyra_cli.observatory.compare import compare


def _seed(tmp_path: Path) -> Path:
    root = tmp_path / ".lyra" / "sessions"
    s = root / "sess1"
    s.mkdir(parents=True)
    now = time.time()
    rows = [
        {"kind": "turn", "ts": now, "user_input": "fix bug",
         "model": "deepseek-v4-pro",
         "tokens_in": 1000, "tokens_out": 500, "cost_delta_usd": 0.003,
         "latency_ms": 5000.0},
        {"kind": "turn", "ts": now + 1, "user_input": "explain",
         "model": "deepseek-v4-flash",
         "tokens_in": 200, "tokens_out": 400, "cost_delta_usd": 0.0005,
         "latency_ms": 1200.0},
    ]
    with (s / "turns.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return root


def test_compare_returns_metrics_for_each_model(tmp_path):
    root = _seed(tmp_path)
    rep = compare(root, ["deepseek-v4-pro", "deepseek-v4-flash"])
    assert {m.model for m in rep.models} == {"deepseek-v4-pro", "deepseek-v4-flash"}


def test_compare_winner_cost_is_cheapest_per_turn(tmp_path):
    root = _seed(tmp_path)
    rep = compare(root, ["deepseek-v4-pro", "deepseek-v4-flash"])
    assert rep.winner_cost == "deepseek-v4-flash"


def test_compare_winner_speed_is_fastest(tmp_path):
    root = _seed(tmp_path)
    rep = compare(root, ["deepseek-v4-pro", "deepseek-v4-flash"])
    assert rep.winner_speed == "deepseek-v4-flash"


def test_compare_unknown_model_returns_zero_row(tmp_path):
    root = _seed(tmp_path)
    rep = compare(root, ["deepseek-v4-pro", "made-up-model"])
    made_up = next(m for m in rep.models if m.model == "made-up-model")
    assert made_up.turns == 0


def test_compare_cli_runs(tmp_path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    res = runner.invoke(app, ["burn", "compare",
                              "deepseek-v4-pro", "deepseek-v4-flash"])
    assert res.exit_code == 0
    assert "deepseek-v4-pro" in res.output
    assert "deepseek-v4-flash" in res.output


def test_compare_cli_json(tmp_path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    res = runner.invoke(app, ["burn", "compare", "--json",
                              "deepseek-v4-pro", "deepseek-v4-flash"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "models" in data
    assert any(m["model"] == "deepseek-v4-pro" for m in data["models"])


def test_compare_requires_at_least_two_models():
    runner = CliRunner()
    res = runner.invoke(app, ["burn", "compare", "deepseek-v4-pro"])
    assert res.exit_code != 0


def test_compare_winner_one_shot_picks_highest(tmp_path):
    root = _seed(tmp_path)
    rep = compare(root, ["deepseek-v4-pro", "deepseek-v4-flash"])
    assert rep.winner_one_shot is not None
