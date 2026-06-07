"""
Tool Executor.

Runs tool handlers in sandboxed subprocesses with timeout, output capture,
and sandbox safety checks (command denylist, path restrictions, domain
allowlist).
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Optional

from src.tools.registry import ToolRegistry, ToolResult
from src.tools.sandbox import (
    SandboxConfig,
    check_command_safety,
    check_domain_safety,
    check_path_safety,
)


class ToolExecutor:
    """Sandboxed tool executor.

    Wraps a ``ToolRegistry`` and enforces sandbox constraints at runtime.

    The executor-level ``timeout`` kwarg controls the ``asyncio.wait_for``
    deadline for the entire tool invocation, *and* is forwarded to the tool
    handler (under the name ``timeout``) so handlers that manage their own
    subprocess communication can respect it.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        sandbox_config: Optional[SandboxConfig] = None,
    ) -> None:
        self._registry = registry
        self._sandbox = sandbox_config or SandboxConfig()

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    @property
    def sandbox_config(self) -> SandboxConfig:
        return self._sandbox

    # ------------------------------------------------------------------
    # Single-tool execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        tool_name: str,
        *,
        timeout: Optional[int] = None,
        **params: Any,
    ) -> ToolResult:
        """Execute a tool by name with sandbox safety checks.

        Steps:
        1. Lookup tool in registry.
        2. Resolve sandbox requirements (tool-level overrides config-level).
        3. Run safety checks (path, command, domain) based on capabilities.
        4. Dispatch with timeout.

        Parameters
        ----------
        tool_name:
            Registered tool name.
        timeout:
            Executor-level timeout in seconds. When provided, it overrides
            both the tool's ``sandbox_requirements.timeout_seconds`` and the
            global ``SandboxConfig.timeout_seconds``.  The value is also
            forwarded to the handler as ``params["timeout"]`` so that
            subprocess-based handlers can set their internal kill timer.
        **params:
            Keyword arguments forwarded to the tool handler.
        """
        tool = self._registry.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: '{tool_name}'",
            )

        # Merge sandbox config with tool-level overrides
        tool_timeout = (
            timeout
            if timeout is not None
            else (
                tool.sandbox_requirements.get("timeout_seconds")
                or self._sandbox.timeout_seconds
            )
        )

        # Inject timeout into handler params if the tool's parameter schema
        # defines a ``timeout`` property and the caller did not already
        # provide one via **params.
        tool_schema = tool.parameters or {}
        if "timeout" in tool_schema.get("properties", {}) and "timeout" not in params:
            params["timeout"] = tool_timeout

        # Check and resolve file paths for file-capable tools
        if "file" in tool.capabilities:
            file_path = params.get("path", params.get("file_path", ""))
            if file_path:
                path_error = check_path_safety(file_path, self._sandbox)
                if path_error:
                    return ToolResult(success=False, error=path_error)

                # Resolve relative paths to workspace-absolute so the handler
                # writes/reads inside the sandbox rather than the process CWD.
                workspace = Path(self._sandbox.workspace_dir).resolve()
                candidate = Path(file_path)
                if not candidate.is_absolute():
                    candidate = workspace / file_path
                # Only rewrite if the handler param uses a known key name
                if "path" in params:
                    params["path"] = str(candidate)
                elif "file_path" in params:
                    params["file_path"] = str(candidate)

        # Check command for shell-capable tools
        if "shell" in tool.capabilities:
            command = params.get("command", params.get("cmd", ""))
            if command:
                cmd_error = check_command_safety(command, self._sandbox)
                if cmd_error:
                    return ToolResult(success=False, error=cmd_error)

        # Check domains for network-capable tools
        if "network" in tool.capabilities:
            domain = params.get("domain", params.get("url", ""))
            if domain:
                # Extract hostname from URL if applicable
                host = domain
                if "://" in domain:
                    host = domain.split("://", 1)[1].split("/")[0].split(":")[0]
                domain_error = check_domain_safety(host, self._sandbox)
                if domain_error:
                    return ToolResult(success=False, error=domain_error)

        # Execute via registry (which handles validation + dispatch)
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                self._registry.run(tool_name, **params),
                timeout=tool_timeout,
            )
        except asyncio.TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' timed out after {tool_timeout}s",
                execution_time_ms=elapsed,
            )

        return result
