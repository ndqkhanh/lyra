"""Tests for :mod:`lyra_cli.serve`."""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from lyra_cli.client import ChatRequest, ChatResponse, LyraClient, StreamEvent
from lyra_cli.serve.app import create_app


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeClient:
    """Minimal LyraClient-shaped stub for routing tests.

    We don't construct a real client (that would require a provider
    factory and on-disk session store). The routing layer only
    cares about the methods, not their internals.
    """

    def __init__(self) -> None:
        self.last_chat_request: ChatRequest | None = None
        self.scripted_text = "hello from fake lyra"
        self.scripted_stream: list[StreamEvent] = [
            StreamEvent(kind="delta", payload="hi"),
            StreamEvent(kind="end", payload={"finish_reason": "stop"}),
        ]
        self.models = ["claude-sonnet-4.5", "deepseek-flash"]
        self.skills: list[dict[str, Any]] = [
            {"id": "echo", "name": "Echo", "description": "Echo back."},
        ]
        self.sessions: list[dict[str, Any]] = [
            {"id": "s1", "title": "first"},
        ]

    def chat(self, req: ChatRequest | str) -> ChatResponse:
        if isinstance(req, str):
            req = ChatRequest(prompt=req)
        self.last_chat_request = req
        return ChatResponse(
            text=self.scripted_text,
            session_id=req.session_id or "session-from-fake",
            model=req.model or "deepseek-flash",
            usage={"input_tokens": 4, "output_tokens": 6},
            error=None,
        )

    def stream(self, req: ChatRequest | str):
        if isinstance(req, str):
            req = ChatRequest(prompt=req)
        for event in self.scripted_stream:
            yield event

    def list_models(self) -> list[str]:
        return list(self.models)

    def list_skills(self) -> list[dict[str, Any]]:
        return list(self.skills)

    def list_sessions(self) -> list[dict[str, Any]]:
        return list(self.sessions)


# ---------------------------------------------------------------------------
# WSGI test harness
# ---------------------------------------------------------------------------


class _Captured:
    def __init__(self) -> None:
        self.status: str = ""
        self.headers: list[tuple[str, str]] = []

    def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
        self.status = status
        self.headers = headers


