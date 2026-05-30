"""Tests for search_tools module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra_cli.tools.search_tools import (
    FileIndex,
    ReplaceOperation,
    SearchMatch,
    SearchMode,
    SearchResult,
    SearchTool,
)


@pytest.fixture
def search_tool():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "a.py").write_text("def hello():\n    return 'world'\n")
        (root / "b.py").write_text("def goodbye():\n    return 'moon'\n")
        (root / "data.txt").write_text("hello world\ngoodbye moon\n")
        (root / "sub").mkdir()
        (root / "sub" / "nested.py").write_text("# nested\nhello()\n")
        yield SearchTool(root=str(root))


class TestSearchTool:
    def test_exact_search(self, search_tool):
        result = search_tool.search("hello", mode=SearchMode.EXACT)
        assert len(result.matches) >= 2  # a.py and data.txt

    def test_regex_search(self, search_tool):
        result = search_tool.search(r"def \w+", mode=SearchMode.REGEX)
        func_matches = [
            m for m in result.matches
            if m.file_path.endswith(".py")
        ]
        assert len(func_matches) >= 2

    def test_file_pattern_filter(self, search_tool):
        result = search_tool.search("hello", file_pattern="*.txt")
        assert len(result.matches) >= 1
        txt_matches = [m for m in result.matches if m.file_path.endswith(".txt")]
        assert len(txt_matches) >= 1

    def test_search_no_results(self, search_tool):
        result = search_tool.search("zzzzz_nonexistent_zzzzz")
        assert len(result.matches) == 0

    def test_search_context_lines(self, search_tool):
        result = search_tool.search("hello", mode=SearchMode.EXACT, context_lines=1)
        assert len(result.matches) > 0

    def test_max_results_truncation(self, search_tool):
        result = search_tool.search("def", mode=SearchMode.REGEX, max_results=1)
        assert result.truncated

    def test_replace_all_dry_run(self, search_tool):
        ops = search_tool.replace_all("world", "earth", file_pattern="*.txt")
        assert len(ops) >= 1
        # Verify no actual change occurred
        result = search_tool.search("earth")
        assert len(result.matches) == 0

    def test_replace_all_apply(self, search_tool):
        ops = search_tool.replace_all("world", "earth", file_pattern="*.txt", dry_run=False)
        assert len(ops) >= 1
        result = search_tool.search("earth")
        assert len(result.matches) >= 1

    def test_glob_search(self, search_tool):
        result = search_tool.search("hello", mode=SearchMode.GLOB)
        assert len(result.matches) >= 2


class TestSearchMatch:
    def test_match_creation(self):
        m = SearchMatch(
            file_path="test.py",
            line_number=10,
            line_content="hello world",
            match_start=0,
            match_end=5,
        )
        assert m.file_path == "test.py"
        assert m.line_number == 10

    def test_match_immutability(self):
        m = SearchMatch(file_path="f.py", line_number=1, line_content="x", match_start=0, match_end=1)
        with pytest.raises(Exception):
            m.file_path = "other.py"


class TestSearchResult:
    def test_result_immutability(self):
        m = SearchMatch(file_path="f.py", line_number=1, line_content="x", match_start=0, match_end=1)
        r = SearchResult(
            query="test",
            mode=SearchMode.EXACT,
            matches=(m,),
            total_files_searched=1,
            duration_ms=5.0,
        )
        with pytest.raises(Exception):
            r.query = "other"


class TestFileIndex:
    def test_index_creation(self):
        idx = FileIndex(root="/app", file_count=100, total_size_bytes=5000)
        assert idx.root == "/app"
        assert idx.file_count == 100

    def test_index_immutability(self):
        idx = FileIndex(root="/", file_count=0, total_size_bytes=0)
        with pytest.raises(Exception):
            idx.file_count = 10


class TestReplaceOperation:
    def test_operation_creation(self):
        op = ReplaceOperation(file_path="test.py", line_number=5, old_text="old", new_text="new")
        assert op.file_path == "test.py"
        assert not op.applied
