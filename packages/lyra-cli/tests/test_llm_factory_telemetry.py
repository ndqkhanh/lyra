"""Factory wires `.env` loader + alias resolver + preflight + telemetry.

Ensures that:
* `.env` values populate `os.environ` when the key is missing.
* Aliases are resolved for `--llm anthropic --model opus`.
* Preflight is not bypassed for known models.
* Every `build_llm` call emits a `provider_selected` HIR event.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from lyra_cli.llm_factory import build_llm, describe_selection


_PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "DASHSCOPE_API_KEY",
)


def _clear_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in _PROVIDER_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_mock_selection_emits_provider_selected_event(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_creds(monkeypatch)
    captured: list[dict] = []
    monkeypatch.setattr(
        "lyra_core.hir.events.emit",
        lambda name, **kw: captured.append({"name": name, **kw}),
    )
    build_llm("mock")
    names = [e["name"] for e in captured]
    assert "provider_selected" in names
    evt = next(e for e in captured if e["name"] == "provider_selected")
    assert evt["provider"] == "mock"


def test_describe_selection_includes_alias_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_creds(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("HARNESS_LLM_MODEL", "opus")
    desc = describe_selection("anthropic")
    assert "claude-opus-4.5" in desc


def test_dotenv_fallback_populates_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_creds(monkeypatch)
    (tmp_path / ".env").write_text('ANTHROPIC_API_KEY="sk-from-dotenv"\n')
    monkeypatch.chdir(tmp_path)
    build_llm("auto")
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-from-dotenv"


def test_missing_creds_hint_surfaced_when_asking_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_creds(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openrouter")
    with pytest.raises(RuntimeError) as e:
        build_llm("anthropic")
    msg = str(e.value).lower()
    assert "openai_api_key" in msg or "openai" in msg
