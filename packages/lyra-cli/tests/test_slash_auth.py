"""`/auth` slash command - device-code OAuth flow for providers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lyra_cli.interactive.auth import (
    AuthFlowResult,
    DeviceCodeAuth,
    run_auth_slash,
)


class _FakeHttp:
    def __init__(self, sequence: list[tuple[int, dict]]) -> None:
        self._seq = list(sequence)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kw):
        self.calls.append({"method": method, "url": url, **kw})
        code, payload = self._seq.pop(0)
        class R:
            status_code = code
            text = json.dumps(payload)
            def json(self): return payload
            def raise_for_status(self):
                if code >= 400: raise RuntimeError(f"HTTP {code}")
        return R()


def test_device_code_success_persists_token(tmp_path: Path) -> None:
    http = _FakeHttp([
        (200, {"device_code": "D123", "user_code": "ABCD-1234",
               "verification_uri": "https://github.com/login/device",
               "interval": 0, "expires_in": 900}),
        (200, {"error": "authorization_pending"}),
        (200, {"access_token": "gho_xyz", "token_type": "bearer",
               "scope": "read:user,copilot"}),
    ])
    flow = DeviceCodeAuth(
        provider="copilot",
        client_id="Iv1.b507a08c87ecfe98",
        scope="read:user copilot",
        device_endpoint="https://github.com/login/device/code",
        token_endpoint="https://github.com/login/oauth/access_token",
        http=http,
        store_path=tmp_path / "auth.json",
        poll_interval_s=0.0,
        poll_timeout_s=5.0,
    )
    result = flow.run()
    assert isinstance(result, AuthFlowResult)
    assert result.provider == "copilot"
    assert result.user_code == "ABCD-1234"
    stored = json.loads((tmp_path / "auth.json").read_text())
    assert stored["copilot"]["token"] == "gho_xyz"


def test_device_code_polling_respects_slow_down(tmp_path: Path) -> None:
    http = _FakeHttp([
        (200, {"device_code": "D1", "user_code": "U1",
               "verification_uri": "https://example.test/device",
               "interval": 0, "expires_in": 60}),
        (200, {"error": "slow_down"}),
        (200, {"access_token": "tok", "token_type": "bearer"}),
    ])
    flow = DeviceCodeAuth(
        provider="copilot",
        client_id="cid",
        scope="",
        device_endpoint="https://example.test/device",
        token_endpoint="https://example.test/token",
        http=http,
        store_path=tmp_path / "auth.json",
        poll_interval_s=0.0,
        poll_timeout_s=5.0,
    )
    res = flow.run()
    assert res is not None


def test_device_code_timeout_returns_none(tmp_path: Path) -> None:
    """A timed-out device-code flow yields ``None`` and persists nothing.

    Important properties this guards against:
    - ``run()`` returns ``None`` (not ``AuthFlowResult``) on deadline
      expiry — callers branch on the ``None`` to print "auth timed
      out" instead of "logged in".
    - The token store is *not* written: a partial flow must not leave
      a stale entry that would mislead the next ``/auth status``
      check.
    """
    store_path = tmp_path / "auth.json"
    http = _FakeHttp([
        (200, {"device_code": "D1", "user_code": "U1",
               "verification_uri": "https://example.test/device",
               "interval": 0, "expires_in": 60}),
        (200, {"error": "authorization_pending"}),
        (200, {"error": "authorization_pending"}),
    ])
    flow = DeviceCodeAuth(
        provider="copilot",
        client_id="cid",
        scope="",
        device_endpoint="https://example.test/device",
        token_endpoint="https://example.test/token",
        http=http,
        store_path=store_path,
        poll_interval_s=0.0,
        poll_timeout_s=0.0,
    )
    result = flow.run()
    assert result is None
    assert not store_path.exists(), "timed-out flow must not leave a stale token on disk"


def test_run_auth_slash_list_shows_providers(tmp_path: Path) -> None:
    out = run_auth_slash(argv=["list"], store_path=tmp_path / "auth.json")
    assert "copilot" in out.lower()


def test_run_auth_slash_logout_clears_token(tmp_path: Path) -> None:
    store_path = tmp_path / "auth.json"
    store_path.write_text(json.dumps({"copilot": {"token": "t", "expires_at": 9999999999}}))
    out = run_auth_slash(argv=["logout", "copilot"], store_path=store_path)
    assert "cleared" in out.lower()
    data = json.loads(store_path.read_text())
    assert "copilot" not in data


def test_run_auth_slash_unknown_subcommand_returns_usage(tmp_path: Path) -> None:
    out = run_auth_slash(argv=["blah"], store_path=tmp_path / "auth.json")
    assert "usage" in out.lower() or "unknown" in out.lower()
