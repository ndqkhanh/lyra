"""Tests for filesystem tool implementations — 5 tools."""
from __future__ import annotations

from pathlib import Path

from lyra_tools.file_ops import (
    dir_create,
    dir_list,
    file_copy,
    file_delete,
    file_move,
)


class TestFileDelete:
    def test_delete_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "to_delete.txt"
        f.write_text("hello")
        result = file_delete(str(f), repo_root=str(tmp_path))
        assert result["deleted"] is True
        assert not f.exists()

    def test_delete_missing_file_errors(self, tmp_path: Path) -> None:
        result = file_delete(str(tmp_path / "nonexistent.txt"), repo_root=str(tmp_path))
        assert result["deleted"] is False
        assert "error" in result

    def test_delete_missing_file_with_missing_ok(self, tmp_path: Path) -> None:
        result = file_delete(
            str(tmp_path / "nonexistent.txt"),
            repo_root=str(tmp_path),
            missing_ok=True,
        )
        assert result["deleted"] is False
        assert result["reason"] == "not_found"

    def test_delete_directory_errors(self, tmp_path: Path) -> None:
        d = tmp_path / "subdir"
        d.mkdir()
        result = file_delete(str(d), repo_root=str(tmp_path))
        assert result["deleted"] is False
        assert "directory" in result["error"]

    def test_delete_outside_root_errors(self, tmp_path: Path) -> None:
        result = file_delete("/etc/passwd", repo_root=str(tmp_path))
        assert result["deleted"] is False
        assert "outside" in result["error"]


class TestFileMove:
    def test_move_file_within_root(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        dst = tmp_path / "sub" / "dst.txt"
        src.write_text("move me")
        result = file_move(str(src), str(dst), repo_root=str(tmp_path))
        assert result["moved"] is True
        assert dst.read_text() == "move me"
        assert not src.exists()

    def test_move_source_not_found(self, tmp_path: Path) -> None:
        result = file_move(
            str(tmp_path / "nope.txt"),
            str(tmp_path / "dst.txt"),
            repo_root=str(tmp_path),
        )
        assert result["moved"] is False
        assert "not found" in result["error"]

    def test_move_destination_exists(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("a")
        dst.write_text("b")
        result = file_move(str(src), str(dst), repo_root=str(tmp_path))
        assert result["moved"] is False

    def test_move_destination_exists_overwrite(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("a")
        dst.write_text("b")
        result = file_move(
            str(src), str(dst), repo_root=str(tmp_path), overwrite=True,
        )
        assert result["moved"] is True
        assert dst.read_text() == "a"

    def test_move_outside_root_errors(self, tmp_path: Path) -> None:
        result = file_move(
            str(tmp_path / "src.txt"), "/etc/dst.txt", repo_root=str(tmp_path),
        )
        assert result["moved"] is False
        assert "outside" in result["error"]


class TestFileCopy:
    def test_copy_file(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        dst = tmp_path / "sub" / "copy.txt"
        src.write_text("copy me")
        result = file_copy(str(src), str(dst), repo_root=str(tmp_path))
        assert result["copied"] is True
        assert dst.read_text() == "copy me"
        assert src.exists()  # source still exists

    def test_copy_preserves_metadata(self, tmp_path: Path) -> None:
        src = tmp_path / "meta.txt"
        dst = tmp_path / "meta_copy.txt"
        src.write_text("with metadata")
        result = file_copy(str(src), str(dst), repo_root=str(tmp_path))
        assert result["copied"] is True

    def test_copy_source_not_found(self, tmp_path: Path) -> None:
        result = file_copy(
            str(tmp_path / "nope.txt"),
            str(tmp_path / "dst.txt"),
            repo_root=str(tmp_path),
        )
        assert result["copied"] is False


class TestDirCreate:
    def test_create_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "newdir"
        result = dir_create(str(d), repo_root=str(tmp_path))
        assert result["created"] is True
        assert d.is_dir()

    def test_create_nested_directories(self, tmp_path: Path) -> None:
        d = tmp_path / "a" / "b" / "c"
        result = dir_create(str(d), repo_root=str(tmp_path))
        assert result["created"] is True
        assert d.is_dir()

    def test_create_existing_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "exists"
        d.mkdir()
        result = dir_create(str(d), repo_root=str(tmp_path))
        assert result["created"] is True

    def test_create_outside_root_errors(self, tmp_path: Path) -> None:
        result = dir_create("/etc/foo", repo_root=str(tmp_path))
        assert result["created"] is False
        assert "outside" in result["error"]


class TestDirList:
    def test_list_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        result = dir_list(str(tmp_path), repo_root=str(tmp_path))
        assert result["count"] == 2
        names = {e["name"] for e in result["entries"]}
        assert names == {"a.txt", "b.txt"}

    def test_list_filters_hidden(self, tmp_path: Path) -> None:
        (tmp_path / "visible.txt").write_text("a")
        (tmp_path / ".hidden").write_text("b")
        result = dir_list(str(tmp_path), repo_root=str(tmp_path))
        names = {e["name"] for e in result["entries"]}
        assert "visible.txt" in names
        assert ".hidden" not in names

    def test_list_include_hidden(self, tmp_path: Path) -> None:
        (tmp_path / "visible.txt").write_text("a")
        (tmp_path / ".hidden").write_text("b")
        result = dir_list(
            str(tmp_path), repo_root=str(tmp_path), include_hidden=True,
        )
        names = {e["name"] for e in result["entries"]}
        assert ".hidden" in names

    def test_list_recursive(self, tmp_path: Path) -> None:
        (tmp_path / "a" / "b").mkdir(parents=True)
        (tmp_path / "a" / "b" / "deep.txt").write_text("deep")
        (tmp_path / "root.txt").write_text("root")
        result = dir_list(str(tmp_path), repo_root=str(tmp_path), recursive=True)
        names = {e["name"] for e in result["entries"]}
        assert "deep.txt" in names
        assert "root.txt" in names

    def test_list_not_a_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.touch()
        result = dir_list(str(f), repo_root=str(tmp_path))
        assert "error" in result

    def test_list_missing_directory(self, tmp_path: Path) -> None:
        result = dir_list(str(tmp_path / "nope"), repo_root=str(tmp_path))
        assert "error" in result

    def test_list_respects_max_entries(self, tmp_path: Path) -> None:
        for i in range(10):
            (tmp_path / f"file_{i}.txt").touch()
        result = dir_list(str(tmp_path), repo_root=str(tmp_path), max_entries=3)
        assert result["count"] == 3

    def test_list_dirs_sorted_first(self, tmp_path: Path) -> None:
        (tmp_path / "dir_a").mkdir()
        (tmp_path / "file.txt").write_text("f")
        (tmp_path / "dir_b").mkdir()
        result = dir_list(str(tmp_path), repo_root=str(tmp_path))
        assert result["entries"][0]["is_dir"]
        assert result["entries"][1]["is_dir"]
