"""HTTP front for Lyra (Phase N.6).

A small WSGI app exposing the embedded :class:`~lyra_cli.client.LyraClient`
over HTTP plus a sandbox runner. Stdlib-only by design — no FastAPI
dependency — so ``lyra serve`` works in minimal containers and on
Air-gapped hosts. The trade-off is that we hand-roll routing,
JSON parsing, and SSE streaming, which is fine for the seven
endpoints we ship.

Endpoints:

* ``GET /healthz`` — liveness probe (always 200 with version).
* ``GET /v1/models`` — alias list from the embedded client.
* ``GET /v1/skills`` — installed skills.
* ``GET /v1/sessions`` — historical sessions.
* ``POST /v1/chat`` — synchronous chat turn → :class:`ChatResponse` JSON.
* ``POST /v1/stream`` — same shape, but SSE-streams the reply.
* ``POST /v1/run`` — execute a command in a fresh
  :class:`~lyra_cli.sandbox.LocalSandbox`.

Auth: when ``LYRA_API_TOKEN`` is set, every non-``/healthz`` request
must carry a matching ``Authorization: Bearer <token>`` header.
Without the env var the server runs unauthenticated (intended only
for ``localhost``).
"""
from __future__ import annotations

from .app import create_app, run_server

__all__ = ["create_app", "run_server"]
