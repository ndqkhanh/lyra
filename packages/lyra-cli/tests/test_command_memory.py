"""Smoke tests for the ``lyra memory`` Typer subcommand."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lyra_cli.commands.memory import memory_app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / ".lyra" / "memory" / "reasoning_bank.sqlite"


def test_stats_on_empty_bank(runner: CliRunner, db: Path) -> None:
    result = runner.invoke(
        memory_app, ["stats", "--db", str(db), "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["lessons_total"] == 0


def test_record_success_then_recall(runner: CliRunner, db: Path) -> None:
    result = runner.invoke(
        memory_app,
        [
            "record",
            "parse-json",
            "success",
            "--summary",
            "use the streaming parser when input is large",
            "--trajectory-id",
            "manual-1",
            "--db",
            str(db),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Recorded" in result.output

    recall = runner.invoke(
        memory_app,
        ["recall", "parse-json", "--db", str(db), "--json"],
    )
    assert recall.exit_code == 0, recall.output
    payload = json.loads(recall.output)
    assert any(lesson["polarity"] == "success" for lesson in payload)


def test_record_failure_yields_anti_skill(runner: CliRunner, db: Path) -> None:
    result = runner.invoke(
        memory_app,
        [
            "record",
            "parse-json",
            "failure",
            "--summary",
            "ImportError when using the v2 parser",
            "--trajectory-id",
            "manual-fail-1",
            "--db",
            str(db),
        ],
    )
    assert result.exit_code == 0, result.output

    recall = runner.invoke(
        memory_app,
        [
            "recall",
            "parse-json",
            "--polarity",
            "failure",
            "--db",
            str(db),
            "--json",
        ],
    )
    assert recall.exit_code == 0
    payload = json.loads(recall.output)
    assert payload, "expected at least one failure lesson"
    assert all(lesson["polarity"] == "failure" for lesson in payload)


def test_recall_polarity_validation(runner: CliRunner, db: Path) -> None:
    result = runner.invoke(
        memory_app,
        ["recall", "x", "--polarity", "neither", "--db", str(db)],
    )
    assert result.exit_code != 0
    assert "polarity" in result.output.lower()


def test_list_filters_polarity(runner: CliRunner, db: Path) -> None:
    runner.invoke(
        memory_app,
        [
            "record",
            "parse-json",
            "success",
            "--summary",
            "use streaming parser",
            "--db",
            str(db),
            "--trajectory-id",
            "ok",
        ],
    )
    runner.invoke(
        memory_app,
        [
            "record",
            "render-table",
            "failure",
            "--summary",
            "table renderer crashed on unicode",
            "--db",
            str(db),
            "--trajectory-id",
            "bad",
        ],
    )
    only_failure = runner.invoke(
        memory_app,
        ["list", "--polarity", "failure", "--db", str(db), "--json"],
    )
    assert only_failure.exit_code == 0
    payload = json.loads(only_failure.output)
    assert payload, "expected at least one failure lesson"
    assert all(lesson["polarity"] == "failure" for lesson in payload)


def test_show_unknown_id_exits_nonzero(runner: CliRunner, db: Path) -> None:
    result = runner.invoke(
        memory_app, ["show", "no-such-lesson", "--db", str(db)]
    )
    assert result.exit_code != 0


def test_wipe_clears(runner: CliRunner, db: Path) -> None:
    runner.invoke(
        memory_app,
        [
            "record",
            "parse-json",
            "success",
            "--summary",
            "use streaming parser",
            "--db",
            str(db),
            "--trajectory-id",
            "ok",
        ],
    )
    result = runner.invoke(memory_app, ["wipe", "--yes", "--db", str(db)])
    assert result.exit_code == 0
    assert "Deleted" in result.output

    after = runner.invoke(memory_app, ["stats", "--db", str(db), "--json"])
    payload = json.loads(after.output)
    assert payload["lessons_total"] == 0
