"""Contract tests for the foreign-cred sniffer.

Generalises claw-code's ``anthropic_missing_credentials_hint`` across
every provider Lyra supports. When the user asks for provider X and
X's key is missing, we surface the most likely fix based on what other
keys ARE set in the environment.
"""
from __future__ import annotations

import pytest

from lyra_core.providers.auth_hints import KNOWN_FOREIGN_CREDS, missing_credential_hint


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for cred in KNOWN_FOREIGN_CREDS:
        monkeypatch.delenv(cred.env_var, raising=False)


def test_clean_env_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    assert missing_credential_hint(asking="anthropic") is None


def test_openai_key_present_when_asking_anthropic_returns_openai_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    hint = missing_credential_hint(asking="anthropic")
    assert hint is not None
    assert "OPENAI_API_KEY is set" in hint
    assert "openai/" in hint


def test_xai_key_present_when_asking_anthropic_returns_xai_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    hint = missing_credential_hint(asking="anthropic")
    assert hint is not None
    assert "XAI_API_KEY is set" in hint
    assert "grok" in hint


def test_empty_string_value_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    assert missing_credential_hint(asking="anthropic") is None


def test_asking_openai_with_anthropic_set_returns_anthropic_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    hint = missing_credential_hint(asking="openai")
    assert hint is not None
    assert "ANTHROPIC_API_KEY is set" in hint
    assert "anthropic/" in hint or "claude-" in hint


def test_asking_dashscope_with_openai_set_returns_openai_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    hint = missing_credential_hint(asking="dashscope")
    assert hint is not None
    assert "OPENAI_API_KEY" in hint


def test_multiple_foreign_creds_returns_first_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    hint = missing_credential_hint(asking="anthropic")
    assert hint is not None
    assert "OPENAI_API_KEY" in hint
    assert "XAI_API_KEY" not in hint  # first match wins, stays focused


def test_asking_for_unknown_provider_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert missing_credential_hint(asking="not-a-real-provider") is None
