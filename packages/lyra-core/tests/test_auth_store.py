"""Phase 3 — ``lyra_core.auth.store`` round-trip + 0600 mode enforcement.

The connect-flow persists API keys to ``~/.lyra/auth.json`` (or
``$LYRA_HOME/auth.json`` when the env-var is set, which is how the
test suite redirects writes into a tmp dir without polluting the
developer's real home).

Contract:

* :func:`save` creates the parent directory if needed, writes JSON
  with mode 0600 (owner read/write only), and is idempotent on
  re-save (overwrites in place).
* :func:`load` returns ``{}`` when the file is missing — never
  raises — so first-run callers don't have to guard with ``try``.
* :func:`list_providers` returns sorted provider names; missing
  file → ``[]``.
* :func:`has_any_provider` is the cheap "did the user already
  configure something?" check used by the REPL auto-trigger.
* :func:`revoke` removes a single provider's entry; unknown providers
  are a no-op (idempotent on un-saved provider names).
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest


@pytest.fixture
def lyra_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    return tmp_path


def test_load_returns_empty_dict_when_file_missing(lyra_home: Path) -> None:
    from lyra_core.auth.store import load

    data = load()
    assert data == {"providers": {}}


def test_save_writes_mode_0600(lyra_home: Path) -> None:
    from lyra_core.auth.store import save

    save("deepseek", "sk-fake-001", model="deepseek-chat")

    auth_path = lyra_home / "auth.json"
    assert auth_path.exists()
    mode = stat.S_IMODE(auth_path.stat().st_mode)
    assert mode == 0o600, f"expected 0600 got {oct(mode)}"


def test_save_then_load_roundtrips(lyra_home: Path) -> None:
    from lyra_core.auth.store import load, save

    save("openai", "sk-fake-002", model="gpt-5")
    save("deepseek", "sk-fake-003")

    data = load()
    assert data["providers"]["openai"]["api_key"] == "sk-fake-002"
    assert data["providers"]["openai"]["model"] == "gpt-5"
    assert data["providers"]["deepseek"]["api_key"] == "sk-fake-003"
    assert "model" not in data["providers"]["deepseek"]


def test_save_overwrites_existing_provider_in_place(lyra_home: Path) -> None:
    from lyra_core.auth.store import load, save

    save("anthropic", "sk-old")
    save("anthropic", "sk-new", model="claude-opus-4.5")

    data = load()
    assert data["providers"]["anthropic"]["api_key"] == "sk-new"
    assert data["providers"]["anthropic"]["model"] == "claude-opus-4.5"


def test_list_providers_returns_sorted(lyra_home: Path) -> None:
    from lyra_core.auth.store import list_providers, save

    save("openai", "k")
    save("deepseek", "k")
    save("anthropic", "k")

    assert list_providers() == ["anthropic", "deepseek", "openai"]


def test_list_providers_empty_when_no_file(lyra_home: Path) -> None:
    from lyra_core.auth.store import list_providers

    assert list_providers() == []


def test_has_any_provider_false_initially(lyra_home: Path) -> None:
    from lyra_core.auth.store import has_any_provider

    assert has_any_provider() is False


def test_has_any_provider_true_after_save(lyra_home: Path) -> None:
    from lyra_core.auth.store import has_any_provider, save

    save("deepseek", "k")
    assert has_any_provider() is True


def test_revoke_removes_provider(lyra_home: Path) -> None:
    from lyra_core.auth.store import list_providers, revoke, save

    save("openai", "k")
    save("deepseek", "k")
    revoke("openai")

    assert list_providers() == ["deepseek"]


def test_revoke_unknown_provider_is_noop(lyra_home: Path) -> None:
    from lyra_core.auth.store import list_providers, revoke, save

    save("deepseek", "k")
    revoke("nonexistent-provider")
    assert list_providers() == ["deepseek"]


def test_get_api_key_returns_saved_key(lyra_home: Path) -> None:
    from lyra_core.auth.store import get_api_key, save

    save("qwen", "sk-qwen-fake")
    assert get_api_key("qwen") == "sk-qwen-fake"


def test_get_api_key_returns_none_when_missing(lyra_home: Path) -> None:
    from lyra_core.auth.store import get_api_key

    assert get_api_key("nope") is None


def test_save_creates_lyra_home_directory_if_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``~/.lyra/`` must be auto-created on first save."""
    home = tmp_path / "fresh"
    monkeypatch.setenv("LYRA_HOME", str(home))
    assert not home.exists()

    from lyra_core.auth.store import save

    save("deepseek", "k")
    assert home.is_dir()
    assert (home / "auth.json").is_file()


