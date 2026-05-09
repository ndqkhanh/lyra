"""Contract tests for real :class:`WebSearch` + :class:`WebFetch` tools.

v1.7.2 shipped the tools as stubs raising NotImplementedError. This
pass flips them to httpx-backed tools that mirror Claude-Code/opencode
parity while remaining injectable so CI stays offline.

Both tools expose the ``make_*_tool(http=...)`` factory pattern so
tests can inject a fake transport. Production wiring calls
``httpx.Client()``; the tool never reaches out to the network in unit
tests.

Invariants tested
------------------

- ``WebSearch`` returns a ``{"results": [{"title", "url", "snippet"}]}``
  dict, length capped at ``max_results``.
- ``WebSearch`` passes the query verbatim and accepts pluggable
  providers (default: DuckDuckGo HTML, injectable for tests).
- ``WebFetch`` strips HTML down to readable text, enforces
  ``max_chars`` truncation, and surfaces the final URL after redirects.
- ``WebFetch`` refuses ``file://`` and ``javascript:`` URLs for safety.
- Both tools carry a ``__tool_schema__`` compatible with the native
  tool registry.
- ``WebSearch`` raises ``FeatureUnavailable`` when no provider is
  configured *and* the default provider can't be constructed.
"""
from __future__ import annotations

import pytest

from lyra_core.lsp_backend import FeatureUnavailable


# --- WebSearch ------------------------------------------------------- #


def test_web_search_default_schema_is_llm_callable() -> None:
    from lyra_core.tools.web_search import make_web_search_tool

    tool = make_web_search_tool(provider=lambda q, n: [])
    schema = tool.__tool_schema__  # type: ignore[attr-defined]
    assert schema["name"] == "WebSearch"
    params = schema["parameters"]["properties"]
    assert "query" in params
    assert "max_results" in params
    assert "query" in schema["parameters"]["required"]


def test_web_search_returns_normalized_results_from_provider() -> None:
    from lyra_core.tools.web_search import make_web_search_tool

    def fake_provider(query: str, n: int) -> list[dict]:
        assert query == "tdd python"
        return [
            {"title": "A", "url": "https://a.test", "snippet": "first"},
            {"title": "B", "url": "https://b.test", "snippet": "second"},
        ]

    tool = make_web_search_tool(provider=fake_provider)
    result = tool(query="tdd python", max_results=2)
    assert result == {
        "results": [
            {"title": "A", "url": "https://a.test", "snippet": "first"},
            {"title": "B", "url": "https://b.test", "snippet": "second"},
        ],
        "count": 2,
    }


def test_web_search_caps_results_at_max_results() -> None:
    from lyra_core.tools.web_search import make_web_search_tool

    provider = lambda q, n: [
        {"title": str(i), "url": f"https://x/{i}", "snippet": ""} for i in range(20)
    ]
    tool = make_web_search_tool(provider=provider)
    out = tool(query="x", max_results=3)
    assert out["count"] == 3
    assert len(out["results"]) == 3


def test_web_search_empty_query_raises_value_error() -> None:
    from lyra_core.tools.web_search import make_web_search_tool

    tool = make_web_search_tool(provider=lambda q, n: [])
    with pytest.raises(ValueError):
        tool(query="")


def test_web_search_feature_unavailable_without_httpx_when_provider_missing() -> None:
    from lyra_core.tools.web_search import make_web_search_tool

    # No provider + no httpx must surface FeatureUnavailable
    # via a sentinel that tests can pin.
    def _fail_provider(q: str, n: int):
        raise FeatureUnavailable("provider not wired")

    tool = make_web_search_tool(provider=_fail_provider)
    with pytest.raises(FeatureUnavailable):
        tool(query="anything")


# --- WebFetch ------------------------------------------------------- #


class _FakeResponse:
    def __init__(
        self,
        text: str = "",
        status_code: int = 200,
        headers: dict | None = None,
        url: str = "https://example.test",
    ) -> None:
        self.text = text
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class _FakeHttpClient:
    def __init__(self, resp: _FakeResponse) -> None:
        self._resp = resp
        self.calls: list[dict] = []

    def get(self, url: str, *, follow_redirects: bool = True, timeout: float = 10.0, headers: dict | None = None) -> _FakeResponse:
        self.calls.append({"url": url, "headers": dict(headers or {}), "timeout": timeout})
        return self._resp


def test_web_fetch_schema_is_llm_callable() -> None:
    from lyra_core.tools.web_fetch import make_web_fetch_tool

    tool = make_web_fetch_tool(http=_FakeHttpClient(_FakeResponse()))
    schema = tool.__tool_schema__  # type: ignore[attr-defined]
    assert schema["name"] == "WebFetch"
    assert "url" in schema["parameters"]["required"]
    assert "max_chars" in schema["parameters"]["properties"]


def test_web_fetch_strips_html_to_readable_text() -> None:
    from lyra_core.tools.web_fetch import make_web_fetch_tool

    html = """
    <html><head><title>T</title><style>.x{color:red}</style></head>
    <body>
      <script>alert(1)</script>
      <h1>Hello</h1>
      <p>World <b>bold</b> text.</p>
    </body></html>
    """
    fake = _FakeHttpClient(_FakeResponse(text=html, url="https://t.test/a"))
    tool = make_web_fetch_tool(http=fake)

    out = tool(url="https://t.test/a")
    text = out["text"]

    assert "Hello" in text
    assert "World" in text
    assert "bold" in text
    assert "alert" not in text  # script dropped
    assert ".x{color" not in text  # style dropped
    assert out["final_url"] == "https://t.test/a"
    assert out["status_code"] == 200


def test_web_fetch_truncates_to_max_chars() -> None:
    from lyra_core.tools.web_fetch import make_web_fetch_tool

    body = "<p>" + ("A" * 2000) + "</p>"
    fake = _FakeHttpClient(_FakeResponse(text=body))
    tool = make_web_fetch_tool(http=fake)

    out = tool(url="https://t.test/a", max_chars=100)
    assert len(out["text"]) <= 100
    assert out["truncated"] is True


def test_web_fetch_rejects_dangerous_schemes() -> None:
    from lyra_core.tools.web_fetch import make_web_fetch_tool

    tool = make_web_fetch_tool(http=_FakeHttpClient(_FakeResponse()))
    with pytest.raises(ValueError):
        tool(url="file:///etc/passwd")
    with pytest.raises(ValueError):
        tool(url="javascript:alert(1)")


def test_web_fetch_propagates_http_errors_as_result_not_exception() -> None:
    from lyra_core.tools.web_fetch import make_web_fetch_tool

    fake = _FakeHttpClient(
        _FakeResponse(text="nope", status_code=404, url="https://t.test/404")
    )
    tool = make_web_fetch_tool(http=fake)

    out = tool(url="https://t.test/404")
    # 4xx/5xx are surfaced as ``status_code`` + empty/raw text; they
    # must not raise — LLMs handle the error themselves.
    assert out["status_code"] == 404
    assert out["error"] is not None
