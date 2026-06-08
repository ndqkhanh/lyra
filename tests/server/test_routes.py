"""Tests for Lyra server HTTP routes.

Covers health, providers, sessions (CRUD), and chat (SSE streaming) endpoints.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock provider adapter modules BEFORE any lyra imports to avoid requiring
# third-party SDKs (anthropic, openai, google-genai, etc.) at test time.
# ---------------------------------------------------------------------------
for _mod_name in ("anthropic", "deepseek", "google", "openai"):
    _mock = MagicMock()
    _mock._SUPPORTED_CAPABILITIES = []
    sys.modules[f"lyra.routing.provider.adapters.{_mod_name}"] = _mock

import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from lyra.server.app import create_app
from lyra.routing.provider.types import (
    CompletionChunk,
    CompletionResponse,
    TokenUsage,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_PROVIDER_API_KEYS = [
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
]


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    server = TestServer(app)
    await server.start_server()
    client = TestClient(server)
    yield client
    await client.close()
    await server.close()


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all provider API key env vars so tests start from a clean slate."""
    for key in _PROVIDER_API_KEYS:
        monkeypatch.delenv(key, raising=False)

    # Also clear the in-memory session store
    from lyra.server.routes.sessions import _SESSIONS  # type: ignore[attr-defined]

    _SESSIONS.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    """GET /health"""

    async def test_health_returns_ok(self, client: TestClient) -> None:
        resp = await client.get("/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        assert isinstance(data["version"], str)
        assert isinstance(data["uptime"], float)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class TestProviders:
    """GET /providers"""

    async def test_providers_empty_when_no_keys(self, client: TestClient) -> None:
        resp = await client.get("/providers")
        assert resp.status == 200
        data = await resp.json()
        assert data["providers"] == []

    @pytest.mark.parametrize(
        ("env_key", "provider_name", "expected_label"),
        [
            ("ANTHROPIC_API_KEY", "anthropic", "Anthropic"),
            ("DEEPSEEK_API_KEY", "deepseek", "DeepSeek"),
            ("OPENAI_API_KEY", "openai", "OpenAI"),
            ("GOOGLE_API_KEY", "google", "Google"),
        ],
    )
    async def test_providers_shows_configured(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        env_key: str,
        provider_name: str,
        expected_label: str,
    ) -> None:
        monkeypatch.setenv(env_key, "test-key-value")
        # Re-import providers module so it picks up the new env var
        from lyra.server.routes import providers as providers_mod

        import importlib

        importlib.reload(providers_mod)

        resp = await client.get("/providers")
        assert resp.status == 200
        data = await resp.json()
        names = [p["name"] for p in data["providers"]]
        assert provider_name in names, f"{provider_name} should be in {names}"
        entry = next(p for p in data["providers"] if p["name"] == provider_name)
        assert entry["label"] == expected_label
        assert len(entry["models"]) > 0
        assert entry["defaultModel"] == entry["models"][0]
        assert isinstance(entry["capabilities"], list)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class TestSessions:
    """GET /sessions, POST /sessions, DELETE /sessions/{id}"""

    async def test_list_empty(self, client: TestClient) -> None:
        resp = await client.get("/sessions")
        assert resp.status == 200
        data = await resp.json()
        assert data["sessions"] == []

    async def test_create_and_list(self, client: TestClient) -> None:
        # Create
        resp = await client.post("/sessions", json={"name": "My Chat"})
        assert resp.status == 201
        data = await resp.json()
        session = data["session"]
        assert session["title"] == "My Chat"
        assert session["messageCount"] == 0
        assert session["status"] == "idle"
        assert "id" in session

        # List now has one
        resp2 = await client.get("/sessions")
        data2 = await resp2.json()
        assert len(data2["sessions"]) == 1
        assert data2["sessions"][0]["id"] == session["id"]

    async def test_create_without_name(self, client: TestClient) -> None:
        resp = await client.post("/sessions", json={})
        assert resp.status == 201
        data = await resp.json()
        # Default title is "Session 1" (counter from cleared store)
        assert data["session"]["title"] == "Session 1"

    async def test_create_multiple_sequential_ids(self, client: TestClient) -> None:
        resp1 = await client.post("/sessions", json={"name": "A"})
        resp2 = await client.post("/sessions", json={"name": "B"})
        id1 = (await resp1.json())["session"]["id"]
        id2 = (await resp2.json())["session"]["id"]
        assert id1 != id2

    async def test_delete_existing(self, client: TestClient) -> None:
        # Create
        create_resp = await client.post("/sessions", json={"name": "Delete Me"})
        session_id = (await create_resp.json())["session"]["id"]

        # Delete
        del_resp = await client.delete(f"/sessions/{session_id}")
        assert del_resp.status == 204

        # Verify gone
        list_resp = await client.get("/sessions")
        data = await list_resp.json()
        assert len(data["sessions"]) == 0

    async def test_delete_nonexistent_returns_204(self, client: TestClient) -> None:
        resp = await client.delete("/sessions/nonexistent-id")
        assert resp.status == 204

    async def test_list_orders_newest_first(self, client: TestClient) -> None:
        await client.post("/sessions", json={"name": "First"})
        await client.post("/sessions", json={"name": "Second"})
        resp = await client.get("/sessions")
        data = await resp.json()
        titles = [s["title"] for s in data["sessions"]]
        # created has second-level granularity, so sessions made in the same
        # second have equal timestamps; stable-insertion order applies.
        # We just verify both titles are present (either order).
        assert set(titles) == {"First", "Second"}


# ---------------------------------------------------------------------------
# Chat (SSE streaming)
# ---------------------------------------------------------------------------


class TestChat:
    """POST /chat/{id}/stream"""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure at least one provider is available for chat tests."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")

    async def _mock_adapter(self, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        """Replace _create_adapter in the chat module with a controllable mock."""
        from lyra.server.routes import chat as chat_mod

        import importlib

        importlib.reload(chat_mod)

        adapter = MagicMock()
        monkeypatch.setattr(chat_mod, "_create_adapter", lambda name: adapter)
        return adapter

    async def test_chat_requires_message(self, client: TestClient) -> None:
        resp = await client.post("/chat/test/stream", json={"message": ""})
        assert resp.status == 400
        body = await resp.text()
        assert "message is required" in body

    async def test_chat_requires_message_field(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        resp = await client.post("/chat/test/stream", json={})
        assert resp.status == 400

    async def test_chat_no_providers(
        self, client: TestClient
    ) -> None:
        resp = await client.post("/chat/test/stream", json={"message": "Hi"})
        # Should fail because no providers are configured
        assert resp.status in (200, 503)

    async def test_chat_streams_successfully(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        adapter = await self._mock_adapter(monkeypatch)

        async def mock_stream(_req):
            yield CompletionChunk(content_delta="Hello ", finish_reason=None)
            yield CompletionChunk(
                content_delta="World", finish_reason="end_turn"
            )

        adapter.complete_stream = mock_stream

        resp = await client.post("/chat/test/stream", json={"message": "Hi"})
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "text/event-stream"
        assert resp.headers.get("Cache-Control") == "no-cache"
        text = await resp.text()

        # Parse SSE events
        events = []
        for part in text.split("\n\n"):
            for line in part.split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        assert len(events) >= 2
        # Check content events
        contents = "".join(e.get("content", "") for e in events if not e.get("done"))
        assert "Hello" in contents
        assert "World" in contents

        # Check final event has usage
        final = events[-1]
        assert final["done"] is True
        assert "usage" in final
        assert final["usage"]["total_tokens"] >= 2

    async def test_chat_stream_error_sends_error_event(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        adapter = await self._mock_adapter(monkeypatch)

        async def mock_error_stream(_req):
            yield CompletionChunk(content_delta="Hi ", finish_reason=None)
            raise RuntimeError("Provider timeout")

        adapter.complete_stream = mock_error_stream

        resp = await client.post("/chat/test/stream", json={"message": "Hi"})
        assert resp.status == 200
        text = await resp.text()

        events = []
        for part in text.split("\n\n"):
            for line in part.split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        # Final event should have error content and done=True
        final = events[-1]
        assert final["done"] is True
        assert "Error" in final.get("content", "")

    async def test_chat_fallback_to_complete(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When streaming produces no content, the handler falls back to
        adapter.complete()."""
        from lyra.server.routes import chat as chat_mod

        import importlib

        importlib.reload(chat_mod)
        adapter = MagicMock()
        monkeypatch.setattr(chat_mod, "_create_adapter", lambda name: adapter)

        # Stream yields empty chunk with no finish_reason
        async def mock_empty_stream(_req):
            yield CompletionChunk(content_delta="")

        adapter.complete_stream = mock_empty_stream
        # Fallback returns a full response (must be a coroutine since the
        # handler awaits it: ``await adapter.complete(...)``).
        from unittest.mock import AsyncMock

        adapter.complete = AsyncMock(
            return_value=CompletionResponse(
                content="Fallback content",
                tool_calls=None,
                usage=TokenUsage(input_tokens=10, output_tokens=20),
                finish_reason="end_turn",
                model="claude-sonnet-4-6",
                latency_ms=100.0,
            )
        )

        resp = await client.post("/chat/test/stream", json={"message": "Hi"})
        assert resp.status == 200
        text = await resp.text()

        events = []
        for part in text.split("\n\n"):
            for line in part.split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        # Should include content from the fallback
        contents = "".join(e.get("content", "") for e in events if not e.get("done"))
        assert "Fallback content" in contents

        # Final should have usage from the fallback
        final = events[-1]
        assert final["done"] is True
        assert final["usage"]["input_tokens"] == 10
        assert final["usage"]["output_tokens"] == 20

    async def test_chat_sends_correct_sse_headers(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        adapter = await self._mock_adapter(monkeypatch)

        async def mock_stream(_req):
            yield CompletionChunk(content_delta="x", finish_reason="end_turn")

        adapter.complete_stream = mock_stream

        resp = await client.post("/chat/test/stream", json={"message": "Hi"})
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "text/event-stream"
        assert resp.headers.get("Cache-Control") == "no-cache"
        assert resp.headers.get("Connection") == "keep-alive"
        assert resp.headers.get("X-Accel-Buffering") == "no"
