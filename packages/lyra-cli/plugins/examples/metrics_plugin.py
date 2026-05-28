"""Example plugin: Code metrics analyzer.

Demonstrates a more complex plugin with multiple tools and state.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class MetricsAnalyzer:
    """Stateful metrics analyzer."""

    def __init__(self):
        self.cache = {}

    def analyze_file(
        self,
        file_path: str,
        *,
        repo_root: str = ".",
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Analyze code metrics for a Python file.

        Args:
            file_path: Path to Python file.
            repo_root: Repository root (default: ".").
            use_cache: Use cached results (default: True).

        Returns:
            Dict with code metrics.
        """
        cache_key = f"{repo_root}:{file_path}"

        if use_cache and cache_key in self.cache:
            return {**self.cache[cache_key], "cached": True}

        root = Path(repo_root).resolve()
        target = Path(file_path)
        if not target.is_absolute():
            target = root / target

        if not target.exists():
            return {"error": f"file not found: {file_path}", "analyzed": False}

        try:
            code = target.read_text(encoding="utf-8")
            tree = ast.parse(code, filename=str(target))
        except SyntaxError as e:
            return {
                "error": f"syntax error: {e}",
                "analyzed": False,
                "line": e.lineno,
            }

        metrics = {
            "lines": len(code.splitlines()),
            "functions": sum(
                1
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ),
            "classes": sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)),
            "imports": sum(
                1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
            ),
            "analyzed": True,
            "cached": False,
        }

        if use_cache:
            self.cache[cache_key] = metrics

        return metrics

    def clear_cache(self) -> dict[str, Any]:
        """Clear the metrics cache.

        Returns:
            Dict with cache stats.
        """
        count = len(self.cache)
        self.cache.clear()
        return {"cleared": count, "cache_size": 0}


# Create analyzer instance
analyzer = MetricsAnalyzer()


# Plugin manifest
manifest = {
    "name": "metrics-plugin",
    "version": "1.0.0",
    "description": "Code metrics analyzer with caching",
    "author": "Lyra Team",
    "tools": [
        {
            "name": "analyze_metrics",
            "function": analyzer.analyze_file,
            "description": "Analyze code metrics for a Python file",
            "category": "code",
        },
        {
            "name": "clear_metrics_cache",
            "function": analyzer.clear_cache,
            "description": "Clear the metrics cache",
            "category": "code",
        },
    ],
}
