"""Tests for :mod:`lyra_cli.provider_registry` (Phase N.8)."""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

from lyra_cli.config_io import LYRA_CONFIG_VERSION, load_settings, save_settings
from lyra_cli.provider_registry import (
    CustomProviderEntry,
    CustomProviderError,
    LYRA_PROVIDERS_CONFIG_VERSION,
    build_provider,
    known_custom_slugs,
    load_registered_providers,
    parse_providers,
    resolve_entry,
)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_providers_returns_empty_when_missing() -> None:
    assert parse_providers({}) == []


def test_parse_providers_ignores_non_dict() -> None:
    assert parse_providers({"providers": [1, 2, 3]}) == []


def test_parse_providers_returns_typed_entries() -> None:
    entries = parse_providers({
        "providers": {"in-house": "mypkg.providers:InHouseLLM"},
    })
    assert len(entries) == 1
    e = entries[0]
    assert e.slug == "in-house"
    assert e.module == "mypkg.providers"
    assert e.symbol == "InHouseLLM"


def test_parse_providers_skips_malformed_strings() -> None:
    entries = parse_providers({
        "providers": {
            "good": "pkg.mod:Sym",
            "bad": "no-colon",
            "empty": "",
        },
    })
    slugs = [e.slug for e in entries]
    assert slugs == ["good"]


def test_parse_providers_skips_non_string_values() -> None:
    entries = parse_providers({"providers": {"slug": 42}})
    assert entries == []


def test_entry_parse_rejects_blank_slug() -> None:
    with pytest.raises(CustomProviderError):
        CustomProviderEntry.parse("", "pkg:Sym")


def test_entry_parse_rejects_missing_module() -> None:
    with pytest.raises(CustomProviderError):
        CustomProviderEntry.parse("slug", ":Sym")


def test_entry_parse_rejects_missing_symbol() -> None:
    with pytest.raises(CustomProviderError):
        CustomProviderEntry.parse("slug", "pkg.mod:")


# ---------------------------------------------------------------------------
# Resolve / build
# ---------------------------------------------------------------------------


def _install_fake_module(monkeypatch: pytest.MonkeyPatch, name: str, source: str) -> ModuleType:
    """Inject a synthetic module so the test doesn't need a real package on PATH."""
    module = ModuleType(name)
    exec(textwrap.dedent(source), module.__dict__)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_resolve_entry_imports_module(monkeypatch) -> None:
    _install_fake_module(monkeypatch, "lyra_test_provider_pkg", """
        class FakeLLM:
            def generate(self, messages):
                return type('Reply', (), {'content': 'ok'})()
    """)
    e = CustomProviderEntry.parse("fake", "lyra_test_provider_pkg:FakeLLM")
    cls = resolve_entry(e)
    assert cls.__name__ == "FakeLLM"


def test_resolve_entry_raises_on_missing_module() -> None:
    e = CustomProviderEntry.parse("missing", "lyra_does_not_exist_pkg:Sym")
    with pytest.raises(CustomProviderError, match="failed to import"):
        resolve_entry(e)


def test_resolve_entry_raises_on_missing_symbol(monkeypatch) -> None:
    _install_fake_module(monkeypatch, "lyra_partial_pkg", """
        class Other:
            pass
    """)
    e = CustomProviderEntry.parse("missing-sym", "lyra_partial_pkg:NotThere")
    with pytest.raises(CustomProviderError, match="has no attribute"):
        resolve_entry(e)


def test_build_provider_instantiates_class(monkeypatch) -> None:
    _install_fake_module(monkeypatch, "lyra_build_pkg", """
        class FakeLLM:
            def __init__(self):
                self.created = True
    """)
    e = CustomProviderEntry.parse("fake", "lyra_build_pkg:FakeLLM")
    instance = build_provider(e)
    assert getattr(instance, "created", False) is True


