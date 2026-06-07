"""
Built-in tool handlers for Lyra.

Provides four default tools: ReadFile, WriteFile, RunBash (sandboxed
subprocess), and WebSearch (stub).  These are registered by
``register_builtins()``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict

from lyra.tools.registry import ToolDef


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def _read_file(**kwargs: Any) -> Dict[str, Any]:
    """Read a file from disk.  Kwargs: ``path`` (required), ``encoding``."""
    path = kwargs.get("path", "")
    if not path:
        return {"success": False, "error": "Missing required parameter: 'path'"}

    encoding = kwargs.get("encoding", "utf-8")
    try:
        text = Path(path).read_text(encoding=encoding, errors="replace")
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: '{path}'"}
    except IsADirectoryError:
        return {"success": False, "error": f"'{path}' is a directory"}
    except PermissionError:
        return {"success": False, "error": f"Permission denied: '{path}'"}
    except OSError as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "output": text}


async def _write_file(**kwargs: Any) -> Dict[str, Any]:
    """Write content to a file.  Kwargs: ``path`` (required), ``content`` (required), ``encoding``."""
    path = kwargs.get("path", "")
    content = kwargs.get("content", "")
    if not path:
        return {"success": False, "error": "Missing required parameter: 'path'"}
    if content is None:
        return {"success": False, "error": "Missing required parameter: 'content'"}

    encoding = kwargs.get("encoding", "utf-8")
    content_str = str(content)

    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content_str, encoding=encoding)
    except PermissionError:
        return {"success": False, "error": f"Permission denied: '{path}'"}
    except IsADirectoryError:
        return {"success": False, "error": f"'{path}' is a directory"}
    except OSError as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "output": f"Wrote {len(content_str.encode(encoding))} bytes to '{path}'"}


async def _run_bash(**kwargs: Any) -> Dict[str, Any]:
    """Run a shell command in a subprocess.  Kwargs: ``command`` (required), ``timeout`` (optional seconds).

    Cancellation-safe: catches ``CancelledError`` and kills the subprocess
    before returning, ensuring no orphan processes are left behind.
    """
    command = kwargs.get("command", "")
    if not command:
        return {"success": False, "error": "Missing required parameter: 'command'"}

    timeout = float(kwargs.get("timeout", 30))

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        return {"success": False, "error": str(exc)}

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        # Kill the subprocess so we don't leave orphans
        proc.kill()
        await proc.wait()
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except OSError as exc:
        proc.kill()
        await proc.wait()
        return {"success": False, "error": str(exc)}

    out_text = stdout.decode("utf-8", errors="replace") if stdout else ""
    err_text = stderr.decode("utf-8", errors="replace") if stderr else ""
    combined = out_text
    if err_text:
        if combined:
            combined += "\n" + err_text
        else:
            combined = err_text

    return {
        "success": proc.returncode == 0,
        "output": combined,
        "error": None if proc.returncode == 0 else err_text or f"Exit code {proc.returncode}",
    }


async def _web_search(**kwargs: Any) -> Dict[str, Any]:
    """Stub web-search tool.  Kwargs: ``query`` (required)."""
    _ = kwargs.get("query", "")
    return {
        "success": False,
        "error": "WebSearch is a stub — no search backend configured",
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_builtins() -> list[ToolDef]:
    """Create and return the four built-in ToolDef instances.

    Caller is responsible for registering them with a ``ToolRegistry``.
    """
    return [
        ToolDef(
            name="ReadFile",
            description="Read the contents of a file from disk.",
            capabilities=["file"],
            sandbox_requirements={"allowed_paths": ["**"], "timeout_seconds": 15},
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or workspace-relative file path",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8",
                    },
                },
                "required": ["path"],
            },
            handler=_read_file,
        ),
        ToolDef(
            name="WriteFile",
            description="Write content to a file on disk.",
            capabilities=["file"],
            sandbox_requirements={"allowed_paths": ["**"], "timeout_seconds": 15},
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or workspace-relative file path",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8",
                    },
                },
                "required": ["path", "content"],
            },
            handler=_write_file,
        ),
        ToolDef(
            name="RunBash",
            description="Execute a shell command in a subprocess.",
            capabilities=["shell"],
            sandbox_requirements={"timeout_seconds": 30, "max_output_bytes": 1_048_576},
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (default: 30)",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
            handler=_run_bash,
        ),
        ToolDef(
            name="WebSearch",
            description="Perform a web search (stub — requires backend configuration).",
            capabilities=["network"],
            sandbox_requirements={"allowed_domains": ["*"], "timeout_seconds": 30},
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                },
                "required": ["query"],
            },
            handler=_web_search,
        ),
    ]
