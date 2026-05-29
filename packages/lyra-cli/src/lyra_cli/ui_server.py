#!/usr/bin/env python3
"""Lightweight HTTP server for Lyra UI to call LLM APIs.

Bridges the TypeScript Ink UI with Python's LLM providers.
Runs on localhost:3737 and provides a simple streaming API.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from lyra_core.auth.store import get_api_key, list_providers
from lyra_core.auth.store import save as auth_save
from lyra_core.providers.registry import (
    PROVIDER_REGISTRY,
    get_available_providers,
    get_provider,
)

from .client.client import LyraClient
from .client.types import ChatRequest
from .config_io import load_settings, save_settings


def _json_response(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    """Send a JSON response with CORS headers."""
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())


def _read_changelog_entries() -> list[dict]:
    """Parse CHANGELOG.md into structured entries for /whats-new."""
    import re

    changelog_paths = [
        Path(__file__).parent.parent.parent.parent / "CHANGELOG.md",
        Path.cwd() / "CHANGELOG.md",
    ]
    changelog = None
    for p in changelog_paths:
        if p.exists():
            changelog = p.read_text()
            break

    if not changelog:
        return []

    entries: list[dict] = []
    current_version: str | None = None
    current_date: str | None = None
    current_changes: list[str] = []

    for line in changelog.split("\n"):
        m = re.match(r"^##\s+\[([^\]]+)\]\s*[—\-]\s*(.+)$", line)
        if m:
            if current_version and current_changes:
                entries.append(
                    {
                        "version": current_version,
                        "date": current_date or "",
                        "highlights": current_changes[:5],
                    }
                )
            current_version = m.group(1)
            current_date = m.group(2).strip()
            current_changes = []
            continue

        change = re.match(r"^-\s+\*\*(.+?)\*\*", line)
        if change and current_version:
            current_changes.append(change.group(1))

    if current_version and current_changes:
        entries.append(
            {
                "version": current_version,
                "date": current_date or "",
                "highlights": current_changes[:5],
            }
        )

    return entries[:5]


class LyraUIHandler(BaseHTTPRequestHandler):
    """HTTP handler for Lyra UI requests."""

    client: LyraClient | None = None

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        """Handle POST requests with route dispatch."""
        if self.path == "/chat":
            self._handle_chat()
        elif self.path == "/auth/set":
            self._handle_auth_set()
        elif self.path == "/settings":
            self._handle_settings_update()
        else:
            self.send_error(404, "Not Found")

    def do_GET(self) -> None:
        """Handle GET requests with route dispatch."""
        if self.path == "/health":
            _json_response(self, {"status": "ok"})
        elif self.path == "/providers":
            self._handle_providers()
        elif self.path == "/providers/available":
            self._handle_available_providers()
        elif self.path.startswith("/auth/check/"):
            self._handle_auth_check()
        elif self.path.startswith("/models/"):
            self._handle_models()
        elif self.path == "/settings":
            self._handle_settings_get()
        elif self.path == "/tips":
            self._handle_tips()
        elif self.path == "/whats-new":
            self._handle_whats_new()
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        if self.path.startswith("/auth/delete/"):
            self._handle_auth_delete()
        else:
            self.send_error(404, "Not Found")

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    def _handle_chat(self) -> None:
        """POST /chat — stream LLM response via SSE."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            prompt = data.get("prompt", "")
            if not prompt:
                self.send_error(400, "Missing prompt")
                return

            session_id = data.get("session_id")
            model = data.get("model")

            if self.client is None:
                self.client = LyraClient(repo_root=Path.cwd())

            # Pre-check: verify at least one provider has credentials
            from lyra_core.auth.store import list_providers
            from lyra_core.providers.registry import get_available_providers

            available = set(get_available_providers()) | set(list_providers())
            if not available:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                error_event = json.dumps(
                    {
                        "kind": "error",
                        "payload": (
                            "No API credentials configured. Configure at least one provider:\n"
                            "  /auth set <provider> <api_key>  — save an API key\n"
                            "  export ANTHROPIC_API_KEY=...      — or set via environment\n"
                            "  /providers                        — list available providers"
                        ),
                    }
                )
                self.wfile.write(f"data: {error_event}\n\n".encode())
                self.wfile.flush()
                return

            system_prompt = (
                "You are Lyra, a CLI-native coding assistant. ALWAYS respond in English "
                "unless the user explicitly requests a different language."
            )

            request = ChatRequest(
                prompt=prompt,
                session_id=session_id,
                model=model,
                system_prompt=system_prompt,
            )

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            for event in self.client.stream(request):
                event_data: dict[str, Any] = {
                    "kind": event.kind,
                    "payload": event.payload,
                }
                if event.metadata is not None:
                    event_data["metadata"] = event.metadata
                self.wfile.write(f"data: {json.dumps(event_data)}\n\n".encode())
                self.wfile.flush()

        except Exception as e:
            error_msg = f"{e.__class__.__name__}: {e}"
            # Try to send error via SSE if headers already sent, otherwise as JSON
            try:
                error_data = json.dumps({"kind": "error", "payload": error_msg})
                self.wfile.write(f"data: {error_data}\n\n".encode())
                self.wfile.flush()
            except Exception as write_error:
                # If we can't write the error (connection closed, etc.), log it
                # We're already in an error handler, so we can't do much more
                import sys

                print(f"Failed to send error to client: {write_error}", file=sys.stderr)

    def _handle_providers(self) -> None:
        """GET /providers — list all providers with their models."""
        result = []
        for spec in PROVIDER_REGISTRY:
            if spec.key == "mock":
                continue
            provider_data = {
                "key": spec.key,
                "display_name": spec.display_name,
                "icon": spec.icon,
                "website": spec.website,
                "api_key_url": spec.api_key_url,
                "notes": spec.notes,
                "default_model": spec.default_model,
                "context_window": spec.context_window,
                "supports_tools": spec.supports_tools,
                "supports_reasoning": spec.supports_reasoning,
                "supports_vision": spec.supports_vision,
                "env_vars": list(spec.env_vars),
                "models": [
                    {
                        "slug": m.slug,
                        "display_name": m.display_name,
                        "description": m.description,
                        "tags": list(m.tags),
                        "context_window": m.context_window,
                        "max_output_tokens": m.max_output_tokens,
                    }
                    for m in spec.models
                ],
            }
            result.append(provider_data)
        _json_response(self, {"providers": result})

    def _handle_available_providers(self) -> None:
        """GET /providers/available — providers with configured credentials."""
        available = get_available_providers()
        saved = list_providers()
        combined = sorted(set(available) | set(saved))
        _json_response(self, {"available": combined})

    def _handle_models(self) -> None:
        """GET /models/{provider} — models for a specific provider."""
        provider_key = self.path.split("/")[-1]
        spec = get_provider(provider_key)
        if not spec:
            _json_response(self, {"error": f"Unknown provider: {provider_key}"}, 404)
            return
        _json_response(
            self,
            {
                "provider": spec.key,
                "models": [
                    {
                        "slug": m.slug,
                        "display_name": m.display_name,
                        "description": m.description,
                        "tags": list(m.tags),
                        "context_window": m.context_window,
                        "max_output_tokens": m.max_output_tokens,
                    }
                    for m in spec.models
                ],
            },
        )

    def _handle_auth_set(self) -> None:
        """POST /auth/set — save API key for a provider."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            provider = data.get("provider", "").strip()
            api_key = data.get("key", "").strip()
            model = data.get("model", "").strip() or None

            if not provider or not api_key:
                _json_response(self, {"ok": False, "error": "Missing provider or key"}, 400)
                return

            spec = get_provider(provider)
            if spec is None:
                _json_response(self, {"ok": False, "error": f"Unknown provider: {provider}"}, 400)
                return

            auth_save(provider, api_key, model=model)
            _json_response(self, {"ok": True})
        except Exception as e:
            _json_response(self, {"ok": False, "error": str(e)}, 500)

    def _handle_auth_check(self) -> None:
        """GET /auth/check/{provider} — check if credentials exist."""
        provider_key = self.path.rsplit("/", 1)[-1]
        has_key = bool(get_api_key(provider_key))
        has_env = any(
            os.environ.get(ev)
            for spec in PROVIDER_REGISTRY
            if spec.key == provider_key
            for ev in spec.env_vars
        )
        _json_response(self, {"provider": provider_key, "has_key": has_key or has_env})

    def _handle_auth_delete(self) -> None:
        """DELETE /auth/delete/{provider} — remove saved API key."""
        provider_key = self.path.rsplit("/", 1)[-1]
        from lyra_core.auth.store import revoke

        revoke(provider_key)
        _json_response(self, {"ok": True})

    def _handle_settings_get(self) -> None:
        """GET /settings — return current settings."""
        config = load_settings()
        _json_response(
            self,
            {
                "last_model": config.last_model,
                "last_provider": config.last_provider,
                "primary_provider": config.primary_provider,
                "theme": config.theme,
                "permission_mode": config.permission_mode,
                "auto_detect_tasks": config.auto_detect_tasks,
                "config_version": config.config_version,
            },
        )

    def _handle_settings_update(self) -> None:
        """POST /settings — update settings."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            config = load_settings()

            if "last_model" in data:
                config.last_model = data["last_model"]
            if "last_provider" in data:
                config.last_provider = data["last_provider"]
            if "primary_provider" in data:
                config.primary_provider = data["primary_provider"]
            if "theme" in data:
                config.theme = data["theme"]
            if "permission_mode" in data:
                config.permission_mode = data["permission_mode"]
            if "auto_detect_tasks" in data:
                config.auto_detect_tasks = data["auto_detect_tasks"]

            save_settings(config)
            _json_response(self, {"ok": True})
        except Exception as e:
            _json_response(self, {"ok": False, "error": str(e)}, 500)

    def _handle_tips(self) -> None:
        """GET /tips — return rotating tips for the header."""
        tips = [
            {
                "title": "Run /init to create a project CLAUDE.md",
                "description": "Scaffold SOUL.md + .lyra/ in your repo",
            },
            {
                "title": "Use @ to mention files",
                "description": "Type @ then a filename for autocomplete",
            },
            {
                "title": "Press Tab to cycle modes",
                "description": "Switch between agent, plan, ask, and auto",
            },
            {
                "title": "Try /model for the picker",
                "description": "Interactive model selection with arrow keys",
            },
            {
                "title": "Use ! for shell commands",
                "description": "Prefix with ! to run bash directly",
            },
            {
                "title": "Ctrl+R searches history",
                "description": "Search your command history across sessions",
            },
            {
                "title": "Shift+Enter for newlines",
                "description": "Multi-line input when you need it",
            },
            {
                "title": "/compact saves context",
                "description": "Summarize your conversation to free up space",
            },
            {
                "title": "/rewind undoes turns",
                "description": "Restore code and conversation to any checkpoint",
            },
            {
                "title": "/feedback sends bug reports",
                "description": "Share your experience with the team",
            },
        ]
        _json_response(self, {"tips": tips})

    def _handle_whats_new(self) -> None:
        """GET /whats-new — return changelog entries."""
        entries = _read_changelog_entries()
        _json_response(self, {"entries": entries})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Suppress default logging."""
        _ = (format, args)
        pass


def start_server(port: int = 3737) -> None:
    """Start the Lyra UI server.

    Args:
        port: Port to listen on (default: 3737)
    """
    server = HTTPServer(("localhost", port), LyraUIHandler)
    print(f"Lyra UI server listening on http://localhost:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...", file=sys.stderr)
        server.shutdown()


if __name__ == "__main__":
    start_server()