def test_build_provider_calls_factory_function(monkeypatch) -> None:
    _install_fake_module(monkeypatch, "lyra_factory_pkg", """
        def make():
            return {"factory": "called"}
    """)
    e = CustomProviderEntry.parse("fake", "lyra_factory_pkg:make")
    out = build_provider(e)
    assert out == {"factory": "called"}


def test_build_provider_raises_when_symbol_not_callable(monkeypatch) -> None:
    _install_fake_module(monkeypatch, "lyra_string_pkg", """
        constant = 'just a string'
    """)
    e = CustomProviderEntry.parse("fake", "lyra_string_pkg:constant")
    with pytest.raises(CustomProviderError, match="not callable"):
        build_provider(e)


# ---------------------------------------------------------------------------
# Settings integration
# ---------------------------------------------------------------------------


def test_load_registered_providers_reads_settings(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    save_settings(p, {
        "providers": {"in-house": "mypkg.providers:InHouseLLM"},
    })
    registry = load_registered_providers(p)
    assert "in-house" in registry
    assert registry["in-house"].symbol == "InHouseLLM"


def test_load_registered_providers_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_registered_providers(tmp_path / "nope.json") == {}


def test_known_custom_slugs_sorted(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    save_settings(p, {
        "providers": {
            "zeta": "z.mod:Z",
            "alpha": "a.mod:A",
        },
    })
    assert known_custom_slugs(p) == ["alpha", "zeta"]


# ---------------------------------------------------------------------------
# config_io v1 → v2 migration
# ---------------------------------------------------------------------------


def test_config_io_migrates_v1_to_v2(tmp_path: Path) -> None:
    """An old v1 file should round-trip with ``providers: {}`` added."""
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({
        "config_version": 1,
        "default_provider": "deepseek",
    }))
    settings = load_settings(p)
    assert settings["config_version"] == LYRA_CONFIG_VERSION == 2
    assert settings["providers"] == {}


def test_config_io_preserves_existing_providers(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({
        "config_version": 2,
        "providers": {"foo": "pkg.mod:Sym"},
    }))
    settings = load_settings(p)
    assert settings["providers"] == {"foo": "pkg.mod:Sym"}


def test_config_io_legacy_no_version_gets_v2(tmp_path: Path) -> None:
    """A hand-crafted file without ``config_version`` migrates straight to v2."""
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"default_provider": "anthropic"}))
    settings = load_settings(p)
    assert settings["config_version"] == 2
    assert settings["providers"] == {}


def test_provider_config_constant_matches() -> None:
    """The N.8 config_version constant should track LYRA_CONFIG_VERSION."""
    assert LYRA_PROVIDERS_CONFIG_VERSION == 2


# ---------------------------------------------------------------------------
# llm_factory integration
# ---------------------------------------------------------------------------


def test_known_llm_names_includes_custom_slugs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    save_settings(tmp_path / "settings.json", {
        "providers": {"in-house": "mypkg.providers:InHouseLLM"},
    })

    from lyra_cli.llm_factory import known_llm_names

    names = known_llm_names()
    assert "in-house" in names


def test_build_llm_dispatches_to_custom_provider(tmp_path: Path, monkeypatch) -> None:
    """``--llm <slug>`` for a registered custom provider must route there."""
    _install_fake_module(monkeypatch, "lyra_inhouse_pkg", """
        class FakeLLM:
            def __init__(self):
                self.flag = 'ok'
            def generate(self, messages):
                return type('Reply', (), {'content': 'fake'})()
    """)
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    save_settings(tmp_path / "settings.json", {
        "providers": {"in-house": "lyra_inhouse_pkg:FakeLLM"},
    })

    # Strip provider-cascade env vars so auto would otherwise fail —
    # the test must prove that the custom slug short-circuits correctly.
    for n in (
        "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(n, raising=False)

    from lyra_cli.llm_factory import build_llm

    llm = build_llm("in-house")
    assert getattr(llm, "flag", None) == "ok"
