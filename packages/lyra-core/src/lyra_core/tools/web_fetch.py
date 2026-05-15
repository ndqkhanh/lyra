"""Real ``WebFetch`` tool — Claude-Code / opencode parity (v1.7.3).

Fetches a URL via an injectable HTTP client, strips HTML down to
readable text (scripts/styles dropped), and enforces ``max_chars``
truncation. 4xx/5xx responses are surfaced as a result dict (never
raised) so LLMs can reason about the failure.

URL safety: ``file://`` and ``javascript:`` schemes are rejected to
avoid the agent being tricked into exfiltrating local files via a
prompt-injection.
"""
from __future__ import annotations

from typing import Any, Callable

from ..lsp_backend.errors import FeatureUnavailable


_FORBIDDEN_SCHEMES = ("file:", "javascript:", "data:", "about:")


def _default_http_client() -> Any:
    try:
        import httpx  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional dep
        raise FeatureUnavailable(
            "WebFetch default client needs httpx. "
            "Install with `pip install 'lyra[web]'` or pass a custom "
            "http client to make_web_fetch_tool(http=...)."
        ) from exc

    return httpx.Client(follow_redirects=True, timeout=10.0)


def _html_to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return " ".join(text.split())
    except Exception:
        # Minimal fallback: strip <script>/<style> blocks then all tags.
        import re

        cleaned = html
        for dangerous in ("script", "style", "noscript"):
            cleaned = re.sub(
                rf"<{dangerous}\b[^>]*>.*?</{dangerous}>",
                " ",
                cleaned,
                flags=re.I | re.S,
            )
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        return " ".join(cleaned.split())


def make_web_fetch_tool(
    *,
    http: Any | None = None,
) -> Callable[..., dict]:
    """Build the LLM-callable ``WebFetch`` tool bound to ``http``."""

    def web_fetch(
        *,
        url: str,
        max_chars: int = 50_000,
        headers: dict[str, str] | None = None,
    ) -> dict:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        lowered = url.strip().lower()
        for scheme in _FORBIDDEN_SCHEMES:
            if lowered.startswith(scheme):
                raise ValueError(
                    f"url scheme {scheme!r} is not allowed for safety"
                )
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")

        client = http or _default_http_client()
        try:
            resp = client.get(
                url,
                follow_redirects=True,
                timeout=10.0,
                headers=headers or {},
            )
        except Exception as exc:
            return {
                "text": "",
                "final_url": url,
                "status_code": 0,
                "truncated": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        status = int(getattr(resp, "status_code", 0))
        final_url = str(getattr(resp, "url", url))

        if status >= 400:
            return {
                "text": "",
                "final_url": final_url,
                "status_code": status,
                "truncated": False,
                "error": f"http {status}",
            }

        raw = getattr(resp, "text", "") or ""
        content_type = ""
        hdrs = getattr(resp, "headers", {}) or {}
        if isinstance(hdrs, dict):
            content_type = hdrs.get("content-type", "") or hdrs.get("Content-Type", "")
        if "html" in content_type.lower():
            body = _html_to_text(raw)
        else:
            body = raw

        truncated = False
        if len(body) > max_chars:
            body = body[:max_chars]
            truncated = True

        return {
            "text": body,
            "final_url": final_url,
            "status_code": status,
            "truncated": truncated,
            "error": None,
        }

    web_fetch.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "WebFetch",
        "description": "Fetch a URL and return its readable text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {"type": "integer", "default": 50000},
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["url"],
        },
    }
    return web_fetch


class WebFetchTool:
    """Tool wrapper for WebFetch compatible with harness_core.tools.ToolRegistry."""

    name = "WebFetch"
    description = "Fetch a URL and return its readable text content."
    risk = "low"
    writes = False

    def __init__(self, *, http: Any | None = None) -> None:
        self._fetch = make_web_fetch_tool(http=http)

    def run(self, args: Any) -> str:
        """Execute the web fetch and return formatted result."""
        result = self._fetch(**args)
        if result.get("error"):
            return f"WebFetch failed: {result['error']}\nURL: {result['final_url']}"

        text = result.get("text", "")
        truncated = " (truncated)" if result.get("truncated") else ""
        status = result.get("status_code", 0)
        return f"fetched {result['final_url']} (HTTP {status}){truncated}\n{text}"

    def to_schema(self) -> dict:
        """Return the tool schema for LLM consumption."""
        return getattr(self._fetch, "__tool_schema__", {})


__all__ = ["make_web_fetch_tool", "WebFetchTool"]
