"""Contract tests for the model-alias registry.

Short names (``opus``, ``sonnet``, ``haiku``, ``grok``, ``kimi``) that
claw-code / hermes users expect should resolve to Lyra's canonical
slugs. Adding an alias should be a one-line registration; removing one
should be safe (resolution falls back to the input).
"""
from __future__ import annotations

import pytest

from lyra_core.providers.aliases import (
    AliasRegistry,
    DEFAULT_ALIASES,
    register_alias,
    resolve_alias,
)


def test_resolves_opus_to_current_claude_slug() -> None:
    assert resolve_alias("opus") == "claude-opus-4.5"


def test_resolves_sonnet_to_current_slug() -> None:
    assert resolve_alias("sonnet") == "claude-sonnet-4.5"


def test_resolves_haiku_to_current_slug() -> None:
    assert resolve_alias("haiku") == "claude-haiku-4"


def test_resolves_grok_aliases() -> None:
    assert resolve_alias("grok") == "grok-4"
    assert resolve_alias("grok-mini") == "grok-4-mini"


def test_resolves_kimi_aliases() -> None:
    assert resolve_alias("kimi") == "kimi-k2.5"
    assert resolve_alias("kimi-k1.5") == "kimi-k1.5"


def test_resolve_is_case_insensitive() -> None:
    assert resolve_alias("OPUS") == resolve_alias("opus")
    assert resolve_alias("Grok-Mini") == resolve_alias("grok-mini")


def test_unknown_alias_falls_back_to_input() -> None:
    assert resolve_alias("some-unknown-slug") == "some-unknown-slug"


def test_trims_whitespace() -> None:
    assert resolve_alias("  opus  ") == "claude-opus-4.5"


def test_custom_registry_isolated_from_default() -> None:
    reg = AliasRegistry()
    reg.register("foo", "foo-canonical-1")
    assert reg.resolve("foo") == "foo-canonical-1"
    assert resolve_alias("foo") == "foo"


def test_register_alias_persists_in_default_registry() -> None:
    register_alias("test-alias-sentinel", "test-canonical-1")
    try:
        assert resolve_alias("test-alias-sentinel") == "test-canonical-1"
    finally:
        DEFAULT_ALIASES._aliases.pop("test-alias-sentinel", None)


def test_provider_key_for_resolves_to_expected_bucket() -> None:
    from lyra_core.providers.aliases import provider_key_for
    assert provider_key_for("opus") == "anthropic"
    assert provider_key_for("grok") == "xai"
    assert provider_key_for("kimi") == "dashscope"
    assert provider_key_for("unknown") is None


# ---------------------------------------------------------------------------
# v2.7.1: DeepSeek small/smart split. The user-facing ``deepseek-v4-flash``
# / ``deepseek-v4-pro`` aliases are what the REPL exposes via ``/model
# fast=...`` and ``/model smart=...``; they MUST resolve to the real
# DeepSeek API slugs (``deepseek-chat`` for general/V3.x, ``deepseek-
# reasoner`` for R1) so the openai-compatible ``deepseek`` preset can
# pick them up via DEEPSEEK_MODEL.
# ---------------------------------------------------------------------------


def test_deepseek_v4_flash_resolves_to_deepseek_chat() -> None:
    """``deepseek-v4-flash`` is the user-facing alias for the cheap slot."""
    from lyra_core.providers.aliases import provider_key_for, resolve_alias

    assert resolve_alias("deepseek-v4-flash") == "deepseek-chat"
    assert provider_key_for("deepseek-v4-flash") == "deepseek"


def test_deepseek_v4_pro_resolves_to_deepseek_reasoner() -> None:
    """``deepseek-v4-pro`` is the user-facing alias for the smart slot."""
    from lyra_core.providers.aliases import provider_key_for, resolve_alias

    assert resolve_alias("deepseek-v4-pro") == "deepseek-reasoner"
    assert provider_key_for("deepseek-v4-pro") == "deepseek"


def test_deepseek_short_aliases_also_resolve() -> None:
    """``deepseek-flash``/``deepseek-pro`` (no ``v4-``) work for terseness."""
    assert resolve_alias("deepseek-flash") == "deepseek-chat"
    assert resolve_alias("deepseek-pro") == "deepseek-reasoner"


def test_deepseek_chat_and_reasoner_are_identity_aliases() -> None:
    """Pasting the raw API slug should round-trip without translation."""
    assert resolve_alias("deepseek-chat") == "deepseek-chat"
    assert resolve_alias("deepseek-reasoner") == "deepseek-reasoner"


