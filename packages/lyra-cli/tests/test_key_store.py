"""Tests for KeyStore — ~/.lyra/credentials.json management."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lyra_cli.interactive.key_store import KeyStore, _mask


@pytest.fixture()
def store(tmp_path: Path) -> KeyStore:
    return KeyStore(path=tmp_path / "credentials.json")


# ---- set / get / remove / list_all ----------------------------------------


def test_set_creates_file(store: KeyStore, tmp_path: Path) -> None:
    store.set("anthropic", "sk-ant-test")
    assert (tmp_path / "credentials.json").exists()


def test_set_and_get_roundtrip(store: KeyStore) -> None:
    store.set("anthropic", "sk-ant-test")
    entry = store.get("anthropic")
    assert entry is not None
    assert entry["api_key"] == "sk-ant-test"


def test_set_with_base_url(store: KeyStore) -> None:
    store.set("openai", "sk-test", base_url="https://my-proxy.com/v1")
    entry = store.get("openai")
    assert entry is not None
    assert entry["base_url"] == "https://my-proxy.com/v1"


def test_get_returns_none_for_missing(store: KeyStore) -> None:
    assert store.get("nonexistent") is None


def test_set_overwrites_existing(store: KeyStore) -> None:
    store.set("anthropic", "old-key")
    store.set("anthropic", "new-key")
    assert store.get("anthropic")["api_key"] == "new-key"


def test_remove_returns_true_when_existed(store: KeyStore) -> None:
    store.set("openai", "sk-test")
    assert store.remove("openai") is True


def test_remove_returns_false_for_missing(store: KeyStore) -> None:
    assert store.remove("nonexistent") is False


def test_remove_deletes_entry(store: KeyStore) -> None:
    store.set("openai", "sk-test")
    store.remove("openai")
    assert store.get("openai") is None


def test_list_all_empty(store: KeyStore) -> None:
    assert store.list_all() == {}


def test_list_all_returns_all_entries(store: KeyStore) -> None:
    store.set("anthropic", "sk-ant")
    store.set("openai", "sk-oai")
    entries = store.list_all()
    assert set(entries.keys()) == {"anthropic", "openai"}


def test_list_all_returns_copies(store: KeyStore) -> None:
    store.set("anthropic", "sk-ant")
    entries = store.list_all()
    entries["anthropic"]["api_key"] = "mutated"
    assert store.get("anthropic")["api_key"] == "sk-ant"


def test_file_is_valid_json(store: KeyStore, tmp_path: Path) -> None:
    store.set("anthropic", "sk-ant")
    raw = json.loads((tmp_path / "credentials.json").read_text())
    assert "providers" in raw
    assert raw["providers"]["anthropic"]["api_key"] == "sk-ant"


# ---- hydrate_env -----------------------------------------------------------


def test_hydrate_env_sets_known_env_var(store: KeyStore, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    store.set("anthropic", "sk-ant-hydrate")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # undo stamp from set
    store.hydrate_env()
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-hydrate"


def test_hydrate_env_does_not_overwrite_existing(store: KeyStore, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "original")
    store.set("anthropic", "sk-ant-new")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "original")  # restore after set()
    store.hydrate_env()
    assert os.environ.get("ANTHROPIC_API_KEY") == "original"


def test_hydrate_env_sets_base_url(store: KeyStore, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    store.set("anthropic", "sk-ant", base_url="https://proxy.example.com")
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    store.hydrate_env()
    assert os.environ.get("ANTHROPIC_BASE_URL") == "https://proxy.example.com"


def test_hydrate_env_unknown_provider_is_noop(store: KeyStore) -> None:
    # Should not raise even for providers not in the env-var map.
    store.set("custom-llm", "key-123")
    store.hydrate_env()  # no crash


# ---- _mask -----------------------------------------------------------------


def test_mask_long_key() -> None:
    assert _mask("sk-ant-ap01XYZ1234") == "****1234"


def test_mask_short_key() -> None:
    assert _mask("abc") == "****"


def test_mask_exactly_8_chars() -> None:
    assert _mask("12345678") == "****5678"


def test_mask_9_chars() -> None:
    result = _mask("123456789")
    assert result == "****6789"


# ---- tolerates corrupt/missing file ----------------------------------------


def test_load_missing_file_returns_empty(store: KeyStore) -> None:
    assert store.list_all() == {}


def test_load_corrupt_file_returns_empty(store: KeyStore, tmp_path: Path) -> None:
    (tmp_path / "credentials.json").write_text("not json!!!")
    assert store.list_all() == {}


def test_load_wrong_schema_returns_empty(store: KeyStore, tmp_path: Path) -> None:
    (tmp_path / "credentials.json").write_text('"just a string"')
    assert store.list_all() == {}