def _request(
    app,
    method: str,
    path: str,
    *,
    body: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    raw = body.encode("utf-8") if isinstance(body, str) else (body or b"")
    environ: dict[str, Any] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    for k, v in (headers or {}).items():
        environ[f"HTTP_{k.upper().replace('-', '_')}"] = v
    captured = _Captured()
    body_iter = app(environ, captured)
    body_bytes = b"".join(body_iter)
    status_code = int(captured.status.split(" ", 1)[0])
    headers_dict = {k: v for k, v in captured.headers}
    return status_code, headers_dict, body_bytes


@pytest.fixture(autouse=True)
def _disable_auth(monkeypatch):
    monkeypatch.delenv("LYRA_API_TOKEN", raising=False)


@pytest.fixture
def app():
    return create_app(client=_FakeClient())


# ---------------------------------------------------------------------------
# Health + introspection
# ---------------------------------------------------------------------------


def test_healthz_returns_200(app) -> None:
    status, _, body = _request(app, "GET", "/healthz")
    assert status == 200
    payload = json.loads(body)
    assert payload["ok"] is True
    assert payload["service"] == "lyra"


def test_models_endpoint_lists_aliases(app) -> None:
    status, _, body = _request(app, "GET", "/v1/models")
    assert status == 200
    payload = json.loads(body)
    assert "claude-sonnet-4.5" in payload["models"]


def test_skills_endpoint_returns_skill_dicts(app) -> None:
    status, _, body = _request(app, "GET", "/v1/skills")
    assert status == 200
    payload = json.loads(body)
    assert payload["skills"][0]["id"] == "echo"


def test_sessions_endpoint_returns_session_dicts(app) -> None:
    status, _, body = _request(app, "GET", "/v1/sessions")
    assert status == 200
    payload = json.loads(body)
    assert payload["sessions"][0]["id"] == "s1"


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


def test_chat_round_trip(app) -> None:
    status, _, body = _request(
        app, "POST", "/v1/chat",
        body=json.dumps({"prompt": "hi", "model": "deepseek-flash"}),
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["text"] == "hello from fake lyra"
    assert payload["model"] == "deepseek-flash"
    assert payload["error"] is None


def test_chat_rejects_empty_prompt(app) -> None:
    status, _, body = _request(
        app, "POST", "/v1/chat",
        body=json.dumps({"prompt": ""}),
    )
    assert status == 400
    assert "prompt" in json.loads(body)["message"]


def test_chat_rejects_invalid_json(app) -> None:
    status, _, body = _request(
        app, "POST", "/v1/chat",
        body="{not valid",
    )
    assert status == 400


def test_chat_uses_provided_session_id(app) -> None:
    fake = _FakeClient()
    a = create_app(client=fake)
    _request(
        a, "POST", "/v1/chat",
        body=json.dumps({"prompt": "hi", "session_id": "carry-over"}),
    )
    assert fake.last_chat_request is not None
    assert fake.last_chat_request.session_id == "carry-over"


# ---------------------------------------------------------------------------
# Stream (SSE)
# ---------------------------------------------------------------------------


def test_stream_yields_sse_events(app) -> None:
    status, headers, body = _request(
        app, "POST", "/v1/stream",
        body=json.dumps({"prompt": "stream please"}),
    )
    assert status == 200
    assert headers["Content-Type"] == "text/event-stream"
    text = body.decode("utf-8")
    assert "data: " in text
    assert "[DONE]" in text


# ---------------------------------------------------------------------------
# Run sandbox
# ---------------------------------------------------------------------------


def test_run_executes_command(app) -> None:
    status, _, body = _request(
        app, "POST", "/v1/run",
        body=json.dumps({"argv": ["echo", "from-sandbox"]}),
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["ok"] is True
    assert "from-sandbox" in payload["stdout"]


def test_run_writes_files_before_executing(app) -> None:
    status, _, body = _request(
        app, "POST", "/v1/run",
        body=json.dumps({
            "argv": ["cat", "foo.txt"],
            "files": {"foo.txt": "hello-from-test"},
        }),
    )
    assert status == 200
    payload = json.loads(body)
    assert "hello-from-test" in payload["stdout"]


def test_run_rejects_missing_argv(app) -> None:
    status, _, _ = _request(
        app, "POST", "/v1/run",
        body=json.dumps({}),
    )
    assert status == 400


# ---------------------------------------------------------------------------
# Misc routing
# ---------------------------------------------------------------------------


def test_unknown_path_returns_404(app) -> None:
    status, _, _ = _request(app, "GET", "/v1/nope")
    assert status == 404


def test_wrong_method_returns_405(app) -> None:
    status, _, _ = _request(app, "DELETE", "/v1/chat")
    assert status == 405


def test_oversized_body_returns_413(app) -> None:
    big_body = b"x" * (1_000_001)
    status, _, _ = _request(
        app, "POST", "/v1/chat",
        body=big_body,
        headers={"Content-Type": "application/json"},
    )
    assert status == 413


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_auth_required_when_token_set(monkeypatch) -> None:
    monkeypatch.setenv("LYRA_API_TOKEN", "secret-123")
    app = create_app(client=_FakeClient())

    status, _, _ = _request(app, "GET", "/v1/models")
    assert status == 401

    status, _, _ = _request(
        app, "GET", "/v1/models",
        headers={"Authorization": "Bearer secret-123"},
    )
    assert status == 200


def test_healthz_remains_unauthenticated(monkeypatch) -> None:
    monkeypatch.setenv("LYRA_API_TOKEN", "secret-123")
    app = create_app(client=_FakeClient())
    status, _, _ = _request(app, "GET", "/healthz")
    assert status == 200
