"""Default-entry routing for the v3.14 TUI flip.

Phase 6 contract:
  * Bare ``lyra`` → v2 Textual shell (the new default)
  * ``lyra --legacy`` → prompt_toolkit REPL
  * ``LYRA_TUI=legacy`` env → prompt_toolkit REPL (per-shell opt-out)
  * ``LYRA_TUI=v2`` env → v2 (no-op, kept for backwards compat with
    Phase 1–5 users who set it)
  * Subcommands (e.g. ``lyra --version``) never hijack the TUI path

The actual Textual app is not mounted (no terminal in CI); both code
paths are patched to record their invocation so the test stays fast
and deterministic.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from lyra_cli import tui_v2
from lyra_cli.__main__ import app


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a clean LYRA_TUI value."""
    monkeypatch.delenv("LYRA_TUI", raising=False)


def test_is_v2_enabled_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LYRA_TUI", raising=False)
    assert tui_v2.is_v2_enabled() is False
    monkeypatch.setenv("LYRA_TUI", "v2")
    assert tui_v2.is_v2_enabled() is True
    monkeypatch.setenv("LYRA_TUI", "V2")
    assert tui_v2.is_v2_enabled() is True
    monkeypatch.setenv("LYRA_TUI", "legacy")
    assert tui_v2.is_v2_enabled() is False


def test_bare_lyra_defaults_to_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 6: bare ``lyra`` (no flag, no env) now opens the v2 shell."""
    monkeypatch.delenv("LYRA_TUI", raising=False)

    runner = CliRunner()
    with patch.object(tui_v2, "launch_tui_v2", return_value=0) as launch, patch(
        "lyra_cli.interactive.driver.run"
    ) as repl_run:
        result = runner.invoke(app, [])

    assert result.exit_code == 0, result.output
    launch.assert_called_once()
    repl_run.assert_not_called()
    kwargs = launch.call_args.kwargs
    assert "repo_root" in kwargs and "model" in kwargs


def test_lyra_v2_env_keeps_v2_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """``LYRA_TUI=v2`` is a backwards-compat affirmation, not an override."""
    monkeypatch.setenv("LYRA_TUI", "v2")

    runner = CliRunner()
    with patch.object(tui_v2, "launch_tui_v2", return_value=0) as launch, patch(
        "lyra_cli.interactive.driver.run"
    ) as repl_run:
        result = runner.invoke(app, [])

    assert result.exit_code == 0, result.output
    launch.assert_called_once()
    repl_run.assert_not_called()


def test_legacy_flag_dispatches_to_prompt_toolkit_repl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``lyra --legacy`` boots the prompt_toolkit REPL."""
    monkeypatch.delenv("LYRA_TUI", raising=False)

    runner = CliRunner()
    with patch.object(tui_v2, "launch_tui_v2") as launch, patch(
        "lyra_cli.interactive.driver.run", return_value=0
    ) as repl_run:
        result = runner.invoke(app, ["--legacy"])

    assert result.exit_code == 0, result.output
    repl_run.assert_called_once()
    launch.assert_not_called()


def test_lyra_legacy_env_dispatches_to_prompt_toolkit_repl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``LYRA_TUI=legacy`` is the per-shell off-ramp during the migration."""
    monkeypatch.setenv("LYRA_TUI", "legacy")

    runner = CliRunner()
    with patch.object(tui_v2, "launch_tui_v2") as launch, patch(
        "lyra_cli.interactive.driver.run", return_value=0
    ) as repl_run:
        result = runner.invoke(app, [])

    assert result.exit_code == 0, result.output
    repl_run.assert_called_once()
    launch.assert_not_called()


def test_legacy_prints_deprecation_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the legacy path runs, the off-ramp must be surfaced.

    Click's CliRunner mixes stderr into ``.output`` by default — that's
    fine for an assertion on the user-visible text. The message goes
    out via ``typer.echo(..., err=True)`` so it lands in stderr at
    runtime even when mixed in tests.
    """
    monkeypatch.delenv("LYRA_TUI", raising=False)

    runner = CliRunner()
    with patch.object(tui_v2, "launch_tui_v2"), patch(
        "lyra_cli.interactive.driver.run", return_value=0
    ):
        result = runner.invoke(app, ["--legacy"])

    assert result.exit_code == 0, result.output
    out = result.output.lower()
    assert "legacy" in out
    assert "v3.15" in out


def test_subcommand_does_not_hijack(monkeypatch: pytest.MonkeyPatch) -> None:
    """A subcommand short-circuits before TUI/REPL dispatch fires."""
    monkeypatch.delenv("LYRA_TUI", raising=False)

    runner = CliRunner()
    with patch.object(tui_v2, "launch_tui_v2") as launch, patch(
        "lyra_cli.interactive.driver.run"
    ) as repl_run:
        result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    launch.assert_not_called()
    repl_run.assert_not_called()
    assert "lyra" in result.output.lower()
