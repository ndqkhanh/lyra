"""Static code analysis for self-modification."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from typing import ClassVar

from .exceptions import CodeAnalysisError

_STDLIB_MODULES: frozenset[str] = frozenset({
    "abc", "ast", "asyncio", "base64", "collections", "copy", "csv",
    "datetime", "decimal", "difflib", "enum", "functools", "glob",
    "hashlib", "heapq", "http", "importlib", "inspect", "io", "itertools",
    "json", "logging", "math", "multiprocessing", "operator", "os",
    "pathlib", "pickle", "platform", "pprint", "queue", "random", "re",
    "secrets", "shutil", "signal", "socket", "sqlite3", "statistics",
    "string", "struct", "subprocess", "sys", "tempfile", "textwrap",
    "threading", "time", "traceback", "types", "typing", "unittest",
    "urllib", "uuid", "warnings", "weakref", "xml", "zipfile",
})


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration for static code analysis."""

    max_file_size: int = 100000
    ignore_patterns: tuple[str, ...] = ("__pycache__", ".git", "tests")
    complexity_threshold: int = 10


@dataclass(frozen=True)
class CodeMetrics:
    """Metrics computed for a single source file."""

    file_path: str
    loc: int
    complexity: int
    functions: tuple[str, ...]
    imports: tuple[str, ...]
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class HotspotReport:
    """Aggregate report of code hotspots across a package."""

    metrics: tuple[CodeMetrics, ...]
    hotspots: tuple[str, ...]
    suggestions: tuple[str, ...]
    overall_health: float


class CodeAnalyzer:
    """Static code analysis for self-modification."""

    CONFIG: ClassVar[AnalysisConfig] = AnalysisConfig()

    @staticmethod
    def compute_complexity(source: str) -> int:
        """Compute cyclomatic complexity of source code."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 1
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (
                ast.If, ast.While, ast.For, ast.AsyncFor,
                ast.ExceptHandler, ast.With, ast.AsyncWith,
            )):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity

    @staticmethod
    def extract_imports(source: str) -> tuple[str, ...]:
        """Extract all import names from source code."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return ()
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    if module:
                        imports.append(f"{module}.{alias.name}")
                    else:
                        imports.append(alias.name)
        return tuple(sorted(set(imports)))

    @staticmethod
    async def analyze_file(path: str) -> CodeMetrics:
        """Analyze a single Python source file."""
        if not os.path.isfile(path):
            raise CodeAnalysisError(f"File not found: {path}")
        file_size = os.path.getsize(path)
        if file_size > CodeAnalyzer.CONFIG.max_file_size:
            raise CodeAnalysisError(
                f"File exceeds max size ({file_size} > {CodeAnalyzer.CONFIG.max_file_size}): {path}"
            )
        try:
            with open(path) as f:
                source = f.read()
        except OSError as e:
            raise CodeAnalysisError(f"Cannot read file {path}: {e}") from e
        loc = len(source.splitlines())
        complexity = CodeAnalyzer.compute_complexity(source)
        imports = CodeAnalyzer.extract_imports(source)
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise CodeAnalysisError(f"Syntax error in {path}: {e}") from e
        functions = tuple(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        dependencies: list[str] = []
        for imp in imports:
            top_level = imp.split(".")[0]
            if top_level not in _STDLIB_MODULES:
                dependencies.append(imp)
        return CodeMetrics(
            file_path=path,
            loc=loc,
            complexity=complexity,
            functions=functions,
            imports=imports,
            dependencies=tuple(dependencies),
        )

    @staticmethod
    async def analyze_package(package_root: str) -> HotspotReport:
        """Analyze all Python files in a package directory."""
        if not os.path.isdir(package_root):
            raise CodeAnalysisError(f"Directory not found: {package_root}")
        all_metrics: list[CodeMetrics] = []
        for dirpath, dirnames, filenames in os.walk(package_root):
            dirnames[:] = [
                d for d in dirnames
                if d not in CodeAnalyzer.CONFIG.ignore_patterns
            ]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    metrics = await CodeAnalyzer.analyze_file(full)
                    all_metrics.append(metrics)
                except CodeAnalysisError:
                    continue
        hotspots: list[str] = []
        suggestions: list[str] = []
        threshold = CodeAnalyzer.CONFIG.complexity_threshold
        for m in all_metrics:
            if m.complexity > threshold:
                hotspots.append(m.file_path)
                suggestions.append(
                    f"Consider refactoring {m.file_path} "
                    f"(complexity={m.complexity} > {threshold})"
                )
        if all_metrics:
            total_complexity = sum(m.complexity for m in all_metrics)
            avg_health = max(0.0, 100.0 - total_complexity / len(all_metrics))
        else:
            avg_health = 100.0
        return HotspotReport(
            metrics=tuple(all_metrics),
            hotspots=tuple(hotspots),
            suggestions=tuple(suggestions),
            overall_health=round(avg_health, 2),
        )
