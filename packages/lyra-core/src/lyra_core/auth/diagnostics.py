"""Translate raw HTTP failures into human-readable single-line strings.

Used by :mod:`lyra_core.auth.preflight` (so the connect-flow can show
"invalid api key (HTTP 401)" instead of dumping JSON), but exposed at
module scope because the same translation is useful from the agent
loop when an auth error fires mid-turn.
"""
from __future__ import annotations

import json
from typing import Any

__all__ = ["friendly_error"]


def _extract_provider_message(body: bytes) -> str:
    """Pull a short human-readable string out of a JSON error body.

    Providers don't agree on the shape:

    * OpenAI / DeepSeek / xAI / Groq / Cerebras / Mistral:
      ``{"error": {"message": "...", "type": "...", ...}}``
    * Anthropic: ``{"error": {"type": "...", "message": "..."}}``
    * Gemini: ``{"error": {"message": "...", "status": "..."}}``
    * Some local servers: bare ``{"error": "..."}`` string

    We walk all of these shapes; if nothing matches, fall back to the
    raw body trimmed to a single line so the user sees *something*.
    """
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        text = body.decode("utf-8", errors="replace").strip()
        return text.splitlines()[0][:200] if text else ""

    err: Any = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(err, str):
        return err
    if isinstance(err, dict):
        for key in ("message", "code", "type", "status"):
            value = err.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(parsed, dict):
        for key in ("message", "detail", "reason"):
            value = parsed.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def friendly_error(provider: str, status: int, body: bytes) -> str:
    """Return a one-line user-facing description of an HTTP failure.

    Args:
        provider: Provider name (used for context, e.g. "deepseek
          rejected the key").
        status: HTTP status code from the failing call.
        body: Raw response body. May be empty.

    Returns:
        A string like ``"invalid api key (HTTP 401)"`` or
        ``"rate limited — try again in a few seconds (HTTP 429)"``.
        Always includes the status code so support tickets stay
        debuggable.
    """
    provider_message = _extract_provider_message(body)
    suffix = f" (HTTP {status})"
    detail = f": {provider_message}" if provider_message else ""

    if status in (401, 403):
        # 401 = bad/missing key. 403 = key valid but lacks scope; both
        # come back as "invalid" because the user-facing fix is the
        # same: "go reconfigure your key".
        return f"invalid api key for {provider}{suffix}{detail}"
    if status == 429:
        return (
            f"rate limited by {provider}; try again in a moment"
            f"{suffix}{detail}"
        )
    if 500 <= status < 600:
        return (
            f"{provider} is unavailable right now (server error)"
            f"{suffix}{detail}"
        )
    if status == 404:
        return (
            f"endpoint not found for {provider}; preflight URL may "
            f"have moved{suffix}{detail}"
        )
    return f"{provider} preflight failed{suffix}{detail}"
