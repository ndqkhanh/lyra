"""Phase 8 — first-run onboarding wizard.

When the user runs ``lyra`` for the very first time we fire a small
wizard before the REPL boots:

1. Greet, explain what's about to happen.
2. Open the connect dialog (Phase 3) for provider + key.
3. Drop them into the REPL with the chosen provider already loaded.

This file locks the *trigger logic* — the wizard must only fire when
**all** of these are true:

* ``$LYRA_HOME/auth.json`` doesn't exist yet (or has zero providers).
* No supported ``*_API_KEY`` env var is set (so users with env-var
  configs aren't dragged through a wizard they don't need).
* stdin & stdout are TTYs (so CI invocations stay headless).

The visual flow itself is exercised by Phase 3's connect tests; the
wizard just orchestrates that flow.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def lyra_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every provider env var so should_run_wizard is deterministic."""
    for var in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "XAI_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def test_should_run_wizard_true_on_pristine_home(
    lyra_home: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lyra_cli.interactive.onboarding import should_run_wizard

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    assert should_run_wizard() is True


def test_should_run_wizard_false_when_authjson_has_provider(
    lyra_home: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lyra_cli.interactive.onboarding import should_run_wizard
    from lyra_core.auth.store import save

    save("deepseek", "sk-fake")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    assert should_run_wizard() is False


def test_should_run_wizard_false_when_env_var_set(
    lyra_home: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lyra_cli.interactive.onboarding import should_run_wizard

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    assert should_run_wizard() is False


def test_should_run_wizard_false_in_non_tty(
    lyra_home: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lyra_cli.interactive.onboarding import should_run_wizard

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    assert should_run_wizard() is False


def test_should_run_wizard_false_when_user_dismissed(
    lyra_home: Path, clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sentinel file (``$LYRA_HOME/.no-onboarding``) suppresses the wizard."""
    (lyra_home / ".no-onboarding").write_text("dismissed at 2026-04-26\n")

    from lyra_cli.interactive.onboarding import should_run_wizard

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    assert should_run_wizard() is False


def test_dismiss_writes_sentinel_file(
    lyra_home: Path, clean_env: None
) -> None:
    from lyra_cli.interactive.onboarding import dismiss_wizard

    dismiss_wizard()
    assert (lyra_home / ".no-onboarding").exists()


def test_render_welcome_returns_text(
    lyra_home: Path, clean_env: None
) -> None:
    """Welcome panel for the wizard is a Rich-renderable Text."""
    from rich.text import Text

    from lyra_cli.interactive.onboarding import render_welcome

    out = render_welcome()
    assert isinstance(out, Text)
    plain = out.plain.lower()
    # The welcome must mention the action the user is about to take.
    assert "lyra" in plain
    assert "provider" in plain or "api key" in plain or "connect" in plain
