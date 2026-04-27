"""Plugin override for model max_output_tokens.

Mirrors claw-code's ``max_tokens_for_model_with_override``: a user can
bump the per-turn output limit for every model via
``~/.lyra/settings.json``'s ``plugins.maxOutputTokens`` without
editing code. A value of ``None`` falls back to the model's registered
default.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.providers.registry import (
    get_provider,
    max_tokens_for_model,
    max_tokens_for_model_with_override,
    plugin_max_output_tokens,
)


def test_default_when_no_override() -> None:
    assert max_tokens_for_model("claude-opus-4.5") == 32_000


def test_explicit_override_wins() -> None:
    assert max_tokens_for_model_with_override("claude-opus-4.5", 12_345) == 12_345


def test_none_override_falls_back_to_model_default() -> None:
    assert (
        max_tokens_for_model_with_override("claude-opus-4.5", None)
        == max_tokens_for_model("claude-opus-4.5")
    )


def test_zero_override_is_rejected() -> None:
    with pytest.raises(ValueError):
        max_tokens_for_model_with_override("claude-opus-4.5", 0)


def test_negative_override_is_rejected() -> None:
    with pytest.raises(ValueError):
        max_tokens_for_model_with_override("claude-opus-4.5", -1)


def test_override_applied_even_to_unknown_model() -> None:
    assert max_tokens_for_model_with_override("totally-fake-model", 5_000) == 5_000


def test_plugin_max_output_tokens_reads_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text('{"plugins": {"maxOutputTokens": 24000}}')
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    assert plugin_max_output_tokens() == 24_000


def test_plugin_max_output_tokens_returns_none_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    assert plugin_max_output_tokens() is None


def test_plugin_max_output_tokens_returns_none_when_malformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "settings.json").write_text("not-json")
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    assert plugin_max_output_tokens() is None


def test_get_provider_roundtrip_is_stable() -> None:
    spec = get_provider("anthropic")
    assert spec is not None
    assert spec.key == "anthropic"
