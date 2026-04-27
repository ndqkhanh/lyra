"""Stdlib WSGI app powering ``lyra serve``.

Built on :mod:`wsgiref` so we can stay dependency-free. Routes are
declared as ``(method, path)`` tuples — no globbing — because the
endpoint count is small and explicit-match is easier to reason
about under load.

Why WSGI and not :class:`http.server`?
* WSGI gets us a clean ``environ → response`` contract that's
  trivially testable (no socket needed).
* :func:`wsgiref.simple_server.make_server` ships threading via
  :class:`socketserver.ThreadingMixIn`, enough for the local-dev
  use case.
* Anyone wanting production deploys can swap in gunicorn/uvicorn
  by importing :func:`create_app` and serving the WSGI callable
  themselves.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
from dataclasses import asdict
from importlib import metadata as importlib_metadata
from typing import Any, Callable, Iterable, Mapping
from wsgiref.simple_server import WSGIRequestHandler, make_server

from ..client import ChatRequest, LyraClient
from ..sandbox import LocalSandbox

_log = logging.getLogger("lyra.serve")

# Hard cap on POST bodies. The endpoints take prompts and small
# JSON payloads; anything bigger is almost certainly a bug or an
# abuse attempt and we'd rather fail fast than buffer megabytes.
_MAX_BODY_BYTES = 1_000_000

# A WSGI app is a callable taking ``(environ, start_response)`` and
# returning an iterable of bytes. We type it loosely because we
# inject our own helpers below.
_StartResponse = Callable[[str, list[tuple[str, str]]], Any]
_Handler = Callable[[Mapping[str, Any]], "_Response"]


class _Response:
    """Minimal response container — body + status + headers.

    Why not just return tuples? Routing handlers compose: an auth
    guard wants to short-circuit with a 401, the JSON wrapper
    wants to set Content-Type, etc. Using a class keeps that
    chaining explicit without dragging in starlette.
    """

    __slots__ = ("status", "headers", "body")

    def __init__(
        self,
        status: int,
        body: bytes | str | Iterable[bytes],
        *,
        headers: list[tuple[str, str]] | None = None,
        content_type: str = "application/json",
    ) -> None:
        self.status = status
        self.headers = list(headers or [])
        if not any(h[0].lower() == "content-type" for h in self.headers):
            self.headers.append(("Content-Type", content_type))
        if isinstance(body, str):
            self.body = body.encode("utf-8")
        elif isinstance(body, bytes):
            self.body = body
        else:
            self.body = body  # type: ignore[assignment]

    def emit(self, start_response: _StartResponse) -> Iterable[bytes]:
        status_line = f"{self.status} {_HTTP_STATUS.get(self.status, 'OK')}"
        if isinstance(self.body, (bytes, bytearray)):
            self.headers = [
                (k, v) for k, v in self.headers
                if k.lower() != "content-length"
            ]
            self.headers.append(("Content-Length", str(len(self.body))))
            start_response(status_line, self.headers)
            return [bytes(self.body)]
        # streaming iterator (SSE)
        start_response(status_line, self.headers)
        return self.body  # type: ignore[return-value]


_HTTP_STATUS = {
    200: "OK", 201: "Created", 204: "No Content",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 413: "Payload Too Large",
    500: "Internal Server Error",
}


def _json_response(payload: Any, status: int = 200) -> _Response:
    body = json.dumps(payload, default=_jsonable, indent=None) + "\n"
    return _Response(status, body)


def _jsonable(o: Any) -> Any:
    """Best-effort JSON coercion for dataclasses and Path objects."""
    if hasattr(o, "to_dict") and callable(o.to_dict):
        return o.to_dict()
    if hasattr(o, "__dataclass_fields__"):
        return asdict(o)
    if hasattr(o, "__fspath__"):
        return os.fspath(o)
    raise TypeError(f"not JSON-serialisable: {type(o).__name__}")


def _read_body(environ: Mapping[str, Any]) -> bytes:
    """Pull the request body off WSGI ``input``, capped at the limit."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    if length < 0:
        return b""
    if length > _MAX_BODY_BYTES:
        raise _HttpError(413, "request body too large")
    stream = environ.get("wsgi.input")
    if stream is None or length == 0:
        return b""
    return stream.read(length)


