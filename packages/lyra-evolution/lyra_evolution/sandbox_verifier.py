"""Concrete sandbox verifier for Voyager skill accumulation.

Runs candidate skills in an isolated subprocess with resource limits,
captures output, and validates against safety rules.
"""
from __future__ import annotations

import ast
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lyra_evolution.voyager import SkillCandidate


__all__ = [
    "SandboxVerifier",
    "SafetyRule",
]


class SafetyRule:
    """Defines what code patterns are forbidden in skills."""

    FORBIDDEN_IMPORTS = {
        "os",
        "subprocess",
        "sys",
        "shutil",
        "pathlib",
        "__import__",
        "eval",
        "exec",
        "compile",
    }

    FORBIDDEN_BUILTINS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",  # File I/O forbidden in sandbox
    }

    @classmethod
    def check(cls, code: str) -> tuple[bool, str]:
        """Return (safe, reason) after static analysis."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in cls.FORBIDDEN_IMPORTS:
                        return False, f"Forbidden import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module in cls.FORBIDDEN_IMPORTS:
                    return False, f"Forbidden import: {node.module}"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.FORBIDDEN_BUILTINS:
                        return False, f"Forbidden builtin: {node.func.id}"

        return True, "Static checks passed"


class SandboxVerifier:
    """Runs candidate skills in a subprocess sandbox with timeout and safety checks.

    Usage::

        verifier = SandboxVerifier(timeout_seconds=5)
        passed, feedback = verifier.verify(candidate)
    """

    def __init__(self, timeout_seconds: int = 5, max_output_bytes: int = 10_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    def verify(self, candidate: "SkillCandidate") -> tuple[bool, str]:
        """Run the candidate in a sandbox. Return (passed, feedback)."""
        # Step 1: Static safety checks
        safe, reason = SafetyRule.check(candidate.code)
        if not safe:
            return False, f"Safety violation: {reason}"

        # Step 2: Execute in subprocess sandbox
        try:
            result = self._run_in_sandbox(candidate.code)
            if result.returncode != 0:
                stderr = result.stderr[:500] if result.stderr else ""
                return False, f"Execution failed (exit {result.returncode}): {stderr}"

            # Step 3: Validate output size
            if len(result.stdout) > self.max_output_bytes:
                return False, f"Output too large: {len(result.stdout)} bytes"

            return True, "Verification passed"

        except subprocess.TimeoutExpired:
            return False, f"Timeout after {self.timeout_seconds}s"
        except Exception as e:
            return False, f"Sandbox error: {e}"

    def _run_in_sandbox(self, code: str) -> subprocess.CompletedProcess:
        """Execute code in a temporary file with subprocess isolation."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(code)
            tmp_path = Path(tmp.name)

        try:
            result = subprocess.run(
                ["python", str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return result
        finally:
            tmp_path.unlink(missing_ok=True)
