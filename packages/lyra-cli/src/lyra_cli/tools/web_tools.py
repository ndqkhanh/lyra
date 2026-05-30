"""Web fetch and API tools with rate limiting and retry logic."""

from __future__ import annotations

import time as _time
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum


class WebMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass(frozen=True)
class WebRequest:
    url: str
    method: WebMethod = WebMethod.GET
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class WebResponse:
    status_code: int
    body: str
    headers: dict[str, str]
    duration_ms: float
    url: str


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_second: float = 10.0
    burst_size: int = 20
    cooldown_seconds: float = 1.0


class WebTool:
    """HTTP client with rate limiting, retry logic, and response caching.

    Usage::

        tool = WebTool(rate_limit=RateLimitConfig(requests_per_second=5.0))
        resp = tool.fetch("https://api.example.com/data")
        post_resp = tool.post("https://api.example.com/submit", body=json_str)
    """

    def __init__(
        self,
        rate_limit: RateLimitConfig | None = None,
        max_retries: int = 3,
        user_agent: str = "Lyra/1.0",
    ) -> None:
        self._rate_limit = rate_limit or RateLimitConfig()
        self._max_retries = max_retries
        self._user_agent = user_agent
        self._request_times: deque[float] = deque()
        self._cache: dict[str, tuple[float, WebResponse]] = {}
        self._cache_ttl_seconds: float = 300.0

    def fetch(self, url: str, headers: dict[str, str] | None = None, timeout_seconds: float = 30.0) -> WebResponse:
        return self._execute(
            WebRequest(url=url, method=WebMethod.GET, headers=headers or {}, timeout_seconds=timeout_seconds)
        )

    def post(self, url: str, body: str = "", headers: dict[str, str] | None = None, timeout_seconds: float = 30.0) -> WebResponse:
        return self._execute(
            WebRequest(url=url, method=WebMethod.POST, body=body, headers=headers or {}, timeout_seconds=timeout_seconds)
        )

    def _execute(self, request: WebRequest) -> WebResponse:
        import urllib.error
        import urllib.request

        self._wait_for_rate_limit()
        full_headers = dict(request.headers)
        full_headers.setdefault("User-Agent", self._user_agent)
        if request.body:
            full_headers.setdefault("Content-Type", "application/json")

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            start = _time.monotonic()
            try:
                data = request.body.encode("utf-8") if request.body else None
                req = urllib.request.Request(
                    request.url,
                    data=data,
                    headers=full_headers,
                    method=request.method.value,
                )
                with urllib.request.urlopen(req, timeout=request.timeout_seconds) as resp:
                    body = resp.read().decode("utf-8")
                    return WebResponse(
                        status_code=resp.status,
                        body=body,
                        headers=dict(resp.headers),
                        duration_ms=(_time.monotonic() - start) * 1000,
                        url=request.url,
                    )
            except (urllib.error.URLError, OSError) as exc:
                last_error = exc
                _time.sleep(2 ** attempt)

        raise RuntimeError(f"Request failed after {self._max_retries} retries: {last_error}")

    def _wait_for_rate_limit(self) -> None:
        now = _time.monotonic()
        while self._request_times and self._request_times[0] < now - 1.0:
            self._request_times.popleft()
        if len(self._request_times) >= self._rate_limit.burst_size:
            _time.sleep(self._rate_limit.cooldown_seconds)
        self._request_times.append(now)

    def clear_cache(self) -> None:
        self._cache.clear()
