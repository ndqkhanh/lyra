"""Tests for text_tools, file_tools, and data_tools modules."""

from __future__ import annotations

import json
import tempfile

import pytest

from lyra_cli.tools.data_tools import DataFormat, DataSchema, DataTool
from lyra_cli.tools.file_tools import FileInfo, FileOperation, FileTool
from lyra_cli.tools.text_tools import TextDiff, TextOperation, TextStats, TextTool


@pytest.fixture
def file_tool():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield FileTool(workspace_root=tmpdir)


@pytest.fixture
def text_tool():
    return TextTool()


@pytest.fixture
def data_tool():
    return DataTool()


# ── FileTool Tests ──


class TestFileTool:
    def test_write_and_read(self, file_tool):
        file_tool.write("test.txt", "hello world")
        assert file_tool.read("test.txt") == "hello world"

    def test_file_exists(self, file_tool):
        file_tool.write("data.txt", "content")
        assert file_tool.exists("data.txt")
        assert not file_tool.exists("missing.txt")

    def test_file_info(self, file_tool):
        file_tool.write("info.txt", "hello")
        info = file_tool.stat("info.txt")
        assert info.size_bytes == 5
        assert not info.is_dir

    def test_list_directory(self, file_tool):
        file_tool.write("a.txt", "a")
        file_tool.write("b.txt", "b")
        file_tool.write("sub/c.txt", "c")
        files = file_tool.list(".")
        assert len(files) >= 2

    def test_delete_file(self, file_tool):
        file_tool.write("del.txt", "x")
        file_tool.delete("del.txt")
        assert not file_tool.exists("del.txt")

    def test_copy_file(self, file_tool):
        file_tool.write("src.txt", "copy me")
        file_tool.copy("src.txt", "dst.txt")
        assert file_tool.read("dst.txt") == "copy me"

    def test_move_file(self, file_tool):
        file_tool.write("old.txt", "move me")
        file_tool.move("old.txt", "new.txt")
        assert not file_tool.exists("old.txt")
        assert file_tool.read("new.txt") == "move me"

    def test_read_missing_raises(self, file_tool):
        with pytest.raises(FileNotFoundError):
            file_tool.read("nope.txt")

    def test_path_traversal_blocked(self, file_tool):
        with pytest.raises(ValueError, match="Path traversal"):
            file_tool.resolve("../outside.txt")

    def test_glob_pattern(self, file_tool):
        file_tool.write("a.py", "x")
        file_tool.write("b.py", "y")
        file_tool.write("c.txt", "z")
        files = file_tool.list(".", pattern="*.py")
        assert len(files) == 2


class TestFileInfo:
    def test_file_info_creation(self):
        info = FileInfo(path="test.txt", size_bytes=100, is_dir=False, modified_at=123.0, permissions="644")
        assert info.path == "test.txt"
        assert info.size_bytes == 100

    def test_file_info_immutability(self):
        info = FileInfo(path="t.txt", size_bytes=0, is_dir=False, modified_at=0.0, permissions="000")
        with pytest.raises(Exception):
            info.path = "other.txt"


# ── TextTool Tests ──


class TestTextTool:
    def test_diff_additions(self, text_tool):
        diff = text_tool.diff("line1\nline2\n", "line1\nline2\nline3\n")
        assert diff.added_lines > 0
        assert diff.removed_lines == 0

    def test_diff_removals(self, text_tool):
        diff = text_tool.diff("line1\nline2\nline3\n", "line1\n")
        assert diff.removed_lines > 0

    def test_analyze(self, text_tool):
        stats = text_tool.analyze("hello world hello")
        assert stats.word_count == 3
        assert stats.unique_word_count == 2
        assert stats.char_count == 17

    def test_analyze_empty(self, text_tool):
        stats = text_tool.analyze("")
        assert stats.word_count == 0

    def test_transform_upper(self, text_tool):
        assert text_tool.transform("hello", TextOperation.UPPER) == "HELLO"

    def test_transform_lower(self, text_tool):
        assert text_tool.transform("HELLO", TextOperation.LOWER) == "hello"

    def test_transform_trim(self, text_tool):
        assert text_tool.transform("  hello  ", TextOperation.TRIM) == "hello"

    def test_extract_pattern(self, text_tool):
        matches = text_tool.extract_pattern("foo bar baz", r"\b\w{3}\b")
        assert len(matches) == 3

    def test_replace_pattern(self, text_tool):
        result = text_tool.replace_pattern("hello world", r"world", "there")
        assert result == "hello there"

    def test_transform_unknown_raises(self, text_tool):
        with pytest.raises(ValueError, match="Unknown operation"):
            text_tool.transform("text", "invalid_op")


class TestTextStats:
    def test_stats_immutability(self):
        s = TextStats(char_count=10, word_count=2, line_count=1, byte_count=10, avg_word_length=5.0, unique_word_count=2)
        with pytest.raises(Exception):
            s.char_count = 20


class TestTextDiff:
    def test_diff_immutability(self):
        d = TextDiff(added_lines=1, removed_lines=0, unchanged_lines=5, unified_diff="...")
        with pytest.raises(Exception):
            d.added_lines = 10


# ── DataTool Tests ──


class TestDataTool:
    def test_json_to_csv(self, data_tool):
        data = json.dumps([{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}])
        result = data_tool.transform(data, DataFormat.JSON, DataFormat.CSV)
        assert result.output_format == DataFormat.CSV
        assert result.row_count == 2
        assert "name,age" in result.output

    def test_json_to_jsonl(self, data_tool):
        data = json.dumps([{"a": 1}, {"a": 2}])
        result = data_tool.transform(data, DataFormat.JSON, DataFormat.JSONL)
        assert result.row_count == 2
        assert result.output.count("\n") == 1

    def test_csv_to_json(self, data_tool):
        data = "name,age\nAlice,30\nBob,25\n"
        result = data_tool.transform(data, DataFormat.CSV, DataFormat.JSON)
        assert result.output_format == DataFormat.JSON
        parsed = json.loads(result.output)
        assert len(parsed) == 2

    def test_single_object_to_csv(self, data_tool):
        data = json.dumps({"name": "Alice", "age": 30})
        result = data_tool.transform(data, DataFormat.JSON, DataFormat.CSV)
        assert result.row_count == 1

    def test_unsupported_transform(self, data_tool):
        result = data_tool.transform("{}", DataFormat.YAML, DataFormat.XML)
        assert result.error != ""

    def test_infer_schema(self, data_tool):
        data = json.dumps([
            {"name": "Alice", "age": 30, "email": None},
            {"name": "Bob", "age": 25, "email": "bob@test.com"},
        ])
        schema = data_tool.infer_schema(data)
        assert len(schema.fields) == 3
        assert schema.row_count == 2
        assert "email" in schema.nullable_fields

    def test_infer_schema_empty(self, data_tool):
        schema = data_tool.infer_schema("[]")
        assert schema.row_count == 0
        assert schema.fields == ()


class TestDataSchema:
    def test_schema_immutability(self):
        s = DataSchema(fields=("a", "b"), types={"a": "str"}, nullable_fields=(), row_count=10)
        with pytest.raises(Exception):
            s.fields = ("c",)


class TestDataFormat:
    def test_format_values(self):
        assert DataFormat.JSON == "json"
        assert DataFormat.CSV == "csv"
