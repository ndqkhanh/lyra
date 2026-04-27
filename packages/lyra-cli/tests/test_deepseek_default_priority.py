"""DeepSeek is the default provider in the ``auto`` cascade.

The user explicitly asked Lyra to "make deepseek as default" because
that's the API key they have funded and the model family they want
to drive day-to-day. Promoting DeepSeek to the top of the cascade
means ``lyra run "<task>"`` (no ``--llm`` flag) routes to DeepSeek
the moment ``DEEPSEEK_API_KEY`` is set — even when an Anthropic key
is *also* present.

The previous order (Anthropic → OpenAI → Gemini → DeepSeek → …)
matched "Claude is the reference target for tool-using agents", but
in 2026 DeepSeek's coder models are competitive on benchmarks and
~10-20× cheaper, so the cost-aware default lives there.

We keep the explicit ``--llm anthropic`` / ``--llm openai`` paths
working unchanged: only ``--llm auto`` (the implicit default)
changes its priority order.
"""
from __future__ import annotations

import os
from typing import Iterator

import pytest


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip *every* provider env var so each test starts from zero.

    Without this, picking up a real ``DEEPSEEK_API_KEY`` from the
    developer's shell would make these tests pass for the wrong
    reason — or fail in CI under a different env.
    """
    for k in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "OLLAMA_HOST",
        "HARNESS_LLM_MODEL",
        "OPEN_HARNESS_DEEPSEEK_MODEL",
    ):
        monkeypatch.delenv(k, raising=False)
    # Belt-and-braces: the dotenv hydration walks up the tree from
    # CWD, so point CWD at /tmp where there's no .env to surprise us.
    monkeypatch.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
    yield


def test_auto_picks_deepseek_when_only_deepseek_configured(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Baseline: only ``DEEPSEEK_API_KEY`` set → cascade returns DeepSeek.

    This passed before too (DeepSeek was reachable in auto, just
    behind 3 other slots). Kept as a guard against future cascade
    regressions.
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")

    from lyra_cli.llm_factory import build_llm

    llm = build_llm("auto")
    assert getattr(llm, "provider_name", None) == "deepseek", (
        f"expected provider_name='deepseek', got "
        f"{getattr(llm, 'provider_name', None)!r}"
    )


def test_auto_picks_deepseek_when_anthropic_also_configured(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point of the change: DeepSeek wins over Anthropic.

    With *both* keys set, the previous cascade went Anthropic →
    DeepSeek (Anthropic wins). v2.1.x makes DeepSeek the head of the
    cascade so cost-aware users get DeepSeek without typing a flag.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")

    from lyra_cli.llm_factory import build_llm

    llm = build_llm("auto")
    assert getattr(llm, "provider_name", None) == "deepseek", (
        f"DeepSeek must outrank Anthropic in auto, got "
        f"{getattr(llm, 'provider_name', None)!r}"
    )


def test_auto_picks_deepseek_when_openai_also_configured(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """And over OpenAI for the same reason."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")

    from lyra_cli.llm_factory import build_llm

    llm = build_llm("auto")
    assert getattr(llm, "provider_name", None) == "deepseek"


def test_explicit_anthropic_still_wins_over_deepseek(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--llm anthropic`` is not affected by the auto-cascade reorder.

    Promoting DeepSeek's *default* priority must not break users who
    explicitly ask for Anthropic via ``--llm anthropic`` even when
    DeepSeek is also configured.
    """
    pytest.importorskip("anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")

    from lyra_cli.llm_factory import build_llm

    llm = build_llm("anthropic")
    # AnthropicLLM doesn't expose ``provider_name`` so check the type
    # via class name rather than asserting on a missing attribute.
    assert "Anthropic" in type(llm).__name__


def test_describe_selection_auto_advertises_deepseek_when_present(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The status line must match what ``build_llm`` would actually pick.

    Status bars (Phase 5) read this string verbatim — drift between
    ``describe_selection`` and ``build_llm`` would put a stale label
    on screen and confuse users.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")

    from lyra_cli.llm_factory import describe_selection

    label = describe_selection("auto")
    assert label.startswith("deepseek ·"), (
        f"describe_selection('auto') must report deepseek when both "
        f"keys are set, got {label!r}"
    )


def test_known_llm_names_lists_deepseek() -> None:
    """Sanity: DeepSeek remains in the discoverable name list."""
    from lyra_cli.llm_factory import known_llm_names

    assert "deepseek" in known_llm_names()
