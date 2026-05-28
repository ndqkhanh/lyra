"""Tests for the Phase-B/C/D CLI transparency commands.

Covers:
- ``lyra model``     (Plan 4 Phase B — routing policy + decisions)
- ``lyra agents``    (Plan 4 Phase D — fleet view)
- ``lyra hops``      (Plan 4 Phase C — IRCoT hop trace)
- ``lyra skills``    (Plan 1 Phase 8 — activated skills)
- ``lyra dag``       (Plan 1 Phase 8 — agent DAG)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from lyra_cli.commands.agents import agents_app
from lyra_cli.commands.hops import hops_app
from lyra_cli.commands.model import model_app
from lyra_cli.commands.skills_view import dag_app, skills_app
from typer.testing import CliRunner


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# lyra model
# ---------------------------------------------------------------------------


def test_model_empty(tmp_path: Path, runner: CliRunner) -> None:
    """Empty repo: graceful 'no routing data found' message."""
    result = runner.invoke(model_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No routing data found" in result.stdout


def test_model_with_decisions(tmp_path: Path, runner: CliRunner) -> None:
    routing = tmp_path / ".lyra" / "routing"
    routing.mkdir(parents=True)
    (routing / "policy.json").write_text(
        json.dumps({"tier_strategy": "BAAR", "fast_model": "haiku-4-5"})
    )
    (routing / "decisions.jsonl").write_text(
        "\n".join(
            json.dumps({
                "ts": f"2026-05-20T08:0{i}:00Z",
                "session_id": "sess-1",
                "turn": i,
                "tier": "fast" if i % 2 == 0 else "reasoning",
                "reason": "low ambiguity",
                "cost_usd": 0.001 * i,
            })
            for i in range(1, 4)
        )
    )

    result = runner.invoke(model_app, ["--repo-root", str(tmp_path), "--tail", "10"])
    assert result.exit_code == 0
    assert "Routing Policy" in result.stdout
    assert "BAAR" in result.stdout
    assert "fast" in result.stdout
    assert "reasoning" in result.stdout


def test_model_json_output(tmp_path: Path, runner: CliRunner) -> None:
    routing = tmp_path / ".lyra" / "routing"
    routing.mkdir(parents=True)
    (routing / "policy.json").write_text(json.dumps({"k": "v"}))
    result = runner.invoke(model_app, ["--repo-root", str(tmp_path), "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["policy"] == {"k": "v"}
    assert parsed["decisions"] == []


# ---------------------------------------------------------------------------
# lyra agents
# ---------------------------------------------------------------------------


def test_agents_empty(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(agents_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No fleet snapshot found" in result.stdout


def test_agents_priority_sort(tmp_path: Path, runner: CliRunner) -> None:
    lyra = tmp_path / ".lyra"
    lyra.mkdir()
    (lyra / "fleet.json").write_text(json.dumps({
        "agents": [
            {"agent_id": "low-pri", "attention_priority": 4, "state": "running",
             "row_summary": "background sync"},
            {"agent_id": "critical", "attention_priority": 0, "state": "blocked",
             "row_summary": "destructive write pending"},
            {"agent_id": "normal", "attention_priority": 2, "state": "running",
             "row_summary": "fetching docs"},
        ]
    }))

    result = runner.invoke(agents_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    # All three agents shown
    assert "critical" in result.stdout
    assert "normal" in result.stdout
    assert "low-pri" in result.stdout
    # P0 sorted before P4
    assert result.stdout.index("critical") < result.stdout.index("low-pri")


def test_agents_priority_filter(tmp_path: Path, runner: CliRunner) -> None:
    lyra = tmp_path / ".lyra"
    lyra.mkdir()
    (lyra / "fleet.json").write_text(json.dumps([
        {"agent_id": "a", "attention_priority": 0, "row_summary": "p0"},
        {"agent_id": "b", "attention_priority": 4, "row_summary": "p4"},
    ]))

    result = runner.invoke(agents_app, ["--repo-root", str(tmp_path), "-p", "P0"])
    assert result.exit_code == 0
    assert "p0" in result.stdout
    assert "p4" not in result.stdout


# ---------------------------------------------------------------------------
# lyra hops
# ---------------------------------------------------------------------------


def test_hops_empty(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(hops_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No hop traces found" in result.stdout


def test_hops_with_trace(tmp_path: Path, runner: CliRunner) -> None:
    hops_dir = tmp_path / ".lyra" / "hops"
    hops_dir.mkdir(parents=True)
    (hops_dir / "sess-research-1.jsonl").write_text(
        "\n".join(
            json.dumps({
                "hop_index": i,
                "query": f"what is X{i}?",
                "support_score": 0.5 + 0.1 * i,
                "reasoning": f"hop {i} reasoning",
                "source_refs": [f"src-{j}" for j in range(i)],
            })
            for i in range(1, 4)
        )
    )

    result = runner.invoke(hops_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "sess-research-1" in result.stdout
    assert "Mean support" in result.stdout
    assert "what is X1?" in result.stdout


def test_hops_explicit_session(tmp_path: Path, runner: CliRunner) -> None:
    hops_dir = tmp_path / ".lyra" / "hops"
    hops_dir.mkdir(parents=True)
    (hops_dir / "abc.jsonl").write_text(
        json.dumps({"hop_index": 1, "query": "q", "support_score": 0.9, "reasoning": "r"})
    )
    result = runner.invoke(hops_app, ["--repo-root", str(tmp_path), "-s", "abc", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["session"] == "abc"
    assert len(parsed["hops"]) == 1


# ---------------------------------------------------------------------------
# lyra skills --active
# ---------------------------------------------------------------------------


def test_skills_without_active_flag(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(skills_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "--active" in result.stdout


def test_skills_active_empty(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(skills_app, ["--repo-root", str(tmp_path), "--active"])
    assert result.exit_code == 0
    assert "No active skills" in result.stdout


def test_skills_active_with_data(tmp_path: Path, runner: CliRunner) -> None:
    sk = tmp_path / ".lyra" / "skills"
    sk.mkdir(parents=True)
    (sk / "active.json").write_text(json.dumps({
        "skills": [
            {"name": "research/discovery", "tier": "embedding",
             "trust_tier": "core", "success_rate": 0.92, "last_used": "2026-05-20T08:00:00Z"},
            {"name": "research/synthesis", "tier": "BM25",
             "trust_tier": "verified", "success_rate": 0.81, "last_used": "2026-05-20T08:01:00Z"},
        ]
    }))
    result = runner.invoke(skills_app, ["--repo-root", str(tmp_path), "--active"])
    assert result.exit_code == 0
    assert "research/discovery" in result.stdout
    assert "research/synthesis" in result.stdout


# ---------------------------------------------------------------------------
# lyra dag
# ---------------------------------------------------------------------------


def test_dag_empty(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(dag_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No DAG snapshot found" in result.stdout


def test_dag_renders_tree(tmp_path: Path, runner: CliRunner) -> None:
    dag_dir = tmp_path / ".lyra" / "dag"
    dag_dir.mkdir(parents=True)
    (dag_dir / "sess-1.json").write_text(json.dumps({
        "total_cost_usd": 0.0042,
        "nodes": [
            {"id": "root", "role": "planner", "status": "done", "cost_usd": 0.001},
            {"id": "child-a", "role": "executor", "status": "running", "cost_usd": 0.002},
            {"id": "child-b", "role": "verifier", "status": "pending", "cost_usd": 0.0},
        ],
        "edges": [
            {"from": "root", "to": "child-a"},
            {"from": "root", "to": "child-b"},
        ],
    }))
    result = runner.invoke(dag_app, ["--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Agent DAG" in result.stdout
    assert "root" in result.stdout
    assert "child-a" in result.stdout
    assert "child-b" in result.stdout


def test_dag_json(tmp_path: Path, runner: CliRunner) -> None:
    dag_dir = tmp_path / ".lyra" / "dag"
    dag_dir.mkdir(parents=True)
    payload = {"total_cost_usd": 0.0, "nodes": [], "edges": []}
    (dag_dir / "x.json").write_text(json.dumps(payload))
    result = runner.invoke(dag_app, ["--repo-root", str(tmp_path), "-s", "x", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed == payload
