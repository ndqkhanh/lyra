"""Phase M.7 - git yield correlation."""
from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest
from typer.testing import CliRunner

from lyra_cli.__main__ import app
from lyra_cli.observatory.yield_tracker import yield_report


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git not available in sandbox",
)


@pytest.fixture
def tiny_repo(tmp_path):
    repo = tmp_path
    try:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "t@t.io"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.name", "t"], check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
        pytest.skip("git not available in sandbox")
    sessions = repo / ".lyra" / "sessions"
    sessions.mkdir(parents=True)
    return repo


def _add_session(repo, sid, ts0):
    s = repo / ".lyra" / "sessions" / sid
    s.mkdir(parents=True)
    (s / "turns.jsonl").write_text(json.dumps(
        {"kind": "turn", "turn": 1, "ts": ts0, "user_input": "x",
         "mode": "agent", "model": "deepseek-v4-pro",
         "tokens_in": 100, "tokens_out": 100, "cost_delta_usd": 0.001},
    ) + "\n")


def test_session_with_no_commit_is_abandoned(tiny_repo):
    _add_session(tiny_repo, "s1", time.time())
    rep = yield_report(tiny_repo)
    assert rep.rows[0].outcome == "abandoned"


def test_session_with_commit_during_is_productive(tiny_repo):
    _add_session(tiny_repo, "s1", time.time())
    (tiny_repo / "f.txt").write_text("x")
    subprocess.run(["git", "-C", str(tiny_repo), "add", "f.txt"], check=True)
    subprocess.run(["git", "-C", str(tiny_repo), "commit", "-q", "-m", "feat"], check=True)
    rep = yield_report(tiny_repo)
    assert rep.rows[0].outcome == "productive"


def test_session_with_revert_after_is_reverted(tiny_repo):
    _add_session(tiny_repo, "s1", time.time())
    (tiny_repo / "f.txt").write_text("x")
    subprocess.run(["git", "-C", str(tiny_repo), "add", "f.txt"], check=True)
    subprocess.run(["git", "-C", str(tiny_repo), "commit", "-q", "-m", "feat"], check=True)
    subprocess.run(["git", "-C", str(tiny_repo), "revert", "-q", "--no-edit", "HEAD"], check=True)
    rep = yield_report(tiny_repo)
    assert rep.rows[0].outcome == "reverted"


def test_yield_report_no_repo_returns_empty(tmp_path):
    rep = yield_report(tmp_path)
    assert rep.rows == ()


def test_yield_aggregates_cost(tiny_repo):
    _add_session(tiny_repo, "s1", time.time())
    rep = yield_report(tiny_repo)
    assert rep.total_cost_usd > 0


def test_yield_cli_runs(tiny_repo, monkeypatch):
    _add_session(tiny_repo, "s1", time.time())
    monkeypatch.chdir(tiny_repo)
    res = CliRunner().invoke(app, ["burn", "yield"])
    assert res.exit_code == 0


def test_yield_cli_json(tiny_repo, monkeypatch):
    _add_session(tiny_repo, "s1", time.time())
    monkeypatch.chdir(tiny_repo)
    res = CliRunner().invoke(app, ["burn", "yield", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "rows" in data


def test_yield_handles_session_outside_window(tiny_repo):
    _add_session(tiny_repo, "old", 1.0)
    rep = yield_report(tiny_repo, since=999.0)
    assert rep.rows == ()


def test_yield_outcome_is_correct_field_name(tiny_repo):
    """Sentinel test: regression guard for outcome literal renaming."""
    _add_session(tiny_repo, "s1", time.time())
    rep = yield_report(tiny_repo)
    assert rep.rows[0].outcome in ("productive", "reverted", "abandoned")
