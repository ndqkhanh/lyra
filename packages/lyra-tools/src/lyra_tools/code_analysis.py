"""Code analysis tools — AST parsing, refactoring, and code understanding.

Implements Hermes-agent style code analysis with tree-sitter and AST operations.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def analyze_complexity(
    file_path: str,
    *,
    repo_root: str = ".",
    threshold: int = 10,
) -> dict[str, Any]:
    """Analyze cyclomatic complexity of Python code.

    Args:
        file_path: Path to Python file.
        repo_root: Repository root (default: ".").
        threshold: Complexity threshold for warnings (default: 10).

    Returns:
        Dict with complexity metrics per function.
    """
    root = Path(repo_root).resolve()
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target

    if not target.exists():
        return {"error": f"file not found: {file_path}", "analyzed": False}

    if not target.suffix == ".py":
        return {"error": "only Python files supported", "analyzed": False}

    try:
        code = target.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(target))
    except SyntaxError as e:
        return {
            "error": f"syntax error: {e}",
            "analyzed": False,
            "line": e.lineno,
        }

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = _calculate_complexity(node)
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": complexity,
                "risk": "high" if complexity > threshold else "low",
            })

    return {
        "file": str(target.relative_to(root)),
        "functions": functions,
        "total_functions": len(functions),
        "high_complexity_count": sum(1 for f in functions if f["risk"] == "high"),
        "analyzed": True,
    }


def _calculate_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate cyclomatic complexity for a function."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.ExceptHandler,)):
            complexity += 1
    return complexity


def find_references(
    symbol: str,
    *,
    repo_root: str = ".",
    file_pattern: str = "**/*.py",
    max_results: int = 100,
) -> dict[str, Any]:
    """Find all references to a symbol in the codebase.

    Args:
        symbol: Symbol name to search for.
        repo_root: Repository root (default: ".").
        file_pattern: Glob pattern for files (default: "**/*.py").
        max_results: Maximum results to return (default: 100).

    Returns:
        Dict with reference locations.
    """
    root = Path(repo_root).resolve()
    references = []

    for file_path in root.glob(file_pattern):
        if not file_path.is_file():
            continue

        try:
            code = file_path.read_text(encoding="utf-8")
            lines = code.splitlines()

            for line_num, line in enumerate(lines, start=1):
                if symbol in line:
                    references.append({
                        "file": str(file_path.relative_to(root)),
                        "line": line_num,
                        "content": line.strip(),
                    })

                    if len(references) >= max_results:
                        break
        except (OSError, UnicodeDecodeError):
            continue

        if len(references) >= max_results:
            break

    return {
        "symbol": symbol,
        "references": references,
        "count": len(references),
        "truncated": len(references) >= max_results,
    }


def extract_imports(
    file_path: str,
    *,
    repo_root: str = ".",
) -> dict[str, Any]:
    """Extract all imports from a Python file.

    Args:
        file_path: Path to Python file.
        repo_root: Repository root (default: ".").

    Returns:
        Dict with import statements.
    """
    root = Path(repo_root).resolve()
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target

    if not target.exists():
        return {"error": f"file not found: {file_path}", "extracted": False}

    try:
        code = target.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(target))
    except SyntaxError as e:
        return {
            "error": f"syntax error: {e}",
            "extracted": False,
            "line": e.lineno,
        }

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "type": "from_import",
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })

    return {
        "file": str(target.relative_to(root)),
        "imports": imports,
        "count": len(imports),
        "extracted": True,
    }


def suggest_refactoring(
    file_path: str,
    *,
    repo_root: str = ".",
    max_suggestions: int = 10,
) -> dict[str, Any]:
    """Suggest refactoring opportunities in a Python file.

    Args:
        file_path: Path to Python file.
        repo_root: Repository root (default: ".").
        max_suggestions: Maximum suggestions (default: 10).

    Returns:
        Dict with refactoring suggestions.
    """
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

    suggestions = []

    # Check for long functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
            if lines > 50:
                suggestions.append({
                    "type": "long_function",
                    "severity": "medium",
                    "line": node.lineno,
                    "message": f"Function '{node.name}' is {lines} lines long (>50)",
                    "suggestion": "Consider breaking into smaller functions",
                })

            # Check complexity
            complexity = _calculate_complexity(node)
            if complexity > 10:
                suggestions.append({
                    "type": "high_complexity",
                    "severity": "high",
                    "line": node.lineno,
                    "message": f"Function '{node.name}' has complexity {complexity} (>10)",
                    "suggestion": "Simplify logic or extract helper functions",
                })

        if len(suggestions) >= max_suggestions:
            break

    return {
        "file": str(target.relative_to(root)),
        "suggestions": suggestions[:max_suggestions],
        "count": len(suggestions),
        "analyzed": True,
    }


__all__ = [
    "analyze_complexity",
    "find_references",
    "extract_imports",
    "suggest_refactoring",
]
