"""Phase M.6 - optimization detector."""
from __future__ import annotations

import json
import time
from pathlib import Path

from typer.testing import CliRunner

from lyra_cli.__main__ import app
from lyra_cli.observatory.optimize import optimize


def _seed(tmp_path: Path, rows: list[dict]) -> Path:
    root = tmp_path / ".lyra" / "sessions" / "s1"
    root.mkdir(parents=True)
    with (root / "turns.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return tmp_path / ".lyra" / "sessions"


def test_R_RETRY_STREAK_fires_on_3_consecutive_retries(tmp_path):
    rows = [
        {"kind": "turn", "ts": float(i), "user_input": "fix bug",
         "mode": "agent", "model": "deepseek-v4-pro",
         "tokens_in": 100, "tokens_out": 50}
        for i in range(3)
    ]
    findings = optimize(_seed(tmp_path, rows))
    assert any(f.rule_id == "R-RETRY-STREAK-3" for f in findings)


def test_R_RETRY_STREAK_does_not_fire_on_2(tmp_path):
    rows = [
        {"kind": "turn", "ts": float(i), "user_input": "fix bug",
         "mode": "agent", "model": "deepseek-v4-pro",
         "tokens_in": 100, "tokens_out": 50}
        for i in range(2)
    ]
    findings = optimize(_seed(tmp_path, rows))
    assert not any(f.rule_id == "R-RETRY-STREAK-3" for f in findings)


def test_R_LOW_ONE_SHOT_RATE_fires(tmp_path):
    rows = [{"kind": "turn", "ts": float(i), "user_input": "fix bug",
             "mode": "agent", "model": "deepseek-v4-pro",
             "tokens_in": 100, "tokens_out": 50} for i in range(10)]
    findings = optimize(_seed(tmp_path, rows))
    assert any(f.rule_id == "R-LOW-1SHOT-RATE" for f in findings)


def test_R_EXPLORE_HEAVY_fires(tmp_path):
    rows = [{"kind": "turn", "ts": float(i), "user_input": "explain X",
             "mode": "ask", "model": "deepseek-v4-flash",
             "tokens_in": 100, "tokens_out": 100} for i in range(10)]
    findings = optimize(_seed(tmp_path, rows))
    assert any(f.rule_id == "R-EXPLORE-HEAVY" for f in findings)


def test_R_FLASH_OVER_PRO_fires(tmp_path):
    rows = [{"kind": "turn", "ts": float(i), "user_input": "add feature X",
             "mode": "agent", "model": "deepseek-v4-flash",
             "tokens_in": 100, "tokens_out": 100} for i in range(5)]
    findings = optimize(_seed(tmp_path, rows))
    assert any(f.rule_id == "R-FLASH-OVER-PRO" for f in findings)


def test_optimize_no_data_returns_empty(tmp_path):
    findings = optimize(tmp_path / ".lyra" / "sessions")
    assert findings == []


def test_finding_has_evidence(tmp_path):
    rows = [{"kind": "turn", "ts": float(i), "user_input": "fix bug",
             "mode": "agent", "model": "deepseek-v4-pro",
             "tokens_in": 100, "tokens_out": 50} for i in range(3)]
    findings = optimize(_seed(tmp_path, rows))
    streak = next(f for f in findings if f.rule_id == "R-RETRY-STREAK-3")
    assert len(streak.evidence) >= 1


def test_finding_estimated_savings_optional(tmp_path):
    rows = [{"kind": "turn", "ts": float(i), "user_input": "explain X",
             "mode": "ask", "model": "deepseek-v4-flash",
             "tokens_in": 100, "tokens_out": 100} for i in range(10)]
    findings = optimize(_seed(tmp_path, rows))
    expl = next(f for f in findings if f.rule_id == "R-EXPLORE-HEAVY")
    assert expl.estimated_savings_usd is None or expl.estimated_savings_usd >= 0


def test_optimize_cli_runs(tmp_path, monkeypatch):
    rows = [{"kind": "turn", "ts": float(i), "user_input": "fix bug",
             "mode": "agent", "model": "deepseek-v4-pro",
             "tokens_in": 100, "tokens_out": 50} for i in range(3)]
    _seed(tmp_path, rows)
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(app, ["burn", "optimize"])
    assert res.exit_code == 0
    assert "R-" in res.output


def test_optimize_cli_json(tmp_path, monkeypatch):
    rows = [{"kind": "turn", "ts": float(i), "user_input": "fix bug",
             "mode": "agent", "model": "deepseek-v4-pro",
             "tokens_in": 100, "tokens_out": 50} for i in range(3)]
    _seed(tmp_path, rows)
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(app, ["burn", "optimize", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert isinstance(data["findings"], list)
