"""Phase M.4 - ``lyra burn`` Typer e2e."""
from __future__ import annotations

import json
import time

import pytest
from typer.testing import CliRunner

from lyra_cli.__main__ import app


runner = CliRunner()


@pytest.fixture
def repo_with_sessions(tmp_path, monkeypatch):
    sessions = tmp_path / ".lyra" / "sessions"
    s = sessions / "20260427-100000-aaa"
    s.mkdir(parents=True)
    now = time.time()
    (s / "turns.jsonl").write_text(json.dumps(
        {"kind": "turn", "turn": 1, "ts": now, "user_input": "fix bug",
         "mode": "agent", "model": "deepseek-v4-pro",
         "tokens_in": 1000, "tokens_out": 500, "cost_delta_usd": 0.003}
    ) + "\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_burn_runs_without_args(repo_with_sessions):
    res = runner.invoke(app, ["burn"])
    assert res.exit_code == 0
    assert "Lyra Burn" in res.output or "burn" in res.output.lower()


def test_burn_with_no_sessions_says_no_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["burn"])
    assert res.exit_code == 0
    assert "no data" in res.output.lower() or "$0" in res.output


def test_burn_json_emits_valid_payload(repo_with_sessions):
    res = runner.invoke(app, ["burn", "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.output)
    assert payload["total_turns"] == 1
    assert "by_model" in payload
    assert "by_category" in payload


def test_burn_since_relative(repo_with_sessions):
    res = runner.invoke(app, ["burn", "--since", "1d"])
    assert res.exit_code == 0


def test_burn_until_iso(repo_with_sessions):
    res = runner.invoke(app, ["burn", "--until", "2026-04-28"])
    assert res.exit_code == 0


def test_burn_limit_clamps_session_list(repo_with_sessions):
    res = runner.invoke(app, ["burn", "--limit", "1"])
    assert res.exit_code == 0


def test_burn_watch_flag_accepted(repo_with_sessions, monkeypatch):
    """--watch loops; we patch the loop to one iteration so the test exits."""
    from lyra_cli.commands import burn as burn_mod
    calls = {"n": 0}

    def fake_sleep(_secs):
        calls["n"] += 1
        if calls["n"] >= 1:
            raise KeyboardInterrupt

    monkeypatch.setattr(burn_mod, "_sleep", fake_sleep)
    res = runner.invoke(app, ["burn", "--watch"])
    assert res.exit_code == 0
