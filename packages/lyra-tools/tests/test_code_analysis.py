"""Tests for code analysis tools."""
from __future__ import annotations

import pytest
from lyra_tools.code_analysis import (
    analyze_complexity,
    extract_imports,
    find_references,
    suggest_refactoring,
)


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository with test files."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Simple function
    simple_file = repo / "simple.py"
    simple_file.write_text("""
def simple_function(x):
    return x + 1
""")

    # Complex function with high complexity
    complex_file = repo / "complex.py"
    complex_file.write_text("""
def complex_function(x, y, z):
    # This function has cyclomatic complexity > 10
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(10):
                    if i % 2 == 0:
                        if i > 5:
                            result = x + y + z
                        else:
                            result = x + y
                    else:
                        if i < 3:
                            result = x - y
                        else:
                            result = y - z
            else:
                result = x + y
        else:
            result = x
    elif x < 0:
        if y < 0:
            result = -x - y
        else:
            result = -x
    else:
        result = 0
    return result
""")

    # File with imports
    imports_file = repo / "imports.py"
    imports_file.write_text("""
import os
import sys
from pathlib import Path
from typing import Any, Dict
from collections import defaultdict as dd
""")

    # Long function
    long_file = repo / "long.py"
    long_lines = ["def long_function():"]
    long_lines.extend([f"    x{i} = {i}" for i in range(60)])
    long_lines.append("    return x0")
    long_file.write_text("\n".join(long_lines))

    return repo


class TestAnalyzeComplexity:
    def test_simple_function_low_complexity(self, temp_repo):
        result = analyze_complexity(
            "simple.py",
            repo_root=str(temp_repo),
        )

        assert result["analyzed"] is True
        assert result["total_functions"] == 1
        assert result["functions"][0]["name"] == "simple_function"
        assert result["functions"][0]["complexity"] == 1
        assert result["functions"][0]["risk"] == "low"

    def test_complex_function_high_complexity(self, temp_repo):
        result = analyze_complexity(
            "complex.py",
            repo_root=str(temp_repo),
            threshold=5,
        )

        assert result["analyzed"] is True
        assert result["total_functions"] == 1
        func = result["functions"][0]
        assert func["name"] == "complex_function"
        assert func["complexity"] > 5
        assert func["risk"] == "high"

    def test_file_not_found_errors(self, temp_repo):
        result = analyze_complexity(
            "nonexistent.py",
            repo_root=str(temp_repo),
        )

        assert result["analyzed"] is False
        assert "error" in result

    def test_non_python_file_errors(self, temp_repo):
        txt_file = temp_repo / "test.txt"
        txt_file.write_text("not python")

        result = analyze_complexity(
            "test.txt",
            repo_root=str(temp_repo),
        )

        assert result["analyzed"] is False
        assert "error" in result

    def test_syntax_error_file(self, temp_repo):
        bad_file = temp_repo / "bad.py"
        bad_file.write_text("def bad_syntax(\n    invalid")

        result = analyze_complexity(
            "bad.py",
            repo_root=str(temp_repo),
        )

        assert result["analyzed"] is False
        assert "error" in result
        assert "line" in result


class TestFindReferences:
    def test_find_references_basic(self, temp_repo):
        result = find_references(
            "simple_function",
            repo_root=str(temp_repo),
        )

        assert "references" in result
        assert result["symbol"] == "simple_function"
        assert result["count"] >= 0

    def test_find_references_with_pattern(self, temp_repo):
        result = find_references(
            "def",
            repo_root=str(temp_repo),
            file_pattern="**/*.py",
        )

        assert result["count"] > 0

    def test_find_references_max_results(self, temp_repo):
        result = find_references(
            "def",
            repo_root=str(temp_repo),
            max_results=2,
        )

        assert result["count"] <= 2
        if result["count"] == 2:
            assert result["truncated"] is True


class TestExtractImports:
    def test_extract_imports_basic(self, temp_repo):
        result = extract_imports(
            "imports.py",
            repo_root=str(temp_repo),
        )

        assert result["extracted"] is True
        assert result["count"] > 0

        # Check for specific imports
        imports = result["imports"]
        import_modules = [imp["module"] for imp in imports if imp["type"] == "import"]
        assert "os" in import_modules
        assert "sys" in import_modules

    def test_extract_from_imports(self, temp_repo):
        result = extract_imports(
            "imports.py",
            repo_root=str(temp_repo),
        )

        from_imports = [
            imp for imp in result["imports"]
            if imp["type"] == "from_import"
        ]
        assert len(from_imports) > 0

        # Check for pathlib.Path
        pathlib_imports = [
            imp for imp in from_imports
            if imp["module"] == "pathlib"
        ]
        assert len(pathlib_imports) > 0

    def test_extract_imports_with_alias(self, temp_repo):
        result = extract_imports(
            "imports.py",
            repo_root=str(temp_repo),
        )

        # Check for aliased import (defaultdict as dd)
        aliased = [
            imp for imp in result["imports"]
            if imp.get("alias") == "dd"
        ]
        assert len(aliased) > 0

    def test_extract_imports_file_not_found(self, temp_repo):
        result = extract_imports(
            "nonexistent.py",
            repo_root=str(temp_repo),
        )

        assert result["extracted"] is False
        assert "error" in result


class TestSuggestRefactoring:
    def test_suggest_long_function(self, temp_repo):
        result = suggest_refactoring(
            "long.py",
            repo_root=str(temp_repo),
        )

        assert result["analyzed"] is True
        assert result["count"] > 0

        # Should suggest refactoring for long function
        long_func_suggestions = [
            s for s in result["suggestions"]
            if s["type"] == "long_function"
        ]
        assert len(long_func_suggestions) > 0

    def test_suggest_max_suggestions(self, temp_repo):
        result = suggest_refactoring(
            "long.py",
            repo_root=str(temp_repo),
            max_suggestions=1,
        )

        assert len(result["suggestions"]) <= 1

    def test_suggest_file_not_found(self, temp_repo):
        result = suggest_refactoring(
            "nonexistent.py",
            repo_root=str(temp_repo),
        )

        assert result["analyzed"] is False
        assert "error" in result
