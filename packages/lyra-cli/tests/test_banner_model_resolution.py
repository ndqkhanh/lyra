"""The REPL banner shows the *resolved* provider when model is ``auto``.

Without this resolution, a user with ``DEEPSEEK_API_KEY`` set who
runs ``lyra`` (no explicit ``--llm``) would see "Model auto" in the
banner — accurate to the flag, but unhelpful: they want to see
*which* backend the auto cascade actually landed on.

The helper :func:`_resolve_banner_model` does the bridging:

* concrete model slugs → pass through (``mock`` stays ``mock``,
  ``deepseek`` stays ``deepseek``, ``gpt-5`` stays ``gpt-5``);
* the literal ``"auto"`` → resolved via :func:`describe_selection`,
  which mirrors what :func:`build_llm` would actually pick.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _clean_provider_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path | None = None,
) -> None:
    for k in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "CEREBRAS_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "OLLAMA_HOST",
        "HARNESS_LLM_MODEL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "BEDROCK_MODEL",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "VERTEX_PROJECT",
        "VERTEX_LOCATION",
        "VERTEX_MODEL",
        "GITHUB_TOKEN",
        "COPILOT_MODEL",
    ):
        monkeypatch.delenv(k, raising=False)
    if tmp_path is not None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
        monkeypatch.chdir(tmp_path)


def test_concrete_model_passes_through_unchanged() -> None:
    """Concrete model names are session state; they must not be rewritten."""
    from lyra_cli.interactive.driver import _resolve_banner_model

    for slug in ("mock", "deepseek", "gpt-5", "claude-opus-4.5"):
        assert _resolve_banner_model(slug) == slug


def test_auto_resolves_to_deepseek_label_when_deepseek_configured(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``auto`` + DEEPSEEK_API_KEY → banner shows the resolved DeepSeek label."""
    _clean_provider_env(monkeypatch, tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")

    from lyra_cli.interactive.driver import _resolve_banner_model

    label = _resolve_banner_model("auto")
    assert label.startswith("deepseek ·"), (
        f"expected 'deepseek · …', got {label!r}"
    )


def test_auto_resolves_to_unconfigured_label_when_nothing_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``auto`` with no keys → banner reads ``unconfigured``, never ``auto``.

    This is the "you need to set up a key" UX hint propagated through
    to the welcome banner: a fresh install must not silently look like
    it has a working backend.
    """
    _clean_provider_env(monkeypatch, tmp_path)

    from lyra_cli.interactive.driver import _resolve_banner_model

    label = _resolve_banner_model("auto")
    assert label.startswith("unconfigured"), (
        f"expected 'unconfigured · …' for fresh install, got {label!r}"
    )


def test_auto_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``Auto`` / ``AUTO`` still trigger resolution.

    Defensive against future code paths that might lower-case-first
    the flag elsewhere.
    """
    _clean_provider_env(monkeypatch, tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")

    from lyra_cli.interactive.driver import _resolve_banner_model

    assert _resolve_banner_model("AUTO").startswith("deepseek ·")
    assert _resolve_banner_model("Auto").startswith("deepseek ·")
    assert _resolve_banner_model(" auto ").startswith("deepseek ·")
