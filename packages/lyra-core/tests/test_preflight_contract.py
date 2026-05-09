"""Phase 2 — preflight performs a cheap auth check before persisting keys.

The Connect Flow (Phase 3) hands a freshly-pasted API key to
:func:`lyra_core.auth.preflight.preflight` to find out *before* writing
``~/.lyra/auth.json`` whether the key actually works. Surfacing
"401 unauthorized" or "429 rate limited" at this seam is way friendlier
than letting the user save a junk key and watch the first turn explode.

The contract:

* ``preflight(provider, api_key) -> PreflightResult`` issues a single
  HTTPS GET against the provider's lightest endpoint (``/models`` for
  OpenAI-compatibles, ``/messages?...`` HEAD for Anthropic, etc.) with
  a short timeout and never retries.
* The result carries ``ok: bool``, ``provider: str``, ``detail: str``
  (human-readable), and ``model_count: int`` (how many models the
  endpoint reported, if any).
* HTTP 200 → ``ok=True``.  401/403 → ``ok=False, detail="invalid…"``.
  429 → ``ok=False, detail="rate limited…"``.  Network errors →
  ``ok=False, detail="<error>"``.
* The HTTP transport is patched in tests via ``_http_get`` so we never
  hit the real network from CI.
"""
from __future__ import annotations

import pytest


def _import_preflight():
    """Skippy import so this file lights up RED, not as a collection error."""
    try:
        from lyra_core.auth.preflight import PreflightResult, preflight
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"lyra_core.auth.preflight must exist for Phase 2 ({exc})"
        )
    return preflight, PreflightResult


def test_preflight_200_returns_ok_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mocked HTTP 200 → ``PreflightResult(ok=True, model_count>=1)``."""
    preflight, PreflightResult = _import_preflight()

    monkeypatch.setattr(
        "lyra_core.auth.preflight._http_get",
        lambda url, headers, timeout: (
            200,
            b'{"data": [{"id": "model-x"}, {"id": "model-y"}]}',
        ),
    )
    r = preflight("openai", "sk-fake")
    assert isinstance(r, PreflightResult)
    assert r.ok is True
    assert r.provider == "openai"
    assert r.model_count == 2


def test_preflight_401_returns_bad_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 401 → ``ok=False`` with an "invalid"/"401" detail."""
    preflight, _ = _import_preflight()

    monkeypatch.setattr(
        "lyra_core.auth.preflight._http_get",
        lambda url, headers, timeout: (401, b'{"error": "invalid api key"}'),
    )
    r = preflight("openai", "sk-bad")
    assert r.ok is False
    assert "invalid" in r.detail.lower() or "401" in r.detail


def test_preflight_429_returns_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 429 → ``ok=False`` with a "rate"/"429" detail.

    A rate-limit during preflight is *not* the same as a bad key —
    the connect-flow surfaces this differently ("try again in 30s")
    so the user doesn't think their key was rejected.
    """
    preflight, _ = _import_preflight()

    monkeypatch.setattr(
        "lyra_core.auth.preflight._http_get",
        lambda url, headers, timeout: (429, b'{"error": "rate limit"}'),
    )
    r = preflight("openai", "sk-fake")
    assert r.ok is False
    assert "rate" in r.detail.lower() or "429" in r.detail


def test_preflight_network_error_surfaces_friendly_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connection failures must not leak Python tracebacks to the user."""
    preflight, _ = _import_preflight()

    def _boom(url, headers, timeout):  # type: ignore[no-untyped-def]
        raise OSError("Connection refused")

    monkeypatch.setattr("lyra_core.auth.preflight._http_get", _boom)
    r = preflight("openai", "sk-fake")
    assert r.ok is False
    # The network error must surface in a human-readable way; we
    # tolerate either the raw message or a friendly synonym.
    assert (
        "connection" in r.detail.lower()
        or "network" in r.detail.lower()
        or "unreachable" in r.detail.lower()
    )


def test_preflight_unknown_provider_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Asking preflight about a provider we don't know is a programmer
    error, not a runtime UX edge case — surface it loudly."""
    preflight, _ = _import_preflight()

    with pytest.raises(ValueError):
        preflight("not-a-real-provider", "sk-fake")


def test_preflight_supports_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anthropic preflight uses the ``/v1/messages`` endpoint with a tiny
    payload, but the contract result shape is identical to OpenAI."""
    preflight, _ = _import_preflight()

    monkeypatch.setattr(
        "lyra_core.auth.preflight._http_get",
        lambda url, headers, timeout: (
            200,
            # Anthropic's ``/v1/models`` returns a list of models; the
            # exact shape is provider-specific but we only count rows.
            b'{"data": [{"id": "claude-3-5-sonnet-latest"}]}',
        ),
    )
    r = preflight("anthropic", "sk-ant-fake")
    assert r.ok is True
    assert r.provider == "anthropic"
    assert r.model_count >= 1


def test_preflight_supports_qwen_dashscope_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Qwen preflight hits the DashScope ``/models`` endpoint."""
    preflight, _ = _import_preflight()

    captured: dict = {}

    def _spy(url, headers, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = url
        captured["headers"] = headers
        return (200, b'{"data": [{"id": "qwen-plus"}]}')

    monkeypatch.setattr("lyra_core.auth.preflight._http_get", _spy)
    r = preflight("qwen", "sk-qwen-fake")
    assert r.ok is True
    assert "dashscope" in captured["url"].lower()
