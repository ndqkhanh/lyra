"""Tests for ``lyra setup`` and ``lyra doctor --json``."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from lyra_cli.commands.doctor import doctor_command
from lyra_cli.commands.setup import setup_command


@pytest.fixture(autouse=True)
def _isolate_lyra_home(tmp_path: Path, monkeypatch):
    """Pin ``$LYRA_HOME`` to a tmpdir so the wizard never touches real ~/.lyra."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra-home"))
    # Strip provider env vars — tests opt back in.
    for name in (
        "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY",
        "GROQ_API_KEY", "CEREBRAS_API_KEY", "MISTRAL_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


runner = CliRunner()


def _setup_app() -> typer.Typer:
    """Multi-command app so Typer keeps ``setup`` as a routable name."""
    a = typer.Typer()
    a.command("setup")(setup_command)
    # Typer collapses the name when only one command is registered,
    # which makes the ``["setup", ...]`` invocation ambiguous. A
    # second placeholder command keeps the routing explicit.
    a.command("noop")(lambda: None)
    return a


def _doctor_app() -> typer.Typer:
    a = typer.Typer()
    a.command("doctor")(doctor_command)
    a.command("noop")(lambda: None)
    return a


# ---------------------------------------------------------------------------
# Doctor --json
# ---------------------------------------------------------------------------


def test_doctor_json_emits_structured_payload(tmp_path: Path) -> None:
    result = runner.invoke(
        _doctor_app(),
        ["doctor", "--repo-root", str(tmp_path), "--json"],
    )
    # Exit code 0 acceptable: no required-non-state probe failed.
    payload = json.loads(result.stdout)
    assert payload["repo_root"] == str(tmp_path.resolve())
    assert "probes" in payload and isinstance(payload["probes"], list)
    cats = {p["category"] for p in payload["probes"]}
    assert {"runtime", "providers", "packages", "state"} <= cats


# ---------------------------------------------------------------------------
# Setup — non-interactive path
# ---------------------------------------------------------------------------


def test_setup_non_interactive_writes_settings(tmp_path: Path) -> None:
    home = Path(os.environ["LYRA_HOME"])
    result = runner.invoke(
        _setup_app(),
        [
            "setup",
            "--non-interactive",
            "--provider", "deepseek",
            "--model", "deepseek-flash",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["provider"] == "deepseek"
    assert payload["model"] == "deepseek-flash"

    settings = json.loads((home / "settings.json").read_text())
    assert settings["default_provider"] == "deepseek"
    assert settings["default_model"] == "deepseek-flash"
    assert settings["config_version"] >= 1


def test_setup_non_interactive_with_api_key_writes_env(tmp_path: Path) -> None:
    home = Path(os.environ["LYRA_HOME"])
    result = runner.invoke(
        _setup_app(),
        [
            "setup",
            "--non-interactive",
            "--provider", "anthropic",
            "--model", "claude-sonnet-4.5",
            "--api-key", "sk-test-secret",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output

    env_body = (home / ".env").read_text()
    assert "ANTHROPIC_API_KEY=sk-test-secret" in env_body


def test_setup_non_interactive_uses_configured_provider_when_no_flag(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
    result = runner.invoke(
        _setup_app(),
        ["setup", "--non-interactive", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    # Configured providers wins the auto-pick.
    assert payload["provider"] == "deepseek"


def test_setup_records_config_version(tmp_path: Path) -> None:
    home = Path(os.environ["LYRA_HOME"])
    runner.invoke(
        _setup_app(),
        [
            "setup",
            "--non-interactive",
            "--provider", "openai",
            "--model", "gpt-5",
        ],
    )
    settings = json.loads((home / "settings.json").read_text())
    from lyra_cli.config_io import LYRA_CONFIG_VERSION

    assert settings["config_version"] == LYRA_CONFIG_VERSION