class _HttpError(Exception):
    """Carries an HTTP status + message back through the dispatch stack."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _require_auth(environ: Mapping[str, Any]) -> _Response | None:
    """Return a 401 response when auth is enabled and the header is wrong."""
    expected = (os.environ.get("LYRA_API_TOKEN") or "").strip()
    if not expected:
        return None
    header = environ.get("HTTP_AUTHORIZATION", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or token.strip() != expected:
        return _json_response(
            {"error": "unauthorized", "message": "missing or invalid bearer token"},
            status=401,
        )
    return None


def create_app(client: LyraClient | None = None) -> Callable[..., Iterable[bytes]]:
    """Build the WSGI callable.

    Args:
        client: Pre-built :class:`LyraClient` to share across
            requests. When ``None`` (the default), the app
            constructs one lazily on first chat call so unit tests
            can run the routing layer without a real provider.

    Returns:
        A WSGI app: ``app(environ, start_response) -> iterable[bytes]``.
    """
    state: dict[str, Any] = {"client": client}

    def get_client() -> LyraClient:
        c = state.get("client")
        if c is None:
            c = LyraClient()
            state["client"] = c
        return c

    routes: dict[tuple[str, str], _Handler] = {
        ("GET", "/healthz"): lambda env: _handle_healthz(),
        ("GET", "/v1/models"): lambda env: _handle_models(get_client()),
        ("GET", "/v1/skills"): lambda env: _handle_skills(get_client()),
        ("GET", "/v1/sessions"): lambda env: _handle_sessions(get_client()),
        ("POST", "/v1/chat"): lambda env: _handle_chat(env, get_client()),
        ("POST", "/v1/stream"): lambda env: _handle_stream(env, get_client()),
        ("POST", "/v1/run"): lambda env: _handle_run(env),
    }

    def app(environ: Mapping[str, Any], start_response: _StartResponse) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        try:
            if path != "/healthz":
                # /healthz must remain unauthenticated so kube-style
                # liveness probes work without baking the token in.
                guard = _require_auth(environ)
                if guard is not None:
                    return guard.emit(start_response)
            handler = routes.get((method, path))
            if handler is None:
                if any(p == path for (_, p) in routes):
                    return _json_response(
                        {"error": "method_not_allowed"}, status=405,
                    ).emit(start_response)
                return _json_response(
                    {"error": "not_found", "path": path}, status=404,
                ).emit(start_response)
            response = handler(environ)
            return response.emit(start_response)
        except _HttpError as e:
            return _json_response(
                {"error": "http_error", "message": e.message},
                status=e.status,
            ).emit(start_response)
        except Exception as e:  # pragma: no cover - hard failure path
            _log.exception("unhandled error in lyra serve")
            return _json_response(
                {"error": "internal", "message": str(e)},
                status=500,
            ).emit(start_response)

    return app


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _handle_healthz() -> _Response:
    try:
        version = importlib_metadata.version("lyra-cli")
    except importlib_metadata.PackageNotFoundError:
        version = "0.0.0+unknown"
    return _json_response({"ok": True, "service": "lyra", "version": version})


def _handle_models(client: LyraClient) -> _Response:
    return _json_response({"models": list(client.list_models())})


def _handle_skills(client: LyraClient) -> _Response:
    return _json_response({"skills": list(client.list_skills())})


def _handle_sessions(client: LyraClient) -> _Response:
    return _json_response({"sessions": list(client.list_sessions())})


def _handle_chat(environ: Mapping[str, Any], client: LyraClient) -> _Response:
    payload = _decode_json_body(environ)
    request = _payload_to_chat_request(payload)
    response = client.chat(request)
    return _json_response(_chat_response_to_dict(response))


def _handle_stream(environ: Mapping[str, Any], client: LyraClient) -> _Response:
    payload = _decode_json_body(environ)
    request = _payload_to_chat_request(payload)

    def sse() -> Iterable[bytes]:
        for event in client.stream(request):
            data = json.dumps({"kind": event.kind, "payload": event.payload}, default=_jsonable)
            yield f"data: {data}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"

    return _Response(
        200,
        sse(),
        headers=[
            ("Content-Type", "text/event-stream"),
            ("Cache-Control", "no-store"),
            ("X-Accel-Buffering", "no"),
        ],
    )


def _handle_run(environ: Mapping[str, Any]) -> _Response:
    payload = _decode_json_body(environ)
    argv = payload.get("argv")
    if not argv or not isinstance(argv, (list, str)):
        raise _HttpError(400, "`argv` must be a non-empty list or string")
    timeout = payload.get("timeout")
    files = payload.get("files") or {}
    cwd = payload.get("cwd")
    env = payload.get("env") or {}
    if not isinstance(files, dict) or not isinstance(env, dict):
        raise _HttpError(400, "`files` and `env` must be objects")
    with LocalSandbox() as sb:
        for relpath, content in files.items():
            if not isinstance(content, str):
                raise _HttpError(400, f"file {relpath!r} must be a string")
            sb.write_file(relpath, content)
        result = sb.run(argv, timeout=timeout, env=env, cwd=cwd)
    return _json_response(result.to_dict())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decode_json_body(environ: Mapping[str, Any]) -> dict[str, Any]:
    raw = _read_body(environ)
    if not raw:
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise _HttpError(400, f"invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise _HttpError(400, "request body must be a JSON object")
    return data


def _payload_to_chat_request(payload: Mapping[str, Any]) -> ChatRequest:
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        raise _HttpError(400, "`prompt` is required")
    return ChatRequest(
        prompt=prompt,
        model=payload.get("model"),
        session_id=payload.get("session_id"),
        system_prompt=payload.get("system_prompt"),
        metadata=payload.get("metadata") or {},
    )


def _chat_response_to_dict(resp: Any) -> dict[str, Any]:
    return {
        "text": getattr(resp, "text", ""),
        "session_id": getattr(resp, "session_id", ""),
        "model": getattr(resp, "model", ""),
        "usage": getattr(resp, "usage", None),
        "error": getattr(resp, "error", None),
    }


# ---------------------------------------------------------------------------
# CLI bridge
# ---------------------------------------------------------------------------


class _QuietHandler(WSGIRequestHandler):
    """WSGIRequestHandler that logs to :mod:`logging` instead of stderr."""

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        _log.info("%s - " + fmt, self.address_string(), *args)


def run_server(host: str = "127.0.0.1", port: int = 9099) -> None:
    """Block on a stdlib HTTP server.

    Used by ``lyra serve``. Production deploys should import
    :func:`create_app` and run it with gunicorn/uvicorn instead.
    """
    app = create_app()
    server = make_server(host, port, app, handler_class=_QuietHandler)
    _log.info("lyra serve listening on http://%s:%d", host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()


# Public re-exports for tests / library callers.
__all__ = ["create_app", "run_server"]
