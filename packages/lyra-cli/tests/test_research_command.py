"""Tests for the v3.12 ``/research`` deep-research slash command."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import (
    COMMAND_REGISTRY,
    InteractiveSession,
    _cmd_research,
    command_spec,
)


def _new_session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="m", mode="agent")


def _patch_web_tools(
    monkeypatch: pytest.MonkeyPatch,
    *,
    search_payload: dict,
    fetch_payload: dict,
):
    """Replace the make_web_*_tool factories with stubs producing fixed payloads."""
    def fake_search_factory():
        return lambda **kwargs: search_payload

    def fake_fetch_factory():
        return lambda **kwargs: fetch_payload

    monkeypatch.setattr(
        "lyra_core.tools.web_search.make_web_search_tool", fake_search_factory
    )
    monkeypatch.setattr(
        "lyra_core.tools.web_fetch.make_web_fetch_tool", fake_fetch_factory
    )


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestCmdResearchParsing:
    def test_empty_args_prints_usage(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_research(s, "")
        assert "usage" in result.output.lower()

    def test_depth_flag_parsed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}

        def fake_search_factory():
            def _search(**kwargs):
                captured["kwargs"] = kwargs
                return {"count": 0, "error": "(stubbed)"}
            return _search

        monkeypatch.setattr(
            "lyra_core.tools.web_search.make_web_search_tool", fake_search_factory
        )
        s = _new_session(tmp_path)
        _cmd_research(s, "claude api --depth 7")
        # --depth 7 means we ask for max(7, 5) = 7 results.
        assert captured["kwargs"]["max_results"] == 7
        assert captured["kwargs"]["query"] == "claude api"

    def test_invalid_depth_rejected(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_research(s, "claude --depth notanumber")
        assert "integer" in result.output.lower()

    def test_invalid_time_range_rejected(self, tmp_path: Path) -> None:
        s = _new_session(tmp_path)
        result = _cmd_research(s, "claude --time forever")
        assert "must be day/week/month/year" in result.output.lower()

    def test_domain_flag_passes_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}

        def fake_search_factory():
            def _search(**kwargs):
                captured["kwargs"] = kwargs
                return {"count": 0, "error": "(stubbed)"}
            return _search

        monkeypatch.setattr(
            "lyra_core.tools.web_search.make_web_search_tool", fake_search_factory
        )
        s = _new_session(tmp_path)
        _cmd_research(
            s, "claude --domain anthropic.com --domain docs.anthropic.com"
        )
        assert captured["kwargs"]["domains_allow"] == [
            "anthropic.com", "docs.anthropic.com",
        ]


# ---------------------------------------------------------------------------
# Successful research dispatch
# ---------------------------------------------------------------------------


class TestCmdResearchHappyPath:
    def test_renders_markdown_with_excerpts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_web_tools(
            monkeypatch,
            search_payload={
                "count": 2,
                "provider": "tavily",
                "results": [
                    {
                        "title": "Claude API guide",
                        "url": "https://example.com/a",
                        "snippet": "tutorial intro",
                    },
                    {
                        "title": "API basics",
                        "url": "https://example.com/b",
                        "snippet": "what is an API",
                    },
                ],
            },
            fetch_payload={
                "text": "full body of the fetched page",
                "error": None,
            },
        )
        s = _new_session(tmp_path)
        result = _cmd_research(s, "claude api --depth 2")
        out = result.output
        assert "# /research: claude api" in out
        assert "tavily" in out
        assert "Claude API guide" in out
        assert "https://example.com/a" in out
        # The fetch excerpt should be present (markdown code-fenced).
        assert "full body of the fetched page" in out

    def test_handles_fetch_errors_gracefully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_web_tools(
            monkeypatch,
            search_payload={
                "count": 1,
                "provider": "duckduckgo",
                "results": [
                    {
                        "title": "broken page",
                        "url": "https://example.com/x",
                        "snippet": "",
                    }
                ],
            },
            fetch_payload={"text": "", "error": "http 503"},
        )
        s = _new_session(tmp_path)
        result = _cmd_research(s, "test")
        # The "fetch failed" inline note should appear; the command
        # shouldn't crash.
        assert "fetch failed" in result.output.lower()
        assert "http 503" in result.output


# ---------------------------------------------------------------------------
# Empty / failure passthrough
# ---------------------------------------------------------------------------


def test_empty_search_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_web_tools(
        monkeypatch,
        search_payload={
            "count": 0,
            "error": "no provider returned results.",
            "results": [],
        },
        fetch_payload={"text": "", "error": None},
    )
    s = _new_session(tmp_path)
    result = _cmd_research(s, "something obscure")
    assert "/research" in result.output
    assert "no provider returned" in result.output


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_research_command_registered() -> None:
    spec = command_spec("research")
    assert spec is not None
    assert spec.name == "research"
    assert "research" in {s.name for s in COMMAND_REGISTRY}
