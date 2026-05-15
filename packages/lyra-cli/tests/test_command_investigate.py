"""CLI tests for `lyra investigate <question>`.

The handler is invoked directly with a stubbed LLM provider so the
test stays hermetic (no network, no real model). Pin only the CLI
contract: arg parsing, error paths, ledger emission.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from lyra_cli.__main__ import app
from lyra_cli.commands import investigate as investigate_mod


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    (tmp_path / "doc.md").write_text("ANSWER: FORTY_TWO\n")
    return tmp_path


@pytest.fixture(autouse=True)
def _stub_llm_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace build_llm with a deterministic fake."""

    class _Stub:
        def generate(self, *, messages: list[dict], tools: list[dict]) -> dict:
            return {
                "content": "the answer is FORTY_TWO per doc.md:1",
                "tool_calls": [],
                "stop_reason": "end_turn",
            }

    monkeypatch.setattr(investigate_mod, "build_llm", lambda _kind: _Stub())


def test_help_lists_investigate_command() -> None:
    runner = CliRunner()
    out = runner.invoke(app, ["--help"])
    assert out.exit_code == 0
    assert "investigate" in out.stdout


def test_runs_against_corpus_and_prints_answer(corpus_dir: Path) -> None:
    runner = CliRunner()
    out = runner.invoke(
        app, ["investigate", "what's the answer?", "--corpus", str(corpus_dir)],
    )
    assert out.exit_code == 0, out.stdout
    assert "FORTY_TWO" in out.stdout


def test_rejects_non_directory_corpus(tmp_path: Path) -> None:
    bogus = tmp_path / "not-a-dir"
    runner = CliRunner()
    out = runner.invoke(
        app, ["investigate", "q", "--corpus", str(bogus)],
    )
    assert out.exit_code == 2

def test_writes_output_dir(corpus_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "investigate", "q",
            "--corpus", str(corpus_dir),
            "--output-dir", str(out_dir),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "final.txt").exists()
    assert (out_dir / "question.txt").exists()
    assert (out_dir / "conversation_full.json").exists()


def test_context_level_flag_accepts_paper_default(corpus_dir: Path) -> None:
    runner = CliRunner()
    out = runner.invoke(
        app,
        ["investigate", "q", "--corpus", str(corpus_dir), "--context-level", "3"],
    )
    assert out.exit_code == 0, out.stdout
    assert "TRUNCATE_PLUS_COMPACT" in out.stdout       # banner prints level name


def test_context_level_rejects_out_of_range(corpus_dir: Path) -> None:
    runner = CliRunner()
    out = runner.invoke(
        app,
        ["investigate", "q", "--corpus", str(corpus_dir), "--context-level", "99"],
    )
    assert out.exit_code != 0
