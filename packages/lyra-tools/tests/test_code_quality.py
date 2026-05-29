"""Tests for code quality tool implementations — lint, format, complexity, dead imports."""
from __future__ import annotations

import ast
from pathlib import Path

from lyra_tools.code_quality import (
    _cyclomatic_complexity,
    code_complexity,
    code_dead_imports,
    code_format,
    code_lint,
)


class TestCodeComplexity:
    def test_simple_function(self) -> None:
        code = "def f(x):\n    return x + 1\n"
        tree = ast.parse(code)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        c = _cyclomatic_complexity(func)
        assert c == 1

    def test_if_adds_complexity(self) -> None:
        code = "def f(x):\n    if x > 0:\n        return 1\n    return 0\n"
        tree = ast.parse(code)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        c = _cyclomatic_complexity(func)
        assert c == 2

    def test_loop_adds_complexity(self) -> None:
        code = "def f(xs):\n    for x in xs:\n        print(x)\n"
        tree = ast.parse(code)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        c = _cyclomatic_complexity(func)
        assert c == 2

    def test_and_or_adds_complexity(self) -> None:
        code = "def f(a, b, c):\n    return a and b and c\n"
        tree = ast.parse(code)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        c = _cyclomatic_complexity(func)
        assert c == 3  # 1 + 2 extra bool operands

    def test_risk_levels(self) -> None:
        # Low: complexity <= 10
        low_code = "def f(x):\n    return x\n"
        tree = ast.parse(low_code)
        f = tree.body[0]
        assert isinstance(f, ast.FunctionDef)
        assert _cyclomatic_complexity(f) <= 10

    def test_complexity_file_smoke(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("def simple(x):\n    return x\n\ndef complex_fn(x, y):\n    if x:\n        return y\n    return None\n")
        result = code_complexity(str(f), repo_root=str(tmp_path))
        assert result["count"] == 2
        names = {fn["name"] for fn in result["functions"]}
        assert names == {"simple", "complex_fn"}

    def test_complexity_non_python_file(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello world")
        result = code_complexity(str(f), repo_root=str(tmp_path))
        assert "error" in result

    def test_complexity_syntax_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("this is not valid python {{{")
        result = code_complexity(str(f), repo_root=str(tmp_path))
        assert "error" in result

    def test_complexity_file_not_found(self, tmp_path: Path) -> None:
        result = code_complexity("nope.py", repo_root=str(tmp_path))
        assert "error" in result


class TestCodeLint:
    def test_lint_missing_file(self, tmp_path: Path) -> None:
        result = code_lint(str(tmp_path / "nope.py"), repo_root=str(tmp_path))
        assert "error" in result

    def test_lint_unsupported_linter(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        result = code_lint(str(f), repo_root=str(tmp_path), linter="nonexistent")
        assert "error" in result

    def test_lint_valid_file_smoke(self, tmp_path: Path) -> None:
        """Smoke test — ruff may or may not be installed."""
        f = tmp_path / "clean.py"
        f.write_text("def hello():\n    return 'world'\n")
        result = code_lint(str(f), repo_root=str(tmp_path))
        assert "path" in result


class TestCodeFormat:
    def test_format_missing_file(self, tmp_path: Path) -> None:
        result = code_format(str(tmp_path / "nope.py"), repo_root=str(tmp_path))
        assert "error" in result

    def test_format_check_only_smoke(self, tmp_path: Path) -> None:
        f = tmp_path / "fmt_test.py"
        f.write_text("x=1\ny  =2\n")
        result = code_format(str(f), repo_root=str(tmp_path), check_only=True)
        assert "path" in result

    def test_format_unsupported_formatter(self, tmp_path: Path) -> None:
        f = tmp_path / "t.py"
        f.write_text("x=1\n")
        result = code_format(str(f), repo_root=str(tmp_path), formatter="nonexistent")
        assert "error" in result


class TestCodeDeadImports:
    def test_dead_imports_missing_file(self, tmp_path: Path) -> None:
        result = code_dead_imports(str(tmp_path / "nope.py"), repo_root=str(tmp_path))
        assert "error" in result

    def test_dead_imports_smoke(self, tmp_path: Path) -> None:
        f = tmp_path / "with_imports.py"
        f.write_text("import os\nprint('hello')\n")
        result = code_dead_imports(str(f), repo_root=str(tmp_path))
        assert "path" in result
        assert "count" in result
