"""Phase 2 — ``qwen`` is a first-class provider name (peer of ``dashscope``).

Pre-Phase-2, callers had to know that Alibaba's OpenAI-compatible
endpoint was named ``dashscope`` in the registry; a user thinking
"I want to use Qwen" got a "no such preset" error. Phase 2 adds a
``qwen`` preset that points at the same endpoint with model-aware
defaults (``qwen-plus``) and an extra env-var alias (``QWEN_API_KEY``)
so muscle memory works either way.

The legacy ``dashscope`` preset stays for back-compat — anyone scripting
``--llm dashscope`` keeps working without churn.
"""
from __future__ import annotations

import pytest

from lyra_cli.llm_factory import known_llm_names
from lyra_cli.providers.openai_compatible import preset_by_name


def test_qwen_in_known_llm_names() -> None:
    """``--llm qwen`` is a public name; it shows up in ``known_llm_names``.

    The CLI's ``--help`` and shell-completion both read from this
    function, so being absent here is the same as not existing.
    """
    assert "qwen" in known_llm_names()


def test_qwen_resolves_to_dashscope_endpoint() -> None:
    """``preset_by_name('qwen')`` returns a real preset on the same URL.

    The alias from Phase 1 was a build-time string substitution; Phase
    2 promotes it to a real registry entry so ``configured_presets``
    iteration treats Qwen as a peer, not a hidden alias.
    """
    p = preset_by_name("qwen")
    assert p is not None, "qwen preset must be registered"
    assert p.base_url.startswith("https://dashscope"), (
        f"qwen preset must point at the DashScope endpoint, got "
        f"{p.base_url!r}"
    )
    # Both env-var names must be readable so users can pick whichever
    # matches their muscle memory.
    assert "DASHSCOPE_API_KEY" in p.env_keys
    assert "QWEN_API_KEY" in p.env_keys


def test_qwen_default_model_is_qwen_plus() -> None:
    """The default Qwen model is ``qwen-plus`` (Alibaba's mid-tier coder)."""
    p = preset_by_name("qwen")
    assert p is not None
    assert p.default_model == "qwen-plus"


def test_dashscope_alias_still_works_for_back_compat() -> None:
    """``preset_by_name('dashscope')`` keeps returning a usable preset.

    Anyone scripting against the old name (or who set
    ``DASHSCOPE_API_KEY`` instead of ``QWEN_API_KEY``) doesn't break.
    """
    p = preset_by_name("dashscope")
    assert p is not None
    assert p.base_url.startswith("https://dashscope")


def test_qwen_reads_qwen_api_key_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting ``QWEN_API_KEY`` (and not ``DASHSCOPE_API_KEY``) configures qwen.

    The whole point of the alias is letting users pick the env name
    that matches how they think about the product.
    """
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_API_KEY", "qwen-test")

    p = preset_by_name("qwen")
    assert p is not None
    assert p.read_api_key() == "qwen-test"


def test_describe_selection_qwen_shows_qwen_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``describe_selection('qwen')`` advertises ``qwen``, not ``dashscope``.

    Status bars / ``lyra doctor`` should match what the user typed.
    """
    monkeypatch.setenv("QWEN_API_KEY", "qwen-test")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    from lyra_cli.llm_factory import describe_selection

    label = describe_selection("qwen")
    assert label.startswith("qwen ·"), (
        f"describe_selection('qwen') should advertise 'qwen', got {label!r}"
    )
    assert "qwen-plus" in label or "qwen" in label.lower()