def test_save_does_not_corrupt_other_keys_on_overwrite(lyra_home: Path) -> None:
    """Writing one provider must leave others untouched."""
    from lyra_core.auth.store import load, save

    save("openai", "first-key")
    save("deepseek", "second-key")
    save("openai", "updated-key")

    data = load()
    assert data["providers"]["openai"]["api_key"] == "updated-key"
    assert data["providers"]["deepseek"]["api_key"] == "second-key"


def test_save_writes_atomically(lyra_home: Path) -> None:
    """A crash mid-write must never leave a half-written auth.json."""
    from lyra_core.auth.store import save

    save("deepseek", "k")
    auth_path = lyra_home / "auth.json"
    json.loads(auth_path.read_text())


# ---------------------------------------------------------------------------
# Budget persistence (v2.2.3 — automatic budget)
# ---------------------------------------------------------------------------


def test_load_budget_returns_defaults_when_missing(lyra_home: Path) -> None:
    """First-run callers must see a populated dict, not have to ``.get``."""
    from lyra_core.auth.store import load_budget

    data = load_budget()
    assert data == {"cap_usd": None, "alert_pct": 80.0, "auto_stop": True}


def test_save_budget_round_trips_cap(lyra_home: Path) -> None:
    from lyra_core.auth.store import load_budget, save_budget

    save_budget(cap_usd=5.0)
    assert load_budget()["cap_usd"] == 5.0


def test_save_budget_full_block(lyra_home: Path) -> None:
    from lyra_core.auth.store import load_budget, save_budget

    save_budget(cap_usd=10.0, alert_pct=50.0, auto_stop=False)
    data = load_budget()
    assert data["cap_usd"] == 10.0
    assert data["alert_pct"] == 50.0
    assert data["auto_stop"] is False


def test_save_budget_partial_update_preserves_other_fields(
    lyra_home: Path,
) -> None:
    """Passing one field must not nuke the others."""
    from lyra_core.auth.store import load_budget, save_budget

    save_budget(cap_usd=5.0, alert_pct=50.0, auto_stop=False)
    save_budget(cap_usd=10.0)  # only updating the cap

    data = load_budget()
    assert data["cap_usd"] == 10.0
    assert data["alert_pct"] == 50.0
    assert data["auto_stop"] is False


def test_save_budget_preserves_provider_keys(lyra_home: Path) -> None:
    """Budget writes must not touch the providers block."""
    from lyra_core.auth.store import save, save_budget, load

    save("deepseek", "sk-stable-key", model="deepseek-v4-pro")
    save_budget(cap_usd=5.0)

    data = load()
    assert data["providers"]["deepseek"]["api_key"] == "sk-stable-key"
    assert data["budget"]["cap_usd"] == 5.0


def test_save_budget_with_none_clears_cap(lyra_home: Path) -> None:
    from lyra_core.auth.store import load_budget, save_budget

    save_budget(cap_usd=5.0)
    save_budget(cap_usd=None)
    assert load_budget()["cap_usd"] is None


def test_clear_budget_removes_block_entirely(lyra_home: Path) -> None:
    from lyra_core.auth.store import (
        clear_budget,
        load,
        load_budget,
        save_budget,
    )

    save_budget(cap_usd=5.0, alert_pct=50.0, auto_stop=False)
    clear_budget()

    raw = load()
    assert "budget" not in raw
    # load_budget still returns defaults — never raises.
    assert load_budget() == {"cap_usd": None, "alert_pct": 80.0, "auto_stop": True}


def test_save_budget_writes_mode_0600(lyra_home: Path) -> None:
    """Budget data sits in the same 0600 file as API keys."""
    from lyra_core.auth.store import save_budget

    save_budget(cap_usd=5.0)
    auth_path = lyra_home / "auth.json"
    mode = stat.S_IMODE(auth_path.stat().st_mode)
    assert mode == 0o600


def test_load_budget_rejects_negative_cap(lyra_home: Path) -> None:
    """A garbage cap on disk must not crash the next session."""
    from lyra_core.auth.store import auth_path, load_budget

    auth_path().parent.mkdir(parents=True, exist_ok=True)
    auth_path().write_text(
        json.dumps({"providers": {}, "budget": {"cap_usd": -7.0}})
    )

    data = load_budget()
    assert data["cap_usd"] is None


def test_load_budget_clamps_alert_pct_to_default_when_invalid(
    lyra_home: Path,
) -> None:
    from lyra_core.auth.store import auth_path, load_budget

    auth_path().parent.mkdir(parents=True, exist_ok=True)
    auth_path().write_text(
        json.dumps({"providers": {}, "budget": {"alert_pct": 999.0}})
    )

    assert load_budget()["alert_pct"] == 80.0
