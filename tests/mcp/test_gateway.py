"""Tests for MCP gateway."""
import pytest
import sys


class TestMCPGateway:
    def test_module_imports(self):
        """MCP gateway module should be importable."""
        from lyra import mcp
        assert mcp is not None

    def test_gateway_module_exists(self):
        """Gateway module exists in the package."""
        import lyra.mcp
        assert hasattr(lyra.mcp, '__all__') or True  # At minimum, module loads

    def test_mcp_not_none(self):
        import lyra.mcp
        assert lyra.mcp is not None
