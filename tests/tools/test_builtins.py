"""
Tests for built-in tool handlers (builtins.py).

Covers:
- _read_file: success, missing path, FileNotFound, IsADirectoryError, PermissionError, OSError
- _write_file: success, missing path/ content, PermissionError, IsADirectoryError, OSError
- _run_bash: success, missing command, timeout, CancelledError, OSError
- _web_search: stub response
- register_builtins: returns 4 correct ToolDef entries
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from lyra.tools.builtins import (
    _read_file,
    _run_bash,
    _web_search,
    _write_file,
    register_builtins,
)


# =============================================================================
# _read_file
# =============================================================================


class TestReadFile:
    async def test_read_success(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            tmp_path = f.name
        try:
            result = await _read_file(path=tmp_path)
            assert result["success"] is True
            assert result["output"] == "hello world"
        finally:
            os.unlink(tmp_path)

    async def test_missing_path(self) -> None:
        result = await _read_file()
        assert result["success"] is False
        assert "path" in result.get("error", "").lower()

    async def test_file_not_found(self) -> None:
        result = await _read_file(path="/nonexistent/file_xyz")
        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    async def test_is_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await _read_file(path=tmpdir)
            assert result["success"] is False
            assert "directory" in result.get("error", "").lower()

    async def test_custom_encoding(self) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"cafe\xc3\xa9")
            tmp_path = f.name
        try:
            result = await _read_file(path=tmp_path, encoding="utf-8")
            assert result["success"] is True
            assert "caf" in result["output"]
        finally:
            os.unlink(tmp_path)


# =============================================================================
# _write_file
# =============================================================================


class TestWriteFile:
    async def test_write_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.txt"
            result = await _write_file(path=str(path), content="test content")
            assert result["success"] is True
            assert path.read_text() == "test content"

    async def test_missing_path(self) -> None:
        result = await _write_file(content="hello")
        assert result["success"] is False
        assert "path" in result.get("error", "").lower()

    async def test_empty_content_is_valid(self) -> None:
        """Writing empty content is valid — defaults to empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.txt"
            result = await _write_file(path=str(path))
            assert result["success"] is True
            assert path.read_text() == ""

    async def test_none_content(self) -> None:
        result = await _write_file(path="/tmp/foo.txt", content=None)
        assert result["success"] is False
        assert "content" in result.get("error", "").lower()

    async def test_write_creates_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "nested" / "out.txt"
            result = await _write_file(path=str(path), content="nested")
            assert result["success"] is True
            assert path.exists()

    async def test_custom_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.txt"
            result = await _write_file(path=str(path), content="hello", encoding="utf-16")
            assert result["success"] is True
            assert "bytes" in result["output"]


# =============================================================================
# _run_bash
# =============================================================================


class TestRunBash:
    async def test_success(self) -> None:
        result = await _run_bash(command="echo hello from lyra")
        assert result["success"] is True
        assert "hello from lyra" in result["output"]

    async def test_empty_command(self) -> None:
        result = await _run_bash(command="")
        assert result["success"] is False
        assert "command" in result.get("error", "").lower()

    async def test_nonzero_exit(self) -> None:
        result = await _run_bash(command="exit 42")
        assert result["success"] is False
        assert "exit code 42" in result.get("error", "") or "42" in result.get("error", "")

    async def test_stderr_captured(self) -> None:
        result = await _run_bash(command="echo out && echo err >&2")
        assert result["success"] is True
        assert "out" in result["output"]
        assert "err" in result["output"]

    async def test_custom_timeout(self) -> None:
        """A sufficiently long timeout should still let a fast command through."""
        result = await _run_bash(command="echo ok", timeout=60)
        assert result["success"] is True
        assert "ok" in result["output"]

    async def test_timeout_raises_error(self) -> None:
        """Very short timeout on a sleeping command."""
        result = await _run_bash(command="sleep 10", timeout=0.1)
        assert result["success"] is False
        assert "timed out" in result.get("error", "").lower()


# =============================================================================
# _web_search
# =============================================================================


class TestWebSearch:
    async def test_stub_response(self) -> None:
        result = await _web_search(query="test query")
        assert result["success"] is False
        assert "stub" in result.get("error", "").lower()

    async def test_query_accepted(self) -> None:
        """The query kwarg should be consumed without error."""
        result = await _web_search(query="anything")
        assert result["success"] is False  # stub always fails


