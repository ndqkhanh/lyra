"""``lyra evolve`` integration tests (Phase J.5, v3.1.0)."""
from __future__ import annotations

import json
from pathlib import Path

from lyra_cli.__main__ import app
from typer.testing import CliRunner


def _write_task(tmp: Path) -> Path:
    """Author a tiny JSON task spec the echo stub can pass."""
    spec = {
        "prompt": "Solve the user's question.",
        "examples": [
            {"input": "what is 2+2?", "expected": "Solve"},
            {"input": "capital of france?", "expected": "Solve"},
        ],
    }
    path = tmp / "task.json"
    path.write_text(json.dumps(spec))
    return path


def test_evolve_runs_with_default_echo_stub(tmp_path: Path) -> None:
    task = _write_task(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["evolve", "--task", str(task), "--generations", "1", "--population", "2"],
    )
    assert result.exit_code == 0, result.output
    assert "lyra evolve" in result.output
    assert "Pareto front" in result.output
    assert "best prompt" in result.output


def test_evolve_emits_json_when_flag_set(tmp_path: Path) -> None:
    task = _write_task(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "evolve",
            "--task",
            str(task),
            "--generations",
            "1",
            "--population",
            "2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "best" in payload
    assert "front" in payload
    assert "history" in payload
    assert payload["task_path"] == str(task)
    assert payload["llm"] == "echo"


def test_evolve_writes_output_file(tmp_path: Path) -> None:
    task = _write_task(tmp_path)
    out = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "evolve",
            "--task",
            str(task),
            "--generations",
            "1",
            "--population",
            "2",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    payload = json.loads(out.read_text())
    assert "best" in payload


def test_evolve_rejects_non_list_examples(tmp_path: Path) -> None:
    spec = {"prompt": "x", "examples": "not a list"}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(spec))
    runner = CliRunner()
    result = runner.invoke(app, ["evolve", "--task", str(path)])
    assert result.exit_code != 0
    # ``typer.BadParameter`` renders to stderr, not stdout; with
    # ```` we have to inspect both streams (newer
    # Click/Typer no longer folds the abort message into ``output``).
    combined = (result.output or "") + (result.stderr or "")
    assert "examples must be a list" in combined or "Invalid value" in combined
