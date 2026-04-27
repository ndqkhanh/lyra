"""GitHub Copilot as an OpenAI-compatible chat backend.

Copilot's chat API is OpenAI-compat-ish but requires a rotating bearer
token derived from a GitHub OAuth token. We refresh it lazily on each
request that returns 401.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from lyra_cli.providers.copilot import (
    CopilotLLM,
    CopilotTokenStore,
    CopilotUnavailable,
    _refresh_copilot_token,
)
from harness_core.messages import Message


class _FakeHttp:
    """Minimal httpx-like client double."""

    def __init__(self, sequence: list[tuple[int, dict]]) -> None:
        self._seq = list(sequence)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kw):
        self.calls.append({"method": method, "url": url, **kw})
        code, payload = self._seq.pop(0)
        class R:
            status_code = code
            text = json.dumps(payload)
            headers = {"content-type": "application/json"}
            def json(self): return payload
            def raise_for_status(self):
                if code >= 400:
                    raise RuntimeError(f"HTTP {code}")
        return R()


def test_requires_github_token() -> None:
    with pytest.raises(CopilotUnavailable):
        CopilotLLM(github_token=None, http=_FakeHttp([]))


def test_generate_uses_copilot_chat_endpoint(tmp_path: Any) -> None:
    http = _FakeHttp([
        (200, {"token": "ghs_session_123", "expires_at": 9999999999}),
        (200, {
            "choices": [{
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "hi from copilot"},
            }],
        }),
    ])
    store = CopilotTokenStore(path=tmp_path / "auth.json")
    llm = CopilotLLM(github_token="gho_personal", http=http, token_store=store)
    msg = llm.generate([Message.user("hello")])
    assert msg.content == "hi from copilot"
    assert http.calls[0]["url"].endswith("/copilot_internal/v2/token")
    assert http.calls[1]["url"].endswith("/chat/completions")
    assert http.calls[1]["headers"]["authorization"].lower().startswith("bearer ghs_")


def test_token_reuse_within_ttl(tmp_path: Any) -> None:
    http = _FakeHttp([
        (200, {"token": "ghs_cached", "expires_at": 9999999999}),
        (200, {"choices": [{"finish_reason": "stop",
                            "message": {"role": "assistant", "content": "a"}}]}),
        (200, {"choices": [{"finish_reason": "stop",
                            "message": {"role": "assistant", "content": "b"}}]}),
    ])
    store = CopilotTokenStore(path=tmp_path / "auth.json")
    llm = CopilotLLM(github_token="gho_personal", http=http, token_store=store)
    llm.generate([Message.user("first")])
    llm.generate([Message.user("second")])
    urls = [c["url"] for c in http.calls]
    refresh_count = sum(1 for u in urls if u.endswith("/copilot_internal/v2/token"))
    assert refresh_count == 1
    chat_count = sum(1 for u in urls if u.endswith("/chat/completions"))
    assert chat_count == 2


def test_refresh_on_401_retry_succeeds(tmp_path: Any) -> None:
    http = _FakeHttp([
        (200, {"token": "ghs_stale", "expires_at": 9999999999}),
        (401, {"message": "bad credentials"}),
        (200, {"token": "ghs_fresh", "expires_at": 9999999999}),
        (200, {"choices": [{"finish_reason": "stop",
                            "message": {"role": "assistant", "content": "ok"}}]}),
    ])
    store = CopilotTokenStore(path=tmp_path / "auth.json")
    llm = CopilotLLM(github_token="gho_personal", http=http, token_store=store)
    msg = llm.generate([Message.user("x")])
    assert msg.content == "ok"


def test_token_store_roundtrip_persists(tmp_path: Any) -> None:
    store = CopilotTokenStore(path=tmp_path / "auth.json")
    store.save("copilot", "ghs_123", expires_at=9_999_999_999)
    loaded = store.load("copilot")
    assert loaded is not None
    token, exp = loaded
    assert token == "ghs_123"
    assert exp == 9_999_999_999


def test_token_store_load_missing_returns_none(tmp_path: Any) -> None:
    store = CopilotTokenStore(path=tmp_path / "auth.json")
    assert store.load("copilot") is None


def test_refresh_helper_raises_on_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    http = _FakeHttp([(403, {"message": "forbidden"})])
    with pytest.raises(CopilotUnavailable):
        _refresh_copilot_token(github_token="gho_x", http=http)
