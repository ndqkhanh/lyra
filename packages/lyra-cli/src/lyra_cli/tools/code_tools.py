"""Code analysis and transformation tools."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum


class CodeLanguage(StrEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    UNKNOWN = "unknown"


class SymbolKind(StrEnum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    MODULE = "module"


@dataclass(frozen=True)
class CodeSymbol:
    name: str
    kind: SymbolKind
    line: int
    end_line: int
    docstring: str = ""
    parent: str = ""


@dataclass(frozen=True)
class CodeMetrics:
    file_path: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    function_count: int
    class_count: int
    complexity_score: int
    avg_function_length: float


@dataclass(frozen=True)
class LintFinding:
    file_path: str
    line: int
    column: int
    message: str
    severity: str  # error, warning, info
    rule_id: str = ""


class CodeTool:
    """Code analysis, symbol extraction, and metrics computation.

    Usage::

        tool = CodeTool()
        symbols = tool.extract_symbols("src/main.py")
        metrics = tool.compute_metrics("src/main.py")
    """

    def extract_symbols(self, source: str, language: CodeLanguage = CodeLanguage.PYTHON) -> list[CodeSymbol]:
        if language == CodeLanguage.PYTHON:
            return self._extract_python_symbols(source)
        return self._extract_generic_symbols(source, language)

    def compute_metrics(self, source: str, file_path: str = "") -> CodeMetrics:
        lines = source.splitlines()
        total = len(lines)
        blank = sum(1 for l in lines if not l.strip())
        comment = sum(1 for l in lines if l.strip().startswith("#"))
        code = total - blank - comment

        symbols = self.extract_symbols(source)
        funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
        classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
        func_lengths = [s.end_line - s.line for s in funcs if s.end_line > s.line]

        return CodeMetrics(
            file_path=file_path,
            total_lines=total,
            code_lines=code,
            comment_lines=comment,
            blank_lines=blank,
            function_count=len(funcs),
            class_count=len(classes),
            complexity_score=len(funcs) + len(classes) * 2,
            avg_function_length=sum(func_lengths) / len(func_lengths) if func_lengths else 0.0,
        )

    @staticmethod
    def _extract_python_symbols(source: str) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return symbols
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        kind=SymbolKind.METHOD if _in_class(node) else SymbolKind.FUNCTION,
                        line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node) or "",
                    )
                )
            elif isinstance(node, ast.ClassDef):
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        kind=SymbolKind.CLASS,
                        line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node) or "",
                    )
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    symbols.append(
                        CodeSymbol(
                            name=alias.name,
                            kind=SymbolKind.IMPORT,
                            line=node.lineno,
                            end_line=node.lineno,
                        )
                    )
        return symbols

    @staticmethod
    def _extract_generic_symbols(source: str, language: CodeLanguage) -> list[CodeSymbol]:
        import re

        patterns: dict[CodeLanguage, list[tuple[SymbolKind, str]]] = {
            CodeLanguage.PYTHON: [
                (SymbolKind.FUNCTION, r"def\s+(\w+)"),
                (SymbolKind.CLASS, r"class\s+(\w+)"),
            ],
            CodeLanguage.JAVASCRIPT: [
                (SymbolKind.FUNCTION, r"function\s+(\w+)"),
                (SymbolKind.CLASS, r"class\s+(\w+)"),
            ],
        }
        symbols: list[CodeSymbol] = []
        for kind, pattern in patterns.get(language, []):
            for m in re.finditer(pattern, source):
                line_num = source[: m.start()].count("\n") + 1
                symbols.append(
                    CodeSymbol(name=m.group(1), kind=kind, line=line_num, end_line=line_num)
                )
        return symbols


def _in_class(node: ast.AST) -> bool:
    for parent in reversed(getattr(node, "_parent", ()) if hasattr(node, "_parent") else []):
        if isinstance(parent, ast.ClassDef):
            return True
    return False
