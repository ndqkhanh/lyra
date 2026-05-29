"""Tests for unified API entry point.

Phase 4, Week 1: System Integration - Unified API
Following TDD approach: RED → GREEN → REFACTOR
"""
from pathlib import Path

import pytest
from lyra_core.api import APIError, APIResponse, LyraAPI


class TestLyraAPIInitialization:
    """Test API initialization and configuration."""

    def test_api_creates_with_defaults(self) -> None:
        """API should initialize with sensible defaults."""
        api = LyraAPI()
        assert api is not None
        assert api.repo_root == Path.cwd()

    def test_api_accepts_custom_repo_root(self, tmp_path: Path) -> None:
        """API should accept custom repository root."""
        custom_root = tmp_path / "test-repo"
        custom_root.mkdir()
        api = LyraAPI(repo_root=custom_root)
        assert api.repo_root == custom_root

    def test_api_validates_repo_root_exists(self) -> None:
        """API should validate that repo root exists."""
        with pytest.raises(APIError, match="Repository root does not exist"):
            LyraAPI(repo_root=Path("/nonexistent/path"))


class TestLyraAPIErrorHandling:
    """Test consistent error handling across API."""

    def test_api_error_has_message(self) -> None:
        """APIError should contain error message."""
        error = APIError("Test error message")
        assert str(error) == "Test error message"

    def test_api_error_has_code(self) -> None:
        """APIError should support error codes."""
        error = APIError("Test error", code="TEST_ERROR")
        assert error.code == "TEST_ERROR"

    def test_api_error_has_details(self) -> None:
        """APIError should support additional details."""
        error = APIError("Test error", details={"key": "value"})
        assert error.details == {"key": "value"}


class TestLyraAPIResponse:
    """Test API response format."""

    def test_response_success_format(self) -> None:
        """Successful response should have consistent format."""
        response = APIResponse.success(data={"result": "test"})
        assert response.success is True
        assert response.data == {"result": "test"}
        assert response.error is None

    def test_response_error_format(self) -> None:
        """Error response should have consistent format."""
        response = APIResponse.error_response(message="Test error", code="TEST_ERROR")
        assert response.success is False
        assert response.data is None
        assert response.error is not None
        assert response.error["message"] == "Test error"
        assert response.error["code"] == "TEST_ERROR"

    def test_response_to_dict(self) -> None:
        """Response should serialize to dict."""
        response = APIResponse.success(data={"result": "test"})
        result = response.to_dict()
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["data"] == {"result": "test"}


class TestLyraAPICapabilities:
    """Test API capability discovery."""

    def test_api_lists_available_capabilities(self) -> None:
        """API should list all available capabilities."""
        api = LyraAPI()
        capabilities = api.list_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        # Core capabilities that should always be present
        assert "agent_loop" in capabilities
        assert "tools" in capabilities
        assert "memory" in capabilities

    def test_api_checks_capability_availability(self) -> None:
        """API should check if specific capability is available."""
        api = LyraAPI()
        assert api.has_capability("agent_loop") is True
        assert api.has_capability("nonexistent_capability") is False


class TestLyraAPIAgentLoop:
    """Test agent loop integration through API."""

    def test_api_runs_agent_loop(self) -> None:
        """API should execute agent loop with task."""
        api = LyraAPI()
        response = api.run_agent(task="echo 'test'", mode="plan")
        assert response.success is True
        assert response.data is not None

    def test_api_agent_loop_validates_mode(self) -> None:
        """API should validate agent loop mode."""
        api = LyraAPI()
        response = api.run_agent(task="test", mode="invalid_mode")
        assert response.success is False
        assert "Invalid mode" in response.error["message"]

    def test_api_agent_loop_handles_errors(self) -> None:
        """API should handle agent loop errors gracefully."""
        api = LyraAPI()
        # Simulate error condition
        response = api.run_agent(task="", mode="plan")
        assert response.success is False
        assert response.error is not None


class TestLyraAPITools:
    """Test tool execution through API."""

    def test_api_lists_available_tools(self) -> None:
        """API should list all available tools."""
        api = LyraAPI()
        tools = api.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Core tools that should be present
        tool_names = [t["name"] for t in tools]
        assert "Read" in tool_names
        assert "Write" in tool_names
        assert "Bash" in tool_names

    def test_api_executes_tool(self) -> None:
        """API should execute tool with parameters."""
        api = LyraAPI()
        response = api.execute_tool(
            tool_name="Read",
            parameters={"file_path": __file__}
        )
        assert response.success is True
        assert response.data is not None

    def test_api_tool_execution_validates_parameters(self) -> None:
        """API should validate tool parameters."""
        api = LyraAPI()
        response = api.execute_tool(tool_name="Read", parameters={})
        assert response.success is False
        assert "Missing required parameter" in response.error["message"]


class TestLyraAPIMemory:
    """Test memory operations through API."""

    def test_api_stores_memory(self) -> None:
        """API should store memory entries."""
        api = LyraAPI()
        response = api.store_memory(
            key="test_key",
            value="test_value",
            namespace="test"
        )
        assert response.success is True

    def test_api_retrieves_memory(self) -> None:
        """API should retrieve stored memory."""
        api = LyraAPI()
        # Store first
        api.store_memory(key="test_key", value="test_value", namespace="test")
        # Retrieve
        response = api.retrieve_memory(key="test_key", namespace="test")
        assert response.success is True
        assert response.data == "test_value"

    def test_api_memory_not_found(self) -> None:
        """API should handle missing memory gracefully."""
        api = LyraAPI()
        response = api.retrieve_memory(key="nonexistent", namespace="test")
        assert response.success is False
        assert response.error is not None


class TestLyraAPIHealthCheck:
    """Test API health check endpoint."""

    def test_api_health_check(self) -> None:
        """API should provide health check."""
        api = LyraAPI()
        health = api.health_check()
        assert health["status"] == "healthy"
        assert "version" in health
        assert "capabilities" in health

    def test_api_health_check_includes_component_status(self) -> None:
        """Health check should include component status."""
        api = LyraAPI()
        health = api.health_check()
        assert "components" in health
        components = health["components"]
        assert "agent_loop" in components
        assert "tools" in components
        assert "memory" in components
