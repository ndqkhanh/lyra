"""Cheap auth-check round-trip for ``lyra connect``.

The connect-flow hands a freshly-pasted API key to :func:`preflight` to
find out *before* we write ``~/.lyra/auth.json`` whether the key
actually works. Returning ``ok=False`` here lets the dialog show a
single-line diagnostic ("invalid api key", "rate limited, try again
in 30s", "connection refused — is Ollama running?") instead of waiting
until the first agent turn explodes.

Endpoint choice per provider (must be the *cheapest* model-listing
call we can make):

* OpenAI-compatibles (``openai``, ``deepseek``, ``xai``, ``groq``,
  ``cerebras``, ``mistral``, ``openrouter``, ``qwen`` /
  ``dashscope``, ``lmstudio``, ``vllm``) — ``GET /v1/models``
* ``anthropic`` — ``GET /v1/models`` (added 2024-04, free)
* ``gemini`` — ``GET /v1beta/models?key=<api-key>`` (Gemini wants the
  key in the query string, not the ``Authorization`` header)
* ``ollama`` — ``GET /api/tags`` (no auth — local-only by design)

The HTTP transport is a thin wrapper over :mod:`urllib.request` so
preflight has zero new third-party dependencies. Tests monkey-patch
:func:`_http_get` directly so the suite never hits the real network.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping
from urllib import request as _urlreq
from urllib.error import HTTPError, URLError

__all__ = ["PreflightResult", "preflight"]


@dataclass(frozen=True)
class PreflightResult:
    """Outcome of a single preflight call.

    Attributes:
        ok: ``True`` iff the provider answered with a valid 200.
        provider: Echo of the provider name passed in.
        detail: Single-line human-readable explanation. Empty string
            when ``ok=True``; otherwise diagnostic text safe to put in
            a Rich panel ("invalid api key (HTTP 401)").
        model_count: Number of models the endpoint listed when
            successful, ``None`` when the endpoint doesn't expose a
            list (some local servers) or the call failed.
    """

    ok: bool
    provider: str
    detail: str
    model_count: int | None


# Per-provider endpoint metadata. Keep this table tight: a missing
# entry raises ``ValueError`` from :func:`preflight` so we never
# silently 404 a fresh provider.
_PROVIDERS: dict[str, dict[str, str]] = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/models",
        "auth": "anthropic",
    },
    "openai": {
        "url": "https://api.openai.com/v1/models",
        "auth": "bearer",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "auth": "gemini-query",
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/models",
        "auth": "bearer",
    },
    "qwen": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        "auth": "bearer",
    },
    "dashscope": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        "auth": "bearer",
    },
    "xai": {
        "url": "https://api.x.ai/v1/models",
        "auth": "bearer",
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/models",
        "auth": "bearer",
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/models",
        "auth": "bearer",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/models",
        "auth": "bearer",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "auth": "bearer",
    },
    "ollama": {
        "url": "http://127.0.0.1:11434/api/tags",
        "auth": "none",
    },
    "lmstudio": {
        "url": "http://127.0.0.1:1234/v1/models",
        "auth": "bearer-optional",
    },
    "vllm": {
        "url": "http://127.0.0.1:8000/v1/models",
        "auth": "bearer-optional",
    },
}


def _http_get(
    url: str, headers: Mapping[str, str], timeout: float
) -> tuple[int, bytes]:
    """Perform a single HTTP GET, returning ``(status, body)``.

    Wrapped in its own function so preflight tests can monkey-patch
    ``lyra_core.auth.preflight._http_get`` to a deterministic stub
    without spinning up a fake server. Real callers go through
    :mod:`urllib.request`, which means we inherit Python's CA bundle
    and proxy resolution for free.
    """
    req = _urlreq.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with _urlreq.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status, resp.read()
    except HTTPError as e:
        return e.code, e.read() or b""


def _build_request(provider: str, api_key: str) -> tuple[str, dict[str, str]]:
    """Resolve URL + headers for ``provider`` given a freshly-pasted key.

    Returns ``(url, headers)`` ready to feed into :func:`_http_get`.
    Raises :class:`ValueError` for providers we don't know about so
    callers can surface "preflight doesn't yet support X" instead of
    hitting a bogus URL.
    """
    if provider not in _PROVIDERS:
        raise ValueError(
            f"unknown provider {provider!r}; "
            f"supported: {sorted(_PROVIDERS)}"
        )
    meta = _PROVIDERS[provider]
    url = meta["url"]
    headers: dict[str, str] = {"Accept": "application/json"}
    auth_kind = meta["auth"]

    if auth_kind == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_kind == "anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    elif auth_kind == "gemini-query":
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}key={api_key}"
    elif auth_kind == "bearer-optional":
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    elif auth_kind == "none":
        # Local-only providers (Ollama). The user's "key" is ignored;
        # we still hit the URL to confirm the daemon is up.
        pass
    else:  # pragma: no cover — guarded by the table above.
        raise ValueError(f"unknown auth kind {auth_kind!r}")
    return url, headers


def _count_models(body: bytes) -> int | None:
    """Best-effort count of models in a successful response body.

    Different providers return different shapes; we walk the obvious
    spots:
    * ``{"data": [{...}, ...]}`` (OpenAI-compatible)
    * ``{"models": [{...}, ...]}`` (Ollama, some local servers)
    * top-level list (rare, but cheap to check)

    Returns ``None`` when the body is not JSON or matches none of the
    known shapes — we never want a parse hiccup to flip a successful
    auth-check into a failed one.
    """
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if isinstance(parsed, list):
        return len(parsed)
    if isinstance(parsed, Mapping):
        for key in ("data", "models"):
            value = parsed.get(key)
            if isinstance(value, list):
                return len(value)
    return None


def preflight(
    provider: str, api_key: str, *, timeout: float = 5.0
) -> PreflightResult:
    """Issue a single HTTP round-trip to verify ``api_key``.

    No retries, no fall-back to a different endpoint, no caching —
    callers are expected to surface the result directly to the user
    and decide whether to retry interactively.

    Args:
        provider: Provider name (must be in :data:`_PROVIDERS`).
        api_key: Raw API key as the user pasted it. May be empty for
            ``ollama`` / local-only providers.
        timeout: Per-request timeout in seconds. Defaults to 5s — the
            connect dialog blocks on this so we trade a bit of
            latency for a much friendlier failure message.

    Returns:
        A :class:`PreflightResult`. ``ok=True`` iff the response was
        HTTP 200 (or 400 with a recognizable "no input" shape, which
        still proves auth worked but we don't depend on that today).

    Raises:
        ValueError: ``provider`` is not in the supported set.
    """
    url, headers = _build_request(provider, api_key)

    try:
        status, body = _http_get(url, headers, timeout)
    except (URLError, OSError, TimeoutError) as exc:
        # ``URLError`` covers DNS failures + connection refused; ``OSError``
        # is the generic network-failure umbrella. Either way we want a
        # human-friendly single-line summary, never a traceback.
        message = str(exc) or exc.__class__.__name__
        lowered = message.lower()
        if "refused" in lowered or "unreachable" in lowered:
            detail = f"connection refused: {message}"
        elif "timed out" in lowered or "timeout" in lowered:
            detail = f"network timeout: {message}"
        else:
            detail = f"connection error: {message}"
        return PreflightResult(
            ok=False, provider=provider, detail=detail, model_count=None
        )

    if status == 200:
        return PreflightResult(
            ok=True,
            provider=provider,
            detail="",
            model_count=_count_models(body),
        )

    # Translate the failure into a one-line, user-readable diagnostic.
    # Imported lazily so circular imports between auth.preflight and
    # auth.diagnostics never bite if the latter grows new helpers.
    from .diagnostics import friendly_error

    return PreflightResult(
        ok=False,
        provider=provider,
        detail=friendly_error(provider, status, body),
        model_count=None,
    )
