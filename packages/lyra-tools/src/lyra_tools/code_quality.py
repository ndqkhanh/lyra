"""Code quality tool implementations — lint, format, complexity, dead imports.

These tools provide structured code analysis without requiring raw shell access.
Each function returns a dict suitable for LLM tool-call marshalling.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _find_executable(name: str) -> str | None:
    """Find an executable in PATH or common venv locations."""
    # Check common venv paths
    venv_bin = Path(sys.prefix) / "bin"
    candidates = [
        venv_bin / name,
        Path.home() / ".local" / "bin" / name,
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)

    # Fall back to shutil.which
    import shutil
    return shutil.which(name)


def _run_command(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    """Run a command and return structured output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return {
            "code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"code": -1, "stdout": "", "stderr": f"timeout after {timeout}s"}
    except FileNotFoundError:
        return {"code": -1, "stdout": "", "stderr": f"command not found: {cmd[0]}"}


# ── lint ────────────────────────────────────────────────────────────────────

def code_lint(
    path: str = ".",
    *,
    linter: str = "ruff",
    repo_root: str = ".",
) -> dict[str, Any]:
    """Run a linter on a file or directory."""
    target = Path(repo_root) / path
    if not target.exists():
        return {"error": f"path not found: {path}", "issues": []}

    if linter == "ruff":
        exe = _find_executable("ruff") or "ruff"
        result = _run_command([exe, "check", str(target), "--output-format=text"])
    elif linter == "flake8":
        exe = _find_executable("flake8") or "flake8"
        result = _run_command([exe, str(target)])
    elif linter == "pylint":
        exe = _find_executable("pylint") or "pylint"
        result = _run_command([exe, str(target), "--output-format=text"])
    else:
        return {"error": f"unsupported linter: {linter}", "issues": []}

    issues = []
    for line in result["stdout"].split("\n"):
        line = line.strip()
        if line:
            issues.append(line)

    return {
        "path": str(target),
        "linter": linter,
        "issues": issues,
        "count": len(issues),
        "exit_code": result["code"],
    }


# ── format ───────────────────────────────────────────────────────────────────

def code_format(
    path: str = ".",
    *,
    formatter: str = "ruff",
    repo_root: str = ".",
    check_only: bool = False,
) -> dict[str, Any]:
    """Format code using a project formatter."""
    target = Path(repo_root) / path
    if not target.exists():
        return {"error": f"path not found: {path}", "formatted": False}

    if formatter in ("ruff", "black"):
        exe = _find_executable("ruff") or "ruff"
        cmd = [exe, "format", str(target)]
        if check_only:
            cmd.append("--check")
        result = _run_command(cmd)
    elif formatter == "isort":
        exe = _find_executable("isort") or "isort"
        cmd = [exe, str(target)]
        if check_only:
            cmd.append("--check-only")
        result = _run_command(cmd)
    else:
        return {"error": f"unsupported formatter: {formatter}", "formatted": False}

    return {
        "path": str(target),
        "formatter": formatter,
        "formatted": result["code"] == 0 and not check_only,
        "needs_format": result["code"] != 0 and check_only,
        "exit_code": result["code"],
    }


# ── complexity ────────────────────────────────────────────────────────────────

def code_complexity(
    file: str,
    *,
    repo_root: str = ".",
) -> dict[str, Any]:
    """Analyze cyclomatic complexity of Python functions."""
    target = Path(repo_root) / file
    if not target.exists():
        return {"error": f"file not found: {file}", "functions": []}

    if not target.suffix == ".py":
        return {"error": "complexity analysis only supports .py files", "functions": []}

    try:
        source = target.read_text()
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"syntax error: {e}", "functions": []}

    functions: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = _cyclomatic_complexity(node)
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "col": node.col_offset,
                "complexity": complexity,
                "risk": (
                    "high" if complexity > 15
                    else "medium" if complexity > 10
                    else "low"
                ),
            })

    functions.sort(key=lambda f: f["complexity"], reverse=True)
    return {
        "file": str(target),
        "functions": functions,
        "count": len(functions),
        "average_complexity": (
            sum(f["complexity"] for f in functions) / len(functions)
            if functions else 0.0
        ),
    }


def _cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """McCabe cyclomatic complexity: 1 + number of decision points."""
    decision_points = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            decision_points += 1
        elif isinstance(child, ast.BoolOp):
            # Each 'and'/'or' operand beyond the first adds a decision point
            decision_points += len(child.values) - 1
    return 1 + decision_points


# ── dead imports ──────────────────────────────────────────────────────────────

def code_dead_imports(
    path: str = ".",
    *,
    repo_root: str = ".",
) -> dict[str, Any]:
    """Find unused imports in Python files."""
    exe = _find_executable("ruff") or "ruff"
    target = Path(repo_root) / path

    if not target.exists():
        return {"error": f"path not found: {path}", "unused_imports": []}

    result = _run_command([
        exe, "check", str(target), "--select=F401,F811", "--output-format=text",
    ])

    unused: list[dict[str, Any]] = []
    for line in result["stdout"].split("\n"):
        line = line.strip()
        if line:
            # Parse ruff output: "file.py:10:8: F401 `os` imported but unused"
            parts = line.split(":", 3)
            if len(parts) >= 4:
                unused.append({
                    "file": parts[0],
                    "line": parts[1].strip() if len(parts) > 1 else "",
                    "col": parts[2].strip() if len(parts) > 2 else "",
                    "message": parts[3].strip() if len(parts) > 3 else line,
                })

    return {
        "path": str(target),
        "unused_imports": unused,
        "count": len(unused),
    }


__all__ = [
    "code_lint",
    "code_format",
    "code_complexity",
    "code_dead_imports",
]
