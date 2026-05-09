"""Red tests for the 5 native tools: Read, Glob, Grep, Edit, Write.

These tools are the kernel's filesystem surface. They must:
    - validate args via pydantic
    - respect a repo_root so they cannot escape the workspace
    - emit useful, tokenizer-bounded results
"""
from __future__ import annotations

from pathlib import Path

import pytest
from harness_core.tools import ToolError

from lyra_core.tools.builtin import (
    EditTool,
    GlobTool,
    GrepTool,
    ReadTool,
    WriteTool,
)

# ------------------------------------------------------------------
# Read
# ------------------------------------------------------------------


def test_read_reads_file(repo: Path) -> None:
    (repo / "hello.txt").write_text("line1\nline2\nline3\n")
    tool = ReadTool(repo_root=repo)
    out = tool.run(tool.ArgsModel(path="hello.txt"))
    assert "line1" in out and "line3" in out


def test_read_rejects_path_outside_repo(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path.parent / "escape.txt"
    outside.write_text("secret")
    tool = ReadTool(repo_root=repo)
    with pytest.raises(Exception) as excinfo:
        tool.run(tool.ArgsModel(path=str(outside)))
    assert "outside" in str(excinfo.value).lower() or "escape" in str(excinfo.value).lower()


def test_read_missing_file_raises_structured_error(repo: Path) -> None:
    tool = ReadTool(repo_root=repo)
    with pytest.raises(Exception) as excinfo:
        tool.run(tool.ArgsModel(path="does_not_exist.txt"))
    assert "not found" in str(excinfo.value).lower() or "no such" in str(excinfo.value).lower()


def test_read_tool_metadata() -> None:
    tool = ReadTool(repo_root=Path("/tmp"))
    assert tool.name == "Read"
    assert tool.writes is False
    assert tool.risk == "low"


def test_read_respects_limit(repo: Path) -> None:
    (repo / "big.txt").write_text("\n".join(f"line{i}" for i in range(100)))
    tool = ReadTool(repo_root=repo)
    out = tool.run(tool.ArgsModel(path="big.txt", limit=10))
    assert out.count("\n") <= 12  # 10 content lines + minor markers


# ------------------------------------------------------------------
# Glob
# ------------------------------------------------------------------


def test_glob_finds_files(repo: Path) -> None:
    (repo / "src" / "a.py").write_text("x")
    (repo / "src" / "b.py").write_text("x")
    (repo / "tests" / "c.py").write_text("x")
    tool = GlobTool(repo_root=repo)
    out = tool.run(tool.ArgsModel(pattern="src/*.py"))
    assert "a.py" in out and "b.py" in out and "c.py" not in out


def test_glob_recursive_pattern(repo: Path) -> None:
    (repo / "src" / "nested").mkdir(parents=True)
    (repo / "src" / "nested" / "deep.py").write_text("x")
    tool = GlobTool(repo_root=repo)
    out = tool.run(tool.ArgsModel(pattern="**/*.py"))
    assert "deep.py" in out


def test_glob_tool_metadata() -> None:
    tool = GlobTool(repo_root=Path("/tmp"))
    assert tool.name == "Glob"
    assert tool.writes is False


# ------------------------------------------------------------------
# Grep
# ------------------------------------------------------------------


def test_grep_finds_matches(repo: Path) -> None:
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src" / "a.py").write_text("def foo(): return 1\n")
    (repo / "src" / "b.py").write_text("def bar(): return 2\n")
    tool = GrepTool(repo_root=repo)
    out = tool.run(tool.ArgsModel(pattern="def foo"))
    assert "a.py" in out and "b.py" not in out


def test_grep_respects_path_filter(repo: Path) -> None:
    (repo / "src").mkdir(exist_ok=True)
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "src" / "a.py").write_text("needle\n")
    (repo / "tests" / "t.py").write_text("needle\n")
    tool = GrepTool(repo_root=repo)
    out = tool.run(tool.ArgsModel(pattern="needle", path="src"))
    assert "a.py" in out and "t.py" not in out


def test_grep_tool_metadata() -> None:
    tool = GrepTool(repo_root=Path("/tmp"))
    assert tool.name == "Grep"
    assert tool.writes is False


# ------------------------------------------------------------------
# Write
# ------------------------------------------------------------------


def test_write_creates_file(repo: Path) -> None:
    tool = WriteTool(repo_root=repo)
    tool.run(tool.ArgsModel(path="hello.txt", content="hi"))
    assert (repo / "hello.txt").read_text() == "hi"


def test_write_rejects_path_outside_repo(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path.parent / "escape.txt"
    tool = WriteTool(repo_root=repo)
    with pytest.raises(ToolError):
        tool.run(tool.ArgsModel(path=str(outside), content="x"))


def test_write_creates_parent_dirs(repo: Path) -> None:
    tool = WriteTool(repo_root=repo)
    tool.run(tool.ArgsModel(path="a/b/c.txt", content="x"))
    assert (repo / "a" / "b" / "c.txt").read_text() == "x"


def test_write_tool_metadata() -> None:
    tool = WriteTool(repo_root=Path("/tmp"))
    assert tool.name == "Write"
    assert tool.writes is True


# ------------------------------------------------------------------
# Edit
# ------------------------------------------------------------------


def test_edit_replaces_unique_substring(repo: Path) -> None:
    (repo / "a.txt").write_text("before middle after")
    tool = EditTool(repo_root=repo)
    tool.run(tool.ArgsModel(path="a.txt", old="middle", new="centre"))
    assert (repo / "a.txt").read_text() == "before centre after"


def test_edit_refuses_ambiguous_old(repo: Path) -> None:
    """Edit must refuse if `old` is not unique (safety invariant)."""
    (repo / "a.txt").write_text("foo foo foo")
    tool = EditTool(repo_root=repo)
    with pytest.raises(Exception) as excinfo:
        tool.run(tool.ArgsModel(path="a.txt", old="foo", new="bar"))
    assert "unique" in str(excinfo.value).lower() or "ambiguous" in str(excinfo.value).lower()


def test_edit_replace_all(repo: Path) -> None:
    (repo / "a.txt").write_text("foo foo foo")
    tool = EditTool(repo_root=repo)
    tool.run(tool.ArgsModel(path="a.txt", old="foo", new="bar", replace_all=True))
    assert (repo / "a.txt").read_text() == "bar bar bar"


def test_edit_refuses_if_old_not_found(repo: Path) -> None:
    (repo / "a.txt").write_text("hello")
    tool = EditTool(repo_root=repo)
    with pytest.raises(ToolError):
        tool.run(tool.ArgsModel(path="a.txt", old="goodbye", new="hi"))


def test_edit_tool_metadata() -> None:
    tool = EditTool(repo_root=Path("/tmp"))
    assert tool.name == "Edit"
    assert tool.writes is True


# ------------------------------------------------------------------
# Registration helper (used by loop to wire all Phase 1 tools at once)
# ------------------------------------------------------------------


def test_register_all_builtin_tools(repo: Path) -> None:
    from harness_core.tools import ToolRegistry

    from lyra_core.tools.builtin import register_builtin_tools

    registry = ToolRegistry()
    register_builtin_tools(registry, repo_root=repo)
    names = set(registry.names())
    assert {"Read", "Write", "Edit", "Glob", "Grep"} <= names
