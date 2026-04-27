"""Phase 3 — ``lyra connect`` non-interactive contract.

The interactive picker (Rich + prompt_toolkit) is harder to test than
it's worth; the picker contract is exercised separately in
``test_dialog_provider.py``. Here we lock down the non-interactive
``--key`` path that backs CI invocations and headless setup scripts:

* ``lyra connect deepseek --key sk-fake --no-prompt`` writes
  ``$LYRA_HOME/auth.json`` with mode 0600 and exits 0.
* Preflight is mocked to ``ok=True`` (so we don't need network) and
  ``ok=False`` (so we lock down the failure path).
* Unknown providers fail with exit code 2 and a friendly message
  rather than dumping a traceback.
* ``--revoke`` removes a saved provider.
* ``--list`` prints every saved provider name.
"""
from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def lyra_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def stub_preflight_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch preflight to always return ``ok=True``."""
    from lyra_core.auth.preflight import PreflightResult

    def _ok(provider: str, api_key: str, *, timeout: float = 5.0) -> PreflightResult:
        return PreflightResult(
            ok=True, provider=provider, detail="", model_count=3
        )

    monkeypatch.setattr("lyra_core.auth.preflight.preflight", _ok)
    monkeypatch.setattr("lyra_cli.commands.connect.preflight", _ok)


@pytest.fixture
def stub_preflight_bad_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from lyra_core.auth.preflight import PreflightResult

    def _bad(provider: str, api_key: str, *, timeout: float = 5.0) -> PreflightResult:
        return PreflightResult(
            ok=False,
            provider=provider,
            detail="invalid api key (HTTP 401)",
            model_count=None,
        )

    monkeypatch.setattr("lyra_core.auth.preflight.preflight", _bad)
    monkeypatch.setattr("lyra_cli.commands.connect.preflight", _bad)


def _invoke(*args: str):
    """Invoke the Typer app and return the click.testing.Result."""
    from lyra_cli.__main__ import app

    return runner.invoke(app, list(args))


def test_connect_with_key_writes_authjson(
    lyra_home: Path, stub_preflight_ok: None
) -> None:
    result = _invoke("connect", "deepseek", "--key", "sk-fake-001", "--no-prompt")
    assert result.exit_code == 0, result.output

    auth_path = lyra_home / "auth.json"
    assert auth_path.exists()
    mode = stat.S_IMODE(auth_path.stat().st_mode)
    assert mode == 0o600

    data = json.loads(auth_path.read_text())
    assert data["providers"]["deepseek"]["api_key"] == "sk-fake-001"


def test_connect_skip_preflight_writes_anyway(
    lyra_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--no-preflight`` saves without round-tripping (useful offline)."""
    sentinel = {"called": False}

    def _explode(*a, **k):
        sentinel["called"] = True
        raise AssertionError("preflight must NOT be called with --no-preflight")

    monkeypatch.setattr("lyra_core.auth.preflight.preflight", _explode)
    monkeypatch.setattr("lyra_cli.commands.connect.preflight", _explode)

    result = _invoke(
        "connect", "deepseek", "--key", "sk-fake", "--no-prompt", "--no-preflight"
    )
    assert result.exit_code == 0, result.output
    assert sentinel["called"] is False
    assert (lyra_home / "auth.json").exists()


def test_connect_failed_preflight_does_not_save(
    lyra_home: Path, stub_preflight_bad_key: None
) -> None:
    result = _invoke(
        "connect", "deepseek", "--key", "sk-bad", "--no-prompt"
    )
    assert result.exit_code != 0
    assert "invalid api key" in result.output.lower()
    assert not (lyra_home / "auth.json").exists()


def test_connect_unknown_provider_fails(lyra_home: Path) -> None:
    result = _invoke(
        "connect", "not-a-real-thing", "--key", "k", "--no-prompt"
    )
    assert result.exit_code != 0
    assert (
        "unknown" in result.output.lower()
        or "not supported" in result.output.lower()
    )


def test_connect_list_prints_saved_providers(
    lyra_home: Path, stub_preflight_ok: None
) -> None:
    _invoke("connect", "deepseek", "--key", "k", "--no-prompt")
    _invoke("connect", "openai", "--key", "k", "--no-prompt")

    result = _invoke("connect", "--list")
    assert result.exit_code == 0
    assert "deepseek" in result.output
    assert "openai" in result.output


def test_connect_revoke_removes_provider(
    lyra_home: Path, stub_preflight_ok: None
) -> None:
    _invoke("connect", "deepseek", "--key", "k", "--no-prompt")
    _invoke("connect", "openai", "--key", "k", "--no-prompt")

    result = _invoke("connect", "deepseek", "--revoke")
    assert result.exit_code == 0

    from lyra_core.auth.store import list_providers

    assert "deepseek" not in list_providers()
    assert "openai" in list_providers()


def test_connect_overwrite_with_new_key(
    lyra_home: Path, stub_preflight_ok: None
) -> None:
    _invoke("connect", "deepseek", "--key", "old-key", "--no-prompt")
    _invoke("connect", "deepseek", "--key", "new-key", "--no-prompt")

    from lyra_core.auth.store import get_api_key

    assert get_api_key("deepseek") == "new-key"


def test_connect_persists_model_when_provided(
    lyra_home: Path, stub_preflight_ok: None
) -> None:
    result = _invoke(
        "connect",
        "anthropic",
        "--key", "sk-ant",
        "--model", "claude-opus-4.5",
        "--no-prompt",
    )
    assert result.exit_code == 0

    from lyra_core.auth.store import load

    data = load()
    assert data["providers"]["anthropic"]["model"] == "claude-opus-4.5"
