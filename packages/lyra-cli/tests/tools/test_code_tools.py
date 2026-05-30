"""Tests for code_tools module."""

from __future__ import annotations

import pytest

from lyra_cli.tools.code_tools import (
    CodeLanguage,
    CodeMetrics,
    CodeSymbol,
    CodeTool,
    SymbolKind,
)


@pytest.fixture
def tool():
    return CodeTool()


class TestCodeTool:
    def test_extract_python_function(self, tool):
        source = "def hello():\n    return 'world'\n"
        symbols = tool.extract_symbols(source)
        funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
        assert len(funcs) == 1
        assert funcs[0].name == "hello"

    def test_extract_python_class(self, tool):
        source = "class MyClass:\n    def method(self):\n        pass\n"
        symbols = tool.extract_symbols(source)
        classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "MyClass"

    def test_extract_python_imports(self, tool):
        source = "import os\nfrom pathlib import Path\n\n"
        symbols = tool.extract_symbols(source)
        imports = [s for s in symbols if s.kind == SymbolKind.IMPORT]
        assert len(imports) >= 1

    def test_extract_multiple_symbols(self, tool):
        source = (
            "import sys\n\n"
            "class App:\n"
            "    def run(self):\n"
            "        pass\n\n"
            "def main():\n"
            "    pass\n"
        )
        symbols = tool.extract_symbols(source)
        funcs = [s for s in symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)]
        assert len(funcs) >= 2  # main + run
        classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
        assert len(classes) == 1

    def test_extract_syntax_error(self, tool):
        source = "this is not valid python {{{"
        symbols = tool.extract_symbols(source)
        assert symbols == []

    def test_extract_docstring(self, tool):
        source = 'def foo():\n    """Doc string."""\n    pass\n'
        symbols = tool.extract_symbols(source)
        funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
        assert len(funcs) == 1
        assert "Doc string" in funcs[0].docstring

    def test_compute_metrics(self, tool):
        source = "# comment\n\n\ndef foo():\n    return 1\n\n\nclass Bar:\n    pass\n"
        metrics = tool.compute_metrics(source, "test.py")
        assert metrics.total_lines > 0
        assert metrics.function_count == 1
        assert metrics.class_count == 1
        assert metrics.file_path == "test.py"

    def test_compute_metrics_empty(self, tool):
        metrics = tool.compute_metrics("")
        assert metrics.total_lines == 0
        assert metrics.function_count == 0

    def test_metrics_with_complex_code(self, tool):
        source = "\n".join(
            f"def func_{i}():\n    return {i}\n" for i in range(10)
        )
        metrics = tool.compute_metrics(source)
        assert metrics.function_count == 10
        assert metrics.avg_function_length > 0


class TestCodeLanguage:
    def test_language_values(self):
        assert CodeLanguage.PYTHON == "python"
        assert CodeLanguage.TYPESCRIPT == "typescript"


class TestSymbolKind:
    def test_kind_values(self):
        assert SymbolKind.FUNCTION == "function"
        assert SymbolKind.CLASS == "class"


class TestCodeSymbol:
    def test_symbol_creation(self):
        s = CodeSymbol(name="foo", kind=SymbolKind.FUNCTION, line=10, end_line=15)
        assert s.name == "foo"
        assert s.line == 10

    def test_symbol_immutability(self):
        s = CodeSymbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=1)
        with pytest.raises(Exception):
            s.name = "bar"


class TestCodeMetrics:
    def test_metrics_immutability(self):
        m = CodeMetrics(
            file_path="test.py",
            total_lines=100,
            code_lines=80,
            comment_lines=10,
            blank_lines=10,
            function_count=5,
            class_count=2,
            complexity_score=9,
            avg_function_length=12.0,
        )
        with pytest.raises(Exception):
            m.total_lines = 200
