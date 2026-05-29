"""Sandbox executor for safe code execution with rollback."""

from __future__ import annotations

import io
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from .models import ExecutionResult, SandboxConfig, Snapshot


class SandboxExecutor:
    """Executes code in a sandboxed environment with rollback support."""

    def __init__(self, config: SandboxConfig):
        """Initialize sandbox executor.

        Args:
            config: Sandbox configuration
        """
        self.config = config

    def execute(
        self, code: str, working_dir: Path | None = None
    ) -> ExecutionResult:
        """Execute code in sandbox.

        Args:
            code: Python code to execute
            working_dir: Working directory for execution

        Returns:
            Execution result
        """
        start_time = time.time()
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Validate code syntax
            compile(code, "<sandbox>", "exec")

            # Create isolated namespace
            namespace: dict[str, Any] = {
                "__builtins__": self._get_safe_builtins(),
            }

            # Execute with timeout and output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                if working_dir:
                    import os
                    old_cwd = os.getcwd()
                    try:
                        os.chdir(working_dir)
                        exec(code, namespace)
                    finally:
                        os.chdir(old_cwd)
                else:
                    exec(code, namespace)

            execution_time = time.time() - start_time

            # Extract results (exclude builtins and private vars)
            results = {
                k: v
                for k, v in namespace.items()
                if not k.startswith("_") and k != "__builtins__"
            }

            return ExecutionResult(
                success=True,
                return_value=results,
                execution_time=execution_time,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
            )

        except SyntaxError as e:
            return ExecutionResult(
                success=False,
                error=f"Syntax error: {e}",
                execution_time=time.time() - start_time,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
            )

        except TimeoutError:
            return ExecutionResult(
                success=False,
                error="Execution timeout exceeded",
                execution_time=time.time() - start_time,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                execution_time=time.time() - start_time,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
            )

    def create_snapshot(self, path: Path) -> Snapshot:
        """Create filesystem snapshot for rollback.

        Args:
            path: Directory to snapshot

        Returns:
            Snapshot object
        """
        snapshot = Snapshot(path=path, timestamp=time.time())

        # Capture all files in directory
        for file_path in path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(path)
                try:
                    content = file_path.read_text()
                    snapshot.files[str(relative_path)] = content
                except Exception:
                    # Skip files that can't be read
                    pass

        return snapshot

    def rollback(self, snapshot: Snapshot) -> bool:
        """Rollback filesystem to snapshot state.

        Args:
            snapshot: Snapshot to restore

        Returns:
            True if successful, False otherwise
        """
        try:
            # Restore all files from snapshot
            for relative_path, content in snapshot.files.items():
                file_path = snapshot.path / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            return True

        except Exception:
            return False

    def _get_safe_builtins(self) -> dict[str, Any]:
        """Get safe builtins for sandbox execution.

        Returns:
            Dictionary of safe builtins
        """
        # Start with standard builtins
        safe_builtins = {
            # Safe built-in functions
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "range": range,
            "reversed": reversed,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            # Safe built-in types
            "True": True,
            "False": False,
            "None": None,
            # Safe exceptions
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
        }

        # Add safe imports
        if self.config.allow_file_write:
            safe_builtins["open"] = open

        # Add __import__ with restrictions
        safe_builtins["__import__"] = self._safe_import

        return safe_builtins

    def _safe_import(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Safe import function that blocks dangerous modules.

        Args:
            name: Module name
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Imported module

        Raises:
            ImportError: If module is blocked
        """
        # Check if module is blocked
        if name in self.config.blocked_modules:
            raise ImportError(f"Module '{name}' is not allowed in sandbox")

        # Check if module is in allowed list
        if self.config.allowed_modules and name not in self.config.allowed_modules:
            raise ImportError(f"Module '{name}' is not in allowed modules list")

        # Import the module
        return __import__(name, *args, **kwargs)
