"""Tests for per-provider layout metadata (Phase CE.3, P2-1)."""
from __future__ import annotations

from lyra_core.context.provider_layouts import (
    ANTHROPIC,
    CACHE_STYLE_EXPLICIT,
    CACHE_STYLE_IMPLICIT,
    CACHE_STYLE_KV_LOCAL,
    CACHE_STYLE_RESOURCE,
    DEFAULT,
    GEMINI,
    OLLAMA,
    OPENAI,
    SOUL_ROLE_DEVELOPER,
    SOUL_ROLE_SYSTEM,
    VLLM,
    get_layout,
    list_layouts,
    supports_explicit_cache,
)


def test_anthropic_uses_explicit_cache_with_breakpoints():
    assert ANTHROPIC.cache_style == CACHE_STYLE_EXPLICIT
    assert ANTHROPIC.cache_breakpoints == 4


def test_openai_uses_implicit_cache_and_developer_role():
    assert OPENAI.cache_style == CACHE_STYLE_IMPLICIT
    assert OPENAI.cache_breakpoints == 0
    assert OPENAI.soul_role == SOUL_ROLE_DEVELOPER


def test_gemini_prefers_single_system_message():
    assert GEMINI.prefers_single_system is True
    assert GEMINI.cache_style == CACHE_STYLE_RESOURCE


def test_local_providers_use_kv_local_style():
    for layout in (OLLAMA, VLLM):
        assert layout.cache_style == CACHE_STYLE_KV_LOCAL
        assert layout.cache_breakpoints == 0


def test_default_is_safe_subset():
    assert DEFAULT.cache_style == CACHE_STYLE_IMPLICIT
    assert DEFAULT.soul_role == SOUL_ROLE_SYSTEM


def test_get_layout_known_names():
    assert get_layout("anthropic") is ANTHROPIC
    assert get_layout("OpenAI") is OPENAI
    assert get_layout("  gemini  ") is GEMINI


def test_get_layout_unknown_returns_default():
    assert get_layout("paranoid-vendor") is DEFAULT
    assert get_layout(None) is DEFAULT
    assert get_layout("") is DEFAULT


def test_list_layouts_returns_all_registered():
    names = {l.provider for l in list_layouts()}
    assert names == {"anthropic", "openai", "gemini", "ollama", "vllm"}


def test_supports_explicit_cache_predicate():
    assert supports_explicit_cache("anthropic") is True
    assert supports_explicit_cache("openai") is False
    assert supports_explicit_cache("gemini") is False
    assert supports_explicit_cache(None) is False


def test_layouts_are_frozen():
    import pytest

    with pytest.raises(Exception):
        ANTHROPIC.cache_style = CACHE_STYLE_IMPLICIT  # type: ignore[misc]


def test_max_tools_respected_where_known():
    # Anthropic and OpenAI have soft caps; locals don't.
    assert ANTHROPIC.max_tools == 64
    assert OPENAI.max_tools == 128
    assert OLLAMA.max_tools is None


def test_provider_names_are_lowercase_canonical():
    for layout in list_layouts():
        assert layout.provider == layout.provider.lower()
        assert " " not in layout.provider
