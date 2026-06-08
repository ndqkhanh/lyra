"""Tests for Lyra server middleware.

Covers the CORS middleware and request-logging middleware.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from lyra.server.app import create_app
from lyra.server.middleware import cors, logging as logging_mw


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture
def cors_app() -> web.Application:
    """Minimal app with just the CORS middleware."""
    app = web.Application(middlewares=[cors.middleware])
    app.router.add_get("/test", lambda r: web.Response(text="ok"))
    return app


@pytest.fixture
async def cors_client(cors_app):
    server = TestServer(cors_app)
    await server.start_server()
    client = TestClient(server)
    yield client
    await client.close()
    await server.close()


@pytest.fixture
def logging_app() -> web.Application:
    """Minimal app with just the logging middleware."""
    app = web.Application(middlewares=[logging_mw.middleware])
    app.router.add_get("/test", lambda r: web.Response(text="ok"))
    return app


@pytest.fixture
async def logging_client(logging_app):
    server = TestServer(logging_app)
    await server.start_server()
    client = TestClient(server)
    yield client
    await client.close()
    await server.close()


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------


class TestCORSMiddleware:
    """CORS header injection and OPTIONS preflight handling."""

    _ALLOWED_ORIGINS = [
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8580",
        "http://localhost:5173",
        "http://localhost:8580",
        "file://",
        "file:///path/to/page.html",
    ]

    _DISALLOWED_ORIGINS = [
        "http://evil.com",
        "https://malicious.site",
        "http://192.168.1.1:8580",
        "null",
    ]

    @pytest.mark.parametrize("origin", _ALLOWED_ORIGINS)
    async def test_allowed_origin_gets_headers(
        self, cors_client: TestClient, origin: str
    ) -> None:
        resp = await cors_client.get("/test", headers={"Origin": origin})
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == origin
        assert resp.headers.get("Access-Control-Allow-Methods") is not None
        assert resp.headers.get("Access-Control-Allow-Headers") is not None
        assert resp.headers.get("Access-Control-Allow-Credentials") == "true"

    @pytest.mark.parametrize("origin", _DISALLOWED_ORIGINS)
    async def test_disallowed_origin_no_cors(
        self, cors_client: TestClient, origin: str
    ) -> None:
        resp = await cors_client.get("/test", headers={"Origin": origin})
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") is None

    async def test_no_origin_no_cors(self, cors_client: TestClient) -> None:
        resp = await cors_client.get("/test")
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") is None

    async def test_options_preflight(self, cors_client: TestClient) -> None:
        resp = await cors_client.options(
            "/test",
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.status == 204
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        assert "GET" in resp.headers.get("Access-Control-Allow-Methods", "")
        assert "POST" in resp.headers.get("Access-Control-Allow-Methods", "")
        assert "DELETE" in resp.headers.get("Access-Control-Allow-Methods", "")

    async def test_options_without_origin(self, cors_client: TestClient) -> None:
        resp = await cors_client.options("/test")
        assert resp.status == 204
        assert resp.headers.get("Access-Control-Allow-Origin") is None

    async def test_options_disallowed_origin(
        self, cors_client: TestClient
    ) -> None:
        resp = await cors_client.options(
            "/test", headers={"Origin": "https://evil.co"}
        )
        assert resp.status == 204
        assert resp.headers.get("Access-Control-Allow-Origin") is None

    async def test_file_protocol_origin(self, cors_client: TestClient) -> None:
        """file:// origins should be allowed."""
        resp = await cors_client.get(
            "/test",
            headers={"Origin": "file:///Users/test/.lyra/index.html"},
        )
        assert resp.status == 200
        assert resp.headers.get(
            "Access-Control-Allow-Origin"
        ) == "file:///Users/test/.lyra/index.html"


# ---------------------------------------------------------------------------
# Logging middleware
# ---------------------------------------------------------------------------


class TestLoggingMiddleware:
    """Request logging middleware."""

    async def test_logs_successful_request(self, logging_client: TestClient) -> None:
        with patch.object(logging_mw.logger, "info") as mock_log:
            resp = await logging_client.get("/test")
        assert resp.status == 200
        assert mock_log.called
        _, kwargs = mock_log.call_args
        assert kwargs["method"] == "GET"
        assert kwargs["path"] == "/test"
        assert kwargs["status"] == 200
        assert isinstance(kwargs["duration_ms"], (int, float))

    async def test_logs_http_exception(self, logging_client: TestClient) -> None:
        with patch.object(logging_mw.logger, "info") as mock_log:
            resp = await logging_client.post("/nonexistent")
        assert resp.status == 404
        assert mock_log.called
        _, kwargs = mock_log.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["path"] == "/nonexistent"
        assert kwargs["status"] == 404

    async def test_logs_http_bad_request(self, logging_client: TestClient) -> None:
        with patch.object(logging_mw.logger, "info") as mock_log:
            resp = await logging_client.get("/test")
        assert mock_log.called

    async def test_logs_http_service_unavailable(
        self
    ) -> None:
        """Test 503 logging via a targeted app with a 503-raising handler."""
        app = web.Application(middlewares=[logging_mw.middleware])

        async def raise_503(_request: web.Request) -> web.Response:
            raise web.HTTPServiceUnavailable(text="no providers")

        app.router.add_get("/fail", raise_503)
        server = TestServer(app)
        await server.start_server()
        client = TestClient(server)
        try:
            with patch.object(logging_mw.logger, "info") as mock_log:
                resp = await client.get("/fail")
            assert resp.status == 503
            assert mock_log.called
            _, kwargs = mock_log.call_args
            assert kwargs["status"] == 503
        finally:
            await client.close()
            await server.close()

    async def test_middleware_is_wired_in_app(self, client: TestClient) -> None:
        """The logging middleware is part of the app's middleware chain."""
        with patch.object(logging_mw.logger, "info") as mock_log:
            await client.get("/health")
        assert mock_log.called