def test_deepseek_aliases_are_case_insensitive() -> None:
    assert resolve_alias("DeepSeek-V4-Flash") == "deepseek-chat"
    assert resolve_alias("DEEPSEEK-V4-PRO") == "deepseek-reasoner"


def test_deepseek_coder_routes_to_chat_for_now() -> None:
    """``deepseek-coder`` is currently a sibling of ``deepseek-chat``.

    DeepSeek folded the coder model into the chat catalog; we keep the
    alias for back-compat with users who pinned ``deepseek-coder`` in
    older lyra setups.
    """
    assert resolve_alias("deepseek-coder") == "deepseek-chat"


# ---------------------------------------------------------------------------
# Future-proof DeepSeek versions: any ``deepseek-vN-{pro|flash|...}`` should
# resolve to the canonical API slug without requiring a code change every
# time DeepSeek bumps the version. The pro/reasoner/smart family routes to
# ``deepseek-reasoner`` (R1-class); flash/chat/fast/coder routes to
# ``deepseek-chat`` (V3-class). Decimal versions (v3.1, v4.5) work too.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alias",
    [
        "deepseek-v5-pro",
        "deepseek-v6-pro",
        "deepseek-v10-pro",
        "deepseek-v5-reasoner",
        "deepseek-v5-smart",
        "deepseek-v3.1-pro",
        "deepseek-v4.5-pro",
    ],
)
def test_deepseek_future_pro_versions_resolve_to_reasoner(alias: str) -> None:
    from lyra_core.providers.aliases import provider_key_for, resolve_alias

    assert resolve_alias(alias) == "deepseek-reasoner"
    assert provider_key_for(alias) == "deepseek"


@pytest.mark.parametrize(
    "alias",
    [
        "deepseek-v5-flash",
        "deepseek-v6-flash",
        "deepseek-v10-flash",
        "deepseek-v5-chat",
        "deepseek-v5-fast",
        "deepseek-v5-coder",
        "deepseek-v3.1-flash",
    ],
)
def test_deepseek_future_flash_versions_resolve_to_chat(alias: str) -> None:
    from lyra_core.providers.aliases import provider_key_for, resolve_alias

    assert resolve_alias(alias) == "deepseek-chat"
    assert provider_key_for(alias) == "deepseek"


def test_deepseek_versioned_aliases_are_case_insensitive() -> None:
    assert resolve_alias("DeepSeek-V5-PRO") == "deepseek-reasoner"
    assert resolve_alias("DEEPSEEK-V7-FLASH") == "deepseek-chat"


def test_deepseek_unrecognized_suffix_falls_back_to_input() -> None:
    """``v5-banana`` is not in the pro/flash family — leave it alone.

    Falling back means the eventual API call surfaces the real DeepSeek
    error rather than silently misrouting to the wrong model.
    """
    assert resolve_alias("deepseek-v5-banana") == "deepseek-v5-banana"


def test_register_pattern_extends_default_registry() -> None:
    """Users / plugins can add their own version pattern at runtime."""
    from lyra_core.providers.aliases import (
        DEFAULT_ALIASES,
        register_pattern,
        resolve_alias,
    )

    register_pattern(r"^myco-v\d+-fast$", "myco-cheap", provider="myco")
    try:
        assert resolve_alias("myco-v9-fast") == "myco-cheap"
    finally:
        DEFAULT_ALIASES._patterns = [
            (p, e) for p, e in DEFAULT_ALIASES._patterns if "myco" not in p.pattern
        ]


def test_custom_registry_does_not_inherit_default_patterns() -> None:
    """A fresh ``AliasRegistry()`` starts empty, including patterns.

    Mirrors the existing isolation contract for ``register()``.
    """
    reg = AliasRegistry()
    assert reg.resolve("deepseek-v5-pro") == "deepseek-v5-pro"


def test_explicit_alias_wins_over_pattern() -> None:
    """An exact-match alias must take precedence over a regex pattern.

    If a future DeepSeek release ships a real ``deepseek-v5-pro`` slug,
    we want to be able to register it directly and have it stop routing
    through the generic pattern.
    """
    reg = AliasRegistry()
    reg.register_pattern(r"^foo-v\d+$", "foo-canonical", provider="foo")
    reg.register("foo-v3", "foo-special", provider="foo")
    assert reg.resolve("foo-v3") == "foo-special"
    assert reg.resolve("foo-v9") == "foo-canonical"
