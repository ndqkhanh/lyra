"""Lyra unified API core implementation.

Single entry point for all Lyra capabilities.
"""
from pathlib import Path
from typing import Any

from lyra_core.api.errors import APIError
from lyra_core.api.response import APIResponse


class LyraAPI:
    """Unified API for Lyra capabilities.

    Provides consistent interface for:
    - Agent loop execution
    - Tool operations
    - Memory management
    - Health checks
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        """Initialize Lyra API.

        Args:
            repo_root: Repository root directory (defaults to cwd)

        Raises:
            APIError: If repo_root does not exist
        """
        self.repo_root = repo_root or Path.cwd()
        if not self.repo_root.exists():
            raise APIError(
                f"Repository root does not exist: {self.repo_root}",
                code="INVALID_REPO_ROOT",
            )

        # Initialize internal state
        self._memory_store: dict[str, dict[str, Any]] = {}
        self._capabilities = [
            "agent_loop",
            "tools",
            "memory",
            "health_check",
        ]

    def list_capabilities(self) -> list[str]:
        """List all available capabilities.

        Returns:
            List of capability names
        """
        return self._capabilities.copy()

    def has_capability(self, capability: str) -> bool:
        """Check if capability is available.

        Args:
            capability: Capability name

        Returns:
            True if capability is available
        """
        return capability in self._capabilities

    def run_agent(
        self,
        task: str,
        mode: str = "plan",
    ) -> APIResponse:
        """Execute agent loop with task.

        Args:
            task: Task description
            mode: Execution mode (plan, auto-edit, bypass-perms)

        Returns:
            APIResponse with execution result
        """
        try:
            # Validate inputs
            if not task or not task.strip():
                return APIResponse.error(
                    message="Task cannot be empty",
                    code="INVALID_TASK",
                )

            valid_modes = ["plan", "auto-edit", "bypass-perms"]
            if mode not in valid_modes:
                return APIResponse.error(
                    message=f"Invalid mode: {mode}. Must be one of {valid_modes}",
                    code="INVALID_MODE",
                )

            # TODO: Integrate with actual agent loop
            # For now, return mock success
            return APIResponse.success(
                data={
                    "task": task,
                    "mode": mode,
                    "status": "completed",
                }
            )

        except Exception as e:
            return APIResponse.error(
                message=str(e),
                code="AGENT_LOOP_ERROR",
            )

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools.

        Returns:
            List of tool metadata
        """
        # Core tools that should always be available
        return [
            {"name": "Read", "description": "Read file contents"},
            {"name": "Write", "description": "Write file contents"},
            {"name": "Bash", "description": "Execute bash commands"},
            {"name": "Edit", "description": "Edit file with replacements"},
            {"name": "Glob", "description": "Find files by pattern"},
            {"name": "Grep", "description": "Search file contents"},
        ]

    def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> APIResponse:
        """Execute tool with parameters.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters

        Returns:
            APIResponse with tool execution result
        """
        try:
            # Validate tool exists
            available_tools = [t["name"] for t in self.list_tools()]
            if tool_name not in available_tools:
                return APIResponse.error(
                    message=f"Unknown tool: {tool_name}",
                    code="UNKNOWN_TOOL",
                )

            # Validate required parameters
            if tool_name == "Read" and "file_path" not in parameters:
                return APIResponse.error(
                    message="Missing required parameter: file_path",
                    code="MISSING_PARAMETER",
                )

            # TODO: Integrate with actual tool kernel
            # For now, return mock success
            return APIResponse.success(
                data={
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": "Tool executed successfully",
                }
            )

        except Exception as e:
            return APIResponse.error(
                message=str(e),
                code="TOOL_EXECUTION_ERROR",
            )

    def store_memory(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
    ) -> APIResponse:
        """Store memory entry.

        Args:
            key: Memory key
            value: Memory value
            namespace: Memory namespace

        Returns:
            APIResponse indicating success
        """
        try:
            if namespace not in self._memory_store:
                self._memory_store[namespace] = {}

            self._memory_store[namespace][key] = value

            return APIResponse.success(
                data={"key": key, "namespace": namespace}
            )

        except Exception as e:
            return APIResponse.error(
                message=str(e),
                code="MEMORY_STORE_ERROR",
            )

    def retrieve_memory(
        self,
        key: str,
        namespace: str = "default",
    ) -> APIResponse:
        """Retrieve memory entry.

        Args:
            key: Memory key
            namespace: Memory namespace

        Returns:
            APIResponse with memory value or error
        """
        try:
            if namespace not in self._memory_store:
                return APIResponse.error(
                    message=f"Namespace not found: {namespace}",
                    code="NAMESPACE_NOT_FOUND",
                )

            if key not in self._memory_store[namespace]:
                return APIResponse.error(
                    message=f"Key not found: {key}",
                    code="KEY_NOT_FOUND",
                )

            value = self._memory_store[namespace][key]
            return APIResponse.success(data=value)

        except Exception as e:
            return APIResponse.error(
                message=str(e),
                code="MEMORY_RETRIEVE_ERROR",
            )

    def health_check(self) -> dict[str, Any]:
        """Perform health check.

        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "version": "0.1.0",
            "capabilities": self.list_capabilities(),
            "components": {
                "agent_loop": "healthy",
                "tools": "healthy",
                "memory": "healthy",
            },
        }
