"""Contract tests for the ``codesearch`` tool (opencode parity).

The tool must:

1. Yield structured ``{path, line, column, text}`` hits so the LLM can
   chain straight into ``apply_patch`` without regex-parsing shell output.
2. Respect ``repo_root`` as the search ceiling.
3. Skip the heavy ignore dirs (``.git``, ``node_modules``, ``.venv`` …)
   so a mid-sized monorepo doesn't drown the result set.
4. Expose ``__tool_schema__`` for :class:`~lyra_core.agent.loop.AgentLoop`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.tools.codesearch import make_codesearch_tool


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(
        "def hello():\n    return 42  # TODO: fix\n", encoding="utf-8"
    )
    (tmp_path / "pkg" / "b.py").write_text(
        "class Widget:\n    # TODO: document\n    pass\n", encoding="utf-8"
    )
    # An ignore-dir that must NOT show in results.
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "noise.js").write_text(
        "// TODO: ignore me\n", encoding="utf-8"
    )
    # Binary-ish suffix we skip.
    (tmp_path / "pkg" / "bin.pyc").write_bytes(b"\x00\x01 TODO \xff")
    return tmp_path


def test_tool_schema_is_present_and_named(tmp_repo: Path) -> None:
    tool = make_codesearch_tool(repo_root=tmp_repo)
    schema = getattr(tool, "__tool_schema__", None)
    assert schema is not None
    assert schema["name"] == "codesearch"
    assert "pattern" in schema["parameters"]["required"]


def test_returns_structured_hits_with_path_line_column(tmp_repo: Path) -> None:
    tool = make_codesearch_tool(repo_root=tmp_repo)
    result = tool("TODO")
    hits = result["hits"]
    assert hits, "expected at least one hit for TODO"
    for h in hits:
        assert set(h) >= {"path", "line", "column", "text"}
        assert h["line"] >= 1
        assert h["column"] >= 1


def test_skips_ignore_directories(tmp_repo: Path) -> None:
    tool = make_codesearch_tool(repo_root=tmp_repo)
    result = tool("TODO")
    paths = {h["path"] for h in result["hits"]}
    assert not any(p.startswith("node_modules/") for p in paths), (
        f"codesearch must skip node_modules; got: {paths}"
    )


def test_skips_non_text_suffixes(tmp_repo: Path) -> None:
    tool = make_codesearch_tool(repo_root=tmp_repo)
    result = tool("TODO")
    paths = {h["path"] for h in result["hits"]}
    assert "pkg/bin.pyc" not in paths, "binary suffix must be skipped"


def test_case_insensitive_toggle(tmp_repo: Path) -> None:
    tool = make_codesearch_tool(repo_root=tmp_repo)
    case_sensitive = tool("todo")
    case_insensitive = tool("todo", case_insensitive=True)
    assert len(case_sensitive["hits"]) == 0, (
        "case-sensitive search for lowercase 'todo' should miss TODO"
    )
    assert len(case_insensitive["hits"]) >= 1, (
        "case-insensitive search for 'todo' should match TODO"
    )


def test_literal_pattern_when_regex_flag_is_false(tmp_repo: Path) -> None:
    """Regex metacharacters in the pattern must be escaped when regex=False."""
    (tmp_repo / "pkg" / "dot.py").write_text(
        "x = a.b.c\n", encoding="utf-8"
    )
    tool = make_codesearch_tool(repo_root=tmp_repo)
    result = tool("a.b.c", regex=False)
    assert any(
        "a.b.c" in h["text"] for h in result["hits"]
    ), "literal search must match a.b.c verbatim"


def test_empty_pattern_surfaces_error_not_crash(tmp_repo: Path) -> None:
    tool = make_codesearch_tool(repo_root=tmp_repo)
    result = tool("")
    assert result["hits"] == []
    assert "error" in result
