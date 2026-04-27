"""`/model list` enumerates every configured + unconfigured backend."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession


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


def _session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path)


def test_model_list_enumerates_all_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_creds(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    out = _session(tmp_path)._cmd_model_list("")
    lower = out.lower()
    for needle in ("anthropic", "openai", "ollama", "dashscope", "vllm", "lmstudio"):
        assert needle in lower, f"missing provider {needle!r} in /model list output"


def _row_for(out: str, provider: str) -> str:
    """Return the per-provider row (excluding the legend line) for *provider*.

    The renderer prints one row per provider followed by a legend at
    the bottom that itself contains the marker glyphs. Tests that
    assert "✓ in out" would pass off the legend alone — that's the
    bug this helper exists to prevent. We pick the first non-legend
    line that mentions the provider's slug.
    """
    for line in out.splitlines():
        lower = line.lower()
        if provider not in lower:
            continue
        if lower.lstrip().startswith("legend"):
            continue
        return line
    return ""


def test_model_list_marks_configured_vs_not(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The configured / not-configured glyphs must appear on the *rows* —
    not just in the trailing legend."""
    _clear_creds(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    out = _session(tmp_path)._cmd_model_list("")

    anthropic_row = _row_for(out, "anthropic")
    assert anthropic_row, "expected an anthropic row in /model list output"
    # Configured provider — either ✓ (configured) or ● (currently selected).
    assert any(m in anthropic_row for m in ("✓", "●")), (
        f"anthropic row missing configured marker: {anthropic_row!r}"
    )

    # An OpenAI row must exist and be marked NOT configured because we
    # cleared every credential at the top of the test.
    openai_row = _row_for(out, "openai")
    assert openai_row, "expected an openai row in /model list output"
    assert "—" in openai_row, (
        f"openai row should be marked '—' (not configured) but was: {openai_row!r}"
    )


def test_model_list_highlights_selected_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_creds(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = _session(tmp_path)
    s.current_llm_name = "anthropic"
    out = s._cmd_model_list("")
    anthropic_line = next(
        (l for l in out.splitlines() if "anthropic" in l.lower()), ""
    )
    assert any(
        marker in anthropic_line
        for marker in ("●", "▶", "[x]", "(selected)")
    )


def test_models_alias_is_accepted(tmp_path: Path) -> None:
    out = _session(tmp_path)._cmd_models("")
    assert "ollama" in out.lower()
