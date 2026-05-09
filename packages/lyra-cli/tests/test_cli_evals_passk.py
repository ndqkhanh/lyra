"""``lyra evals --passk`` integration test (Phase J.2)."""
from __future__ import annotations

import json

from lyra_cli.__main__ import app
from typer.testing import CliRunner


def test_evals_passk_emits_text_summary() -> None:
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["evals", "--passk", "3"])
    assert result.exit_code == 0, result.output
    assert "k=3" in result.output
    assert "pass@k=" in result.output
    assert "pass^k=" in result.output
    assert "reliability_gap=" in result.output


def test_evals_passk_emits_json_payload() -> None:
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["evals", "--passk", "2", "--json"])
    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    assert body["k"] == 2
    assert "pass_at_k" in body
    assert "pass_pow_k" in body
    assert "reliability_gap" in body
    assert "per_case" in body


def test_evals_default_path_unchanged_when_passk_zero() -> None:
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["evals", "--corpus", "golden"])
    assert result.exit_code == 0, result.output
    assert "corpus=golden" in result.output