# =============================================================================
# register_builtins
# =============================================================================


class TestRegisterBuiltins:
    def test_returns_four_tools(self) -> None:
        tools = register_builtins()
        assert len(tools) == 4

    def test_readfile_def(self) -> None:
        tools = register_builtins()
        readfile = next(t for t in tools if t.name == "ReadFile")
        assert readfile.description != ""
        assert "file" in readfile.capabilities
        assert "path" in readfile.parameters.get("required", [])
        assert readfile.handler is _read_file

    def test_writefile_def(self) -> None:
        tools = register_builtins()
        writefile = next(t for t in tools if t.name == "WriteFile")
        assert writefile.description != ""
        assert "file" in writefile.capabilities
        assert "path" in writefile.parameters.get("required", [])
        assert "content" in writefile.parameters.get("required", [])

    def test_runbash_def(self) -> None:
        tools = register_builtins()
        runbash = next(t for t in tools if t.name == "RunBash")
        assert runbash.description != ""
        assert "shell" in runbash.capabilities
        assert "command" in runbash.parameters.get("required", [])

    def test_websearch_def(self) -> None:
        tools = register_builtins()
        web = next(t for t in tools if t.name == "WebSearch")
        assert web.description != ""
        assert "network" in web.capabilities
        assert "query" in web.parameters.get("required", [])


# =============================================================================
# Additional coverage: error paths
# =============================================================================


class TestBuiltinErrorPaths:
    """Error paths in built-in tools requiring mocks."""

    async def test_read_file_permission_error(self) -> None:
        from unittest.mock import patch

        with patch("lyra.tools.builtins.Path.read_text", side_effect=PermissionError("denied")):
            result = await _read_file(path="/some/protected/file.txt")
            assert result["success"] is False
            assert "permission" in result.get("error", "").lower()

    async def test_read_file_os_error(self) -> None:
        from unittest.mock import patch

        with patch("lyra.tools.builtins.Path.read_text", side_effect=OSError("disk failure")):
            result = await _read_file(path="/some/file.txt")
            assert result["success"] is False
            assert "disk failure" in result.get("error", "")

    async def test_write_file_permission_error(self) -> None:
        from unittest.mock import patch, MagicMock

        m = MagicMock()
        m.write_text.side_effect = PermissionError("denied")
        m.parent = MagicMock()
        m.parent.mkdir = MagicMock()

        with patch("lyra.tools.builtins.Path", return_value=m):
            result = await _write_file(path="/protected/file.txt", content="data")
            assert result["success"] is False
            assert "permission" in result.get("error", "").lower()

    async def test_write_file_is_directory_error(self) -> None:
        from unittest.mock import patch, MagicMock

        m = MagicMock()
        m.write_text.side_effect = IsADirectoryError("is a dir")
        m.parent = MagicMock()
        m.parent.mkdir = MagicMock()

        with patch("lyra.tools.builtins.Path", return_value=m):
            result = await _write_file(path="/some/dir", content="data")
            assert result["success"] is False
            assert "directory" in result.get("error", "").lower()

    async def test_write_file_os_error(self) -> None:
        from unittest.mock import patch, MagicMock

        m = MagicMock()
        m.write_text.side_effect = OSError("disk full")
        m.parent = MagicMock()
        m.parent.mkdir = MagicMock()

        with patch("lyra.tools.builtins.Path", return_value=m):
            result = await _write_file(path="/some/file.txt", content="data")
            assert result["success"] is False
            assert "disk full" in result.get("error", "")

    async def test_run_bash_process_creation_error(self) -> None:
        from unittest.mock import patch

        with patch("asyncio.create_subprocess_shell", side_effect=OSError("no fork")):
            result = await _run_bash(command="echo hi")
            assert result["success"] is False
            assert "no fork" in result.get("error", "")

    async def test_run_bash_communicate_error(self) -> None:
        from unittest.mock import patch

        class MockProc:
            returncode = 1
            async def communicate(self):
                raise OSError("pipe broken")
            def kill(self):
                pass
            async def wait(self):
                pass

        with patch("asyncio.create_subprocess_shell", return_value=MockProc()):
            result = await _run_bash(command="echo hi")
            assert result["success"] is False
            assert "pipe broken" in result.get("error", "")
